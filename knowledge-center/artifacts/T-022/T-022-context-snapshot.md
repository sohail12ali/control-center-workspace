---
ticket: "T-022"
artifact: context-snapshot
status: draft
created: "2026-10-01"
last_updated: "2026-10-01"
scope: codebase + history
---

# Context Snapshot: T-022

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only. Every bullet cites a source. Paths are relative to the workspace root.

## 1. Intent (echo)

Add a stdlib-only golden-prompt eval suite that regression-tests role and skill behaviour (claim/trace before work, stop on a refused gate, blocker needs a reason, no-work exit), with a free offline replay mode, an opt-in live mode, a product/model/grading/infra failure taxonomy, and usage that is UNKNOWN rather than zero. Source: [[T-022-summary]] Overview.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Backend registry + argv templates | `Backend.session_argv`, `compose_prompt` | config row -> argv | Build the live argv and the prompt exactly as the Agents tab does | `console/server/agent_backends.py:547-573,627-643` |
| Wire-format reader | `Normalizer.feed` | raw stream-json -> events | Single reader of the claude wire format; do not write a second | `console/server/agent_normalize.py:52-155` |
| Transcript replay | `agent_events.replay_file` | `.events.jsonl` -> list | Tolerant JSONL reader (torn last line) | `console/server/agent_events.py:60-79` |
| Token/cost records, "unknown is not zero" | `telemetry.price`, `summarize` | usage -> cost | `price()` for table pricing; `cost_complete` pattern for totals | `console/server/telemetry.py:89-111,243-262` |
| Static harness check | `harness_lint.lint` | `.claude/` files | Frontmatter/path parsing helpers; roster count | `console/server/harness_lint.py:246-317` |
| Verb registry | `verbs.registry`, `check_gates` | verbs.toml -> handler | One-line adapter for a read-only replay verb | `console/server/verbs.py:114-193`; `console/config/verbs.toml:21-23` |
| CLI subcommands | `build_parser`, `main` | argparse | Add an `evals` command group; exit codes via `sys.exit(1)` | `console/kanban.py:341-353,1015-1046` |
| Minimal TOML reader | `tomlio.load` | text -> dict | Scenario parser (read only) | `console/server/tomlio.py:190-229` |
| Test fixtures | `repo` fixture | tmp workspace | Throwaway root; real-workspace guard-test pattern | `console/tests/conftest.py:120-130`; `console/tests/test_harness_lint.py:208-225` |

### Existing patterns to reuse
- "The real workspace, not a fixture" guard tests for committed config - `console/tests/test_harness_lint.py:208-225`, `console/tests/test_agent_backends.py:15-55`.
- Fail-closed refusals with a one-line CLI error (`ValueError` -> `_die`) - `console/kanban.py:1038-1046`.
- ASCII-only report lines (CI logs, Windows consoles) - `console/server/harness_lint.py:327-331`.
- Gitignored `console/.cache/` for anything a transcript could contain - `.gitignore:66`; `console/server/agent_manager.py:8-9`.

### Naming and architectural conventions in play
- Stdlib-only runtime; pytest dev-only (`console/requirements-dev.txt`); no build step - `console/requirements-dev.txt:1-8`.
- Verb handler signature `(repo_root, ticket=None, **args)`; mutating/expensive verbs carry `needs_confirm` - `console/config/verbs.toml:1-30`.
- Exactly 7 agents, 39 skills; lint warns on roster drift - `CLAUDE.md:20,40`; `console/server/harness_lint.py:300-317`.
- Ticket/tracker TOML is CLI-mutated only - `CLAUDE.md:24`; `.claude/skills/questions/SKILL.md:19,46`.
- Artifact filenames `{T}-{artifact}.md` with a `## Links` block - `CLAUDE.md:24`.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-011 | Resume of past chats via transcript `native_session_id` | Shipped | The `.events.jsonl` is already treated as durable replay data - `console/server/agent_manager.py:273-333` |
| T-012 / T-014 | API sessions, pricing table, model catalog | Shipped; `pricing.toml` has no rows | Cost is often unknown; must be shown as such - `console/config/pricing.toml:1-30` |
| T-016 | Runs, Assistant home, `cursor-agent` role launch | Shipped | `launch_role` verb starts a role as a Run - `console/config/verbs.toml:96-102` |
| T-017 | MCP verbs, `ready`/`claim`/`comment`, AGENTS.md snippet | Shipped | `claim` conflict is refused by name; no prompt tells agents to claim - `console/server/tickets.py:212-255`; `console/server/setup_editor.py:30-44` |
| T-018 | Worktree isolation per Run | Shipped | Evals must not create worktrees or Runs |
| T-004 | Roster guard "exactly 7 agents" test | Shipped | Pattern for a real-roster guard - `console/tests/test_harness_lint.py:214-225` |
| T-020 (open) | Reliable Runs: claude failure classifiers, retry, stale claims | GROUND | Overlaps the `infra` class - [[T-020-summary]] |
| T-021 (open) | Honest close: liveness lint, skill text, skill-description lint | GROUND | Edits skill text and the `blocked` contract that scenarios quote - [[T-021-summary]] |

### Relevant commits / PRs
- `0c42658` Add T-016 artifacts; `1698d6e` Ship T-018; `6902b92` Ship T-017 (git log head, branch `development`).
- Predecessor roadmap asked for "golden prompts per skill, judge-scored, run nightly by the scheduler" - `knowledge-center/investigations/INV-2026-08-29-control-center-v3/INV-2026-08-29-control-center-v3-dossier.md:151,241`. Never delivered.

