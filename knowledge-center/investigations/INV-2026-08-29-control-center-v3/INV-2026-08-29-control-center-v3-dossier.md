---
id: INV-2026-08-29-control-center-v3
date: 2026-08-29
owner: Sohail Ali
type: roadmap-dossier
status: proposed
---

# Control Center v3 — improvement roadmap

Scope: `control-center-workspace` (the generic template) measured against the ShopLC fork
(`lc-wms-cursor-config`) and three reference harnesses now in the workspace
(`deepseek-harness`, `prime-agent`, `skills`). Classification: **feature/roadmap** — nothing
here is a defect report except where marked **DEFECT**.

---

## 1. Ground truth

### What exists here today

| Surface | State | Evidence |
|---|---|---|
| Agents | 7 (`analyst planner builder verifier fixer deployer harness`) | `.claude/agents/` |
| Skills | 39, ~4,836 lines total (avg ~60 lines — already lean) | `.claude/skills/` |
| Console backend | 5,322 LOC Python, plugin registry, 9 feature modules | `console/server/` |
| Console frontend | 6,985 lines vanilla JS/CSS, no build step | `console/static/` |
| Agent transports | `stream_json`, `resume`, `oneshot` — **subprocess only** | `console/server/agent_backends.py` |
| Approval gate | PreToolUse hook, per-backend `gated_tools`, 300s timeout | `console/server/agent_approvals.py` |
| Chat | store + render + markdown + voice (852 lines) | `console/static/chat-*.js` |
| Tests | **none** | `find . -iname "*test*"` → 1 template file |
| CI | **none** | no `.github/` |
| Scheduling | **none** | — |
| Worktree isolation | **none** | — |
| Cost/token telemetry | **none** | — |

### What the ShopLC fork has that this template does not

The fork's `.kanban/` is a materially larger app than `console/`. Missing here:

| Fork capability | File | Why it matters to your 9 items |
|---|---|---|
| **verbs** — mechanical no-LLM jobs | `config/verbs.toml`, `core/verbs.py` | #2 token cost, #7 agent body |
| **recipes** — named runs, one "▸ advance" per lane | `config/recipes.toml` | #7, #8 |
| **schedules** — server-ticked cron, no external daemon | `config/schedules.toml`, `core/schedules.py` | #4 remote dispatch |
| **worktrees** — isolated git worktree per run | `agents/worktrees.py` | #4 prerequisite |
| **jobs / store / transcripts / terminals** | `agents/*.py` | #4, #9 |
| **custom backends** — register a CLI live, no restart | `agents/custom_backend.py` | #1 seam |
| **models.toml** — per-backend model shortlist + hints | `config/models.toml` | #9 |
| **readiness / work_evidence / gitmodel / gitview** | `core/*.py` | #8 |
| **vault graph view** | `web/vault-graph.js`, `core/vault_graph.py` | #3 |
| **tests + CI + pre-commit** | `.kanban/tests/`, `.github/workflows/`, `.githooks/` | #5 |
| **32 extra skills** (43 fork-only, 14 template-only) | `.claude/skills/` | #6 — mostly ShopLC-specific, correctly excluded |

### DEFECTS found while grounding

1. **`.claude/settings.json` is largely inert.** Top-level keys `workspace`, `agents`,
   `skills`, `claudeCode.defaultMode`, `claudeCode.permissions.allow` are not in the Claude
   Code settings schema and are silently ignored. Only `hooks` is doing anything.
   Consequence: there is **no `permissions` block at all** — the fork's ask-gates on
   `git push`, `git commit`, `gh pr create`, `WebFetch`, `WebSearch` do not exist here.
2. **`knowledge-center/investigations/` is referenced by `CLAUDE.md` and the `investigate`
   skill but did not exist** until this dossier created it.
3. **Dead config**: `console/config/console.toml` still carries a legacy `[agents.backends]`
   block superseded by `agents.toml`; `agent_backends._from_legacy` only reads it when
   `agents.toml` is absent. Harmless but misleading.

---

## 2. Your nine items, against reality

### #1 — OpenRouter agent backend

**Gap is structural, not config.** Every backend today is a subprocess
(`BaseSession` → `LiveSession` | `TurnSession`). OpenRouter is HTTP + SSE. No amount of
`agents.toml` editing reaches it.

Two routes:

- **A — native `ApiSession` (recommended).** Add `transport = "openai_api"`, a fourth
  transport, and a `ApiSession(BaseSession)` that: streams SSE from
  `openrouter.ai/api/v1/chat/completions`, runs its own tool loop (Read/Write/Edit/Bash/
  Glob/Grep), and emits the **same normalized events** `agent_normalize.py` already
  produces — so the existing chat UI, approval gate, and job records all work unchanged.
  ~600–900 LOC. Buys: every OpenRouter model in the picker, real cost data (OpenRouter
  returns `usage` plus a `/generation` endpoint for actual spend), and the gates stay yours.
