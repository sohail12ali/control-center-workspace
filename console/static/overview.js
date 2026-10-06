/* Overview tab — the landing dashboard.

   Two rules this tab is built on:
   1. Every number is clickable through to the board that produced it. A stat
      you can't drill into is decoration.
   2. Everything flows through ONE `.grid`, so panels form columns and each
      keeps its own height. Full-width stacked slabs were the old layout's
      problem: on a wide monitor you got three 1200px-wide bands of mostly
      empty space, and the stat row stretched so thin it stopped reading as a
      group. */
(function (C) {
  "use strict";

  function attnGroup(rows, label, badgeFn, api) {
    if (!rows.length) return null;
    var box = C.el("div", { class: "rows" });
    rows.forEach(function (r) {
      box.appendChild(C.el("div", {
        class: "lrow clickable",
        onclick: function () {
          if (r.href === "agents") api.go("agents");
          else api.go("board:" + r.kind);
        },
        title: r.href === "agents" ? "Open Agents" : "Open the " + r.kind + " board",
      }, [
        badgeFn(r),
        C.el("span", { class: "ltext" }, [
          C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: r.id + " " + (r.ref ? r.ref + " " : "") }),
          r.title,
        ]),
        C.el("span", { class: "chip", text: r.stage }),
      ]));
    });
    return C.el("div", {}, [C.el("h4", { text: label }), box]);
  }

  function ofType(rows, type) {
    return (rows || []).filter(function (r) { return r.type === type; });
  }

  /* Needs you is capped; the rows beyond the cap are one click away on the
     board, with the exact number said out loud. Navigates only. */
  function moreRow(n, api) {
    return C.el("div", { class: "rows" }, [C.el("div", {
      class: "lrow clickable", title: "Open the Tickets board",
      onclick: function () { api.go("board:tickets"); },
    }, [
      C.el("span", { class: "ltext", text: "and " + n + " more" }),
      C.el("span", { class: "chip" }, [C.icon("chevRight")]),
    ])]);
  }

  /* j/k/arrows move the highlighted row, Enter opens it. One function for both
     attention panels so they cannot drift apart. */
  function rowNav(panel) {
    panel.tabIndex = 0;
    panel.addEventListener("keydown", function (e) {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      /* The header is a fold control (Enter toggles it); it must fold without
         also opening the highlighted row. A folded panel has no rows to open. */
      if (e.target && e.target.closest && e.target.closest("header")) return;
      /* A button (the Refresh button in the as-of row) keeps its own Enter: it
         must act, not open the highlighted row. */
      if (e.target && ((e.target.tagName === "BUTTON") || (e.target.closest && e.target.closest(".fresh-row")))) return;
      if (panel.classList.contains("collapsed")) return;
      var rows = panel.querySelectorAll(".lrow");
      if (!rows.length) return;
      var idx = 0;
      rows.forEach(function (r, i) { if (r.classList.contains("kbd")) idx = i; });
      if (e.key === "j" || e.key === "ArrowDown") idx = Math.min(rows.length - 1, idx + 1);
      else if (e.key === "k" || e.key === "ArrowUp") idx = Math.max(0, idx - 1);
      else if (e.key === "Enter") { rows[idx].click(); e.preventDefault(); return; }
      else return;
      rows.forEach(function (r, i) { r.classList.toggle("kbd", i === idx); });
      if (rows[idx].scrollIntoView) rows[idx].scrollIntoView({ block: "nearest" });
      e.preventDefault();
    });
  }

  /* ---------------- onboarding ----------------
     A card, dismissible, shown until the steps are done. It is the first
     thing on Overview because the person who most needs it is the one who
     has never opened Settings — and the last step (requirements) is real
     work, not setup, so the card stays useful well past first run. */
  var STATUS_TONE = { ok: "ok", todo: "warn", warn: "warn", fail: "danger" };

  function onboardingCard(api, onDismiss) {
    var host = C.el("div", { class: "span2" });
    C.get("/api/onboarding").then(function (r) {
      if (C.prefs.get("hideOnboarding", false) && !r.steps.some(function (s) { return s.status === "fail"; })) {
        return;                       // dismissed, and nothing is broken
      }
      var open = C.prefs.get("onboardingOpen", true);

      var list = C.el("div", { class: "steps" });
      r.steps.forEach(function (s) {
        var tone = STATUS_TONE[s.status] || "";
        var body = [];
        if (s.hint) {
          body.push(C.el("code", { class: "stephint", text: s.hint }));
        }
        if (s.chain && s.status !== "ok") {
          body.push(C.el("div", { class: "stepchain" },
            s.chain.map(function (skill, i) {
              return C.el("span", {}, [
                i ? C.el("span", { class: "chev", text: "›" }) : null,
                C.el("code", { text: "/" + skill }),
              ]);
            })));
        }
        var jump = s.jump && s.jump.tab
          ? C.el("button", { class: "btn sm", onclick: function () { api.go(s.jump.tab); } },
              ["Open", C.icon("chevRight")])
          : null;

        list.appendChild(C.el("div", { class: "step " + s.status }, [
          C.el("span", { class: "stepdot " + tone, title: s.status },
            [C.icon(s.status === "ok" ? "check" : s.status === "fail" ? "alert" : "circle")]),
          C.el("div", { class: "stepbody" }, [
            C.el("div", { class: "steprow" }, [
              C.el("b", { text: s.title }),
              C.el("span", { class: "muted", text: s.detail }),
            ]),
            body.length ? C.el("div", { class: "stepextra" }, body) : null,
          ]),
          jump,
        ]));
      });

      var toggle = C.el("button", {
        class: "btn sm",
        onclick: function () {
          open = !open;
          C.prefs.set("onboardingOpen", open);
          syncToggle();
        },
      }, []);
      function syncToggle() {
        // Label and state together — flipping one without the other left the
        // button saying "Hide steps" over a hidden list.
        list.classList.toggle("hidden", !open);
        toggle.textContent = open ? "Hide steps" : "Show steps";
        toggle.setAttribute("aria-expanded", String(open));
      }
      syncToggle();

      var dismiss = C.el("button", {
        class: "btn sm iconly", "aria-label": "Dismiss setup", title: "Dismiss — reachable again from Settings",
        onclick: function () { C.prefs.set("hideOnboarding", true); if (onDismiss) onDismiss(); },
      }, [C.icon("x")]);

      host.appendChild(C.panel(
        r.complete ? "Setup complete" : "Getting started",
        [
          C.el("p", { class: "muted", style: "margin:0" }, [
            r.complete
              ? "Every step is done. Dismiss this card — Settings can bring it back."
              : "Work down to Product requirements; the steps above it are setup, that one is the actual work.",
          ]),
          list,
        ],
        C.el("div", { class: "row" }, [
          C.el("span", { class: "chip" + (r.complete ? " ok" : " warn"),
            text: r.done + "/" + r.total }),
          C.el("button", {
            class: "btn sm", type: "button",
            onclick: function () {
              if (window.ConsoleOnboarding) window.ConsoleOnboarding.open();
            },
          }, ["Open setup"]),
          toggle, dismiss,
        ]),
        { icon: r.complete ? "check" : "info", tone: r.complete ? "ok" : "warn" }
      ));
    }).catch(function () { /* onboarding plugin off — Overview still works */ });
    return host;
  }

  /* ---------------- operations ----------------
     Jobs and schedules live here rather than on a tab of their own: what is
     running and what will run are exactly the "state of the work" questions
     this dashboard already answers, and a tab you must navigate to is a tab
     you check after it mattered.

     Both panels REMOVE THEMSELVES when there is nothing to say. A workspace
     using neither should not pay for them with two permanently empty boxes on
     its landing page — the empty state is a panel that is not there. */

  var JOB_TONE = {
    running: "accent", queued: "warn", done: "ok",
    error: "danger", interrupted: "warn", cancelled: null,
  };
  var ACTIVE_STATES = { queued: 1, running: 1 };

  function jobRow(job, api, reload) {
    var cancel = job.state === "queued"
      ? C.el("button", {
          class: "btn sm", title: "Cancel this queued job",
          onclick: function (e) {
            e.stopPropagation();
            C.post("/api/jobs/" + encodeURIComponent(job.id) + "/cancel", {})
              .then(function () { C.toast("Cancelled " + job.verb, "ok"); reload(); })
              .catch(function (err) { C.toast(err.message, "err"); });
          },
        }, [C.icon("x")])
      : null;

    return C.el("div", { class: "lrow" }, [
      C.el("span", { class: "chip " + (JOB_TONE[job.state] || ""), text: job.state }),
      C.el("span", { class: "ltext" }, [
        C.el("b", { text: job.verb }),
        job.ticket ? C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: " " + job.ticket }) : null,
      ]),
      /* Why it failed matters more than that it failed, and the row is the
         only place a person will look. */
      job.error ? C.el("span", { class: "muted", title: job.error, text: String(job.error).slice(0, 40) }) : null,
      C.el("span", { class: "muted mono", style: "font-size:11px", text: (job.submitted || "").slice(11, 16) }),
      cancel,
    ]);
  }

  /* A repaint builds fresh hosts for Jobs and Scheduled. The new host takes
     over the old host's panel first, so a refetch that fails leaves the rows
     and their old as-of time on screen instead of dropping the panel. */
  var lastHost = {};
  function opsHost(name) {
    var host = C.el("div"), prev = lastHost[name];
    while (prev && prev.firstChild) host.appendChild(prev.firstChild);
    lastHost[name] = host;
    return host;
  }

  function jobsPanel(api, onRefresh) {
    var host = opsHost("jobs");
    function load() {
      C.get("/api/jobs").then(function (d) {
        var fetchedAt = Date.now();
        C.clear(host);
        var jobs = (d && d.jobs) || [];
        if (!jobs.length) return;              // never used here — say nothing
        var active = jobs.filter(function (j) { return ACTIVE_STATES[j.state]; });
        /* Active first, then a short tail of finished work: a job that ended
           three days ago is history, and history is what `kanban job list`
           is for. */
        var shown = active.concat(
          jobs.filter(function (j) { return !ACTIVE_STATES[j.state]; }).slice(0, 5));
        var rows = C.el("div", { class: "rows" });
        shown.forEach(function (j) { rows.appendChild(jobRow(j, api, load)); });
        host.appendChild(C.panel("Jobs", rows,
          C.el("span", { class: "chip" + (active.length ? " accent" : " zero"),
                         text: active.length ? active.length + " active" : "idle" }),
          { icon: "queue", tone: active.length ? "info" : null, collapse: { id: "ov.jobs", open: true },
            fresh: { asOf: fetchedAt, onRefresh: onRefresh } }));
      }).catch(function () { /* verbs plugin off, or a static export */ });
    }
    load();
    return host;
  }

  function schedulesPanel(onRefresh) {
    var host = opsHost("schedules");
    C.get("/api/schedules").then(function (d) {
      var fetchedAt = Date.now();
      C.clear(host);
      var rows = (d && d.schedules) || [];
      if (!rows.length && !(d && d.error)) return;
      var box = C.el("div", { class: "rows" });

      if (d.error) {
        /* A cron expression that failed to parse is a config error the owner
           has to see. Blanking the panel would hide it until the day the job
           did not run. */
        box.appendChild(C.el("div", { class: "lrow" }, [
          C.el("span", { class: "chip danger" }, [C.icon("alert"), "config"]),
          C.el("span", { class: "ltext", text: d.error }),
        ]));
      }

      rows.forEach(function (s) {
        box.appendChild(C.el("div", { class: "lrow" }, [
          C.el("span", { class: "chip " + (s.enabled ? "ok" : "zero"),
                         text: s.enabled ? "on" : "off" }),
          C.el("span", { class: "ltext" }, [
            C.el("b", { text: s.label || s.id }),
            C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: " " + s.verb }),
          ]),
          C.el("code", { class: "mono", style: "font-size:11px", text: s.expr }),
          C.el("span", { class: "muted", text: s.next_run || "—" }),
        ]));
      });

      var on = (d.enabled_count || 0);
      /* The caveat is the panel's most important line. Next-run times read as
         a promise, and this deployment only keeps that promise while `serve`
         is running — there is no daemon. Saying so here is the difference
         between a schedule that quietly never fires and one you knew about. */
      box.appendChild(C.el("p", { class: "muted", style: "margin:8px 0 0;font-size:11px",
        text: on
          ? "The running console is the clock — these fire only while the server is up. Missed runs are skipped, never replayed."
          : "All schedules are parked. Nothing will fire." }));

      host.appendChild(C.panel("Scheduled", box,
        C.el("span", { class: "chip" + (on ? " ok" : " zero"),
                       text: on ? on + " on" : "parked" }),
        { icon: "clock", collapse: { id: "ov.schedules", open: true },
          fresh: { asOf: fetchedAt, onRefresh: onRefresh } }));
    }).catch(function () { /* ops plugin off, or a static export */ });
    return host;
  }

  /* Refresh = fetch first, repaint only on success. It must not go through
     C.load, which blanks the page on an error: a failed refresh keeps the rows
     and the old as-of time, so the panels age into STALE instead of vanishing. */
  function refresh(host, api) {
    return C.get("/api/overview").then(function (d) {
      C.clear(host);
      paint(host, d, api);
    }, function (err) {
      C.toast("Could not refresh: " + (err && err.message ? err.message : err), "err");
    });
  }

  function paint(host, d, api) {
    var grid = C.el("div", { class: "grid" });
    /* The server's generated_at is the as-of time of every panel fed by
       /api/overview. No Refresh button in a static export. */
    var fresh = { asOf: d.generated_at, onRefresh: C.IS_STATIC ? null : function () { refresh(host, api); } };
    host.appendChild(C.splitter.foldBar(host));
    grid.appendChild(onboardingCard(api, function () { render(host, api); }));
    var a = d.attention;

    /* -- at a glance: one panel, tight tile grid -- */
    grid.appendChild(C.panel("At a glance", C.stats([
      C.stat(d.stats.open, "Open", { tone: "accent", onClick: function () { api.go("board:tickets"); } }),
      C.stat(a.counts.blocked, "Blocked", {
        tone: a.counts.blocked ? "danger" : null, sub: "critical items",
      }),
      C.stat(a.counts.stale, "Stale", {
        tone: a.counts.stale ? "warn" : null, sub: d.stale_days + "d+ idle",
      }),
      C.stat(d.stats.tracker_open, "Items", { sub: "Q + B + T" }),
      C.stat(d.stats.done, "Done", { tone: "ok" }),
    ]), null, { icon: "layout", collapse: { id: "ov.glance", open: true }, fresh: fresh }));

    /* -- needs you: only a person can clear these; above needs repair -- */
    var counts = a.counts;
    var youRows = a.needs_you || [];
    var youKids = [
      attnGroup(ofType(youRows, "approval"), "Approvals", function () {
        return C.el("span", { class: "chip danger" }, [C.icon("alert"), "!"]);
      }, api),
      attnGroup(ofType(youRows, "question"), "Questions waiting", function () {
        return C.el("span", { class: "chip warn" }, [C.icon("info"), "?"]);
      }, api),
      counts.needs_you > youRows.length ? moreRow(counts.needs_you - youRows.length, api) : null,
    ].filter(Boolean);
    var needsPanel = C.panel(
        "Needs you",
        youKids.length ? youKids
                       : C.empty("Nothing is waiting on you", "No open questions or approvals.", "check"),
        C.el("span", { class: "chip" + (counts.needs_you ? " warn" : " zero"), text: String(counts.needs_you) }),
        { icon: "user", tone: counts.needs_you ? "warn" : null, collapse: { id: "ov.needsyou", open: true }, fresh: fresh }
      );
    rowNav(needsPanel);
    grid.appendChild(C.el("div", { class: "span2" }, [needsPanel]));

    /* -- needs repair: the widest panel, since its rows are sentences -- */
    var fixRows = a.needs_repair || [];
    var attnKids = [
      attnGroup(ofType(fixRows, "blocked"), "Blocked by a critical item", function (r) {
        return C.el("span", { class: "chip danger" }, [C.icon("alert"), String(r.blocking)]);
      }, api),
      attnGroup(ofType(fixRows, "stale"), "Stale (" + d.stale_days + "+ days)", function (r) {
        return C.el("span", { class: "chip warn" }, [C.icon("clock"), C.fmtAgo(r.idle_days)]);
      }, api),
      attnGroup(ofType(fixRows, "unowned"), "Nobody owns these", function () {
        return C.el("span", { class: "chip" }, [C.icon("user"), "—"]);
      }, api),
      attnGroup(ofType(fixRows, "answered"), "Answers not yet applied", function () {
        return C.el("span", { class: "chip warn" }, [C.icon("info"), "answered, not applied"]);
      }, api),
      attnGroup(ofType(fixRows, "run"), "Runs that need a look", function (r) {
        return C.el("span", { class: "chip danger", text: r.stage });
      }, api),
    ].filter(Boolean);
    var attnPanel = C.panel(
        "Needs repair",
        attnKids.length ? attnKids
                        : C.empty("Nothing needs repair",
                                  "No blocked, stale or unowned work, answers waiting to be applied, or failed runs.", "check"),
        C.el("span", { class: "chip" + (counts.needs_repair ? " warn" : " zero"), text: String(counts.needs_repair) }),
        { icon: "alert", tone: counts.needs_repair ? "warn" : null, collapse: { id: "ov.attention", open: true }, fresh: fresh }
      );
    rowNav(attnPanel);
    grid.appendChild(C.el("div", { class: "span2" }, [attnPanel]));

    /* -- flow, one row per board -- */
    var flowKids = [];
    Object.keys(d.flow).forEach(function (kind) {
      flowKids.push(C.el("div", {}, [
        C.el("div", { class: "row", style: "margin-bottom:5px" }, [
          C.el("h4", { text: kind, style: "margin:0" }),
          C.el("span", { class: "grow" }),
          C.el("button", {
            class: "btn sm", onclick: function () { api.go("board:" + kind); },
          }, ["Board", C.icon("chevRight")]),
        ]),
        C.stack(d.flow[kind].map(function (l) { return { label: l.label, count: l.count }; })),
      ]));
    });
    grid.appendChild(C.panel("Flow", flowKids, null,
      { icon: "columns", tone: "info", collapse: { id: "ov.flow", open: true }, fresh: fresh }));

    /* -- recent -- */
    var recent = C.el("div", { class: "rows" });
    if (!d.recent.length) {
      recent.appendChild(C.empty("Nothing yet", "Create a ticket to see it here.", "inbox"));
    }
    d.recent.forEach(function (r) {
      recent.appendChild(C.el("div", {
        class: "lrow clickable",
        onclick: function () { api.go("board:" + r.kind); },
      }, [
        C.el("span", { class: "chip", text: r.kind === "tickets" ? "T" : r.kind[0].toUpperCase() }),
        C.el("span", { class: "ltext" }, [
          C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: r.id + " " }),
          r.title,
        ]),
        r.owner ? C.el("span", { class: "chip" }, [r.owner]) : null,
        C.el("span", { class: "muted", text: r.updated }),
      ]));
    });
    grid.appendChild(C.panel("Recently touched", recent, null,
      { icon: "clock", collapse: { id: "ov.recent", open: true }, fresh: fresh }));

    grid.appendChild(jobsPanel(api, fresh.onRefresh));
    grid.appendChild(schedulesPanel(fresh.onRefresh));

    host.appendChild(grid);
  }

  function render(host, api) {
    C.load(host, C.get("/api/overview"), function (d) { paint(host, d, api); },
      { skeletonRows: 5 });
  }

  C.tab("overview", { render: render });
})(window.Console);
