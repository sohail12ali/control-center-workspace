---
ticket: "T-021"
artifact: context-snapshot
status: final
created: "2026-10-01"
last_updated: "2026-10-01"
scope: codebase + history
---

# Context Snapshot: T-021

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source. Numbers were measured on 2026-10-01 against the working tree at `development` (HEAD `0c42658`); measurement scripts lived in the session scratchpad and are not deliverables.

**Command reference:**
- **Created/refreshed by:** `analyze T-021 context`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

---

## 1. Intent (echo)

Turn the honesty gates from policy into checks: a liveness contract for non-terminal tickets, an evidence-gated close, a skill-description lint, a plan-to-tasks boundary rule, a doc-drift audit, and an untrusted-content clause for the Assistant (dossier items 7, 8, 10-13, [[INV-2026-10-01-paperclip-adoption-dossier]] § 2 Tier 2).

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Harness lint (ERROR = broken, WARN = judgement) | `harness_lint.lint`, `Finding(level, code, path, message)` | `.claude/skills`, `.claude/agents`, `CLAUDE.md` | Add rules as `Finding`s; `_check_declared_counts` already compares CLAUDE.md roster numbers | `console/server/harness_lint.py:9-25, 246-317` |
| Lint exit policy | `cmd_harness_lint`: exit 1 on errors, on warnings only with `--strict` | CLI, CI job `harness`, pre-commit | A WARN rule cannot turn CI red | `console/kanban.py:341-355`; `.github/workflows/verify.yml` (job `harness`) |
| Pre-commit gate | Runs harness lint only if staged paths match `^(\.claude/(skills\|agents)/\|CLAUDE\.md)` | git hook | A ticket-state change never reaches it | `.githooks/pre-commit:16-18` |
| Blocking items | `trackers.blockers` = open critical questions + unverified critical bugs; todos/comments never block | tracker | close-check reuses it; no second blocking engine | `console/server/trackers.py:38-44, 225-233` |
| Lane move | `tickets.move` validates the lane name only; verb `ticket-move` (`needs_confirm`) and CLI `ticket move` call it; board drag calls it from `boards_feature` | verb, CLI, HTTP | One guarded wrapper at the verb and CLI; raw writer unchanged | `console/server/tickets.py:176-188`; `verb_handlers.py:411-421`; `kanban.py:68-69`; `features/boards_feature.py:65` |
| Lane vocabulary | open, in-progress, blocked, verify, done (`terminal = true`); boards are config, `lanes_for` exposes the terminal flag | `console/config/boards/tickets.toml` | Use `terminal` instead of the literal `done` | `console/server/boards.py:60-85` |
| Plan task parser | `context.plan_tasks` returns `{exists, parsed, tasks[{id,title,done}]}` and the `plan-status` verb | context | `plan_open` check reuses it | `console/server/context.py:67-91` |
| Context digest | `context.build` / `format_markdown`, additive sections, truncation stated | trace-context | A ticket-liveness line follows T-020 FR-23's additive pattern | `console/server/context.py:166-222` |
| Run store | `runs.create/get/list_runs/set_state`; ids are `uuid4().hex[:12]`; stored under `console/.cache/runs` (gitignored) | runs | `run:<id>` evidence refs resolve via `runs.get` | `console/server/runs.py:14-23, 58-110`; `.gitignore:66` |
| Audit | `audit.record(repo, action, actor=, target=, detail=, outcome=)`, never fatal | audit | New actions `ticket.close`, `ticket.close.override`, `ticket.block` | `console/server/audit.py:94-119` |
| Verb registry | `verbs.toml` rows plus handlers `(repo_root, ticket=None, **args)` in `verb_handlers.py`; MCP/HTTP/CLI derive from it; `needs_confirm` is a stray-call guard, not the human gate | verbs | 3 new rows | `console/config/verbs.toml:1-30, 116-122`; `verb_handlers.py:72-74` |
| Stop hook | Holder-side reminder: claimed ticket with no update since the claim | `stop_hook.py` | Isolation: "stale" there means no update, not a dead owner | `console/server/stop_hook.py:1-110` |
| Persona text cap | `persona_text` cuts at `PERSONA_CAP = 4_000` chars with a notice; same function feeds CLI `system_append` and `openai_api` | prompt_build | FR-5 must fit under it | `console/server/prompt_build.py:40, 69-105` |
| Approval gate | `gated_tools` per backend row in `agents.toml`; desktop clipboard-read and screenshot are gated, `console_desktop_ocr` is not | agents.toml | The untrusted-content clause is defence in depth behind real gates | `console/config/agents.toml:110-121, 245-252`; `verb_handlers.py:271-282` |

