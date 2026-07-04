---
name: do
description: Autonomous dispatch. Classifies free-form requests → lane (deliver / skill / role / investigate / cross-repo). Matches and invokes one or more skills and agents when helpful. Drives iterate-until-done loop with BE HONEST verification, safe minimal diffs toward the goal, and terse caveman output. Obeys the 5 harness gates + ACT/ASK boundary. Ends with `log-work` when work shipped. Use with /do {request} — including remote/unattended.
---

# 🧭 /do — autonomous dispatch

**▶️ Usage:** `/do {request}` — observe → classify → match → execute loop → log → report. Inherits `.claude/agents/harness.md`. Non-trivial detail → **[dispatch-reference.md](dispatch-reference.md)**.

**Remote (`claude -p "/do …"`):** no interactive wait. Batch gates as `❓ NEEDS-INPUT` / `🛑 ASK-GATE`, exit clean. Default resume when in-progress.

## Principles (always on)

1. **BE HONEST** — Report verified vs assumed vs skipped/deferred. Tests fail → show output. Never claim done without running the success check. Bad news early.
2. **Goal-first, safe** — Smallest increment toward stated DONE. Min scope; read surrounding code/conventions before edit; no drive-by refactors or unrelated fixes. If a step risks breaking other behavior → verify or ASK.
3. **Caveman voice** — User-facing prose: terse, no filler/hedging (caveman **lite**). Technical terms, paths, errors exact. Full detail lives in artifacts, code, citations — not chat padding. Drop caveman for security/irreversible confirmations (see `.claude/skills/caveman/SKILL.md` Auto-Clarity).
4. **Parallel when independent** — Independent subtasks → multiple skills and/or agents in **one message**; reconcile in parent before next PLAN.

## Step 0 — OBSERVE (≤3 reads)

If ticket `{ID}` known: run `trace-context` (reads `{ID}-summary.md`, `{ID}-questions.md`, `{ID}-plan.md`, `{ID}-progress.md`). Unresolved open/blocker question → Step 1 ASK. In-progress or unchecked plan tasks → `🔁 RESUME?`. Log dedup for Step 4. Uncertain lane + `{ID}` → one targeted read of `artifact-map.md`. Emit one-line `🔍 STATE:`.

## Step 1 — CLARIFY-lite (gate 1)

Blocking unknowns (scope, ticket id, target repo, risky op) → batch once via `clarify` (interactive) or `❓ NEEDS-INPUT` (remote), stop. Else ≤3 lines stated assumptions, proceed. Ambiguous lane → ASK, never guess.

## Step 2 — CLASSIFY (one lane, first match)

| If request… | Lane | Action |
|---|---|---|
| ticket `{ID}` or end-to-end delivery | **A deliver** | `/kickoff {ID} full` |
| maps to skill(s) | **B skill** | invoke matched skill(s) — Step 2b |
| critique / red-team / challenge plan / challenge implementation / adversarial review | **B skill** | `/criticize` (or explicit `challenge-plan` / `challenge-implementation` / `challenge-requirements`) |
| whole role-phase, no ticket | **C role** | load `.claude/agents/<role>.md`, run |
| read-only ("where/why/trace/show") | **D investigate** | grep, read, `trace` |
| sub-project (build/test/publish in a workspace-folder repo) | **E cross-repo** | route to that sub-project's own `CLAUDE.md` / commands |

Tie-breakers, lane-D verify → [dispatch-reference.md](dispatch-reference.md).

## Step 2b — SKILL MATCH

Source of truth: **live skill catalog** — never invent ids. CCW's roster spans setup/state (`kickoff`, `trace-context`), spec (`draft-requirements`, `analyze-context`, `identify-gaps`, `enrich-requirements`, `iterate-requirements`, `extract-stories`, `challenge-requirements`, `freeze-requirements`, `template`, `consolidate`), planning (`analyze-components`, `breakdown-tasks`, `create-implementation-plan`, `estimate-development`, `generate-effort-forecast`, `replan`, `challenge-plan`, `plan`, `plan-effort`, `risk-scan`, `progress-tracker`), build/fix (`fix`, `evolve`), verify (`verify`, `challenge-implementation`, `criticize`, `validate-artifacts`, `check-artifact-links`, `trace`, `generate-test-cases`), tracking (`questions`, `bugs`, `todos`, `clarify`, `handoff`, `reconcile`, `standup`), decisions (`tech-select`, `analyze`), workspace hygiene (`log-work`, `work-summary`, `optimize-cursor-artifacts`, `project-layout`, `harness-standards`, `caveman`, `do`).

