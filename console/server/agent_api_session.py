"""The `openai_api` transport — an agent loop the console owns.

## Where this sits

`agent_session` has two transports, both of which drive somebody else's agent:
`LiveSession` holds one CLI process with stdin open, `TurnSession` runs one per
turn. Both inherit that CLI's tools, its permission model, and its idea of what
a skill is.

This is the third shape: there is no CLI. The console talks to an HTTP API and
runs the loop itself — send the conversation, receive text and tool calls,
execute the tools, send the results back, repeat until the model stops asking.

Owning the loop is the whole point. It means the tools are the console's own
verbs, the gate is the same "Permission needed" card a human already answers,
and telemetry is recorded by the same path every other backend uses.

## What it must not do differently

**Events.** It publishes the same normalized events that `agent_normalize`
produces for the CLI backends. The chat UI, the transcript reader and the
telemetry hook are all written against that shape; a second shape would mean a
second renderer, and the two would drift.

They did drift. This module used to publish `text.stop` where the renderer
listens for `text.done`, `tool.start` carrying `input` where it reads `args`,
and `tool.end` — an event nothing anywhere consumed — instead of
`tool.result`. It also left `block` off every tool event, and `block` is the
key the store files items under, so every tool call in a chat collapsed onto
the single key `undefined`. The visible result was a console-agent transcript
whose tool calls showed no arguments and never resolved, an always-empty "files
touched" panel (it is derived from `args`), and read-aloud that never fired
because no text block was ever marked closed.

So: `block` is allocated per content block from one session-wide counter, the
way the normalizer does it, and the event names below are the renderer's, not
this module's own.

**Gating.** `agent_approvals.REGISTRY.request()` takes a `publish` callable and
blocks the calling thread. That was built for a hook process, but nothing about
it is hook-specific — in-process it is a strictly better gate, with no hook
subprocess and no HTTP round trip, showing the human the identical card.

## The runaway problem

A loop that can call tools can call them forever, and every round costs money,
so the number of rounds is capped. When the cap is hit the turn ends with a
notice saying so rather than silently stopping, because "the agent stopped
early" and "the agent finished" look identical in a transcript otherwise.

Both budgets — rounds per turn, and messages of history kept — are read off the
backend row (`agent_backends.Backend.max_tool_rounds` /
`.max_history_messages`), not fixed here. They used to be module constants, and
one pair of numbers cannot be right for both a 4k local model and a 200k hosted
one: the history cap overflowed the first long before it was reached, and the
round cap was timid for the second.
"""

import json
import threading

from . import agent_approvals
from . import agent_tools
from . import multimodal
from . import openai_client
from . import prompt_build
from . import telemetry
from .agent_session import BaseSession


