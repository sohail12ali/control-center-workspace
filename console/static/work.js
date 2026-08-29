/* Work tab — timesheet over the per-author daily log files /log-work writes.

   Read-only by design: adding an entry goes through /log-work, which owns
   author resolution and the idempotency rule. Duplicating that here would
   mean two writers with different rules for the same file.

   Details worth having:
   - day view and range view are different questions ("what did I do today"
     vs "where did the month go"), so they are separate modes rather than
     one date picker.
   - the author filter is built from who actually has log files.
   - explicit ~Nh hints are marked, because a pinned hour and an allocated
     one are not the same claim and a timesheet that hides the difference is
     misleading. */
(function (C) {
  "use strict";

  var st = { mode: "day", date: C.todayISO(), author: "", host: null };

  function catTone(cat) {
    return { Development: "c1", "Code Review": "c2", Testing: "c3", Design: "c4", Documentation: "c5", Internal: "c6" }[cat] || "cother";
  }

  function shiftDate(days) {
    var d = new Date(st.date + "T00:00:00");
    d.setDate(d.getDate() + days);
    st.date = d.toISOString().slice(0, 10);
  }

  function controls(authors) {
    var seg = C.el("div", { class: "seg" }, [
      C.el("button", { "aria-pressed": String(st.mode === "day"), onclick: function () { st.mode = "day"; paint(); } }, ["Day"]),
      C.el("button", { "aria-pressed": String(st.mode === "week"), onclick: function () { st.mode = "week"; paint(); } }, ["7 days"]),
      C.el("button", { "aria-pressed": String(st.mode === "month"), onclick: function () { st.mode = "month"; paint(); } }, ["30 days"]),
    ]);

    var kids = [seg];
    if (st.mode === "day") {
      kids.push(C.el("button", { class: "btn sm iconly", "aria-label": "Previous day", title: "Previous day",
        onclick: function () { shiftDate(-1); paint(); } }, [C.icon("chevLeft")]));
      kids.push(C.el("input", {
        type: "date", value: st.date, style: "width:auto",
        onchange: function (e) { st.date = e.target.value; paint(); },
      }));
      kids.push(C.el("button", { class: "btn sm iconly", "aria-label": "Next day", title: "Next day",
        onclick: function () { shiftDate(1); paint(); } }, [C.icon("chevRight")]));
      if (st.date !== C.todayISO()) {
        kids.push(C.el("button", { class: "btn sm", onclick: function () { st.date = C.todayISO(); paint(); } }, ["Today"]));
      }
    }

    if (authors && authors.length > 1) {
      kids.push(C.el("select", {
        "aria-label": "Filter by author", style: "width:auto;min-width:130px",
        onchange: function (e) { st.author = e.target.value; paint(); },
      }, [C.el("option", { value: "" }, ["All authors"])].concat(authors.map(function (a) {
        return C.el("option", { value: a.slug, selected: a.slug === st.author || null }, [a.name]);
      }))));
    }

    return C.el("div", { class: "row", style: "margin-bottom:12px;flex-wrap:wrap" }, kids);
  }

  function sheetPanel(sheet) {
    var cats = Object.keys(sheet.by_category);
    var body = [];

    // Category proportion bar first: the shape of the day in one line.
    body.push(C.stack(cats.map(function (cat) {
      return { label: cat, count: Math.round(sheet.by_category[cat].total * 100) / 100 };
    })));

    cats.forEach(function (cat) {
      var data = sheet.by_category[cat];
      var rows = C.el("div", { class: "rows" });
      Object.keys(data.tickets).forEach(function (tid) {
        var t = data.tickets[tid];
        rows.appendChild(C.el("div", { class: "lrow" }, [
          C.el("span", { class: "chip", text: C.fmtNum(t.hours) + "h" }),
          C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: tid }),
          C.el("span", { class: "ltext" }, [
            t.activities.map(function (a, i) {
              return C.el("div", { style: i ? "margin-top:2px" : "", text: a });
            }),
          ]),
          t.pinned ? C.el("span", { class: "chip info", title: "Hours were stated explicitly with ~Nh" }, ["pinned"]) : null,
        ]));
      });
      body.push(C.el("div", { style: "margin-top:10px" }, [
        C.el("h4", { text: cat + " — " + C.fmtNum(data.total) + "h" }),
        rows,
      ]));
    });

    return C.panel(
      sheet.author || sheet.author_slug || "(unknown author)",
      body,
      C.el("span", { class: "chip accent", text: C.fmtNum(sheet.total_hours) + "h" })
    );
  }

  function paintDay(host) {
    C.load(host, C.get("/api/work/day?date=" + st.date + (st.author ? "&author=" + st.author : "")),
      function (res) {
        var sheets = res.sheets || [];
        if (!sheets.length) {
          host.appendChild(C.empty(
            "No work logged on " + st.date,
            "Add a line with:  /log-work {T} ~2h what shipped",
            "clock"
          ));
          return;
        }
        sheets.forEach(function (s) { host.appendChild(sheetPanel(s)); });
      }, { skeletonRows: 4 });
  }

  function paintRange(host) {
    var days = st.mode === "week" ? 7 : 30;
    var end = C.todayISO();
    var start = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
    C.load(host, C.get("/api/work/range?start=" + start + "&end=" + end + (st.author ? "&author=" + st.author : "")),
      function (d) {
        var total = Object.keys(d.hours_by_day).reduce(function (n, k) { return n + d.hours_by_day[k]; }, 0);
        if (!d.files_scanned) {
          host.appendChild(C.empty("No logs in the last " + days + " days", null, "clock"));
          return;
        }
        host.appendChild(C.el("div", { class: "row", style: "margin-bottom:10px" }, [
          C.el("span", { class: "chip accent", text: C.fmtNum(total) + "h total" }),
          C.el("span", { class: "chip", text: d.files_scanned + " day-files" }),
          C.el("span", { class: "chip", text: start + " → " + end }),
        ]));
        var grid = C.el("div", { class: "grid" }, [
          C.panel("Hours by day", C.bars(Object.entries(d.hours_by_day), { unit: "h", sort: false, keyLabel: "Day", valLabel: "Hours" })),
          C.panel("Hours by ticket", C.bars(Object.entries(d.hours_by_ticket), { unit: "h", colorByIndex: true, keyLabel: "Ticket", valLabel: "Hours" })),
          C.panel("Category split", C.bars(Object.entries(d.category_split), { unit: "h", colorByIndex: true, keyLabel: "Category", valLabel: "Hours" })),
          C.panel("Hours by author", C.bars(Object.entries(d.hours_by_author), { unit: "h", colorByIndex: true, keyLabel: "Author", valLabel: "Hours" })),
        ]);
        host.appendChild(grid);
      }, { skeletonRows: 4 });
  }

  /* ---------------- audit trail ----------------
     On the Work tab because it answers the timesheet's own question — what
     happened and who did it — for the half of the work nobody types into a
     log file: verbs run, chats started, approvals answered.

     It is the console's record, not the person's, so it sits BELOW the
     timesheet and is collapsed by default. The two must not be confused: one
     is a claim about hours, the other is a machine's account of itself. */

  var ACTION_TONE = {
    "approval.decide": "warn", "job.cancel": "warn",
    "chat.start": "accent", "chat.stop": null,
    "verb.run": "ok", "verb.submit": "ok", "schedule.fire": "info",
  };

  function auditPanel() {
    var host = C.el("div");
    var open = C.prefs.get("workAuditOpen", false);

    C.get("/api/work/audit?limit=60").then(function (d) {
      var entries = (d && d.entries) || [];
      if (!d.enabled && !entries.length) return;   // switched off: say nothing

      var body = C.el("div");
      function fill() {
        C.clear(body);
        if (!open) return;
        if (!entries.length) {
          body.appendChild(C.empty("Nothing recorded yet",
            "Reads are deliberately not logged — only actions that change something.",
            "list"));
          return;
        }
        var rows = C.el("div", { class: "rows" });
        entries.forEach(function (e) {
          rows.appendChild(C.el("div", { class: "lrow" }, [
            C.el("span", { class: "chip " + (ACTION_TONE[e.action] || ""), text: e.action }),
            C.el("span", { class: "ltext" }, [
              C.el("b", { text: e.target || "—" }),
              /* "ok" is the default outcome on every successful row, so
                 printing it would be noise on every line and invisible on the
                 few that matter. Only a non-ok outcome earns space. */
              e.outcome && e.outcome !== "ok"
                ? C.el("span", { class: "muted", text: " " + e.outcome }) : null,
            ]),
            /* The address is the point of the trail once more than one
               device can start work — it is how "was that me?" gets an
               answer. */
            C.el("span", { class: "chip", title: "Where the request came from",
                           text: (e.actor && e.actor.addr) || "local" }),
            C.el("span", { class: "muted mono", style: "font-size:11px",
                           text: (e.ts || "").replace("T", " ").slice(0, 16) }),
          ]));
        });
        body.appendChild(rows);
        body.appendChild(C.el("p", { class: "muted", style: "margin:8px 0 0;font-size:11px",
          text: "Local and gitignored — these rows carry client addresses." }));
      }

      var toggle = C.el("button", {
        class: "btn sm",
        onclick: function () {
          open = !open;
          C.prefs.set("workAuditOpen", open);
          toggle.textContent = open ? "Hide" : "Show";
          fill();
        },
      }, [open ? "Hide" : "Show"]);

      host.appendChild(C.panel("Console activity", [body],
        C.el("span", { class: "row", style: "gap:6px" }, [
          C.el("span", { class: "chip", text: entries.length + " recent" }), toggle,
        ]), { icon: "list" }));
      fill();
    }).catch(function () { /* plugin off, or a static export */ });

    return host;
  }

  function paint() {
    var host = C.clear(st.host);
    C.get("/api/work/authors").then(function (authors) {
      host.appendChild(controls(authors));
      var body = C.el("div", {});
      host.appendChild(body);
      if (st.mode === "day") paintDay(body); else paintRange(body);
      host.appendChild(auditPanel());
    }).catch(function (err) {
      host.appendChild(controls([]));
      host.appendChild(C.errbox(err));
    });
  }

  C.tab("work", { render: function (host) { st.host = host; paint(); } });
})(window.Console);
