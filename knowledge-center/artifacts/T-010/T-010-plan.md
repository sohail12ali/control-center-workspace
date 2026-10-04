---
ticket: "T-010"
artifact: plan
---

# Plan: T-010

## Approach

Measure, then fix in the order the numbers say. The overlay and the tones come
last: they make the irreducible second acceptable rather than removing it.

## Tasks

### [x] T-010-01 — Instrument the take (1 h)
- [x] Per-take breakdown at Info; per-step detail at Debug
- [x] `CONSOLE_LOG=debug` so detail is reachable without a rebuild
- **Done-criteria:** a slow take can be diagnosed from the log alone
- **Depends on:** —

### [x] T-010-02 — The stall (1 h)
- [x] `tray_link` reads the state and releases it before sleeping
- **Done-criteria:** `paint_listening` in single-digit milliseconds
- **Depends on:** T-010-01

### [x] T-010-03 — The detector (2 h)
- [x] Room calibration, energy gate, `SPEECH_RUN`, drifting floor
- [x] `listen_max_seconds` / `listen_silence_ms` settings; cap 20s to 12s
- **Done-criteria:** takes end on silence in this room; a noisy frame per ten
  cannot hold one open
- **Depends on:** T-010-01

### [x] T-010-04 — The decoder (1 h)
- [x] Flags verified against `whisper-server --help`, benchmarked on one WAV
- [x] `stt_model` names the model instead of "smallest on disk"
- **Depends on:** T-010-01

### [x] T-010-05 — The overlay and the tones (3 h)
- [x] `hud.rs` + `console/static/hud.html`; `cue.rs`
- [x] Both driven from `tray_paint`, the one event path
- **Depends on:** T-010-02

### [x] T-010-06 — One switch for speaking (1 h)
- [x] Tray mute writes `speak`; initial tick read from settings
- [x] Settings panel gains the three new keys and says what mute means
- **Depends on:** T-010-05

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-010-01 — Instrument | 1 h | logging only |
| T-010-02 — The stall | 1 h | one scope change, once found |
| T-010-03 — The detector | 2 h | pure logic plus tests |
| T-010-04 — The decoder | 1 h | flags and a benchmark |
| T-010-05 — Overlay and tones | 3 h | a window, a page, a synthesiser |
| T-010-06 — Mute | 1 h | a POST from the tray |
| **Total** | **9 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1 | T-010-01 |
| 2 | T-010-02 |
| 3, 4 | T-010-03 |
| 5, 7 | T-010-04 |
| 8 | T-010-05 |
| 6 | T-010-03, T-010-05 |
| 9 | T-010-06 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Fixing what looks slow rather than what is | High | High | Instrument first; the three obvious suspects were all wrong | Builder |
| A "faster" decoder that transcribes worse | Med | High | Benchmark on a fixed WAV and compare the text | Builder |
| An always-on-top panel in the way | Med | Med | Small, hides itself, never takes focus | Builder |
| A warm mic lighting the OS indicator | Med | High | Only hands-free, where it is already on | Builder |

## Dependencies
- Blocks: —
- Blocked by: T-009

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
