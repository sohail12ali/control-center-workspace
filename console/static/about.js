/* About tab — orientation, not reference. The reference lives in
   console/README.md and .claude/skills/console/SKILL.md, and duplicating it
   here would guarantee two versions of it.

   Everything board-shaped on this page is read from the live config as it
   renders: lane names, lane counts, terminal lanes, which tabs exist. A fork
   that renames a lane, adds a board, or disables a plugin gets a correct
   About page without editing this file — which is the whole reason the
   diagrams are built rather than written. */
(function (C) {
  "use strict";

  var SECTIONS = [
    ["ab-start", "Start here"],
    ["ab-boards", "Boards and lanes"],
    ["ab-tabs", "Tabs in this build"],
    ["ab-agents", "Agents"],
    ["ab-keys", "Keyboard"],
  ];

  /* What each tab is for. Keyed by manifest id and only rendered for tabs
     this deployment actually loaded, so a disabled plugin doesn't leave a
     paragraph describing a tab that isn't there. */
  var BLURBS = {
    overview: "What needs a human right now — blocked, stale and unowned work, plus lane flow and what changed recently.",
    agents: "Launch a configured CLI as a one-shot headless run and watch its output.",
    work: "Read-only timesheet over the per-author daily logs that /log-work writes.",
    analytics: "Pipeline shape, ageing, throughput and hours. Every chart has a table twin.",
    todos: "Every open todo across every ticket, plus general ones, in one filterable list.",
    vault: "Wikilink graph and read-only file browser over knowledge-center/.",
    about: "This page.",
    settings: "Theme and per-tab visibility, stored in this browser only.",
  };

  /* Section spacing lives in CSS (`.prose section`), not here — an inline
     margin per section meant the rhythm couldn't respond to the breakpoints. */
  function sect(id, title, kids) {
    return C.el("section", { id: id },
      [C.el("h3", { text: title })].concat(Array.isArray(kids) ? kids : [kids]));
  }

  function toc() {
    return C.el("nav", { class: "toc", "aria-label": "On this page" }, SECTIONS.map(function (s) {
      return C.el("button", {
        class: "btn sm", type: "button",
        onclick: function () {
          var el = document.getElementById(s[0]);
          // scrollIntoView rather than an href="#…": the router owns the hash,
          // and a section anchor in it would be read as a tab id.
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        },
      }, [s[1]]);
    }));
  }

  function startHere() {
    var steps = [
      ["Find the work", "Each board is one kind of work with its own lifecycle. Press 1–9 to switch tabs, / to search."],
      ["Move it", "Drag a card between lanes, or open it and use the stage buttons. Every move writes to that ticket's ticket.toml — there is no database, so the CLI and the board cannot disagree."],
      ["Log what shipped", "One line via /log-work. The Work tab totals it; hours are computed, never hand-entered."],
    ];
    return sect("ab-start", "Start here", [
      C.el("div", { class: "ab-steps" }, steps.map(function (s, i) {
        return C.el("div", { class: "ab-step" }, [
          C.el("span", { class: "num", text: String(i + 1) }),
          C.el("b", { text: s[0] }),
          C.el("p", { text: s[1] }),
        ]);
      })),
    ]);
  }

  function laneFlow(view) {
    var flow = C.el("div", { class: "flowline" });
    view.lanes.forEach(function (lane, i) {
      if (i) flow.appendChild(C.el("span", { class: "farrow" }, ["→"]));
      var box = C.el("span", {
        class: "fbox" + (lane.terminal ? " done" : ""),
        title: lane.terminal ? "Terminal lane — cards here are out of the pipeline" : lane.id,
      }, [
        lane.label,
        C.el("span", { class: "fn", text: String(lane.cards.length) }),
      ]);
      flow.appendChild(box);
    });
    return flow;
  }

  function boardPanel(view) {
    var terminal = view.lanes.filter(function (l) { return l.terminal; }).map(function (l) { return l.label; });
    return C.panel(view.label, [
      view.blurb ? C.el("p", { class: "muted", style: "margin-bottom:6px", text: view.blurb }) : null,
      laneFlow(view),
      C.el("div", { class: "muted" }, [
        view.lanes.length + " lanes, " + view.total + " cards (" + view.open_total + " open). ",
        terminal.length ? "Terminal: " + terminal.join(", ") + ". " : "No terminal lane declared. ",
        "Numbers are live.",
      ]),
      view.orphans && view.orphans.length
        ? C.el("div", { class: "errbox", style: "margin-top:8px",
            text: view.orphans.length + " card(s) sit in a stage no lane declares — the board shows them in an "
              + "\"Unknown stage\" column rather than hiding them." })
        : null,
    ], C.el("span", { class: "chip mono", text: view.kind }));
  }

  function boardsSect(cfg, host) {
    var body = C.el("div", {});
    var s = sect("ab-boards", "Boards and lanes", [
      C.el("p", {}, [
        "A board is one kind of work with its own lifecycle. They do not share stages, because a ticket in ",
        C.el("i", {}, ["verify"]), " and an investigation in ", C.el("i", {}, ["triage"]),
        " are not the same state. Every card is a projection of files under ",
        C.el("code", {}, ["knowledge-center/artifacts/"]), " — the lane names below are read from ",
        C.el("code", {}, ["console/config/boards/*.toml"]), " as this page renders, not copied into it.",
      ]),
      body,
    ]);
    host.appendChild(s);

    var boards = (cfg.boards || []);
    if (!boards.length) {
      body.appendChild(C.empty("No boards enabled", "Set general.enabled_boards in console/config/console.toml.", "columns"));
      return;
    }
    var grid = C.el("div", { class: "grid" });
    body.appendChild(grid);
    boards.forEach(function (b) {
      var slot = C.el("div", {}, [C.skeleton(3)]);
      grid.appendChild(slot);
      C.get("/api/board/" + b.kind)
        .then(function (view) { C.clear(slot).appendChild(boardPanel(view)); })
        .catch(function (err) { C.clear(slot).appendChild(C.errbox(err)); });
    });
  }

  function tabsSect(cfg, api) {
    var tabs = (cfg.tabs || []).filter(function (t) { return t.group !== "boards"; });
    var rows = tabs.map(function (t) {
      return C.el("tr", {}, [
        C.el("td", {}, [
          C.el("button", {
            class: "btn sm", title: "Go to " + t.label,
            onclick: function () { api.go(t.id); },
          }, [t.icon ? C.icon(t.icon) : null, t.label]),
        ]),
        C.el("td", { class: "muted", text: BLURBS[t.id] || "" }),
        C.el("td", {}, [t.needs_live ? C.chip("live only", "warn") : C.chip("in exports", "ok")]),
      ]);
    });

    return sect("ab-tabs", "Tabs in this build", [
      C.el("p", {}, [
        "This list is the server's own manifest, so it shows exactly what this checkout loaded. A tab is missing "
        + "here when its plugin row is ", C.el("code", {}, ["enabled = false"]), " in ",
        C.el("code", {}, ["console/config/plugins.toml"]),
        " — that switch is committed and applies to everyone. The Settings tab's switches are different: they hide "
        + "a tab in your browser only.",
      ]),
      C.IS_STATIC
        ? C.el("p", { class: "muted" }, [
            "This is a snapshot, so tabs marked ", C.el("b", {}, ["live only"]),
            " (Agents, Work, Analytics, Vault) were left out of it — their date pickers, window filters and "
            + "per-path readers would have one frozen answer for every question.",
          ])
        : null,
      C.el("div", { class: "tablewrap" }, [
        C.el("table", { class: "dt" }, [
          C.el("thead", {}, [C.el("tr", {}, [
            C.el("th", { text: "Tab" }), C.el("th", { text: "What it shows" }), C.el("th", { text: "Static export" }),
          ])]),
          C.el("tbody", {}, rows),
        ]),
      ]),
      C.el("p", { class: "muted", style: "margin-top:8px" }, [
        "Migrations and Releases boards ship as config (disabled by default); Projects and Files tabs are "
        + "intentionally not built in this template.",
      ]),
    ]);
  }

  function agentsSect(cfg, api) {
    var has = (cfg.tabs || []).some(function (t) { return t.id === "agents"; });
    if (!has) {
      // Two very different reasons the tab can be absent, and saying the
      // wrong one is worse than saying nothing: a snapshot simply cannot
      // host a process, whereas a disabled plugin means the route is gone
      // for everyone on the checkout.
      return sect("ab-agents", "Agents", [
        C.el("p", { class: "muted" }, C.IS_STATIC
          ? ["Agents need a live server, so the tab is not part of a static snapshot. Run ",
             C.el("code", {}, ["python console/kanban.py serve"]), " to use it."]
          : ["The agents plugin is disabled in ", C.el("code", {}, ["console/config/plugins.toml"]),
             ", so this build cannot launch processes at all — the launch route does not exist."]),
      ]);
    }
    return sect("ab-agents", "Agents", [
      C.el("p", {}, [
        "The Agents tab runs a configured CLI (", C.el("code", {}, ["claude"]), ", ",
        C.el("code", {}, ["cursor-agent"]), ", or whatever a fork adds under ",
        C.el("code", {}, ["[agents.backends]"]), ") as a headless one-shot subprocess in this checkout, and polls "
        + "its output. Skill and persona pickers are read off disk from ", C.el("code", {}, [".claude/skills/"]),
        " and ", C.el("code", {}, [".claude/agents/"]), ".",
      ]),
      C.el("ul", {}, [
        C.el("li", {}, [C.el("b", {}, ["No live steering."]), " A running job can be watched and stopped, not replied to."]),
        C.el("li", {}, [C.el("b", {}, ["No worktree isolation."]), " Jobs run directly in the target directory."]),
        C.el("li", {}, [C.el("b", {}, ["Approval gate on live chats."]), " Gated tools (", C.el("code", {}, ["gated_tools"]), " in agents.toml) park on a Permission-needed card in the chat until you answer — Allow once, Allow for this chat, or Deny; no answer within the timeout denies fail-closed. One-shot CLI runs (", C.el("code", {}, ["kanban.py agents launch"]), ") have no gate, which is why their default stays ", C.el("code", {}, ["--permission-mode plan"]), "."]),
      ]),
      C.el("button", { class: "btn sm", onclick: function () { api.go("agents"); } }, ["Open the Agents tab"]),
    ]);
  }

  function keysSect() {
    var keys = [
      ["1 – 9", "jump to the nth visible tab"],
      ["/", "focus search"],
      ["r", "reload the current tab"],
      ["← →", "move along the tab strip (when it has focus)"],
      ["Esc", "close the drawer, or clear the search box"],
      ["Ctrl / ⌘ + Enter", "launch the run (Agents tab)"],
    ];
    return sect("ab-keys", "Keyboard", [
      C.el("div", { class: "keys" }, keys.map(function (k) {
        return C.el("div", { class: "keyrow" }, [C.el("kbd", { text: k[0] }), C.el("span", { text: k[1] })]);
      })),
    ]);
  }

  function footer() {
    return C.el("footer", { style: "margin-top:34px;padding-top:14px;border-top:1px solid var(--line)" }, [
      C.el("p", { class: "muted" }, [
        "Every verb here is also a CLI verb — ",
        C.el("code", {}, ["python console/kanban.py move {ID} {stage}"]), ", ",
        C.el("code", {}, ["… overview"]), ", ", C.el("code", {}, ["… todos"]), ", ",
        C.el("code", {}, ["… work day"]), ", ", C.el("code", {}, ["… vault tree"]), ". ",
        "Board reference: ", C.el("code", {}, [".claude/skills/console/SKILL.md"]), ". ",
        "Architecture and how to add a plugin: ", C.el("code", {}, ["console/README.md"]), ".",
      ]),
    ]);
  }

  function render(host, api) {
    var cfg = api.config || {};
    var wrap = C.el("div", { class: "prose" });
    host.appendChild(wrap);

    wrap.appendChild(C.el("h2", { text: cfg.title || "Delivery Console" }));
    wrap.appendChild(C.el("p", {}, [
      "A local board over the tickets and investigations already tracked under ",
      C.el("code", {}, ["knowledge-center/artifacts/"]),
      ", plus supporting tabs that read the same files from different angles. Nothing here is specific to a "
      + "project: boards, lanes, tabs and backends are all config under ",
      C.el("code", {}, ["console/config/"]), ".",
    ]));

    if (C.IS_STATIC) {
      wrap.appendChild(C.el("div", { class: "errbox", style: "border-color:var(--info-line);background:var(--info-soft);color:var(--info)" }, [
        "This is the read-only export. Run ",
        C.el("code", {}, ["python console/kanban.py serve"]),
        " to move cards, edit trackers and run agents.",
      ]));
    }

    wrap.appendChild(toc());
    wrap.appendChild(startHere());
    boardsSect(cfg, wrap);
    wrap.appendChild(tabsSect(cfg, api));
    wrap.appendChild(agentsSect(cfg, api));
    wrap.appendChild(keysSect());
    wrap.appendChild(footer());
  }

  C.tab("about", { render: render });
})(window.Console);
