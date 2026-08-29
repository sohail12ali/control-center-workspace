/* Command palette — Ctrl/Cmd-K.

   The console had grown a navigation problem: to run a check you opened a
   terminal, to open a ticket you found the right board and scrolled, and to
   start an agent on a skill you filled in three dropdowns. All of those are
   one intent expressed as several clicks.

   This is one box. Type what you want, press Enter.

   Sources come from what already exists — the tab manifest, the boards, the
   verb registry, the skills and personas the composer offers. Nothing is
   hardcoded here, so a new tab, ticket, verb or skill appears in the palette
   the moment it exists anywhere else.

   Loaded before app.js, which calls Console.palette.open() from its key
   handler. */
window.Console = window.Console || {};
(function (C) {
  "use strict";

  var st = {
    open: false, query: "", index: 0, rows: [], all: [], loaded: false,
    node: null, input: null, list: null, lastFocus: null,
  };

  /* ---------------- sources ---------------- */

  /* Loaded once per open rather than once per keystroke: the palette is used
     in bursts, and re-fetching four endpoints on every character typed would
     make it feel worse the faster you type. */
  function collect() {
    var app = window.ConsoleApp;
    var tabs = (app && app.manifest && app.manifest()) || {};
    var rows = [];

    (tabs.tabs || []).forEach(function (t) {
      rows.push({
        group: "Go to", label: t.label || t.id, hint: "tab",
        icon: t.icon || "layout",
        run: function () { app.go(t.id); },
      });
    });

    return Promise.all([
      C.get("/api/verbs").catch(function () { return { verbs: [] }; }),
      C.get("/api/agents/catalog").catch(function () { return {}; }),
    ]).then(function (res) {
      var verbs = (res[0] && res[0].verbs) || [];
      var catalog = res[1] || {};

      (catalog.tickets || []).forEach(function (t) {
        rows.push({
          group: "Ticket", label: t.id + " — " + (t.title || ""),
          hint: t.stage || "", icon: "file",
          run: function () { app.go("board:tickets"); },
        });
      });

      verbs.forEach(function (v) {
        rows.push({
          group: "Run", label: v.label || v.id,
          hint: v.id + (v.needs_ticket ? " · needs a ticket" : ""),
          icon: "play",
          /* A verb needing a ticket cannot be run from a global palette with
             no ticket in hand — saying so beats a failure on Enter. */
          disabled: !!v.needs_ticket,
          disabledReason: v.needs_ticket
            ? "Open the ticket and run it from there."
            : "",
          run: function () { runVerb(v); },
        });
      });

      (catalog.skills || []).forEach(function (s) {
        rows.push({
          group: "Start agent", label: "/" + s, hint: "skill", icon: "cpu",
          run: function () { app.go("agents"); },
        });
      });

      st.all = rows;
      st.loaded = true;
      return rows;
    });
  }

  function runVerb(verb) {
    C.toast("Running " + (verb.label || verb.id) + "…");
    C.post("/api/verbs/" + encodeURIComponent(verb.id) + "/run", {})
      .then(function (out) {
        C.toast((verb.label || verb.id) + " finished", "ok");
        showResult(verb, out && out.result);
      })
      .catch(function (err) { C.toast(err.message, "err"); });
  }

  /* A verb's answer is data, and the palette is not a place to read data —
     so the result goes to the drawer the app already has for exactly this. */
  function showResult(verb, result) {
    var app = window.ConsoleApp;
    if (!app || !app.drawer) return;
    app.drawer(verb.label || verb.id, [
      C.el("pre", { class: "code",
                    text: JSON.stringify(result, null, 2).slice(0, 20000) }),
    ]);
  }

  /* ---------------- matching ---------------- */

  /* Subsequence matching, so "hl" finds "harness lint" — the way every
     palette worth using behaves. Scored so that earlier and tighter matches
     sort first, and an exact prefix always wins. */
  function score(text, query) {
    if (!query) return 1;
    var haystack = text.toLowerCase(), needle = query.toLowerCase();
    if (haystack.indexOf(needle) === 0) return 1000;
    var direct = haystack.indexOf(needle);
    if (direct > 0) return 500 - direct;

    var hi = 0, gaps = 0, last = -1;
    for (var qi = 0; qi < needle.length; qi++) {
      var found = haystack.indexOf(needle[qi], hi);
      if (found === -1) return 0;
      if (last >= 0) gaps += found - last - 1;
      last = found;
      hi = found + 1;
    }
    return Math.max(1, 200 - gaps);
  }

  function filter() {
    var q = st.query.trim();
    var scored = st.all.map(function (row) {
      return { row: row, s: score(row.label + " " + (row.hint || ""), q) };
    }).filter(function (x) { return x.s > 0; });
    scored.sort(function (a, b) { return b.s - a.s; });
    st.rows = scored.slice(0, 40).map(function (x) { return x.row; });
    st.index = 0;
  }

  /* ---------------- rendering ---------------- */

  function paint() {
    C.clear(st.list);
    if (!st.rows.length) {
      st.list.appendChild(C.el("div", { class: "cp-empty", text:
        st.loaded ? "Nothing matches." : "Loading…" }));
      return;
    }
    var lastGroup = null;
    st.rows.forEach(function (row, i) {
      if (row.group !== lastGroup) {
        lastGroup = row.group;
        st.list.appendChild(C.el("div", { class: "cp-group", text: row.group }));
      }
      var node = C.el("div", {
        class: "cp-row" + (i === st.index ? " on" : "") +
               (row.disabled ? " off" : ""),
        role: "option",
        "aria-selected": String(i === st.index),
        onclick: function () { st.index = i; choose(); },
      }, [
        C.icon(row.icon || "circle"),
        C.el("span", { class: "cp-label", text: row.label }),
        C.el("span", { class: "cp-hint muted", text:
          row.disabled ? (row.disabledReason || "unavailable") : (row.hint || "") }),
      ]);
      st.list.appendChild(node);
    });
    var on = st.list.querySelector(".cp-row.on");
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
  }

  function choose() {
    var row = st.rows[st.index];
    if (!row) return;
    if (row.disabled) { C.toast(row.disabledReason || "Not available here"); return; }
    close();
    try { row.run(); } catch (e) { C.toast(String(e && e.message || e), "err"); }
  }

  /* ---------------- lifecycle ---------------- */

  function build() {
    st.input = C.el("input", {
      class: "cp-input", type: "text", autocomplete: "off",
      "aria-label": "Command palette",
      placeholder: "Go to a tab, open a ticket, run a check…",
      oninput: function (e) { st.query = e.target.value; filter(); paint(); },
    });
    st.list = C.el("div", { class: "cp-list", role: "listbox" });
    var panel = C.el("div", { class: "cp-panel", role: "dialog",
                              "aria-modal": "true", "aria-label": "Command palette" }, [
      C.el("div", { class: "cp-inputwrap" }, [C.icon("search"), st.input]),
      st.list,
      C.el("div", { class: "cp-foot muted" }, [
        C.el("span", { text: "↑↓ move" }), C.el("span", { text: "↵ run" }),
        C.el("span", { text: "esc close" }),
      ]),
    ]);
    st.node = C.el("div", { class: "cp-scrim", onclick: function (e) {
      if (e.target === st.node) close();
    } }, [panel]);
    document.body.appendChild(st.node);
  }

  function onKey(e) {
    if (!st.open) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") {
      e.preventDefault(); st.index = Math.min(st.index + 1, st.rows.length - 1); paint();
    } else if (e.key === "ArrowUp") {
      e.preventDefault(); st.index = Math.max(st.index - 1, 0); paint();
    } else if (e.key === "Enter") { e.preventDefault(); choose(); }
  }

  function open() {
    if (st.open) return;
    if (!st.node) build();
    /* Remember where focus was so closing returns it — a palette that drops
       you somewhere else is worse than no palette for anyone on a keyboard. */
    st.lastFocus = document.activeElement;
    st.open = true;
    st.query = "";
    st.input.value = "";
    st.node.classList.add("on");
    document.addEventListener("keydown", onKey, true);

    st.rows = st.all;
    filter();
    paint();
    st.input.focus();

    collect().then(function () { filter(); paint(); });
  }

  function close() {
    if (!st.open) return;
    st.open = false;
    st.node.classList.remove("on");
    document.removeEventListener("keydown", onKey, true);
    if (st.lastFocus && st.lastFocus.focus) st.lastFocus.focus();
  }

  C.palette = { open: open, close: close, isOpen: function () { return st.open; } };
})(window.Console);
