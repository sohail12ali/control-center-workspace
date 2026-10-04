---
ticket: "CC-T006"
artifact: decision-log
---

# Decisions: CC-T006

These were answered by the user on 2026-08-29, before any code was written. Recorded here
so the ticket carries its own premises when it is picked up.

## remote-access-via-tailscale

**Decision:** Reach the console over Tailscale (or an equivalent private VPN). The console
does **not** terminate public traffic and does not become the security boundary.

**Rationale:** User's choice among Tailscale, a Cloudflare tunnel, and a LAN bind with a
bearer token. It carries the least new attack surface: the tailnet already authenticates, so
nothing here has to get authentication right from scratch.

**Impact on scope:**

- Add a configurable bind address (still defaulting to `127.0.0.1`) with a loud startup line
  whenever it is anything else — a console listening beyond loopback must never be a quiet
  fact.
- Add an audit log: who dispatched what, from where, when.
- Do **not** build token auth, HMAC signing, or TLS termination. Building a second, weaker
  authentication layer beside a working one adds risk without adding safety.
- Keep the existing `X-Console-Request` header check on writes; it is CSRF defence, not
  authentication, and is still needed.
- Full-bypass permission modes stay unavailable remotely, per the standing rule in
  `agents.toml`.

## approval-notifications-via-telegram

**Decision:** Telegram bot for "Permission needed" cards.

**Rationale:** User's choice among ntfy, Pushover, Slack and Telegram. Free, instant, and the
app is already installed.

**Impact on scope:**

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment, read per send, never
  stored and never logged — same discipline as the OpenRouter key.
- Notify on `approval.request`, and on turn end for a run started remotely.
- **Fail soft.** A notification that cannot be delivered must never block or fail the run it
  is describing; it is reported in the event stream and the run continues to its normal
  300-second deny.
- This is a hard prerequisite for remote running, not a nicety: without it a remote run
  stalls at the first gated tool and the timeout denies it.

## Links
- [[CC-T006-summary]] · [[CC-T006-decision-log]] · [[CC-T006-plan]] · [[CC-T006-progress]] · [[CC-T006-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
