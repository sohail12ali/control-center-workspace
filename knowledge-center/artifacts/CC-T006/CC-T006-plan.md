---
ticket: "CC-T006"
artifact: plan
---

# Plan: CC-T006

## Approach

Phase 3b — remote running, on the two decisions the user made: **Tailscale** for reach,
**Telegram** for approvals. Both recorded in [[CC-T006-decision-log]] before any code.

The Tailscale answer makes the scope *smaller*, which is the point of having asked. Because
the tailnet authenticates before traffic arrives, the console does not need token auth, HMAC
signing, or TLS — and building a second, weaker authentication layer beside a working one
would add risk without adding safety. What is left is three things it genuinely does need:
know when it is listening beyond this machine, record what started work, and be able to reach
a human who is not at the desk.

That last one is not a nicety. A gated tool call denies after 300 seconds of silence, so
without notifications **every remote run stalls at its first write and dies quietly**.

## Tasks

### [x] CC-T006-01 — Telegram notifications (4 h)

- [x] `console/server/notify.py` — one channel behind one function, credentials read per send
      from the environment and never stored
- [x] Fires on `approval.request`, off the calling thread, best-effort
- [x] The message leads with the decision-relevant fact — which file and how much changed, or
      the command — because the question on a lock screen is "must I walk to a laptop"
- [x] `notify status` and `notify test`
- **Done-criteria:** a parked approval sends; a provider failure is reported without leaking
  the token; a broken notifier never breaks the gate.
- **Depends on:** —

### [x] CC-T006-02 — Bind address that announces itself (2 h)

- [x] `[general] host` already existed; a non-loopback value now prints a four-line warning at
      **every** start, naming the address and saying the console has no authentication
- [x] Config comments explain the Tailscale model rather than just the setting
- **Done-criteria:** loopback is silent; every other address warns and says why.
- **Depends on:** —

### [x] CC-T006-03 — Audit trail (3 h)

- [x] `console/server/audit.py` + `kanban audit`; client address captured on the request
- [x] Records only actions that start work or change state — chat start/stop, verb run/submit,
      approval decisions. Not reads.
- [x] Local and gitignored; a failed write is dropped, never raised
- **Done-criteria:** a verb run over HTTP appears with its actor and outcome; a refused run
  appears with the reason.
- **Depends on:** —

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T006-01 — Telegram | 4 h | channel + message + status/test + fail-soft |
| CC-T006-02 — Bind warning | 2 h | config + startup announce |
| CC-T006-03 — Audit | 3 h | store + route wiring + CLI |
| **Total** | **9 h** | |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Someone binds beyond loopback without a tailnet and exposes an unauthenticated console | Med | Critical | Warning at every start naming the address, plus config comments and two docs; loopback stays the default | Builder |
| A bot token leaks into a log or an event | Med | High | Read per send, never stored; the failure path reports a status code, never the URL — the URL contains the token. A test asserts it | Builder |
| A failed notification breaks a run | Med | High | Off-thread, best-effort, wrapped; a test asserts the gate still asks when the notifier throws | Builder |
| The audit log becomes noise nobody reads | High | Med | Only state-changing actions; reads are deliberately excluded | Builder |

## Not built, deliberately

Token authentication, HMAC-signed dispatch, and TLS termination — all in the dossier's
original Phase 3 sketch, all made unnecessary by the Tailscale decision. Listed here so their
absence reads as a choice rather than an omission.

## Links
- [[CC-T006-summary]] · [[CC-T006-decision-log]] · [[CC-T006-plan]] · [[CC-T006-progress]] · [[CC-T006-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T005-summary]]
