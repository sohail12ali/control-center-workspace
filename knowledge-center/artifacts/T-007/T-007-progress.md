---
ticket: "T-007"
artifact: progress
---

# Progress: T-007

## Status Summary
Stage: VERIFY — pixels reach vision models, the feature registry tells the truth. Ready to close.

## Dated Log

### 2026-09-07
- Done: 
- Started: 
- Blocked: 
- Next: 

- Done: TEMPLATE — `console/server/multimodal.py`, wired into the `openai_api` tool loop. When a capture tool returns, the session appends one follow-up user message: the picture as an `image_url` part for a model matching `vision_models`, or a sentence naming `desktop_ocr` for one that does not. Images ride on a user message because the tool protocol says a `tool` message is text, which also makes the transcript read correctly — the tool reported a capture, then the picture arrived.
- Done: TEMPLATE — `vision_models` now ships populated with globs rather than empty. Empty was the safe default but meant captures were never actually looked at; globs keep working as model ids move.
- Done: TEMPLATE — `desktop/features.toml` set to what is ACTUALLY built. It had been understating badly: voice, clipboard and capture all landed in T-005/T-006 while their rows still said "needs phase 3/4". Fifteen rows are now available; the ten that are not each say why, in terms of the missing work rather than a phase number. `dictate`, `mic_muted`, `listen_hands_free` and `clipboard_attach_no_send` stay unavailable because they genuinely are not built.
- Done: VERIFY — **pytest 1061 passed** (1023 before T-007), **cargo test 84**, lint clean. 34 unit tests plus 3 that drive the REAL session loop against a scripted provider and read what went on the wire: a vision model receives a base64 PNG data URL, a text-only model receives the OCR instruction and no pixels, and an ordinary tool call adds nothing.
- Done: SIMPLIFY — deleted an "attach the path to the prompt" helper written for CLI backends. They already get the path in the tool result and open it themselves, so it duplicated what was already said; an unused function with a confident docstring is worse than no function. Also replaced `test_non_skeleton_unavailable`, which asserted nothing outside the T-002 skeleton was available — true when written, false for three tickets — with an exact-set check that fails both ways: a row flipped without the work, and work landed without the row.
- Note: the destination chip from the plan was NOT built, and is not needed for safety. Screenshot is gated on every hosted backend, and the approval card already names the destination ("capture {target} -> {backend}"), so the chip would be a second copy of a decision the card already puts in front of a human. Recorded as a deliberate cut rather than an omission.
- Note: `/send image_path` was also cut. It was in the plan as an explicit user attach, but there is no UI that would call it, and an endpoint with no consumer is surface to maintain and mis-secure for nothing. The model-driven path covers the actual use case.
- Blocked: none.
- Next: `close-work`. Remaining backlog is hands-free listening, actuation and watch mode; T-002 still needs its manual tray click-through.

## Links
- [[T-007-summary]] · [[T-007-analysis]] · [[T-007-requirements]] · [[T-007-decision-log]] · [[T-007-plan]] · [[T-007-progress]] · [[T-007-verification]]
