"""Ask a human before a gated tool runs.

The Claude CLI has no way to show its own permission prompt in a headless
stream-json session, so the only supported seam is a **PreToolUse hook**: a
command the CLI runs before the tool, whose JSON verdict it obeys. The hook
blocks for as long as it likes, and its ``permissionDecision: "deny"`` becomes
the tool's result. That gives the shape here:

    CLI  --spawns-->  hooks/pretooluse.py  --POST-->  console  --SSE-->  browser
                              ^                                            |
                              +---------- verdict <----- POST -------------+

The hook process, the parked HTTP thread, and the agent's tool call all block
together on one ``threading.Event`` per question; the browser's answer (or the
timeout) releases all three. Every failure mode is fail-closed: no live
session, unreachable console, malformed payload, or silence all become a deny
with a reason the agent can read.

Which tools are gated is config, not code — ``gated_tools`` on the backend row
in ``console/config/agents.toml``. An empty list means no settings file is
written and the CLI runs exactly as before this module existed.
"""

import json
import os
import sys
import threading
import uuid

DEFAULT_TIMEOUT = 300  # seconds a question may wait before it is denied

HOOK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "hooks", "pretooluse.py")


class Pending:
    __slots__ = ("key", "chat", "tool", "tool_input", "tool_use_id",
                 "event", "decision", "reason", "by")

    def __init__(self, key, chat, tool, tool_input, tool_use_id):
        self.key = key
        self.chat = chat
        self.tool = tool
        self.tool_input = tool_input
        self.tool_use_id = tool_use_id
        self.event = threading.Event()
        self.decision = ""
        self.reason = ""
        self.by = ""


#: Tools that may only ever be approved by someone sitting at this machine.
#:
#: Two rules apply to every name here, and both exist because the person
#: answering cannot see what they are agreeing to from a phone:
#:
#:   * a Telegram tap is refused - a parked approval that ships a screenshot of
#:     a bank app to a chat is a different product from the one this is;
#:   * "allow for this chat" is downgraded to a single allow - the whole point
#:     is that each screen, and each clipboard, is a fresh decision.
#:
#: Names are matched exactly, and both the `console_*` (API-backend) and
#: `mcp__console__*` (CLI-backend) spellings are listed, because the same verb
#: reaches a model under two names depending on transport.
LOCAL_ONLY = frozenset({
    "console_desktop_screenshot",
    "console_desktop_clipboard_read",
    "mcp__console__desktop-screenshot",
    "mcp__console__desktop-clipboard-read",
})


def local_only(tool):
    """Is `tool` desk-only? Kept a function so callers do not each re-derive
    the membership test (and so a future prefix rule lands in one place)."""
    return tool in LOCAL_ONLY


