---
id: INV-2026-10-01-paperclip-adoption
date: 2026-10-01
owner: Sohail Ali
type: roadmap-dossier
status: proposed
---

# Paperclip — what Control Center can adopt

Scope: `control-center-workspace` measured against Paperclip (`D:\Workspace\research-workspace\paperclip`,
an open-source multi-tenant control plane for teams of AI agents; TypeScript, Postgres, React).
Classification: **feature/roadmap** — nothing here is a defect report. Most of Paperclip is SaaS machinery
we should not copy; the useful part is how it keeps agent runs reliable, forces "what moves this next?"
answers, tests its agent prompts, and presents run activity and human decisions.

Method: four read-only Explore passes over paperclip (server/packages/CLI; skills/docs/guidance; UI/CI/docker;
the skills/UI pass was re-run after a truncated report) plus one baseline pass over this workspace.
`grep -ri paperclip` found no earlier mention in this repo. Paperclip paths below are relative to its repo root.

---

## 1. Ground truth

### Already covered here — do not re-port

Worktree isolation per Run (T-018) · verbs exposed as MCP tools · run records · SSE transcripts with `seq` and
`?from=` replay · resume that refuses rather than silently starting fresh · "unpriced is never zero" ·
PreToolUse approval cards plus Telegram · `agents doctor` · `harness lint` · static export.

### Gaps this dossier targets

| Gap | Evidence |
|---|---|
| Runs have no stall watchdog, retry/backoff, timeout policy or failure classification | grep of `console/server/{runs,agent_manager,jobs}.py` finds only `approval_timeout`; the baseline pass agrees. Not traced path-by-path. |
| Claims record `claimed_at` but nothing reads it | `console/server/tickets.py:218` (`set_claim`) |
| Gate 6 "done is backed by cited evidence" is policy, not enforced | `.claude/skills/harness-standards/core.md`; see memory `subagent-status-not-evidence` |
| No agent evals | Roadmap item "golden-prompt evals" in [[INV-2026-08-29-control-center-v3-dossier]] was never delivered |
| No spend or token budget | Only per-chat loop caps exist; `console/config/pricing.toml` ships with no rows |
| Stale docs | `console/README.md` and `console/server/agents.py` say "no worktree isolation"; `desktop/README.md` calls the tray a remote for Agents chat; `knowledge-center/docs/console-feature-comparison.md` is dated 2026-08-24 |

---

## 2. Recommended adoptions, ranked

Effort: S = days, M = 1–2 weeks.

### Tier 1 — Reliable Runs

| # | Adopt | Paperclip source | Lands in | Effort |
|---|---|---|---|---|
| 1 | Claude failure classifiers (max-turns, exit-0 refusal, unknown or poisoned session, transient upstream, quota). Parse "resets 5pm (TZ)" into `retry_not_before` | `packages/adapters/claude-local/src/server/parse.ts:30` (quota regex, confirmed), `:271-343`; `execute.ts:1112-1257` | `agent_manager.py`, `runs.py` | S |
| 2 | Run-liveness classifier plus stall watchdog (completed / advanced / plan_only / empty / blocked / failed). Durable evidence beats "I'll do X" prose. Scale their 60 min / 4 h thresholds down | `server/src/services/run-liveness.ts`; `server/src/modules/active-run-watchdog/domain/policy.ts` | `runs.py`; new states `timed_out`, `scheduled_retry` | S–M |
| 3 | Retry table with caps: 2 transient retries, bounded continuation, quota backoff, explicit non-retryable list | `server/src/services/heartbeat.ts:815-825, 899-922` | `agent_manager.py` | S |
| 4 | Child-process hygiene: grace-then-kill, output cap, kill a process that lingers after its result line, strip nesting env vars. Windows needs `taskkill /T` or a Job Object, not process-group signals | `packages/adapter-utils/src/server-utils.ts:122-144` | `agent_manager.py` | S |
| 5 | Stale-claim rule: adopt if the owning run/pid is dead or `claimed_at` is past a TTL; audited force-release | `server/src/services/issues.ts:11360-11614`; `doc/execution-semantics.md:160-185` | `tickets.py` `set_claim`, `claim` verb | S |
| 6 | Bounded review loop: after 3 consecutive changes-requested rounds, escalate to the human | `server/src/services/issue-execution-policy.ts:69` (`DEFAULT_MAX_REVIEW_ROUNDS = 3`, confirmed) | verifier/fixer protocols, a tracker counter | S |

