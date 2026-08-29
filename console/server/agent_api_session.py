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

**Events.** It publishes the same normalized events (`text.start`,
`text.delta`, `tool.start`, `tool.end`, `usage`, `turn.end`) that
`agent_normalize` produces for the CLI backends. The chat UI, the transcript
reader and the telemetry hook are all written against that shape; a second
shape would mean a second renderer, and the two would drift.

**Gating.** `agent_approvals.REGISTRY.request()` takes a `publish` callable and
blocks the calling thread. That was built for a hook process, but nothing about
it is hook-specific — in-process it is a strictly better gate, with no hook
subprocess and no HTTP round trip, showing the human the identical card.

## The runaway problem

A loop that can call tools can call them forever, and every round costs money.
`MAX_TOOL_ROUNDS` caps it. When the cap is hit the turn ends with a notice
saying so rather than silently stopping, because "the agent stopped early" and
"the agent finished" look identical in a transcript otherwise.
"""

import json
import threading

from . import agent_approvals
from . import agent_tools
from . import openai_client
from . import prompt_build
from . import telemetry
from .agent_session import BaseSession

#: Tool-call rounds allowed in one turn before the loop stops itself.
MAX_TOOL_ROUNDS = 25

#: Conversation turns kept before the oldest are dropped. Cheap guard against
#: a long chat growing past the model's context; a real compaction strategy is
#: a later problem, and dropping the oldest is at least predictable.
MAX_HISTORY_MESSAGES = 120


class ApiSession(BaseSession):
    """One conversation with an OpenAI-compatible endpoint."""

    steerable = False  # a queued message is delivered between turns, not mid-turn

    def __init__(self, sid, backend, cwd, stream, **kw):
        super().__init__(sid, backend, cwd, stream, **kw)
        raw = backend.raw
        self.client = openai_client.Client(
            base_url=raw.get("base_url"),
            api_key_env=raw.get("api_key_env") or "OPENROUTER_API_KEY",
            timeout=int(raw.get("timeout") or openai_client.DEFAULT_TIMEOUT),
            extra_headers=dict(raw.get("extra_headers", {}) or {}))
        self.model = self.model or raw.get("default_model") or ""
        self._gated = set(backend.gated_tools or ())
        self._messages = []
        self._alive = True
        self._turn_thread = None
        self._interrupt = threading.Event()
        self._system_report = {}

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        self.started = self._stamp()
        system, report = prompt_build.build(
            self.cwd, persona=self.persona, skill=self.skill,
            ticket=self.ticket)
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

    def _emit_text(self, block, text, first):
        if first:
            self.stream.publish({"type": "text.start", "block": block})
        self.stream.publish({"type": "text.delta", "block": block, "text": text})

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
                if rounds >= MAX_TOOL_ROUNDS:
                    # Silently stopping looks identical to finishing.
                    self._notice(
                        "warn", "tool_limit",
                        "Stopped after %d tool rounds in one turn. The task is "
                        "not necessarily finished — ask it to continue if it "
                        "should." % MAX_TOOL_ROUNDS)
                    stop_reason = "tool_limit"
                    break

                block = [0]
                state = {"first": True}

                def on_text(chunk, block=block, state=state):
                    self._emit_text(block[0], chunk, state["first"])
                    state["first"] = False

                result = self.client.stream(
                    self._trimmed_messages(), model=self.model, tools=tools,
                    on_text=on_text)

                if not state["first"]:
                    self.stream.publish({"type": "text.stop", "block": block[0]})

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
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": call.id or ("call_%d" % call.index),
                        "content": self._execute(call),
                    })

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
        if len(self._messages) <= MAX_HISTORY_MESSAGES:
            return self._messages
        return [self._messages[0]] + self._messages[-(MAX_HISTORY_MESSAGES - 1):]

    # -- tools -------------------------------------------------------------
    def _execute(self, call):
        name = call.name or ""
        arguments = call.arguments

        if not call.arguments_valid:
            # Give the model the failure rather than a silent empty dict, so it
            # can re-emit the call properly instead of acting on nothing.
            self.stream.publish({"type": "tool.start", "id": call.id,
                                 "name": name, "input": {},
                                 "error": "unparseable arguments"})
            return ("Error: the arguments for %s were not valid JSON. "
                    "Send them again as a single JSON object." % name)

        self.stream.publish({"type": "tool.start", "id": call.id,
                             "name": name, "input": arguments})

        if self._needs_approval(name):
            decision, reason = agent_approvals.REGISTRY.request(
                self.id, name, arguments, call.id or "",
                self.stream.publish,
                timeout=self.backend.approval_timeout,
                repo_root=self.cwd, title=self.title)
            if decision == "deny":
                self.stream.publish({"type": "tool.end", "id": call.id,
                                     "name": name, "denied": True})
                return "Denied: %s" % reason

        output = agent_tools.dispatch(self.cwd, name, arguments)
        self.stream.publish({"type": "tool.end", "id": call.id, "name": name,
                             "chars": len(output)})
        return output

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
        return snap
