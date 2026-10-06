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
    var scrim = null, panel = null, lastFocus = null, handle = null, modeBound = false;
    var docked = false;

    /* The one place that decides docked or modal. T-037 D-1 / Q1: above 900px
       the dock REPLACES the overlay (accepted default, pending user
       confirmation); an opt-in toggle later is a one-expression change here. */
    function dockMode() { return window.matchMedia(C.splitter.WIDE).matches; }

    function close() {
      if (!panel) return;
      [scrim, panel].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
      scrim = panel = handle = null;
      docked = false;
      document.getElementById("app").classList.remove("has-dock");
      /* a removed handle never notices itself: let the registry end any drag */
      C.splitter.reapplyAll();
      document.removeEventListener("keydown", onKey);
      if (lastFocus && lastFocus.isConnected) lastFocus.focus();
    }

    /* T-037 D-10: modal = Esc anywhere closes (as before). Docked = the panel
       sits beside live content, so Esc closes it only from inside the panel; Esc
       in the board search, on a card or in the topbar is left alone, not even
       stopped. An Esc in a drawer field still reverts the field (board.js) and
       reaches here, so it closes too. */
    function onKey(e) {
      if (e.key !== "Escape") return;
      if (docked && !(panel && panel.contains(e.target))) return;
      e.stopPropagation();
      close();
    }

    /* Put the open panel in its mode: docked = a grid child of #app, no scrim,
       role complementary, resize handle; modal = on <body> with scrim, role
       dialog + aria-modal. The same node is moved, never rebuilt, so the body
       and any half-typed field survive a live switch. Moving a node blurs its
       focused descendant, so focus is saved and put back. */
    function mount(isDocked) {
      var app = document.getElementById("app"), f = document.activeElement;
      var had = !!f && panel.contains(f);
      if (handle && handle.parentNode) handle.parentNode.removeChild(handle);
      handle = null;
      if (scrim && scrim.parentNode) scrim.parentNode.removeChild(scrim);
      scrim = null;
      docked = isDocked;
      app.classList.toggle("has-dock", isDocked);
      if (isDocked) {
        panel.setAttribute("role", "complementary");
        panel.removeAttribute("aria-modal");
        app.appendChild(panel);
        handle = C.splitter({
          host: panel, pane: panel, owner: app, dir: -1, cssVar: "dock", key: "dock.w",
          min: 320, max: 720, flexPane: function () { return document.getElementById("view"); },
          flexMin: 360, label: "Resize ticket panel",
        });
      } else {
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        scrim = C.el("button", { class: "scrim", "aria-label": "Close panel", onclick: close });
        document.body.appendChild(scrim);
        document.body.appendChild(panel);
      }
      C.splitter.reapplyAll();
      if (had && f.isConnected) f.focus();
    }

    function titleNodes(title, subtitle) {
      return [
        C.el("h2", { text: title }),
        subtitle ? C.el("div", { class: "muted", text: subtitle }) : null,
      ];
    }

    /* Repeat open() while a panel is up (an edit re-opens the ticket to refresh
       it): same aside, same width, same restore target, no slide-in replay.
       Only the title and the body change, and the body is a NEW node: the old
       one is left detached, so a slow response from an earlier call can only
       write into an orphan and never over newer content (T-037 D-9). Focus
       that sat in the replaced body goes to Close, as a refresh always ended. */
    function refresh(title, subtitle) {
      var old = panel.querySelector(".dbody"), f = document.activeElement;
      var had = !!f && old.contains(f);
      var body = C.el("div", { class: "dbody" });
      var head = C.clear(panel.querySelector(".dtitle"));
      titleNodes(title, subtitle).forEach(function (n) { if (n) head.appendChild(n); });
      panel.setAttribute("aria-label", title);
      panel.replaceChild(body, old);
      if (had) panel.querySelector("button").focus();
      return body;
    }

    function open(title, subtitle) {
      if (panel) return refresh(title, subtitle);
      lastFocus = document.activeElement;
      var body = C.el("div", { class: "dbody" });
      panel = C.el("aside", { class: "drawer", "aria-label": title }, [
        C.el("header", {}, [
          C.el("div", { class: "dtitle" }, titleNodes(title, subtitle)),
          C.el("button", { class: "btn sm iconly", "aria-label": "Close", onclick: close }, [C.icon("x")]),
        ]),
        body,
      ]);
      mount(dockMode());
      if (!modeBound) {
        modeBound = true;
        var mq = window.matchMedia(C.splitter.WIDE);
        /* F-8: the media-query change event alone was not enough (a browser
           resize flipped the CSS but left the aside docked in JS), so a window
           resize re-checks the same dockMode(). Re-mount only on a real flip. */
        var sync = function () {
          if (panel && docked !== dockMode()) mount(dockMode());
        };
        if (mq.addEventListener) mq.addEventListener("change", sync);
        window.addEventListener("resize", sync);
      }
      document.addEventListener("keydown", onKey);
      panel.querySelector("button").focus();
      return body;
    }

    return { open: open, close: close };
  })();

  function inShell() {
    return document.documentElement.classList.contains("in-shell");
  }

  /* T-016 FR-1: native shell opens on Assistant. The server NAV_ORDER cannot
     see html.in-shell (the class is client-only), so the browser keeps the
     shipped Overview-first list and only this sort moves Assistant first. */
  function orderManifest(tabs) {
    tabs = (tabs || []).slice();
    if (!inShell()) return tabs;
    var home = [], rest = [];
    tabs.forEach(function (t) {
      if (t.id === "assistant") home.push(t);
      else rest.push(t);
    });
    return home.concat(rest);
  }

  /* ---------------- nav ---------------- */
  // What hiddenTabs held the last time the nav was built, as JSON text: a change
  // picked up from the shared preferences rebuilds the nav only if it differs.
  var navHidden = null;

  function buildNav() {
    var nav = C.clear(document.getElementById("tabs"));
    var hidden = C.prefs.get("hiddenTabs", []);
    navHidden = JSON.stringify(hidden);
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
    // C.clear returns this same #tabs node every time, so a listener added on
    // each rebuild would stack and one arrow key would move several tabs. A
    // marker on the node keeps it to one, however often the nav is rebuilt.
    if (!nav.hasAttribute("data-keys-bound")) {
      nav.setAttribute("data-keys-bound", "1");
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
    if (hasTab("overview")) {
      jobs.push(function () {
        return C.get("/api/overview").then(function (d) {
          var c = (d.attention && d.attention.counts) || {};
          var n = (c.blocked || 0) + (c.stale || 0) + (c.unowned || 0)
            + (c.questions || 0) + (c.approvals || 0) + (c.runs || 0);
          set("overview", n || "", n > 0);
        });
      });
    }
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
    heartbeat = setInterval(probe, HEARTBEAT_MS);
    watchVersion();
  }

  /* ---------------- shared preferences ----------------
     The heartbeat already fetches /api/config, which carries the preferences'
     revision, so keeping this page in step with the app and every other browser
     costs no extra request unless something actually changed. */

  /* A beat that arrives while this page has changes the server has not seen
     retries them (their send may have failed) and does not pull: pulling would
     replace the map and undo them. Otherwise a different revision means another
     client wrote, so pull. Compared with !== only: a revision is an identity,
     not an ordering, and a server whose file was reset can go down as well as
     up. An absent prefs_rev (an older server, or the plugin switched off) means
     nothing to compare. */
  function onHeartbeat(cfg) {
    checkVersion(cfg);    // first: the pending-writes return below must not skip it
    maybeReload(cfg);     // same reason, and every trigger arrives here through probe()
    if (C.prefs.pending()) { C.prefs.flush(); return; }
    if (cfg && cfg.prefs_rev !== undefined && cfg.prefs_rev !== C.prefs.rev()) C.prefs.refresh();
  }

  /* What a pickup changes on screen. Only the two preferences with a global
     visual effect are applied; every other key takes effect the next time its
     tab renders. Never go(): the active tab keeps what the person typed into it,
     even if it was just hidden. The nav is rebuilt only when hiddenTabs really
     differs, because each rebuild replaces every tab button. */
  function bindPrefs() {
    C.prefs.onChange(function (changed) {
      if (changed.indexOf("theme") !== -1) applyTheme(C.prefs.get("theme", "system"));
      if (changed.indexOf("hiddenTabs") !== -1 &&
          JSON.stringify(C.prefs.get("hiddenTabs", [])) !== navHidden) buildNav();
    });
  }

  /* ---------------- new UI version ----------------
     The server stamps the files it serves as `ui_version` in /api/config. A page
     keeps the stamp it booted with and compares every later answer, so the check
     adds no request and no timer of its own: the heartbeat already asks. A
     differing stamp shows a notice and sets `versionPending`, which the rules for
     reloading by itself (below) use. Nothing here runs in a static export. */

  // A usable stamp is a non-empty string; anything else counts as absent.
  function versionOf(cfg) {
    return cfg && typeof cfg.ui_version === "string" ? cfg.ui_version : "";
  }

  /* Whether the server now serves a different UI than this page booted with. The
     boot stamp is read from state.cfg (set once at boot), not copied.
       - No stamp in the answer says nothing: a server that lost the field, or
         never had it, must not move anybody (present then absent is ignored,
         absent both times is nothing).
       - A page that booted WITHOUT a stamp met a server that had not restarted
         yet, so it runs on local preferences; the first stamp it ever sees counts
         as a change, which is what moves it onto the new server. */
  var versionPending = false;

  function checkVersion(cfg) {
    if (C.IS_STATIC || !state.cfg) return;
    var now = versionOf(cfg);
    if (!now) return;
    var boot = versionOf(state.cfg);
    if (!boot) versionPending = true;       // absent, then present
    else versionPending = now !== boot;     // present, and different
    showNotice(versionPending);
  }

  /* The same request the heartbeat makes, asked out of turn when a reason to
     look appears. Cheapest endpoint that proves the server is answering. Failures
     are swallowed: core.js has already flipped the pill, and a toast per failed
     check would be noise on a server that is simply stopped. */
  function probe() {
    return C.get("/api/config").then(onHeartbeat).catch(function () {});
  }

  /* Look again when the connection comes back or the window becomes visible, not
     only on the next beat. Registered once: watchConnection runs a second time
     when boot fails after it ran. */
  var versionWatched = false;

  function watchVersion() {
    if (versionWatched) return;
    versionWatched = true;
    watchActivity();
    C.onConnection(function (online) { if (online) probe(); });
    document.addEventListener("visibilitychange", function () { if (!document.hidden) probe(); });
  }

  /* The notice is persistent and non-modal on purpose, and not a toast: a toast
     fades in seconds and the reload may be a minute away. */
  var NOTICE_TEXT = {
    ready: "A new version of the console is ready. It reloads when you pause.",
    busy: "A new version of the console is ready. Unsaved text will be lost if you reload now; it reloads by itself when you are done.",
    paused: "A new version of the console is ready. Automatic reload is paused after several reloads in a row; use Reload now when you are ready.",
  };
  var notice = null, noticeText = null;

  function buildNotice() {
    noticeText = C.el("span");
    notice = C.el("div", { class: "ui-notice", role: "status" }, [
      noticeText,
      C.el("button", { class: "btn sm", type: "button", text: "Reload now", onclick: reloadNow }),
    ]);
    document.body.appendChild(notice);
    // Text goes in once the element is in the page: a screen reader announces a
    // change inside a status region, not the region's first paint.
    setNoticeText("ready");
  }

  function showNotice(show) {
    if (!show) { if (notice) notice.hidden = true; return; }
    if (!notice) buildNotice();
    notice.hidden = false;
  }

  /* mode: "ready" | "busy" | "paused". Written only when it differs, because
     rewriting identical text would make the status region announce it again on
     every beat. */
  function setNoticeText(mode) {
    if (!noticeText) return;
    var text = NOTICE_TEXT[mode] || NOTICE_TEXT.ready;
    if (noticeText.textContent !== text) noticeText.textContent = text;
  }

  /* Reload now is the person's own decision (D-20): it never waits for the busy
     rules and never counts against the limit on automatic reloads. */
  function reloadNow() { window.location.reload(); }

  /* ---- reloading by itself, only when it cannot cost anyone their work ----
     The heartbeat is the only clock: "idle" is a timestamp compared at each beat,
     not a timer, so a reload lands within one beat (15 s) of the page becoming
     free. */
  var IDLE_MS = 30000;
  var lastActive = Date.now();
  var typedInto = new WeakSet();

  /* Capture phase, so a handler that stops propagation cannot hide the person.
     pointermove is left out on purpose: a mouse resting on a jittery desk, or a
     pointer parked over the window, would keep the page "active" forever. */
  function watchActivity() {
    ["keydown", "pointerdown", "wheel", "touchstart"].forEach(function (type) {
      document.addEventListener(type, function () { lastActive = Date.now(); }, true);
    });
    /* Only a real keystroke or paste marks a field as typed-in. Code that fills
       a field (Settings sets .value on render) fires no trusted event, so those
       fields stay "not typed". */
    document.addEventListener("input", function (e) {
      if (e.isTrusted && e.target && typeof e.target === "object") typedInto.add(e.target);
    }, true);
  }

  function isTextField(el) {
    if (!el || !el.tagName) return false;
    if (el.tagName === "TEXTAREA") return true;
    if (el.tagName === "INPUT") return /^(text|search|url|email|tel|password|number)$/.test(el.type || "text");
    return !!el.isContentEditable;
  }

  function hasText(el) {
    var text = (el.tagName === "TEXTAREA" || el.tagName === "INPUT") ? el.value : el.textContent;
    return String(text || "").trim() !== "";
  }

  /* Text a reload would throw away. Deliberately not "value !== defaultValue":
     Settings fills inputs with .value = ..., which would read as edited and
     keep that tab from ever reloading.
       - a textarea is a draft by nature, however its text got there: dictation
         and the / @ # picker assign .value and fire no input event
       - a text input or editable region counts only if the person typed in it
         and it still has text
       - the focused field counts when it has text (the caret is in it) */
  function draftOpen() {
    var i, list = document.querySelectorAll("textarea");
    for (i = 0; i < list.length; i++) if (hasText(list[i])) return true;
    list = document.querySelectorAll("input, [contenteditable]");
    for (i = 0; i < list.length; i++) {
      if (typedInto.has(list[i]) && isTextField(list[i]) && hasText(list[i])) return true;
    }
    var focused = document.activeElement;
    return !!(focused && isTextField(focused) && hasText(focused));
  }

  /* Busy is read from the page itself, not from a list of tabs, so a new tab
     is protected without anyone remembering to register it. The class names are
     owned elsewhere: app.js (.drawer), onboarding-wizard.js (.ob-scrim) and
     palette.js (.cp-scrim, with .on while open). A test pins each against its
     owner, so a rename fails there instead of in front of a user. */
  function isBusy() {
    if (draftOpen()) return true;
    if (document.querySelector(".drawer")) return true;
    if (document.querySelector(".ob-scrim")) return true;
    if (document.querySelector(".cp-scrim.on")) return true;
    var voice = window.ConsoleVoice;
    if (voice && (voice.listening() || voice.speaking())) return true;
    return C.reloadHeld();      // drafts that live off-screen, registered by tabs
  }

  /* Called on every answer to /api/config, whatever caused the request. An
     answer without a stamp is not evidence of anything (a stopped or restarting
     server answers nothing; an older one has no stamp), so it never reloads: a
     server flapping with unchanged files must cause no reload, and comparing
     against the boot stamp already guarantees that for answers that do have one.
     A hidden window has nobody to protect from a reload, so it goes at the next
     check; the idle clock stays as the fallback in case a window that is hidden
     (a tray app) is never reported as hidden. */
  function maybeReload(cfg) {
    if (!versionPending || !versionOf(cfg)) return;
    if (isBusy()) { setNoticeText(reloadPaused() ? "paused" : "busy"); return; }
    if (document.hidden || Date.now() - lastActive >= IDLE_MS) autoReload();
    else setNoticeText(reloadPaused() ? "paused" : "ready");
  }

  /* ---- the loop guard ----
     A reload that does not cure the mismatch (files still changing, a stamp that
     never settles) would otherwise repeat every 30 s for ever. So automatic
     reloads are counted, and the third one inside five minutes is the last:
     after that the notice says so and only Reload now works. It re-arms by
     itself because only timestamps are kept and old ones fall out of the
     window; no target version is stored, since a count bounds every kind of loop
     and a stamp comparison would not. sessionStorage, not localStorage: it
     survives a reload but belongs to this tab alone. */
  var RELOAD_KEY = "console-reload";
  var RELOAD_LIMIT = 3;
  var RELOAD_WINDOW_MS = 300000;

  /* Timestamps of automatic reloads still inside the window; null when storage
     cannot be read at all. A corrupt value reads as none. */
  function recentReloads() {
    var raw, list, now = Date.now();
    try { raw = window.sessionStorage.getItem(RELOAD_KEY); } catch (e) { return null; }
    try { list = JSON.parse(raw || "[]"); } catch (e) { list = []; }
    if (!Array.isArray(list)) return [];
    return list.filter(function (at) { return typeof at === "number" && now - at < RELOAD_WINDOW_MS; });
  }

  /* No readable storage counts as paused: a guard that cannot count cannot bound
     a loop, and a counter held in memory would not survive the reload it is
     meant to count. */
  function reloadPaused() {
    var recent = recentReloads();
    return !recent || recent.length >= RELOAD_LIMIT;
  }

  function autoReload() {
    var recent = recentReloads();
    if (!recent || recent.length >= RELOAD_LIMIT) { setNoticeText("paused"); return; }
    recent.push(Date.now());
    // Written before the reload, so the count is there for the page that follows.
    try { window.sessionStorage.setItem(RELOAD_KEY, JSON.stringify(recent)); }
    catch (e) { setNoticeText("paused"); return; }
    window.location.reload();
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
  // Hydration is awaited with the config so the first read of a preference
  // (applyTheme below) sees the shared copy, not an empty map. hydrate() never
  // rejects and gives up after 3 s, so a hung /api/prefs cannot hold first paint.
  Promise.all([C.get("/api/config"), C.prefs.hydrate()]).then(function (res) {
    var cfg = res[0];
    state.cfg = cfg;
    state.manifest = orderManifest(cfg.tabs || []);
    document.getElementById("brandTitle").textContent = cfg.title || "Delivery Console";
    document.getElementById("brandSub").textContent = cfg.subtitle || "";
    markConnection(true);
    watchConnection();

    applyTheme(C.prefs.get("theme", "system"));
    bindPrefs();
    buildNav();
    bindKeys();

    var wanted = window.location.hash.slice(1);
    var ids = visibleTabs().map(function (t) { return t.id; });
    go(ids.indexOf(wanted) !== -1 ? wanted : ids[0]);
    refreshBadges();
    if (!C.IS_STATIC) setInterval(refreshBadges, 30000);
    if (!C.IS_STATIC && window.ConsoleOnboarding) window.ConsoleOnboarding.maybeOpen();
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

  function setTitle(title) {
    if (!title) return;
    if (state.cfg) state.cfg.title = title;
    var brand = document.getElementById("brandTitle");
    if (brand) brand.textContent = title;
    if (state.active) {
      var target = visibleTabs().filter(function (t) { return t.id === state.active; })[0];
      if (target) document.title = target.label + " — " + title;
    }
  }

  window.ConsoleApp = { go: go, applyTheme: applyTheme, refreshBadges: refreshBadges, drawer: drawer,
                        setTitle: setTitle,
                        manifest: function () { return state.manifest; }, rebuildNav: buildNav };
})(window.Console);
