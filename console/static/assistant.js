/* Assistant home tab — talk, live Runs, ticket strip.

   First paint is three GETs and no EventSource (T-016 / T-015 no-probe).
   The stream opens only after the person sends a turn that needs a reply. */
(function (C) {
  "use strict";

  var st = { host: null, api: null, es: null, log: [] };

  function closeStream() {
    if (st.es) { st.es.close(); st.es = null; }
  }

  function listen() {
    if (st.es || C.IS_STATIC) return;
    st.es = new EventSource("/api/assistant/stream?from=0");
    st.es.onmessage = function (m) {
      var ev;
      try { ev = JSON.parse(m.data); } catch (e) { return; }
      if (ev.type === "reply" && ev.text) {
        st.log.push({ role: "assistant", text: ev.text });
        paintLog();
      }
    };
  }

  function paintLog() {
    var box = document.getElementById("asLog");
    if (!box) return;
    C.clear(box);
    if (!st.log.length) {
      box.appendChild(C.el("div", { class: "muted",
        text: "Ask about a ticket, or what is running." }));
      return;
    }
    st.log.forEach(function (line) {
      box.appendChild(C.el("div", { class: "lrow" }, [
        C.el("span", { class: "chip", text: line.role === "user" ? "you" : "Assistant" }),
        C.el("span", { class: "ltext", text: line.text }),
      ]));
    });
    box.scrollTop = box.scrollHeight;
  }

  function send(text) {
    text = (text || "").trim();
    if (!text) return;
    st.log.push({ role: "user", text: text });
    paintLog();
    C.post("/api/assistant/say", { text: text, source: "tab" })
      .then(function (out) {
        if (out.result === "handled" && out.spoken) {
          st.log.push({ role: "assistant", text: out.spoken });
          paintLog();
        } else if (out.result === "error") {
          C.toast(out.reason || "Assistant error", "err");
        } else {
          listen();
        }
      })
      .catch(function (err) { C.toast(err.message, "err"); });
  }

  function runRow(run, api) {
    return C.el("div", {
      class: "lrow clickable",
      title: "Open the Run inspector",
      onclick: function () { api.go("agents"); },
    }, [
      C.el("span", { class: "chip", text: run.state || "" }),
      C.el("span", { class: "ltext" }, [
        C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)",
          text: (run.id || "") + " " }),
        [(run.ticket || ""), run.role || ""].filter(Boolean).join(" "),
      ]),
    ]);
  }

  function ticketRow(r, api) {
    return C.el("div", {
      class: "lrow clickable",
      onclick: function () { api.go("board:" + (r.kind || "tickets")); },
    }, [
      C.el("span", { class: "chip", text: r.stage || r.kind || "" }),
      C.el("span", { class: "ltext" }, [
        C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)", text: r.id + " " }),
        r.title || "",
      ]),
    ]);
  }

  function render(host, api) {
    st.host = host;
    st.api = api;
    if (C.IS_STATIC) {
      host.appendChild(C.empty("Assistant needs a live server",
        "This is a read-only snapshot. Run: python console/kanban.py serve", "mic"));
      return;
    }

    var ta = C.el("textarea", {
      "aria-label": "Talk to the Assistant",
      placeholder: "Ask about a ticket, or what is running…",
      rows: "3",
    });
    ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send(ta.value);
        ta.value = "";
      }
    });

    C.load(host, Promise.all([
      C.get("/api/runs").catch(function () { return { runs: [] }; }),
      C.get("/api/overview").catch(function () { return { recent: [], attention: { blocked: [] } }; }),
      C.get("/api/assistant/session").catch(function () { return { active: false }; }),
    ]), function (res) {
      var runs = (res[0] && res[0].runs) || [];
      var overview = res[1] || {};
      var session = res[2] || {};
      var recent = overview.recent || [];
      var blocked = (overview.attention && overview.attention.blocked) || [];

      var runBox = C.el("div", { class: "rows" });
      if (!runs.length) {
        runBox.appendChild(C.el("div", { class: "muted",
          text: "No Runs yet. Start one from a ticket, or ask me to delegate." }));
      } else {
        runs.forEach(function (r) { runBox.appendChild(runRow(r, api)); });
      }

      var tickets = C.el("div", { class: "rows" });
      var seen = {};
      var strip = blocked.concat(recent);
      var n = 0;
      strip.forEach(function (r) {
        if (!r || seen[r.id] || n >= 8) return;
        seen[r.id] = 1;
        n += 1;
        tickets.appendChild(ticketRow(r, api));
      });
      if (!n) {
        tickets.appendChild(C.el("div", { class: "muted", text: "No open tickets." }));
      }

      host.appendChild(C.el("div", { class: "grid as-home" }, [
        C.el("div", { class: "span2" }, [
          C.panel("Talk", [
            C.el("div", { class: "as-talk" }, [
              ta,
              C.el("button", {
                class: "btn primary iconly as-send", type: "button",
                title: "Send", "aria-label": "Send",
                onclick: function () { send(ta.value); ta.value = ""; },
              }, [C.icon("send")]),
            ]),
            C.el("div", { id: "asLog", class: "as-log" }),
          ], session.active
            ? C.el("span", { class: "chip", text: "live" })
            : C.el("span", { class: "chip zero", text: "idle" }),
          { icon: "mic" }),
        ]),
        C.panel("Runs", runBox,
          C.el("span", { class: "chip" + (runs.length ? "" : " zero"), text: String(runs.length) }),
          { icon: "play" }),
        C.panel("Tickets", tickets, null, { icon: "file" }),
      ]));
      paintLog();
    });
  }

  C.tab("assistant", {
    render: render,
    onLeave: function () { closeStream(); },
  });
})(window.Console);