### Existing patterns to reuse
- WARN-never-red lint with a test per rule that proves it fires on a planted fault and stays quiet on a clean tree — `console/tests/test_harness_lint.py:1-8, 58-76`.
- Fixture workspace `repo` (tmp ws with `console.toml`, `tickets.toml`, `agents.toml`) and injectable clocks — `console/tests/conftest.py:120-130`; `test_mutation_verbs.py:19-24`.
- Refusals as `{"ok": False, "error": ...}` plus an audit row with `outcome="error: ..."` — `verb_handlers.py:437-458` (`ticket_claim`).
- `REAL_WORKSPACE` real-tree assertions (roster of 7 agents) — `test_harness_lint.py:208-225`.

### Naming and architectural conventions in play
- Exactly 7 agents and 39 skills; harness lint warns on drift — `CLAUDE.md:40, 44`; `harness_lint.py:300-317`.
- Ticket and tracker TOML are mutated only through `console/kanban.py` or verb handlers wrapping the same writers — `CLAUDE.md` § Console sync.
- One fact, one file (CANONICAL): the task-boundary rule is defined once in `plan` and referenced from `breakdown-tasks`.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| [[T-017-summary]] | Claim/ready/comment verbs, `claimed_by`/`claimed_at` | done | Claims exist but 0 of 28 tickets are claimed today (measured); builder protocol never claims |
| [[T-018-summary]] | Worktree isolation per ticketed Run, PR lane hints that never move lanes | done | Hard rule: automation suggests, never calls `ticket_move`/`close-work` (T-018 verification § a4); T-021's guard is a refusal, not an automatic move |
| [[T-020-summary]] | Run lifecycle, failure classes, stale claims, review loop (frozen, built before T-021) | frozen | Supplies `runs.ACTIVE`, `claim_status`, `review_escalated`, digest pattern; see analysis § 4 |
| [[T-004-summary]] | Assistant persona is console-owned, capped | done | BR-7 cap and the truncation notice exist for argv/prompt budget |
| memory `subagent-status-not-evidence` | Delegated builds mis-reported in T-004 | lesson | Verify from the tree; motivates item 8 |

### Relevant commits / PRs
- `1698d6e` Ship T-018 (worktree isolation) — makes two docs stale (analysis § 5).
- `6902b92` Ship T-017 (one-api, claim/ready/comment).

### Known incidents / regressions in this area
- 2026-10-01 measurement: `assistant.md` is over its own persona cap, so its Safety section is cut mid-bullet today (analysis § 3).
- T-018 verification found the builder's progress log overstated what a test covered (`T-018-verification.md` § a4) — evidence claims drift from evidence even when honest.

## 4. External Systems in the Loop

- Paperclip repo `D:\Workspace\research-workspace\paperclip` (read-only): `doc/execution-semantics.md:36-83, 337-376`, `server/src/services/routable-blocked.ts:3, 18-21`, `doc/architecture/native-status-arbitration.md:67-124, 213-223, 305-316`, `server/src/services/native-runtime/{evidence-classifier,status-arbiter}.ts`, `packages/skills-catalog/src/shipped-catalog.test.ts:30, 95-110, 145`, `.agents/skills/create-paperclip-bundled-skill/SKILL.md:177-179`, `skills/paperclip-converting-plans-to-tasks/SKILL.md`, `.agents/skills/doc-maintenance/SKILL.md`, `skills/slack/SKILL.md`.
- GitHub Actions (`verify.yml`): shallow checkout, no `console/.cache`.

