# control-center-workspace

A **project-independent agentic harness** for **Claude Code** and **Cursor**. It pairs one agent pipeline (definitions under `.claude/`) with an Obsidian knowledge vault, a structured ticket lifecycle, and a local **Delivery Console** — so every piece of work (feature, bug, refactor) produces a paper trail you can navigate, audit, and resume months later.

This workspace doesn't contain your project's source code. It sits *next to* your projects and tracks them: their requirements, plans, decisions, progress, and verification — all as plain Markdown and TOML the agents read and write, and the console renders.

---

## Table of contents

1. [Workspace structure](#workspace-structure)
2. [The agent pipeline](#the-agent-pipeline)
3. [Agents in detail](#agents-in-detail)
4. [The Delivery Console](#the-delivery-console)
5. [The role of Obsidian](#the-role-of-obsidian)
6. [Adding a project to the workspace](#adding-a-project-to-the-workspace)
7. [Creating and working a ticket — step by step](#creating-and-working-a-ticket--step-by-step)
8. [Anatomy of a ticket](#anatomy-of-a-ticket)
9. [Common operations](#common-operations)
10. [Conventions](#conventions)
11. [Where to read more](#where-to-read-more)

---

## Workspace structure

```
control-center-workspace/
├── .claude/
│   ├── agents/                    # 7 agent definitions
│   │   ├── harness.md             # Orchestrator — routes every stage
│   │   ├── analyst.md             # GROUND, CLARIFY
│   │   ├── planner.md             # CANONICAL
│   │   ├── builder.md             # TEMPLATE, SIMPLIFY
│   │   ├── verifier.md            # VERIFY
│   │   ├── fixer.md               # Any stage — root-cause + minimal patch
│   │   └── deployer.md            # After close-work — ASK-gated publish
│   ├── skills/                    # 39 skills, each a lean directive contract
│   │   │                          #   (grouped roster below; ids in CLAUDE.md)
│   │   ├── harness-standards/     # Always-on gates + norms (core.md auto-imported)
│   │   ├── do/                    # /do — free-form autonomous dispatch
│   │   ├── kickoff/ trace-context/ template/ consolidate/ console/
│   │   ├── ticket-draft/ investigate/            # intake
│   │   ├── analyze/ requirements/ challenge-requirements/ clarify/
│   │   ├── tech-select/                          # user-gated decisions
│   │   ├── plan/ analyze-components/ breakdown-tasks/ estimate/ replan/ challenge-plan/
│   │   ├── progress-tracker/ fix/ evolve/
│   │   ├── verify/ challenge-implementation/ criticize/ validate-artifacts/
│   │   ├── questions/ bugs/ todos/               # console-backed TOML trackers
│   │   ├── handoff/ reconcile/ standup/ close-work/ invoke-project-skill/
│   │   └── log-work/ optimize-cursor-artifacts/ project-layout/ caveman/
│   ├── projects/control-center/memory/   # Persistent memory across sessions
│   ├── hooks/                     # SessionStart context + console refresh
│   └── settings.json              # Workspace config (agents/skills roster, hooks)
├── .cursor/                       # Cursor wiring (same harness; no duplicate skills)
├── console/                       # The Delivery Console (see section below)
│   ├── kanban.py                  # CLI entry point
│   ├── server/                    # Stdlib Python: plugins, boards, trackers, agent chats
│   ├── static/                    # Vanilla-JS SPA: boards, tabs, chat UI, themes
│   └── config/                    # console.toml, agents.toml, plugins.toml, boards/*.toml
├── knowledge-center/              # The Obsidian vault
│   ├── artifact-map.md            # Index of every ticket
│   ├── artifacts/
│   │   ├── _template/             # Files copied + renamed when a ticket is seeded
│   │   ├── _shared/               # Unscoped trackers (general todos)
│   │   └── T001/ …                # One directory per ticket
│   ├── investigations/            # Pre-ticket dossiers (investigate skill)
│   ├── logs/{YYYY-MM}/            # Per-author daily activity logs (log-work)
│   └── wiki/                      # Long-lived reference docs (ADRs, guides)
├── CLAUDE.md                      # What Claude Code reads on every session
├── CURSOR.md / AGENTS.md          # Same harness story for Cursor
└── control-center-workspace.code-workspace
```

**The deal:** agent and skill definitions live only in **`.claude/`** (both products use those files). Knowledge lives in **`knowledge-center/`**. The console lives in **`console/`** and renders that knowledge. Your project source code lives in a sibling directory you add as a workspace folder.

### Using Cursor

Read **`CURSOR.md`**. `AGENTS.md` points at the same harness — skills and agents stay under `.claude/`; `.cursor/rules/` supplies always-on rules and `.cursor/hooks.json` runs the same session-context idea as the Claude Code hook. Where `harness.md` says to delegate via the Agent tool, Cursor uses its Task tool with the same specialist roles.

---

## The agent pipeline

Six stages, seven agents. Each stage produces a specific artifact and hands off through a gate (`handoff`) to the next.

```
GROUND ──→ CLARIFY ──→ CANONICAL ──→ TEMPLATE ──→ SIMPLIFY ──→ VERIFY ──→ Closed ──→ (deploy)
analyst    analyst     planner       builder      builder      verifier              deployer
                                                                    │                 (ASK-gated)
                                                              fixer ◄┘ (on failure)
```

| Stage | Agent | Output artifact | What "done" means |
|-------|-------|-----------------|-------------------|
| GROUND | analyst | `{T}-analysis.md` | Findings, current state, recommended path |
| CLARIFY | analyst | `{T}-requirements.md`, `{T}-decision-log.md`, `{T}-questions.toml` | Frozen requirements, no critical open questions |
| CANONICAL | planner | `{T}-plan.md` (+ components/task-breakdown/implementation-plan for multi-layer) | Tasks, effort, risks, 100% AC coverage |
| TEMPLATE | builder | Source code + `{T}-progress.md` | Each task implemented to its done-criteria |
| SIMPLIFY | builder | Refined source + progress | Code reviewed for reuse and clarity |
| VERIFY | verifier | `{T}-verification.md` | Every acceptance criterion has cited evidence |
| — | deployer | `{T}-release.md` | Sub-project's own publish procedure ran; always ASK-gated |

The **harness** orchestrates: reads ticket state, picks the next stage, routes to the specialist. The **fixer** is invoked at any stage when something fails. **`/do {request}`** is the free-form entry point — it classifies your request into a lane and drives an iterate-until-done loop without you naming a stage.

---

## Agents in detail

### Harness — the orchestrator
Reads `artifact-map.md` + ticket state, runs `handoff` per transition, delegates. Never writes code or requirements. States the stage on every turn; never skips one. Full routing table: `.claude/agents/harness.md`.

### Analyst — GROUND + CLARIFY
Runs `analyze` (survey → `{T}-analysis.md`; mode `context` deep-scans into `{T}-context-snapshot.md`), then the **`requirements`** pipeline — one skill, five ops:

```
requirements draft → challenge-requirements (gaps + red-team) → requirements enrich
  → clarify/questions → requirements iterate (×N) → requirements freeze → requirements stories
```

- `draft` — v0 from your intent, grounded in the context snapshot; every assumption becomes an open question.
- `challenge-requirements` — one pass, two dimensions: completeness gaps (stakeholders, rules, edge cases, NFRs, data, integrations, compliance) **and** adversarial findings (ambiguity, contradictions, untestable criteria) **and** existing-feature overlap/conflict/reuse.
- `enrich` — replaces `〈TBD〉` placeholders with cited facts; never invents data.
- `iterate` — folds your answers back in; the only op that bumps the iteration counter.
- `freeze` — a 10-item deterministic gate; on pass finalizes `{T}-requirements.md`.
- `stories` — extracts user stories with acceptance criteria for the planner.

Critical questions live in `{T}-questions.toml` (console CLI) and block the freeze until resolved.

### Planner — CANONICAL
Confirms the freeze, then **`plan`**:
- **Flat case** (1 component, ≤6 tasks): plan writes Approach/Tasks/Effort/Risks directly into `{T}-plan.md`.
- **Multi-layer**: chains `analyze-components` (dependency graph + critical path) → `breakdown-tasks` (atomic tasks **and** the synthesized `{T}-implementation-plan.md`) → `challenge-plan` (critical findings block the build).
- `plan risk` re-rates risks after every `evolve`/`replan`; `estimate` gives an upfront envelope (`mode=upfront`) and mid-build re-forecast (`mode=forecast`); `tech-select` gates any new stack/library/pattern choice on your approval and records it to `{T}-decision-log.md`.

### Builder — TEMPLATE + SIMPLIFY
The only agent that writes source files. One task per turn: implement the minimum meeting done-criteria, `progress-tracker` the completion, mark `[x]`, then a `simplify` pass. New dependency not in the decision log → `tech-select(confirm-existing)` first. Can't do a task as planned → `evolve(target=plan)`, never a silent rewrite.

### Verifier — VERIFY
`challenge-implementation` (adversarial drift check) → `verify cases` (test-case artifact with AC traceability) → `verify {scope}` (unit / integration / e2e / review / ready) → per-AC evidence into `{T}-verification.md` → `validate-artifacts` (+ `links` scope for the full Requirement ↔ Task ↔ Code ↔ Verification chain) → `reconcile` → clean ⇒ `close-work`, unmet ⇒ fixer. Never green-by-default; static-only verification is labeled as such.

### Fixer — any stage
`fix`: reproduce → root-cause → minimal patch (1–3 files) → re-run → validating test. No fix without reproduction; no suppression to make CI pass; scope expansion routes back to the planner.

### Deployer — after close-work
Resolves the owning sub-project via `invoke-project-skill`, runs *that repo's own* publish procedure, records `{T}-release.md`. **Always ASK-gated** — a clean verify never triggers a deploy.

---

## The Delivery Console

A local web app + CLI at `console/` — stdlib Python and vanilla JS, no build step, no dependencies. It renders the same TOML/Markdown the agents write, and it is the **only** writer of ticket/tracker TOML (agents shell out to it; nothing hand-edits those files).

```
python console/kanban.py serve            # UI at http://127.0.0.1:8790
python console/kanban.py export --out X   # static snapshot that opens from file://
```

### Boards and tabs

| Tab | What it shows |
|-----|---------------|
| **Overview** | Attention buckets (blocked / stale / unowned), lane funnel, recent activity |
| **Tickets** | Kanban: open → in-progress (WIP 3) → blocked → verify → done; cards carry Q/bug/todo counts |
| **Investigations** | Pre-ticket triage board: open → investigating → resolved → closed |
| **Agents** | Live agent chats (below) |
| **Work** | Timesheet over `knowledge-center/logs/` daily files (written by `log-work`) |
| **Analytics** | Pipeline, ageing, throughput, timesheet charts — every chart has a table twin |
| **Todos** | Every todo across every ticket plus the unscoped `_shared` tracker |
| **Vault** | Knowledge-center file tree, reader, and wikilink force-graph |
| **About / Settings** | Orientation derived from live config; per-browser prefs (theme, tabs, backends, voice) |

`Migrations`/`Releases` boards ship config-present but off (`enabled = false`); a fork flips the flag. Features are plugins (`console/config/plugins.toml`) — `enabled = false` removes a feature's routes *and* tab.

### Agent chats — launch, steer, approve

The Agents tab runs a real CLI (Claude Code by default; backends are config rows in `console/config/agents.toml`) as a live stream-json session:

- **Composer** — pick backend, permission mode, persona (`@agent`), skill (`/skill`), and **model** (a curated shortlist — aliases like `opus` plus pinned ids like `claude-fable-5` — with a *custom id* box for anything else; "(backend default)" sends no `--model` flag).
- **Steer / queue / interrupt** — messages land mid-turn on a steerable backend, queue on a turn-per-process one; interrupt stops the turn without killing the session.
- **Approval gate** — tools listed in `gated_tools` (Bash, Write, Edit, WebFetch, Task, ExitPlanMode, …) are held by a PreToolUse hook: a **"Permission needed"** card appears in the transcript with **Allow once / Allow for this chat / Deny**. Silence denies fail-closed after `approval_timeout` (default 300 s). In acceptEdits mode the file-edit tools auto-allow so the mode means what it says. This is what makes headless `default` mode usable: gated tools ask *you*, in the chat.
- **Voice** — read-aloud speaks each finished reply (off by default); **announce** (on by default) says *"The agent is done."* at turn end and *"Permission needed for Bash"* when a run parks on you. Dictation feeds the composer where the browser supports it.
- Side rail: the agent's live plan, todos, and files touched. Transcripts persist (`console/.cache/agent-chats/`) and replay read-only after a restart.

### CLI + stage sync

The pipeline keeps the board honest via the CLI: `kickoff` → `ticket create` (lane `open`) · build → `in-progress` · blocker → `blocked` · verification → `verify` · `close-work` → `ticket move {T} done`. Trackers (`questions`/`bugs`/`todos`) use `tracker add|list|update|blockers`. Full verbs: `console/README.md`.

---

## The role of Obsidian

`knowledge-center/` is an Obsidian vault: backlinks, graph view, tag search, `[[T013-summary]]` wikilinks. You don't *need* Obsidian — every file is plain Markdown — but it's the intended reading interface. Claude Code is the **writer**, Obsidian and the console are the **readers**.

Setup: install Obsidian → *Open folder as vault* → select `knowledge-center/`.

---

## Adding a project to the workspace

The workspace is multi-root and tracks tickets for any number of sibling projects.

1. Clone or create your project as a sibling directory (`D:\Workspace\my-app`).
2. Add a folder entry to `control-center-workspace.code-workspace`:
   ```json
   { "folders": [ { "path": "." }, { "path": "../my-app" } ] }
   ```
3. Open the workspace file in VS Code. Claude Code now sees both the harness and your code.

Tickets reference the project by **path**: artifacts live in `knowledge-center/artifacts/T002/`; the code they describe lives in `../my-app/lib/...`. For a brand-new project, make the first ticket a bootstrap ticket; for an existing one, an optional onboarding ticket surveys the code into `wiki/`.

---

## Creating and working a ticket — step by step

```
/kickoff T013 "Add dark-mode toggle"
```
Seeds `knowledge-center/artifacts/T013/` from `_template/` (every file renamed `T013-*`), scaffolds `ticket.toml` + empty tracker TOMLs via the console CLI, adds the artifact-map row. Not sure it deserves a ticket yet? `/ticket-draft` triages the idea first; `/investigate` handles "is this even a bug?" with a proof-backed dossier.

```
analyst T013            # GROUND: analysis.md → CLARIFY: requirements pipeline
```
The analyst surveys code (file:line citations), drafts requirements, challenges them, asks you the blocking questions, iterates on your answers, freezes, and extracts stories.

```
planner T013            # CANONICAL: plan.md (flat) or the multi-layer chain
builder T013            # TEMPLATE/SIMPLIFY: one task per turn, progress logged
verifier T013           # VERIFY: challenge → test cases → scoped checks → evidence
close-work T013         # gates pass → Status=Complete, board lane → done
deployer T013           # only if it ships elsewhere — and only when you say go
```

Or skip the stage names entirely:

```
/do "add a retry to the sync job in my-app"
```

Every step leaves a trail in the ticket directory. Months later you `grep T013 knowledge-center/` and the entire reasoning chain is right there.

---

## Anatomy of a ticket

| File | Purpose | Filled by |
|------|---------|-----------|
| `T013-summary.md` | One-page status: title, stage, owner, current state | every agent |
| `T013-analysis.md` | Findings + recommended path | analyst |
| `T013-requirements.md` | FRs, NFRs, acceptance criteria, out-of-scope | analyst |
| `T013-decision-log.md` | Every significant decision with rationale | analyst, planner, tech-select |
| `T013-plan.md` | Approach, tasks, effort, risks, AC coverage | planner |
| `T013-progress.md` | Dated log of every action | every agent |
| `T013-verification.md` | AC table with PASS/FAIL + evidence | verifier |
| `ticket.toml` | Board lane/status/owner/priority — **console CLI only** | kickoff, close-work |
| `T013-{questions,bugs,todos}.toml` | Trackers — **console CLI only** | questions/bugs/todos skills |

Multi-layer tickets add `T013-user-stories.md`, `T013-components.md`, `T013-task-breakdown.md`, `T013-implementation-plan.md`, `T013-test-cases.md`. Every artifact ends with a `## Links` block listing every sibling — each ticket renders as a connected cluster in Obsidian's graph.

---

## Common operations

| Operation | Command |
|-----------|---------|
| Free-form autonomous work | `/do "…"` (lanes + ACT/ASK boundary; `caveman`-terse output) |
| Cross-ticket digest | `/standup` |
| Resume a stale ticket | `trace-context T013` |
| Amend a frozen artifact | `/evolve T013 target=requirements reason="…"` — logs the delta, never silent |
| Track questions / bugs / todos | `/questions T013` · `/bugs T013` · `/todo [T013] "…"` (console-backed TOML) |
| Adversarial review | `/criticize T013 [requirements \| plan \| implementation]` |
| Tech decision | `/tech-select` — researched options, your approval, decision-log entry |
| Daily log / timesheet | `/log-work T013 ~2h …` · `/log-work summary [date] [--all]` |
| Serve / export the console | `python console/kanban.py serve` · `… export --out DIR` |
| Terse output | `/caveman lite \| full \| ultra` |
| Config/skill token trim | `/optimize-cursor-artifacts` |

---

## Conventions

- **Ticket IDs:** `T###` (or `BUG-###`, `FEATURE-NAME`, per-project prefixes like `NA-T001`). Pattern is config: `console/config/console.toml` `id_pattern`.
- **Filenames:** every artifact is `{TICKET}-{artifact}.md`, flat in the ticket dir — globally unique, so `[[T013-plan]]` resolves from anywhere. Canonical rules: `.claude/skills/consolidate/SKILL.md`.
- **`## Links` block:** mandatory on every artifact — lists every sibling.
- **TOML is CLI-mutated only:** `ticket.toml` and tracker files go through `console/kanban.py`, never a text editor.
- **Never silently rewrite:** frozen artifacts change only through `evolve`.
- **Memory vs artifacts:** user-specific facts → `.claude/projects/control-center/memory/`; project facts → artifacts.
- **The 6 gates + BE HONEST:** `.claude/skills/harness-standards/core.md` — auto-imported into every session.

---

## Where to read more

- `CLAUDE.md` — the session contract: layout, order, console sync.
- `console/README.md` — full console architecture, CLI reference, security posture.
- `.claude/agents/*.md` · `.claude/skills/*/SKILL.md` — the definitions themselves (lean directive contracts: When / Steps / Output / Gate).
- `CURSOR.md` / `AGENTS.md` — the Cursor side.
- `knowledge-center/artifact-map.md` — the live index of all tickets.
