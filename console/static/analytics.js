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

      body.appendChild(grid);
    }, { skeletonRows: 6 });
  }

  C.tab("analytics", { render: function (host) { st.host = host; paint(); } });
})(window.Console);