## 5. Preliminary Risks Spotted

- A liveness check that reads Runs cannot be a CI check (no Run records there) — and before T-020 every Run stays `running` forever (`runs.set_state` has no caller outside tests; grep of `console/server` finds none).
- Evidence that must resolve to a file would block most real closes: 84 % of 212 historical PASS rows are prose or measurements (analysis § 2).
- The clause for the Assistant can be written and never delivered (persona cap).
- 20 of 39 skills already exceed 300 chars; an ERROR rule would be red on day one.

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source:

- T-020's final shipped names (`tickets.claim_status`, `runs.ACTIVE`, `review_escalated`, digest keys) come from the frozen [[T-020-requirements]] (FR-1, FR-19, FR-20, FR-23, FR-24), not from code: T-020 is not built (`grep claim_status console/server` finds nothing). Confirm at T-021 build start; if a name differs, T-021 adapts, it does not redefine.
- Whether agents will actually follow a "claim on first task" line in `builder.md` is a behaviour question only T-022 evals can answer.
- The assumption that no external process drives `tickets.move` over HTTP besides the board UI is not verified (the HTTP server is reachable by any local process).

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-01 | Read | `console/server/harness_lint.py`, `console/tests/test_harness_lint.py`, `kanban.py:341-355`, `.github/workflows/verify.yml`, `.githooks/pre-commit` | What lint checks, how severities affect CI and pre-commit |
| 2026-10-01 | Bash | python over `.claude/skills/*/SKILL.md` frontmatter | Description length distribution (min 86, median 316, max 658; 20 of 39 over 300) |
| 2026-10-01 | Read | `close-work`, `verify`, `reconcile`, `validate-artifacts`, `plan`, `breakdown-tasks`, `harness-standards` SKILL.md and `core.md`, `verifier.md`, `harness.md` | Where "evidence" is prose only |
| 2026-10-01 | Read | `tickets.py`, `trackers.py`, `verbs.toml`, `verb_handlers.py`, `context.py`, `runs.py`, `audit.py`, `stop_hook.py`, `boards.py` | What a lane move checks today (nothing beyond the lane name) |
| 2026-10-01 | Bash | ticket survey over 28 `ticket.toml` | 22 done, 3 verify, 3 open, 0 blocked, 0 claimed |
| 2026-10-01 | Bash | prototype evidence resolver over 24 `*-verification.md` (scratchpad) | Calibrate block versus warn |
| 2026-10-01 | Bash | `context.plan_tasks` over every ticket | `plan_open` would have refused 3 of 22 historical closes |
| 2026-10-01 | Read | `console/config/assistant.md`, `prompt_build.py`, `agents.toml`, desktop verbs in `verb_handlers.py` | Item 13 and the persona cap |
| 2026-10-01 | Bash | `prompt_build.persona_text('.', 'assistant')`, persona sizes of 7 agents | Assistant 4,725 chars vs cap 4,000; harness 3,622 (headroom 378) |
| 2026-10-01 | Read | `console/README.md`, `agents.py`, `desktop/README.md`, `desktop/features.toml`, `knowledge-center/wiki/desktop-assistant.md`, `console-feature-comparison.md`, `agents.toml` | Re-verify stale-doc claims |
| 2026-10-01 | Read | Paperclip files listed in § 4 | Re-read, did not rely on the dossier's line references |

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements-draft]] · [[T-021-requirements]] · [[T-021-context-snapshot]] · [[T-021-gap-analysis]] · [[T-021-critique-report]] · [[T-021-iteration-log]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]] · Dependency: [[T-020-requirements]]