class Approvals:
    """Registry of questions in flight. One per server process."""

    def __init__(self):
        self._pending = {}
        self._session_allow = {}  # chat id -> set of tool names allowed for it
        self._lock = threading.Lock()

    def request(self, chat, tool, tool_input, tool_use_id, publish,
                timeout=DEFAULT_TIMEOUT, repo_root=None, title=""):
        """Park the calling thread until a human answers or the timeout hits.

        Returns ``(decision, reason)`` where decision is ``allow`` or ``deny``.

        ``repo_root`` enables the preview — a diff for a file write, the command
        for a shell call. Optional so a caller without one still works, but
        passing it is what turns this from a yes/no prompt into a review: a card
        showing escaped JSON gets approved unread, which is a speed bump with a
        log rather than a gate.
        """
        with self._lock:
            # Desk-only tools deliberately skip this: even if something had
            # recorded a session allow for one, each screen and each clipboard
            # is its own decision.
            if not local_only(tool) and tool in self._session_allow.get(chat, ()):
                return "allow", "%s was allowed for this chat" % tool

        key = uuid.uuid4().hex[:12]
        p = Pending(key, chat, tool, tool_input, tool_use_id)
        with self._lock:
            self._pending[key] = p

        preview = None
        if repo_root:
            try:
                from . import tool_preview
                preview = tool_preview.build(repo_root, tool, tool_input)
            except Exception:  # noqa: BLE001
                # A preview is a convenience. Failing to build one must never
                # stop the question being asked, or a gated tool would run
                # unreviewed because the diff crashed.
                preview = None

        publish({"type": "approval.request", "key": key, "tool": tool,
                 "input": tool_input, "tool_use_id": tool_use_id,
                 "preview": preview, "timeout": timeout})

        # Reach a phone. Without this a run started from anywhere but this
        # desk stalls here and dies on the timeout with nothing said about it.
        # Best-effort and off the calling thread: a notification that cannot
        # be delivered must never delay or fail the run it describes.
        if repo_root:
            try:
                from . import notify
                # Buttons, so the answer can happen where the notification
                # arrived. Without them the message says a run is blocked and
                # leaves you to find a browser — which on a phone means the
                # run dies on this same timeout regardless.
                # A desk-only tool still gets a notification - a run that
                # stalls in silence is worse than one you cannot answer
                # remotely - but no buttons, because tapping one would be
                # approving something you cannot see.
                buttons = None if local_only(tool) else notify.approval_buttons(key)
                message = notify.approval_message(tool, tool_input, preview,
                                                  timeout, chat_title=title)
                if buttons is None:
                    message += ("\n\nAnswer this one in the console - it needs "
                                "someone at the machine.")
                notify.send(repo_root, "approval", message, buttons=buttons)
            except Exception:  # noqa: BLE001
                pass

        answered = p.event.wait(timeout=timeout)
        with self._lock:
            self._pending.pop(key, None)

        if not answered:
            publish({"type": "approval.decided", "key": key, "tool": tool,
                     "decision": "deny", "by": "timeout"})
            return "deny", (
                "No one answered within %ds, so the console denied this %s "
                "call. Nothing was run. Ask again if it is still needed."
                % (timeout, tool))
        if p.decision == "deny":
            return "deny", p.reason or "A human denied this %s call." % tool
        return "allow", p.reason or ""

    def decide(self, key, decision, by="", reason=""):
        """Answer a pending question: ``allow``, ``allow-session`` or ``deny``.

        A desk-only tool (see ``LOCAL_ONLY``) refuses a remote answer outright
        and never records a session allow. A DENY is always accepted, from
        anywhere: refusing to let someone stop something would be a strange
        reading of "this needs a human here".
        """
        if decision not in ("allow", "allow-session", "deny"):
            raise ValueError("unknown decision %r" % decision)
        with self._lock:
            p = self._pending.get(key)
            if p is None:
                raise ValueError(
                    "that approval is no longer pending — it may have timed "
                    "out or already been answered")
            if local_only(p.tool) and decision != "deny":
                if by.startswith("telegram:"):
                    raise ValueError(
                        "%s can only be approved from the console, by someone "
                        "who can see what is on the screen" % p.tool)
                # Allow, but only this once.
                decision = "allow"
            if decision == "allow-session":
                self._session_allow.setdefault(p.chat, set()).add(p.tool)
            p.decision = "allow" if decision.startswith("allow") else "deny"
            p.reason = reason
            p.by = by
        p.event.set()
        return p

    def forget(self, chat):
        """Deny everything a chat still has in flight, so its hook processes
        are not left blocked when the session ends."""
        with self._lock:
            stale = [p for p in self._pending.values() if p.chat == chat]
            self._session_allow.pop(chat, None)
        for p in stale:
            p.decision = "deny"
            p.reason = "the session ended before this was answered"
            p.event.set()


REGISTRY = Approvals()


def settings_payload(hook_cmd, gated, timeout=DEFAULT_TIMEOUT):
    """The ``--settings`` JSON that installs the gate for one session."""
    return {
        "hooks": {
            "PreToolUse": [{
                "matcher": "^(" + "|".join(gated) + ")$",
                "hooks": [{"type": "command", "command": hook_cmd,
                           "timeout": timeout + 30}],
            }],
        },
    }


def write_settings(chats_dir, sid, gated, port, timeout=DEFAULT_TIMEOUT):
    """Write ``{sid}.settings.json`` next to the transcript; returns its path.

    The hook command re-runs this exact interpreter so nothing about PATH is
    assumed, and both paths are quoted because the CLI runs the command
    through a shell.
    """
    hook_cmd = '"%s" "%s" --chat %s --port %d' % (
        sys.executable, HOOK_SCRIPT, sid, int(port))
    path = os.path.join(chats_dir, sid + ".settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings_payload(hook_cmd, gated, timeout), f, indent=2)
    return path
