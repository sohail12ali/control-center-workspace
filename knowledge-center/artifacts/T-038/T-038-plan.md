---
ticket: "T-038"
artifact: plan
---

# Plan: T-038 — Command Center: MAPS Agentic OS 3-Column UI with 6-View Brain Canvas

## Approach
Implement the MAPS Agentic OS Command Center UI ("Screen" layer) into the Delivery Console as a high-density, 3-column command dashboard. The architecture strictly adheres to the MAPS "Show, Don't Store" principle: background deterministic code generates compact JSON graph and status caches (`brain.json`, `agenda.json`), while interactive UI buttons (such as running a routine) only drop request files into execution queue folders. The visualization engine uses vanilla JavaScript and an HTML5 Canvas to provide 6 distinct interactive views (Rings, Circle, Areas, Links, Timeline, 3D Orbit) at a capped 60fps budget.

## Slices

### Slice 1 — Backend Data Engine & Memory Map Scanner
Implements `console/server/brain.py` to traverse the workspace (`CLAUDE.md`, `knowledge-center/`, `.claude/skills/`, `console/config/schedules.toml`), cache `data/brain.json`, and expose REST endpoints for graph data, 14-day agenda, and system telemetry.

### Slice 2 — 6-View Brain Canvas Engine & Layout Transforms
Implements `console/static/brain-views.js` and `console/static/brain-canvas.js` supporting the 6 coordinate projections (Rings, Circle, Areas, Links, Timeline, 3D Orbit), smooth view interpolation, hover dimming, pan/zoom, and camera fly-to easing.

### Slice 3 — 3-Column Command Center Container & Widgets
Implements `console/static/command-center.js` and `console/static/styles-command.css` assembling the Left Column (Today clock, Heatmap, 14-day roadmap, Pulse), Center Canvas stage, and Right Column (Needs Human Review, Routines status board, System gauges).

### Slice 4 — HUD Inspector, In-App Reader Modal & Verification
Implements the bottom-right node inspector card, in-dashboard syntax/markdown reader modal, global search fly-to, hotkeys (`s`, `/`, `Esc`), and end-to-end test verification.

---

## Tasks

### [ ] T-038-01 — Backend Data Engine & Workspace Graph Generator (3 h)
- [ ] Implement `console/server/brain.py` with `build_brain_graph(root_dir)`:
  - Scans `CLAUDE.md` as root node (`kind: root`, `layer: core`).
  - Scans `knowledge-center/wiki/` and `knowledge-center/artifacts/` (`kind: memory/file`, `layer: memory`).
  - Scans `.claude/skills/*/SKILL.md` (`kind: skill`, `layer: skills`).
  - Scans `console/config/schedules.toml` and log files (`kind: routine`, `layer: routines`).
  - Extracts area categories (`business`, `clients`, `career`, `content`, `youtube`, `personal`, `system`).
  - Generates nodes `[{id, kind, label, area, layer, path, note, changed, links_count}]` and links `[{s, t}]`.
- [ ] Implement HTTP routes in `console/server/httpd.py`:
  - `GET /api/brain` (cached with file mtime validation).
  - `GET /api/command-center/agenda` (upcoming 14-day items & deep work timer).
  - `GET /api/command-center/system` (CPU, RAM, Disk percentages).
  - `POST /api/routines/queue` (drops `.request` file into `.claude/queue/`).
- [ ] Add unit test suite in `console/tests/test_brain.py`.
- **Done-criteria:** `GET /api/brain` returns valid JSON with all workspace nodes and links matching the schema; unit tests pass.
- **Basis:** Multi-file filesystem scan, graph construction, HTTP route registration, and test suite.
- **Depends on:** —

### [ ] T-038-02 — Brain 6-View Mathematics & Layout Transforms (2.5 h)
- [ ] Implement `console/static/brain-views.js`:
  - `layoutRings(nodes, width, height)`: Concentric layer radii, radial angular fanning grouped by area.
  - `layoutCircle(nodes, width, height)`: Equidistant perimeter distribution; chord link arcs.
  - `layoutAreas(nodes, width, height)`: Multi-cluster constellation with area signposts as cluster centers.
  - `layoutLinks(nodes, links, width, height)`: Force-directed simulation with charge repulsion and spring tension.
  - `layoutTimeline(nodes, width, height)`: Dual horizontal tracks: top = routines by run date; bottom = files by modification date.
  - `layoutOrbit3D(nodes, width, height, t)`: Spherical 3D coordinates projected with dynamic rotation matrix `rotY(t)` and depth alpha.
