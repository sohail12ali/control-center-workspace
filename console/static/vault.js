/* Vault — the knowledge-center link graph, and a reader for every text file
   in it.

   Obsidian already draws this vault, but only its markdown: the ticket.toml
   lifecycle files and any SQL under a ticket are invisible there and
   unopenable from it. Hence a second graph rather than a link to the first,
   and hence the "include non-markdown" filter, which is the point of the tab.

   ---- Why a canvas here, when analytics.js argues charts must be DOM

   That argument holds for a couple of hundred static marks. It does not
   survive a force simulation: every tick moves every node, so as DOM that is
   thousands of style-invalidating attribute writes per frame. So this is a
   canvas — and it pays back all three things a canvas normally costs:

     theming        no colour is written here. The palette is read from the CSS
                    custom properties on <html> and re-read on theme change,
                    so a theme flip repaints exactly like everything else.
     accessibility  the navigator is the twin: focusable rows over the same
                    nodes, arrow-key navigation, Enter to open. The canvas is
                    the overview; the list is the interface.
     hover          two layers. Hover dims on an overlay and redraws only the
                    highlighted neighbourhood, never the full edge set.

   ---- Layout

   A collapsible card sidebar (filters / display / forces / navigator), the
   canvas stage, and a file viewer that opens as a third column on demand. */