- **B — delegate to an OpenRouter-capable CLI** registered as a `oneshot`/`resume` backend
  (the fork already proves the pattern with `dsh_backend.py`). Near-zero code. Cost: you
  inherit *that* tool's harness, not yours — your skills, agents, and gates do not apply.

Take **A**. The tool loop is precisely where your gates live; outsourcing it outsources the
harness. Non-obvious requirement: an OpenRouter agent has no `/skill` mechanism, so the
skill text must be **injected** — which makes #2 a hard dependency, not a parallel track.

### #2 — Token-efficient workflow

The skills are already lean; the waste is elsewhere. Ranked levers:

1. **Verbs — move deterministic work out of the model entirely.** `trace-context`,
   `validate-artifacts`, `reconcile`, `standup`, `log-work summary`, artifact scaffolding,
   link checking, lane sync are all computable. Today they cost model turns. Port the fork's
   verb registry; each verb converted is a permanent, compounding saving.
2. **One-call context.** `trace-context` currently has the model read ~8 artifact files.
   Replace with `kanban context {T}` returning one compact JSON digest. Biggest single-turn
   saving in the pipeline.
3. **Per-stage model routing.** Mechanical stages → Haiku; critique/planning → Opus.
   Currently one model per session.
4. **Declared context budgets** per stage in each agent protocol, enforced by the runner.
5. `caveman` already exists and is correctly wired as the `/do` default.

