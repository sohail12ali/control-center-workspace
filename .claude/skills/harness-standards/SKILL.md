---
name: harness-standards
description: Harness gates, communication norms, evidence policy, scope, token discipline, and test policy. Always-on — load before any agent output.
---

# Harness Standards

Orchestration entry: `.claude/agents/harness.md`

---

## The 6 stages (run in order as gates)

Canonical: **[core.md](core.md)** — the 6 gates (GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY), the cross-cutting **BE HONEST** rule, and the default concise voice. That file is the always-on core (imported by the umbrella `CLAUDE.md`); the sections below add the on-demand detail: evidence, communication, scope, token discipline, and test policy.

---

## 1. Ground before clarifying

Before asking questions or drafting, survey the current state: existing code, prior artifacts (`analysis.md`, `summary.md`), and any decision log. Don't ask what a quick look would answer.

---

## 2. Clarify before acting

If any instruction, requirement, ticket scope, repo root, acceptance criterion, or context is **ambiguous or missing**, ask **specific questions** instead of assuming. Prefer a short checklist of unknowns over guessing.

---

## 3. Every output must be linkable

Any **artifact**, Markdown note, or **generated file** must be referenceable by a **clear path** (workspace-relative or vault-relative) or **URL**. In chat, state the path(s) created or changed. In vault notes, use wikilinks per the vault's own conventions; artifact filenames are ticket-prefixed so links resolve unambiguously.

---

## 4. Single source of truth

Do **not** duplicate normative information across multiple files. If defined elsewhere, **link** to the canonical file. Extend the smallest domain skill when adding norms rather than forking a parallel copy. Ticket hub: `knowledge-center/artifacts/{T}/{T}-artifact-map.md` (or `summary.md` for single-file tickets).

---

## 5. Prioritize simplicity in code

Use the **least complex** solution. Avoid unnecessary abstractions. Match existing project patterns — minimal diffs, repo truth, no speculative APIs. Consult the owning sub-project's own style rules where the project defines them.

---

## 6. Manual file templates

**Canonical copy-paste templates** live under `knowledge-center/artifacts/_template/`. When creating a new file of a known type, start from the matching template manually (copy, rename placeholders). No template for the type → declare the gap in one sentence before creating a first instance.

---

## 7. Contradictions

If two or more requirements **conflict** (user vs. system instructions, ticket vs. code, or two items in this list), **state the contradiction explicitly** and propose a **resolution** or ask which side wins before proceeding.

---

## 8. Evidence, assumptions, completion

- **Evidence before "done"** — Cite checks run (build, grep, paths, tests **only if** run per policy below), not assertions.
- **Test policy** — Run the project's own test suite/build command (as declared in that sub-project's `CLAUDE.md` or manifest) for the surfaces actually touched. Do not run a full/slow test suite for routine changes unless the user asks or the workflow implies it (e.g. `/verify` with a test scope). Prefer the fastest reliable check (build, lint, targeted test) for everyday work.
- **Assumptions** — If you must proceed without an answer, state assumptions in one short block, then continue.
- **No silent partial work** — Say what is intentionally skipped or deferred and why.

---

## 9. Communication and questions

- **Status first (one line):** done / in progress / blocked / need input — then details.
- **Use icons for scannability (every output):** Lead status lines, section headers, and list items with a small, consistent icon so results are easy to read at a glance. Standard set — do not invent new meanings: ✅ done/pass · ⏳ in progress · ⛔ blocked/hard-stop · 🛑 ASK gate (awaiting approval) · ❓ needs input/open question · ⚠️ warning/risk · 🔴🟠🟡🟢ℹ️ review severity · 📁 path/file · 🔗 link/trace · 🧭 dispatch/routing · ▶️ next step. Keep it to one icon per line; never let icons replace the words.
- **Changes:** List modified paths; use markdown links when it helps navigation.
- **Errors:** Problem → what you tried → why it failed → two short options → what you need from user.
- **Questions:** Prefer a tight checklist. For ticket work, use `questions` conventions and `{T}-questions.md` when that file exists.
- **Next steps (when applicable):** When a clear follow-on exists (command handoff, artifact to update, approval gate), add a short **Next steps** list (1–3 concrete items: `@agent`, `/command`, paths). Omit when nothing natural follows.
- **Skills used (every completion):** End with **`Skills:`** listing procedures and norms **actually loaded or invoked** (not every skill in the repo). Use kebab-case skill ids; sub-project delegation as `invoke-project-skill → {id}`; rules-only reads as `{skill}/SKILL.md (read)`. Cap at **8** entries. Do **not** list `CLAUDE.md`.
- **Daily activity (meaningful work):** **`/log-work`** → `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md` under `## Work` (human-outcome bullets only).

---

## 10. Scope and batching

