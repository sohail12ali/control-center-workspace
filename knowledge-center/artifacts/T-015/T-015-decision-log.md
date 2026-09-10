---
ticket: "T-015"
artifact: decision-log
---

# Decisions: T-015

## openrouter-ahead-of-the-clis
**Decision:** `assistant_config.LOCAL_FIRST` becomes
`("ollama", "lm-studio", "openrouter", "claude", "cursor-agent")` — a hosted API row now
outranks a coding CLI for the TALK role. `work_backend` is untouched.  
**Rationale:** the old order put `claude` third, so a machine with no usable local model
held every conversation through the Claude Code CLI. `knowledge-center/telemetry/2026-09.jsonl`
prices that: 2.4s on a good turn, 307s on a bad one, to answer a question about ticket
lanes. The T-014 split is right — a CLI is a fine place to send *work* — it was the
ordering that sent talking there too.  
**Impact:** a machine with a key gets a ~1s talk model by default. A machine with neither
a key nor a local server still lands on `claude` and says why.

## reachable-is-not-usable
**Decision:** a keyless API row (`auth = "none"`) must pass `talk_ready` before it is
chosen: a model resident, and that resident model claiming tool support.  
**Rationale:** `installed` for an API row means only "something answered at that address".
All three real failures in `console/.cache/agent-chats/` got past it and died mid-turn —
`qwen3:8b` wanting 5.5 GiB with 4.7 free, `deepseek-coder` "does not support tools", a
reachable LM Studio with nothing loaded. From the outside each reads as a broken
assistant rather than a bad pick.  
**Impact:** two extra requests when considering a local runtime, cached for 10s. Nothing
for a CLI or a keyed provider. A silence from the server gets the benefit of the doubt —
`None` is "cannot say", not "nothing loaded", and the tool flag is documented as a hint.

## auth-none-not-is-local
**Decision:** the preflight is gated on `backend.auth == "none"`, not `backend.is_local`.  
**Rationale:** `is_local` tests whether the host is `127.0.0.1`. This machine's LM Studio
is at `192.168.1.14` — a box that swaps models one at a time, i.e. exactly the case the
preflight exists for, which `is_local` would classify as hosted and skip. `auth = "none"`
names the real class: a model runtime you run yourself, LAN or not.  
**Impact:** caught before shipping, by asking what the predicate would say about the
provider that actually broke.

## availability-is-not-the-settings-endpoints-job
**Decision:** `GET /api/assistant/settings` stops returning `installed`. The Settings tab
reads availability from `GET /api/agents/backends`, which it already polls. Writes still
validate a chosen backend strictly.  
**Rationale:** computing `installed` probes every API row at
`agent_backends.PROBE_TIMEOUT` (1.5s). That endpoint is on the desktop shell's hot path —
every take, and until this ticket every tray click. **Measured: 3092ms cold versus 8ms
now.** A read that is allowed to touch the network cannot be on a hot path; a write can
afford to be strict.  
**Impact:** one extra request on the Settings tab, where slowness is expected and
explained. The 3-second stall a previous ticket had already papered over with a
client-side cache is gone at the source.

## the-opening-message-was-never-load-bearing
**Decision:** `agent_manager.create(..., open=False)` starts a session and sends nothing.
The Assistant uses it.  
**Rationale:** sending a message was the only way to start a session, so the Assistant
said "Hello." — and the first thing you actually said queued behind a full turn spent
answering a greeting.  
**Impact:** a backend with no system-prompt flag has its persona parked on the session
for the first real send. Consumed in `BaseSession.send`, deliberately, because that is the
one path every caller goes through — the assistant feature calls `send` directly rather
than through `agent_manager.send`, so a fix in either caller alone would have left the
other silently dropping the persona.

## the-tray-is-generated-not-described
**Decision:** the menu is built by walking `desktop/features.toml`
(`desktop/src-tauri/src/features.rs`), parsed from an `include_str!` at compile time.  
**Rationale:** the registry has called itself the source of truth since T-002 and a test
held it to describing reality — but the menu was eight items typed by hand against sixteen
features marked available. Clipboard copy, clipboard send, both captures and the whole
listening submenu were implemented, declared, and unreachable. Two sources of truth drift;
one cannot.  
**Impact:** 15 rows where 10 were. A malformed registry is a failed build rather than a
shell that starts with a silently defaulted menu. Adding a feature is a row plus a
dispatch arm, and both directions of that are checked — Rust warns at startup, a Python
test fails.

## never_one_click-is-read-not-restated
**Decision:** the three gated rows are routed by *reading* `feature.never_one_click`, not
by listing their ids in the match.  
**Rationale:** the first implementation listed them, which left the registry field
declared, tested, and deciding nothing — the same two-sources-of-truth problem the
generated menu exists to remove. The release build's `dead_code` warning is what caught
it.  
**Impact:** `clipboard_send`, `capture_this_turn` and `capture_region` open the window
instead of acting, because a click cannot tell you what is about to be sent and a
clipboard can hold a password. A future gated row gets that behaviour by declaring it.

## risk-is-informational-and-says-so
**Decision:** `risk` is used in a startup summary line, not in an invariant.  
**Rationale:** the tempting check — "a gated row must be `never_one_click`" — is FALSE in
this registry: `listen_hands_free` is gated and one-click on purpose, because toggling a
microphone from the icon is the feature. A warning that fires on every launch for correct
configuration trains people to ignore warnings.  
**Impact:** `tray: 18 rows — session_backend show_window … clipboard_send[gated,opens-window] …`
in the log. The tray is invisible to UI Automation, so one line answers "what was on your
menu" without a Win32 drive.

## the-overlay-emits-it-does-not-call
**Decision:** every overlay control emits a Tauri event; the shell does the work. No
`invoke_handler`, no new capability, no console call from the page.  
**Rationale:** `hud.html` has always been deliberately dumb, and the reason is stated in
its own header: it is always-on-top over whatever you are working in, and a credential in
it would be a poor trade for a level meter. Adding buttons must not change that. The `hud`
window already holds `core:event:default`.  
**Impact:** the page still cannot reach the console; it can only say what was pressed.

## the-overlay-may-answer-a-card
**Decision:** Allow and Deny appear on the panel, including for
`agent_approvals.LOCAL_ONLY` tools, via a new `POST /api/assistant/approve`.  
**Rationale:** the rule for a desk-only tool is that a human *at the machine* decides —
and the panel is a window on that machine's screen. It is the remote paths (Telegram) that
must not get buttons. Meanwhile "open the window" was a longer way of not answering, and
an unanswered card is denied on the console's own timeout.  
**Impact:** a new route rather than reusing `/api/agents/chats/{sid}/approve`, because
there is exactly one Assistant chat and the console is what knows which — making the
overlay look it up first would be two round trips to answer a yes/no question.

## a-watchdog-rather-than-a-proof
**Decision:** the panel hides after 120s with no state change, on top of fixing the two
specific paths that stranded it.  
**Rationale:** the specific fixes — hide on `ApprovalResolved`, clear a stale card on a
lost stream — close the cases that were found. The watchdog is what makes the *next* one
cosmetic instead of blocking. 120s because it must be longer than a slow turn (hiding the
panel while a model is thinking would be worse) and far shorter than forever.  
**Impact:** a generation counter bumped on every state change, so "did anything happen"
needs no clock arithmetic and no lock.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
