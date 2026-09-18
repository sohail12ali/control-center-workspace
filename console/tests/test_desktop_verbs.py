"""T-005: the desktop verbs, and the gate that decides who may approve them.

Two different things are tested here and they are worth keeping apart:

* the verbs exist, reach the bridge, and degrade honestly when no shell is
  running — the boring half;
* **a screenshot and a clipboard read can only be approved by someone at this
  machine.** That is the half worth reading. A parked approval answered from a
  phone would send the pixels of whatever happens to be on screen, or whatever
  a password manager last put on the clipboard, to a hosted model — and the
  person tapping cannot see either one.
"""

import json

import pytest

from server import agent_approvals, agent_backends, agent_tools, verbs
from server.paths import find_repo_root


@pytest.fixture
def root():
    """The REAL checkout. The question these tests ask is whether *this*
    workspace's shipped config gates a screenshot — not whether the mechanism
    could gate one in a fixture, which would pass while the real config was
    wide open. Nothing here writes: the desktop verbs only call the bridge."""
    return find_repo_root()


@pytest.fixture
def no_shell(monkeypatch):
    """Force "no shell running" whatever is actually on this machine.

    Without this the degrade tests would pass or fail depending on whether a
    desktop shell happened to be open, and `desktop-clipboard-write` would
    really replace the developer's clipboard mid-test.
    """
    from server import native_bridge
    monkeypatch.setattr(native_bridge, "_read_pointer", lambda _root: None)


DESKTOP_VERBS = (
    "desktop-windows",
    "desktop-monitors",
    "desktop-screenshot",
    "desktop-ocr",
    "desktop-clipboard-peek",
    "desktop-clipboard-read",
    "desktop-clipboard-write",
)


class TestRegistered:
    def test_every_desktop_verb_loads(self, root):
        registry = verbs.registry(root)
        for verb_id in DESKTOP_VERBS:
            assert verb_id in registry, verb_id

    def test_they_reach_a_model_as_tools(self, root):
        names = {d["function"]["name"] for d in agent_tools.tool_definitions(root)}
        for verb_id in DESKTOP_VERBS:
            assert agent_tools.verb_tool_name(verb_id) in names, verb_id

    def test_the_tool_name_uses_underscores(self, root):
        # The gate lists in agents.toml spell it this way, and a mismatch would
        # silently un-gate a screenshot.
        assert agent_tools.verb_tool_name("desktop-screenshot") == "console_desktop_screenshot"
        assert (agent_tools.verb_tool_name("desktop-clipboard-read")
                == "console_desktop_clipboard_read")

    def test_writing_the_clipboard_needs_confirm_but_reading_does_not(self, root):
        """`needs_confirm` guards against a HALLUCINATED call; the approval
        card guards against an unwanted one. A write is the first kind of
        problem, a read is the second — so they are guarded differently, and
        conflating them would either nag on every read or let a write slip."""
        registry = verbs.registry(root)
        assert registry["desktop-clipboard-write"].needs_confirm is True
        assert registry["desktop-clipboard-read"].needs_confirm is False


class TestDegradesHonestly:
    @pytest.mark.parametrize("verb_id", DESKTOP_VERBS)
    def test_with_no_shell_every_verb_says_so(self, root, no_shell, verb_id):
        # A tool that raises ends the turn; one that returns its reason lets
        # the model tell the user the shell is not running.
        confirm = verbs.registry(root)[verb_id].needs_confirm
        args = {"capture_id": "deadbeef"} if verb_id == "desktop-ocr" else None
        result = verbs.run(root, verb_id, confirm=confirm, args=args)
        assert result == {"ok": False, "reason": "shell not running"}

    def test_ocr_without_a_capture_id_says_which_capture(self, root, no_shell):
        # It never reaches the bridge: a model that forgot the argument needs
        # to be told what is missing, not that the shell is down.
        result = verbs.run(root, "desktop-ocr")
        assert result["ok"] is False
        assert "capture_id" in result["reason"]

    def test_ocr_is_not_gated(self, root):
        """The decision about these pixels was made when the CAPTURE was
        approved. Asking again to read text out of the same image trains
        people to click allow without reading."""
        for backend in agent_backends.registry(root).values():
            assert "console_desktop_ocr" not in set(backend.gated_tools)
            assert "mcp__console__desktop-ocr" not in set(backend.gated_tools)


class TestGateLists:
    """The gate is config, so these read the shipped config rather than a
    fixture — the question is whether THIS workspace is gated, not whether the
    mechanism can be."""

    def test_every_api_backend_gates_screenshot_and_clipboard_read(self, root):
        registry = agent_backends.registry(root)
        api_backends = [b for b in registry.values() if b.is_api]
        assert api_backends, "the fixture workspace should ship API backends"
        for backend in api_backends:
            gated = set(backend.gated_tools)
            assert "console_desktop_screenshot" in gated, backend.id
            assert "console_desktop_clipboard_read" in gated, backend.id

    def test_claude_gates_them_under_their_mcp_names(self, root):
        backend = agent_backends.get(root, "claude")
        gated = set(backend.gated_tools)
        # A CLI backend sees the same verbs through MCP, under a different
        # spelling. Gating one spelling and not the other would leave a hole
        # that depends only on which backend the chat happens to use.
        assert "mcp__console__desktop-screenshot" in gated
        assert "mcp__console__desktop-clipboard-read" in gated

    def test_the_hook_matcher_actually_matches_those_names(self, root):
        # The claude gate is a regex in a settings file. A name that does not
        # match compiles fine and gates nothing.
        import re
        backend = agent_backends.get(root, "claude")
        payload = agent_approvals.settings_payload("cmd", backend.gated_tools)
        matcher = payload["hooks"]["PreToolUse"][0]["matcher"]
        pattern = re.compile(matcher)
        assert pattern.match("mcp__console__desktop-screenshot")
        assert pattern.match("mcp__console__desktop-clipboard-read")
        assert pattern.match("Bash")
        assert not pattern.match("mcp__console__desktop-windows"), (
            "a window LIST is not sensitive and should not train people to "
            "click allow")

    def test_reading_the_window_list_is_not_gated(self, root):
        for backend in agent_backends.registry(root).values():
            gated = set(backend.gated_tools)
            assert "console_desktop_windows" not in gated
            assert "console_desktop_clipboard_peek" not in gated


