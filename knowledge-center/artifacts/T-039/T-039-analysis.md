---
ticket: "T-039"
artifact: analysis
created: "2026-10-06"
---

# Analysis: T-039 — Needs you panel and panel freshness

## Context

User decisions of 2026-10-06 (from [[INV-2026-10-06-maps-os-ui-adoption-dossier]]): (1) a list reserved for what only a person can resolve ("Needs you"), separate from items that need repair; (2) every panel shows its own timestamp and is marked STALE after a threshold instead of hiding or silently showing old data. Out of scope: routines board ([[T-040-summary]]), brain views ([[T-038-summary]]), clock, heatmap, deep-work bar, gate countdown, system gauges. Full fact table with sources: [[T-039-context-snapshot]].

## Current State

- `needs_attention()` builds six lists in one payload (`console/server/overview.py:36-100`): blocked, stale, unowned (per open ticket, `:44-60`), pending questions with status `open` or `answered` (`:22`, `:61-66`), live approvals (`:68-70`), runs in `failed|timed_out|scheduled_retry` (`:21`, `:72-85`). Each list is cut to 8 (`:90-95`); counts are exact (`:96-99`).
- Overview renders it as ONE panel "Needs attention" (`console/static/overview.js:272-303`, collapse id `ov.attention`) and the nav badge sums all six counts (`console/static/app.js:286-295`).
- Nothing in the Overview can clear an item: rows only navigate (`overview.js:18-25`). Items leave when the underlying state changes (a tracker status, an approval decision, a run state).
- No panel has a timestamp. `/api/overview` carries no `generated_at` (grep over `console/server` finds none), and the page renders it once per visit of the tab (`overview.js:252-253`, `app.js:238-247`); only the nav badge re-fetches, every 30 s (`app.js:693`). A tab left open therefore shows arbitrarily old data with no sign of it. The Jobs and Scheduled panels fetch once each (`overview.js:179-250`); a failed reload leaves the old rows in place without a word (`:182-198`).
- The static export bakes `full_overview()` output into `data.js` (`console/server/export.py:50-52,141-147`); Jobs and Scheduled are not captured there so their panels do not render (`core.js:150-158`, `overview.js:198,248`).
- Shared preferences (T-036) are view-state only; the server never acts on one (`console/server/prefs_store.py:11-14`).

## Key Findings

- **Verified, as the dossier said:** the list mixes human-wait and repair items; there is no per-panel timestamp or STALE marker; approvals are answered by a person in the console or Telegram (`agent_approvals.py:172-201`, `telegram_bot.py:246-264`); the badge sums everything.
- **Correction 1: "answered" questions are not a human wait.** The question lifecycle is `open -> answered -> resolved -> closed`; `answered` means a person already answered and the answer is "not yet folded into the source artifact" (`.claude/skills/questions/SKILL.md:29-31`), a job the agent does. Only `open` waits for a person. The summary and dossier listed "open or answered" under human-only; this analysis puts `answered` under repair (D-3; the user may override, Q1).
- **Correction 2: "reviews waiting" needs no new kind.** The review loop already opens one critical question when it escalates (`verb_handlers.py:640-643`), which Needs you shows as an open question; the follow-up `human_decision` is a gated verb answered through an approval card (`config/agents.toml:119-127`), which Needs you shows as an approval. A third entry for `review_escalated` (`close_check.py:261`) would list one wait twice.
- **Correction 3: line numbers.** Jobs and Scheduled are at `overview.js:179-250` (dossier `:176-251`); `needs_attention` is `:36-100` (summary `:34-96`). The claims themselves were accurate.
- **"The agent never marks done" is a property of the Overview, not of the system.** Nothing in `overview.py`/`overview.js` writes. But an agent with the console CLI can still run `tracker update ... status=answered`, and `review-round human_decision` is audit-checked only ("the verb cannot verify the caller", `config/verbs.toml:174-176`) plus approval-gated for agents (`agents.toml:122-126`). The requirement is stated and tested at the Overview level and the limit is recorded (D-15).
- **Real data matters for the cap.** Measured 2026-10-06: 9 open questions across 3 tickets, 0 approvals, 0 runs; the existing cap of 8 would hide one human-only item. Payload build time 0.11 s.
- **Name collision.** `stale` already means "ticket idle >= `stale_days`" (`render.py:59`, tile "Stale" `overview.js:265`). The data-freshness mark is a different thing and must read distinctly (D-9).
- **Freshness cannot depend on the heartbeat succeeding.** `probe()` runs `onHeartbeat` only when `/api/config` answers (`app.js:439-441`), so a heartbeat tick would never mark data STALE while the server is down (D-8).
- **Collapsed panels hide their body** (`styles.css:522`, `core.js:297`), so the STALE mark lives in the header (D-12).
- **Test pins to respect:** `test_splitter.py:1118-1141` fixes `overview.js` to exactly six `collapse: {id: "ov.*"}` literals and 18 section ids overall; `:1146-1160` pins the keydown handler text on `attnPanel`; `test_stylesheet.py` (duplicate bare class; hyphenated JS classes must exist; baseline failure `.ob-count` is not ours); `test_ui_constraints.py` (ES5).
- **Consumers of the payload:** nav badge (`app.js:289-292`), Overview (`overview.js:257-295`), Assistant home reads only `attention.blocked` (`assistant.js:123`), static export, `kanban overview` CLI (`kanban.py:141`), `test_attention.py`; copy in `about.js:25` mentions "blocked, stale and unowned". No agent file, Telegram path or MCP tool reads `needs_attention`.

## Research

None needed: no tech choice is open (no new dependency; `<time>`, `Date.parse`, one `setInterval` already exist in the platform). `tech-select` not invoked.

## Recommended Path

Small, additive change in three layers: (1) `overview.py` adds `needs_you`/`needs_repair`, counts and `generated_at`, keeping legacy keys so the Assistant home and old consumers keep working; (2) `core.js` adds a `fresh` option to `C.panel` with one shared timer and a pure age function; (3) `overview.js` renders two panels and feeds `asOf` to every data panel; `app.js` badge counts Needs you only and names it. No new file, no new script tag. Requirements: [[T-039-requirements]]; decisions: [[T-039-decision-log]].

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
- Upstream: [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · [[T-036-summary]]
