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
        if (!res.ok) throw new Error(data.error || res.status + " " + res.statusText);
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
    append(body, Array.isArray(kids) ? kids : [kids]);
    return el("section", { class: "panel" }, [head, body]);
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

  /* ---------------- preferences (browser-local) ---------------- */
  var prefs = {
    get: function (key, fallback) {
      try {
        var raw = localStorage.getItem("console." + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set: function (key, val) {
      try { localStorage.setItem("console." + key, JSON.stringify(val)); } catch (e) { /* private mode */ }
    },
    del: function (key) {
      try { localStorage.removeItem("console." + key); } catch (e) { /* ignore */ }
    },
  };

  /* ---------------- toasts ---------------- */
  function toast(msg, kind) {
    var host = document.querySelector(".toasts");
    if (!host) { host = el("div", { class: "toasts" }); document.body.appendChild(host); }
    var t = el("div", { class: "toast" + (kind ? " " + kind : ""), text: msg });
    host.appendChild(t);
    setTimeout(function () {
      t.style.opacity = "0";
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 200);
    }, kind === "err" ? 5200 : 2600);
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

  return {
    IS_STATIC: IS_STATIC,
    score: score,
    tab: tab, tabImpl: tabImpl, tabIds: tabIds,
    get: get, post: post,
    el: el, append: append, clear: clear, icon: icon,
    panel: panel, empty: empty, errbox: errbox, skeleton: skeleton, chip: chip,
    stat: stat, stats: stats,
    bars: bars, stack: stack, catClass: catClass, catVar: catVar,
    fmtNum: fmtNum, fmtAgo: fmtAgo, todayISO: todayISO,
    prefs: prefs, toast: toast, load: load,
    inflightCount: inflightCount,
    onConnection: onConnection, isOnline: isOnline,
  };
})();
