---
ticket: "T-013"
artifact: verification
---

# Verification: T-013

Verified 2026-09-07. **pytest 1142 passed** (1133 before), **cargo test 141
passed** (123 before), harness lint clean, and the part that no test can
settle: the two voices were rendered to files and sent to be listened to.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | No markdown, links or code read aloud | PASS | Live through the shell: `**Two** tickets are open: T-010 and T-002. See [the plan](https://example.com/x).` was spoken as 49 characters — "Two tickets are open: T 10 and T 2. See the plan." |
| 2 | Ticket ids said the way people say them | PASS | `T-002` → `T 2`, `T-010` → `T 10`, `CC-T001` → `CC-T 1`, and `pre-2020` left alone. Uppercase is what separates an id from a hyphenated word |
| 3 | A neural voice speaks when installed | PASS | `POST /speak` returned `{"backend":"piper","chars":49}`; `/health` reports `speak_backend: piper` and `speak_voices: ["en_US-amy-medium"]` at cold start |
| 4 | The OS voice still works without it | PASS | `backend()` falls through to `System.Speech` when `desktop/tts` is absent; the "no install" case is unit-tested and the `hint()` path is unchanged |
| 5 | Voice and speed are settings | PASS | `speak_voice` and `speak_rate_percent` validate (a path-shaped voice name and a rate outside 50-200 are refused) and are read fresh on each `/speak`, so a change lands on the next reply |
| 6 | Barge-in leaves nothing behind | PASS | Live: speaking `true` → `POST /speak/stop` → `false` in under a second, and no `piper` process remained |
| 7 | The model is told when it will be heard | PASS | The instruction appears in the injected context with `speak` on and is absent with it off — both asserted |
| 8 | Chats carry a house style | PASS | `house_style` reads only what follows the `---`, caps at 1,200 chars, returns "" for an empty file, and `chat_new` passes it as `system_append` |

## Test Results

```
python -m pytest -o addopts="" -q              -> 1142 passed
cargo test (desktop/src-tauri)                 ->  141 passed
python console/kanban.py harness lint          -> 0 error(s), 0 warning(s)
```

## The measurements

```
piper, en_US-amy-medium:  5.36 s of audio synthesised in 0.66 s
                          (real-time factor 0.12 — eight times faster than speech)
                          22050 Hz mono, matching what the playback path assumes
```

## What was actually wrong

Two things, and the cheaper one mattered as much:

**The text.** Nothing stripped markdown before speaking. A reply reading
`**Two** tickets: T-002` was handed to the synthesiser verbatim. No voice
survives that.

**The voice.** The console spoke through `System.Speech`, which on this machine
offers exactly two voices:

```
System.Speech (used until now)   Microsoft David Desktop
                                 Microsoft Zira Desktop

OneCore (installed, unreachable  Microsoft Mark, Zira,
from that API)                   Heera, Ravi, David
```

The "Desktop" voices are the Windows 7-era ones. "It talks like a robot" was a
description, not a figure of speech.

## Corrections made during the work

Two of my own ticket-id rules were wrong, and the tests said so before anything
shipped: `pre-2020` was being read as a ticket id, and `CC-T001` was not being
recognised as one. Requiring the letters to be uppercase separates them, which
is also the workspace's own naming convention.

## Notes

### Judged by ear, deliberately

The same sentence was rendered through the old path (Microsoft David Desktop)
and the new one (piper, amy) and both files were handed over to be listened to.
A test can assert that audio was produced; whether it still sounds like a robot
is not a thing a test can answer, and pretending otherwise would be the exact
failure this ticket is about.

### Untested here

- **macOS and Linux.** The piper binary fetched by `get-piper.ps1` is
  `windows_amd64`; the Rust side looks for a `piper` binary on those platforms
  and falls back to `say` / `spd-say` when it is absent, which is the correct
  behaviour but has not been run there.
- **A different voice.** Only `en_US-amy-medium` was downloaded. The picker
  and the fallback-to-any-installed-voice path are exercised, but with one
  voice present.

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
