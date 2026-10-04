---
tags: [active]
status: Done
ticket: "T-013"
---

# T-013: Voice quality: neural TTS, speech-shaped text, and a less robotic house style

**Status:** Done
**Stage:** VERIFY
**Owner:** Sohail Ali
**Created:** 2026-09-07
**Due:**

## Overview

"It talks like a robot" turned out to be two complaints with two causes, and
the smaller-sounding one mattered more.

**What was being spoken.** A model writes for a screen — `**bold**`, bullet
lists, fenced code, `[links](http://…)`, `T-002` — and the synthesiser read all
of it literally. `speech_text` now shapes a reply for the ear first: markdown
out, links reduced to their text, code blocks skipped with a note that they
were, ticket ids said the way a person says them ("T two", not "T dash zero
zero two").

**Which voice.** Windows' `System.Speech` reaches only the old "Desktop"
voices; on this machine that is Microsoft David and Zira, and the description
was fair. `piper.rs` adds a local neural voice — ~65 MB, offline, eight times
faster than real time on this CPU — fetched deliberately by
`desktop/get-piper.ps1`, with the OS synthesiser as the fallback that always
works.

**And the writing.** The Assistant's persona gained a "how to sound" section,
and it is now *told* when a reply will be read aloud so it writes prose rather
than a bulleted list for a machine to recite. Agent chats, which get no persona
at all, now carry a short house style through `system_append`.

## Current State

Shipped and verified: piper synthesises 5.4 s of speech in 0.66 s, the shell
speaks through it, barge-in cuts it off mid-word with no leaked process, and
`/health` names the voice that would speak before anything has spoken.

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