- **>10 files or risky refactors:** Confirm direction before a large sweep.
- **In scope:** Implement per ticket/plan, follow repo rules, keep diffs minimal.
- **Out of scope:** Product or architecture policy calls — ask; do not decide silently.

---

## 11. Compiler, analyzer, and lint fixes (preserve behavior)

When diagnostics involve **wrong identifiers**, **naming/casing**, **missing members**, and the "easy" fix is to delete call sites or menu entries:

- **Do not** remove working user-facing behavior just to silence the build unless the user explicitly agrees.
- **Do** resolve by aligning names with the defining API, type, contract, generated sources, and cross-boundary conventions already in the repo.
- **If** the correct spelling is ambiguous (external API, data mapping, third-party codegen), **ask** with options instead of deleting functionality.

---

## 12. Token discipline

- **Commands:** Only the invoked `/name` pulls its full `SKILL.md` — do not preload other command bodies.
- **Heavy rules:** Large glob-scoped rule files — **read once** when needed; never paste whole files into chat.
- **Unknown facts before wide reads:** ground first in the repo and prior artifacts; only reach for external sources (docs, web) when local truth is insufficient, and say so.
- **Search:** Prefer narrow path + `grep` over whole-repo file lists.
- **Replies:** Status line first, then dense bullets; skip re-quoting long policy blocks already in rules.

---

## Harness v2 — orchestration patterns

For handoff/delegation, hierarchical spawning, and verifier→builder feedback loops, see below (genericized from the kickoff orchestration reference).

### 1. Handoff (`request_handoff`)

**When:** Problem is **fixable without product/architecture policy** (small code/test fixes, artifact metadata repair, bounded perf fix). If it needs a judgment call on design or scope → user, not a chain of handoffs.

| Situation | Delegate to |
|-----------|-------------|
| Artifact/link corruption (broken cross-refs, orphan artifacts) | @fixer |
| Requirement ambiguity mid-implementation | @harness / user |
| Test failures (non-architectural) | @builder |
| Performance regression (bounded fix) | @fixer |

**Contract:** Pass **complete** context (ticket, artifact paths, symptom, impacted list, logs). Handler **owns** artifact updates; delegator **does not** re-write the same sections. **Depth ≤ 2** (no A→B→C→A). **Timebox** handler work (~5 min intent: surgical, not exploratory).

**Shape:** `if fixable(problem): request_handoff(to, reason, context); on return, continue_with(merged_context)`.

### 2. Hierarchical spawn

**When:** **≥12 files** touched across **≥3 layers**. Below that: usually **no** spawn.

**Contract:** Each child owns **one layer** or **one sub-project**. Children get **isolated** task context; **parallel** when independent. **Parent** merges file lists, resolves conflicts, validates **cross-layer** links and the artifact map. **Child failure** → parent retries once or **escalates** to user with cause.

### 3. Verifier → builder feedback loop

**Flow:** @verifier runs checks → classifies each failure → **fixable** → `request_handoff(@builder, test_output, scope)` → builder patches minimal surface → re-run → continue; **blocker** (spec vs implementation conflict, wrong architecture) → user.

| Failure kind | Fixable? |
|--------------|----------|
| Assertion mismatch, wrong expected value | Often ✓ (code or test) |
| Missing import, typo, off-by-one, null guard | ✓ |
| Perf with known lever (index, cache) | ✓ |
| Artifact link / metadata drift | ✓ (@fixer) |
| Architecture / requirement contradiction | ✗ → user |

### 4. Why three roles (plan / build / evaluate)

- **Split "does work" from "judges work."** Generators overrate subjective quality; a dedicated evaluation pass catches that.
- **Long runs need structured continuity.** Use handoff artifacts and explicit state (what changed, what's next) so the next step does not depend on an ever-growing chat.
- **Iterate inside the system.** Short generator ↔ evaluator cycles reduce `agent → user → agent` churn; human stays for calibration of criteria and true blockers.

**Local mapping:** Handoff + spawn shrink user loops; the verify→fix loop is the evaluation half applied to fixable failures.

### 5. Subagent output lines (explore / investigate)

When spawning explore or read-only investigation, require **one line per hit** — no narrative:

```
{path}:{line} — `{symbol}` — {≤6 word note}
```

Cap at **20 lines** unless the user asked for exhaustive search; then paginate with `… +{N} more`.

### 6. Reporting (optional footer)

Keep harness stage lines **short**. Every role completion includes **`Skills:`** per §9 (invoked slash skills, `{skill}/SKILL.md (read)`, `invoke-project-skill → …`; max 8). If handoff/spawn occurred, append compact lines:

```
HANDOFF: @fixer — reason — paths touched — result
SPAWN: N children (layer/sub-project) — merged — conflicts: 0
SKILLS: kickoff, verify, invoke-project-skill → build
```

**Version:** 1.0 — ported from lc-wms-cursor-config harness-standards, genericized for CCW's 6-stage GROUND→VERIFY model | **Updated:** 2026-07-04
