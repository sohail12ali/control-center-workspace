/* Splitter: one pointer- and keyboard-operable divider between two panes.

   C.splitter(opts) appends a .sp handle to opts.host and returns it. The
   handle is an overlay on the pane's edge: it owns no grid track and changes
   no width by being there. The size the user chose is written as --sp-<name>
   on opts.owner and consumed by the stylesheet only inside the wide query, so
   below it a stored size changes nothing. This file never writes the grid's
   column list inline and never touches the root element.

   The option names, the six surfaces and the paper walk-through live in
   T-037-components.md ("C1 API contract"). Persistence is one object,
   "layout", through C.prefs only, written once per finished gesture
   (writeLayout below holds the file's only prefs.set).

   Loaded after core.js (it needs C.el and C.prefs) and before app.js. */
window.Console = window.Console || {};
(function (C) {
  "use strict";

  /* The one "wide" condition: the complement of the 900px structural cliff in
     the stylesheet. Kept here once so the dock can ask the same question. */
  var WIDE = "(min-width: 901px)";
  var STEP = 16;          // one arrow press, px (x4 with Shift)
  var SLOP = 3;           // px a press may wobble before it counts as a drag
  var registry = [];      // every handle attached; pruned by prune() below
  var paneSeq = 0;        // ids for panes that have none (aria-controls)
  var wideMq = null;
  var installed = false;  // the window-level listeners go on once, at the first attach

  /* One MediaQueryList for the file: wide() reads it, the change listener
     watches it. */
  function wq() {
    if (!wideMq) wideMq = window.matchMedia(WIDE);
    return wideMq;
  }

  function wide() { return wq().matches; }

  function isObj(v) { return !!v && typeof v === "object" && !Array.isArray(v); }

  /* A stored width is a positive finite number; a fold flag is true. Anything
     else in layout (a string, null, a negative) is ignored, never an error. */
  function validMember(v) {
    return v === true || (typeof v === "number" && isFinite(v) && v > 0);
  }

  function splitPath(path) {
    var i = String(path).indexOf(".");
    return [path.slice(0, i), path.slice(i + 1)];
  }

  /* Read one member of layout, or undefined. Read every time, never cached:
     Reset layout and a server hydrate both change it behind our back. */
  function readMember(path) {
    var p = splitPath(path);
    var obj = C.prefs.get("layout", null);
    var group = isObj(obj) ? obj[p[0]] : null;
    var v = isObj(group) ? group[p[1]] : undefined;
    return validMember(v) ? v : undefined;
  }

  /* The only write to storage. Read-modify-write of the whole object so a
     sibling key, and any key a newer build added, survives; undefined
     deletes the member (double-click, restore) rather than storing a default,
     which would freeze the fluid Agents default at today's viewport. */
  function writeLayout(path, value) {
    if (value !== undefined && !validMember(value)) return;
    var p = splitPath(path);
    var cur = C.prefs.get("layout", null);
    var obj = isObj(cur) ? cur : {};
    if (typeof obj.v !== "number") obj.v = 1;
    var old = isObj(obj[p[0]]) ? obj[p[0]] : {};
    var group = {};
    Object.keys(old).forEach(function (k) {
      if (validMember(old[k])) group[k] = old[k];
    });
    if (value === undefined) delete group[p[1]];
    else group[p[1]] = typeof value === "number" ? Math.round(value) : value;
    obj[p[0]] = group;
    C.prefs.set("layout", obj);
  }

  /* ---------------- geometry ---------------- */

  /* A lane is built before its .lanes exists, so the owner may be a function
     asked at every write; null means "not mounted yet, skip". */
  function ownerOf(e) {
    var o = e.opts.owner;
    return typeof o === "function" ? o() : (o || e.host);
  }

  function setVar(e, w) {
    var own = ownerOf(e), name = "--sp-" + e.opts.cssVar;
    if (!own) return;
    if (w === null) own.style.removeProperty(name);
    else own.style.setProperty(name, w + "px");
  }

  function widthOf(node) { return node ? node.getBoundingClientRect().width : 0; }

  function flexOf(e) {
    var f = e.opts.flexPane;
    return typeof f === "function" ? f() : f;
  }

  function limits(o) { return [o.min || 0, o.max > 0 ? o.max : Infinity]; }

  /* [lo, hi] for the pane at width cur. The flexible neighbour bounds the top:
     what it has to spare above its own minimum is what this pane may take. */
  function bounds(e, cur) {
    var o = e.opts, b = limits(o), f = flexOf(e);
    if (f) b[1] = Math.min(b[1], cur + widthOf(f) - (o.flexMin || 0));
    b[1] = Math.max(b[1], b[0]);
    return b;
  }

  function clamp(w, b) { return Math.min(b[1], Math.max(b[0], w)); }

  function folded(e) {
    var o = e.opts;
    if (typeof o.collapseGet === "function") return !!o.collapseGet();
    return !!o.collapseKey && readMember(o.collapseKey) === true;
  }

  /* The handle sits on the pane's MEASURED edge, so a fluid default such as
     clamp(208px, 22vw, 302px) is read, never duplicated here. A pane with no
     box (display:none) has no edge to read: it sits on the container side the
     pane would hug. Skipped while the handle itself has no box (hidden, or the
     wide query is off): there is nothing to place. */
  function place(e) {
    var h = e.handle, host = e.host, w = h.offsetWidth, edge;
    if (!w) return;
    if (e.pane.getClientRects().length) {
      var pr = e.pane.getBoundingClientRect();
      edge = (e.dir === 1 ? pr.right : pr.left) -
        host.getBoundingClientRect().left - host.clientLeft;
    } else {
      edge = e.dir === 1 ? 0 : host.clientWidth;
    }
    h.style.left = Math.max(w / 2, Math.min(host.clientWidth - w / 2, edge)) + "px";
  }

  /* Visual and ARIA state from what is true now. A collapsible pane reports
     0 while folded (APG window splitter), so its minimum is 0 too. Every
     handle carries the value, aria-hidden or not. */
  function mark(e) {
    var h = e.handle, o = e.opts, off = folded(e);
    h.classList.toggle("sp-collapsed", off);
    h.hidden = off && !o.keepWhenCollapsed;
    var cur = Math.round(widthOf(e.pane)), b = bounds(e, cur);
    h.setAttribute("aria-valuenow", off ? 0 : cur);
    h.setAttribute("aria-valuemin", typeof o.collapseSet === "function" ? 0 : b[0]);
    if (isFinite(b[1])) h.setAttribute("aria-valuemax", b[1]);
  }

  /* Handles that share a key share one width (the board's lane handles), so
     they are all brought up to date together; the others are just e. */
  function refresh(e) {
    mark(e);
    place(e);
    registry.forEach(function (o) {
      if (o !== e && o.opts.key === e.opts.key) { mark(o); place(o); }
    });
  }

  /* ---------------- apply and fold ---------------- */

  /* Put the stored layout on screen: read it, clamp, write the variable (or
     remove it, so the stylesheet's own default shows). Never writes storage:
     a width saved on a big monitor must survive a visit on a small one, and a
     clamp that rewrote it would shrink it for good. A drag in flight is left
     alone; its release finishes the job. */
  function apply(e) {
    if (e.drag) return;
    var o = e.opts, stored = readMember(o.key);
    if (o.collapseKey && typeof o.collapseSet === "function") {
      var off = readMember(o.collapseKey) === true;
      if (folded(e) !== off) o.collapseSet(off);
    }
    if (typeof stored !== "number") {
      setVar(e, null);
    } else {
      var w = clamp(stored, limits(o)), f = flexOf(e);
      setVar(e, w);
      /* The neighbour may be too narrow for this width in a small window:
         give back exactly what it is short, never going under our minimum. */
      var short = f ? (o.flexMin || 0) - widthOf(f) : 0;
      if (short > 0) setVar(e, Math.max(o.min || 0, w - short));
    }
    refresh(e);
  }

  function canFold(e) { return typeof e.opts.collapseSet === "function"; }

  /* Collapse or restore. The surface owns what "folded" looks like
     (collapseSet); the splitter keeps the flag only when it has a collapseKey
     (the Agents list keeps its own). The width key is never touched, so a
     restore returns to the last width, or to the default when there was none. */
  function fold(e, off) {
    var o = e.opts;
    o.collapseSet(off);
    if (o.collapseKey) writeLayout(o.collapseKey, off ? true : undefined);
    apply(e);
  }

  /* ---------------- pointer ---------------- */

  /* Pointer Events with capture: once captured, every move and the release go
     to the handle wherever the pointer is (over the Vault canvas, outside the
     window), so no overlay is needed and nothing is lost on the way. */
  function startDrag(e, ev) {
    if (e.drag || !wide() || (ev.button !== undefined && ev.button !== 0)) return;
    try { e.handle.setPointerCapture(ev.pointerId); } catch (x) { return; }
    var w0 = widthOf(e.pane);
    e.drag = {
      id: ev.pointerId, x0: ev.clientX, x: ev.clientX, w0: w0, b: bounds(e, w0),
      wasFolded: folded(e), moved: false, raf: 0, raw: w0, last: Math.round(w0),
    };
    document.body.classList.add("sp-dragging");
    e.handle.classList.add("sp-active");
    try {
      if (typeof e.opts.onDragStart === "function") e.opts.onDragStart(e.handle);
    } catch (x) { endDrag(e); throw x; }
  }

  /* One write per frame at most, whatever the pointer's event rate. A press
     that wobbles under SLOP px is still a click, not a drag. */
  function moveDrag(e, ev) {
    var d = e.drag;
    if (!d || ev.pointerId !== d.id) return;
    d.x = ev.clientX;
    if (!d.moved && Math.abs(d.x - d.x0) < SLOP) return;
    d.moved = true;
    if (d.wasFolded || d.raf) return;
    d.raf = requestAnimationFrame(function () {
      d.raf = 0;
      if (e.drag === d) sizeTo(e, d);
    });
  }

  /* The new width follows the pointer; ordinal divides the delta for a lane
     whose edge moves that many times the width change. */
  function sizeTo(e, d) {
    d.raw = d.w0 + e.dir * (d.x - d.x0) / e.ordinal;
    d.last = Math.round(clamp(d.raw, d.b));
    setVar(e, d.last);
    refresh(e);
  }

  /* The one end of a gesture, whichever path got us here: release, cancel,
     lostpointercapture, or the handle leaving the DOM. The first call wins (a
     release is followed by lostpointercapture) and the body class goes first,
     so a throwing hook cannot leave the page unselectable. Every path commits
     the width already on screen, once and only if it changed; only a release
     may also collapse, or restore a folded pane. */
  function endDrag(e, up) {
    var d = e.drag, o = e.opts, changed = false;
    if (!d) return;
    e.drag = null;
    document.body.classList.remove("sp-dragging");
    e.handle.classList.remove("sp-active");
    if (d.raf) { cancelAnimationFrame(d.raf); d.raf = 0; }
    try {
      if (up) d.x = up.clientX;
      if (d.wasFolded) {
        if (up) { restore(e); changed = true; }
      } else if (d.moved) {
        sizeTo(e, d);
        if (up && canFold(e) && d.raw < (o.min || 0) / 2) {
          fold(e, true);
          changed = true;
        } else if (d.last !== Math.round(d.w0)) {
          writeLayout(o.key, d.last);
          changed = true;
        }
      }
      if (!changed) apply(e);
    } finally {
      if (typeof o.onDragEnd === "function") o.onDragEnd(e.handle, changed);
    }
  }

  /* ---------------- keyboard, reset, restore ---------------- */

  function restore(e) {
    fold(e, false);
    e.restoredAt = Date.now();
  }

  /* One key step is one gesture: one write, and none when the clamp leaves the
     width where it was (Arrow at the maximum is not a change). */
  function setWidth(e, w) {
    var cur = widthOf(e.pane);
    if (!isFinite(w)) return;
    w = Math.round(clamp(w, bounds(e, cur)));
    if (w === Math.round(cur)) return;
    setVar(e, w);
    refresh(e);
    writeLayout(e.opts.key, w);
  }

  /* The handle moves the way the arrow points: ArrowRight adds dir * 16 px,
     so on a right-edge handle (dir -1) it narrows the pane. Only the primary
     handle takes keys; the rest are pointer-only. A folded pane answers
     Enter (restore) and nothing else. */
  function onKey(e, ev) {
    if (e.drag || !wide() || !e.primary || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    var k = ev.key, cur = widthOf(e.pane), big = ev.shiftKey ? 4 : 1, to;
    if (k === "Enter") {
      if (!canFold(e)) return;
      ev.preventDefault();
      if (folded(e)) restore(e); else fold(e, true);
      return;
    }
    if (folded(e)) return;
    if (k === "ArrowRight") to = cur + e.dir * STEP * big;
    else if (k === "ArrowLeft") to = cur - e.dir * STEP * big;
    else if (k === "Home") to = bounds(e, cur)[0];
    else if (k === "End") to = bounds(e, cur)[1];
    else return;
    ev.preventDefault();
    setWidth(e, to);
  }

  /* Double-click deletes the key, so the width follows the stylesheet default
     again (a fluid one stays fluid). A double-click whose first click just
     restored a fold must not also throw away the width it restored. */
  function onDouble(e) {
    if (!wide() || Date.now() - e.restoredAt < 600) return;
    if (readMember(e.opts.key) === undefined) return;
    writeLayout(e.opts.key, undefined);
    apply(e);
  }

  /* ---------------- attach ---------------- */

  /* Build the handle, put it in opts.host and apply the stored layout once: an
     owner such as .lanes is new on every paint, so every attach must set its
     variable itself. The host is a containing block through the stylesheet
     (.appshell, .vault, and position: relative on .ct-split, .lane
     and the dock aside), never through an inline style written here.
     The handle's own listeners go with it when the host does; the only
     window-level ones are installed once, by install() below. Stale entries
     are pruned first, so a repaint that builds a handle per paint cannot pile
     them up (and a throwing end hook then fails before anything is built). */
  function splitter(opts) {
    prune(true);
    var pane = opts.pane;
    var e = {
      opts: opts, host: opts.host, pane: pane, handle: null, drag: null,
      restoredAt: 0, seen: false, dir: opts.dir === -1 ? -1 : 1,
      ordinal: opts.ordinal > 0 ? opts.ordinal : 1, primary: opts.primary !== false,
    };
    var attrs = { class: "sp", role: "separator", "aria-orientation": "vertical" };
    if (e.primary) {
      if (!pane.id) pane.id = "sp-pane-" + (++paneSeq);
      attrs.tabindex = "0";
      attrs["aria-label"] = opts.label;
      attrs["aria-controls"] = pane.id;
    } else {
      attrs["aria-hidden"] = "true";
    }
    var h = e.handle = C.el("div", attrs);
    h.addEventListener("pointerdown", function (ev) { startDrag(e, ev); });
    h.addEventListener("pointermove", function (ev) { moveDrag(e, ev); });
    h.addEventListener("pointerup", function (ev) {
      if (e.drag && ev.pointerId === e.drag.id) endDrag(e, ev);
    });
    h.addEventListener("pointercancel", function () { endDrag(e); });
    h.addEventListener("lostpointercapture", function () { endDrag(e); });
    h.addEventListener("keydown", function (ev) { onKey(e, ev); });
    h.addEventListener("dblclick", function () { onDouble(e); });
    e.host.appendChild(h);
    e.seen = h.isConnected;
    registry.push(e);
    install();
    apply(e);
    return h;
  }

  /* ---------------- registry and window listeners ---------------- */

  /* Drop the entries that left the document. The handle is the host's child,
     so its isConnected covers a removed host and a handle removed from a live
     one. An entry that was never in the document is pending, not dead: a lane
     is built, and its handle attached, before the lane has a parent, so attach
     (keepPending) must not drop the lanes built just before. Every other
     caller runs between tasks, when a still-detached entry was abandoned.

     A removed handle never receives its own lostpointercapture, so a drag in
     flight ends here, through the one endDrag: the body class and the
     surface's onDragEnd hook are released. The registry is swapped before any
     hook runs and every hook gets its turn; the first error is rethrown. */
  function prune(keepPending) {
    var live = [], dead = [], err = null;
    registry.forEach(function (e) {
      if (e.handle.isConnected) { e.seen = true; live.push(e); }
      else if (keepPending && !e.seen) live.push(e);
      else dead.push(e);
    });
    registry = live;
    dead.forEach(function (e) {
      try { endDrag(e); } catch (x) { err = err || x; }
    });
    if (err) throw err;
  }

  /* Re-read layout and put it on screen for every entry still in the document:
     Reset layout (the stored object was deleted), a server hydrate (it was
     replaced), and a lane or dock just mounted (its handle had no box to be
     placed on while the host was outside the document) all end here. It never
     writes storage. A surface that removes a handle calls it afterwards, since
     nothing else notices. Safe on an empty registry. */
  function reapplyAll() {
    prune(false);
    registry.forEach(function (e) { apply(e); });
  }

  /* One re-apply per frame, however many events arrive. */
  var queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; reapplyAll(); });
  }

  /* The window-level listeners, added once at the first attach and never per
     handle: the board repaints on every keystroke and would pile up a set per
     paint. A resize moves a fluid default (clamp(208px, 22vw, 302px)), so every
     handle is measured again and a stored width is clamped afresh; crossing
     the wide breakpoint shows or hides every handle through the stylesheet,
     and one that had no box at attach has to be placed then. */
  function install() {
    if (installed) return;
    installed = true;
    window.addEventListener("resize", schedule);
    var mq = wq();
    if (mq.addEventListener) mq.addEventListener("change", schedule);
  }

  /* ---------------- fold bar ---------------- */

  /* A click handler that opens or closes every C.panel / C.group section under
     host. The sections are looked up when the button is pressed, never when the
     bar is built: Overview fills its panels in as requests return and two of
     them remove themselves when empty, so a list taken earlier would miss the
     new panels and poke the removed ones. A node without _setOpen is not a
     collapsible section and is skipped. _setOpen persists to panelOpen by
     itself, so nothing here touches storage. */
  function setAllOpen(host, open) {
    return function () {
      var nodes = host.querySelectorAll("[data-panel-id]");
      for (var i = 0; i < nodes.length; i++) {
        if (typeof nodes[i]._setOpen === "function") nodes[i]._setOpen(open);
      }
    };
  }

  /* The Collapse all / Expand all row. The surface inserts it as the first row
     of host; this only builds it. Settings keeps its own jump bar. */
  function foldBar(host) {
    return C.el("div", { class: "sp-foldbar" }, [
      C.el("button", { class: "btn sm", type: "button", text: "Collapse all", onclick: setAllOpen(host, false) }),
      C.el("button", { class: "btn sm", type: "button", text: "Expand all", onclick: setAllOpen(host, true) }),
    ]);
  }

  /* ---------------- export ---------------- */
  C.splitter = splitter;
  C.splitter.WIDE = WIDE;
  C.splitter.reapplyAll = reapplyAll;
  C.splitter.foldBar = foldBar;
})(window.Console);
