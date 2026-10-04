---
ticket: "T-013"
artifact: plan
---

# Plan: T-013

## Approach

Cheapest and largest first: shape the text. Then the voice. Then the writing.

## Tasks

### [x] T-013-01 — Speech-shaped text (2 h)
- [x] `speech_text.rs`: markup, links, tables, code, list markers, ticket ids
- [x] `tts::spoken_form` delegates to it
- **Done-criteria:** a reply full of markdown reads as sentences
- **Depends on:** —

### [x] T-013-02 — The neural voice (3 h)
- [x] `desktop/get-piper.ps1`, mirroring `get-whisper.ps1`
- [x] `piper.rs`: spawn, stream PCM, resample, play, stop
- [x] `tts` prefers it; `/health` reports the backend and installed voices
- **Depends on:** T-013-01

### [x] T-013-03 — Settings (1 h)
- [x] `speak_voice`, `speak_rate_percent`, validated, in the panel
- [x] Read fresh on each `/speak`, so a change takes effect next reply
- **Depends on:** T-013-02

### [x] T-013-04 — How it writes (1 h)
- [x] A "how to sound" section in the Assistant's persona
- [x] The spoken-mode instruction, only when `speak` is on
- [x] `console/config/house-style.md`, appended to chats this console starts
- **Depends on:** —

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-013-01 — Speech-shaped text | 2 h | pure logic, heavily tested |
| T-013-02 — The neural voice | 3 h | a script, a process, and playback |
| T-013-03 — Settings | 1 h | the established pair |
| T-013-04 — How it writes | 1 h | prose and one conditional |
| **Total** | **7 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1, 2 | T-013-01 |
| 3, 4, 6 | T-013-02 |
| 5 | T-013-03 |
| 7, 8 | T-013-04 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| A better voice reading raw markdown | High | High | The text is fixed first, and independently of the backend | Builder |
| Wrong sample rate = wrong pitch | Med | Med | Read from the voice's own config, with a documented fallback | Builder |
| A killed synthesiser leaving audio queued | Med | Med | `CANCEL` stops playback separately from killing the child; tested live | Builder |
| A tone note crowding out the task | Med | Med | Capped at 1,200 chars, and emptying the file switches it off | Builder |

## Dependencies
- Blocks: —
- Blocked by: T-006 (voice), T-010 (the speaking path)

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
