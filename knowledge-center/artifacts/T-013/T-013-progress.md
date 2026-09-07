---
ticket: "T-013"
artifact: progress
---

# Progress: T-013

## Status Summary
Stage: VERIFY — heard, not just tested. See [[T-013-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-013-01 `speech_text.rs` — markdown, links, tables and code out; ticket
    ids said the way people say them. 16 tests, because the rules are opinions.
  - T-013-02 `get-piper.ps1` and `piper.rs` — a local neural voice, streaming
    its PCM to the output device, with the OS synthesiser as fallback.
  - T-013-03 `speak_voice` / `speak_rate_percent`, read fresh on each reply.
  - T-013-04 A "how to sound" section in the persona, a spoken-mode
    instruction that appears only when speech is on, and a house style for
    chats that have no persona at all.
- Corrected mid-run: two of my own id rules were wrong and the tests said so —
  `pre-2020` was being read as a ticket, and `CC-T001` was not. Uppercase is
  what separates them.
- Verified: piper renders 5.4 s of speech in 0.66 s; the shell speaks through
  it; barge-in leaves no process; `/health` names the backend at cold start.
  Before/after recordings sent for a human ear.
- Blocked: —
- Next: —

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
