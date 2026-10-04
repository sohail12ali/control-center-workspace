---
ticket: "CC-T005"
artifact: plan
---

# Plan: CC-T005

## Approach

Phase 4 — the console as something you operate, not just look at.

Priority came from the dossier's own ranking, and the top item is not the flashiest: the
approval card. It renders the tool's arguments as JSON, which for a file write is a wall of
escaped text with `
` between every line. Nobody reads that, so it gets approved unread —
which makes the gate a speed bump with a log rather than a gate. Fixing it is the difference
between having a review step and only appearing to.

Everything else follows from the same idea: the console already knows things the interface
makes you go and find out.

## Tasks

### [x] CC-T005-01 — Diff cards on the approval gate (4 h)

- [x] `console/server/tool_preview.py` — a unified diff for a write or an edit, the command
      for a shell call, computed **server-side** so both the CLI hook path and the in-process
      API loop get it from one implementation
- [x] Carried on the `approval.request` event; renderer paints it, falls back to arguments
- [x] Truthful about what it cannot know: an edit whose target text is missing says the call
      will fail, an ambiguous edit says which occurrence wins, a shell command is shown but
      not predicted
- **Done-criteria:** a `write_file` approval shows +N/−M and the changed lines; a preview
  failure never stops the question being asked.
- **Depends on:** —

### [x] CC-T005-02 — Command palette (4 h)

- [x] `console/static/palette.js` + Ctrl/Cmd-K, sourced from the tab manifest, the ticket
      list, the verb registry and the skill catalogue — nothing hardcoded
- [x] Subsequence matching so `hl` finds "harness lint"; exact prefixes win
- [x] A verb needing a ticket is shown greyed with the reason, not offered and then failed
- [x] Focus is returned on close; arrow keys, Enter and Escape behave
- **Done-criteria:** the palette lists every tab, ticket, verb and skill live; running a verb
  shows its result in the drawer.
- **Depends on:** CC-T005-03

### [x] CC-T005-03 — Verbs over HTTP (2 h)

- [x] `features/verbs_feature.py` + a `plugins.toml` row — list, run, submit, and job listing
- [x] No tab: verbs are run from where you already are, not somewhere you navigate to
- **Done-criteria:** `/api/verbs` returns the registry with per-ticket availability; the
  plugin registers no tab.
- **Depends on:** —

### [x] CC-T005-04 — Per-turn model and cost (2 h)

- [x] `usage` events were being discarded, so the token counters never moved — now folded in
- [x] Each turn's own model, tokens, cost and duration on the turn, not just a session total
- [x] A turn stopped by the tool-round cap says so instead of looking finished
- **Done-criteria:** a completed turn shows model, in/out tokens and cost; a capped turn is
  visibly distinct from a complete one.
- **Depends on:** —

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T005-01 — Diff cards | 4 h | diff builder + renderer + styles |
| CC-T005-02 — Command palette | 4 h | new module + matching + keys + styles |
| CC-T005-03 — Verbs over HTTP | 2 h | one plugin, four routes |
| CC-T005-04 — Per-turn cost | 2 h | store fix + badge |
| **Total** | **12 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
| --- | --- |
| The approval gate is a review, not a yes/no | CC-T005-01 |
| Any tab, ticket, verb or skill is one shortcut away | CC-T005-02 |
| Deterministic jobs are runnable from the UI | CC-T005-03 |
| Cost is attributable to a step, not just a session | CC-T005-04 |

## Deferred, and why

- **`@`-file and `/`-skill pickers in the composer.** The palette covers the same intent for
  now, and an inline autocomplete inside a growing textarea is a fiddly piece of work that
  deserves its own pass rather than being rushed at the end of one.
- **Artifact graph view.** Real value, but it is a visualisation task with no dependency on
  anything here; it belongs beside the vault tab work.
- **Ticket drawer with tabs.** The palette plus the existing board covers most of the
  navigation win it would have delivered.

Not silently dropped — logged as todos on this ticket.

## Links
- [[CC-T005-summary]] · [[CC-T005-decision-log]] · [[CC-T005-plan]] · [[CC-T005-progress]] · [[CC-T005-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T004-summary]]
