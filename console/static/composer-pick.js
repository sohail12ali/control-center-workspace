/* Inline `/` `@` `#` picker for a composer textarea.

   `/` a skill, `@` an agent, `#` a file or folder — the three rosters an agent
   message actually refers to, kept as three triggers because a single list
   mixing them is one nobody can scan.

   ## It only suggests; the server decides

   Choosing a row inserts TEXT. What `/plan` then means on the wire is resolved
   server-side by `prompt_tokens`, per backend: claude parses `/plan` itself,
   cursor-agent needs a sentence naming the file, an API model needs the path.
   Putting that translation here would have meant the tab and the CLI could
   disagree about what a token means, which is exactly the class of bug the
   backend registry exists to prevent.

   So this file has no opinion about backends. It offers names.

   ## Prose has to survive

   A trigger only opens the menu at a token boundary — start of input, or after
   whitespace — which is what keeps "and/or", "24/7" and "a@b.com" from opening
   it mid-word. Typing past a match simply closes it; nothing is ever inserted
   without a deliberate Enter or click. And an unresolved token is not an
   error: the server leaves it as text, so a half-typed reference sends as what
   it looks like.

   Attached to both composers — the New-chat form and the live one. */
window.ConsoleComposerPick = (function (C) {
  "use strict";

  /* File search hits the disk, so it is debounced. Skills and personas come
     from one catalog fetch that is already in memory. */
  var FILE_DEBOUNCE = 140;
  var MAX_ROWS = 12;

  var TRIGGERS = {
    "/": { kind: "skill", icon: "brain", label: "Skill", pref: "pickSkills" },
    "@": { kind: "persona", icon: "user", label: "Agent", pref: "pickAgents" },
    "#": { kind: "path", icon: "file", label: "File", pref: "pickFiles" }
  };

  /* Each trigger can be switched off in Settings. Switching one off stops the
     MENU, not the syntax: the server still resolves a token you type by hand,
     so turning the file menu off does not quietly change what `#src/app.py`
     means once sent. */
  function enabled(trigger) {
    return C.prefs.get(TRIGGERS[trigger].pref, true);
  }

  /* Mirrors prompt_tokens.TOKEN_RE. A name must START alphanumeric, which is
     what keeps `# Heading` and a bare `/` out of it. */
  var ACTIVE_RE = /(^|\s)([/@#])([A-Za-z0-9][A-Za-z0-9._\-/\\]*)?$/;

  /* Find the trigger the caret currently sits inside, if any. Only the text
     BEFORE the caret is considered: editing earlier in a line must not reopen
     a menu for a token you finished with ten words ago. */
  function activeToken(el) {
    var caret = el.selectionStart;
    if (caret !== el.selectionEnd) return null;      // a selection is not typing
    var before = el.value.slice(0, caret);
    var m = ACTIVE_RE.exec(before);
    if (!m) return null;
    return {
      trigger: m[2],
      query: m[3] || "",
      start: caret - (m[3] || "").length - 1,        // includes the trigger
      end: caret
    };
  }

  function attach(el, opts) {
    opts = opts || {};
    var catalog = opts.catalog || {};
    var st = { open: false, rows: [], index: 0, token: null, timer: null, seq: 0 };

    var list = C.el("div", {
      class: "cpick", role: "listbox", "aria-label": "Insert a reference"
    });
    list.hidden = true;
    // Positioned by the composer's own wrapper, so it floats over the
    // transcript rather than pushing the input around as rows come and go.
    (opts.mount || el.parentNode).appendChild(list);

    function close() {
      if (!st.open && list.hidden) return;
      st.open = false;
      st.rows = [];
      st.token = null;
      list.hidden = true;
      C.clear(list);
      el.removeAttribute("aria-activedescendant");
    }

    function paint() {
      C.clear(list);
      if (!st.rows.length) { list.hidden = true; return; }
      var meta = TRIGGERS[st.token.trigger];
      list.appendChild(C.el("div", { class: "cpick-head muted" }, [
        C.icon(meta.icon),
        C.el("span", { text: meta.label }),
        C.el("span", { class: "grow" }),
        C.el("span", { text: "↑↓ ↵ esc" })
      ]));
      st.rows.forEach(function (row, i) {
        list.appendChild(C.el("div", {
          class: "cp-row cpick-row" + (i === st.index ? " on" : ""),
          role: "option",
          id: "cpick-" + i,
          "aria-selected": String(i === st.index),
          // mousedown, not click: the textarea must not lose focus first, or
          // the caret position we are about to splice into is already gone.
          onmousedown: function (e) { e.preventDefault(); st.index = i; choose(); }
        }, [
          C.icon(row.icon || meta.icon),
          C.el("span", { class: "cp-label", text: row.label }),
          row.hint ? C.el("span", { class: "cp-hint muted", text: row.hint }) : null
        ]));
      });
      list.hidden = false;
      var on = list.querySelector(".cpick-row.on");
      if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
      el.setAttribute("aria-activedescendant", "cpick-" + st.index);
    }

    function rank(items, query) {
      return items
        .map(function (it) { return { it: it, s: C.score(it.label + " " + (it.hint || ""), query) }; })
        .filter(function (x) { return x.s > 0; })
        .sort(function (a, b) { return b.s - a.s; })
        .slice(0, MAX_ROWS)
        .map(function (x) { return x.it; });
    }

    function localRows(kind, query) {
      var source = kind === "skill" ? (catalog.skills || []) : (catalog.personas || []);
      return rank(source.map(function (name) {
        return { label: name, value: name };
      }), query);
    }

    function offer(rows) {
      st.rows = rows;
      st.index = 0;
      st.open = !!rows.length;
      paint();
    }

    function refresh() {
      var token = activeToken(el);
      st.token = token;
      if (!token || !enabled(token.trigger)) { close(); return; }

      if (token.trigger !== "#") {
        offer(localRows(TRIGGERS[token.trigger].kind, token.query));
        return;
      }

      // Files come from the server. Debounced, and answers are dropped if the
      // caret moved on — an out-of-order response would otherwise repopulate
      // the menu for a token that is no longer being typed.
      if (st.timer) clearTimeout(st.timer);
      var seq = ++st.seq;
      st.timer = setTimeout(function () {
        C.get("/api/agents/files?limit=" + MAX_ROWS +
              "&q=" + encodeURIComponent(token.query))
          .then(function (d) {
            if (seq !== st.seq) return;
            var current = activeToken(el);
            if (!current || current.trigger !== "#") return;
            offer((d.files || []).map(function (f) {
              return {
                label: f.path,
                value: f.path,
                icon: f.kind === "dir" ? "folder" : "file"
              };
            }));
          })
          .catch(function () { close(); });   // no menu beats a broken menu
      }, FILE_DEBOUNCE);
    }

    function choose() {
      var row = st.rows[st.index];
      var token = st.token;
      if (!row || !token) return;
      var insert = token.trigger + row.value + " ";
      el.value = el.value.slice(0, token.start) + insert + el.value.slice(token.end);
      var caret = token.start + insert.length;
      el.setSelectionRange(caret, caret);
      close();
      /* Remember a chosen PATH on the catalog itself.

         Skills and agents can be recognised later by looking them up in the
         roster the picker was built from. A path cannot — the browser has no
         way to stat the workspace — so the one moment its existence is known
         for certain is right here, when it came back from
         `/api/agents/files`. Recording it lets the transcript mark `#path` the
         same way it marks `/skill`, without ever guessing at one that was
         merely typed. */
      if (TRIGGERS[token.trigger].kind === "path") {
        if (!catalog.paths) catalog.paths = [];
        if (catalog.paths.indexOf(row.value) === -1) catalog.paths.push(row.value);
      }
      // The composer keeps its own copy of the text for the Start button's
      // enabled state; without this it would still think the box was empty.
      if (opts.onChange) opts.onChange(el.value);
      el.focus();
    }

    el.addEventListener("input", refresh);
    // Arrow keys and clicks move the caret without firing `input`, and a token
    // the caret has left must stop being offered.
    el.addEventListener("keyup", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight" ||
          e.key === "Home" || e.key === "End") refresh();
    });
    el.addEventListener("blur", function () { setTimeout(close, 120); });

    /* Capture phase, and only while the menu is open: the composer's own
       Enter-to-send handler is on the same element, and it must not fire when
       Enter is choosing a row. */
    el.addEventListener("keydown", function (e) {
      if (!st.open) return;
      if (e.key === "ArrowDown") {
        e.preventDefault(); e.stopPropagation();
        st.index = Math.min(st.index + 1, st.rows.length - 1); paint();
      } else if (e.key === "ArrowUp") {
        e.preventDefault(); e.stopPropagation();
        st.index = Math.max(st.index - 1, 0); paint();
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault(); e.stopPropagation();
        choose();
      } else if (e.key === "Escape") {
        e.preventDefault(); e.stopPropagation();
        close();
      }
    }, true);

    return {
      close: close,
      setCatalog: function (next) { catalog = next || {}; }
    };
  }

  return { attach: attach, TRIGGERS: TRIGGERS };
})(window.Console);
