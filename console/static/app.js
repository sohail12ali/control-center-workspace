/* Router + shell. Intersects the server's tab manifest (/api/config) with the
   tabs that registered client-side, applies the user's own hide list, and
   renders whichever is active.

   The router knows no tab by name. A tab appears because (a) its server
   plugin is enabled, so it's in the manifest, and (b) its JS file called
   Console.tab(). Either half missing means it silently isn't offered, which
   is what makes `enabled = false` in plugins.toml a complete off switch. */
(function (C) {
  "use strict";

  var state = { manifest: [], active: null, cfg: null };

  /* ---------------- drawer ----------------
     One drawer for the whole app, owned here rather than by each tab, so
     Escape/scrim/back-button behaviour is identical everywhere. */
  var drawer = (function () {
    var scrim = null, panel = null, lastFocus = null;

    function close() {
      if (!panel) return;
      [scrim, panel].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
      scrim = panel = null;
      document.removeEventListener("keydown", onKey);
      if (lastFocus && lastFocus.isConnected) lastFocus.focus();
    }

    function onKey(e) { if (e.key === "Escape") { e.stopPropagation(); close(); } }

    function open(title, subtitle) {
      close();
      lastFocus = document.activeElement;
      scrim = C.el("button", { class: "scrim", "aria-label": "Close panel", onclick: close });
      var body = C.el("div", { class: "dbody" });
      panel = C.el("aside", { class: "drawer", role: "dialog", "aria-modal": "true", "aria-label": title }, [
        C.el("header", {}, [
          C.el("div", { class: "dtitle" }, [
            C.el("h2", { text: title }),
            subtitle ? C.el("div", { class: "muted", text: subtitle }) : null,
          ]),
          C.el("button", { class: "btn sm iconly", "aria-label": "Close", onclick: close }, [C.icon("x")]),
        ]),
        body,
      ]);
      document.body.appendChild(scrim);
      document.body.appendChild(panel);
      document.addEventListener("keydown", onKey);
      panel.querySelector("button").focus();
      return body;
    }

    return { open: open, close: close };
  })();

  /* ---------------- nav ---------------- */
  function buildNav() {
    var nav = C.clear(document.getElementById("tabs"));
    var hidden = C.prefs.get("hiddenTabs", []);
    visibleTabs().forEach(function (t) {
      var btn = C.el("button", {
        class: "tab", role: "tab", id: "tab-" + t.id,
        "data-tab": t.id,
        "aria-selected": String(t.id === state.active),
        title: t.label,
        onclick: function () { go(t.id); },
      }, [
        t.icon ? C.icon(t.icon) : null,
        C.el("span", { class: "tlab-full", text: t.label }),
        C.el("span", { class: "tlab-short", text: t.short || t.label }),
      ]);
      if (t.badge) {
        btn.appendChild(C.el("span", { class: "tbadge", "data-badge-for": t.id, text: "" }));
      }
      nav.appendChild(btn);
    });
    // Keyboard: arrows move between tabs, matching the tablist role we claim.
    nav.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var ids = visibleTabs().map(function (t) { return t.id; });
      var i = ids.indexOf(state.active);
      if (i < 0) return;
      var next = ids[(i + (e.key === "ArrowRight" ? 1 : ids.length - 1)) % ids.length];
      go(next);
      var b = nav.querySelector('[data-tab="' + next + '"]');
      if (b) b.focus();
      e.preventDefault();
    });
  }

  function visibleTabs() {
    var hidden = C.prefs.get("hiddenTabs", []);
    return state.manifest.filter(function (t) {
      if (t.always) return true;
      if (hidden.indexOf(t.id) !== -1) return false;
      // A needs_live tab is meaningless in a static export.
      if (C.IS_STATIC && t.needs_live) return false;
      // No client implementation registered → don't offer a dead tab.
      return !!C.tabImpl(implIdFor(t));
    });
  }

  /* Board tabs share one implementation ("board"), parameterised by kind —
     the manifest can list any number of boards without a JS file each. */
  function implIdFor(t) { return t.id.indexOf("board:") === 0 ? "board" : t.id; }

  function go(id) {
    var tabs = visibleTabs();
    var target = tabs.filter(function (t) { return t.id === id; })[0] || tabs[0];
    if (!target) return;
    drawer.close();

    var prev = state.active ? C.tabImpl(implIdFor({ id: state.active })) : null;
    if (prev && prev.onLeave) { try { prev.onLeave(); } catch (e) { /* keep navigating */ } }

    state.active = target.id;
    if (window.location.hash !== "#" + target.id) {
      history.replaceState(null, "", "#" + target.id);
    }
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.setAttribute("aria-selected", String(b.dataset.tab === target.id));
    });

    var host = C.clear(document.getElementById("view"));
    var impl = C.tabImpl(implIdFor(target));
    /* A tab declares its own layout need rather than the router guessing from
       the id: "flush" = the tab supplies its own padding (boards),
       "app" = give it the exact remaining viewport height and let it
       distribute it (agents). Default is the padded scrolling page. */
    host.className = impl.layout || "";
    document.title = target.label + " — " + (state.cfg.title || "Delivery Console");
    try {
      impl.render(host, { tab: target, config: state.cfg, drawer: drawer, go: go, refreshBadges: refreshBadges });
    } catch (err) {
      C.clear(host).appendChild(C.errbox(err));
    }
  }

  /* ---------------- badges ----------------
     Counts live on the nav so you can see work waiting on a tab you're not
     looking at. Two rules:

     1. Failures are silent. A badge is a nicety and a broken one must never
        block the tab it decorates.
     2. The requests run ONE AT A TIME, not in parallel. Fired together they
        were five simultaneous connections; with an event stream also open
        that reached the browser's ~6-per-origin ceiling, and the tab's own
        data request then queued behind them and appeared to hang. Badges are
        background work, so they take the slow lane. */
  var badgeRun = 0;

  function refreshBadges() {
    var myRun = ++badgeRun;
    var set = function (id, text, alert) {
      var b = document.querySelector('[data-badge-for="' + id + '"]');
      if (!b) return;
      b.textContent = text ? String(text) : "";
      b.classList.toggle("alert", !!alert);
      b.style.display = text ? "" : "none";
    };

    var jobs = [];
    state.manifest.filter(function (t) { return t.group === "boards"; }).forEach(function (t) {
      jobs.push(function () {
        return C.get("/api/board/" + t.kind).then(function (view) {
          set(t.id, view.lanes.reduce(function (n, l) {
            return n + (l.terminal ? 0 : l.cards.length);
          }, 0) || "");
        });
      });
    });
    if (hasTab("todos")) {
      jobs.push(function () {
        // Filtered client-side as well as in the query: a static export maps
        // every /api/todos request to one file, so the query alone would make
        // this badge count closed items too.
        return C.get("/api/todos?status=open").then(function (items) {
          set("todos", items.filter(function (t) { return t.status === "open"; }).length || "");
        });
      });
    }
    if (hasTab("agents") && !C.IS_STATIC) {
      jobs.push(function () {
        return C.get("/api/agents/chats").then(function (d) {
          var busy = (d.chats || []).filter(function (c) { return c.busy; }).length;
          set("agents", busy || "", busy > 0);
        });
      });
    }
    if (hasTab("work") && !C.IS_STATIC) {
      jobs.push(function () {
        return C.get("/api/work/day?date=" + C.todayISO()).then(function (res) {
          var total = (res.sheets || []).reduce(function (n, s) { return n + s.total_hours; }, 0);
          set("work", total ? C.fmtNum(total) + "h" : "");
        });
      });
    }

    // Sequential chain; a superseded run stops so two timers can't interleave.
    return jobs.reduce(function (chain, job) {
      return chain.then(function () {
        if (myRun !== badgeRun) return null;
        return job().catch(function () { return null; });
      });
    }, Promise.resolve());
  }

  function hasTab(id) {
    return state.manifest.some(function (t) { return t.id === id; }) && !!C.tabImpl(id);
  }

  /* ---------------- connection pill ----------------
     Reflects live state, not a one-time verdict at boot. It used to be set
     twice during startup and never again, so a console whose server had since
     stopped went on cheerfully reporting "live" — the one thing the indicator
     exists to rule out.

     Two inputs keep it honest:
       - every request updates it (core.js distinguishes a rejected fetch from
         an HTTP error, so a 404 does not read as "server down")
       - a heartbeat, because a console nobody is clicking makes no requests,
         and a server that dies during that quiet period must still be noticed */
  var HEARTBEAT_MS = 15000;
  var heartbeat = null;

  function markConnection(ok, label) {
    var pill = document.getElementById("connPill");
    var text = document.getElementById("connText");
    if (!pill || !text) return;
    pill.classList.toggle("err", !ok && !C.IS_STATIC);
    pill.classList.toggle("off", C.IS_STATIC);
    text.textContent = label || (C.IS_STATIC ? "snapshot" : (ok ? "live" : "offline"));
    pill.title = C.IS_STATIC
      ? "A static snapshot — there is no server behind this page."
      : (ok ? "Connected to the console server."
            : "Cannot reach the console server. Start it with: python console/kanban.py serve");
  }

  function watchConnection() {
    if (C.IS_STATIC) { markConnection(false, "snapshot"); return; }
    C.onConnection(function (online) { markConnection(online); });
    if (heartbeat) clearInterval(heartbeat);
    heartbeat = setInterval(function () {
      // Cheapest endpoint that proves the server is answering. Failures are
      // swallowed here: core.js has already flipped the pill, and a toast per
      // failed heartbeat would be noise on a server that is simply stopped.
      C.get("/api/config").catch(function () {});
    }, HEARTBEAT_MS);
  }

  /* ---------------- global keys ---------------- */
  function bindKeys() {
    document.addEventListener("keydown", function (e) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || ""));
      /* Ctrl/Cmd-K works even while typing — it is the one shortcut whose
         whole point is "get me out of here and somewhere else". */
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (C.palette) C.palette.open();
      } else if (e.key === "/" && !typing) {
        e.preventDefault();
        document.getElementById("search").focus();
      } else if (e.key === "r" && !typing && !e.metaKey && !e.ctrlKey) {
        go(state.active);
      } else if (e.key >= "1" && e.key <= "9" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        var t = visibleTabs()[Number(e.key) - 1];
        if (t) { e.preventDefault(); go(t.id); }
      }
    });

    document.getElementById("refreshBtn").appendChild(C.icon("refresh"));
    document.getElementById("refreshBtn").addEventListener("click", function () {
      go(state.active);
      refreshBadges();
    });

    var search = document.getElementById("search");
    var timer = null;
    search.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { runSearch(search.value.trim()); }, 160);
    });
    search.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { search.value = ""; search.blur(); runSearch(""); }
    });

    window.addEventListener("hashchange", function () {
      var id = window.location.hash.slice(1);
      if (id && id !== state.active) go(id);
    });
  }

  /* Search jumps straight to a ticket if the query matches an id, otherwise
     it filters the active board in place (board.js owns that filter). */
  function runSearch(q) {
    var impl = C.tabImpl(implIdFor({ id: state.active || "" }));
    if (impl && impl.onSearch) impl.onSearch(q);
    else if (q) C.toast("Search applies to the board tabs.", "");
  }

  /* ---------------- boot ---------------- */
  C.get("/api/config").then(function (cfg) {
    state.cfg = cfg;
    state.manifest = cfg.tabs || [];
    document.getElementById("brandTitle").textContent = cfg.title || "Delivery Console";
    document.getElementById("brandSub").textContent = cfg.subtitle || "";
    markConnection(true);
    watchConnection();

    applyTheme(C.prefs.get("theme", "system"));
    buildNav();
    bindKeys();

    var wanted = window.location.hash.slice(1);
    var ids = visibleTabs().map(function (t) { return t.id; });
    go(ids.indexOf(wanted) !== -1 ? wanted : ids[0]);
    refreshBadges();
    if (!C.IS_STATIC) setInterval(refreshBadges, 30000);
  }).catch(function (err) {
    markConnection(false, "no server");
    // Keep watching even though boot failed: starting the server should bring
    // the console back without the user having to know to reload.
    watchConnection();
    C.onConnection(function (online) { if (online) window.location.reload(); });
    C.clear(document.getElementById("view")).appendChild(
      C.el("div", { class: "empty" }, [
        C.icon("alert"),
        C.el("div", { class: "etitle", text: "Cannot reach the console server" }),
        C.el("div", { class: "ehint", text: String(err.message) }),
        C.el("div", { class: "ehint", text: "Start it with:  python console/kanban.py serve" }),
        C.el("div", { class: "ehint muted", text: "This page will reload itself once the server answers." }),
      ])
    );
  });

  /* Theme is applied here (not settings.js) so it lands before first paint
     of the tab content, and works even if the Settings tab never loads. */
  function applyTheme(theme) {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }

  window.ConsoleApp = { go: go, applyTheme: applyTheme, refreshBadges: refreshBadges, drawer: drawer,
                        manifest: function () { return state.manifest; }, rebuildNav: buildNav };
})(window.Console);