- **Done-criteria:** Deterministic coordinate mapping functions return `{x, y}` coordinates for all nodes in each of the 6 layout modes.
- **Basis:** Coordinate mathematics, geometry transforms, and projection algorithms.
- **Depends on:** T-038-01

### [ ] T-038-03 — High-Performance Canvas Renderer & Interaction Engine (3.5 h)
- [ ] Implement `console/static/brain-canvas.js`:
  - HTML5 Canvas stage with dark space theme (`#0c0d12`), glow filters, and subtle concentric orbital rings.
  - Node rendering: Hexagon for root, diamonds for skills, circles for files, concentric rings for routines, squares for apps.
  - Color palette by area (`business` blue, `clients` amber, `career` cyan, `content` purple, `youtube` pink, `personal` lime, `system` gray).
  - Smooth animation engine: 60fps capped interpolation between layout target positions.
  - Motion toggle: Subtle idle orbit motion when enabled.
  - Pan and zoom engine with mouse drag and wheel events.
  - Hover raycasting: Dims entire canvas except hovered node and its 1-hop connected neighbors.
  - Camera fly-to: Smooth cubic easing animating viewport to selected node coordinates.
- **Done-criteria:** Canvas renders all 6 modes fluidly at 60fps; view switching smoothly interpolates node positions; hover and pan/zoom work reliably.
- **Basis:** Canvas animation loop, coordinate interpolation, input handling, and rendering optimizations.
- **Depends on:** T-038-02

### [ ] T-038-04 — Floating HUD Inspector & In-App File Reader Modal (2 h)
- [ ] Implement floating HUD card (`console/static/brain-hud.js`):
  - Fixed bottom-right overlay card showing selected node name, area badge, layer badge, scope path, and linked nodes list.
  - Action buttons:
    - `OPEN`: Opens modal file viewer.
    - `COPY PATH`: Copies file path to clipboard with toast confirmation.
    - `VS CODE`: Opens `vscode://file/...` URI.
    - `FLY TO`: Re-centers camera on node.
    - `ONLY THIS AREA`: Filters canvas strictly to this area.
- [ ] Implement in-app markdown / code viewer modal (`console/static/brain-modal.js`):
  - Dark modal dialog fetching raw content via `/api/vault/file?path=...`.
  - Header with file path, monospace body with syntax/markdown formatting, close `✕` button and `Esc` key listener.
- **Done-criteria:** Clicking any node brings up the HUD card with accurate metadata; clicking `OPEN` displays the file content in the modal; clipboard copy works.
- **Basis:** DOM HUD overlay, modal component, clipboard API, and `/api/vault/file` integration.
- **Depends on:** T-038-03

### [ ] T-038-05 — 3-Column Command Center Shell & Dashboard Widgets (3 h)
- [ ] Implement `console/static/command-center.js` and register `Console.tab("center", ...)`:
  - Header: System status pills (`CORE`, `AGENTS`, `SYNC`, `IDLE`), branding (`CONTROL CENTER Agentic OS`), time/date, search input.
  - Left Column:
    - `TODAY`: Canvas mini-clock, deep work meter, gate review countdown, weekly heatmap matrix.
    - `NEXT 14 DAYS`: Chronological agenda feed with status badges.
    - `PULSE`: Overnight check summary.
    - `SKILLS DECK`: Drawer shortcut button (`tap s to run`).
  - Center Column:
    - View switcher pills (`RINGS`, `CIRCLE`, `AREAS`, `LINKS`, `TIMELINE`, `3D ORBIT`).
    - Area filter pills with counts and color dots.
    - Canvas container with zoom controls (`100%`, `-`, `+`), `Fit`, `Full`, `Names`, `Motion`.
  - Right Column:
    - `NEEDS REVIEW`: Overdue actions counter, cards with `2d`/`1d` badges, segmented ratio bar (`WARM • DM • COLD`).
    - `ROUTINES`: Daily fired counter, table (`TIME`, `ROUTINE`, `MACHINE`, `STATUS`), next highlighted routine, `+ Add` and `▶ Run all` queue buttons.
    - `SYSTEM MONITOR`: Resource gauges (`CPU %`, `RAM %`, `DISK %`).
