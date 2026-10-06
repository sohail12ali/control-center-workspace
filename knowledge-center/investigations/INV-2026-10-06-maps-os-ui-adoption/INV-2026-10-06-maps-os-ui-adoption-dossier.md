---
id: INV-2026-10-06-maps-os-ui-adoption
date: 2026-10-06
owner: Sohail Ali
type: roadmap-dossier
status: approved
---

# MAPS "AI OS" UI — what Control Center can adopt

Source: a YouTube video the user extracted into `scratch/` (transcript, a 7-page guide, 14 UI frames). It describes a personal operating system in four layers, **M**emory, **A**gent, **P**ulse, **S**creen, with a dashboard whose centre is a graph of the user's real files drawn six ways. The video's own message: the dashboard is about 20% of the value; the files and routines are the rest; **show, don't store** (every panel reads a file something else wrote).
Classification: **feature/roadmap**. Method: reading the transcript, guide and frames, plus one read-only Explore pass over `console/` (read, not run). Paths below are relative to the repo root.

Another session had already opened [[T-038-summary]] from the same video as a new `center` tab with a new `brain.py`. This dossier re-scopes it onto the existing Vault tab and splits the rest into three small tickets.

---

## 1. Ground truth

### Already covered here — do not rebuild

- **Vault graph** (`console/static/vault.js`, `console/server/vault.py`, `features/vault_feature.py`): force-directed canvas (`tick()` ~:149-206), two canvases (`vaultBase`, `vaultFx`, :787-789), `GET /api/vault/graph` (`vault.py` `build_graph` :100-167; nodes `{id,label,kind,links,folder,md}`; edges wikilink + contains; 5000-file cap with `truncated`), size by link count, hover-dim on the overlay canvas (:332-370), search + isolate (:674, :834-840), read-only viewer `/api/vault/file` (:558-597, 256 KB, text types), fit (:473), arrow-key navigator, splitter handles (T-037). **Scope: `knowledge-center/` only.**
- **Needs-attention list** (`console/server/overview.py:34-96`): blocked, stale and unowned tickets, open or answered questions, pending approvals (`agent_approvals.REGISTRY.pending_all()`), failed or timed-out runs. Feeds the Overview panel and the sidebar badge. Agents never close these; Telegram answers approvals (`telegram_bot.py:246-264`).
- **Routines** (`console/server/schedules.py`, `console/config/schedules.toml`, ticker `:180-250`; run records in `console/.cache/jobs/`, `jobs.py`, 2 concurrent; Overview "Jobs" and "Scheduled" panels `overview.js:176-251`; `/api/jobs` with cancel). The UI already says nothing fires while the console is not running. Two schedules exist, both parked.
- **Checks** (`console/server/harness_lint.py`: skill/agent references and orphan skills, a parked weekday `harness-lint` schedule; `workspace_check.py`; the `validate-artifacts` skill, not scheduled).

### Gaps

| Gap | Evidence |
|---|---|
| Graph covers only `knowledge-center/`; no skills, agents, tickets, routines or runs | `vault.py:13` (`_vault_root`) |
| Only the force layout; no rings, areas, timeline | grep of `vault.js` |
| Colour by kind only, every node a circle, no legend, node card has no note, copy path or fly-to, search has no fly-to | `vault.js:56-82, 296-310, 558-597` |
| No per-panel timestamp or STALE marker | none found in `core.js`/`overview.js` |
| The attention list mixes "needs a human" with "needs repair" (failed runs, stale tickets) | `overview.py:34-96` |
| No routines board (no last-run status per schedule) and no per-routine Run-now button | `overview.js:176-251` |
| No scheduled link check over `artifact-map.md` and `## Links` blocks | `harness_lint.py` covers skills/agents only |
| The Vault is dropped from the static export | `export.py:71-72`, `vault_feature.py:9` (`needs_live`) |

---

## 2. Verdict per idea (user decisions 2026-10-06)

| Video idea | Verdict | Ticket |
|---|---|---|
| Six-view brain graph from one JSON, as a mode of the Vault | **INCLUDE** | [[T-038-summary]] |
| Colour by area, shape by kind, legend isolate, richer node card (note, copy path, fly-to), search fly-to | INCLUDE | [[T-038-summary]] |
| Whole-workspace nodes (skills, agents, tickets, routines, runs) | INCLUDE | [[T-038-summary]] |
| Rings, areas, links, timeline views first; circle if cheap | INCLUDE | [[T-038-summary]] |
| 3D orbit | DEFER (least useful, costs most) | [[T-038-summary]] |
| "Needs you": the only list that waits for a human; the agent never marks done | INCLUDE | [[T-039-summary]] |
| Every panel shows its own timestamp, marked STALE rather than hidden | INCLUDE | [[T-039-summary]] |
| Routines board + play button (Run now through the existing `/api/jobs`, not a `.claude/queue/` file drop) | INCLUDE, adapted | [[T-040-summary]] |
| Nightly signpost/link checker; "every fact has one home" | INCLUDE | [[T-041-summary]] |
| Today / next 14 days | DEFER (no forward agenda exists) | — |
| Clock, heatmap, deep-work bar, gate countdown, CPU/RAM gauges | SKIP (the author's personal cadence) | — |
| VPS + Tailscale + always-on agent + voice bot | SKIP (cost, terms; Telegram bot exists) | — |
| Interview-first memory map | SKIP (`ticket-draft`, `clarify`, `console context` already do this) | — |

---

## 3. Design notes for T-038 (analyst to confirm)

- **Data:** extend `build_graph` (or a sibling builder it calls) with `area`, `layer`, `kind` (root, area, project, skill, agent, ticket, memory, note, routine, run), `path`, `note`, `changed`; keep the cap and `truncated`. Define OUR areas and layers in a small config (for example `console/config/brain.toml`), never the video's. The analyst proposes the mapping and asks the user.
- **Views:** pure layout functions in a new `console/static/brain-views.js`, plus today's force layout as "links"; the choice persists through `Console.prefs` as one `brain` object. No d3, no CDN.
- **Constraints:** ES5 IIFE (no `=>`, no statement-leading `let/const`; `console/tests/test_ui_constraints.py`); every class used from JS exists in `styles.css`, no duplicate bare selectors (`test_stylesheet.py`); script order (`test_plugins.py`); the 900 px cliff and the wide-only splitter; the force sim is O(n²)/sqrt(n), so measure whole-workspace node counts before choosing layouts; decide whether a brain payload joins `_TAB_DATA` in `export.py:47` or the Vault stays live-only.

## 4. Order and caveats

[[T-039-summary]], [[T-040-summary]] and [[T-041-summary]] are small and independent; [[T-038-summary]] is the large one and edits `vault.js` and `styles.css`, so do not run it in parallel with another ticket touching those files.
T-038 was created by another session with an empty requirements template while its stage said CANONICAL; it is reset to GROUND and its old plan is superseded, not built.

## 5. Evidence status

- **From reading:** the video's transcript, guide and frames; every `console/` claim above comes from a read-only code pass, not from running the app.
- **Unverified:** whether anything outside `console/` sets a Content-Security-Policy (none found inside); the real node count of a whole-workspace graph; whether the T-037 splitter hunks are the final shipped ones.

## Links
- [[T-038-summary]] · [[T-039-summary]] · [[T-040-summary]] · [[T-041-summary]]
- Related: [[T-037-summary]] (splitters, layout prefs) · [[T-036-summary]] (server-side prefs) · [[INV-2026-10-05-micdrop-adoption-dossier]]
