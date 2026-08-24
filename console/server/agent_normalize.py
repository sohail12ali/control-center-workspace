"""Raw CLI stream-json → one normalised event vocabulary.

Every backend speaks its own dialect. The UI must not: a transcript renderer
that branches on which CLI produced a line ends up with two half-tested
rendering paths. So each backend's output funnels through here and comes out
as the same small set of events, and the frontend only ever learns this list:

    session.init      the CLI reported its session id / model
    text.start        an assistant text block opened
    text.delta        …grew by `text`
    text.done         …closed, with the final `text`
    thinking.start/.delta/.done   same, for reasoning blocks
    tool.pending      a tool call is being composed (name known, args partial)
    tool.start        a tool call is dispatched, with parsed `args`
    tool.result       its output came back (`ok`, `content`)
    todo              the agent published a todo list
    plan              the agent published a plan
    usage             token counts
    turn.end          the turn finished (cost, tokens, duration)
    notice            something worth saying but not an error
    error             something went wrong
    raw               unrecognised — surfaced rather than swallowed

`raw` matters: a CLI that adds an event type should show up as something
visible rather than silently disappearing, so a version bump is a thing you
notice instead of a thing you debug.

Blocks are identified by a string id so deltas can find their block in the UI
without depending on arrival order.
"""

import json


