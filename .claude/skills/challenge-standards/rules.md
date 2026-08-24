# Challenge standards — shared adversarial critique rules

Shared by `challenge-requirements` and any future stage-specific challenge skills (e.g. a plan or implementation challenger), plus any orchestrator that routes between them.

## Core principle

**Find, don't fix.** Challenge passes surface issues only. Resolutions happen via the owning stage's repair command (e.g. `clarify` / `requirements iterate` for requirements, `replan` for plan, `fix` / `evolve` for implementation).

Never silently rewrite source artifacts except the designated critique outputs (a draft's own Challenge Findings section, and `{T}-critique-report.md`).

---

## Finding format

Each finding gets a stable ID and a grep-able line:

```
CR-{n} | {severity} | [{kind}] | {pointer} | {one-sentence issue} | resolution: 〈TBD〉
```

| Field | Rules |
|-------|-------|
| `CR-{n}` | Sequential per ticket across all stages; never reuse a resolved ID for a new issue |
| `severity` | `critical` \| `major` \| `minor` |
| `kind` | Lowercase kebab-case from the stage's taxonomy below |
| `pointer` | Section/anchor or `path:line` locating the issue |
| `resolution` | `〈TBD〉` until fixed; then `resolved: {command} {date}` or `accepted: {rationale}` |

### Severity

| Level | Meaning | Gate behavior |
|-------|---------|----------------|
| **critical** | Blocks the next lifecycle gate (freeze, build start, close) | Must resolve or explicitly accept before proceeding |
| **major** | Should fix before proceeding; risk of rework | Report prominently; suggest the repair command |
| **minor** | Deferrable; note for backlog | Log only |

### Critique report artifact

Canonical path: `knowledge-center/artifacts/{T}/{T}-critique-report.md`

Scaffold it on first use if missing: a short header plus one section per stage that has run a challenge pass (e.g. `## Requirements critique`), each with a Summary table (counts by severity, last run timestamp) and a `CR-{n}` findings table.

---

## Kind taxonomy — requirements

Used by `challenge-requirements` (inline Challenge Findings + sync to critique report):

| Kind | Signal |
|------|--------|
| `ambiguity` | Vague modifiers, undefined terms |
| `contradiction` | Conflicting sections, or vs. context snapshot |
| `untestable` | Acceptance criterion without observable outcome |
| `unstated-assumption` | Inferred precondition not documented |
| `unrealistic-constraint` | NFR/infra mismatch |
| `spof` | Single external dependency, no fallback |
| `scope-creep` | Work not traceable to intent |
| `nfr-unmeasurable` | NFR without a measurement method |

Map inline ⚠ markers to `CR-{n}` rows in the critique report's Requirements critique section.

---

## Kind taxonomies — other stages (for future challenge skills)

Any skill that challenges a later stage (plan, implementation, etc.) should define its own kind taxonomy here as a new subsection, following the same `CR-{n}` finding format and severity scale, so all challenge passes share one report and one ID sequence. Suggested starting points:

- **Plan-stage kinds:** `traceability`, `scope-drift`, `contradiction`, `sequencing-risk`, `effort-unrealistic`, `untestable`, `layer-violation`, `rollback-gap`, `critical-path`.
- **Implementation-stage kinds:** `plan-drift`, `incomplete-slice`, `spec-gap`, `error-handling`, `test-gap`, `security-risk`, `operational-risk`.

---

## Open questions from critical findings

When a **critical** finding needs a product/design decision, log it via `console/kanban.py tracker add {T} questions "..." --set type=<stage where raised, e.g. requirements|plan> --set priority=<critical (requirements) | high (later stages)>` (`{T}-questions.toml`).

---

## Iteration logs

| Stage | Log file | Bump iteration? |
|-------|----------|------------------|
| Requirements | `{T}-iteration-log.md` | No — only `requirements iterate` bumps |
| Later stages | that stage's own log/progress file, if any | No |

---

## Related

- `.claude/skills/harness-standards/core.md` — the 5 gates, honesty norm
- `.claude/skills/validate/SKILL.md` — general artifact critique (requirements/plan/verification) — use `challenge-requirements` for the deeper pre-freeze requirements pass specifically
- `CLAUDE.md` § Filename and linking convention — `{T}-critique-report.md` placement
