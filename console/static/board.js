/* Board tab — one implementation serving every board kind in the manifest.

   Detail beyond "columns of cards", each earning its keep:
   - lane tone/WIP from config, so Blocked looks blocked and an over-WIP
     column says so (warns, never blocks — a board that refuses a move just
     gets worked around).
   - cards sorted by blocking-items then idle time, so the thing that needs a
     human is at the top of the column rather than wherever it sorted.
   - stale and blocking markers computed server-side (render.py) so the
     static export shows the same flags as the live board.
   - drag to move, with an optimistic re-render and a revert on failure.
   - orphan lane for tickets whose stage no lane declares: surfaced loudly,
     because a silently invisible ticket is the worst failure mode here.
   - search filters in place (app.js routes the query here). */
(function (C) {
  "use strict";

  var st = { kind: null, view: null, query: "", host: null, api: null, dragId: null };

  function laneToneChip(lane) {
    if (lane.over_wip) return C.el("span", { class: "chip warn", text: lane.cards.length + "/" + lane.wip });
    if (lane.wip) return C.el("span", { class: "chip", text: lane.cards.length + "/" + lane.wip });
    return C.el("span", { class: "chip" + (lane.cards.length ? "" : " zero"), text: String(lane.cards.length) });
  }

  function matches(card, q) {
    if (!q) return true;
    q = q.toLowerCase();
    return (card.id + " " + card.title + " " + (card.owner || "") + " " + (card.tags || []).join(" "))
      .toLowerCase().indexOf(q) !== -1;
  }

  /* Priority as an icon, not a word. Four levels read at a glance in a dense
     column, and the arrow direction/count carries the meaning independently
     of colour — a red "critical" chip and an amber "high" chip look the same
     to a lot of people. */
  var PRIORITY = {
    low: { label: "Low", icon: "prioLow", cls: "prio-low" },
    medium: { label: "Medium", icon: "prioMed", cls: "prio-med" },
    high: { label: "High", icon: "prioHigh", cls: "prio-high" },
    critical: { label: "Critical", icon: "prioCrit", cls: "prio-crit" },
  };

  function priorityMeta(p) { return PRIORITY[p] || PRIORITY.medium; }

  function priorityBadge(priority) {
    var m = priorityMeta(priority);
    return C.el("span", { class: "prio " + m.cls, title: m.label + " priority" }, [C.icon(m.icon)]);
  }

  /* External tracker link. `rel="noopener"` because target=_blank without it
     hands the opened page a handle back to this one. The click is stopped so
     it doesn't also open the card drawer underneath. */
  function urlChip(url, label) {
    return C.el("a", {
      class: "chip link", href: url, target: "_blank", rel: "noopener noreferrer",
      title: "Open in the external tracker: " + url,
      onclick: function (e) { e.stopPropagation(); },
    }, [C.icon("external"), label || "tracker"]);
  }

  /* Corner variant: pinned to the card's top-right, icon only.
     A fixed corner has no room for a word, so the accessible name has to be
     carried by aria-label/title rather than by visible text — an icon-only
     link with neither is unusable with a screen reader. Rendered only when a
     url exists; there is no placeholder, so a card without one is simply
     clean rather than showing a dead affordance. */
  function urlCorner(url) {
    return C.el("a", {
      class: "cardlink", href: url, target: "_blank", rel: "noopener noreferrer",
      title: "Open in the external tracker: " + url,
      "aria-label": "Open this ticket in the external tracker",
      onclick: function (e) { e.stopPropagation(); },
      // Keyboard users tab to this link; Enter must follow it, not also
      // trigger the card's own Enter handler behind it.
      onkeydown: function (e) { if (e.key === "Enter" || e.key === " ") e.stopPropagation(); },
    }, [C.icon("external")]);
  }

  function cardNode(card) {
    var cls = "card";
    if (card.priority === "high" || card.priority === "critical") cls += " prio-" + card.priority;

    var foot = C.el("div", { class: "cfoot" });
    foot.appendChild(priorityBadge(card.priority));
    if (card.blocking) {
      foot.appendChild(C.el("span", {
        class: "chip danger", title: card.blocking + " critical open item(s)",
      }, [C.icon("alert"), String(card.blocking)]));
    }
    Object.keys(card.trackers || {}).forEach(function (k) {
      var n = card.trackers[k];
      if (!n) return;
      foot.appendChild(C.el("span", { class: "chip", title: n + " open " + k }, [k[0].toUpperCase() + n]));
    });
    if (card.has_scripts) foot.appendChild(C.el("span", { class: "chip", title: "Has ticket-scripts/" }, [C.icon("file")]));
    if (card.stale) {
      foot.appendChild(C.el("span", { class: "chip warn", title: "No update in " + card.idle_days + " days" },
        [C.icon("clock"), C.fmtAgo(card.idle_days)]));
    }
    if (card.owner) foot.appendChild(C.el("span", { class: "chip", title: "Owner" }, [C.icon("user"), card.owner]));

    var node = C.el("article", {
      class: cls, tabindex: "0", role: "button", draggable: "true",
      "data-id": card.id,
      "aria-label": card.id + ": " + card.title,
      onclick: function () { openTicket(card.id); },
      onkeydown: function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openTicket(card.id); } },
      ondragstart: function (e) {
        st.dragId = card.id;
        e.dataTransfer.setData("text/plain", card.id);
        e.dataTransfer.effectAllowed = "move";
      },
      ondragend: function () { st.dragId = null; },
    }, [
      card.url ? urlCorner(card.url) : null,
      C.el("div", { class: "cid" + (card.url ? " has-link" : ""), text: card.id }),
      C.el("div", { class: "ctitle" + (card.url ? " has-link" : ""), text: card.title }),
      foot.childNodes.length ? foot : null,
    ]);
    return node;
  }

  function laneNode(lane) {
    var cards = lane.cards.filter(function (c) { return matches(c, st.query); });
    var body = C.el("div", { class: "lanebody" });
    if (!cards.length) {
      body.appendChild(C.el("div", { class: "muted", style: "padding:6px 3px", text: st.query ? "No match" : "—" }));
    }
    cards.forEach(function (c) { body.appendChild(cardNode(c)); });

    var head = C.el("header", {}, [
      C.el("h3", { text: lane.label }),
      laneToneChip(lane),
    ]);
    if (lane.tone) head.querySelector("h3").style.color = "var(--" + lane.tone + ")";

    var node = C.el("div", {
      class: "lane", "data-lane": lane.id,
      ondragover: function (e) {
        if (!st.dragId) return;
        e.preventDefault();
        node.classList.add("over");
      },
      ondragleave: function () { node.classList.remove("over"); },
      ondrop: function (e) {
        e.preventDefault();
        node.classList.remove("over");
        var id = st.dragId || e.dataTransfer.getData("text/plain");
        if (id) moveTicket(id, lane.id);
      },
    }, [head, body]);
    return node;
  }

  function moveTicket(id, stage) {
    if (C.IS_STATIC) { C.toast("Static export is read-only.", "err"); return; }
    var from = null;
    st.view.lanes.forEach(function (l) {
      l.cards.forEach(function (c) { if (c.id === id) from = l.id; });
    });
    if (from === stage) return;
    C.post("/api/ticket/" + encodeURIComponent(id) + "/move", { stage: stage })
      .then(function () {
        C.toast(id + " → " + stage, "ok");
        reload();
        if (st.api) st.api.refreshBadges();
      })
      .catch(function (err) { C.toast(err.message, "err"); });
  }

  function render(host, api) {
    st.host = host;
    st.api = api;
    st.kind = api.tab.kind;
    reload();
  }

  function reload() {
    var host = st.host;
    C.load(host, C.get("/api/board/" + st.kind), function (view) {
      st.view = view;
      paint();
    }, { skeletonRows: 3, skeletonKind: "card" });
  }

  function paint() {
    var host = C.clear(st.host);
    var view = st.view;

    var shell = C.el("div", { class: "boardshell" });
    host.appendChild(shell);

    var bar = C.el("div", { class: "boardbar" }, [
      C.el("span", { class: "muted", text: view.blurb || "" }),
      C.el("span", { class: "grow" }),
      C.el("span", { class: "chip accent", title: "Open (non-terminal lanes)" }, [view.open_total + " open"]),
      C.el("span", { class: "chip", title: "Every card on this board" }, [view.total + " total"]),
      st.query ? C.el("span", { class: "chip info" }, ["filter: " + st.query]) : null,
    ]);
    shell.appendChild(bar);

    var lanes = C.el("div", { class: "lanes" });
    view.lanes.forEach(function (l) { lanes.appendChild(laneNode(l)); });

    if (view.orphans && view.orphans.length) {
      var body = C.el("div", { class: "lanebody" });
      view.orphans.forEach(function (c) {
        var n = cardNode(c);
        n.appendChild(C.el("div", { class: "chip danger", text: "stage: " + c.unknown_stage }));
        body.appendChild(n);
      });
      lanes.appendChild(C.el("div", { class: "lane", style: "border-color:var(--danger-line)" }, [
        C.el("header", {}, [
          C.el("h3", { text: "Unknown stage", style: "color:var(--danger)" }),
          C.el("span", { class: "chip danger", text: String(view.orphans.length) }),
        ]),
        body,
      ]));
    }
    shell.appendChild(lanes);

    if (!view.total) {
      C.clear(host).appendChild(C.el("div", { style: "padding:24px 14px" }, [
        C.empty(
          "No " + view.label.toLowerCase() + " yet",
          "Create one with:  python console/kanban.py ticket create ID --title \"…\" --kind " + st.kind,
          "columns"
        ),
      ]));
    }
  }

  /* ---------------- ticket drawer ---------------- */
  /* ---------------- ticket drawer ----------------
     Compact by design: this is a side panel, not a page. Every field that
     can be changed is changed in place — the previous version could only
     move a ticket between lanes, so editing an owner or a priority meant
     leaving for the CLI. Writes go through one patch call so changing two
     fields stamps `updated` once instead of twice. */
  function openTicket(id) {
    var body = window.ConsoleApp.drawer.open(id, "");
    C.load(body, C.get("/api/ticket/" + encodeURIComponent(id)), function (t) {
      paintTicket(body, t);
    });
  }

  function patchTicket(t, fields, done) {
    C.post("/api/ticket/" + encodeURIComponent(t.id) + "/patch", fields)
      .then(function () {
        C.toast("Saved", "ok");
        reload();
        if (st.api) st.api.refreshBadges();
        if (done) done();
      })
      .catch(function (e) { C.toast(e.message, "err"); });
  }

  /* An editable line: label, value, and a control that only commits on blur
     or Enter. Committing per keystroke would write the file on every letter. */
  function editRow(label, value, onCommit, opts) {
    opts = opts || {};
    var input = C.el("input", {
      type: "text", value: value || "", placeholder: opts.placeholder || "",
      "aria-label": label,
    });
    var commit = function () {
      var next = input.value.trim();
      if (next === (value || "").trim()) return;   // nothing changed
      onCommit(next);
    };
    input.addEventListener("blur", commit);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
      if (e.key === "Escape") { input.value = value || ""; input.blur(); }
    });
    return C.el("div", { class: "dfield" }, [
      C.el("span", { class: "dlabel", text: label }),
      input,
    ]);
  }

  function selectRow(label, value, options, onCommit) {
    return C.el("div", { class: "dfield" }, [
      C.el("span", { class: "dlabel", text: label }),
      C.el("select", {
        "aria-label": label,
        onchange: function (e) { onCommit(e.target.value); },
      }, options.map(function (o) {
        return C.el("option", { value: o[0], selected: o[0] === value || null }, [o[1]]);
      })),
    ]);
  }

  function paintTicket(body, t) {
    var pm = priorityMeta(t.priority);

    /* -- header strip: identity + the things you glance at -- */
    body.appendChild(C.el("div", { class: "drow" }, [
      C.el("span", { class: "chip accent", text: t.stage }),
      C.el("span", { class: "chip", title: "Priority" }, [priorityBadge(t.priority), pm.label]),
      C.el("span", { class: "chip", text: t.status }),
      t.owner ? C.el("span", { class: "chip" }, [C.icon("user"), t.owner]) : null,
      t.idle_days !== null && t.idle_days !== undefined
        ? C.el("span", { class: "chip", title: "Last updated" }, [C.icon("clock"), C.fmtAgo(t.idle_days)]) : null,
      t.url ? urlChip(t.url, "tracker") : null,
    ]));

    /* -- actions -- */
    if (!C.IS_STATIC) {
      body.appendChild(C.el("div", { class: "drow dactions" }, [
        C.el("button", {
          class: "btn sm primary", title: "Open the Agents tab with this ticket's context",
          onclick: function () { startAgentFor(t); },
        }, [C.icon("cpu"), "Start agent"]),
        C.el("button", {
          class: "btn sm", title: "Copy this ticket's id",
          onclick: function () {
            if (navigator.clipboard) {
              navigator.clipboard.writeText(t.id).then(
                function () { C.toast("Copied " + t.id, "ok"); },
                function () { C.toast("Clipboard blocked by the browser", "err"); });
            } else { C.toast("Clipboard unavailable", "err"); }
          },
        }, ["Copy id"]),
      ]));
    }

    /* -- stage -- */
    if (!C.IS_STATIC && t.lanes && t.lanes.length) {
      var seg = C.el("div", { class: "seg dseg" });
      t.lanes.forEach(function (l) {
        seg.appendChild(C.el("button", {
          "aria-pressed": String(l.id === t.stage),
          title: "Move to " + l.label,
          onclick: function () {
            C.post("/api/ticket/" + encodeURIComponent(t.id) + "/move", { stage: l.id })
              .then(function () {
                C.toast(t.id + " → " + l.id, "ok");
                window.ConsoleApp.drawer.close();
                reload();
                if (st.api) st.api.refreshBadges();
              })
              .catch(function (e) { C.toast(e.message, "err"); });
          },
        }, [l.label]));
      });
      body.appendChild(dsection("Stage", seg));
    }

    /* -- details, all editable in place -- */
    if (!C.IS_STATIC) {
      var fields = C.el("div", { class: "dfields" }, [
        editRow("Title", t.title, function (v) { patchTicket(t, { title: v }, function () { openTicket(t.id); }); }),
        editRow("Owner", t.owner, function (v) { patchTicket(t, { owner: v }); }, { placeholder: "unassigned" }),
        selectRow("Priority", t.priority,
          ["low", "medium", "high", "critical"].map(function (p) { return [p, p]; }),
          function (v) { patchTicket(t, { priority: v }, function () { openTicket(t.id); }); }),
        selectRow("Status", t.status,
          ["active", "blocked", "completed", "archived"].map(function (s) { return [s, s]; }),
          function (v) { patchTicket(t, { status: v }, function () { openTicket(t.id); }); }),
        editRow("Tracker URL", t.url, function (v) { patchTicket(t, { url: v }, function () { openTicket(t.id); }); },
          { placeholder: "https://…" }),
      ]);
      body.appendChild(dsection("Details", fields));
    }

    /* -- trackers -- */
    Object.keys(t.trackers || {}).forEach(function (kind) {
      var items = t.trackers[kind];
      var openN = items.filter(function (i) {
        return ["resolved", "closed", "verified", "done", "dropped"].indexOf(i.status) === -1;
      }).length;

      var rows = C.el("div", { class: "drows" });
      if (!items.length) rows.appendChild(C.el("div", { class: "muted", text: "None yet." }));
      items.forEach(function (it) {
        var isOpen = ["resolved", "closed", "verified", "done", "dropped"].indexOf(it.status) === -1;
        var sev = it.priority || it.severity || "";
        rows.appendChild(C.el("div", { class: "drow-item" }, [
          C.el("span", { class: "chip" + (isOpen ? "" : " ok"), text: it.id }),
          C.el("span", { class: "ltext", text: it.text }),
          sev && sev !== "medium"
            ? C.chip(sev, sev === "critical" || sev === "high" ? "danger" : null) : null,
          C.el("span", { class: "chip" + (isOpen ? " warn" : " ok"), text: it.status }),
        ]));
      });

      var addRow = null;
      if (!C.IS_STATIC) {
        var input = C.el("input", {
          type: "text", placeholder: "Add " + kind.replace(/s$/, "") + "…",
          "aria-label": "Add " + kind,
        });
        var send = function () {
          var text = input.value.trim();
          if (!text) return;
          input.disabled = true;
          C.post("/api/ticket/" + encodeURIComponent(t.id) + "/trackers/" + kind, { text: text })
            .then(function () { C.toast("Added to " + kind, "ok"); openTicket(t.id); reload(); })
            .catch(function (e) { C.toast(e.message, "err"); input.disabled = false; });
        };
        input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
        addRow = C.el("div", { class: "daddrow" }, [
          input, C.el("button", { class: "btn sm", onclick: send }, ["Add"]),
        ]);
      }

      body.appendChild(dsection(
        kind, [rows, addRow],
        C.el("span", { class: "chip" + (openN ? " warn" : " zero"), text: openN + " open" })
      ));
    });

    /* -- artifacts: the markdown is still where the substance lives -- */
    var art = t.artifacts || { files: [] };
    var fileRows = C.el("div", { class: "drows" });
    if (!art.files.length) fileRows.appendChild(C.el("div", { class: "muted", text: "No markdown artifacts." }));
    art.files.forEach(function (f) {
      fileRows.appendChild(C.el("div", { class: "drow-item" }, [
        C.icon("file"),
        C.el("span", { class: "ltext", text: f.artifact }),
        C.el("span", { class: "muted", text: (f.size / 1024).toFixed(1) + " KB" }),
      ]));
    });
    if (art.scripts_dir) {
      fileRows.appendChild(C.el("div", { class: "drow-item" }, [
        C.icon("folder"),
        C.el("span", { class: "ltext", text: "ticket-scripts/" }),
        C.chip(art.scripts_dir.count + " files"),
      ]));
    }
    body.appendChild(dsection("Artifacts", fileRows));
  }

  /* A drawer section: a label line and its content. Deliberately not a
     `.panel` — a bordered card per tracker turned the drawer into a stack of
     boxes inside a box, which is where most of its wasted height came from. */
  function dsection(title, kids, extra) {
    var head = C.el("div", { class: "dhead" }, [
      C.el("span", { class: "dtitle", text: title }),
      C.el("span", { class: "dhair" }),
      extra || null,
    ]);
    return C.el("section", { class: "dsection" }, [head].concat(Array.isArray(kids) ? kids : [kids]));
  }

  /* Hand the ticket to the Agents tab. The prompt names the ticket and its
     artifact folder rather than pasting its contents — the agent can read the
     files, and a prompt stuffed with a whole ticket is both expensive and
     stale the moment anything changes. */
  function startAgentFor(t) {
    var prompt = "Work on ticket " + t.id + ": " + t.title + "\n\n" +
      "Its artifacts are in knowledge-center/artifacts/" + t.id + "/. " +
      "Read them first, then propose what to do next.";
    if (window.ConsoleAgents && window.ConsoleAgents.compose) {
      window.ConsoleAgents.compose({ prompt: prompt, ticket: t.id });
      window.ConsoleApp.drawer.close();
      if (st.api) st.api.go("agents");
    } else {
      C.toast("The Agents tab is not available in this build.", "err");
    }
  }

  C.tab("board", {
    // Full remaining height, so the lane strip's horizontal scrollbar sits on
    // the bottom edge rather than floating mid-window.
    layout: "app",
    render: render,
    onSearch: function (q) { st.query = q; if (st.view) paint(); },
    onLeave: function () { st.query = ""; },
  });
})(window.Console);