### Tier 2 — Enforce honesty instead of asking for it

| # | Adopt | Paperclip source | Lands in | Effort |
|---|---|---|---|---|
| 7 | Liveness contract as a lint: a non-terminal ticket needs a live run, a claim, or a pending question; `blocked` needs `{owner, action}` | `doc/execution-semantics.md:62-83, 337-360`; `server/src/services/routable-blocked.ts` | `harness_lint.py` | S–M |
| 8 | Evidence-gated close: `close-work` accepts only evidence refs that resolve to a file, test record or run; agents report a disposition and do not self-close | `doc/architecture/native-status-arbitration.md`; `server/src/services/native-runtime/status-arbiter.ts` | `close-work` skill plus a verb | M |
| 9 | Golden-prompt evals for role agents and skills (claim before work, stop on conflict, blocked needs a reason). Failure taxonomy product / model / grading / infra; missing usage is unknown, not zero | `evals/promptfoo/tests/core.yaml`; `doc/evals.md:137-165` | new `console/evals/` (stdlib runner via the `claude` backend) | M |
| 10 | Skill lint: description ≤ 300 chars with use-when / not-when; SKILL.md stays a hot path, rare procedures go to `references/` | `packages/skills-catalog/src/shipped-catalog.test.ts:30` (from a subagent report, not re-read) | `harness_lint.py` | S |
| 11 | Plan-to-tasks boundary rule: fewest tasks, split only for owner, parallelism, dependency or independent review; merge-back pass; re-fetch before closing | `skills/paperclip-converting-plans-to-tasks/SKILL.md:18-54` | `plan`, `breakdown-tasks` skills | S |
| 12 | Doc-drift audit with a SHA cursor and minimal patches | `.agents/skills/doc-maintenance/SKILL.md:36-47` | new skill or `harness lint` rule | S |
| 13 | Untrusted-content clause for the Assistant, which reads clipboard/OCR/screenshots through verbs. *Inference, not a Paperclip finding.* | pattern: `skills/slack/SKILL.md` | `console/config/assistant.md` | S |

### Tier 3 — UI patterns for the vanilla SPA

| # | Adopt | Paperclip source | Lands in | Effort |
|---|---|---|---|---|
| 14 | "Needs me" desk: blocking questions, critical bugs, permission cards, PR lane hints, stale claims in one list; sidebar badge computed identically to the page; j/k/Enter. Check overlap with `overview.js` first | `ui/src/pages/WhatNeedsMe.tsx`; `ui/src/lib/attention.ts:51-145` | new `static/needs-me.js` | M |
| 15 | Transcript normalizer: merge consecutive tool calls, force-expand errors, Nice/Raw toggle, bounded live buffer with a trim marker | `ui/src/components/transcript/RunTranscriptView.tsx`; `ui/src/lib/live-log-buffer.ts` | `chat-render.js`, `chat-store.js` | M |
| 16 | Run pill with stall hint and a result card listing checks as passed / failed / not_run plus the blocker and its unblock action | `ui/src/components/task-chat/TaskChatLiveRunPill.tsx`; `TaskChatProtocolCard.tsx` | `agents.js` Run rows | S |
| 17 | Steer-queue badges, composer outcome preview, interrupt shown amber not red | `ui/src/components/IssueChatThread.tsx:2032-2160`; `ui/src/lib/interrupt-handoff.ts:216-274` | `agents.js` composer | S–M |
| 18 | One status vocabulary: one glyph per status (colour-blind safe), tokens from a single hue variable | `ui/src/index.css:197-235`; `ui/src/components/StatusGlyph.tsx` | `core.js`, CSS | S |
| 19 | Kanban: collapse cold columns to a count rail, "Show 10 more", live pulse | `ui/src/components/KanbanBoard.tsx:30-33` | `board.js` | S |
| 20 | Toast policy (silent for on-screen state, dedupe, cap 5, silent on outcomes older than 5 min) and palette operators such as `status:blocked updated:>7d` | `ui/src/context/LiveUpdatesProvider.tsx`; `ui/src/lib/search-query-parser.ts` | `core.js`, `palette.js` | S |

### Tier 4 — Later or optional

