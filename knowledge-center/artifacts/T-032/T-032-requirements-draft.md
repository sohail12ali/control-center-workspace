---
ticket: "T-032"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 0
created: "2026-10-05"
last_updated: "2026-10-06"
---

# Requirements Draft: T-032

> Superseded by [[T-032-requirements]] (frozen 2026-10-06). This draft is kept as the pre-freeze record; the FR/AC text lives ONLY in the frozen file.

## 1. Intent
**Stakeholder:** Sohail Ali. Stop the pipeline cutting the user off mid-thought and stop it hearing things never said; make both verifiable without a microphone.
**Raw intent verbatim:** "Make the pipeline stop cutting the user off and stop hearing things that were never said" ([[T-032-summary]] Overview). Scope ids B9 (first), B3, B4.

## 2. Context Summary
See [[T-032-analysis]] (current state with file:line). Mechanics reference: Mic Drop `assembler.rs`, `speech.rs:115-150`, `audio.rs` FileSource/FileSink.

## 3. v0 outline (as drafted, before challenge)
- B9: replay source + file sink. B3: provisional endpoint then wait for resumed speech, merge, re-transcribe, cap merges. B4: strip tags, drop hallucinated phrases, drop punctuation-only.
- Seeds the challenge found open: how replay is selected (setting vs env), what "merge" means for a contiguous buffer, how the merge window interacts with `first_pause`, tail trimming, bracketed ticket ids, latency cost. All resolved as decisions; see [[T-032-gap-analysis]] and [[T-032-decision-log]].

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Dossier: [[INV-2026-10-05-micdrop-adoption-dossier]] · Related: [[T-019-summary]] · [[T-031-summary]] · [[T-035-summary]] · [[T-034-summary]]
