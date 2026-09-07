---
ticket: "T-008"
artifact: verification
---

# Verification: T-008

Verified 2026-09-07. **pytest 1076 passed** (1070 before this ticket's Python
tests), **cargo test 97 passed** (84 before T-008), plus a live run of the
built shell against a real microphone.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Starts and stops from the tray and the bridge; state is reported | PASS | Live: `POST /listen {"mode":"hands_free"}` → `{"hands_free":true}`; `GET /listen/state` → `hands_free:true, listening:true, engine_running:true, model:"ggml-base.en.bin"`; `{"mode":"hands_free_off"}` → `{"hands_free":false}`; an unknown mode is a 400. Tray row `listen_hands_free` calls the same entry point |
| 2 | Unaddressed speech never leaves the machine | PASS | Live: a spoken "The console is slow today" produced `listen: 3.5s of audio, ended by Silence` and **nothing else** — no `heard`, no send. The gate runs inside `listen` before `say()` |
| 3 | Whole-word wake match at the start, tolerant of punctuation and "hey"/"ok" | PASS | Unit: "Console, what's open?", "hey console …", "OK console …" match; "consolidate the tickets", "consoles are great", "the console is slow today" do not |
| 4 | The gate holds against real recogniser output | PASS | Four phrases synthesised, spoken, and transcribed by whisper.cpp `ggml-base.en`; the exact transcripts (leading spaces, punctuation and all) are pinned in `real_whisper_transcripts_are_gated_correctly` |
| 5 | Pauses while speaking; always while an approval is open | PASS | Unit on `should_pause`: paused while speaking by default, open on headphones (`listen_while_speaking`), and paused for an approval card even on headphones |
| 6 | A session ends at the time cap and says why | PASS | `run()` compares elapsed against the cap and calls `stop("reached the time limit")`; the reason is readable at `GET /listen/state` as `hands_free_stopped`, live-checked as `""` while running and set on stop |
| 7 | Settings validate | PASS | A one-character wake word and a zero-minute cap are refused; a wake word is stored trimmed; booleans coerce from form strings; the shipped `assistant.toml` is asserted equal to `DEFAULTS` |
| 8 | `features.toml` matches what is built | PASS | `listen_hands_free` flipped to available, pinned by the exact-set test that fails in both directions |

## Test Results

```
python -m pytest -o addopts=""     -> 1076 passed
cargo test (desktop/src-tauri)     ->   97 passed
```

Live run (built debug shell, real microphone, phrases played through the
speakers), from `console/.cache/desktop/host.log`:

```
hands-free: on (wake word required: yes, "console")
listen: 3.5s of audio, ended by Silence          <- overheard, discarded
listen: heard "Hey console, take a screenshot."
hands-free: sent "Hey console, take a screenshot."
hands-free: stopping (asked to stop)
hands-free: off (asked to stop)
```

## A bug the live run found

The first live run logged `hands-free: the console said HTTP/1.0 201 Created`
— reported as a failure, for a transcript the console had in fact accepted.
`listen::say` was checking for `200` alone, and the **first** message of a new
chat is answered `201 Created`. That is the ordinary case for the first thing
you say after launching, so push-to-talk had the same latent bug and nobody
had hit it in a test. Fixed to accept any 2xx (`listen::accepted`), with tests
for 200/201/204 and for 3xx/4xx/5xx/garbage.

This is the whole argument for running the thing: seven unit tests around the
send path did not find it, and one spoken sentence did.

## Known limitation — VAD on a noisy microphone

On the test machine's array microphone, a take often ran to the 20-second cap
(`ended by Capped`) instead of ending on silence, because the room floor stays
above the VAD threshold. Hands-free still works — the take is transcribed and
gated as normal — but the reply waits for the cap rather than for you to stop
talking, which feels slow. Tuning the VAD threshold (or making it adaptive to
the room) is follow-up work, not part of this ticket.

The doubled transcript in the same run ("Hey console, take a screenshot. Hey
console, take a screenshot.") is the same cause: a long take with the phrase
plus room noise, which the recogniser resolved by repeating it.

## Edge Cases Probed

- An empty wake word addresses everything — documented behaviour, not an
  accident: the console refuses to store one that short, and failing *open* on
  the gate had to be a deliberate answer rather than an emergent one.
- Stopping when nothing is running is harmless.
- A second `start` while running is refused with "hands-free is already on".
- A microphone or engine failure stops the loop rather than spinning it.
- Unknown `mode` on `POST /listen` is a 400, not a silent no-op.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
