---
name: clarify
description: Resolve open questions on an artifact through targeted user conversation. Distinct from `requirements` (which drafts) — `clarify` closes ambiguity into decisions. Use whenever an artifact has unresolved Qs blocking the next stage.
---

# /clarify

**When:** Whenever an artifact has unresolved questions blocking the next stage — in the pre-freeze chain, typically after `challenge-requirements` and before `requirements iterate` applies the answers.
**Order:** feeds `requirements iterate` (requirements) or the relevant stage skill; after clarifying, re-run the relevant challenge skill (`challenge-requirements` / `challenge-plan`) or `criticize(target)` before advancing stage.
**Inputs:** `id` (required); `target` (optional): `requirements` | `plan` | `analysis` (default: whichever has open Qs).

## Steps

1. Pull all open questions from the target file and the `questions` queue (`{T}-questions.toml`).
2. Group by theme; ask the user the smallest set that unblocks the stage (≤5 at a time). One decision per Q — bundle only when Qs are truly the same axis.
3. For each answer, append to `decision-log.md`: Context / Choice / Alternatives / Rationale. Never invent answers; if the user defers, mark the Q `deferred`, not resolved.
4. Patch the target file to remove resolved ambiguity (replace placeholders, rewrite vague clauses with the metric the user gave).
5. Update the `questions` queue: mark resolved, link to the decision.

Full question lifecycle, types, and blocking rules: `.claude/skills/clarify/question-templates.md`.

## Output

- `{T}-decision-log.md` entries (Context / Choice / Alternatives / Rationale).
- Patched target artifact sections.
- `{T}-questions.toml` updated (resolved/deferred, linked to decisions).
- Report: list of resolved Qs and the patched section refs.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
