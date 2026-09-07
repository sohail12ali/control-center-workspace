---
ticket: "T-007"
artifact: verification
---

# Verification: T-007

Verified 2026-09-07. **pytest 1061 passed** (1023 before T-007),
**cargo test 84 passed**, harness lint clean.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | A vision model receives the pixels | PASS | Drives the real `ApiSession` loop against a scripted provider and reads the wire: the last request carries a `user` message whose content is a parts list with an `image_url` holding a `data:image/png;base64,` URL, and the decoded bytes are the file's |
| 2 | A text-only model is told, not left guessing | PASS | Same harness: the follow-up is a string naming `desktop_ocr`, and **no** image part reaches the wire. It also asks the model to say it worked from OCR — a confident description of a screen nobody looked at is the worst outcome this feature can produce |
| 3 | Other tool calls are untouched | PASS | An ordinary `console_context` call leaves exactly the one user message the person sent |
| 4 | Vision detection is configurable and honest | PASS | Globs from `assistant.toml`; `qwen2.5vl:7b`, `gpt-4o-mini`, `claude-sonnet-5`, `llava:13b` match, `llama3` and `mistral` do not. Empty list means "assume none" |
| 5 | The capture path is confined | PASS | The path arrives inside a tool result, i.e. model-influenced text. `../../.env`, a traversal through the captures directory, an absolute path, and the assistant's own memory file are all refused, and a refusal reaches the model as a sentence rather than an attachment |
| 6 | Oversized captures are refused, not truncated | PASS | Reported with its size and a pointer to OCR |
| 7 | Both tool spellings are recognised | PASS | `console_desktop_screenshot` and `mcp__console__desktop-screenshot` — the same verb reaches a model under two names depending on transport, and missing one would silently skip the attachment |
| 8 | `features.toml` matches what is built | PASS | 15 rows available, 10 not, each of the 10 explaining itself in terms of the missing work. Pinned by an exact-set test that fails in both directions |
| 9 | Destination chip | **CUT** | Not built, and not needed for safety: screenshot is gated on every hosted backend and the approval card already names the destination. See Notes |
| 10 | `/send image_path` | **CUT** | No UI would call it. See Notes |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1061 passed
cargo test                            ->   84 passed
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

## Edge Cases Probed

- A failed capture (`{"ok": false}`) produces no follow-up at all.
- A tool result that is not JSON, is `{}`, is `[]`, or is empty: no follow-up.
- A bare `.png` path instead of the JSON shape still attaches, so a tool that
  changes shape does not silently stop working.
- A path inside the captures directory that does not exist is refused.
- Model ids are matched case-insensitively (`QWEN2.5VL:7B`).

## Notes

### Two things from the plan were cut, deliberately

**The destination chip.** The plan wanted the composer to show "this turn
includes a screenshot → {backend}" before sending. It is not built, and on
inspection it is not load-bearing: `desktop-screenshot` is gated on every
hosted backend, and the approval card already says `capture {target} ->
{backend}` in front of a human who must click Allow. The chip would be a
second rendering of a decision already made, in a place the user has already
passed. Cutting it removes UI, not a safeguard.

**`/send image_path`.** An endpoint for a user to attach an image explicitly.
Nothing in the UI would call it, and an endpoint with no consumer is surface
to keep working and to get the confinement right on, for no one. The
model-driven path — ask for a screenshot, get one, look at it — is the actual
use case and it works.

Both are recorded here as cuts rather than quietly dropped, so a later ticket
can disagree with the reasoning rather than rediscover the gap.

### The feature registry had been lying

`desktop/features.toml` still said voice "needs phase 3 local STT" and
clipboard "needs phase 4" after both had shipped. It is the file the tray and
Settings project from, so an out-of-date row is a greyed-out control with a
wrong explanation attached. Every row is now set to what the code does, and
the test that pinned "nothing outside the skeleton is available" — true when
written, false for three tickets — is replaced by an exact-set check that
fails if a row claims too much OR too little.

### Not verified

- **A real vision model looking at a real screenshot.** The wire format is
  proven end to end against a scripted provider; what is untested is a live
  OpenRouter or Ollama vision model receiving it. That needs a key or a pulled
  model, and either is the user's call.
- **macOS and Linux**: unchanged by this ticket, and still unexercised.

## Links
- [[T-007-summary]] · [[T-007-analysis]] · [[T-007-requirements]] · [[T-007-decision-log]] · [[T-007-plan]] · [[T-007-progress]] · [[T-007-verification]]
