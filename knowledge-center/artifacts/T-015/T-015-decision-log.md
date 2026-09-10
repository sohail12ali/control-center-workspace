---
ticket: "T-015"
artifact: decision-log
---

# Decisions: T-015

## openrouter-ahead-of-the-clis
**Decision:** `assistant_config.LOCAL_FIRST` becomes
`("ollama", "lm-studio", "openrouter", "claude", "cursor-agent")` — a hosted API row now
outranks a coding CLI for the TALK role.

*Superseded in part, same day:* this entry originally said "`work_backend` is untouched",
which was true when it was written and is not now — see
[[#work-resolves-local-first-too]]. The work role got the same treatment on request.  
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

## work-resolves-local-first-too
**Decision:** `work_backend = ""` means resolve at use time through `WORK_FIRST`
(local-first), the way `backend` already did. `delegate` resolves through the chain and
reports what it passed over.  
**Rationale:** the work role had no chain at all — one id, set by hand, and `delegate`
refused outright when it was empty. In practice that pinned work to whichever CLI was
chosen once, which is how a machine with Ollama AND LM Studio installed sent every task to
a hosted coding agent.  
**Impact:** what has NOT changed is the refusal that matters: `delegate` still never runs
the task on the talk model. If nothing in the chain is ready it says so and names what it
tried.

## work-has-a-higher-bar-than-talking
**Decision:** `work_ready` = `talk_ready` plus tool calling (not optional) and
`WORK_MIN_CONTEXT` of 16k. A model that fails either is still used for talking.  
**Rationale:** the two roles want different things, which is the whole premise of T-014's
split. A model that cannot call a tool can hold a conversation but cannot change a line of
code. A work turn carries a file, an edit, a command's output and often a test log; below
about 16k that stops fitting, and a model that has forgotten the start of its own task
reads as one that will not follow instructions.  
**Impact:** judged separately per role, so a small local model can be the talk model while
work goes elsewhere — which is the useful outcome on modest hardware.

## loaded-context-not-advertised-context
**Decision:** `model_catalog.capabilities` reports the context the runtime actually LOADED
(`loaded_context_length`, or `loaded_instances[].config.context_length`), keeping
`max_context` alongside.  
**Rationale:** it reported `max_context_length` — what the weights support. Qwen3-4B says
262144; LM Studio had it loaded at **8192**. Only the loaded figure constrains a turn, so
the preflight was passing a model that would silently truncate a file plus a diff plus a
test log. Caught by loading a real model and watching the check say PASS when the honest
answer was no.  
**Impact:** the same model went from passing to a correct refusal purely because the real
number arrived. The refusal names the shortfall and says it is still fine for talking.

## backend_chain-rather-than-a-local-only-boolean
**Decision:** one setting, `backend_chain` — comma-separated ids, ordered, applying to both
roles. Empty means the built-in local-first order.  
**Rationale:** "never use a CLI" needed saying, and a boolean to mean it would have been a
second thing that can disagree with the order. Naming the backends you accept says it
directly, and a role with none of them available then FAILS and reports what it tried
rather than falling through to something you did not want. Which of those two you want —
strict, or always-working — is a genuine preference that no default can settle.  
**Impact:** also closes the approved plan's "settings-driven ordered chain", which the
first pass implemented as a constant and recorded as a delta.

## local-is-now-possible-and-slow-and-both-are-said
**Decision:** ship local-first for both roles as asked, and record the measured cost
prominently rather than in a footnote.  
**Rationale:** local now demonstrably works — three real turns, all correct answers, tools
called properly. It is also **121-201 seconds per turn** on this hardware, against 2.4-6.6s
for the CLI it replaced. The cause is not the model: a turn is 2-3 sequential tool rounds,
each re-processing a 5-7k-token prompt (7393-char system prompt + 26 tool definitions) on a
box with a 2 GB-VRAM iGPU that processes prompt at roughly 100 tokens/second.  
**Impact:** the request was honoured and the trade is now a number instead of a guess. The
useful lever is not a different 4B model — it is either a hosted talk model
(`OPENROUTER_API_KEY`) or a smaller injected prompt, and the second is its own ticket. If
LM Studio is closed the chain degrades to the next candidate with a stated reason, so
nothing breaks.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