def _text_of(content):
    """Flatten an Anthropic-style content array to plain text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for b in content:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            parts.append(b.get("text") or "")
        elif b.get("type") == "image":
            parts.append("[image]")
    return "".join(parts)


class Normalizer:
    """Stateful because deltas only make sense in sequence: a `text.delta`
    belongs to whichever block is currently open."""

    def __init__(self, flavor="claude"):
        self.flavor = flavor
        self._n = 0
        self._text_blk = ""
        self._think_blk = ""
        self._tools = {}
        # Whether this turn produced any assistant content. A turn that ends
        # with none is a real outcome worth naming — see _result.
        self._had_output = False

    # -- block ids -----------------------------------------------------------
    def _next_block(self):
        self._n += 1
        return "b%d" % self._n

    def _seal_text(self, text=""):
        if not self._text_blk:
            return []
        out = [{"type": "text.done", "block": self._text_blk, "text": text}]
        self._text_blk = ""
        return out

    def _seal_thinking(self, text=""):
        if not self._think_blk:
            return []
        out = [{"type": "thinking.done", "block": self._think_blk, "text": text}]
        self._think_blk = ""
        return out

    # -- entry point ---------------------------------------------------------
    def feed(self, raw):
        """One parsed JSON object in, a list of normalised events out."""
        if not isinstance(raw, dict):
            return [{"type": "raw", "payload": raw}]
        t = raw.get("type")

        if t == "system":
            return self._system(raw)
        if t == "stream_event":
            return self._stream(raw.get("event") or {})
        if t == "assistant":
            return self._assistant(raw.get("message") or {})
        if t == "user":
            # Our own message replayed back by --replay-user-messages. That is
            # how a steer is confirmed as *admitted* rather than merely
            # written, so it is a notice rather than nothing.
            return [{"type": "notice", "level": "info", "kind": "replay",
                     "text": _text_of((raw.get("message") or {}).get("content"))}]
        if t == "result":
            return self._result(raw)
        if t == "control_response":
            resp = raw.get("response") or {}
            if resp.get("subtype") == "success":
                return [{"type": "notice", "level": "info", "kind": "control",
                         "text": "interrupt acknowledged"}]
            return [{"type": "notice", "level": "warn", "kind": "control",
                     "text": json.dumps(resp)[:400]}]
        if t == "thinking":
            # cursor-agent's reasoning dialect: flat {type:"thinking",
            # subtype:"delta"|"completed"} rather than claude's nested
            # content_block_delta/thinking_delta. Same concept, different
            # shape — absorbing it here is the entire point of this module.
            sub = raw.get("subtype")
            if sub == "completed":
                return self._seal_thinking()
            text = raw.get("text") or ""
            if not self._think_blk:
                self._think_blk = self._next_block()
                return [{"type": "thinking.start", "block": self._think_blk},
                        {"type": "thinking.delta", "block": self._think_blk, "text": text}]
            return [{"type": "thinking.delta", "block": self._think_blk, "text": text}]

        if t == "rate_limit_event":
            # Worth surfacing rather than dumping as an unrecognised blob: it
            # is the difference between "the agent stopped" and "your quota
            # window is about to reset".
            info = raw.get("rate_limit_info") or {}
            status = info.get("status") or "unknown"
            return [{
                "type": "notice",
                "level": "warn" if status not in ("allowed",) else "info",
                "kind": "rate_limit",
                "status": status,
                "window": info.get("rateLimitType") or "",
                "resets_at": info.get("resetsAt") or 0,
                "using_overage": bool(info.get("isUsingOverage")),
                "text": "rate limit %s (%s window)" % (status, info.get("rateLimitType") or "?"),
            }]
        # cursor-agent's plain-text streaming lines arrive without a wrapper.
        if t is None and isinstance(raw.get("text"), str):
            return self._loose_text(raw["text"])
        return [{"type": "raw", "payload": raw}]

    # -- handlers ------------------------------------------------------------
    #: `system` subtypes that are transport bookkeeping, not conversation.
    #: Observed from claude 2.1.146: hook lifecycle, a periodic status ping and
    #: an end-of-turn summary. Rendering them put five "notice" rows in front
    #: of every reply, which is noise the reader can do nothing with — the
    #: information that matters (cost, tokens) already arrives on turn.end.
    #: They still reach the durable transcript; they just don't become items.
    #: Matched by exact name, plus any `hook_*` subtype — the hook lifecycle
    #: has grown new members between CLI versions (hook_progress appeared
    #: alongside hook_started/hook_response), and enumerating them one bug
    #: report at a time is the wrong shape for a list like this.
    QUIET_SYSTEM = frozenset({"status", "post_turn_summary"})

    def _system(self, raw):
        if raw.get("subtype") == "init":
            return [{
                "type": "session.init",
                "session_id": raw.get("session_id") or "",
                "model": raw.get("model") or "",
                "tools": raw.get("tools") or [],
                "cwd": raw.get("cwd") or "",
            }]
        subtype = raw.get("subtype") or "system"
        if subtype in self.QUIET_SYSTEM or subtype.startswith("hook_"):
            return []
        return [{"type": "notice", "level": "info", "kind": "system", "text": subtype}]

    def _stream(self, e):
        """Anthropic streaming events: block starts, deltas, stops."""
        et = e.get("type")

        if et == "content_block_start":
            blk = e.get("content_block") or {}
            kind = blk.get("type")
            bid = self._next_block()
            if kind == "text":
                self._text_blk = bid
                return [{"type": "text.start", "block": bid}]
            if kind == "thinking":
                self._think_blk = bid
                return [{"type": "thinking.start", "block": bid}]
            if kind == "tool_use":
                self._tools[e.get("index")] = {"block": bid, "id": blk.get("id") or "",
                                               "name": blk.get("name") or "tool", "buf": ""}
                return [{"type": "tool.pending", "block": bid,
                         "id": blk.get("id") or "", "name": blk.get("name") or "tool"}]
            return []

        if et == "content_block_delta":
            d = e.get("delta") or {}
            dt = d.get("type")
            if dt == "text_delta":
                self._had_output = True
                return [{"type": "text.delta", "block": self._text_blk or self._next_block(),
                         "text": d.get("text") or ""}]
            if dt == "thinking_delta":
                return [{"type": "thinking.delta", "block": self._think_blk or self._next_block(),
                         "text": d.get("thinking") or ""}]
            if dt == "input_json_delta":
                slot = self._tools.get(e.get("index"))
                if slot is not None:
                    slot["buf"] += d.get("partial_json") or ""
                    return [{"type": "tool.delta", "block": slot["block"],
                             "text": d.get("partial_json") or ""}]
            return []

        if et == "content_block_stop":
            slot = self._tools.pop(e.get("index"), None)
            if slot is not None:
                try:
                    args = json.loads(slot["buf"]) if slot["buf"].strip() else {}
                except json.JSONDecodeError:
                    args = {"_unparsed": slot["buf"][:2000]}
                return self._tool_start(slot["block"], slot["id"], slot["name"], args)
            if self._think_blk:
                return self._seal_thinking()
            if self._text_blk:
                return self._seal_text()
            return []

        if et == "message_delta":
            usage = (e.get("usage") or {})
            if usage:
                return [{"type": "usage",
                         "input_tokens": usage.get("input_tokens") or 0,
                         "output_tokens": usage.get("output_tokens") or 0}]
            return []
        return []

    def _tool_start(self, block, tid, name, args):
        self._had_output = True
        out = [{"type": "tool.start", "block": block, "id": tid, "name": name, "args": args}]
        # Two tools carry structured state the side panels render directly.
        low = (name or "").lower()
        if low in ("todowrite", "todo_write") and isinstance(args, dict):
            out.append({"type": "todo", "id": tid, "items": args.get("todos") or []})
        elif low in ("exitplanmode", "exit_plan_mode") and isinstance(args, dict):
            out.append({"type": "plan", "id": tid, "plan": args.get("plan") or ""})
        return out

    def _assistant(self, msg):
        """A complete assistant message. With --include-partial-messages the
        deltas already arrived, so this mostly seals blocks; without it, this
        is the only place content shows up."""
        out = []
        for b in (msg.get("content") or []):
            if not isinstance(b, dict):
                continue
            kind = b.get("type")
            if kind == "text":
                self._had_output = True
                blk = self._text_blk or self._next_block()
                if not self._text_blk:
                    out.append({"type": "text.start", "block": blk})
                    out.append({"type": "text.delta", "block": blk, "text": b.get("text") or ""})
                self._text_blk = blk
                out.extend(self._seal_text(b.get("text") or ""))
            elif kind == "thinking":
                blk = self._think_blk or self._next_block()
                if not self._think_blk:
                    out.append({"type": "thinking.start", "block": blk})
                self._think_blk = blk
                out.extend(self._seal_thinking(b.get("thinking") or ""))
            elif kind == "tool_use":
                out.extend(self._tool_start(self._next_block(), b.get("id") or "",
                                            b.get("name") or "tool", b.get("input") or {}))
            elif kind == "tool_result":
                out.append({
                    "type": "tool.result", "id": b.get("tool_use_id") or "",
                    "ok": not b.get("is_error"),
                    "content": _text_of(b.get("content"))[:8000],
                })
        return out

    def _loose_text(self, text):
        """A backend that streams bare text rather than block events."""
        self._had_output = True
        if not self._text_blk:
            self._text_blk = self._next_block()
            return [{"type": "text.start", "block": self._text_blk},
                    {"type": "text.delta", "block": self._text_blk, "text": text}]
        return [{"type": "text.delta", "block": self._text_blk, "text": text}]

    def _result(self, raw):
        out = self._seal_thinking() + self._seal_text()
        # A turn that produced no assistant content at all is a real outcome,
        # not a rendering gap — observed from cursor-agent, which sometimes
        # ends a resumed turn with thinking, no assistant message and an empty
        # result. Without this the UI shows a completed turn and no reply,
        # which reads as the console having lost the answer.
        if not self._had_output and not (raw.get("result") or "").strip():
            out.append({
                "type": "notice", "level": "warn", "kind": "empty_turn",
                "text": "The agent ended this turn without returning any text.",
            })
        self._had_output = False
        out.append({
            "type": "turn.end",
            "subtype": raw.get("subtype") or "",
            "is_error": bool(raw.get("is_error")),
            "cost_usd": raw.get("total_cost_usd") or 0.0,
            "duration_ms": raw.get("duration_ms") or 0,
            "num_turns": raw.get("num_turns") or 1,
            "input_tokens": ((raw.get("usage") or {}).get("input_tokens") or 0),
            "output_tokens": ((raw.get("usage") or {}).get("output_tokens") or 0),
            "result": (raw.get("result") or "")[:4000],
        })
        return out

    def reset_turn(self):
        """Drop any half-open block. Used after an interrupt, where the CLI
        stops mid-block and no stop event ever arrives."""
        out = self._seal_thinking() + self._seal_text()
        self._tools.clear()
        return out