- [ ] Implement `console/static/styles-command.css` with dark neon sci-fi styling and responsive flex/grid layouts.
- [ ] Mount script tags and navigation tab in `console/static/index.html`.
- **Done-criteria:** Full 3-column layout renders correctly; all widgets load real or mock-backed workspace state; tab is accessible from top nav.
- **Basis:** DOM layout assembly, CSS stylesheet, event wiring, and tab registration.
- **Depends on:** T-038-04

### [ ] T-038-06 — End-to-End Verification & Performance Profiling (1.5 h)
- [ ] Run backend tests (`pytest console/tests/test_brain.py`).
- [ ] Verify 60fps canvas performance under sustained animation.
- [ ] Verify "Show, Don't Store" contract: routine buttons create queue files in `.claude/queue/` without mutating source data.
- [ ] Verify responsiveness in browser and native Tauri window (`desktop/`).
- **Done-criteria:** All automated tests pass; canvas rendering is smooth and responsive; queue files write properly; layout scales properly.
- **Basis:** Test execution, browser performance profiling, and desktop app validation.
- **Depends on:** T-038-05

---

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-038-01 — Backend Data Engine & Workspace Graph Generator | 3.0 h | Graph crawler, HTTP routes, cache mechanism, unit tests |
| T-038-02 — Brain 6-View Mathematics & Layout Transforms | 2.5 h | Mathematical transforms for 6 projection algorithms |
| T-038-03 — High-Performance Canvas Renderer & Interaction Engine | 3.5 h | Canvas 60fps loop, shaders/colors, raycasting, camera fly-to |
| T-038-04 — Floating HUD Inspector & In-App File Reader Modal | 2.0 h | Bottom-right HUD, modal reader, clipboard & editor links |
| T-038-05 — 3-Column Command Center Shell & Dashboard Widgets | 3.0 h | Left/Right widget columns, header, CSS theme, tab mount |
| T-038-06 — End-to-End Verification & Performance Profiling | 1.5 h | Pytest execution, fps profiling, queue validation |
| **Total** | **15.5 h** | |

### Acceptance Criterion Coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| Workspace files, skills, routines mapped to `{nodes, links}` | T-038-01 |
| 6 interactive views (Rings, Circle, Areas, Links, Timeline, 3D Orbit) | T-038-02, T-038-03 |
| Hover dimming, selection, and smooth camera fly-to animation | T-038-03 |
| Floating HUD card with Open, Copy Path, VS Code, Fly To actions | T-038-04 |
| In-dashboard markdown/code viewer modal | T-038-04 |
| Left Column: Today clock, Deep work, 14-day roadmap, Pulse | T-038-05 |
| Right Column: Needs Review overdue cards, Routines board, System gauges | T-038-05 |
| Action buttons write to queue without modifying source data | T-038-01, T-038-05, T-038-06 |
| 60fps frame budget maintained on standard laptop hardware | T-038-03, T-038-06 |

---

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| Large node count causes canvas frame drops | Med | Med | Spatial indexing / grid binning for raycasting; skip off-screen labels; cap particle animation | Builder | T-038-03 |
| Workspace crawl latency on large git repos | Low | Med | Cache `brain.json` with timestamp invalidation; only re-index on demand or file mtime change | Builder | T-038-01 |
| Layout overflow on smaller laptop screens | Med | Low | CSS media queries collapsing left/right sidebars into slide-out drawers below 1200px width | Builder | T-038-05 |

---

## Dependencies
- Blocks: —
- Blocked by: —

## Links
- [[T-038-summary]] · [[T-038-analysis]] · [[T-038-requirements]] · [[T-038-decision-log]] · [[T-038-plan]] · [[T-038-progress]] · [[T-038-verification]]