- **Default:** one most-specific skill by `description` (purpose + trigger).
- **Multi-skill:** when subtasks are **independent**, a description **explicitly hands off**, or **complementary skills** cover different surfaces (e.g. `analyze-context` + `identify-gaps`). Load in dependency order; parent reconciles. Cap ~3 concurrent unless a pipeline says more.
- Redirect in description → lane E. Unclear top vs runner-up → ASK.
- Record chosen skill(s), runner-up, reason → `🧭 DISPATCH`.

## Step 2c — AGENT MATCH

Source of truth: **live agent catalog**. Inline for short single-surface work; **spawn** when delegable, parallelizable, or read-heavy.

| Lane / signal | Agent |
|---|---|
| **A deliver** | kickoff owns `@analyst→@planner→@builder→@verifier` — don't duplicate |
| **C** requirements / plan / code / verify / fix | Analyst / Planner / Builder / Verifier / Fixer |
| **D** broad read | Explore ×2–3 parallel |
| **D** architecture | Plan |
| unclear / multi-step | general-purpose |

CCW has no `deployer` agent — deploy/publish requests stay lane B/E (skill or sub-project) and always ASK first.

**Multi-agent:** independent work → multiple Agent calls in one message; continue via SendMessage; depth cap → dispatch-reference. Record → `🌿 SPAWN`.

## ACT vs ASK (summary)

**ACT:** investigate, read-only vault/artifact reads, draft/plan, in-repo edits, build, analyzers, vault writes, artifact-map updates.

**ASK (batch, never auto-approve):** deploy/publish, non-read writes to systems outside this repo, git push/commit/PR, secrets, external MCP mutations, >10 files / risky refactor, wrong-tree edits.

**Hard stops:** open/blocker questions, failed gate → stop. Full lists → [dispatch-reference.md](dispatch-reference.md).

## Step 3 — EXECUTE (loop)

**Define DONE first** — one observable success criterion. Not measurable → ASK. >~3 steps → task list.

```
PLAN → smallest safe increment (check prior failed attempts for known-bad tactics)
ACT  → skill(s), agent(s), tools
OBSERVE → ✓ changed | ✗ error → note the failing tactic before retrying
EVALUATE → done? stuck? gate? budget? → loop or exit
```

Lane A: kickoff owns inner loop. B/C/E: re-enter until criterion met or terminate.

**Verify before Done** — run actual check (rebuild, tests, re-read artifact, Verifier). Unrun/failed → loop or `🛑 ASK-GATE`. Report only what passed; label unchecked.

**Retry:** N=3 varied attempts per increment → [dispatch-reference.md](dispatch-reference.md).

**Recurring/watch** → `/loop` (no sleep-spin). **Remote defer** → persist + `blocker: awaiting-approval`, never auto-approve.

## Step 4 — LOG

Meaningful deliverables → load `log-work/SKILL.md`, append one work line. Skip: lane D with no writes; duplicate today. `{ID}` or `Internal`.

## Step 5 — REPORT

Harness contract (`harness.md`). Caveman TL;DR first:

```
📱 TL;DR:     {≤140 chars — shipped or blocked}
🧭 DISPATCH:  {lane} → {target} [{skill(s) over runner-up — reason}]
🌿 SPAWN:     {agent(s) | inline — reason}
🛠️ SKILLS:    {kebab-case ids invoked, order; cap 8}
🛑 ASK-GATE:  {none | stopped: <action>}
STATUS:       ✅ done | 🛑 blocked | ❓ needs-input
```

## Delegates

`kickoff`, `clarify`, `criticize`, `log-work`, `/loop` + skills/agents from live catalogs.

**Version:** 1.0 — ported from lc-wms-cursor-config `/do` v2.1, genericized for CCW's 6-agent roster (no deployer) and workspace-folder cross-repo model | **Updated:** 2026-07-04