class TestDeskOnlyApproval:
    """`LOCAL_ONLY` — the rules that make "someone at the machine" real."""

    def test_the_sensitive_tools_are_marked_desk_only(self):
        assert agent_approvals.local_only("console_desktop_screenshot")
        assert agent_approvals.local_only("console_desktop_clipboard_read")
        assert agent_approvals.local_only("mcp__console__desktop-screenshot")
        assert agent_approvals.local_only("mcp__console__desktop-clipboard-read")

    def test_ordinary_tools_are_not(self):
        for tool in ("run_command", "write_file", "console_desktop_windows",
                     "console_desktop_clipboard_write", "Bash"):
            assert not agent_approvals.local_only(tool), tool

    def _park(self, registry, tool):
        """Start a request on a worker thread and return its key."""
        import threading
        published = []
        done = threading.Event()
        out = {}

        def run():
            out["result"] = registry.request(
                "chat-1", tool, {}, "tu-1", published.append, timeout=5)
            done.set()

        threading.Thread(target=run, daemon=True).start()
        for _ in range(200):
            if published:
                break
            import time
            time.sleep(0.01)
        assert published, "the request should have published a card"
        return published[0]["key"], out, done

    def test_telegram_cannot_approve_a_screenshot(self):
        registry = agent_approvals.Approvals()
        key, out, done = self._park(registry, "console_desktop_screenshot")
        with pytest.raises(ValueError, match="only be approved from the console"):
            registry.decide(key, "allow", by="telegram:sohail")
        # Still pending, so a human at the desk can still answer it.
        registry.decide(key, "allow", by="console")
        done.wait(2)
        assert out["result"][0] == "allow"

    def test_telegram_may_still_deny_it(self):
        """Refusing to let someone STOP something would be a strange reading
        of "this needs a human here"."""
        registry = agent_approvals.Approvals()
        key, out, done = self._park(registry, "console_desktop_clipboard_read")
        registry.decide(key, "deny", by="telegram:sohail")
        done.wait(2)
        assert out["result"][0] == "deny"

    def test_allow_for_this_chat_is_downgraded_to_one_allow(self):
        registry = agent_approvals.Approvals()
        key, out, done = self._park(registry, "console_desktop_screenshot")
        registry.decide(key, "allow-session", by="console")
        done.wait(2)
        assert out["result"][0] == "allow"

        # The next call must ask again: each screen is its own decision.
        key2, out2, done2 = self._park(registry, "console_desktop_screenshot")
        assert key2 != key, "a second card was raised rather than auto-allowed"
        registry.decide(key2, "deny", by="console")
        done2.wait(2)

    def test_an_ordinary_tool_still_gets_allow_for_this_chat(self):
        # The downgrade must be specific to the desk-only set, or approving
        # `run_command` once for a chat would stop working.
        registry = agent_approvals.Approvals()
        key, out, done = self._park(registry, "run_command")
        registry.decide(key, "allow-session", by="console")
        done.wait(2)
        assert out["result"][0] == "allow"

        decision, reason = registry.request(
            "chat-1", "run_command", {}, "tu-2", lambda _e: None, timeout=1)
        assert decision == "allow"
        assert "allowed for this chat" in reason


class TestScreenshotArguments:
    def test_a_region_is_assembled_from_flat_arguments(self, root, monkeypatch):
        """A model passes flat arguments; the bridge wants a rectangle. The
        translation is the verb's job, and getting it wrong would silently
        capture the wrong part of the screen."""
        seen = {}

        def fake_capture(root, **kwargs):
            seen.update(kwargs)
            return {"ok": True}

        from server import verb_handlers
        monkeypatch.setattr(verb_handlers.native_bridge, "capture", fake_capture)
        verbs.run(root, "desktop-screenshot", args={
            "target": "region", "x": 10, "y": 20, "width": 30, "height": 40})
        assert seen["region"] == {"x": 10, "y": 20, "width": 30, "height": 40}
        assert seen["target"] == "region"

    def test_a_non_region_target_sends_no_rectangle(self, root, monkeypatch):
        seen = {}

        def fake_capture(root, **kwargs):
            seen.update(kwargs)
            return {"ok": True}

        from server import verb_handlers
        monkeypatch.setattr(verb_handlers.native_bridge, "capture", fake_capture)
        verbs.run(root, "desktop-screenshot",
                  args={"target": "window", "window_title": "Notepad"})
        assert seen["region"] is None
        assert seen["window_title"] == "Notepad"

    def test_an_unknown_argument_is_refused_by_name(self, root):
        # The handlers declare their real parameters precisely so a typo fails
        # loudly instead of being dropped into a default capture.
        with pytest.raises(Exception):
            verbs.run(root, "desktop-screenshot", args={"windwo_title": "x"})
