---
ticket: "T-008"
artifact: decision-log
---

# Decisions: T-008

## gate-sits-between-transcription-and-sending
**Decision:** The wake-word check runs inside `listen`, after local
transcription and before the transcript is POSTed anywhere. `listen::take`
delegates to `take_gated`, which takes a closure.
**Rationale:** Anywhere later — the console, the model — would mean the room's
speech had already left the machine, which is the exact thing an always-on
microphone must not do. A closure rather than a policy type keeps `listen`
free of a dependency on `hands_free`, which depends on it.
**Impact:** An unaddressed take returns `Err("not addressed")`, which the loop
treats as a normal outcome rather than a fault.

## wake-word-must-start-the-utterance
**Decision:** The wake word matches as a whole word at the START, tolerating
leading punctuation and "hey"/"ok"/"hi" in front of it.
**Rationale:** It makes the rule predictable: "console, what's open" addresses
the assistant and "the console is slow today" does not, and a rule matching
anywhere in the sentence could not tell those two apart.
**Impact:** "Ask the console about X" mid-sentence is not heard as a command.
That is the intended trade.

## every-default-is-the-cautious-one
**Decision:** Wake word required, no listening while speaking, a 30-minute cap.
**Rationale:** The alternative to each is a surprise — the room going to a
model, the assistant answering itself, a microphone open all night.
**Impact:** Headphone users turn two of them off deliberately; the cap cannot
be set below one minute.

## the-approval-pause-is-not-configurable
**Decision:** Listening pauses while an approval card is open, even with
`listen_while_speaking` on.
**Rationale:** Not an echo question. Someone reading "allow this?" out loud, or
talking it over with a colleague, must not have that recorded and sent as
their next instruction.
**Impact:** One unconditional branch in `should_pause`.

## the-tray-tick-follows-the-outcome
**Decision:** The checkbox is set from what `toggle_hands_free` returns, and a
watcher corrects it when the loop ends on its own.
**Rationale:** Starting can fail (no speech model) and the loop can end by
itself (time cap). A ticked box over a closed microphone is the one state this
must never show — the mirror of the T-006 bug where the tray showed idle with
the microphone open.
**Impact:** A 2-second poll thread in `tray.rs`.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