class ApiSession(BaseSession):
    """One conversation with an OpenAI-compatible endpoint."""

    steerable = False  # a queued message is delivered between turns, not mid-turn

    def __init__(self, sid, backend, cwd, stream, **kw):
        super().__init__(sid, backend, cwd, stream, **kw)
        raw = backend.raw
        # No OpenRouter default: a row with no api_key_env is a KEYLESS
        # provider (Ollama, LM Studio), not an OpenRouter one. Defaulting sent
        # the user's OpenRouter key to whatever base_url the row named.
        self.client = openai_client.Client(
            base_url=raw.get("base_url"),
            api_key_env=backend.api_key_env,
            timeout=int(raw.get("timeout") or openai_client.DEFAULT_TIMEOUT),
            extra_headers=dict(raw.get("extra_headers", {}) or {}))
        self.model = self.model or raw.get("default_model") or ""
        # Read once at construction: a chat should not change its own limits
        # halfway through because someone edited agents.toml mid-conversation.
        self.max_tool_rounds = backend.max_tool_rounds
        self.max_history_messages = backend.max_history_messages
        self._gated = set(backend.gated_tools or ())
        self._messages = []
        self._alive = True
        self._turn_thread = None
        self._interrupt = threading.Event()
        self._system_report = {}
        # One counter for the whole session, not per turn. The store keys items
        # by block, so a number that restarts each turn makes round two
        # overwrite round one's bubbles.
        self._block = 0

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        self.started = self._stamp()
        system, report = prompt_build.build(
            self.cwd, persona=self.persona, skill=self.skill,
            ticket=self.ticket, extra=self.extra)
        self._system_report = report
        self._messages = [{"role": "system", "content": system}]
        self.stream.publish({
            "type": "session.init", "id": self.id, "model": self.model,
            "backend": self.agent,
            # Surfaced rather than logged: if a skill was cut to fit, the
            # person watching should know before they trust the answer.
            "prompt": {"chars": report["chars"],
                       "included": report["included"],
                       "truncated": report["truncated"],
                       "missing": report["missing"]},
        })
        if report["missing"]:
            self._notice("warn", "prompt",
                         "Not found and therefore not injected: %s"
                         % ", ".join(report["missing"]))
        if report["truncated"]:
            self._notice("warn", "prompt",
                         "Prompt budget cut: %s" % ", ".join(report["truncated"]))
        return self

    @staticmethod
    def _stamp():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def alive(self):
        return self._alive

    def stop(self):
        self._interrupt.set()
        self._alive = False
        self.exit_code = 0
        self._finish()

    def interrupt(self):
        """Ask the loop to stop after the tool call in flight.

        There is no way to abort a request already in the provider's hands, so
        this does not claim to. It stops the *next* round, which is the honest
        version of the promise.
        """
        self._interrupt.set()
        self._notice("info", "interrupt",
                     "Stopping after the current step; a request already sent "
                     "cannot be recalled.")
        return True

    # -- speaking ----------------------------------------------------------
    def _deliver(self, text):
        """Called by BaseSession's queue drain with one user message."""
        self._messages.append({"role": "user", "content": text})
        self._turn_thread = threading.Thread(target=self._run_turn, daemon=True)
        self._turn_thread.start()

    # -- events ------------------------------------------------------------
    def _notice(self, level, kind, text):
        self.stream.publish({"type": "notice", "level": level, "kind": kind,
                             "text": text})

    def _next_block(self):
        self._block += 1
        return self._block

    # -- the loop ----------------------------------------------------------
    def _run_turn(self):
        tools = agent_tools.tool_definitions(self.cwd)
        rounds = 0
        total_in = total_out = 0
        reported_cost = 0.0
        cost_reported = False
        stop_reason = ""

        try:
            while True:
                if self._interrupt.is_set():
                    stop_reason = "interrupted"
                    break
                if rounds >= self.max_tool_rounds:
                    # Silently stopping looks identical to finishing.
                    self._notice(
                        "warn", "tool_limit",
                        "Stopped after %d tool rounds in one turn. The task is "
                        "not necessarily finished — ask it to continue if it "
                        "should." % self.max_tool_rounds)
                    stop_reason = "tool_limit"
                    break

                # Allocated on the FIRST chunk, so a round that returns only
                # tool calls opens no empty text bubble.
                text_block = [None]

                def on_text(chunk, holder=text_block):
                    if holder[0] is None:
                        holder[0] = self._next_block()
                        self.stream.publish({"type": "text.start",
                                             "block": holder[0]})
                    self.stream.publish({"type": "text.delta",
                                         "block": holder[0], "text": chunk})

                result = self.client.stream(
                    self._trimmed_messages(), model=self.model, tools=tools,
                    on_text=on_text)

                if text_block[0] is not None:
                    # `text.done`, not `text.stop`: this is what closes the
                    # block, and an unclosed block is one read-aloud skips.
                    self.stream.publish({"type": "text.done",
                                         "block": text_block[0]})

                total_in += result.input_tokens
                total_out += result.output_tokens
                if result.cost_usd is not None:
                    reported_cost += result.cost_usd
                    cost_reported = True
                if result.input_tokens or result.output_tokens:
                    self.stream.publish({
                        "type": "usage",
                        "input_tokens": total_in, "output_tokens": total_out})

                assistant = {"role": "assistant",
                             "content": result.content or None}
                if result.tool_calls:
                    assistant["tool_calls"] = [c.as_message_part()
                                               for c in result.tool_calls]
                self._messages.append(assistant)

                if not result.tool_calls:
                    stop_reason = result.finish_reason or "stop"
                    break

                rounds += 1
                for call in result.tool_calls:
                    tool_result = self._execute(call, rounds)
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": call.id or ("call_%d" % call.index),
                        "content": tool_result,
                    })
                    # A screenshot tool hands back a PATH, which an API
                    # backend has no way to open — it has no file tools. So
                    # for a vision-capable model the picture itself follows as
                    # an image part, and for a text-only one a sentence saying
                    # to use OCR instead. Silence here is what produces a
                    # confident description of a screen nobody looked at.
                    follow_up = multimodal.after_capture(
                        self.cwd, call.name, tool_result, self.model,
                        self._vision_patterns())
                    if follow_up is not None:
                        self._messages.append(follow_up)

        except openai_client.ApiError as exc:
            self._notice("error", exc.kind, str(exc))
            stop_reason = "error"
        except Exception as exc:  # noqa: BLE001
            self._notice("error", "internal", "%s: %s" % (type(exc).__name__, exc))
            stop_reason = "error"

        end = {
            "type": "turn.end",
            "subtype": stop_reason,
            "is_error": stop_reason == "error",
            "cost_usd": reported_cost if cost_reported else 0.0,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "num_turns": 1,
            "duration_ms": 0,
        }
        # Publish BEFORE observing, for the same reason the CLI path does:
        # `_observe` reacts to turn.end by draining the queue, and draining
        # publishes the next turn.start. Observing first would open the next
        # turn at a lower sequence number than the turn it follows.
        self.stream.publish(end)
        self._observe(end)

    def _trimmed_messages(self):
        """System message plus the most recent history.

        The system message is never dropped — it carries the injected skill,
        and losing it mid-conversation would silently change what the agent
        thinks it was asked to do.
        """
        if len(self._messages) <= self.max_history_messages:
            return self._messages
        return [self._messages[0]] + self._messages[-(self.max_history_messages - 1):]

    # -- tools -------------------------------------------------------------
    def _execute(self, call, round_no=0):
        name = call.name or ""
        arguments = call.arguments
        block = self._next_block()
        # `args`, not `input` — `args` is the key the store reads, and the one
        # it derives "files touched" from. `round` rides along so the UI can
        # show budget pressure while the turn is still running; a renderer that
        # does not know the field simply ignores it, so the shape stays
        # additive rather than divergent.
        start = {"type": "tool.start", "block": block, "id": call.id,
                 "name": name, "round": round_no,
                 "max_rounds": self.max_tool_rounds}

        def finish(ok, content):
            self.stream.publish({"type": "tool.result", "id": call.id,
                                 "ok": ok, "content": content})
            return content

        if not call.arguments_valid:
            # Give the model the failure rather than a silent empty dict, so it
            # can re-emit the call properly instead of acting on nothing.
            self.stream.publish(dict(start, args={}))
            return finish(False,
                          "Error: the arguments for %s were not valid JSON. "
                          "Send them again as a single JSON object." % name)

        self.stream.publish(dict(start, args=arguments))

        if self._needs_approval(name):
            decision, reason = agent_approvals.REGISTRY.request(
                self.id, name, arguments, call.id or "",
                self.stream.publish,
                timeout=self.backend.approval_timeout,
                repo_root=self.cwd, title=self.title)
            if decision == "deny":
                return finish(False, "Denied: %s" % reason)

        return finish(True, agent_tools.dispatch(self.cwd, name, arguments))

    def _vision_patterns(self):
        """Model-id globs that can actually see a picture.

        Read from the Assistant's settings rather than hardcoded, because
        which models have vision changes far faster than this file does. An
        empty list means "assume none", which keeps the honest default.
        """
        try:
            from . import assistant_config
            return assistant_config.settings(self.cwd).get("vision_models") or []
        except Exception:  # noqa: BLE001
            return []

    def _needs_approval(self, name):
        """Gate by tool name, with read-only console verbs exempt.

        Every `console_*` verb that does not declare `needs_confirm` is a pure
        read — asking a human to approve "look up this ticket's lane" trains
        them to click allow without reading, which is exactly how the gate
        stops working for the calls that matter.
        """
        if name in self._gated:
            return True
        if name.startswith(agent_tools.VERB_PREFIX):
            return False
        return False

    # -- snapshot ----------------------------------------------------------
    def snapshot(self):
        snap = super().snapshot()
        snap["prompt"] = dict(self._system_report)
        snap["api"] = {"base_url": self.client.base_url,
                       "key_env": self.client.api_key_env,
                       "has_key": self.client.has_key}
        # The limits this chat is actually running under, so the UI can show
        # "3 of 25" without knowing the defaults or re-reading the config.
        snap["budgets"] = {"tool_rounds": self.max_tool_rounds,
                           "history_messages": self.max_history_messages}
        return snap
