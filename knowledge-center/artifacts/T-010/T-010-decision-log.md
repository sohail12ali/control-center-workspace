---
ticket: "T-010"
artifact: decision-log
---

# Decisions: T-010

## measure-before-fixing
**Decision:** Instrument the whole take path first, and only then change
anything.
**Rationale:** The visible symptom was "3 seconds before the mic opens", and
the three obvious suspects — device enumeration, the availability checks, the
tray call — were all wrong. The checks cost 3 ms and painting costs 3 ms.
**Impact:** The real cause (a lock held across a sleep) would not have been
found by fixing what looked slow, and the timing lines stayed in the code.

## the-room-is-measured-and-a-run-is-required
**Decision:** Calibrate the detector on the first 200 ms of each take, and
require three consecutive speech frames before resetting the silence counter.
**Rationale:** Thresholds alone were not enough — the first live run after
adding them still took 9.4 s for a 3-second phrase, because one loud frame per
second was enough to hold the take open.
**Impact:** `SPEECH_RUN = 3` (48 ms) is shorter than any syllable and longer
than any click.

## a-warm-microphone-only-where-it-is-already-on
**Decision:** Hands-free opens the microphone once per session; push-to-talk
opens and closes per take.
**Rationale:** Reopening between hands-free takes buys no privacy — the mic is
openly on — and makes the assistant deaf for a second exactly where the next
wake word lands. For push-to-talk, holding it open would light the OS
indicator while nothing is being recorded, which is the kind of lie this
project keeps refusing to tell.
**Impact:** `audio::Mic` is owned by the caller's thread; `cpal::Stream` is
not `Send`, and the hands-free loop is a thread, so that works out.

## the-overlay-is-a-read-out
**Decision:** A separate always-on-top window with no API access, fed by
`eval` from the shell.
**Rationale:** It sits over whatever you are working in. A panel with a token
in it would be a bad trade for a level meter.
**Impact:** `console/static/hud.html` is dumb by construction; the level comes
from the frames the VAD already scores.

## one-switch-for-speaking
**Decision:** The tray's *Mute replies* writes the Assistant's `speak`
setting, and reads it at startup.
**Rationale:** They disagreed. The tray mirrored a browser preference while
the server-side setting decided what actually happened, so the tray could show
"muted" over an assistant that was talking.
**Impact:** The webview's `autoRead` keeps its own job — the browser's
read-aloud — and the Settings panel says which is which.

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
