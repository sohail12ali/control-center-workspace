---
ticket: "T-013"
artifact: requirements
---

# Requirements: T-013

## Functional Requirements
1. A spoken reply contains no markdown, no URLs, and no code blocks read out
   character by character.
2. Ticket ids are spoken the way a person says them.
3. A local neural voice speaks replies when installed, fetched deliberately.
4. With no neural voice installed, the OS synthesiser still speaks.
5. Voice and speaking speed are settings.
6. Barge-in stops a neural utterance mid-word, leaving no process behind.
7. The Assistant is told when its reply will be heard rather than read.
8. Chats started by this console carry a short house style.

## Non-Functional Requirements
1. Nothing is downloaded without being asked for.
2. The reply text still goes to the synthesiser on stdin, never on a command
   line — it is model output.
3. Playback starts before synthesis finishes.
4. The house style is capped: it is prepended to someone else's system prompt.

## Acceptance Criteria
- [x] 1. `spoken_form` strips markup, links, tables and code, and says when a
      code block was skipped.
- [x] 2. `T-002` -> `T 2`, `CC-T001` -> `CC-T 1`, while `pre-2020` is left alone.
- [x] 3. Piper speaks when installed; `/health` reports which backend would.
- [x] 4. Without it, `System.Speech` (or `say`/`spd-say`) still speaks.
- [x] 5. `speak_voice` and `speak_rate_percent` validate and round-trip.
- [x] 6. `/speak/stop` ends it and leaves no `piper` process.
- [x] 7. The spoken-mode instruction appears only when `speak` is on.
- [x] 8. `house_style` is read, capped, switchable off, and passed to new chats.

## Out of Scope
- Cloud voices. Every reply would leave the machine to be spoken, which is a
  larger decision than "it sounds robotic".
- Windows' own "Natural" voices: they need a separate OS-level install, and
  piper covers the same want without one.

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
