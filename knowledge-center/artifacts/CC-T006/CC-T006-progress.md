---
ticket: "CC-T006"
artifact: progress
---

# Progress: CC-T006

## Status Summary
Stage: Closed — three tasks done; one gap needing the user's Telegram credentials.

## Dated Log

### 2026-08-29

**All three tasks done (~6 h vs 9 h est). 500 tests passing; harness lint clean.**

- **Telegram notifications.** Fires when an approval parks, off the calling thread and
  best-effort. The message leads with the file and the size of the change, or the command,
  because the question on a lock screen is whether to walk to a laptop — a generic "approval
  needed" tells you nothing the buzz did not. Credentials are read per send and the failure
  path reports a status code rather than the URL, since the URL carries the bot token.
- **Bind warning.** Any non-loopback host now prints four lines at every start naming the
  address and saying the console has no authentication of its own. The Tailscale model is
  only safe while it is known, so it is announced rather than assumed.
- **Audit trail.** Only actions that start work or change state, with the client address.
  Reads are excluded on purpose: a log recording every board poll is one nobody scrolls.
- **The scope shrank because the question was asked.** Token auth, HMAC signing and TLS were
  all in the original Phase 3 sketch and are all unnecessary given a tailnet that
  authenticates first. Recorded as a decision, not dropped quietly.
- **A defect the work found in itself:** the new audit trail immediately showed four verb runs
  nobody had performed. They came from `test_plugins.py`, which runs against the real checkout
  on purpose — so once the routes audited, the tests wrote into the real workspace. Silenced
  there and the stray records deleted.

- Done: CC-T006-01, -02, -03.
- Gap: no live Telegram send — needs the user's bot token and chat id, then `notify test`.
- Next: Phase 5 (evals and evidence-based skill pruning) is the last roadmap phase.

## Links
- [[CC-T006-summary]] · [[CC-T006-analysis]] · [[CC-T006-requirements]] · [[CC-T006-decision-log]] · [[CC-T006-plan]] · [[CC-T006-progress]] · [[CC-T006-verification]]