| # | Adopt | Note | Effort |
|---|---|---|---|
| 21 | Budgets: warn 80 %, hard stop 100 %, one incident per window (`server/src/services/budgets.ts:213-297`) | `pricing.toml` is empty, so start with token caps; USD caps would mostly read "unpriced" | S–M |
| 22 | Worktree hardening: rescue-branch commit of a dirty tree, HEAD check on reuse, exact-branch attach, unresolvable base ref becomes a pre-dispatch blocker (`server/src/services/workspace-runtime.ts:3198-3320`) | builds on T-018 | M |
| 23 | Resume fingerprint: resume only if cwd, prompt-bundle hash and MCP identity match (`claude-local/src/server/execute.ts:1303-1351`) | | S–M |
| 24 | `console doctor --repair` with `pass/warn/fail` plus repair hint, unifying `agents doctor` and `harness lint` (`cli/src/commands/doctor.ts:155-200`) | | S |
| 25 | Vault lint: orphans, broken links, stale claims, weak provenance, index/log drift (`packages/plugins/plugin-llm-wiki/skills/wiki-lint/SKILL.md`) | | S |
| 26 | Mocked-provider smoke test so voice/launcher regressions are checkable while `OPENROUTER_API_KEY` is empty (`scripts/docker-onboard-smoke.sh`) | does not replace the real latency measurement T-015/T-019 are blocked on | S |
| 27 | Per-run write boundary via an env var checked in the verb layer, not a JWT (`server/src/agent-auth-jwt.ts`) | | S–M |
| 28 | Role/skill/schedule export-import bundle: Markdown plus sidecar, secrets as declarations only (`docs/companies/companies-spec.md:51-117`) | ties to the undelivered `console init` | M |

---

## 3. Skip

Multi-company tenancy, auth, invites, org chart, hire approvals (7 fixed agents). The adapter registry for 20+
CLIs (4 transports here). Plugin host, worker isolation, capability system (marketplace is out of scope per
`.cursor/plans/split-repo_delivery_os_4060c023.plan.md`). Postgres/drizzle. Sandbox providers, the Rust runner,
the Tailscale broker. Chat connectors, release lanes, Mintlify, Greptile, avatars, i18n.

Cautionary tale: paperclip's own `skills/paperclip/SKILL.md` is 728 lines (65 KB) plus a 96 KB API reference and
duplicates a paragraph (`:663,665`); its tightening plan requires evals first. That argues for item 9 before any
shrinking of our 39 skills.

---

## 4. Proposed tickets (each through `kickoff`)

1. **Reliable Runs** — items 1–6. Builds on T-018; touches `console/server` only. Ticketed as T-020.
2. **Honest close** — items 7, 8, 10, 11, 12, 13. Mostly lint and skill text. Ticketed as T-021.
3. **Evals** — item 9; afterwards use it to gate skill changes. Ticketed as T-022.
4. **Needs-me and run-activity UI** — items 14–20, cheap ones (16, 18, 19, 20) first. Not yet ticketed.
5. Tier 4 as separate todos.

## 5. Constraints every adoption must respect

- Ticket and tracker TOML is mutated only through `console/kanban.py`; new mutations are verbs in `verbs.toml`.
- Stdlib-only Python, no-build vanilla JS. `tomlio.py` is a hand-rolled subset that drops comments — never write to `agents.toml`.
- New artifact types need a template plus a manifest entry. No new agents (cap of 7).
- Fail closed: unknown or unpriced is never shown as zero.
- Windows-first: paperclip's process and kill scripts are POSIX and need a port.

## 6. Evidence caveats

- Spot-checked in source: 13 paperclip files exist; the review-round constant and the quota-reset regex are real.
  All other line references come from subagent reports and were not re-read.
- `server/src/secrets/*` could not be read (permission rule). `heartbeat.ts` (~30k lines) and `issues.ts` (~13k)
  were read by section only.
- "No stall or retry logic in our Runs" rests on a grep of three files plus the baseline report, not a full trace.

---

## Links

- Source: `D:\Workspace\research-workspace\paperclip`
- Predecessor roadmap: [[INV-2026-08-29-control-center-v3-dossier]]
- Spawned: [[T-020-summary]] · [[T-021-summary]] · [[T-022-summary]]
- [[CLAUDE]] · [[console]] · [[harness-standards]]