(function (C) {
  "use strict";

  var CARDS = [
    { id: "filters", icon: "filter", label: "Filters", open: true },
    { id: "display", icon: "layout", label: "Display", open: false },
    { id: "forces", icon: "sliders", label: "Forces", open: false },
    { id: "navigator", icon: "folder", label: "Navigator", open: true, grow: true },
  ];

  var st = {
    host: null, graph: null, nodes: [], edges: [],
    pos: {},                          // id -> {x,y,vx,vy,fixed}
    view: { x: 0, y: 0, k: 1 },
    hover: null, selected: null, dragging: null,
    raf: 0, alpha: 0, settled: false,
    base: null, fx: null, palette: {},
    filters: { q: "", isolate: false, nonMd: false, orphans: true, depth: 0 },
    display: { labels: true, sizeByLinks: true, arrows: false },
    forces: { link: 62, charge: 620, center: 1.0 },
    openCards: {},
    viewerPath: null,
  };

  /* ---------------- palette (read, never written) ---------------- */
  function readPalette() {
    var cs = getComputedStyle(document.documentElement);
    var v = function (n, fb) { return (cs.getPropertyValue(n) || "").trim() || fb; };
    st.palette = {
      edge: v("--line", "#e2e6ec"),
      edgeSoft: v("--line-soft", "#eef0f4"),
      md: v("--accent", "#2563eb"),
      folder: v("--ink-3", "#858c9a"),
      other: v("--cat-2", "#d1571f"),
      toml: v("--cat-6", "#8a6a08"),
      sql: v("--cat-3", "#178f63"),
      ink: v("--ink", "#16181d"),
      ink3: v("--ink-3", "#858c9a"),
      surface: v("--bg-sunk", "#eceef2"),
      hi: v("--accent", "#2563eb"),
      warn: v("--warn", "#b8730a"),
    };
  }

  function nodeColor(n) {
    if (n.kind === "folder") return st.palette.folder;
    if (n.kind === "toml") return st.palette.toml;
    if (n.kind === "sql") return st.palette.sql;
    if (n.kind === "md") return st.palette.md;
    return st.palette.other;
  }

  /* ---------------- filtering ---------------- */
  function visibleSet() {
    var f = st.filters;
    var q = f.q.trim().toLowerCase();
    var keep = {};

    st.nodes.forEach(function (n) {
      if (!f.nonMd && !n.md && n.kind !== "folder") return;
      if (!f.orphans && n.links === 0 && n.kind !== "folder") return;
      if (q && f.isolate && n.id.toLowerCase().indexOf(q) === -1) return;
      keep[n.id] = true;
    });

    // Local-graph depth: from the selection outward, N hops.
    if (f.depth > 0 && st.selected && keep[st.selected]) {
      var adj = adjacency();
      var reach = {}, frontier = [st.selected];
      reach[st.selected] = true;
      for (var d = 0; d < f.depth; d++) {
        var next = [];
        frontier.forEach(function (id) {
          (adj[id] || []).forEach(function (o) {
            if (!reach[o]) { reach[o] = true; next.push(o); }
          });
        });
        frontier = next;
      }
      Object.keys(keep).forEach(function (id) { if (!reach[id]) delete keep[id]; });
    }
    return keep;
  }

  var _adjCache = null;
  function adjacency() {
    if (_adjCache) return _adjCache;
    var adj = {};
    st.edges.forEach(function (e) {
      (adj[e.source] = adj[e.source] || []).push(e.target);
      (adj[e.target] = adj[e.target] || []).push(e.source);
    });
    _adjCache = adj;
    return adj;
  }

  function activeGraph() {
    var keep = visibleSet();
    var nodes = st.nodes.filter(function (n) { return keep[n.id]; });
    var edges = st.edges.filter(function (e) { return keep[e.source] && keep[e.target]; });
    return { nodes: nodes, edges: edges, keep: keep };
  }

  /* ---------------- simulation ----------------
     Plain Verlet-ish integration with a cooling alpha. Runs on the main
     thread: these vaults are small enough that a worker would be more moving
     parts than it saves, and it stops entirely once settled so an idle tab
     burns nothing. */
  function seed(nodes) {
    var w = st.base ? st.base.width : 800, h = st.base ? st.base.height : 600;
    nodes.forEach(function (n, i) {
      if (st.pos[n.id]) return;
      var a = (2 * Math.PI * i) / Math.max(1, nodes.length);
      var r = Math.min(w, h) * 0.3;
      st.pos[n.id] = { x: w / 2 + Math.cos(a) * r, y: h / 2 + Math.sin(a) * r, vx: 0, vy: 0 };
    });
  }

  function tick(g) {
    var w = st.base.width, h = st.base.height;
    var f = st.forces;
    var nodes = g.nodes, edges = g.edges;
    var n = nodes.length;
    if (!n) return;

    /* Repulsion is divided by sqrt(n). Without that, every added node adds
       another pushing pair while centering stays fixed, so the layout blows
       apart as the vault grows — measured spreads went from ~1500px at 16
       nodes to ~62,000px at 400, far outside any canvas and past what the
       zoom clamp can fit. Scaling by sqrt(n) holds the spread at roughly
       600-950px from 16 nodes to 1200. O(n^2) pairs are fine at this scale
       and avoid a quadtree's bugs. */
    var charge = f.charge / Math.sqrt(Math.max(1, n));
    for (var i = 0; i < n; i++) {
      var a = st.pos[nodes[i].id];
      for (var j = i + 1; j < n; j++) {
        var b = st.pos[nodes[j].id];
        var dx = a.x - b.x, dy = a.y - b.y;
        var d2 = dx * dx + dy * dy;
        if (d2 < 0.01) { dx = (Math.random() - 0.5) * 2; dy = (Math.random() - 0.5) * 2; d2 = 4; }
        if (d2 > 90000) continue;                 // far enough to ignore
        var force = charge / d2;
        var d = Math.sqrt(d2);
        var fx = (dx / d) * force, fy = (dy / d) * force;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
    }
    // Link attraction.
    edges.forEach(function (e) {
      var a2 = st.pos[e.source], b2 = st.pos[e.target];
      if (!a2 || !b2) return;
      var dx = b2.x - a2.x, dy = b2.y - a2.y;
      var d = Math.max(Math.sqrt(dx * dx + dy * dy), 0.5);
      var k = (d - f.link) * 0.045 * (e.type === "contains" ? 0.5 : 1);
      var fx = (dx / d) * k, fy = (dy / d) * k;
      a2.vx += fx; a2.vy += fy; b2.vx -= fx; b2.vy -= fy;
    });
    // Centering + integrate + damping.
    var moved = 0;
    nodes.forEach(function (nd) {
      var p = st.pos[nd.id];
      if (st.dragging === nd.id) { p.vx = p.vy = 0; return; }
      p.vx += (w / 2 - p.x) * 0.012 * f.center;
      p.vy += (h / 2 - p.y) * 0.012 * f.center;
      p.vx *= 0.86; p.vy *= 0.86;
      p.x += p.vx * st.alpha; p.y += p.vy * st.alpha;
      moved += Math.abs(p.vx) + Math.abs(p.vy);
    });
    /* Cooling is the settle guarantee, and it is deliberately arithmetic
       rather than "stop when it looks still": 0.975^n < 0.02 at n = 155, so
       the layout ALWAYS converges within ~2.6s at 60fps no matter how the
       forces are tuned. The movement test below just ends it sooner when the
       graph is small enough to stop early. */
    st.alpha *= 0.975;
    if (st.alpha < 0.02 || moved / n < 0.02) { st.alpha = 0; st.settled = true; }
  }

  function kick(strength) {
    st.alpha = strength || 1;
    st.settled = false;
    /* Always cancel and reschedule. `loop()` refuses to double-schedule by
       checking st.raf, but a frame requested while the tab is hidden never
       fires — rAF is paused, not merely slowed — so that id stays truthy and
       the guard would block every later kick forever. Cancelling first makes
       a kick unconditionally restart the loop. */
    if (st.raf) { cancelAnimationFrame(st.raf); st.raf = 0; }
    loop();
  }

  function loop() {
    if (st.raf) return;
    var step = function () {
      st.raf = 0;
      if (!st.base || !document.getElementById("vaultBase")) return;   // tab left
      var g = activeGraph();
      seed(g.nodes);
      if (st.alpha > 0) tick(g);
      draw(g);
      if (st.alpha > 0) st.raf = requestAnimationFrame(step);
    };
    st.raf = requestAnimationFrame(step);
  }

  /* ---------------- drawing ---------------- */
  function resize() {
    var stage = document.getElementById("vaultStage");
    if (!stage || !st.base) return;
    var r = stage.getBoundingClientRect();
    // A hidden pane measures 0; writing width=0 discards the backing store and
    // the canvas never comes back. Refuse non-positive boxes.
    if (r.width < 2 || r.height < 2) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    [st.base, st.fx].forEach(function (cv) {
      cv.width = Math.round(r.width * dpr);
      cv.height = Math.round(r.height * dpr);
      cv.style.width = r.width + "px";
      cv.style.height = r.height + "px";
      cv.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    // Keep logical coords in CSS pixels.
    st.base.width = r.width; st.base.height = r.height;
    st.fx.width = r.width; st.fx.height = r.height;
    draw(activeGraph());
  }

  function radius(n) {
    if (n.kind === "folder") return 3.4;
    if (!st.display.sizeByLinks) return 4.6;
    return 3.6 + Math.min(6, Math.sqrt(n.links || 0) * 1.7);
  }

  function xf(p) {
    return { x: p.x * st.view.k + st.view.x, y: p.y * st.view.k + st.view.y };
  }

  function draw(g) {
    if (!st.base) return;
    var ctx = st.base.getContext("2d");
    var w = st.base.width, h = st.base.height;
    ctx.clearRect(0, 0, w, h);

    // edges
    ctx.lineWidth = 1;
    g.edges.forEach(function (e) {
      var a = st.pos[e.source], b = st.pos[e.target];
      if (!a || !b) return;
      var pa = xf(a), pb = xf(b);
      ctx.strokeStyle = e.type === "contains" ? st.palette.edgeSoft : st.palette.edge;
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    });

    // nodes
    var q = st.filters.q.trim().toLowerCase();
    g.nodes.forEach(function (n) {
      var p = st.pos[n.id];
      if (!p) return;
      var pt = xf(p);
      var r = radius(n) * Math.max(0.7, Math.min(1.6, st.view.k));
      var isMatch = q && n.id.toLowerCase().indexOf(q) !== -1;
      ctx.fillStyle = nodeColor(n);
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, r, 0, 2 * Math.PI);
      ctx.fill();
      if (n.id === st.selected || isMatch) {
        ctx.strokeStyle = isMatch && n.id !== st.selected ? st.palette.warn : st.palette.hi;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.lineWidth = 1;
      }
    });

    // labels — only when there is room, else they become mush
    if (st.display.labels && (g.nodes.length < 120 || st.view.k > 1.4)) {
      ctx.font = "10px -apple-system, Segoe UI, sans-serif";
      ctx.fillStyle = st.palette.ink3;
      ctx.textAlign = "center";
      g.nodes.forEach(function (n) {
        var p = st.pos[n.id];
        if (!p) return;
        var pt = xf(p);
        ctx.fillText(n.label.replace(/\.(md|toml|sql|txt|json|ya?ml)$/, ""),
                     pt.x, pt.y - radius(n) - 4);
      });
    }
    hud(g);
    fxDraw();
  }

  /* Hover overlay: dim once, then redraw only the neighbourhood. */
  function fxDraw() {
    if (!st.fx) return;
    var ctx = st.fx.getContext("2d");
    ctx.clearRect(0, 0, st.fx.width, st.fx.height);
    if (!st.hover) return;
    var adj = adjacency();
    var near = {};
    near[st.hover] = true;
    (adj[st.hover] || []).forEach(function (id) { near[id] = true; });

    ctx.fillStyle = "rgba(0,0,0,0.30)";
    ctx.fillRect(0, 0, st.fx.width, st.fx.height);

    var g = activeGraph();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = st.palette.hi;
    g.edges.forEach(function (e) {
      if (e.source !== st.hover && e.target !== st.hover) return;
      var a = st.pos[e.source], b = st.pos[e.target];
      if (!a || !b) return;
      var pa = xf(a), pb = xf(b);
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
    });
    ctx.font = "11px -apple-system, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    g.nodes.forEach(function (n) {
      if (!near[n.id]) return;
      var p = st.pos[n.id];
      if (!p) return;
      var pt = xf(p);
      ctx.fillStyle = nodeColor(n);
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, radius(n) + (n.id === st.hover ? 2.5 : 1), 0, 2 * Math.PI);
      ctx.fill();
      ctx.fillStyle = st.palette.ink;
      ctx.fillText(n.label, pt.x, pt.y - radius(n) - 6);
    });
  }

  function hud(g) {
    var el = document.getElementById("vaultCounts");
    if (el) {
      el.textContent = g.nodes.length + " / " + st.nodes.length + " nodes · " +
                       g.edges.length + " edges" + (st.settled ? "" : " · settling…");
    }
  }

  /* ---------------- picking / interaction ---------------- */
  function nodeAt(mx, my) {
    var g = activeGraph();
    var best = null, bestD = 14;
    g.nodes.forEach(function (n) {
      var p = st.pos[n.id];
      if (!p) return;
      var pt = xf(p);
      var d = Math.hypot(pt.x - mx, pt.y - my);
      if (d < bestD) { bestD = d; best = n; }
    });
    return best;
  }

  function wireStage() {
    var stage = document.getElementById("vaultStage");
    var fx = st.fx;
    var panning = false, last = null;

    function local(e) {
      var r = fx.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }

    fx.addEventListener("mousemove", function (e) {
      var m = local(e);
      if (st.dragging) {
        var p = st.pos[st.dragging];
        p.x = (m.x - st.view.x) / st.view.k;
        p.y = (m.y - st.view.y) / st.view.k;
        draw(activeGraph());
        return;
      }
      if (panning && last) {
        st.view.x += m.x - last.x;
        st.view.y += m.y - last.y;
        last = m;
        draw(activeGraph());
        return;
      }
      var hit = nodeAt(m.x, m.y);
      var id = hit ? hit.id : null;
      if (id !== st.hover) {
        st.hover = id;
        fx.style.cursor = id ? "pointer" : "grab";
        var status = document.getElementById("vaultStatus");
        if (status) status.textContent = hit ? hit.id : "";
        fxDraw();
      }
    });

    fx.addEventListener("mousedown", function (e) {
      var m = local(e);
      var hit = nodeAt(m.x, m.y);
      if (hit) { st.dragging = hit.id; st.alpha = Math.max(st.alpha, 0.25); loop(); }
      else { panning = true; last = m; fx.style.cursor = "grabbing"; }
    });

    window.addEventListener("mouseup", function () {
      if (st.dragging) { st.dragging = null; kick(0.35); }
      panning = false;
      if (fx) fx.style.cursor = st.hover ? "pointer" : "grab";
    });

    fx.addEventListener("click", function (e) {
      var m = local(e);
      var hit = nodeAt(m.x, m.y);
      if (hit) selectNode(hit.id, hit.kind !== "folder");
    });

    fx.addEventListener("wheel", function (e) {
      e.preventDefault();
      var m = local(e);
      var k0 = st.view.k;
      var k1 = Math.max(0.25, Math.min(4, k0 * (e.deltaY < 0 ? 1.12 : 0.89)));
      // Zoom about the cursor so the thing under it stays put.
      st.view.x = m.x - (m.x - st.view.x) * (k1 / k0);
      st.view.y = m.y - (m.y - st.view.y) * (k1 / k0);
      st.view.k = k1;
      draw(activeGraph());
    }, { passive: false });

    if (window.ResizeObserver && stage) {
      new ResizeObserver(function () { resize(); }).observe(stage);
    }

    /* rAF is paused entirely while the tab is hidden, so a graph opened in a
       background tab has not laid out by the time someone looks at it. Resume
       on becoming visible rather than showing them a seeded ring. */
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && st.base && !st.settled) { resize(); kick(Math.max(st.alpha, 0.6)); }
    });
  }

  function fit() {
    var g = activeGraph();
    if (!g.nodes.length || !st.base) return;
    var xs = [], ys = [];
    g.nodes.forEach(function (n) {
      var p = st.pos[n.id];
      if (p) { xs.push(p.x); ys.push(p.y); }
    });
    if (!xs.length) return;
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var pad = 40;
    var kx = (st.base.width - pad * 2) / Math.max(1, maxX - minX);
    var ky = (st.base.height - pad * 2) / Math.max(1, maxY - minY);
    st.view.k = Math.max(0.25, Math.min(2.5, Math.min(kx, ky)));
    st.view.x = pad - minX * st.view.k + (st.base.width - pad * 2 - (maxX - minX) * st.view.k) / 2;
    st.view.y = pad - minY * st.view.k + (st.base.height - pad * 2 - (maxY - minY) * st.view.k) / 2;
    draw(activeGraph());
  }

  /* ---------------- selection + viewer ---------------- */
  function selectNode(id, openFile) {
    st.selected = id;
    paintNavigator();
    draw(activeGraph());
    if (openFile) openViewer(id);
  }

  function openViewer(path) {
    st.viewerPath = path;
    var wrap = document.getElementById("vaultWrap");
    var viewer = document.getElementById("vaultViewer");
    if (!viewer) return;
    wrap.classList.add("has-viewer");
    C.clear(viewer).appendChild(C.skeleton(4));
    C.get("/api/vault/file?path=" + encodeURIComponent(path)).then(function (d) {
      C.clear(viewer);
      viewer.appendChild(C.el("header", {}, [
        C.el("h3", { class: "truncate", title: d.path, text: d.path.split("/").pop() }),
        C.el("span", { class: "muted", text: (d.size / 1024).toFixed(1) + " KB" }),
        C.el("button", {
          class: "btn sm iconly", "aria-label": "Close file", title: "Close",
          onclick: function () {
            wrap.classList.remove("has-viewer");
            st.viewerPath = null;
            setTimeout(resize, 60);
          },
        }, [C.icon("x")]),
      ]));
      var body = C.el("div", { class: "vault-viewbody" });
      if (/\.md$/i.test(d.path)) body.appendChild(window.ConsoleMarkdown.render(d.content));
      else body.appendChild(C.el("pre", { class: "code", text: d.content }));
      viewer.appendChild(body);
      setTimeout(resize, 60);
    }).catch(function (err) {
      C.clear(viewer).appendChild(C.errbox(err));
    });
  }

  /* ---------------- sidebar cards ---------------- */
  function card(def, body) {
    var open = st.openCards[def.id] !== undefined ? st.openCards[def.id] : def.open;
    var chev = C.el("span", { class: "chev" }, [C.icon("chevDown")]);
    var head = C.el("button", {
      class: "vault-card-h", "aria-expanded": String(open),
      onclick: function () {
        st.openCards[def.id] = !(st.openCards[def.id] !== undefined ? st.openCards[def.id] : def.open);
        paintSidebar();
        setTimeout(resize, 60);
      },
    }, [C.icon(def.icon), C.el("span", { class: "grow", text: def.label }), chev]);
    var node = C.el("section", {
      class: "vault-card" + (def.grow ? " grow" : "") + (open ? "" : " shut"),
    }, [head, C.el("div", { class: "vault-card-b" }, [body])]);
    return node;
  }

  function chk(label, key, group, onChange) {
    var cb = C.el("input", { type: "checkbox" });
    cb.checked = !!st[group][key];
    cb.addEventListener("change", function () {
      st[group][key] = cb.checked;
      if (onChange) onChange();
    });
    return C.el("label", { class: "vault-chk" }, [cb, C.el("span", { text: label })]);
  }

  function rng(label, key, min, max, step, fmt) {
    var out = C.el("b", { text: fmt ? fmt(st.forces[key]) : String(st.forces[key]) });
    var input = C.el("input", {
      type: "range", min: min, max: max, step: step, value: st.forces[key],
    });
    input.addEventListener("input", function () {
      st.forces[key] = Number(input.value);
      out.textContent = fmt ? fmt(st.forces[key]) : input.value;
      kick(0.6);
    });
    return C.el("label", { class: "vault-rng" }, [
      C.el("span", {}, [label + " ", out]), input,
    ]);
  }

  function paintSidebar() {
    var side = document.getElementById("vaultSide");
    if (!side) return;
    C.clear(side);

    // Filters
    var search = C.el("input", {
      type: "search", placeholder: "Find a file…", value: st.filters.q,
      "aria-label": "Search the vault",
    });
    search.addEventListener("input", function () {
      st.filters.q = search.value;
      paintNavigator();
      draw(activeGraph());
    });
    side.appendChild(card(CARDS[0], C.el("div", {}, [
      search,
      chk("Isolate matches", "isolate", "filters", function () { kick(0.5); paintNavigator(); }),
      chk("Include non-markdown", "nonMd", "filters", function () { kick(0.6); paintNavigator(); }),
      chk("Show orphans", "orphans", "filters", function () { kick(0.5); paintNavigator(); }),
      (function () {
        var out = C.el("b", { text: st.filters.depth ? String(st.filters.depth) : "off" });
        var input = C.el("input", { type: "range", min: "0", max: "5", step: "1", value: st.filters.depth });
        input.addEventListener("input", function () {
          st.filters.depth = Number(input.value);
          out.textContent = st.filters.depth ? input.value : "off";
          kick(0.6);
          paintNavigator();
        });
        return C.el("label", { class: "vault-rng" }, [
          C.el("span", {}, ["Local graph depth ", out]), input,
          C.el("span", { class: "muted", style: "font-size:10.5px",
            text: st.selected ? "" : "select a node first" }),
        ]);
      })(),
    ])));

    // Display
    side.appendChild(card(CARDS[1], C.el("div", {}, [
      chk("Labels", "labels", "display", function () { draw(activeGraph()); }),
      chk("Size by links", "sizeByLinks", "display", function () { draw(activeGraph()); }),
    ])));

    // Forces
    side.appendChild(card(CARDS[2], C.el("div", {}, [
      rng("Link distance", "link", 20, 160, 2),
      rng("Repulsion", "charge", 100, 2000, 20),
      rng("Centering", "center", 0, 3, 0.1, function (v) { return v.toFixed(1); }),
      C.el("div", { class: "row", style: "margin-top:7px" }, [
        C.el("button", { class: "btn sm", onclick: fit }, ["Fit"]),
        C.el("button", { class: "btn sm", onclick: function () { kick(1); } }, ["Re-settle"]),
      ]),
    ])));

    // Navigator (the accessible twin)
    side.appendChild(card(CARDS[3], C.el("div", { class: "vault-tree", id: "vaultTree", role: "tree", tabindex: "0" })));
    paintNavigator();
  }

  function paintNavigator() {
    var tree = document.getElementById("vaultTree");
    if (!tree) return;
    C.clear(tree);
    var g = activeGraph();
    var q = st.filters.q.trim().toLowerCase();
    var rows = g.nodes.filter(function (n) { return n.kind !== "folder"; });
    if (q) {
      rows = rows.filter(function (n) { return n.id.toLowerCase().indexOf(q) !== -1; });
    }
    rows.sort(function (a, b) { return a.id < b.id ? -1 : 1; });

    if (!rows.length) {
      tree.appendChild(C.el("div", { class: "muted", style: "padding:6px", text: "No files match." }));
      return;
    }
    rows.slice(0, 400).forEach(function (n) {
      var row = C.el("div", {
        class: "trow", role: "treeitem", tabindex: "-1",
        "aria-selected": String(n.id === st.selected),
        title: n.id,
        onclick: function () { selectNode(n.id, true); },
        onmouseenter: function () { st.hover = n.id; fxDraw(); },
        onmouseleave: function () { if (st.hover === n.id) { st.hover = null; fxDraw(); } },
      }, [
        C.icon(n.kind === "md" ? "file" : "file"),
        C.el("span", { class: "truncate", text: n.label }),
        n.links ? C.el("span", { class: "muted", style: "font-size:10px", text: String(n.links) }) : null,
      ]);
      tree.appendChild(row);
    });
    if (rows.length > 400) {
      tree.appendChild(C.el("div", { class: "muted", style: "padding:6px",
        text: "+" + (rows.length - 400) + " more — narrow the search to see them." }));
    }

    // Arrow-key navigation over the same nodes the canvas draws.
    tree.onkeydown = function (e) {
      var items = Array.prototype.slice.call(tree.querySelectorAll(".trow"));
      if (!items.length) return;
      var i = items.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); (items[i + 1] || items[0]).focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); (items[i - 1] || items[items.length - 1]).focus(); }
      else if (e.key === "Enter" && i >= 0) { e.preventDefault(); items[i].click(); }
      else if (i < 0) { items[0].focus(); }
    };
  }

  /* ---------------- theme ---------------- */
  function watchTheme() {
    var mo = new MutationObserver(function () {
      readPalette();
      draw(activeGraph());
    });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) {
        mq.addEventListener("change", function () { readPalette(); draw(activeGraph()); });
      }
    }
  }

  /* ---------------- render ---------------- */
  function render(host) {
    st.host = host;
    C.clear(host);

    host.appendChild(C.el("div", { class: "vault", id: "vaultWrap" }, [
      C.el("aside", { class: "vault-side", id: "vaultSide" }),
      C.el("div", { class: "vault-stage", id: "vaultStage" }, [
        C.el("canvas", { id: "vaultBase", role: "img",
          "aria-label": "Knowledge-center link graph. The navigator list beside it carries the same nodes as focusable rows." }),
        C.el("canvas", { id: "vaultFx", "aria-hidden": "true" }),
        C.el("div", { class: "vault-hud" }, [
          C.el("span", { id: "vaultStatus", class: "mono" }),
          C.el("span", { id: "vaultCounts", class: "muted" }),
        ]),
      ]),
      C.el("section", { class: "vault-viewer", id: "vaultViewer" }),
    ]));

    st.base = document.getElementById("vaultBase");
    st.fx = document.getElementById("vaultFx");
    readPalette();
    watchTheme();
    paintSidebar();
    wireStage();
    resize();

    C.get("/api/vault/graph").then(function (g) {
      st.graph = g;
      st.nodes = g.nodes || [];
      st.edges = g.edges || [];
      _adjCache = null;
      st.pos = {};
      // Default: markdown only, which is the readable view; the filter says
      // so and turning it on is one click.
      seed(activeGraph().nodes);
      paintSidebar();
      resize();
      kick(1);
      setTimeout(fit, 700);
      if (g.truncated) {
        C.toast("Graph truncated at the file cap — showing a partial view.", "");
      }
    }).catch(function (err) {
      C.clear(host).appendChild(C.el("div", { style: "padding:14px" }, [C.errbox(err)]));
    });
  }

  C.tab("vault", {
    layout: "app",
    render: render,
    onSearch: function (q) {
      st.filters.q = q;
      var s = document.querySelector("#vaultSide input[type=search]");
      if (s) s.value = q;
      paintNavigator();
      draw(activeGraph());
    },
    onLeave: function () {
      if (st.raf) { cancelAnimationFrame(st.raf); st.raf = 0; }
      st.alpha = 0;
      st.base = st.fx = null;
    },
  });
})(window.Console);
