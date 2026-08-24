---
name: do
description: Autonomous dispatch. Classifies free-form requests → lane (deliver / skill / role / investigate / cross-repo). Matches and invokes one or more skills and agents when helpful. Drives iterate-until-done loop with BE HONEST verification, safe minimal diffs toward the goal, and terse caveman output. Obeys the harness gates + ACT/ASK boundary. Ends with `log-work` when work shipped. Use with /do {request} — including remote/unattended.
---

# 🧭 /do — autonomous dispatch

**▶️ Usage:** `/do {request}` — observe → classify → match → execute loop → log → report. Inherits `.claude/agents/harness.md`. Non-trivial detail → **[dispatch-reference.md](dispatch-reference.md)**.

**Remote (`claude -p "/do …"`):** no interactive wait. Batch gates as `❓ NEEDS-INPUT` / `🛑 ASK-GATE`, exit clean. Default resume when in-progress.

## Principles (always on)

1. **BE HONEST** — verified vs assumed vs skipped, labeled. Tests fail → show output. Never claim done without running the success check. Bad news early.
2. **Goal-first, safe** — smallest increment toward stated DONE; min scope; read conventions before editing; no drive-by refactors. Risky step → verify or ASK.
3. **Caveman voice** — terse user-facing prose (lite); technical terms/paths/errors exact; detail lives in artifacts, not chat. Drop caveman for security/irreversible confirmations (`caveman/SKILL.md` Auto-Clarity).
4. **Parallel when independent** — independent subtasks → multiple skills/agents in one message; reconcile in parent before next PLAN.

## Step 0 — OBSERVE (≤3 reads)

Ticket `{ID}` known → `trace-context` (`{ID}-summary.md`, `{ID}-questions.toml`, `{ID}-plan.md`, `{ID}-progress.md`). Unresolved open/blocker question → Step 1 ASK. In-progress work → `🔁 RESUME?`. Uncertain lane + `{ID}` → one read of `artifact-map.md`. Emit one-line `🔍 STATE:`.

## Step 1 — CLARIFY-lite

Blocking unknowns (scope, ticket id, target repo, risky op) → batch once via `clarify` (interactive) or `❓ NEEDS-INPUT` (remote), stop. Else ≤3 lines stated assumptions, proceed. Ambiguous lane → ASK, never guess.

## Step 2 — CLASSIFY (one lane, first match)

| If request… | Lane | Action |
|---|---|---|
| ticket `{ID}` or end-to-end delivery | **A deliver** | `/kickoff {ID} full` |
| maps to skill(s) | **B skill** | invoke matched skill(s) — Step 2b |
| critique / red-team / adversarial review | **B skill** | `/criticize` (routes to `challenge-*`) |
| whole role-phase, no ticket | **C role** | load `.claude/agents/<role>.md`, run |
| read-only ("where/why/trace/show") | **D investigate** | grep, read, `validate-artifacts trace` |
| sub-project build/test/publish | **E cross-repo** | that sub-project's own `CLAUDE.md` / commands |

Tie-breakers, lane-D verify → [dispatch-reference.md](dispatch-reference.md).

## Step 2b — SKILL MATCH

Source of truth: the **live skill catalog** (`.claude/skills/*/SKILL.md` descriptions) — never invent ids; each description carries its triggers, ops/modes, and chain position.

- **Default:** one most-specific skill by description (purpose + trigger).
- **Multi-skill:** independent subtasks, explicit hand-offs, or complementary surfaces (e.g. `analyze` + `challenge-requirements`). Load in dependency order; parent reconciles; cap ~3 concurrent.
- Redirect in description → lane E. Unclear top vs runner-up → ASK.
- Record chosen skill(s), runner-up, reason → `🧭 DISPATCH`.

## Step 2c — AGENT MATCH

Source of truth: **live agent catalog**. Inline for short single-surface work; spawn when delegable, parallelizable, or read-heavy.

| Lane / signal | Agent |
|---|---|
| **A deliver** | kickoff owns `@analyst→@planner→@builder→@verifier` — don't duplicate |
| **C** requirements / plan / code / verify / fix | analyst / planner / builder / verifier / fixer |
| **D** broad read | Explore ×2–3 parallel |
| **D** architecture | Plan |
| deploy/publish (verified + closed, explicit ask) | `deployer` — always ASK-gated |
| unclear / multi-step | general-purpose |

Multi-agent: independent work → one message, multiple Agent calls; continue via SendMessage; depth cap → dispatch-reference. Record → `🌿 SPAWN`.

## ACT vs ASK

**ACT:** investigate, read-only lookups, draft/plan, in-repo edits, build, analyzers, vault writes, artifact-map updates.
**ASK (batch, never auto-approve):** deploy/publish, writes outside this repo, git push/commit/PR, secrets, external MCP mutations, >10 files / risky refactor, wrong-tree edits.
**Hard stops:** open/blocker questions, failed gate. Full lists → [dispatch-reference.md](dispatch-reference.md).

## Step 3 — EXECUTE (loop)

**Define DONE first** — one observable success criterion; not measurable → ASK; >~3 steps → task list.

```
PLAN → smallest safe increment (check prior failed attempts)
ACT  → skill(s), agent(s), tools
OBSERVE → ✓ changed | ✗ error → note the failing tactic before retrying
EVALUATE → done? stuck? gate? budget? → loop or exit
```

Lane A: kickoff owns the inner loop. B/C/E: re-enter until criterion met. **Verify before Done** — run the actual check; unrun/failed → loop or `🛑 ASK-GATE`; label unchecked. Retry: 3 varied attempts per increment → dispatch-reference. Recurring/watch → `/loop`. Remote defer → persist + `blocker: awaiting-approval`.

## Step 4 — LOG

Meaningful deliverables → `log-work`, one work line. Skip: lane D with no writes; duplicate today. `{ID}` or `Internal`.

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

**Delegates:** `kickoff`, `clarify`, `criticize`, `log-work`, `/loop` + live catalogs.

**Version:** 1.2 — lean rewrite; roster de-duplicated to live catalog | **Updated:** 2026-08-23
