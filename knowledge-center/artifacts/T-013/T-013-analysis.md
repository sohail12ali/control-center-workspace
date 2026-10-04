---
ticket: "T-013"
artifact: analysis
---

# Analysis: T-013

## Context

"When I am using agent it is talking like a robot — what can we do about it?"
Ambiguous between the voice and the writing, and it turned out to be both.

## Current State

- `tts.rs` spawns `powershell` + `System.Speech` on Windows. Its own docstring
  said WinRT would "mean owning WAV decoding and an output stream to gain
  better voices — a cost worth avoiding unless something demands it".
- `spoken_form` did nothing but truncate. Markdown went to the synthesiser
  verbatim.
- The Assistant has a persona with a reply contract; agent chats have none.

## Key Findings

- **The installed voices are the problem, and they are worse than the
  platform's.** `System.Speech` on this machine offers only "Microsoft David
  Desktop" and "Microsoft Zira Desktop". The OneCore set — five voices,
  including Mark — is installed and unreachable from that API. Even those are
  not the neural "Natural" voices, which are a separate download.
- **The text mattered at least as much as the voice.** Nothing stripped
  markdown. `**Two** tickets: T-002` was handed to a synthesiser as-is.
- **Piper fits this project's existing bargain.** whisper.cpp is already
  fetched by a script into a gitignored directory and shelled out to; a neural
  TTS is the same shape of dependency, and `cue.rs` already showed how to
  drive a cpal output stream.
- **`--output_raw` removes the round trip.** Piper streams headerless PCM to
  stdout as it synthesises, so playback can start before synthesis finishes,
  and killing the child is barge-in.
- **The prose half has two audiences.** The Assistant can be told how to
  sound in its persona; an agent chat's tone belongs to the CLI's own system
  prompt, and `system_append` is the console's only channel into it.

## Research

`tts.rs`, `audio.rs` and `cue.rs` (for the output-stream pattern),
`assistant.md`, `assistant_feature._compose_extra`, `agents_feature.chat_new`,
`get-whisper.ps1` as the script template; the installed voice sets read from
`System.Speech` and the `Speech_OneCore` registry key; piper's release assets
and voice layout on Hugging Face.

## Recommended Path

Shape the text first, because it is free and it is half the problem. Then add
piper as a preferred backend with the OS voice as fallback. Then the persona
and the house style. Prove the voice by listening to it, not by asserting it.

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
