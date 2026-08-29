---
ticket: "CC-T006"
artifact: verification
---

# Verification: CC-T006

**Verified:** 2026-08-29 · **Result:** PASS with one stated gap (no live Telegram send — needs the user's bot token).

## Evidence

| Check | Result |
| --- | --- |
| `python -m pytest` | **500 passed, 1 skipped** |
| `python console/kanban.py harness lint` | `39 skills, 7 agents, 0 errors, 0 warnings` |
| `kanban notify status` | `ready: false`, reason "notifications are disabled in console.toml" |
| Live: `POST /api/verbs/harness-lint/run` | ran; audit row `verb.run 127.0.0.1 harness-lint ok` |
| Live: `POST /api/verbs/context/run` with no ticket | refused; audit row records the reason |
| `kanban audit` | both rows, newest first, with actor and outcome |

33 tests added.

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| A parked approval can reach a phone | **Met, unproven live** | Delivery, message shaping, event filtering and failure paths tested against a fake provider; see the gap |
| A failed notification never breaks a run | **Met** | A notifier that raises still leaves the card shown and the decision returned |
| No secret reaches a log, event or record | **Met** | `status` reports presence only; the HTTP failure path reports a status code, never the URL that carries the token |
| Listening beyond this machine is never quiet | **Met** | Loopback silent; `0.0.0.0`, a tailnet address and a LAN address each warn, naming the address and the lack of auth |
| State-changing actions are recorded with an actor | **Met** | Verified live over HTTP for a successful and a refused run |
| A failed audit write never breaks the work | **Met** | An unwritable directory returns None rather than raising |

## The gap

**No real Telegram message has been sent.** Everything up to the socket is exercised — the
enable/disable logic, event filtering, the message text, the URL-encoded body, HTTP failure
handling, and the fail-soft path — but a real send needs the user's bot token and chat id.

To close it: create a bot with BotFather, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`,
flip `[notify] enabled = true`, then run `kanban notify test`. That command exists precisely
because a notification path you have not tested is one you discover at the moment it matters.

## A defect the work found in itself

Wiring the audit trail made `kanban audit` show four `verb.run` rows nobody had performed.
They came from `test_plugins.py`, which deliberately runs against the **real** checkout
because its subject is the shipped config — and once the route handlers audited, those tests
began writing real records into the developer's own workspace.

Fixed with an autouse fixture that silences `audit.record` for that module, and the stray
records were deleted. Worth recording because the mechanism generalises: a test that runs
against the real root inherits every side effect later added to the code it calls. This one
surfaced only because the audit trail was the first such side effect visible from outside.

## What was deliberately not built

Token authentication, HMAC-signed dispatch, and TLS termination — all in the dossier's
original Phase 3 sketch, all made unnecessary by choosing Tailscale. The console has no
authentication of its own **on purpose**, documented in three places, and the startup warning
exists so that decision can never quietly stop being true.

## Effort

Estimated 9 h, actual ~6 h.

## Links
- [[CC-T006-summary]] · [[CC-T006-decision-log]] · [[CC-T006-plan]] · [[CC-T006-progress]] · [[CC-T006-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