### Known incidents / regressions in this area
- 2026-09-17: the only recorded claude turn on this machine failed authentication ("OAuth session expired"), `is_error:true` with `subtype:"success"` and zero usage - `console/.cache/agent-chats/fc9143d7696c.log`, `...events.jsonl` (seq 8).
- Memory `subagent-status-not-evidence` (T-004): delegated builds mis-reported "done"; the reason Gate 6 needs enforcement and why replay cannot claim to prove live behaviour.

## 4. External Systems in the Loop

- `claude` CLI 2.1.286 on PATH (`claude --version`); flags confirmed in `claude --help`: `--agent`, `--permission-mode`, `--max-budget-usd` (print only), `--no-session-persistence` (print only), `--bare` (skips hooks and CLAUDE.md, so unusable for evals). `--max-turns` is NOT listed in this version's help.
- Anthropic account/OAuth for live runs: currently expired on this machine; `OPENROUTER_API_KEY` empty (T-015/T-019 blocked on it) - `console/config/agents.toml:210-233`.
- GitHub Actions `verify.yml` (pytest on 3.11/3.13, harness lint, cli smoke) - `.github/workflows/verify.yml`.
- SessionStart hooks inject the artifact-map and run `refresh --quiet` in every claude session - `.claude/settings.json`, `.claude/hooks/session-context.sh`, `.claude/hooks/console-refresh.sh` (read-only re-index, `console/kanban.py:636-647`).

## 5. Preliminary Risks Spotted

- Normalizer quirks (dropped tool results, possible duplicate `tool.start`, zero-collapsed usage) make graders on top of it wrong in subtle ways - `console/server/agent_normalize.py:106-111,223-230,280-289,313-323`.
- A graded run needs tool calls observable under `plan` mode; if headless `plan` suppresses the `tool_use` event or runs Bash, scenarios mean something different. Unverified.
- Live runs are non-hermetic (real CLAUDE.md, real artifact-map injected, real model) and non-deterministic; one pass is not reliability.
- Provenance quotes will trip when T-021 edits skill text - intended, but needs a sequencing note.
- Scenarios that pass on an empty transcript (forbid-only) are vacuous.
- Committed fixtures could leak absolute paths or keys if promoted from a real transcript.

## 6. Open Confirmations

- Real claude stream-json with partial messages emits both `stream_event` tool_use blocks and a complete `assistant` message (so `tool.start` doubles) - confirm with one captured stream; until then de-duplicate by id.
- `tool_result` blocks arrive in `user` messages in stream-json (inferred from the persisted session-log shape of this session) - confirm.
- `--permission-mode plan` in headless `-p` denies Bash while still emitting the `tool_use` event - confirm with ONE explicitly-authorised live scenario.
- Whether `claude -p --input-format stream-json` ends after the first `result` when stdin closes - inferred from `LiveSession.stop` (`agent_session.py:476-492`).

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-01 | Read | `console/server/agent_backends.py`, `agent_session.py`, `agent_manager.py`, `agent_events.py`, `agent_normalize.py`, `telemetry.py`, `harness_lint.py`, `tomlio.py`, `verbs.py`, `verb_handlers.py`, `tickets.py`, `setup_editor.py`, `agents.py` | How a turn is driven/observed; reuse points |
| 2026-10-01 | Read | `console/config/agents.toml`, `verbs.toml`, `schedules.toml`, `pricing.toml`, `kanban.py`, `.github/workflows/verify.yml`, `pytest.ini`, `.claude/settings.json`, `.claude/hooks/*` | Config, CLI, CI, gates |
| 2026-10-01 | Read | `.claude/agents/*.md` (7), `.claude/skills/{trace-context,handoff,evolve,do,questions,progress-tracker,requirements,analyze,challenge-requirements,clarify}/SKILL.md`, `CLAUDE.md` | Testable behaviours with line cites |
| 2026-10-01 | Read | Paperclip `evals/promptfoo/{promptfooconfig.yaml,tests/core.yaml}`, `doc/evals.md`, `.agents/skills/paperclip-evals/SKILL.md` | Reference design and taxonomy |
| 2026-10-01 | Grep | `console/tests` for `Normalizer`, `fixture`, `events.jsonl`, `stream_event` | No normalizer tests, no transcript fixtures |
| 2026-10-01 | Grep | `.claude/` for `claim` | No prompt requires claiming |
| 2026-10-01 | Bash | `python console/kanban.py harness lint`; `pytest --co`; `claude --version/--help` | Baseline: 0 errors/0 warnings; 1416 tests; CLI flags |
| 2026-10-01 | Bash | python probes of `tomlio.loads` and `Normalizer.feed` with synthetic input | Subset limits; tool.start duplication; tool_result swallowed (code behaviour only) |
| 2026-10-01 | Bash | Structure-only read of `console/.cache/agent-chats/fc9143d7696c.*` and this session's persisted log | Event shapes; no content copied |
| 2026-10-01 | Bash | Key names of `tool_use.input` across persisted Claude Code logs for this workspace (enrich) | Verified: `Bash.command`, `Edit.file_path`, `Write.file_path`, `Skill.skill/args`, `ExitPlanMode.plan`, `Agent.prompt/subagent_type`; MCP tools appear as `mcp__console__<verb-id>` (e.g. `mcp__console__kickoff` with `ticket,title,owner,confirm`) |
| 2026-10-01 | Read | `console/config/agents.toml:233,258` | Precedents for the proposed 180 s timeout and 25-call cap (enrich) |

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements-draft]] · [[T-022-context-snapshot]] · [[T-022-gap-analysis]] · [[T-022-iteration-log]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
