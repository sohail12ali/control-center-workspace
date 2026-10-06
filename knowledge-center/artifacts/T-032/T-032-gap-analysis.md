---
ticket: "T-032"
artifact: gap-analysis
status: resolved
created: "2026-10-05"
last_updated: "2026-10-06"
---

# Gap Analysis: T-032

**Sources:** [[T-032-requirements-draft]] · [[T-032-analysis]]

## Summary

| Category        | Red | Yellow | Green | Total |
|-----------------|-----|--------|-------|-------|
| Stakeholders    | 0 | 1 | 0 | 1 |
| Business rules  | 0 | 3 | 0 | 3 |
| Edge cases      | 0 | 4 | 0 | 4 |
| NFRs            | 0 | 2 | 0 | 2 |
| Data / entities | 0 | 1 | 0 | 1 |
| Integrations    | 0 | 2 | 0 | 2 |
| UX / UI         | 0 | 0 | 0 | 0 |
| Compliance      | 0 | 1 | 0 | 1 |
| **Total**       | **0** | **14** | **0** | **14** |

No blockers: every gap is closed by a recorded decision (default chosen, reversible via settings). Interactions with existing features: overlap=3 conflict=1 reuse=4.

## Resolution Log
| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-06 | all | challenge-requirements pass; each gap mapped to FR/D below; freeze | analyst |

## Stakeholders
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| S-1 | Y | T-019 owner decides whether replay of owner-voice fixtures satisfies AC-7/AC-8 (T-019-requirements.md:28-29) | D-8: T-032 delivers the mechanism; closing T-019 ACs stays with T-019 |

## Business rules
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| R-1 | Y | Merge window vs `first_pause` double patience (700+1200 after 1500 = 2.7 s) | CONFLICT -> D-3, FR-14 |
| R-2 | Y | Apply merging to push-to-talk / tray takes too? | Yes to silence-ended takes; Released bypasses; window 0 = off (D-4, FR-13) |
| R-3 | Y | Bare "Thank you." is dropped even if said on purpose | Accepted tradeoff (D-6); wake-gated speech is never bare |

## Edge cases
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| E-1 | Y | Long silent tail fed to Whisper triggers hallucination | FR-11 trim tail |
| E-2 | Y | Ticket ids in parentheses/brackets stripped as "sound tags" | FR-17 keep bracketed text containing a digit |
| E-3 | Y | Click/knock inside the window falsely extends the take | FR-8 same SPEECH_RUN debounce (audio.rs:125); AC-6 |
| E-4 | Y | Replay file ends mid-window / cursor exhausted on next take | FR-2 trailing silence pad; exhausted file -> "nothing heard" |

## Non-functional requirements
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| N-1 | Y | Latency cost of the window | NFR-2: documented, configurable to 0, logged per take |
| N-2 | Y | Wall-clock cap/sleep makes replay non-deterministic and slow | FR-2, NFR-1: audio-time clock |

## Data / entities
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| D-1 | Y | Fixtures: real voice vs synthetic; size; provenance | FR-6: Piper-generated, provenance doc'd; owner-voice wake wavs reused where they exist |

## Integrations
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| I-1 | Y | Settings: 2 new keys need defaults, bounds, live-note, allowlist in assistant_config.py and docs in assistant.toml; Rust reads via `limits_from` | FR-9, FR-20 |
| I-2 | Y | Hands-free loop and take path hold concrete `Mic`; replay must reach both | FR-1, FR-5; sequencing risk on files carrying T-031 edits (builder note) |

## Compliance / audit
| ID | Sev | Gap | Resolution |
|----|-----|-----|------------|
| C-1 | Y | A file-source switch could be abused to feed arbitrary files, or hide a dead mic | D-1: env var only, no settings/bridge/UI route, loud WARN + `source` in /listen/state; logs never contain transcripts of discarded speech |

## Existing-feature interaction (overlap / conflict / reuse)
- Overlap: `listen_preroll_ms` + RING (audio.rs:76) unchanged; replay must expose `rewound`. T-031 settings applier (listen.rs:294-337) unchanged. voice_test.rs `Source` trait (:~45) is a different seam (peak test).
- Conflict: `first_pause` semantics (audio.rs:458-465) -> R-1.
- Reuse: `Endpointer` (audio.rs:328), `to_mono_16k` (:198), `Take::wav` (:173), wake.rs:385 wav reader and fixtures dir, `stt::transcribe`.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Dossier: [[INV-2026-10-05-micdrop-adoption-dossier]] · Related: [[T-019-summary]] · [[T-031-summary]] · [[T-035-summary]] · [[T-034-summary]]
