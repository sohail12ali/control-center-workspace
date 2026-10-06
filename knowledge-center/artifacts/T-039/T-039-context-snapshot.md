---
ticket: "T-039"
artifact: context-snapshot
status: final
created: "2026-10-06"
last_updated: "2026-10-06"
scope: codebase + history
---

# Context Snapshot: T-039

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only. Every bullet cites a source (line numbers as of HEAD `2040634`; they drift).

## 1. Intent (echo)

A list for what only a person can resolve ("Needs you") separate from what needs repair, and a timestamp plus STALE mark on every panel instead of hiding or silently showing old data ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]).

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers | Reuse | Source |
|---|---|---|---|---|
| Attention payload | `needs_attention` | server | extend, additive | `console/server/overview.py:36-100` |
| Overview page | `render`, `attnGroup` | UI | split one panel into two | `console/static/overview.js:14-35,252-369` |
| Panel helper | `C.panel`, `collapsible`, `group`, `empty` | UI | add `opts.fresh` | `console/static/core.js:228-245,283-322,328-349` |
| Nav badge | `refreshBadges` | UI | count Needs you only | `console/static/app.js:266-295,693` |
| Heartbeat and version reload | `probe`, `onHeartbeat`, `checkVersion` | UI | NOT reused for the clock (offline case) | `console/static/app.js:347-441` |
| Shared prefs | `C.prefs`, `prefs_store` | UI/server | `staleAfterSecs` view key | `console/static/core.js:520-640`; `console/server/prefs_store.py:11-14` |
| Static export | `export_static`, `_TAB_DATA` | server | `generated_at` rides `full_overview` | `console/server/export.py:50-52,141-147` |
| Static fetch | `get` with `IS_STATIC` | UI | Jobs/Schedules not captured, so panels absent | `console/static/core.js:150-158` |
| Approvals | `Approvals.pending_all/decide` | server | people answer in console or Telegram | `console/server/agent_approvals.py:172-208`; `console/server/telegram_bot.py:246-264` |
| Tracker statuses | questions `open/answered/resolved/closed` | server | `answered` = not yet applied | `.claude/skills/questions/SKILL.md:29-31`; `console/server/trackers.py:31-42` |
| Run states | `failed, timed_out, scheduled_retry, needs-approval, ...` | server | repair kinds; `needs-approval` not emitted today | `console/server/runs.py:20-27`; `console/server/run_sync.py:184` |
| Review escalation | `record_review`, `review_escalated` | server | already opens a critical question | `console/server/tickets.py:432-466`; `console/server/verb_handlers.py:640-643`; `console/server/close_check.py:261` |
| Assistant home | reads `attention.blocked` | UI | keep that key | `console/static/assistant.js:116-123` |
| CLI | `kanban overview` prints `full_overview` | CLI | additive payload ok | `console/kanban.py:141` |
| Overview copy | tab blurb | UI | update wording | `console/static/about.js:25` |

### Existing patterns to reuse
- Panel header chip and counts: `C.el("span", {class: "chip warn"...})` (`overview.js:301`); chip tones `.chip.warn/.danger/.zero` (`styles.css:448-459`).
- Empty state `C.empty(title, hint, icon)` (`core.js:343`); rows `.lrow` / `.lrow.clickable` / `.kbd` (`styles.css:811-819`).
- Status region with text written only when changed (`app.js:483-490`, T-036) for the accessibility rule.
- Server UTC stamp `_now_iso()` `YYYY-MM-DDTHH:MM:SSZ` (`trackers.py:56-57`).

### Naming and architectural conventions in play
- ES5 IIFE, no `=>`/leading `let`/`const` (`console/tests/test_ui_constraints.py:1-60`).
- Hyphenated classes used from JS must exist in CSS; no repeated bare single-class rule (`console/tests/test_stylesheet.py:65-130`). New CSS mid-file (T-037 rule).
- Collapse ids are literal and pinned: seven in `overview.js` after this change (`console/tests/test_splitter.py:1118-1141`); enter-guard text pinned on `attnPanel` (`:1146-1160`).
- Preferences are view state; the server never acts on one (`prefs_store.py:11-14`).
- Page renders Overview on each tab visit (`app.js:238-247`); only the badge polls (30 s, `app.js:693`).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-036 | server-side prefs, heartbeat, `ui_version` reload | shipped | `prefs_rev` and version ride the heartbeat; heartbeat only fires on success |
| T-037 | splitters, foldable sections, `ov.*` ids | requirements frozen | shares `styles.css`, `core.js`, `app.js`; re-read before edit |
| T-016/T-020 | runs, claims, review loop | shipped | review loop opens a critical question |
| T-038, T-040 | brain views, routines board | siblings | out of scope; do not run in parallel on `styles.css` |

### Relevant commits / PRs
- `2040634` T-032 (HEAD) · `2a3d3ce` voice assets, synced preferences, MAPS tickets.

### Known incidents / regressions in this area
- Baseline test failure `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`), not ours ([[handoff-2026-10-06-pending-work]] section 5).

## 4. External Systems in the Loop

- Telegram bot (answers approvals; unchanged). No external service is added.

## 5. Preliminary Risks Spotted

- Cap 8 hides human-only items: measured 9 open questions on 2026-10-06 (`needs_attention` counts).
- Two tests pin the Overview panel ids and handler text; a new panel breaks them unless updated deliberately.
- A heartbeat-driven freshness tick would be silent while the server is down.
- `stale` already names ticket idleness; the new STALE mark can be misread.
- `core.js`, `app.js`, `styles.css` are shared with T-037 edits in a CRLF working tree.

## 6. Open Confirmations

- Whether the user wants `answered` questions in Needs you (Q1) and a repair count on the badge (Q2): defaults applied, not confirmed.
- Static export on `file://` was not run here; its behaviour is derived from `export.py` and `core.js` source.
- No browser was available to any agent; all [BROWSER] criteria are unverified.

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-06 | Read | `overview.py`, `overview.js`, `app.js`, `core.js`, `export.py`, `agent_approvals.py`, `telegram_bot.py`, `trackers.py`, `runs.py`, `tickets.py` | verify dossier claims |
| 2026-10-06 | Grep | `needs_attention`, `api/overview`, `attention` across repo | find consumers |
| 2026-10-06 | Read | `test_stylesheet.py`, `test_ui_constraints.py`, `test_splitter.py:1105-1160`, `test_attention.py` | constraints |
| 2026-10-06 | Bash | `needs_attention` and `full_overview` on the live repo (read-only) | counts and timing |
| 2026-10-06 | Bash | `kanban context T-039` | ticket state |

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
- Upstream: [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · [[handoff-2026-10-06-pending-work]] · [[T-036-summary]] · [[T-037-summary]]
