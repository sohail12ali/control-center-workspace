---
name: harness-standards
description: Harness gates, communication norms, evidence policy, scope, token discipline, and test policy. Always-on — load before any agent output.
---

# Harness Standards

Orchestration entry: `.claude/agents/harness.md`. The 6 gates (GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY), **BE HONEST**, and the default concise voice are canonical in **[core.md](core.md)** (auto-imported by `CLAUDE.md`). This file adds the on-demand detail.

## 1. Ground before clarifying
Survey current state (code, `analysis.md`, `summary.md`, decision log) before asking or drafting. Don't ask what a quick look would answer.

## 2. Clarify before acting
Anything ambiguous or missing (instruction, scope, repo root, acceptance criterion) → ask specific questions as a short checklist of unknowns. Never guess.

## 3. Every output must be linkable
Every artifact/file gets a clear path or URL; state created/changed paths in chat. Vault notes use wikilinks; artifact filenames are ticket-prefixed so links resolve unambiguously.

## 4. Single source of truth
Never duplicate normative information — link to the canonical file; extend the smallest domain skill rather than forking a copy. Ticket hub: `knowledge-center/artifacts/{T}/{T}-artifact-map.md` (or `summary.md` for single-file tickets).

## 5. Simplicity in code
Least complex solution, minimal diffs, match existing project patterns, no speculative APIs. Respect the owning sub-project's own style rules.

## 6. Manual file templates
Canonical templates: `knowledge-center/artifacts/_template/`. New file of a known type starts from its template. No template → declare the gap in one sentence before creating a first instance.

## 7. Contradictions
Conflicting requirements → state the contradiction, propose a resolution or ask which side wins before proceeding.

## 8. Evidence, assumptions, completion
- **Evidence before "done"** — cite checks run (build, grep, paths, tests per policy), not assertions.
- **Test policy** — run the sub-project's own declared test/build for touched surfaces only; no full/slow suite for routine changes unless asked or the workflow implies it. Prefer the fastest reliable check.
- **Assumptions** — proceeding without an answer → state assumptions in one short block, continue.
- **No silent partial work** — say what was skipped/deferred and why.

## 9. Communication and questions
- **Status first (one line):** done / in progress / blocked / need input — then details.
- **Icons (every output), one per line, never replacing words:** ✅ done/pass · ⏳ in progress · ⛔ blocked · 🛑 ASK gate · ❓ needs input · ⚠️ warning/risk · 🔴🟠🟡🟢ℹ️ review severity · 📁 path · 🔗 link/trace · 🧭 dispatch · ▶️ next step.
- **Changes:** list modified paths.
- **Errors:** problem → tried → why it failed → two options → what you need.
- **Questions:** tight checklist; ticket work uses `questions` + `{T}-questions.toml` when present.
- **Next steps:** 1–3 concrete items (`@agent`, `/command`, paths) when a clear follow-on exists.
- **Skills footer (every completion):** `Skills:` — kebab-case ids actually loaded/invoked; sub-project delegation as `invoke-project-skill → {id}`; rules-only reads as `{skill}/SKILL.md (read)`; cap 8; never list `CLAUDE.md`.
- **Daily activity:** meaningful work → `/log-work` → `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md` under `## Work`.

## 10. Scope and batching
>10 files or risky refactors → confirm direction first. In scope: per ticket/plan, repo rules, minimal diffs. Out of scope: product/architecture policy calls — ask.

## 11. Compiler/analyzer/lint fixes (preserve behavior)
Never delete working user-facing behavior to silence a build. Align names with the defining API/type/contract/codegen. Ambiguous correct spelling (external API, mapping, codegen) → ask with options.

## 12. Token discipline
Only the invoked `/name` pulls its full SKILL.md. Heavy rule files: read once, never paste into chat. Ground in repo before wide/external reads. Narrow path + grep over whole-repo listings. Replies: status line, dense bullets, no re-quoting policy.

## Orchestration patterns

**Handoff** — for problems fixable without product/architecture policy (small code/test fixes, artifact metadata repair, bounded perf fix); judgment calls → user. Artifact/link corruption → @fixer; requirement ambiguity mid-build → @harness/user; non-architectural test failures → @builder; bounded perf regression → @fixer. Contract: pass complete context (ticket, paths, symptom, impacted list, logs); handler owns artifact updates; depth ≤ 2 (no A→B→C→A); timebox ~5 min, surgical.

**Hierarchical spawn** — only at ≥12 files across ≥3 layers. Each child owns one layer or sub-project, isolated context, parallel when independent. Parent merges file lists, resolves conflicts, validates cross-layer links + artifact map. Child failure → retry once or escalate with cause.

**Verifier → builder loop** — verifier classifies each failure: fixable (assertion mismatch, missing import, typo, off-by-one, null guard, perf with known lever, artifact/metadata drift → @fixer) → handoff to @builder with test output + scope, patch minimal surface, re-run; blocker (spec vs implementation conflict, wrong architecture) → user.

**Subagent output lines (explore/investigate)** — one line per hit, no narrative: `{path}:{line} — \`{symbol}\` — {≤6 word note}`. Cap 20 unless exhaustive was requested; then paginate `… +{N} more`.

**Reporting footer** — stage lines short; every completion has `Skills:` per §9. If handoff/spawn occurred:
```
HANDOFF: @fixer — reason — paths touched — result
SPAWN: N children (layer/sub-project) — merged — conflicts: 0
SKILLS: kickoff, verify, invoke-project-skill → build
```

**Version:** 2.0 — lean rewrite | **Updated:** 2026-08-23
