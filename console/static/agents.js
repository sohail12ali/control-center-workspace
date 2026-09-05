/* Agents tab — live agent conversations.

   A real back-and-forth chat, not a one-shot launcher: one process holds the
   conversation open, output streams in over SSE, and you can reply, steer
   mid-turn, queue a follow-up, or interrupt.

   Two send gestures, and the difference is real rather than cosmetic:
     send/steer  written to the agent immediately. While a turn is running,
                 this is a STEER — it lands at the next step boundary and
                 changes what happens next.
     queue       held until the current turn ends, then sent as the next turn.
   A backend whose transport is one-process-per-turn has no channel to steer
   down, so the control is hidden there rather than offered and quietly
   downgraded. The composer says which you're about to do.

   Working directory is not offered: chats run at the workspace root, which is
   what the harness assumes everywhere else.

   Backends come from console/config/agents.toml — adding a CLI is config, not
   code, and this file names no product. Capability flags (steerable,
   streaming, modes) are read off the backend, so a new entry gets the right
   controls without changes here. */
(function (C) {
  "use strict";

  var Store = window.ConsoleChatStore;
  var Render = window.ConsoleChatRender;
  var Voice = window.ConsoleVoice;
  var Pick = window.ConsoleComposerPick;

  var st = {
    host: null, chats: [], sel: null, mode: "new",
    backends: [], catalog: { skills: [], personas: [], tickets: [] },
    store: null, view: null, offMeta: null,
    // No `skill` / `persona` here any more: both are read out of the opening
    // message rather than held as separate form state that could disagree
    // with what the message says.
    form: { backend: "", mode: "", model: "", ticket: "", prompt: "" },
    sendMode: "auto",   // auto | queue
    poll: null,
    pending: null,      // one-shot handoff from another tab
    pendingTicket: "",
    catalogs: {},       // backend id -> fetched model catalogue (cached server-side)
    listShown: true,
    lane: "cli",        // which kind of agent the composer is set up for
    laneFilter: "all",  // which kinds the chat list shows
    drafts: {},         // chat id -> half-typed message, kept across repaints
  };

  /* ---------------- the two kinds of agent ----------------

     Not a grouping — a fork. A CLI backend spawns somebody else's agent and
     inherits its tools and its permission model; a console backend has no
     process at all, so the loop, the tools, the gate and the cost accounting
     are all this console's.

     They overlap on exactly ONE control, the model. Everything else is
     disjoint: a CLI has permission modes and we have none of its budgets; a
     console agent has no modes worth showing (every API row declares a single
     `default`) and budgets we enforce ourselves. Two disjoint control sets in
     one form is why the old one had a segmented control with a single button
     in it. */
  var LANES = [
    { id: "cli", api: false, icon: "wrench", label: "CLI agent",
      blurb: "Spawns someone else's agent. Their tools, their permission " +
             "model — the console watches and records." },
    { id: "api", api: true, icon: "cpu", label: "Console agent",
      blurb: "This console runs the loop: its own verbs as tools, the same " +
             "approval card, cost attributed to a ticket." },
  ];

  function lane(id) {
    return LANES.filter(function (l) { return l.id === (id || st.lane); })[0] || LANES[0];
  }

  /* Backends belonging to one lane. `is_api` is the server's own flag, so the
     fork stays keyed on transport rather than on a list of names here. */
  function laneRows(id) {
    var want = lane(id).api;
    return st.backends.filter(function (b) { return !!b.is_api === want; });
  }

  /* Switching lanes switches the backend, so the model becomes whichever one
     that backend was last used with — never the previous backend's, which
     would be an id it has never heard of. */
  function setLane(id, repaint) {
    st.lane = lane(id).id;
    C.prefs.set("agentLane", st.lane);
    var rows = laneRows(st.lane);
    var usable = rows.filter(function (b) { return b.installed; })[0];
    var pick = usable || rows[0];
    st.form.backend = pick ? pick.id : "";
    st.form.mode = "";
    st.form.model = pick ? rememberedModel(pick.id) : "";
    if (pick) loadCatalog(pick.id);
    if (repaint !== false) paintMain();
  }

  /* ---------------- chat list: shown or folded ----------------

     ONE flag drives two affordances, because they are one state. Above the
     breakpoint `.hide-list` collapses the grid column; below it, the same flag
     drives `.show-main`, which is the pane swap this shell already had — so on
     a narrow window "hide the list" means "show the chat", not "show nothing".

     The preference is remembered, but only from a desktop. Below the
     breakpoint the list is a pane you swap to, and swapping away from it after
     picking a chat is an interaction, not a setting: persisting it would
     silently fold the list away on the next wide session. */
  var NARROW = function () { return window.matchMedia("(max-width: 900px)").matches; };

  function applyShell() {
    var shell = document.getElementById("agShell");
    if (!shell) return;
    // Two classes, one state. `hide-list` collapses the grid column on a wide
    // window; `show-main` is the pane swap the narrow layout already used.
    // Only one of them does anything at any given width.
    shell.classList.toggle("hide-list", !st.listShown);
    shell.classList.toggle("show-main", !st.listShown);
    var fold = document.getElementById("agFold");
    var reveal = document.getElementById("agReveal");
    // Each button is visible in exactly one state, and both report the state
    // of the LIST rather than what pressing them would do.
    if (fold) fold.setAttribute("aria-expanded", String(st.listShown));
    if (reveal) reveal.setAttribute("aria-expanded", String(st.listShown));
  }

  function setListShown(on) {
    st.listShown = !!on;
    if (!NARROW()) C.prefs.set("chatListHidden", !st.listShown);
    applyShell();
  }

  function backend(id) {
    return st.backends.filter(function (b) { return b.id === id; })[0] || null;
  }

  /* The model you last used, per backend.

     Keyed by backend rather than held as one setting, because a model id is
     meaningless anywhere else: `claude-opus-5` means nothing to Ollama and
     `qwen3:8b` means nothing to OpenRouter. Switching backends used to clear
     the field for exactly that reason — which was right about the id and wrong
     about the memory, so every visit to a provider started by finding the same
     model again in a list of 396.

     A remembered id is NOT validated against the catalogue. It may have been
     retired, or the catalogue may not be cached yet; either way the picker
     shows it and the provider gets the final say, which is better than
     silently dropping a choice that is probably still good. */
  function rememberedModel(backendId) {
    return (C.prefs.get("modelByBackend", {}) || {})[backendId] || "";
  }

  function rememberModel(backendId, model) {
    if (!backendId) return;
    var map = C.prefs.get("modelByBackend", {}) || {};
    if (model) map[backendId] = model; else delete map[backendId];
    C.prefs.set("modelByBackend", map);
  }

  /* ---------------- rail ---------------- */
  /* Which kind a past chat was. `backend()` is the only honest source — the
     transcript records the backend id, not the kind — so a chat whose backend
     has since been removed from agents.toml reports neither rather than
     guessing from its name. */
  function chatKind(chat) {
    var b = chat.agent ? backend(chat.agent) : null;
    return b ? (b.is_api ? "api" : "cli") : "";
  }

  function chatRow(chat) {
    var selected = chat.id === st.sel && st.mode === "chat";
    var tone = chat.busy ? "info running" : (chat.alive ? "ok" : "");
    var label = chat.busy ? "working" : (chat.alive ? "live" : "ended");
    var kind = chatKind(chat);
    return C.el("div", {
      class: "lrow clickable" + (kind ? " k-" + kind : ""), role: "button", tabindex: "0",
      "aria-current": String(selected),
      style: selected ? "background:var(--accent-soft)" : "",
      onclick: function () { openChat(chat.id); },
      onkeydown: function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openChat(chat.id); } },
    }, [
      kind ? C.el("span", { class: "kind-dot", title: kind === "api"
        ? "Console agent — this console ran the loop and gated its tools."
        : "CLI agent — its own tools and permission model." },
        [C.icon(kind === "api" ? "cpu" : "wrench")]) : null,
      C.el("span", { class: "chip " + tone, text: label }),
      C.el("span", { class: "ltext" }, [
        C.el("div", { class: "truncate", style: "font-size:12.2px", text: chat.title || "(untitled)" }),
        C.el("div", { class: "muted", style: "font-size:10.8px",
          text: [chat.agent, chat.mode, chat.num_turns ? chat.num_turns + " turns" : null]
            .filter(Boolean).join(" · ") }),
      ]),
      chat.orphaned ? C.el("span", { class: "chip", title: "From a previous server run — replay only" }, ["past"]) : null,
    ]);
  }

  /* One list for both kinds, filterable.

     Not two lists: once a chat is running the kinds are identical — same
     transcript, same composer, same approval card — and splitting the history
     would mean looking in two places for "what did I run yesterday". */
  function laneFilterRow() {
    var opts = [["all", "All", ""]].concat(LANES.map(function (l) {
      return [l.id, l.label.replace(" agent", ""), l.icon];
    }));
    var row = C.el("div", { class: "lane-filter", role: "group",
                            "aria-label": "Filter chats by kind" });
    opts.forEach(function (o) {
      row.appendChild(C.el("button", {
        "aria-pressed": String(st.laneFilter === o[0]),
        onclick: function () { st.laneFilter = o[0]; paintRail(); },
      }, [o[2] ? C.icon(o[2]) : null, o[1]]));
    });
    return row;
  }

  function paintRail() {
    var pane = document.getElementById("agChats");
    if (!pane) return;
    C.clear(pane);
    if (!st.chats.length) {
      pane.appendChild(C.empty("No chats yet", "Start one with New chat.", "cpu"));
      return;
    }
    // Offered only once there are both kinds to tell apart.
    var kinds = {};
    st.chats.forEach(function (c) { var k = chatKind(c); if (k) kinds[k] = 1; });
    if (Object.keys(kinds).length > 1) pane.appendChild(laneFilterRow());

    var shown = st.chats.filter(function (c) {
      return st.laneFilter === "all" || chatKind(c) === st.laneFilter;
    });
    if (!shown.length) {
      pane.appendChild(C.el("div", { class: "muted", style: "padding:10px",
        text: "No " + lane(st.laneFilter).label.toLowerCase() + " chats yet." }));
      return;
    }
    var rows = C.el("div", { class: "rows" });
    shown.forEach(function (c) { rows.appendChild(chatRow(c)); });
    pane.appendChild(rows);
  }

  function refreshChats() {
    return C.get("/api/agents/chats").then(function (d) {
      st.chats = d.chats || [];
      paintRail();
      var live = st.chats.filter(function (c) { return c.busy; }).length;
      var chip = document.getElementById("agLive");
      if (chip) {
        chip.textContent = live ? live + " working" : String(st.chats.length);
        chip.className = "chip" + (live ? " info running" : (st.chats.length ? "" : " zero"));
      }
      return st.chats;
    }).catch(function (err) {
      var pane = document.getElementById("agChats");
      if (pane) C.clear(pane).appendChild(C.errbox(err));
    });
  }

  /* ---------------- new-chat form ---------------- */
  function field(label, hint, control) {
    return C.el("label", { class: "field" }, [
      C.el("span", {}, [label, hint ? C.el("span", { class: "muted", style: "font-weight:400", text: " " + hint }) : null]),
      control,
    ]);
  }

  function select(opts, value, onChange, aria) {
    return C.el("select", {
      "aria-label": aria || "",
      onchange: function (e) { onChange(e.target.value); },
    }, opts.map(function (o) {
      return C.el("option", { value: o[0], selected: o[0] === value || null, title: o[2] || null }, [o[1]]);
    }));
  }


  /* Which ticket this chat is working on. Optional on purpose — an
     exploratory chat belongs to no ticket, and forcing a choice would get one
     picked at random, which is worse than none: telemetry attributed to the
     wrong ticket is harder to spot than telemetry attributed to nothing.
     Closed tickets are not offered; the server filters terminal lanes. */
  function ticketField() {
    var tickets = st.catalog.tickets || [];
    if (!tickets.length) return null;
    var opts = [["", "(none — not ticket work)"]].concat(
      tickets.map(function (t) {
        return [t.id, t.id + " — " + t.title, t.stage];
      }));
    return C.el("div", { class: "fieldrow", style: "margin-bottom:10px" }, [
      field("Ticket", "attributes tokens + cost",
        select(opts, st.form.ticket, function (v) { st.form.ticket = v; }, "Ticket")),
    ]);
  }

  /* The fetched catalogue for a provider, if one has been cached.

     Read-only and offline: this GETs what `kanban agents models --refresh`
     (or the Settings button) last stored. A GET that reached a paid API would
     be one a browser repeats on back-navigation and a prefetcher makes
     unprompted, so refreshing is never something merely opening this form
     does. */
  function loadCatalog(id) {
    var b = backend(id);
    if (!b || !b.is_api || st.catalogs[id] !== undefined) return;
    st.catalogs[id] = null;   // in flight; do not ask twice
    C.get("/api/agents/models?backend=" + encodeURIComponent(id))
      .then(function (d) {
        st.catalogs[id] = d.error ? { models: [] } : d;
        if (st.mode === "new" && st.form.backend === id) paintMain();
        // A running chat needs it too: the catalogue is what tells the budget
        // panel whether this model is priced at zero, and without it a
        // genuinely free model reads as "unpriced".
        else if (st.mode === "chat" && st.repaintChat) st.repaintChat();
      })
      .catch(function () { st.catalogs[id] = { models: [] }; });
  }

  function fmtPrice(m) {
    // An unpriced model must never render as $0.00 — that reads as free, which
    // is the one thing the cost panels refuse to say without evidence. Local
    // models genuinely are free, and their card already says "local".
    if (m.input_per_mtok === undefined && m.output_per_mtok === undefined) return "";
    return "$" + (m.input_per_mtok || 0).toFixed(2) + "/" +
           (m.output_per_mtok || 0).toFixed(2) + " per Mtok";
  }

  /* The model picker.

     Was a native <select>. That was survivable while the only entries were a
     hand-written shortlist of five, and stopped being so the moment catalogue
     fetching landed: OpenRouter returns 396 rows, and a <select> can only put
     each row's price and context window in a `title` you hover one at a time.
     Now a `C.filterPicker` — type to narrow, over id, label AND hint, so
     "128k" and "free" find models the way people actually look for them.

     Order is unchanged and deliberate: cache first, hand-curated shortlist
     second, free-text last. The shortlist is a handful of ids worth one click;
     the catalogue is the provider's real answer, and could never live in a
     committed file without rotting. */
  function modelField() {
    var b = backend(st.form.backend);
    var models = (b && b.models) || [];
    var cat = (b && st.catalogs[b.id]) || null;
    var fetched = (cat && cat.models) || [];

    var rows = [{ value: "", label: "(backend default)",
                  hint: "send no --model flag" }]
      .concat(fetched.map(function (m) {
        var ctx = m.context ? C.fmtNum(m.context) + " ctx" : "";
        var price = fmtPrice(m);
        // A model priced at zero on both sides IS free, and saying so is the
        // difference between a row you can choose confidently and one you have
        // to go and look up.
        if (m.input_per_mtok === 0 && m.output_per_mtok === 0) price = "free";
        return { value: m.id, label: m.label || m.id,
                 hint: [ctx, price].filter(Boolean).join(" · ") };
      }))
      .concat(models
        // Don't list an id twice when the catalogue already carries it.
        .filter(function (m) {
          return !fetched.some(function (f) { return f.id === m.id; });
        })
        .map(function (m) {
          return { value: m.id, label: m.label || m.id, hint: m.hint || "" };
        }));

    var picker = C.filterPicker({
      rows: rows,
      value: st.form.model,
      ariaLabel: "Model",
      placeholder: "(backend default)",
      searchPlaceholder: "Filter models…",
      emptyText: "No model matches. Type a full id to use it anyway.",
      // The paste box the old picker kept beside it, folded in: anything typed
      // that matches no row is offered as an id and sent verbatim.
      custom: { label: "Use", hint: "sent verbatim" },
      onPick: function (v) {
        st.form.model = v;
        rememberModel(st.form.backend, v);
      },
    });

    var hint = "";
    if (b && b.is_api) {
      hint = cat && cat.count
        ? cat.count + " fetched" + (cat.age_days ? " · " + cat.age_days + "d old" : "")
        : "no catalogue cached — Settings ▸ Refresh models";
    }
    return field("Model", hint, picker);
  }

  function modeRow() {
    var b = backend(st.form.backend);
    /* A choice with one option is not a choice. Every API row declares
       `modes = ["default"]`, so this used to render a segmented control with a
       single button for every console agent — a control that cannot be
       operated. Keyed on the data rather than on the lane, so a backend that
       ever declares real modes gets them whichever lane it sits in. */
    if (!b || b.modes.length < 2) return null;
    if (!st.form.mode || !b.modes.some(function (m) { return m.id === st.form.mode; })) {
      st.form.mode = b.default_mode || b.modes[0].id;
    }
    var seg = C.el("div", { class: "seg" });
    b.modes.forEach(function (m) {
      seg.appendChild(C.el("button", {
        "aria-pressed": String(m.id === st.form.mode),
        title: m.blurb || m.id,
        onclick: function () { st.form.mode = m.id; paintMain(); },
      }, [m.id]));
    });
    var blurb = (b.modes.filter(function (m) { return m.id === st.form.mode; })[0] || {}).blurb || "";
    return C.el("div", { style: "margin-bottom:10px" }, [
      C.el("span", { class: "muted", style: "display:block;margin-bottom:3px", text: "Permission mode" }),
      seg,
      blurb ? C.el("div", { class: "muted", style: "margin-top:4px", text: blurb }) : null,
    ]);
  }

  /* Backend picker as cards, not a <select>.

     A dropdown hides exactly the information that decides the choice: which
     CLIs exist, whether each is installed, and whether it can be steered
     mid-turn. You had to open it, read one line, and remember the rest. Cards
     show all of that at once, and an uninstalled backend can say so in place
     rather than looking identical to a working one until you press Start. */
  function backendCard(b) {
    var chosen = b.id === st.form.backend;
    // What identifies it: a CLI is its command, a provider is its endpoint.
    var subtitle = b.is_api ? (b.base_url || "") : b.command;
    return C.el("button", {
      class: "pick-card" + (chosen ? " on" : "") + (b.installed ? "" : " off"),
      role: "radio", "aria-checked": String(chosen),
      title: b.installed ? subtitle : (b.unavailable_reason || subtitle),
      // A model id is meaningless on another backend, so switching swaps in
      // the one THIS backend was last used with rather than carrying one over.
      onclick: function () {
        st.form.backend = b.id; st.form.mode = "";
        st.form.model = rememberedModel(b.id);
        loadCatalog(b.id);
        paintMain();
      },
    }, [
      C.el("div", { class: "pick-top" }, [
        C.icon(b.is_api ? (b.is_local ? "cpu" : "external") : "wrench"),
        C.el("span", { class: "pick-name", text: b.label }),
        chosen ? C.icon("check") : null,
      ]),
      C.el("div", { class: "pick-cmd mono truncate", text: subtitle }),
      C.el("div", { class: "pick-tags" }, [
        b.installed ? null : C.el("span", { class: "chip danger", text: "unavailable" }),
        b.is_local ? C.el("span", { class: "chip ok", title:
          "Runs on this machine — free, private, works offline." }, ["local"]) : null,
        C.el("span", { class: "chip" + (b.steerable ? " ok" : ""), title: b.steerable
          ? "A message sent mid-turn lands immediately and changes what happens next."
          : "This backend runs one turn at a time, so a message can only be queued." },
          [b.steerable ? "steerable" : "queue-only"]),
        C.el("span", { class: "chip", title: "Transport", text: b.transport }),
      ]),
      /* The card is where an unavailable backend explains itself. It used to
         say "not on PATH" for everything, which is simply wrong for a provider
         with no binary — it sent people off to install something when the real
         problem was an unset key or a server that was not running. */
      b.installed || !b.unavailable_reason ? null
        : C.el("div", { class: "pick-why", text: b.unavailable_reason }),
      b.notes ? C.el("div", { class: "pick-why muted", text: b.notes }) : null,
    ]);
  }

  /* The lane tabs — the fork itself.

     They stay visible after a lane is chosen, which is what lets the choice be
     REMEMBERED without the split becoming invisible: the tab is pre-selected,
     not skipped. A modal "which kind?" gate would have had to trade one
     against the other. */
  function laneTabs() {
    var wrap = C.el("div", { class: "lane-tabs", role: "tablist",
                             "aria-label": "Kind of agent" });
    LANES.forEach(function (l) {
      var rows = laneRows(l.id);
      var ready = rows.filter(function (b) { return b.installed; }).length;
      var on = st.lane === l.id;
      wrap.appendChild(C.el("button", {
        class: "lane-tab" + (on ? " on" : ""),
        role: "tab", "aria-selected": String(on),
        // A lane with nothing in it is disabled rather than hidden: "this
        // console can run models directly" is worth knowing even before you
        // have configured a provider for it.
        disabled: rows.length ? null : true,
        title: rows.length ? l.blurb
          : "No " + l.label.toLowerCase() + " is configured in agents.toml.",
        onclick: function () { setLane(l.id); },
      }, [
        C.el("span", { class: "lane-top" }, [
          C.icon(l.icon),
          C.el("b", { text: l.label }),
          C.el("span", { class: "lane-count muted", text:
            rows.length ? ready + " of " + rows.length + " available" : "none configured" }),
        ]),
        C.el("span", { class: "lane-blurb", text: l.blurb }),
      ]));
    });
    return wrap;
  }

  function backendCards() {
    var rows = laneRows(st.lane);
    if (!rows.length) {
      return C.el("div", { class: "muted", style: "padding:6px 0",
        text: "Add a [[backend]] row to console/config/agents.toml." });
    }
    var cards = C.el("div", { class: "pick", role: "radiogroup",
                              "aria-label": lane().label });
    rows.forEach(function (b) { cards.appendChild(backendCard(b)); });
    return cards;
  }

  /* What a console agent has instead of permission modes.

     These are the limits the loop will actually enforce, reported by the
     server as effective values — so a row that sets nothing reads the same as
     one that sets the default explicitly, and the browser never has to know
     what the default is. A CLI backend reports `budgets: null`, because its
     loop belongs to someone else and inventing a number we do not enforce
     would be a lie this panel then displays. */
  function budgetRow(b) {
    if (!b || !b.budgets) return null;
    var gated = (b.gated_tools || []).length;
    return C.el("div", { class: "budgets" }, [
      C.icon("sliders"),
      C.el("span", { class: "muted", text: (b.modes[0] || {}).blurb ||
        "writes and shell ask you; reads do not" }),
      C.el("span", { class: "grow" }),
      C.el("span", { class: "chip", title:
        "Tool calls allowed in one turn before the loop stops itself and says so.",
        text: b.budgets.tool_rounds + " rounds" }),
      C.el("span", { class: "chip", title:
        "Messages kept before the oldest are dropped. The system prompt is never dropped.",
        text: b.budgets.history_messages + " messages" }),
      gated ? C.el("span", { class: "chip warn", title:
        (b.gated_tools || []).join(", "), text: gated + " gated" }) : null,
      b.is_local ? C.el("span", { class: "chip ok", title:
        "Runs on this machine — no token cost.", text: "free" }) : null,
    ]);
  }

  function newChatForm() {
    // The remembered lane may name a kind this workspace no longer configures
    // (a provider row removed, a CLI uninstalled), so fall back to one that
    // has rows rather than opening on an empty tab.
    if (!laneRows(st.lane).length) {
      var filled = LANES.filter(function (l) { return laneRows(l.id).length; })[0];
      if (filled) st.lane = filled.id;
    }
    if (!st.form.backend || !backend(st.form.backend) ||
        !!backend(st.form.backend).is_api !== lane().api) {
      setLane(st.lane, false);
    }
    var b = backend(st.form.backend);

    var prompt = C.el("textarea", {
      placeholder: "What should the agent do?   / skill   @ agent   # file",
      "aria-label": "Opening message", rows: "6",
      oninput: function (e) { st.form.prompt = e.target.value; syncStart(); },
    });
    prompt.value = st.form.prompt;
    prompt.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); startChat(); }
    });
    // The wrapper is what the menu positions against; the textarea itself
    // cannot hold an absolutely-positioned child.
    var promptWrap = C.el("div", { class: "cpick-anchor" }, [prompt]);
    Pick.attach(prompt, {
      catalog: st.catalog, mount: promptWrap,
      onChange: function (v) { st.form.prompt = v; syncStart(); },
    });

    var micWrap = C.el("div", { class: "row", style: "margin-bottom:10px" }, [
      Voice.micButton(function (committed, interim) {
        prompt.value = (st.form.prompt + " " + committed + " " + interim).replace(/\s+/g, " ").trim();
        syncStart();
      }),
      C.el("span", { class: "muted", text: Voice.support().dictation
        ? "Dictate — audio goes to your browser's speech service"
        : Voice.support().dictationWhy }),
    ]);

    return C.el("div", { class: "ap-form" }, [
      st.pendingTicket
        ? C.el("div", { class: "chip accent", style: "margin-bottom:10px" },
            [C.icon("columns"), "from ticket " + st.pendingTicket])
        : null,
      laneTabs(),
      C.el("div", { style: "margin-bottom:12px" }, [
        backendCards(),
        st.hiddenBackends
          ? C.el("div", { class: "muted", style: "margin-top:5px",
              text: st.hiddenBackends + " backend hidden by your Settings." })
          : null,
      ]),
      modeRow(),
      budgetRow(b),
      /* The reason comes from the backend, because "not on PATH" is wrong for
         an API backend that has no binary at all — its problem is a missing
         key, and telling someone to install something would send them off to
         fix the wrong thing. */
      b && !b.installed ? C.el("div", { class: "errbox", style: "margin-bottom:10px",
        text: (b.unavailable_reason ||
               (b.label + " is not on PATH (command: " + b.command + ")")) +
              " Fix that or pick another backend." }) : null,
      /* Persona and Skill used to be two <select>s here. They are gone: for a
         CLI backend the selection was prepended to the message as literally
         the same token you can now type (`@builder /plan go`), so it was a
         second route to one thing — and the two could collide, sending
         "/plan /plan" when you used both. One input method, one meaning.

         The whole-chat scope they carried is kept, not dropped: whatever the
         OPENING message names becomes the chat's skill and persona, which is
         what an API backend needs (it injects the text into the system prompt
         for every turn, something a per-message token cannot do). */
      C.el("div", { class: "fieldrow", style: "margin-bottom:10px" }, [modelField()]),
      ticketField(),
      field("Opening message",
            "type / for a skill, @ for an agent, # for a file", promptWrap),
      C.el("div", { class: "ct-refs", id: "agRefs" }),
      micWrap,
      C.el("div", { class: "row", style: "flex-wrap:wrap" }, [
        C.el("button", { class: "btn primary", id: "agStart", disabled: true, onclick: startChat },
          [C.icon("play"), "Start chat"]),
        C.el("span", { class: "muted", text: "Runs at the workspace root." }),
      ]),
    ]);
  }

  /* What this message will actually resolve to, shown before it is sent.

     The same rule the wire uses: a token counts only if it names something
     real. Without this the only way to discover that `/pln` is a typo — and
     will travel as prose rather than loading a skill — is to send it and read
     a reply that ignored it. Unresolved tokens are named too, because silence
     about them is what made the typo invisible in the first place. */
  var REF_RE = /(?:^|\s)([/@#])([A-Za-z0-9][A-Za-z0-9._\-/\\]*)/g;
  var REF_KINDS = { "/": "skill", "@": "persona", "#": "path" };

  function scanRefs(text) {
    var known = {
      skill: st.catalog.skills || [],
      persona: st.catalog.personas || [],
      path: st.catalog.paths || [],
    };
    var found = [], unknown = [], m;
    REF_RE.lastIndex = 0;
    while ((m = REF_RE.exec(text || "")) !== null) {
      var kind = REF_KINDS[m[1]];
      if (known[kind].indexOf(m[2]) !== -1) found.push({ kind: kind, raw: m[1] + m[2] });
      else unknown.push(m[1] + m[2]);
    }
    return { found: found, unknown: unknown };
  }

  function paintRefs(host, text, opening) {
    if (!host) return;
    C.clear(host);
    var r = scanRefs(text);
    if (!r.found.length && !r.unknown.length) return;
    if (r.found.length) {
      host.appendChild(C.el("span", { text: "sending with" }));
      // In the OPENING message the first skill and agent set the whole chat —
      // that is the scope the dropdowns used to carry, and it is worth saying
      // out loud, because the same token in a later message applies to that
      // message alone.
      var claimed = {};
      r.found.forEach(function (f) {
        var sets = opening && (f.kind === "skill" || f.kind === "persona") &&
                   !claimed[f.kind];
        if (sets) claimed[f.kind] = true;
        host.appendChild(C.el("span", {
          class: "ct-ref ref-" + f.kind + (sets ? " ct-ref-sets" : ""),
          title: sets ? "Sets this chat's " + (f.kind === "skill" ? "skill" : "agent")
                        + " for every turn, not just this message." : "",
          text: f.raw,
        }));
      });
      if (Object.keys(claimed).length) {
        host.appendChild(C.el("span", { class: "muted", text: "· for the whole chat" }));
      }
    }
    if (r.unknown.length) {
      // Named, not corrected. It may well be prose — "and/or", an issue
      // number — and rewriting someone's words would be worse than saying
      // plainly that this one will travel as text.
      host.appendChild(C.el("span", { class: "muted", title:
        "No skill, agent or file by that name, so it is sent as plain text.",
        text: (r.found.length ? "· " : "") + r.unknown.join(" ") + " as text" }));
    }
  }

  function syncStart() {
    var btn = document.getElementById("agStart");
    if (btn) btn.disabled = !st.form.prompt.trim();
    paintRefs(document.getElementById("agRefs"), st.form.prompt, true);
  }

  function startChat() {
    if (!st.form.prompt.trim()) return;
    var btn = document.getElementById("agStart");
    if (btn) btn.disabled = true;
    /* The opening message defines the chat, so the first skill and agent it
       names become the session's — the scope the two dropdowns used to carry.
       This matters for a console agent, where `prompt_build` injects the text
       into the system prompt for every turn; a token alone would apply to the
       first message only. The server drops the duplicate, so naming it here
       and in the text does not send it twice. */
    var refs = scanRefs(st.form.prompt);
    var first = function (kind) {
      var hit = refs.found.filter(function (f) { return f.kind === kind; })[0];
      return hit ? hit.raw.slice(1) : "";
    };
    C.post("/api/agents/chats", {
      backend: st.form.backend,
      prompt: st.form.prompt,
      mode: st.form.mode,
      model: st.form.model,
      skill: first("skill"),
      persona: first("persona"),
      ticket: st.form.ticket,
    }).then(function (snap) {
      st.form.prompt = "";
      refreshChats();
      openChat(snap.id);
      if (window.ConsoleApp) window.ConsoleApp.refreshBadges();
    }).catch(function (err) {
      C.toast(err.message, "err");
      if (btn) btn.disabled = false;
    });
  }

  /* ---------------- chat view ---------------- */
  function detachStore() {
    if (st.offMeta) { st.offMeta(); st.offMeta = null; }
    if (st.view) { st.view.destroy(); st.view = null; }
    if (st.store) { st.store.destroy(); st.store = null; }
    // Dropped with the panes it paints: an in-flight catalogue fetch resolving
    // after a chat switch would otherwise repaint nodes that are gone.
    st.repaintChat = null;
  }

  function openChat(id) {
    detachStore();
    st.sel = id;
    st.mode = "chat";
    paintRail();
    showMain(true);
    paintMain();
  }

  function newChat() {
    detachStore();
    st.mode = "new";
    st.sel = null;
    paintRail();
    showMain(true);
    paintMain();
    emitTray("");
  }

  /* Narrow-window pane swap: opening a chat shows it, Back returns to the
     list. Deliberately does nothing on a wide window, where both panes are
     visible and folding the list is a separate, deliberate choice — and never
     writes the preference, because swapping panes is navigation, not a
     setting you meant to keep. */
  function showMain(on) {
    if (!NARROW()) return;
    st.listShown = !on;
    applyShell();
  }

  function backBtn() {
    return C.el("button", {
      class: "btn sm pane-back", "aria-label": "Back to chats", title: "Back to chats",
      onclick: function () { showMain(false); },
    }, [C.icon("chevLeft")]);
  }

  function paintMain() {
    var head = document.getElementById("agHead");
    var body = document.getElementById("agBody");
    if (!head || !body) return;

    if (st.mode === "new") {
      C.clear(head);
      C.append(head, [backBtn(), C.el("h3", { text: "New chat" })]);
      body.className = "ap-body";
      C.clear(body).appendChild(newChatForm());
      syncStart();
      return;
    }
    if (!st.sel) {
      C.clear(head);
      C.append(head, [backBtn(), C.el("h3", { text: "Chat" })]);
      body.className = "ap-body";
      C.clear(body).appendChild(C.empty("No chat selected", "Pick one, or start a New chat.", "list"));
      return;
    }
    mountChat(st.sel);
  }

  function mountChat(id) {
    var head = C.clear(document.getElementById("agHead"));
    var body = document.getElementById("agBody");
    body.className = "ap-chat";
    C.clear(body);

    var scroll = C.el("div", { class: "ct-scroll", id: "ctScroll" });
    var rail = C.el("aside", { class: "ct-rail", id: "ctRail" });
    var composer = C.el("div", { class: "ct-composer", id: "ctComposer" });
    body.appendChild(C.el("div", { class: "ct-split" }, [scroll, rail]));
    body.appendChild(composer);

    var store = Store.create(id);
    st.store = store;
    // The same catalog the picker offers, so a reference highlighted in the
    // transcript is one the server also recognised.
    var view = Render.mount(scroll, store, { catalog: st.catalog });
    st.view = view;

    st.repaintChat = function () {
      if (st.store !== store) return;   // a later chat owns the panes now
      paintHead(head, store);
      paintRail2(rail, store);
      paintComposer(composer, store);
    };
    st.offMeta = store.on("meta", st.repaintChat);

    // Auto read-aloud, if the user asked for it: speak each finished reply.
    // Never during history replay — reopening a chat must not re-read it.
    store.on("patch", function (item) {
      if (store.state.replaying) return;
      if (!Voice.prefs().autoRead) return;
      if (item.kind === "text" && item.open === false && !item._spoken) {
        item._spoken = true;
        Voice.speak(item.text);
      }
    });

    // Announcements — the moments worth looking up from other work: the turn
    // ended (agent is waiting), or a tool call is parked on your permission.
    // With read-aloud on, the "done" line is skipped — the reply itself was
    // just read. Approval is announced regardless: a blocked run should not
    // sit silent.
    store.on("item", function (item) {
      if (store.state.replaying || item.role !== "system") return;
      var p = Voice.prefs();
      if (!p.announce) return;
      if (item.kind === "turnend" && !p.autoRead) {
        Voice.speak(item.is_error ? "The agent stopped with an error." : "The agent is done.");
      } else if (item.kind === "approval" && !(item.approval || {}).decided) {
        Voice.speak("Permission needed for " + ((item.approval || {}).tool || "a tool"));
      }
    });

    C.clear(scroll).appendChild(C.skeleton(5));
    store.load().then(function () {
      view.renderAll();
      loadCatalog((store.state.snapshot || store.state.meta || {}).agent || "");
      st.repaintChat();
      store.subscribe();
    }).catch(function (err) {
      C.clear(scroll).appendChild(C.errbox(err));
    });
  }

  /* Which gate is in force, carried for the life of the chat.

     This is the session's blast radius — whether a write is stopped by this
     console's approval card or by somebody else's permission model — and it
     used to be visible only while you were picking, then gone the moment you
     pressed Start. Two chats that look otherwise identical can differ here.

     Silent for a chat whose backend is no longer configured: guessing the kind
     from a name we can't resolve would be exactly the wrong place to guess. */
  function kindChip(backendId) {
    var b = backendId ? backend(backendId) : null;
    if (!b) return null;
    return b.is_api
      ? C.el("span", { class: "chip accent", title:
          "This console runs the loop. Its own verbs are the tools, and " +
          "gated ones stop at the approval card in this chat." },
          [C.icon("cpu"), "console-gated"])
      : C.el("span", { class: "chip", title:
          "The CLI runs its own loop with its own tools. The console watches " +
          "and records; the permission model is the CLI's." },
          [C.icon("wrench"), "cli-gated"]);
  }

  function modelChip(id) {
    if (!id) return null;
    // The trailing segment is the distinguishing part — `openai/gpt-4o-mini`
    // and `openai/gpt-4o` differ at the end, never at the vendor prefix.
    var short = id.length > 26 ? "…" + id.slice(-25) : id;
    return C.el("span", { class: "chip mono", title: id, text: short });
  }

  /* Free, but only on evidence.

     A provider-hosted `:free` model genuinely costs nothing, and the fetched
     catalogue says so — both prices are 0. Reading that is the difference
     between "free" and "unpriced", and the console refuses to print the first
     without proof, because a wrong "free" is the one error nobody checks. */
  function priceOf(backendId, modelId) {
    var cat = st.catalogs[backendId];
    var rows = (cat && cat.models) || [];
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].id === modelId) return rows[i];
    }
    return null;
  }

  function isFree(backendId, modelId) {
    var b = backend(backendId);
    if (b && b.is_local) return true;   // runs on this machine
    var m = priceOf(backendId, modelId);
    return !!m && m.input_per_mtok === 0 && m.output_per_mtok === 0;
  }

  function paintHead(head, store) {
    var s = store.state;
    var meta = s.snapshot || s.meta || {};
    C.clear(head);
    C.append(head, [
      backBtn(),
      C.el("h3", { class: "truncate", text: meta.title || "Chat" }),
      s.busy ? C.el("span", { class: "chip info running" }, [C.icon("play"), "working"])
             : C.el("span", { class: "chip" + (s.alive ? " ok" : "") }, [s.alive ? "live" : "ended"]),
      kindChip(meta.agent),
      meta.agent ? C.chip(meta.agent) : null,
      // Same rule as the composer: a mode is worth a chip only where there
      // was a choice. Every console agent declares `modes = ["default"]`, so
      // this chip said "default" and meant nothing.
      meta.mode && (backend(meta.agent) || {modes: []}).modes.length > 1
        ? C.chip(meta.mode) : null,
      // A model id runs to `nvidia/nemotron-3.5-lightning:free` and was taking
      // half the bar. Truncated in place, whole thing on hover.
      modelChip(s.model || meta.model),
      s.usage.cost ? C.chip("$" + s.usage.cost.toFixed(4)) : null,
      s.usage.turns ? C.chip(s.usage.turns + " turns") : null,
      C.el("span", { class: "grow" }),
      s.busy ? C.el("button", { class: "btn sm danger", title: "Stop the turn in flight",
        onclick: function () {
          C.post("/api/agents/chats/" + encodeURIComponent(s.id) + "/interrupt", {})
            .catch(function (e) { C.toast(e.message, "err"); });
        } }, [C.icon("stop"), "Interrupt"]) : null,
      s.alive ? C.el("button", { class: "btn sm", title: "End this session",
        onclick: function () {
          C.post("/api/agents/chats/" + encodeURIComponent(s.id) + "/stop", {})
            .then(function () { C.toast("Session ended", "ok"); refreshChats(); })
            .catch(function (e) { C.toast(e.message, "err"); });
        } }, ["End"]) : null,
      C.el("button", { class: "btn sm iconly", "aria-label": "Delete chat", title: "Delete chat and transcript",
        onclick: function () {
          C.post("/api/agents/chats/" + encodeURIComponent(s.id) + "/delete", {})
            .then(function () { C.toast("Deleted", "ok"); detachStore(); refreshChats(); newChat(); })
            .catch(function (e) { C.toast(e.message, "err"); });
        } }, [C.icon("trash")]),
    ]);
    emitTray(meta.agent);
  }

  /* Budget pressure, for a chat whose loop this console is running.

     The old rail offered Plan / Todos / Files to every chat and, when a
     console agent produced none of them — it never will; those come from
     claude's own stream — fell through to "the agent's plan, todos and touched
     files appear here". Three things that were never coming.

     `tool.start` carries `round` and `max_rounds` for this transport, so the
     cap is shown while the turn is still running rather than only in the
     notice that fires once it has been hit. */
  function budgetPanel(store) {
    var s = store.state;
    var meta = s.snapshot || {};
    var budgets = meta.budgets;
    if (!budgets) return null;

    var used = s.toolRound || 0;
    var rounds = budgets.tool_rounds || 0;
    var pct = rounds ? Math.min(100, Math.round((used / rounds) * 100)) : 0;
    var b = backend(meta.agent);

    function meter(label, value, fill, tone) {
      return [
        C.el("div", { class: "ct-meter" }, [
          C.el("span", { text: label }),
          C.el("b", { text: value }),
        ]),
        C.el("div", { class: "ct-gauge" + (tone ? " " + tone : "") },
          [C.el("i", { style: "width:" + fill + "%" })]),
      ];
    }

    var kids = meter("Tool rounds", used + " of " + rounds, pct,
                     pct >= 80 ? "warn" : "");
    kids.push(C.el("div", { class: "ct-meter" }, [
      C.el("span", { text: "History kept" }),
      C.el("b", { text: String(budgets.history_messages) }),
    ]));
    var model = s.model || meta.model || "";
    var free = isFree(meta.agent, model);
    kids.push(C.el("div", { class: "ct-meter" }, [
      C.el("span", { text: "Spend" }),
      // "free" only where something says so — a local runtime, or a catalogue
      // row priced at zero. Otherwise "unpriced", which means we do not know,
      // and must never be rendered as $0.00.
      C.el("b", { text: free ? "free"
        : (s.usage.cost ? "$" + s.usage.cost.toFixed(4) : "unpriced") }),
    ]));
    if (free) {
      kids.push(C.el("div", { class: "muted", text: b && b.is_local
        ? "Runs on this machine."
        : "This model is priced at zero in the provider's catalogue." }));
    }
    return C.el("section", { class: "ct-panel" },
      [C.el("h4", { text: "Console budget" })].concat(kids));
  }

  function paintRail2(rail, store) {
    var s = store.state;
    C.clear(rail);

    var budget = budgetPanel(store);
    if (budget) rail.appendChild(budget);

    if (s.plan) {
      rail.appendChild(C.el("section", { class: "ct-panel" }, [
        C.el("h4", { text: "Plan" }),
        C.el("div", { class: "ct-planbody" }, [window.ConsoleMarkdown.render(s.plan)]),
      ]));
    }

    if (s.todos.length) {
      var list = C.el("div", { class: "ct-todos" });
      s.todos.forEach(function (t) {
        var status = t.status || "pending";
        list.appendChild(C.el("div", { class: "ct-todo " + status }, [
          C.icon(status === "completed" ? "check" : status === "in_progress" ? "play" : "circle"),
          C.el("span", { text: t.content || t.activeForm || "" }),
        ]));
      });
      rail.appendChild(C.el("section", { class: "ct-panel" }, [
        C.el("h4", { text: "Todos" }), list,
      ]));
    }

    if (s.files.length) {
      var fl = C.el("div", { class: "rows" });
      s.files.slice(-40).forEach(function (f) {
        fl.appendChild(C.el("div", { class: "lrow" }, [
          C.el("span", { class: "chip " + (f.verb === "write" ? "warn" : ""), text: f.verb }),
          C.el("span", { class: "ltext truncate", title: f.path, text: f.path }),
        ]));
      });
      rail.appendChild(C.el("section", { class: "ct-panel" }, [
        C.el("h4", { text: "Files touched (" + s.files.length + ")" }), fl,
      ]));
    }

    if (s.queued.length) {
      var q = C.el("div", { class: "rows" });
      s.queued.forEach(function (item) {
        q.appendChild(C.el("div", { class: "lrow" }, [
          C.icon("queue"),
          C.el("span", { class: "ltext truncate", text: item.text }),
          C.el("button", { class: "btn sm iconly", "aria-label": "Remove from queue", title: "Remove",
            onclick: function () {
              C.post("/api/agents/chats/" + encodeURIComponent(s.id) + "/queue/" +
                     encodeURIComponent(item.id) + "/remove", {})
                .catch(function (e) { C.toast(e.message, "err"); });
            } }, [C.icon("x")]),
        ]));
      });
      rail.appendChild(C.el("section", { class: "ct-panel" }, [
        C.el("h4", { text: "Queued (" + s.queued.length + ")" }), q,
      ]));
    }

    if (!rail.childNodes.length) {
      /* Named per kind, because the old line promised a console agent three
         things it can never produce: plan, todos and the file list all come
         out of claude's own stream. Promising them to a transport that has no
         such events reads as "nothing happened yet" forever. */
      var b = backend((s.snapshot || {}).agent);
      rail.appendChild(C.el("div", { class: "muted", style: "padding:4px",
        text: b && b.is_api
          ? "Tool calls and budget appear here once the agent starts working."
          : "The agent's plan, todos and touched files appear here." }));
    }
  }

  function paintComposer(composer, store) {
    var s = store.state;
    /* Captured BEFORE the clear, which is the whole point: afterwards the old
       textarea is out of the document and `activeElement` has fallen back to
       <body>, so asking then always answers "no". */
    var live = document.activeElement;
    var hadFocus = !!live && live.classList &&
                   live.classList.contains("ct-input");
    var caret = hadFocus ? live.selectionStart : null;
    C.clear(composer);

    if (!s.alive) {
      composer.appendChild(C.el("div", { class: "ct-dead" }, [
        C.icon("info"),
        C.el("span", { text: "This session has ended. Its transcript is read-only — start a new chat to continue." }),
        C.el("button", { class: "btn sm", onclick: newChat }, [C.icon("play"), "New chat"]),
      ]));
      return;
    }

    var meta = s.snapshot || {};
    var steerable = meta.steerable !== false;

    var ta = C.el("textarea", {
      class: "ct-input", rows: "2",
      placeholder: s.busy
        ? (steerable ? "Steer the run in flight…  (Enter to send)" : "Queue a follow-up…  (Enter to send)")
        : "Reply…   / skill   @ agent   # file",
      "aria-label": "Message",
    });
    /* Restore the half-typed message.

       This whole composer is rebuilt on every `meta` event, and `meta` fires
       on usage, todos, plan, queue changes, turn start/end and now each tool
       round — that is, constantly, and precisely while a turn is running,
       which is exactly when you are typing a steer or a follow-up. Every one
       of those repaints used to hand back an empty box, so the message you
       were part-way through vanished mid-keystroke.

       Held per chat so switching away and back does not paste one chat's
       draft into another. */
    var draft = st.drafts[s.id] || "";
    if (draft) ta.value = draft;
    ta.addEventListener("input", function () { st.drafts[s.id] = ta.value; });
    ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); fire(); }
    });

    function fire() {
      var text = ta.value.trim();
      if (!text) return;
      /* The server's "auto" deliberately QUEUES a message sent mid-turn —
         silently steering a run someone thought they were replying to would
         be a surprising default, so it makes the UI ask. This button is that
         asking: while a turn is in flight and the transport can steer, the
         label says "Steer" and so must the request. Sending "auto" here would
         quietly queue while the button promised otherwise. */
      var mode;
      if (st.sendMode === "queue") mode = "queue";
      else if (s.busy && steerable) mode = "steer";
      else mode = "auto";
      ta.disabled = true;
      C.post("/api/agents/chats/" + encodeURIComponent(s.id) + "/send", { text: text, mode: mode })
        .then(function (r) {
          ta.value = "";
          // Sent, so the draft is spent — otherwise the next repaint would
          // restore the message that has just gone.
          delete st.drafts[s.id];
          paintRefs(refs, "");
          ta.disabled = false;
          ta.focus();
          if (r.result === "queued") C.toast("Queued for the next turn", "ok");
        })
        .catch(function (err) { C.toast(err.message, "err"); ta.disabled = false; });
    }

    var sendLabel = s.busy ? (st.sendMode === "queue" ? "Queue" : (steerable ? "Steer" : "Queue")) : "Send";
    var sendIcon = s.busy ? (st.sendMode === "queue" ? "queue" : (steerable ? "steer" : "queue")) : "send";

    var toggle = C.el("div", { class: "seg" }, [
      C.el("button", {
        "aria-pressed": String(st.sendMode === "auto"),
        title: steerable ? "Send now — steers a running turn" : "Send now (queues while busy)",
        onclick: function () { st.sendMode = "auto"; paintComposer(composer, store); },
      }, [steerable ? "now" : "send"]),
      C.el("button", {
        "aria-pressed": String(st.sendMode === "queue"),
        title: "Hold until the current turn ends",
        onclick: function () { st.sendMode = "queue"; paintComposer(composer, store); },
      }, ["queue"]),
    ]);

    composer.appendChild(C.el("div", { class: "ct-bar" }, [
      toggle,
      Voice.micButton(function (committed, interim) {
        ta.value = (committed + " " + interim).replace(/\s+/g, " ").trim();
      }),
      Voice.speakButton(function () { return st.view ? st.view.lastAssistantText() : ""; }),
      C.el("label", { class: "ct-autoread", title: "Speak each reply as it finishes" }, [
        (function () {
          var cb = C.el("input", { type: "checkbox" });
          cb.checked = !!Voice.prefs().autoRead;
          cb.addEventListener("change", function () {
            Voice.setPrefs({ autoRead: cb.checked });
            if (!cb.checked) Voice.stopSpeaking();
            emitTray();
          });
          return cb;
        })(),
        C.el("span", { text: "read aloud" }),
      ]),
      C.el("label", { class: "ct-autoread",
        title: "Say when the agent finishes a turn or needs permission" }, [
        (function () {
          var cb = C.el("input", { type: "checkbox" });
          cb.checked = !!Voice.prefs().announce;
          cb.addEventListener("change", function () {
            Voice.setPrefs({ announce: cb.checked });
          });
          return cb;
        })(),
        C.el("span", { text: "announce" }),
      ]),
      C.el("span", { class: "grow" }),
      s.busy ? C.el("span", { class: "chip info running", text: "turn in flight" }) : null,
      !steerable ? C.el("span", { class: "chip", title:
        "This backend runs one process per turn, so a message can only be queued." }, ["queue-only"]) : null,
    ]));
    /* The picker attaches to the LIVE composer too, which is the point of the
       whole change: skill and persona used to be choosable only at the moment
       a chat was started, and `agent_manager.send` resolved nothing for a
       message typed afterwards. */
    var taWrap = C.el("div", { class: "cpick-anchor grow" }, [ta]);
    Pick.attach(ta, { catalog: st.catalog, mount: taWrap });

    composer.appendChild(C.el("div", { class: "ct-inputrow" }, [
      taWrap,
      C.el("button", { class: "btn primary ct-go", onclick: fire, title: sendLabel },
        [C.icon(sendIcon), C.el("span", { class: "blab", text: sendLabel })]),
    ]));

    // Same judgement as the New-chat form, live on every keystroke. It has to
    // be here too: since `agent_manager.send` started resolving tokens, a
    // reference typed mid-conversation is as real as one typed at the start.
    var refs = C.el("div", { class: "ct-refs" });
    composer.appendChild(refs);
    ta.addEventListener("input", function () { paintRefs(refs, ta.value); });
    paintRefs(refs, ta.value);

    /* Put the caret back where the repaint took it from. Restoring the text
       without the caret still interrupts typing — the cursor jumps to the
       start and the next character lands in the wrong place. */
    if (hadFocus) {
      ta.focus();
      var at = caret === null ? ta.value.length : Math.min(caret, ta.value.length);
      ta.setSelectionRange(at, at);
    }
  }

  /* ---------------- render ---------------- */
  function render(host) {
    st.host = host;
    if (C.IS_STATIC) {
      host.appendChild(C.el("div", { style: "padding:24px" }, [
        C.empty("Agents need a live server",
          "This is a read-only snapshot. Run: python console/kanban.py serve", "cpu"),
      ]));
      return;
    }

    C.clear(host).appendChild(C.el("div", { style: "padding:14px" }, [C.skeleton(5)]));

    Promise.all([C.get("/api/agents/backends"), C.get("/api/agents/catalog")])
      .then(function (res) {
        var all = (res[0] || {}).backends || [];
        /* Honour the per-user "don't offer me this CLI" switch from Settings.
           Never filter down to nothing: if the preference would leave the
           picker empty (someone disabled a CLI, then it stopped being
           installed) the list is shown unfiltered rather than presenting a
           composer with no options and no explanation. */
        var off = C.prefs.get("disabledBackends", []);
        var kept = all.filter(function (b) { return off.indexOf(b.id) === -1; });
        st.backends = kept.length ? kept : all;
        st.hiddenBackends = all.length - st.backends.length;
        st.catalog = res[1] || { skills: [], personas: [], tickets: [] };
        // The remembered lane. Validated against what this workspace actually
        // configures by newChatForm(), so a stored id for a kind that no
        // longer has any rows falls back rather than opening on an empty tab.
        st.lane = lane(C.prefs.get("agentLane", "cli")).id;
        C.clear(host);

        if (!st.backends.length) {
          host.appendChild(C.el("div", { style: "padding:14px;max-width:720px" }, [
            C.panel("No backends configured", C.empty("Nothing to launch",
              "Add a [[backend]] row to console/config/agents.toml.", "cpu"),
              null, { icon: "cpu", tone: "warn" }),
          ]));
          return;
        }

        host.appendChild(C.el("div", { class: "appshell", id: "agShell" }, [
          C.el("div", { class: "ap-rail" }, [
            C.el("header", {}, [
              C.el("h3", { text: "Chats" }),
              C.el("span", { class: "chip zero", id: "agLive", text: "0" }),
              C.el("button", { class: "btn sm primary", title: "Start a new chat", onclick: newChat },
                [C.icon("play"), "New"]),
              C.el("button", {
                class: "btn sm iconly", id: "agFold", "aria-label": "Hide the chat list",
                title: "Hide the chat list", "aria-expanded": "true",
                onclick: function () { setListShown(false); },
              }, [C.icon("chevLeft")]),
            ]),
            C.el("div", { class: "ap-items", id: "agChats" }, [C.skeleton(3)]),
          ]),
          C.el("div", { class: "ap-main" }, [
            C.el("header", { id: "agHead" }, []),
            C.el("div", { class: "ap-body", id: "agBody" }, []),
          ]),
          // The only control visible once the list is folded away.
          C.el("button", {
            class: "list-reveal", id: "agReveal", "aria-label": "Show the chat list",
            title: "Show the chat list", "aria-expanded": "false",
            onclick: function () { setListShown(true); },
          }, [C.icon("chevRight")]),
        ]));

        /* Entry, and every crossing of the breakpoint: a narrow window opens
           on the chat rather than the list, a wide one restores your choice. */
        st.listShown = NARROW() ? false : !C.prefs.get("chatListHidden", false);
        applyShell();
        if (st.mql) st.mql.onchange = null;
        st.mql = window.matchMedia("(max-width: 900px)");
        st.mql.onchange = function () {
          st.listShown = NARROW() ? false : !C.prefs.get("chatListHidden", false);
          applyShell();
        };

        refreshChats().then(function () {
          // A handoff wins over "resume the newest chat": someone who just
          // clicked "Start agent" on a ticket is asking for a new one.
          if (st.pending) {
            st.form.prompt = st.pending.prompt || "";
            st.pendingTicket = st.pending.ticket || "";
            st.pending = null;
            newChat();
            return;
          }
          var live = st.chats.filter(function (c) { return c.alive; })[0];
          if (live) openChat(live.id);
          else if (st.chats.length) openChat(st.chats[0].id);
          else newChat();
        });

        // The rail shows the state of other chats too, so it refreshes on a
        // timer even while this one streams. Cheap: one small JSON list.
        if (st.poll) clearInterval(st.poll);
        st.poll = setInterval(refreshChats, 8000);
      })
      .catch(function (err) {
        C.clear(host).appendChild(C.el("div", { style: "padding:14px" }, [C.errbox(err)]));
      });
  }

  function emitTray(backend) {
    if (!window.ConsoleDesktopTray || !ConsoleDesktopTray.emitSession) return;
    var agent = backend;
    if (agent === undefined) {
      agent = "";
      if (st.store && st.store.state) {
        var meta = st.store.state.snapshot || st.store.state.meta || {};
        agent = meta.agent || "";
      }
    }
    ConsoleDesktopTray.emitSession(agent || "");
  }

  function busyChatId() {
    if (st.store && st.store.state && st.store.state.busy && st.sel) return st.sel;
    var list = st.chats || [];
    var hit = list.filter(function (c) { return c.busy; })[0];
    return hit ? hit.id : "";
  }

  function trayInterrupt() {
    if (window.ConsoleApp && ConsoleApp.go) ConsoleApp.go("agents");
    function post(id) {
      if (!id) {
        C.toast("Nothing is running", "warn");
        return;
      }
      C.post("/api/agents/chats/" + encodeURIComponent(id) + "/interrupt", {})
        .catch(function (e) { C.toast(e.message, "err"); });
    }
    var id = busyChatId();
    if (id) { post(id); return; }
    C.get("/api/agents/chats").then(function (d) {
      var hit = (d.chats || []).filter(function (c) { return c.busy; })[0];
      post(hit ? hit.id : "");
    }).catch(function (e) { C.toast(e.message, "err"); });
  }

  /* Called from the native tray via window.eval. Ids match desktop/features.toml. */
  function trayAction(id) {
    if (id === "new_chat") {
      if (window.ConsoleApp && ConsoleApp.go) ConsoleApp.go("agents");
      newChat();
      return;
    }
    if (id === "mute_on" || id === "mute_off") {
      var muted = id === "mute_on";
      Voice.setPrefs({ autoRead: !muted });
      if (muted) Voice.stopSpeaking();
      emitTray();
      if (st.mode === "chat" && st.repaintChat) st.repaintChat();
      return;
    }
    if (id === "interrupt") trayInterrupt();
  }

  /* Handoff from elsewhere in the console (the ticket drawer's "Start
     agent"). Stored rather than acted on immediately: the tab may not be
     mounted yet, and render() picks it up when it is. One-shot — cleared on
     use so returning to the tab later doesn't resurrect an old prompt. */
  window.ConsoleAgents = {
    compose: function (payload) {
      st.pending = payload || null;
    },
    trayAction: trayAction,
  };

  C.tab("agents", {
    layout: "app",
    render: render,
    onLeave: function () {
      detachStore();
      if (st.poll) { clearInterval(st.poll); st.poll = null; }
      Voice.stopDictation();
      Voice.stopSpeaking();
    },
  });
})(window.Console);
