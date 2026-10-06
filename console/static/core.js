/* Shared kernel: DOM helpers, fetch, the client-side tab-plugin registry,
   preferences, and toasts.

   Client mirror of the server's plugin idea: a tab is a module that calls
   `Console.tab(id, {...})` at load time. The router never imports a tab and
   no tab imports another — app.js walks whatever registered and intersects
   it with the server's /api/config manifest. Adding a tab is one new file
   plus one <script> tag; nothing existing is edited. */
window.Console = (function () {
  "use strict";

  var IS_STATIC = !!window.__STATIC__;
  var I = window.ConsoleIcons;

  /* ---------------- tab registry ---------------- */
  var _tabs = {};

  /** Register a tab implementation.
   *  def: { render(host, api), title?, onLeave?() }
   *  Server-side manifest (label/short/icon/badge/needs_live) is merged in
   *  by app.js — a tab file does not restate what /api/config already says. */
  function tab(id, def) { _tabs[id] = def; }
  function tabImpl(id) { return _tabs[id]; }
  function tabIds() { return Object.keys(_tabs); }

  /* ---------------- reload holds ----------------
     The automatic UI-version reload (app.js) can see text in the DOM, but not a
     draft a tab keeps in a module variable and repaints from. Such a module
     registers a hold, in the same register-yourself style as `tab` above. It
     lives here and not on ConsoleApp because tab scripts load before app.js
     creates ConsoleApp: a top-level ConsoleApp.holdReload() would throw and
     abort the tab module. Keyed by id, so registering twice replaces. */
  var _holds = {};

  /** fn() returns true while the module holds unsaved state. */
  function holdReload(id, fn) { _holds[id] = fn; }

  /** True when any hold says so. A hold that throws counts as not holding: a
   *  broken module must not pin the page forever, and the DOM rules in app.js
   *  still protect typed text. A truthy return counts, so a hold that forgets
   *  to coerce to a boolean errs on the side of keeping the user's text. */
  function reloadHeld() {
    return Object.keys(_holds).some(function (id) {
      try { return !!_holds[id](); } catch (e) { return false; }
    });
  }

  /* ---------------- fetch ----------------
     A static export is read from `window.__CONSOLE_DATA__`, a plain script
     the exported index.html loads, NOT from data/*.json over fetch(). That
     is not a preference: a page opened from file:// has a null origin, and
     Chromium blocks fetch() against it entirely, so a fetch-backed snapshot
     cannot boot at all without a web server. A <script> tag has no such
     restriction. The .json files are still written next to it for anything
     that wants to read the export as data. */
  function staticKeyFor(path) {
    return path.replace(/^\/api\//, "").split("?")[0].replace(/\/$/, "").replace(/\//g, "-");
  }

  /* ---------------- request gate ----------------
     A browser allows only ~6 connections per origin on HTTP/1.1, and an SSE
     stream holds one open for as long as the chat lives. Left unmanaged, a
     burst of parallel fetches (a tab's data plus the nav badge refresh) plus
     one stream reaches that ceiling, and the next request does not fail — it
     HANGS, which surfaces as "Failed to fetch" once something gives up.

     So regular GETs go through a small queue that never uses more than
     MAX_INFLIGHT, deliberately leaving headroom for the event stream, and
     every request carries a timeout so a saturated pool reports a real error
     instead of a spinner that never resolves. */
  var MAX_INFLIGHT = 3;
  var REQUEST_TIMEOUT_MS = 15000;
  var inflight = 0;
  var waiting = [];

  function pump() {
    while (inflight < MAX_INFLIGHT && waiting.length) {
      var job = waiting.shift();
      inflight++;
      job();
    }
  }

  function gated(run) {
    return new Promise(function (resolve, reject) {
      waiting.push(function () {
        run().then(resolve, reject).then(function () {
          inflight--;
          pump();
        }, function () {
          inflight--;
          pump();
        });
      });
      pump();
    });
  }

  /* ---------------- connection state ----------------
     Derived from real traffic rather than assumed once at boot. The critical
     distinction is network failure vs HTTP error: a 400 or a 404 means the
     server answered, so it is UP — treating those as "offline" would light
     the warning every time someone requests a missing ticket. Only a
     rejected fetch (connection refused, DNS, abort/timeout) means down. */
  var _online = true;
  var _connListeners = [];

  function onConnection(fn) {
    _connListeners.push(fn);
    return function () {
      _connListeners = _connListeners.filter(function (f) { return f !== fn; });
    };
  }

  function setOnline(value) {
    if (value === _online) return;      // only fire on an actual change
    _online = value;
    _connListeners.slice().forEach(function (fn) {
      try { fn(value); } catch (e) { /* a bad listener must not break requests */ }
    });
  }

  function isOnline() { return _online; }

  function rawGet(path) {
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, REQUEST_TIMEOUT_MS);
    var opts = { headers: { Accept: "application/json" } };
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(path, opts).then(function (res) {
      clearTimeout(timer);
      // The server answered — whatever the status, it is reachable.
      setOnline(true);
      if (!res.ok) {
        return res.json().catch(function () { return {}; }).then(function (e) {
          throw new Error(e.error || res.status + " " + res.statusText);
        });
      }
      return res.json();
    }, function (err) {
      clearTimeout(timer);
      setOnline(false);
      if (err && err.name === "AbortError") {
        throw new Error("Request timed out (" + path + "). The console may be busy or stopped.");
      }
      throw err;
    });
  }

  function get(path) {
    if (IS_STATIC) {
      var store = window.__CONSOLE_DATA__ || {};
      var key = staticKeyFor(path);
      if (Object.prototype.hasOwnProperty.call(store, key)) return Promise.resolve(store[key]);
      return Promise.reject(new Error(
        "Not captured in this snapshot (" + key + "). Run the live server for this view."
      ));
    }
    return gated(function () { return rawGet(path); });
  }

  function inflightCount() { return { active: inflight, queued: waiting.length }; }

  function post(path, body) {
    if (IS_STATIC) return Promise.reject(new Error("This is a static export — it is read-only."));
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Console-Request": "1" },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      setOnline(true);
      return res.json().catch(function () { return {}; }).then(function (data) {
        // `status` lets a caller tell a rejected request (400: do not retry) from a
        // network failure (retry); the prefs write-through needs that distinction.
        if (!res.ok) throw Object.assign(new Error(data.error || res.status + " " + res.statusText), { status: res.status });
        return data;
      });
    }, function (err) {
      setOnline(false);
      throw err;
    });
  }

  /* ---------------- DOM ---------------- */
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k === "html") n.innerHTML = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") n.addEventListener(k.slice(2), v);
      else if (v === true) n.setAttribute(k, "");
      else n.setAttribute(k, v);
    });
    append(n, kids);
    return n;
  }

  /* Children may be nested arrays. `items.map(...)` returns an array, and
     writing it inline as one child is the natural thing to do — without
     flattening it fell through to String(array) and rendered the literal text
     "[object HTMLDivElement]". Flattening here fixes that everywhere rather
     than requiring every caller to remember to spread. */
  function append(parent, kids) {
    if (kids === null || kids === undefined || kids === false) return parent;
    if (!Array.isArray(kids)) kids = [kids];
    kids.forEach(function (c) {
      if (c === null || c === undefined || c === false || c === "") return;
      if (Array.isArray(c)) { append(parent, c); return; }
      parent.appendChild(typeof c === "object" && c.nodeType ? c : document.createTextNode(String(c)));
    });
    return parent;
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

  function icon(name, cls) { return I.svg(name, cls); }

  /* Common building blocks so every tab renders the same shapes.

     Content always goes in a `.body` wrapper — that is what owns the padding
     and the gap between blocks, so a caller can append panels' worth of
     content without hand-spacing each one. `opts.icon` adds the tinted header
     chip; `opts.tone` colours it; `opts.flush` is for content that supplies
     its own padding (a tree, a code block). */
  function panel(title, kids, headExtra, opts) {
    opts = opts || {};
    var head = null;
    if (title) {
      head = el("header", {}, [
        opts.icon ? el("span", { class: "hico" + (opts.tone ? " " + opts.tone : "") }, [icon(opts.icon)]) : null,
        el("h3", { text: title }),
      ]);
      if (headExtra) append(head, headExtra);
    }
    var body = el("div", { class: "body" + (opts.flush ? " flush" : "") });
    var note = opts.help && head ? helpNote(head, body, title) : null;
    append(body, Array.isArray(kids) ? kids : [kids]);
    if (note) note(opts.help);
    var section = el("section", { class: "panel" }, [head, body]);
    if (opts.collapse && head) collapsible(section, head, opts.collapse);
    return section;
  }

  /* An ⓘ in the header that reveals one paragraph of "what is this and where
     does it live". Hidden by default and pinned to the TOP of the body, so the
     explanation is one click away instead of costing every reader the vertical
     space it takes — which is what made the Settings page a scroll marathon.

     Returns a function so the caller can insert the note after its own
     children are appended and still have it come first. */
  function helpNote(head, body, title) {
    var note = el("p", { class: "helpnote", hidden: true });
    var btn = el("button", {
      class: "btn sm iconly helpbtn", type: "button",
      title: "What " + (title || "this") + " does",
      "aria-label": "What " + (title || "this") + " does",
      "aria-expanded": "false",
      onclick: function (e) {
        e.stopPropagation();
        note.hidden = !note.hidden;
        btn.setAttribute("aria-expanded", note.hidden ? "false" : "true");
        btn.classList.toggle("on", !note.hidden);
        // Explaining a panel you cannot see would be a no-op.
        var sec = body.parentNode;
        if (!note.hidden && sec && sec.classList.contains("collapsed")) sec._setOpen(true);
      },
    }, [icon("info")]);
    head.appendChild(btn);
    return function (content) {
      append(note, Array.isArray(content) ? content : [content]);
      body.insertBefore(note, body.firstChild);
    };
  }

  /* Open/closed, remembered per id across reloads.

     One preference object rather than a key per panel: the Settings page
     lists every saved preference, and ten near-identical rows there would be
     noise about the mechanism rather than about the settings. */
  function collapsible(section, head, spec) {
    var id = spec.id;
    var open = prefs.get("panelOpen", {});
    var isOpen = Object.prototype.hasOwnProperty.call(open, id)
      ? !!open[id] : spec.open !== false;

    var chev = el("span", { class: "chev" }, [icon("chevDown")]);
    head.appendChild(chev);
    section.classList.add("collapsible");
    head.setAttribute("role", "button");
    head.setAttribute("tabindex", "0");

    function apply(next, persist) {
      isOpen = next;
      section.classList.toggle("collapsed", !isOpen);
      head.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (persist) {
        var map = prefs.get("panelOpen", {});
        map[id] = isOpen;
        prefs.set("panelOpen", map);
      }
    }

    // A click anywhere on the header toggles, EXCEPT on a control someone put
    // there — a header "Show all tabs" button must not also fold the panel.
    head.addEventListener("click", function (e) {
      if (e.target.closest("button,input,select,a,label,textarea")) return;
      apply(!isOpen, true);
    });
    head.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      apply(!isOpen, true);
    });
    chev.addEventListener("click", function () { apply(!isOpen, true); });

    section.dataset.panelId = id;
    section._setOpen = function (next) { apply(next, true); };
    apply(isOpen, false);
  }

  /* A collapsible block INSIDE a panel — same contract as `panel`'s collapse,
     one level quieter. Exists because the Assistant panel is twenty settings
     in six unrelated subjects, and a panel that is either all of it or none of
     it is not a useful choice. */
  function group(title, kids, opts) {
    opts = opts || {};
    var head = el("header", {}, [
      opts.icon ? icon(opts.icon) : null,
      el("h4", { text: title }),
    ]);
    var body = el("div", { class: "gbody" });
    var note = opts.help ? helpNote(head, body, title) : null;
    append(body, Array.isArray(kids) ? kids : [kids]);
    if (note) note(opts.help);
    var box = el("section", { class: "group" }, [head, body]);
    if (opts.id) collapsible(box, head, { id: opts.id, open: opts.open });
    return box;
  }

  function empty(title, hint, iconName) {
    return el("div", { class: "empty" }, [
      icon(iconName || "inbox"),
      el("div", { class: "etitle", text: title }),
      hint ? el("div", { class: "ehint", text: hint }) : null,
    ]);
  }

  function errbox(err) {
    return el("div", { class: "errbox" }, [String(err && err.message ? err.message : err)]);
  }

  function skeleton(n, cls) {
    var wrap = el("div", {});
    for (var i = 0; i < (n || 3); i++) wrap.appendChild(el("div", { class: "skel " + (cls || "line") }));
    return wrap;
  }

  function chip(text, kind) { return el("span", { class: "chip" + (kind ? " " + kind : ""), text: text }); }

  /** One stat tile. Clickable when `onClick` is given — and it usually should
   *  be, since a number you can't drill into is decoration. */
  function stat(value, label, opts) {
    opts = opts || {};
    return el(opts.onClick ? "button" : "div", {
      class: "stat" + (opts.tone ? " " + opts.tone : ""),
      title: opts.title || (opts.onClick ? "Open " + label : ""),
      onclick: opts.onClick || null,
    }, [
      el("div", { class: "v", text: String(value) }),
      el("div", { class: "k", text: label }),
      opts.sub ? el("div", { class: "sub", text: opts.sub }) : null,
    ]);
  }

  function stats(tiles) { return el("div", { class: "stats" }, tiles); }

  /** Horizontal bar list. Pairs every chart with a real table twin, because a
   *  chart alone is unreadable to a screen reader and unusable for copying
   *  exact numbers. */
  function bars(entries, opts) {
    opts = opts || {};
    var rows = entries.slice();
    if (opts.sort !== false) rows.sort(function (a, b) { return b[1] - a[1]; });
    if (!rows.length) return empty(opts.emptyTitle || "No data yet", opts.emptyHint);
    var max = Math.max.apply(null, rows.map(function (r) { return r[1]; })) || 1;
    var wrap = el("div", { class: "bars" });
    rows.forEach(function (r, i) {
      var pct = (100 * r[1] / max).toFixed(1);
      wrap.appendChild(el("div", { class: "bar" }, [
        el("div", { class: "blabel", title: String(r[0]), text: String(r[0]) }),
        el("div", { class: "btrack" }, [
          el("div", { class: "bfill " + (opts.colorByIndex ? catClass(i) : "c1"), style: "width:" + pct + "%" }),
        ]),
        el("div", { class: "bval", text: fmtNum(r[1]) + (opts.unit || "") }),
      ]));
    });
    var out = el("div", {}, [wrap]);
    if (opts.table !== false) out.appendChild(tableTwin(rows, opts));
    return out;
  }

  function tableTwin(rows, opts) {
    var body = el("tbody", {});
    rows.forEach(function (r) {
      body.appendChild(el("tr", {}, [
        el("td", { text: String(r[0]) }),
        el("td", { class: "num", text: fmtNum(r[1]) + (opts.unit || "") }),
      ]));
    });
    return el("details", { class: "twin" }, [
      el("summary", { class: "muted", text: "Show values" }),
      el("div", { class: "tablewrap" }, [
        el("table", { class: "dt" }, [
          el("thead", {}, [el("tr", {}, [
            el("th", { text: opts.keyLabel || "Item" }),
            el("th", { class: "num", text: opts.valLabel || "Value" }),
          ])]),
          body,
        ]),
      ]),
    ]);
  }

  function catClass(i) {
    return i < 6 ? "c" + (i + 1) : "cother";
  }

  /** Stacked proportion bar + legend, for lane flow. */
  function stack(segments) {
    var total = segments.reduce(function (s, x) { return s + x.count; }, 0);
    if (!total) return el("div", { class: "muted", text: "Empty" });
    var bar = el("div", { class: "stack", role: "img", "aria-label": segments.map(function (s) { return s.label + ": " + s.count; }).join(", ") });
    var legend = el("div", { class: "legend" });
    segments.forEach(function (s, i) {
      if (!s.count) return;
      var pct = 100 * s.count / total;
      bar.appendChild(el("div", {
        class: "seg2", style: "flex:0 0 " + pct.toFixed(2) + "%;background:var(--" + catVar(i) + ")",
        title: s.label + ": " + s.count,
      }, [pct > 7 ? String(s.count) : ""]));
      legend.appendChild(el("span", { class: "lg" }, [
        el("span", { class: "sw", style: "background:var(--" + catVar(i) + ")" }),
        s.label + " " + s.count,
      ]));
    });
    return el("div", {}, [bar, legend]);
  }

  function catVar(i) { return i < 6 ? "cat-" + (i + 1) : "cat-other"; }

  function fmtNum(n) {
    if (typeof n !== "number") return String(n);
    return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.0+$/, "");
  }

  function fmtAgo(days) {
    if (days === null || days === undefined) return "—";
    if (days === 0) return "today";
    if (days === 1) return "1 day";
    return days + " days";
  }

  function todayISO() { return new Date().toISOString().slice(0, 10); }

  /* ---------------- preferences ----------------
     View state (theme, hidden tabs, panel layout) shared by the desktop app
     and every browser tab. They are different origins with separate
     localStorage, so a theme chosen in one never reached the other (T-036).
     One synchronous interface over two stores:

       server  reads and writes a private in-memory map that hydrate() fills
               from /api/prefs; a write reaches the server a moment later, in
               one batch. Callers keep their old synchronous get/set/del.
       local   exactly the old behaviour against localStorage["console.*"]. A
               static export is always local, and a page falls back to it when
               /api/prefs is missing, fails or is slow, so an older server, a
               stopped one or a disabled plugin never blanks the UI.

     The map is empty until hydrate() settles, so nothing may read a
     preference while a script is being evaluated; callers read at render time. */

  /* A hung /api/prefs must not hold first paint: the shared request timeout is
     15 s, far too long to stare at a skeleton. After this the page proceeds as
     if the server were unreachable and a late answer arrives through onChange. */
  var HYDRATE_BOUND_MS = 3000;

  /* The server's limits (prefs_store.py: KEY_PATTERN, MAX_VALUE_BYTES). Mirrored
     so a key or value it would refuse is never sent. Change them together. */
  var PREF_KEY_RE = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/;
  var PREF_MAX_BYTES = 32768;

  /* Writes are coalesced: a drag or a keystroke calls set() many times a second
     and the server needs the last value once, so the page waits this long after
     the latest write before sending. */
  var FLUSH_MS = 250;

  /* A keepalive request (the only kind that survives the page going away) has a
     body budget of 64 KiB in the Fetch standard. This leaves headroom under it. */
  var KEEPALIVE_MAX_BYTES = 60000;

  /* Kill switch for server mode; hydrate() falls back to local mode on its own
     whenever the server cannot answer. */
  var SERVER_PREFS = true;

  var prefMode = "local";      // "server" once /api/prefs has answered
  var prefMap = {};            // server mode: the one copy of every value
  var prefRev = null;          // server mode: the rev the map reflects
  var prefImportOpen = true;   // the server's say-so; the migration reads it
  var prefListeners = [];
  var prefHydrating = null;    // the attempt in flight, shared by a second hydrate()
  var prefUndecided = true;    // no attempt has settled yet: writes are remembered
  var prefTouched = {};        // key -> {del, val}: writes made while undecided
  var prefQueue = {};          // key -> {del, val}: changes the server has not been sent
  var prefSending = [];        // batches on the wire; a batch is a prefQueue snapshot
  var prefTimer = null;        // the pending debounce
  var prefWarned = {};         // key -> true: one toast per key per page lifetime

  function prefOwn(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }

  /* Through JSON rather than a structural copy: what is held must be what would
     be sent, and a value JSON cannot carry (undefined, a function) shows up
     here as undefined instead of failing later. */
  function prefRound(val) {
    var text = JSON.stringify(val);
    return text === undefined ? undefined : JSON.parse(text);
  }

  /* Text of a JSON value with object keys sorted, the same equality the server
     applies (canonical JSON), so {a:1,b:2} and {b:2,a:1} are one value. */
  function prefCanon(val) {
    if (val === null || typeof val !== "object") return JSON.stringify(val);
    if (Array.isArray(val)) return "[" + val.map(prefCanon).join(",") + "]";
    return "{" + Object.keys(val).sort().map(function (k) {
      return JSON.stringify(k) + ":" + prefCanon(val[k]);
    }).join(",") + "}";
  }

  /* Every readable console.* entry. An entry that does not parse is not one we
     wrote, so it is left out rather than reported as a preference. */
  function prefLocalEntries() {
    var out = {};
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var name = localStorage.key(i);
        if (!name || name.indexOf("console.") !== 0) continue;
        try { out[name.slice(8)] = JSON.parse(localStorage.getItem(name)); } catch (e) { /* skip */ }
      }
    } catch (e) { /* storage blocked */ }
    return out;
  }

  function prefAll() {
    return prefMode === "server" ? prefRound(prefMap) : prefLocalEntries();
  }

  /* Key names whose value differs between two maps, sorted. */
  function prefDiff(a, b) {
    var seen = {};
    Object.keys(a).forEach(function (k) { seen[k] = true; });
    Object.keys(b).forEach(function (k) { seen[k] = true; });
    return Object.keys(seen).sort().filter(function (k) {
      return prefOwn(a, k) !== prefOwn(b, k) || prefCanon(a[k]) !== prefCanon(b[k]);
    });
  }

  function prefNotify(changed) {
    if (!changed.length) return;
    prefListeners.slice().forEach(function (fn) {
      try { fn(changed.slice()); } catch (e) { /* a bad listener must not break hydration */ }
    });
  }

  /* Until the first attempt settles the page cannot know which store wins, so a
     write is made locally (it must survive if the server never answers) and also
     remembered, to be laid over the server's map if it does. Without that a
     choice made in the first seconds would be overwritten by the hydrate. */
  function prefRemember(key, val, removed) {
    if (!prefUndecided || !SERVER_PREFS || IS_STATIC) return;
    var v;
    try { v = removed ? undefined : prefRound(val); } catch (e) { return; }
    prefTouched[key] = v === undefined ? { del: true } : { del: false, val: v };
  }

  function prefUsable(res) {
    return !!res && typeof res === "object" && typeof res.rev === "number" &&
      !!res.prefs && typeof res.prefs === "object" && !Array.isArray(res.prefs);
  }

  /* `late` is an answer that arrived after the bound: the page already painted
     from local values, so the keys that differ are announced. An answer inside
     the bound is simply what the first render reads. */
  function prefAdopt(res, late) {
    var before = late ? prefAll() : null;
    prefMap = prefRound(res.prefs);
    prefRev = res.rev;
    prefImportOpen = res.import_open !== false;
    prefUndecided = false;
    prefMode = "server";
    // What the person chose while the page could not tell which store wins is
    // now an ordinary write: laid over the server's map and queued, so it is
    // sent (and wins over the server's older value). The local copy goes, or
    // the migration would find it later and take it for an old, conflicting
    // value from a previous session.
    var touched = prefTouched;
    prefTouched = {};
    Object.keys(touched).forEach(function (k) {
      try { localStorage.removeItem("console." + k); } catch (e) { /* ignore */ }
      prefStage(k, touched[k].val, touched[k].del);
    });
    if (late) prefNotify(prefDiff(before, prefMap));
  }

  /* Never rejects, and resolves with the mode the page ended in. A 404, an
     error or an unusable reply all mean the same thing here (stay local), and
     none of them is worth a toast: this is the normal state of an older server. */
  function prefHydrate() {
    if (!SERVER_PREFS || IS_STATIC) return Promise.resolve("local");
    if (prefMode === "server") return Promise.resolve("server");
    if (prefHydrating) return prefHydrating;
    var bounded = false;
    prefUndecided = true;
    prefHydrating = new Promise(function (resolve) {
      var timer = setTimeout(function () { bounded = true; resolve(prefMode); }, HYDRATE_BOUND_MS);
      get("/api/prefs").then(function (res) {
        if (!prefUsable(res)) throw new Error("unusable reply from /api/prefs");
        prefAdopt(res, bounded);
        // The migration is part of hydration, under the same bound: a browser
        // holding theme=dark against an empty server must paint dark on this
        // first load, not default and then correct itself (CR-29).
        return prefMigrate(function () { return bounded; });
      }).catch(function () {
        if (prefMode !== "server") { prefTouched = {}; prefUndecided = false; }
      }).then(function () {
        clearTimeout(timer);
        prefHydrating = null;
        resolve(prefMode);
      });
    });
    return prefHydrating;
  }

  /* ---- write-through (server mode) ----
     set/del change the map at once and queue a delta; the server hears about it
     after FLUSH_MS of quiet, one request for everything queued. Deltas, not the
     whole map, so two clients editing different keys never overwrite each other
     (the same key is last writer wins). */

  /* UTF-8 length of a string: the unit the server's cap is written in. Counted
     by hand because TextEncoder is not in every context this file loads in. */
  function prefBytes(text) {
    var n = 0;
    for (var i = 0; i < text.length; i++) {
      var c = text.charCodeAt(i);
      n += c < 0x80 ? 1 : (c < 0x800 || (c >= 0xD800 && c <= 0xDFFF)) ? 2 : 3;
    }
    return n;
  }

  /* Why the server would refuse this key or value, or "". */
  function prefProblem(key, v) {
    if (typeof key !== "string" || !PREF_KEY_RE.test(key)) {
      return "the name must start with a letter and then use up to 63 letters, digits, '.', '_' or '-'";
    }
    if (v !== undefined) {
      var size = prefBytes(JSON.stringify(v));
      if (size > PREF_MAX_BYTES) return "its value is " + size + " bytes and the limit is " + PREF_MAX_BYTES;
    }
    return "";
  }

  function prefSay(sentence, kind) {
    try { toast(sentence, kind); } catch (e) { /* no DOM to show it in */ }
  }

  /* The one write path in server mode (and for what was remembered while
     undecided). A key or value the server would refuse stays in memory for this
     page and is never queued, so it cannot turn into a 400 that drops its
     neighbours' batch. */
  function prefStage(key, val, removed) {
    var v;
    try { v = removed ? undefined : prefRound(val); } catch (e) { return; }
    var problem = prefProblem(key, v);
    if (problem) {
      if (v === undefined) delete prefMap[key]; else prefMap[key] = v;
      delete prefQueue[key];
      if (v !== undefined && !prefWarned[key]) {
        prefWarned[key] = true;
        prefSay("Preference \"" + key + "\" is kept for this window only: " + problem + ".", "err");
      }
      return;
    }
    if (v === undefined) {
      if (!prefOwn(prefMap, key)) return;
      delete prefMap[key];
      prefQueue[key] = { del: true };
    } else {
      // Equal to what the map already holds: nothing to tell the server.
      if (prefOwn(prefMap, key) && prefCanon(prefMap[key]) === prefCanon(v)) return;
      prefMap[key] = v;
      prefQueue[key] = { del: false, val: v };
    }
    prefSchedule();
  }

  function prefPending() { return prefSending.length > 0 || Object.keys(prefQueue).length > 0; }

  function prefSchedule() {
    if (prefTimer) clearTimeout(prefTimer);
    prefTimer = setTimeout(function () { prefTimer = null; prefFlush(); }, FLUSH_MS);
  }

  function prefBody(batch) {
    var set = {}, del = [], body = {};
    Object.keys(batch).forEach(function (k) {
      if (batch[k].del) del.push(k); else set[k] = batch[k].val;
    });
    if (Object.keys(set).length) body.set = set;
    if (del.length) body.del = del;
    return body;
  }

  /* A page that is going away needs `keepalive` for its request to outlive it,
     and post() cannot send that, so this repeats its few lines. It does not touch
     the connection pill: a page being hidden is not evidence about the server. */
  function prefTransport(body, keepalive) {
    if (!keepalive) return post("/api/prefs", body);
    return fetch("/api/prefs", {
      method: "POST",
      keepalive: true,
      headers: { "Content-Type": "application/json", "X-Console-Request": "1" },
      body: JSON.stringify(body),
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw Object.assign(new Error(data.error || res.status + " " + res.statusText), { status: res.status });
        return data;
      });
    });
  }

  /* Resolves whatever happens; the outcome is handled here, not by the caller. */
  function prefSend(batch, keepalive) {
    prefSending.push(batch);
    var epoch = prefEpoch;
    var leave = function () { prefSending.splice(prefSending.indexOf(batch), 1); };
    return prefTransport(prefBody(batch), keepalive).then(function (res) {
      leave();
      // Adopt the server's rev only when this write followed the rev the page
      // knew (D-21). Otherwise another client wrote in between, `res.rev`
      // already includes that write, and believing it would hide it: keep the
      // older rev and the next heartbeat's mismatch pulls the other client's
      // change.
      if (res && typeof res.rev === "number" && res.prev === prefRev) prefRev = res.rev;
      // Entries written while this request was out were left queued.
      if (!prefTimer && Object.keys(prefQueue).length) prefSchedule();
    }, function (err) {
      leave();
      if (err && err.status === 400) {
        // The server read it and refused it; sending it again cannot succeed.
        prefSay("Preferences were not saved: " + (err.message || "the server refused them") + ".", "err");
        return;
      }
      // A Reset began while this was out: what it carried is what was cleared.
      if (epoch !== prefEpoch) return;
      // Unreachable or failing: keep every delta for the next attempt (the next
      // set, the connection coming back, the heartbeat). A key written again
      // meanwhile keeps its newer value.
      Object.keys(batch).forEach(function (k) {
        if (!prefOwn(prefQueue, k)) prefQueue[k] = batch[k];
      });
    });
  }

  /* Send what is queued now. One request at a time keeps the writes in order;
     whatever is queued when it ends is sent after it. Never rejects. */
  function prefFlush() {
    if (prefTimer) { clearTimeout(prefTimer); prefTimer = null; }
    if (IS_STATIC || prefMode !== "server" || prefSending.length) return Promise.resolve();
    if (!Object.keys(prefQueue).length) return Promise.resolve();
    var batch = prefQueue;
    prefQueue = {};
    return prefSend(batch, false);
  }

  /* The page is being hidden or closed: the debounce may never fire, so send
     now. A batch already on the wire may be cancelled by the unload, so it is
     sent again (a set is idempotent). Small enough, one keepalive request; else
     one per key; a single value too large for keepalive goes without it. */
  function prefFlushOnHide() {
    if (IS_STATIC || prefMode !== "server") return;
    if (prefTimer) { clearTimeout(prefTimer); prefTimer = null; }
    var batch = {};
    prefSending.forEach(function (b) {
      Object.keys(b).forEach(function (k) { batch[k] = b[k]; });
    });
    Object.keys(prefQueue).forEach(function (k) { batch[k] = prefQueue[k]; });
    prefQueue = {};
    var keys = Object.keys(batch);
    if (!keys.length) return;
    if (prefBytes(JSON.stringify(prefBody(batch))) <= KEEPALIVE_MAX_BYTES) { prefSend(batch, true); return; }
    keys.forEach(function (k) {
      var one = {};
      one[k] = batch[k];
      prefSend(one, prefBytes(JSON.stringify(prefBody(one))) <= KEEPALIVE_MAX_BYTES);
    });
  }

  /* ---- migration, Reset, refresh ----
     The three ways the page replaces what it holds with what the server holds.
     Each lays the changes it has not sent yet back on top (prefOverlay), so a
     write made while one of them is in flight is not lost. */

  var PREF_CLOSED_SENTENCE = "Old settings in this browser were discarded because preferences were reset.";

  /* A reset makes every batch already on the wire stale: if one fails later it
     must not be retried, or it would bring back what the person just cleared. */
  var prefEpoch = 0;

  /* Unsent local changes laid over a map the server sent. */
  function prefOverlay(map, batches) {
    batches.forEach(function (b) {
      Object.keys(b).forEach(function (k) {
        if (b[k].del) delete map[k]; else map[k] = b[k].val;
      });
    });
    return map;
  }

  /* Make the server's map the page's own. `announce` is for a page that may
     already have read the old one: the keys that differ go to the listeners. */
  function prefReplace(res, announce) {
    var before = announce ? prefAll() : null;
    prefMap = prefOverlay(prefRound(res.prefs), prefSending.concat([prefQueue]));
    prefRev = res.rev;
    if (announce) prefNotify(prefDiff(before, prefMap));
  }

  function prefLocalDrop(keys) {
    keys.forEach(function (k) {
      try { localStorage.removeItem("console." + k); } catch (e) { /* ignore */ }
    });
  }

  /* Every console.* entry, whatever it holds (a Reset clears all of them). */
  function prefLocalClear() {
    var names = [];
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var name = localStorage.key(i);
        if (name && name.indexOf("console.") === 0) names.push(name.slice(8));
      }
    } catch (e) { /* storage blocked */ }
    prefLocalDrop(names);
  }

  /* What the old C.prefs could have written: "console." plus a valid key. An
     entry that does not parse is dropped without a word (BR-16). */
  function prefLegacy() {
    var out = { values: {}, names: [] };
    var dead = [];
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var name = localStorage.key(i);
        if (!name || name.indexOf("console.") !== 0) continue;
        var key = name.slice(8);
        if (!PREF_KEY_RE.test(key)) continue;
        try { out.values[key] = JSON.parse(localStorage.getItem(name)); out.names.push(key); } catch (e) { dead.push(key); }
      }
    } catch (e) { /* storage blocked */ }
    prefLocalDrop(dead);
    return out;
  }

  function prefShort(val) {
    var text = JSON.stringify(val);
    return text.length > 40 ? text.slice(0, 40) + "…" : text;
  }

  /* One-time move of this browser's old localStorage values onto the server:
     per key, never overwriting what the server already holds (BR-3). Local
     copies are deleted only after the server acknowledges, so a lost reply
     leaves them for the next boot and the import is idempotent. Never rejects.
     `isLate()` says whether the page has already painted without these values. */
  function prefMigrate(isLate) {
    var legacy = prefLegacy();
    if (!legacy.names.length) return Promise.resolve();
    if (!prefImportOpen) {
      // A Reset closed the window: a stale browser must not bring back what
      // the person cleared.
      prefLocalDrop(legacy.names);
      prefSay(PREF_CLOSED_SENTENCE, "");
      return Promise.resolve();
    }
    return post("/api/prefs/import", { values: legacy.values }).then(function (res) {
      if (!prefUsable(res)) throw new Error("unusable reply from /api/prefs/import");
      prefReplace(res, isLate());
      if (res.closed) {
        prefImportOpen = false;
        prefLocalDrop(legacy.names);
        prefSay(PREF_CLOSED_SENTENCE, "");
        return;
      }
      var done = (res.imported || []).concat(res.skipped || []);
      (res.skipped || []).forEach(function (key) {
        prefSay("Preference \"" + key + "\" already had a shared value, so this browser's " +
          prefShort(legacy.values[key]) + " was not used.", "");
      });
      (res.rejected || []).forEach(function (r) {
        done.push(r.key);
        prefSay("Preference \"" + r.key + "\" could not be moved to the shared copy: " + r.reason + ".", "err");
      });
      prefLocalDrop(done);
    }).catch(function () { /* keys stay; the next boot tries again */ });
  }

  /* Clear every preference everywhere: the shared copy, this page's map and the
     old localStorage keys. Whatever was queued is discarded first, so a flush
     cannot write back what is being cleared. Rejects with an Error the caller
     can show; the discarded changes are then put back. */
  function prefReset() {
    prefEpoch++;
    if (prefTimer) { clearTimeout(prefTimer); prefTimer = null; }
    var dropped = prefQueue;
    prefQueue = {};
    prefTouched = {};
    if (prefMode !== "server") {
      prefLocalClear();
      return Promise.resolve();
    }
    return post("/api/prefs/reset", {}).then(function (res) {
      var before = prefAll();
      // Only what was written after reset() was called survives it.
      prefMap = prefOverlay({}, [prefQueue]);
      if (res && typeof res.rev === "number") prefRev = res.rev;
      prefImportOpen = false;
      prefLocalClear();
      prefNotify(prefDiff(before, prefMap));
    }, function (err) {
      Object.keys(dropped).forEach(function (k) {
        if (!prefOwn(prefQueue, k)) prefQueue[k] = dropped[k];
      });
      if (Object.keys(prefQueue).length) prefSchedule();
      throw err;
    });
  }

  /* Pull the shared copy now. Not while this page has changes the server has
     not seen: replacing the map would undo them. Never rejects. */
  function prefRefresh() {
    if (prefMode !== "server" || prefPending()) return Promise.resolve();
    return get("/api/prefs").then(function (res) {
      if (!prefUsable(res)) return;
      prefReplace(res, true);
      prefImportOpen = res.import_open !== false;
    }).catch(function () { /* the heartbeat asks again; the pill reports an outage */ });
  }

  var prefs = {
    get: function (key, fallback) {
      if (prefMode === "server") return prefOwn(prefMap, key) ? prefRound(prefMap[key]) : fallback;
      try {
        var raw = localStorage.getItem("console." + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set: function (key, val) {
      // Server mode holds `val` as its JSON round trip so a caller mutating it
      // afterwards cannot change what is stored behind its back. A value JSON
      // cannot carry (a cycle) is dropped, as the local store's try/catch drops it.
      if (prefMode === "server") { prefStage(key, val, false); return; }
      try { localStorage.setItem("console." + key, JSON.stringify(val)); } catch (e) { /* private mode */ }
      prefRemember(key, val, false);
    },
    del: function (key) {
      if (prefMode === "server") { prefStage(key, null, true); return; }
      try { localStorage.removeItem("console." + key); } catch (e) { /* ignore */ }
      prefRemember(key, null, true);
    },
    hydrate: prefHydrate,
    all: prefAll,
    keys: function () { return Object.keys(prefAll()); },
    mode: function () { return prefMode; },
    rev: function () { return prefMode === "server" ? prefRev : null; },
    onChange: function (fn) {
      prefListeners.push(fn);
      return function () {
        prefListeners = prefListeners.filter(function (f) { return f !== fn; });
      };
    },
    pending: prefPending,
    flush: prefFlush,
    refresh: prefRefresh,
    reset: prefReset,
  };

  /* Retry points for a failed write that need no caller: the connection coming
     back, and the page being hidden or closed (the debounce cannot be trusted to
     fire then). Registered once, here, and inert in a static export. The beacon
     API is deliberately not used: it cannot carry the X-Console-Request header
     the server requires, so every beacon would be refused. */
  onConnection(function (online) { if (online) prefFlush(); });
  if (!IS_STATIC) {
    window.addEventListener("pagehide", prefFlushOnHide);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") prefFlushOnHide();
    });
  }

  /* One glyph per status. Colour comes from a single --status-hue, chosen by
     the status class in the stylesheet, so a new status is a map entry plus
     a hue — not a new icon style. Unknown statuses get the muted circle. */
  var STATUS_GLYPHS = {
    open: ["circle", "open"], backlog: ["circle", "open"], todo: ["circle", "open"],
    "in-progress": ["play", "progress"], running: ["play", "progress"],
    working: ["play", "progress"], live: ["play", "progress"],
    verify: ["scope", "review"], "in-review": ["scope", "review"],
    blocked: ["alert", "blocked"],
    done: ["check", "done"], completed: ["check", "done"], passed: ["check", "done"],
    resolved: ["check", "done"], closed: ["check", "done"], ok: ["check", "done"],
    advanced: ["check", "done"],
    failed: ["x", "failed"], "timed-out": ["clock", "failed"], error: ["x", "failed"],
    cancelled: ["x", "muted"], ended: ["circle", "muted"],
    "scheduled-retry": ["refresh", "queued"], queued: ["queue", "queued"],
    "plan-only": ["clock", "queued"], empty: ["circle", "muted"],
    "not-run": ["circle", "muted"],
  };

  function statusGlyph(status, title) {
    var key = String(status || "").trim().toLowerCase().replace(/[\s_]+/g, "-");
    var spec = STATUS_GLYPHS[key] || ["circle", "muted"];
    var node = icon(spec[0], "sglyph sglyph-" + spec[1]);
    node.setAttribute("data-status", key || "unknown");
    if (title) {
      node.setAttribute("role", "img");
      node.setAttribute("aria-label", title);
      node.removeAttribute("aria-hidden");
    }
    return node;
  }

  /* ---------------- toasts ----------------
     Same text already on screen is not announced again. Five is the cap;
     a sixth drops the oldest. `opts.quiet` is for a change the current view
     already shows, so the toast would only repeat it. */
  var TOAST_CAP = 5;

  function armToast(t, kind) {
    if (t._fade) clearTimeout(t._fade);
    if (t._gone) clearTimeout(t._gone);
    t.style.opacity = "";
    t._fade = setTimeout(function () {
      t.style.opacity = "0";
      t._gone = setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 200);
    }, kind === "err" ? 5200 : 2600);
  }

  function toast(msg, kind, opts) {
    opts = opts || {};
    if (opts.quiet) return;
    var host = document.querySelector(".toasts");
    if (!host) { host = el("div", { class: "toasts" }); document.body.appendChild(host); }
    var key = (kind || "") + "\n" + String(msg);
    var existing = host.querySelectorAll(".toast");
    for (var i = 0; i < existing.length; i++) {
      if (existing[i].getAttribute("data-key") === key) { armToast(existing[i], kind); return; }
    }
    while (host.children.length >= TOAST_CAP) host.removeChild(host.firstChild);
    var t = el("div", { class: "toast" + (kind ? " " + kind : ""), text: msg });
    t.setAttribute("data-key", key);
    host.appendChild(t);
    armToast(t, kind);
  }

  /* ---------------- async render helper ----------------
     Every tab loads the same way: skeleton, then content or a real error
     box. Centralised so no tab invents its own loading/error look, and a
     failed fetch never leaves a blank pane with no explanation. */
  function load(host, promise, renderFn, opts) {
    opts = opts || {};
    clear(host).appendChild(skeleton(opts.skeletonRows || 4, opts.skeletonKind));
    return promise.then(function (data) {
      clear(host);
      renderFn(data, host);
      return data;
    }).catch(function (err) {
      clear(host).appendChild(errbox(err));
      return null;
    });
  }

  /* Subsequence match with a score, so "hl" finds "harness lint" — the way
     every picker worth using behaves. Earlier and tighter matches sort first
     and an exact prefix always wins. Returns 0 for no match.

     Lives here because two surfaces need it: the command palette and the
     composer's inline / @ # picker. It was written for the palette; the second
     caller is what moved it, since a copy would have drifted the moment either
     one was tuned. */
  function score(text, query) {
    if (!query) return 1;
    var haystack = String(text).toLowerCase(), needle = query.toLowerCase();
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

  /* A dropdown you can type into.

     A native <select> stops working somewhere around fifty options, and the
     model picker now gets fed a fetched catalogue — OpenRouter alone returns
     396 rows, each with a price and a context window that a <select> can only
     hide in a `title` you have to hover one row at a time to read. It was
     unusable the moment catalogue fetching landed.

     Lives in core beside `score()` rather than in the tab that needed it
     first: the same control fits every long list this console has (models,
     backends, tickets), and a second copy would drift the moment either was
     tuned — which is the argument that moved `score()` here too.

     opts: {rows:[{value,label,hint}], value, onPick, ariaLabel, placeholder,
            searchPlaceholder, emptyText, custom:{label,hint}} */
  function filterPicker(opts) {
    opts = opts || {};
    var rows = opts.rows || [];
    var value = opts.value || "";
    var shown = [];
    var index = 0;

    var wrap = el("div", { class: "fpick" });
    var btn = el("button", {
      type: "button", class: "fpick-btn",
      "aria-haspopup": "listbox", "aria-expanded": "false",
      "aria-label": opts.ariaLabel || "",
      onclick: function (e) { e.preventDefault(); toggle(); },
    });
    var input = el("input", {
      type: "text", class: "fpick-input",
      placeholder: opts.searchPlaceholder || "Type to filter…",
      "aria-label": (opts.ariaLabel || "Options") + " filter",
      // A form would submit on Enter and reload the page under the panel.
      onkeydown: function (e) { keys(e); },
      oninput: function () { render(); },
    });
    var list = el("div", { class: "fpick-list", role: "listbox",
                           "aria-label": opts.ariaLabel || "" });
    var foot = el("div", { class: "fpick-foot" });
    var panel = el("div", { class: "fpick-panel", hidden: true }, [
      el("div", { class: "fpick-search" }, [icon("search"), input]),
      list, foot,
    ]);
    append(wrap, [btn, panel]);

    function labelFor(v) {
      for (var i = 0; i < rows.length; i++) if (rows[i].value === v) return rows[i].label || v;
      // A value with no row is one that was typed — still a real choice, and
      // showing it beats showing the placeholder as if nothing were selected.
      return v || (opts.placeholder || "(none)");
    }

    function paintButton() {
      clear(btn);
      append(btn, [
        el("span", { class: "fpick-val truncate", text: labelFor(value) }),
        icon("chevDown"),
      ]);
      btn.title = value || opts.placeholder || "";
    }

    function matches() {
      var q = input.value.trim();
      var out = [];
      rows.forEach(function (r) {
        // Search the hint too: "128k" and "free" are how people actually look
        // for a model, and neither is in its id.
        var s = Math.max(score(r.label || r.value, q),
                         score(r.value, q),
                         q ? score(r.hint || "", q) * 0.4 : 0);
        if (s > 0) out.push({ row: r, s: s });
      });
      out.sort(function (a, b) { return b.s - a.s; });
      return out.map(function (o) { return o.row; });
    }

    function render() {
      shown = matches();
      var q = input.value.trim();
      // An exact-match row makes the custom escape hatch noise.
      var exact = shown.some(function (r) { return r.value === q; });
      if (opts.custom && q && !exact) {
        shown = shown.concat([{
          value: q, custom: true,
          label: (opts.custom.label || "Use") + " “" + q + "”",
          hint: opts.custom.hint || "",
        }]);
      }
      if (index >= shown.length) index = Math.max(0, shown.length - 1);
      clear(list);
      if (!shown.length) {
        list.appendChild(el("div", { class: "fpick-empty muted",
          text: opts.emptyText || "Nothing matches." }));
      }
      shown.forEach(function (r, i) {
        list.appendChild(el("div", {
          class: "cp-row fpick-row" + (i === index ? " on" : "") +
                 (r.custom ? " fpick-custom" : ""),
          role: "option", "aria-selected": String(r.value === value),
          onmousedown: function (e) { e.preventDefault(); pick(i); },
          onmouseenter: function () { index = i; mark(); },
        }, [
          r.value === value ? icon("check") : el("span", { class: "fpick-gap" }),
          el("span", { class: "cp-label", text: r.label || r.value }),
          r.hint ? el("span", { class: "cp-hint muted", text: r.hint }) : null,
        ]));
      });
      foot.textContent = q
        ? shown.length + " of " + rows.length
        : rows.length + (rows.length === 1 ? " option" : " options");
    }

    function mark() {
      var kids = list.childNodes;
      for (var i = 0; i < kids.length; i++) {
        if (kids[i].classList) kids[i].classList.toggle("on", i === index);
      }
      var cur = kids[index];
      if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: "nearest" });
    }

    function pick(i) {
      var r = shown[i];
      if (!r) return;
      value = r.value;
      paintButton();
      close();
      if (opts.onPick) opts.onPick(value, r);
    }

    function keys(e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!shown.length) return;
        index = (index + (e.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length;
        mark();
      } else if (e.key === "Enter") {
        e.preventDefault();
        pick(index);
      } else if (e.key === "Escape") {
        e.preventDefault();
        close();
        btn.focus();
      }
    }

    function outside(e) { if (!wrap.contains(e.target)) close(); }

    function open() {
      panel.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      input.value = "";
      index = 0;
      render();
      /* Flip above the control when there is not room below it. Measured
         rather than assumed: this control is reused, and where it sits on the
         page is the caller's business, not something to hard-code here. */
      var box = btn.getBoundingClientRect();
      var need = Math.min(panel.offsetHeight || 300, 300);
      wrap.classList.toggle("up",
        box.bottom + need > window.innerHeight && box.top > need);
      input.focus();
      // Registered only while open, and removed on close — a listener per
      // picker left on the document is how a long session gets slow.
      document.addEventListener("mousedown", outside, true);
    }

    function close() {
      if (panel.hidden) return;
      panel.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      document.removeEventListener("mousedown", outside, true);
    }

    function toggle() { if (panel.hidden) open(); else close(); }

    paintButton();
    wrap.setValue = function (v) { value = v || ""; paintButton(); };
    wrap.setRows = function (next) { rows = next || []; paintButton(); if (!panel.hidden) render(); };
    return wrap;
  }

  return {
    IS_STATIC: IS_STATIC,
    score: score,
    filterPicker: filterPicker,
    tab: tab, tabImpl: tabImpl, tabIds: tabIds,
    holdReload: holdReload, reloadHeld: reloadHeld,
    get: get, post: post,
    el: el, append: append, clear: clear, icon: icon,
    panel: panel, group: group, empty: empty, errbox: errbox, skeleton: skeleton, chip: chip,
    stat: stat, stats: stats,
    bars: bars, stack: stack, catClass: catClass, catVar: catVar,
    fmtNum: fmtNum, fmtAgo: fmtAgo, todayISO: todayISO,
    prefs: prefs, toast: toast, statusGlyph: statusGlyph, load: load,
    inflightCount: inflightCount,
    onConnection: onConnection, isOnline: isOnline,
  };
})();
