---
name: ticket-draft
description: Triage an unstructured idea, report, or ask into a lightweight draft — title, scope, summary, optional stories/AC — and decide whether it deserves a full ticket, before any {T} id exists. Chat-only until confirmed; then hands off to kickoff. Distinct from kickoff, which assumes the id and scope are already decided.
---

# /ticket-draft

**When:** A rough idea, bug report, or one-line "we should probably..." with no ticket yet — before `kickoff`, before `requirements` (op draft). If `{T}` already exists, use `requirements` (draft/iterate) instead. On confirmation this skill hands off to `kickoff`.

**Inputs:** free-form text, a pasted report, or a description of the ask. No `{T}` required.

## Steps

1. **Read back the ask** in one or two sentences before drafting anything.
2. **Decide if it deserves a ticket:** trivial, obviously-safe, <1h, unambiguous → suggest `fix`, no ticket; stray thought without owner/timeline → suggest `todos`; non-trivial, multi-session, or audit-trail-worthy → continue.
3. **Draft in chat (no file yet):** Title (short, specific) · Scope (one paragraph — in and explicitly out) · Summary (plain language) · Suggested id per the workspace's `id_pattern` (`console/config/console.toml` if `console/` exists, else ask) · optional rough story/AC only if the shape is obvious.
4. **Ask the user to confirm id and scope** before persisting anything.
5. **On confirmation:** run `kickoff {id} --title "..."`, fold the draft into `{id}-summary.md` and `{id}-requirements.md` (or leave requirements to `requirements` op draft if the draft is thin). Hand off to `analyze` / `requirements` next.
6. **On rejection or "not now":** persist nothing — chat is the record. Suggest `todos` if worth keeping.

## Output

No files from this skill (kickoff creates the artifact set). Chat report:

```
── ticket-draft ──
Verdict:      {needs a ticket | suggest fix instead | suggest todos instead}
Suggested id: {T}
Title:        {title}
Scope:        {one line}
Next:         kickoff {id} (on confirmation) | todos "..." | fix "..."
```

## Rules

- Never create `knowledge-center/artifacts/{T}/` here — that's `kickoff`'s job, post-confirmation.
- Never guess an id and proceed silently.
- A production issue needing root-cause triage → `investigate` instead (proof-backed classification this skill doesn't attempt).

**Delegates:** `kickoff` (on confirmation), `todos`/`fix` (no ticket warranted), `investigate` (bug report needing triage).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
