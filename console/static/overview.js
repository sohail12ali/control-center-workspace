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
        onclick: function () { api.go("board:" + r.kind); },
        title: "Open the " + r.kind + " board",
      }, [
        badgeFn(r),
        C.el("span", { class: "ltext" }, [
          C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: r.id + " " }),
          r.title,
        ]),
        C.el("span", { class: "chip", text: r.stage }),
      ]));
    });
    return C.el("div", {}, [C.el("h4", { text: label }), box]);
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
          toggle, dismiss,
        ]),
        { icon: r.complete ? "check" : "info", tone: r.complete ? "ok" : "warn" }
      ));
    }).catch(function () { /* onboarding plugin off — Overview still works */ });
    return host;
  }

  function render(host, api) {
    C.load(host, C.get("/api/overview"), function (d) {
      var grid = C.el("div", { class: "grid" });
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
      ]), null, { icon: "layout" }));

      /* -- attention: the widest panel, since its rows are sentences -- */
      var attnKids = [
        attnGroup(a.blocked, "Blocked by a critical item", function (r) {
          return C.el("span", { class: "chip danger" }, [C.icon("alert"), String(r.blocking)]);
        }, api),
        attnGroup(a.stale, "Stale (" + d.stale_days + "+ days)", function (r) {
          return C.el("span", { class: "chip warn" }, [C.icon("clock"), C.fmtAgo(r.idle_days)]);
        }, api),
        attnGroup(a.unowned, "Nobody owns these", function () {
          return C.el("span", { class: "chip" }, [C.icon("user"), "—"]);
        }, api),
      ].filter(Boolean);
      var attnTotal = a.counts.blocked + a.counts.stale + a.counts.unowned;
      grid.appendChild(C.el("div", { class: "span2" }, [
        C.panel(
          "Needs attention",
          attnKids.length ? attnKids
                          : C.empty("Nothing needs attention", "No blocked, stale or unowned work.", "check"),
          C.el("span", { class: "chip" + (attnTotal ? " warn" : " zero"), text: String(attnTotal) }),
          { icon: "alert", tone: attnTotal ? "warn" : null }
        ),
      ]));

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
      grid.appendChild(C.panel("Flow", flowKids, null, { icon: "columns", tone: "info" }));

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
      grid.appendChild(C.panel("Recently touched", recent, null, { icon: "clock" }));

      host.appendChild(grid);
    }, { skeletonRows: 5 });
  }

  C.tab("overview", { render: render });
})(window.Console);
