---
ticket: "T-019"
artifact: progress
---

# Progress: T-019

## Status Summary
Stage: VERIFY — pipeline rebuilt, 1445 python + 181 Rust tests green, live-checked in the
running shell. One half (reply speed) blocked on a credential that is the owner's to set.

## Dated Log

### 2026-09-16
- Done: ground truth from `console/.cache/desktop/host.log` (five discarded takes, 16:08)
  and `console/.cache/assistant/settings.json` (`backend: "claude"`) before writing code —
  the workspace's own lesson about reading per-machine state first.
- Done: `audio.rs` ring buffer replaces the cleared-per-take `Vec`; cursor-based reads;
  `record_from` for takes that begin in the past; first-pause grace in `Endpointer`.
- Done: `wake.rs` — rustpotter spotter, train/forget/samples, sensitivity, live score.
- Done: `hands_free.rs` rewritten as Armed → Capturing → Dispatch over one open mic.
- Done: `stt.rs` decoder prompt biasing; engine restarts when the prompt changes.
- Done: console settings (`listen_first_pause_ms`, `listen_preroll_ms`, `wake_sensitivity`)
  with validation and a float branch in `_coerce` that was missing; four passthrough routes;
  wake recorder and Voice diagnostics panel in Settings.
- Done: live verification through the real API against a running debug build; two bugs found
  and fixed that way (see [[T-019-verification]]).
- Blocked: reply speed. `OPENROUTER_API_KEY` is in `.env` with an empty value and both local
  runtimes are down, so `claude` is correctly the only backend that resolves. Reported in
  the UI rather than worked around.
- Next: record a real wake word on this machine and try it; then `close-work`.

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
