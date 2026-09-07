---
ticket: "T-011"
artifact: progress
---

# Progress: T-011

## Status Summary
Stage: VERIFY — proved end to end against a real CLI. See
[[T-011-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-011-01 Transcript now yields cwd, the CLI session id and the last seq;
    `Stream` can continue an existing numbering.
  - T-011-02 `session_argv` takes a resume id; `can_resume` is read off the
    config row; claude's row gained `resume_session_args`.
  - T-011-03 `agent_manager.resume` rebuilds the session in place, refuses
    when it cannot work, and records `session.resumed`.
  - T-011-04 Route, audit line, `resumable` on the listing, and the Resume
    button in place of the read-only banner.
  - T-011-05 The Assistant resumes its own chat across a restart.
- Corrected mid-run: opening a resumed chat showed two events and no history,
  because `transcript()` preferred the in-memory ring over the file. Found by
  opening one; fixed and pinned by a test.
- Verified: told a chat a word, stopped the console, restarted, resumed, asked
  — "Pomegranate." pytest 1099 + 8 new, harness lint clean.
- Blocked: —
- Next: —

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
