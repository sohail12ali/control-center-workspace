/* Analytics tab — DOM charts (not canvas) so they theme themselves and every
   one has a real table twin for screen readers and exact numbers.

   Two independent filters, and each section header says which of them
   reaches it — a filter that silently applies to half the page is worse
   than no filter.

   Uses --cat-* for series colour, never --accent/--info/--run: those three
   are the same blue, so a multi-series chart drawn from them would be one
   colour with several labels. */
(function (C) {
  "use strict";

  var st = { window: 30, board: "all", host: null };

  function scopeNote(text) {
    return C.el("span", { class: "chip", style: "font-weight:400", text: text });
  }

  function controls(boards) {
    var win = C.el("div", { class: "seg" });
    [[7, "7d"], [30, "30d"], [90, "90d"]].forEach(function (p) {
      win.appendChild(C.el("button", {
        "aria-pressed": String(st.window === p[0]),
        onclick: function () { st.window = p[0]; paint(); },
      }, [p[1]]));
    });

    var bsel = C.el("div", { class: "seg" });
    [["all", "All boards"]].concat(boards.map(function (b) { return [b.kind, b.label]; }))
      .forEach(function (p) {
        bsel.appendChild(C.el("button", {
          "aria-pressed": String(st.board === p[0]),
          onclick: function () { st.board = p[0]; paint(); },
        }, [p[1]]));
      });

    return C.el("div", { class: "row", style: "margin-bottom:12px;flex-wrap:wrap" }, [
      C.el("span", { class: "muted", text: "Window" }), win,
      C.el("span", { class: "muted", text: "Board" }), bsel,
    ]);
  }

  /* ---------------- spend ----------------
     Agent cost belongs on the tab that already answers "where did the effort
     go" — it is the same question with a different unit.

     The rule this section is built around: **an unpriced turn is never
     silently free.** A model the pricing table does not know contributes
     tokens but no cost, and every total drawn from such a window says so,
     inline, every time. A dashboard that quietly under-reports spend is worse
     than one that reports nothing, because it gets believed. */

  function costText(t) {
    return t.cost_complete ? "$" + (t.cost_usd || 0).toFixed(2)
                           : "$" + (t.cost_usd || 0).toFixed(2) + "*";
  }

  function spendTable(rows, keyLabel) {
    return C.el("div", { class: "tablewrap" }, [
      C.el("table", { class: "dt" }, [
        C.el("thead", {}, [C.el("tr", {}, [
          C.el("th", { text: keyLabel }),
          C.el("th", { class: "num", text: "Turns" }),
          C.el("th", { class: "num", text: "Tokens" }),
          C.el("th", { class: "num", text: "Cost" }),
        ])]),
        C.el("tbody", {}, rows.map(function (r) {
          return C.el("tr", {}, [
            C.el("td", { text: r.key || "—" }),
            C.el("td", { class: "num", text: String(r.turns) }),
            C.el("td", { class: "num", text: C.fmtNum(r.tokens) }),
            C.el("td", {
              class: "num", text: costText(r),
              title: r.cost_complete ? "" :
                r.unpriced_turns + " turn(s) had no price — excluded from this total",
            }),
          ]);
        })),
      ]),
    ]);
  }

  function spendPanels(grid, spend) {
    /* Older server, or the telemetry module unavailable: show nothing rather
       than an empty box explaining an absence nobody asked about. */
    if (!spend) return;

    if (!spend.available) {
      grid.appendChild(C.panel("Agent spend", [
        C.empty("Telemetry unavailable", spend.reason || "", "alert"),
      ]));
      return;
    }

    var t = spend.totals || {};
    if (!t.turns) {
      /* The honest empty state, and a genuinely useful one here: it names the
         single action that fills it, because "no data" on a brand-new console
         means "nothing has run yet", not "something is broken". */
      grid.appendChild(C.panel("Agent spend", [
        C.empty("No agent turns recorded yet",
          "Start a chat from the Agents tab. Every turn records its tokens and cost here.",
          "cpu"),
      ], scopeNote("window")));
      return;
    }

    grid.appendChild(C.panel("Agent spend", [
      C.stats([
        C.stat(C.fmtNum(t.turns), "Turns", { tone: "accent" }),
        C.stat(C.fmtNum(t.tokens), "Tokens", { sub: "in + out" }),
        C.stat(costText(t), "Cost", {
          tone: t.cost_complete ? "ok" : "warn",
          sub: t.cost_complete ? "all turns priced"
                               : t.unpriced_turns + " unpriced",
        }),
        C.stat(C.fmtNum(t.input_tokens), "Input"),
        C.stat(C.fmtNum(t.output_tokens), "Output"),
      ]),
      t.cost_complete ? null : C.el("p", {
        class: "muted", style: "margin:8px 0 0;font-size:11px",
        text: "* " + t.unpriced_turns + " turn(s) ran on a model with no entry in "
            + "console/config/pricing.toml. Their tokens are counted; their cost "
            + "is excluded rather than assumed to be zero.",
      }),
    ], scopeNote("window"), { icon: "cpu" }));

    if (spend.by_model.length) {
      grid.appendChild(C.panel("Spend by model", [
        C.bars(spend.by_model.map(function (r) { return [r.key || "—", r.tokens]; }),
          { colorByIndex: true, keyLabel: "Model", valLabel: "Tokens" }),
        C.el("div", { style: "margin-top:8px" }, [spendTable(spend.by_model, "Model")]),
      ], scopeNote("window")));
    }

    if (spend.by_ticket.length) {
      grid.appendChild(C.panel("Spend by ticket", [
        spendTable(spend.by_ticket, "Ticket"),
      ], scopeNote("window")));
    }
  }

  function kindsToShow(data) {
    var all = Object.keys(data.lane_funnel);
    return st.board === "all" ? all : all.filter(function (k) { return k === st.board; });
  }

  function paint() {
    var host = C.clear(st.host);
    var cfg = window.ConsoleApp.manifest().filter(function (t) { return t.group === "boards"; })
      .map(function (t) { return { kind: t.kind, label: t.label }; });
    host.appendChild(controls(cfg));

    var body = C.el("div", {});
    host.appendChild(body);

    C.load(body, C.get("/api/analytics?window=" + st.window), function (d) {
      var grid = C.el("div", { class: "grid" });

      /* -- pipeline per board (board filter applies; window does not) -- */
      kindsToShow(d).forEach(function (kind) {
        var lanes = d.lane_funnel[kind];
        grid.appendChild(C.panel(
          "Pipeline — " + kind,
          [
            C.stack(lanes.map(function (l) { return { label: l.label, count: l.count }; })),
            C.el("div", { style: "margin-top:9px" }, [
              C.bars(lanes.map(function (l) { return [l.label, l.count]; }),
                { sort: false, colorByIndex: true, keyLabel: "Lane", valLabel: "Cards" }),
            ]),
          ],
          scopeNote("board filter")
        ));
      });

      /* -- ageing: median/max idle per lane -- */
      kindsToShow(d).forEach(function (kind) {
        var idle = d.idle_by_lane[kind] || {};
        var keys = Object.keys(idle);
        if (!keys.length) return;
        var rows = keys.map(function (k) { return [k, idle[k].median]; });
        grid.appendChild(C.panel(
          "Median idle days — " + kind,
          [
            C.bars(rows, { unit: "d", colorByIndex: true, keyLabel: "Lane", valLabel: "Median days" }),
            C.el("div", { class: "tablewrap", style: "margin-top:8px" }, [
              C.el("table", { class: "dt" }, [
                C.el("thead", {}, [C.el("tr", {}, [
                  C.el("th", { text: "Lane" }), C.el("th", { class: "num", text: "Median" }),
                  C.el("th", { class: "num", text: "Max" }), C.el("th", { class: "num", text: "Cards" }),
                ])]),
                C.el("tbody", {}, keys.map(function (k) {
                  return C.el("tr", {}, [
                    C.el("td", { text: k }),
                    C.el("td", { class: "num", text: idle[k].median + "d" }),
                    C.el("td", { class: "num", text: idle[k].max + "d" }),
                    C.el("td", { class: "num", text: String(idle[k].count) }),
                  ]);
                })),
              ]),
            ]),
          ],
          scopeNote("board filter")
        ));
      });

      /* -- flagged -- */
      var flagRows = Object.keys(d.flag_bars)
        .filter(function (k) { return st.board === "all" || k === st.board; })
        .map(function (k) { return [k, d.flag_bars[k].flagged]; });
      grid.appendChild(C.panel("Tickets with a critical open item", [
        C.bars(flagRows, { colorByIndex: true, keyLabel: "Board", valLabel: "Flagged" }),
      ], scopeNote("board filter")));

      /* -- throughput (window applies) -- */
      grid.appendChild(C.panel("Closed per week", [
        C.bars(Object.entries(d.throughput), { sort: false, keyLabel: "Week", valLabel: "Closed" }),
        C.el("div", { class: "muted", style: "margin-top:6px",
          text: "Proxy: last update on a card sitting in a terminal lane — this template stores no explicit closed date." }),
      ], scopeNote("all boards")));

      /* -- worklog (window + author apply; absent if the work plugin is off) -- */
      if (d.worklog === null) {
        grid.appendChild(C.panel("Timesheet", [
          C.empty("Work plugin is disabled",
            "Enable the `work` row in console/config/plugins.toml to chart logged hours.", "clock"),
        ]));
      } else {
        var w = d.worklog;
        if (!w.files_scanned) {
          grid.appendChild(C.panel("Timesheet", [
            C.empty("No logged hours in this window", "Use /log-work to record work.", "clock"),
          ], scopeNote("window")));
        } else {
          grid.appendChild(C.panel("Hours by day", [
            C.bars(Object.entries(w.hours_by_day), { unit: "h", sort: false, keyLabel: "Day", valLabel: "Hours" }),
          ], scopeNote("window")));
          grid.appendChild(C.panel("Hours by ticket", [
            C.bars(Object.entries(w.hours_by_ticket), { unit: "h", colorByIndex: true, keyLabel: "Ticket", valLabel: "Hours" }),
          ], scopeNote("window")));
          grid.appendChild(C.panel("Category split", [
            C.bars(Object.entries(w.category_split), { unit: "h", colorByIndex: true, keyLabel: "Category", valLabel: "Hours" }),
          ], scopeNote("window")));
        }
      }

      spendPanels(grid, d.spend);

      body.appendChild(grid);
    }, { skeletonRows: 6 });
  }

  C.tab("analytics", { render: function (host) { st.host = host; paint(); } });
})(window.Console);