**Measure it or it isn't real:** none of this is falsifiable without per-stage token
telemetry (see *My additions #1*). Build the meter before the optimizations.

### #3 — Console UI

Foundation is good (no build step, plugin-gated tabs, theme-aware CSS). Highest-value adds:

- **Command palette (Ctrl+K)** over tickets, verbs, recipes, skills — replaces tab-hopping.
- **Ticket drawer** with artifacts / questions / bugs / todos / timeline in one panel.
- **Inline diff cards in chat** — approve/reject a proposed edit with the diff visible. This
  turns the approval gate from a blind yes/no into an actual review, and is the single
  biggest quality-of-life win in the whole list.
- **Run timeline** with per-turn model, tokens, cost, and tool calls.
- **Artifact graph view** — port `vault-graph.js`; makes the link gates visible.
- **Keyboard-first board** (j/k navigate, lane move, `a` to advance).

### #4 — Remote start, dispatch, control

Ordered by dependency — do not skip the first two:

1. **Worktree isolation** (`agents/worktrees.py`). Remote and parallel runs fighting over one
   working tree is the failure mode that makes everything after it untrustworthy.
2. **Job queue** with a concurrency cap and resumable records.
3. **Scheduler** — `schedules.toml` ticked by `serve`; no external daemon, no new dependency.
4. **Remote surface** — token auth + HMAC-signed `/api/dispatch`, bound behind Tailscale or a
   Cloudflare tunnel. Never expose the bypass modes remotely; keep the `agents.toml` policy of
   "full-bypass is a decision for a terminal you're sitting at".
5. **Push notifications** (ntfy / Pushover / Slack) for "Permission needed" cards. Without
   this, every remote run stalls at the first gated tool and the 300s timeout denies it.
6. **Audit log** of every dispatched run: who, what, from where.

### #5 — Automation testing

Four layers, cheapest first:

| Layer | What | Catches |
|---|---|---|
| 1 | pytest over `tomlio`, `trackers`, `tickets`, `boards`; JS tests over the store modules | console regressions |
| 2 | **Harness contract test** — a fixture ticket driven kickoff → close-work, asserting artifacts, links, and lane transitions | skill/agent drift |
| 3 | **Skill lint** — frontmatter schema, referenced-skill existence, orphan detection, agent↔skill graph validity (port the fork's `verify_harness.py`) | broken pipeline wiring |
| 4 | **Agent evals** — golden prompts per skill, judge-scored, run nightly by the scheduler; tokens-per-stage tracked as a metric | prompt regressions, and it makes #2 measurable |

Plus GitHub Actions running 1–3 on PR, and the fork's `pre-commit` hook.

### #6 — Prune and optimize the harness

The premise needs correcting: **the skills are not bloated** (39 skills, ~60 lines average).
Merge candidates exist but are judgment calls, not obvious wins:

- `criticize` is a pure router over three `challenge-*` skills → could be an op.
- `reconcile` and `validate-artifacts` overlap on drift detection.
- `replan` is arguably `plan --op replan`.
- `estimate` is the largest surface (162 lines + 223 template lines) for the least frequent use.

**Do not prune on intuition.** Ship skill-usage telemetry from the run records first, then cut
what demonstrably never fires. Meanwhile the concrete, uncontested fixes are the three DEFECTS
in §1 — especially restoring a real `permissions` block.

### #7 — Agent with a program body (the console)

The strongest idea in the list. Its real form is a **tool surface**, and the clean delivery
mechanism is an **MCP server**:

- Everything deterministic becomes a **verb** (Python, no model).
- Verbs are exposed over **one MCP server** → Claude Code, Cursor, *and* the new OpenRouter
  backend all get the same native tools. One implementation, every client.
- The console owns state transitions; the agent never computes status, never hand-edits TOML
  (already true), never re-derives what a query can answer.
- `console context {T}` becomes the agent's single grounding call.

This is what makes #2 and #8 achievable rather than aspirational.

### #8 — Work / track / test / orchestrate

- **Lane advance recipes** — one button per lane, invoking the owning role agent for *that
  lane's work only* (the fork's design is right: `skill = ""`, `persona = "{Role}"`).
- **Readiness** — the console computes "what blocks this ticket right now" from trackers +
  artifacts + git, instead of the model re-reading and re-deciding each session.
- **Work evidence** — link branches/commits to tickets automatically; feeds Work + Analytics.
- **Configurable git model** — branch tier → stage sync, with patterns in config so the
  template stays stack-agnostic.

### #9 — Model selection and a real chat

Already present: model picker per backend, streaming chat, markdown render, voice input.
Missing versus Cursor/Claude Code:

- per-**message** model switch (not just per-session)
- `@`-file / `@`-symbol references with a picker
- `/`-skill picker with argument hints
- inline diff cards (see #3)
- per-turn model badge + running cost
- chat history browser, resume, and conversation forking
- multiple concurrent chats

---

## 3. My additions — not on your list

1. **Cost & token telemetry as a first-class board metric** — per ticket, per stage, per
   model, per backend. Prerequisite for #2, #6, and any honest model-routing decision.
   OpenRouter makes this easy; Claude Code's stream already carries usage.
2. **MCP server for the console** — the correct expression of #7 (see above).
3. **Secrets policy** — an OpenRouter key changes the threat model. Today subprocesses inherit
   the full parent environment (`runner.py` passes no `env=`). Need explicit key sourcing,
   redaction in transcripts, and a documented "never commit, never log" rule.
4. **Fork ↔ template divergence ledger** — you will hit this on every port. A `harness diff`
   verb that lists what `lc-wms-cursor-config` has and the template doesn't, with a
   port/skip/won't-port decision recorded per row. Cheap to build, saves the manual diff I
   just did by hand, every time.
5. **Skill usage telemetry → evidence-based pruning** (feeds #6).
6. **`console init` for a new sub-project** — ticket ID space, branch model, publish
   procedure. The template's whole promise is reuse; make joining a two-minute operation.
7. **Reference-harness mining** — `deepseek-harness` (`packages/`: `llm`, `workflow`,
   `schedule`, `subagent`, `sandbox`, `guard`, `compaction`, `webhook`) and `prime-agent`
   (durable harness state, `/refine` self-improvement, daemon-backed background sessions) are
   directly relevant prior art for #1, #2, and #4. Worth reading `compaction` and `guard`
   before writing the OpenRouter tool loop.

---

## 4. Sequenced plan

| Phase | Work | Unblocks |
|---|---|---|
| **0 — Foundation** | Fix the 3 DEFECTS · pytest + JS tests + CI · skill lint · **cost/token telemetry** | everything measurable |
| **1 — Body** | Verb registry · `console context {T}` · **MCP server** · worktrees · job queue | #2, #4, #7, #8 |
| **2 — Backends** | `ApiSession` + OpenRouter · skill injection · per-stage model routing | #1, #9 |
| **3 — Remote** | Scheduler · auth + HMAC dispatch · push notifications · audit log · mobile view | #4 |
| **4 — UI/Chat** | Command palette · diff cards · `@`/`/` pickers · run timeline · graph view | #3, #9 |
| **5 — Evals** | Golden-prompt evals · token budgets per stage · evidence-based skill pruning | #2, #5, #6 |

Phase 0 before anything else: without telemetry, "less tokens" (#2) and "remove unneeded
skills" (#6) are both unfalsifiable, and without tests every subsequent phase is a regression
risk on a 12,000-line codebase with zero coverage.

---

## Links

- Fork: `d:/Workspace/shoplc-workspace/lc-wms-cursor-config/.kanban/`
- Reference harnesses: `deepseek-harness/packages/`, `prime-agent/packages/`
- [[CLAUDE]] · [[console]] · [[harness-standards]]
