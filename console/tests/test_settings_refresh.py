"""T-031 task 15: the console's nudge to the shell after a settings write.

The shell caches the merged settings for 30 seconds, so without a nudge every
"(live)" claim is false for up to that long (D-7). The contract tested here is
the console half only: the helper, and a settings write that stays a success
whatever the nudge does. The shell's `/settings/refresh` route is Rust and is
tested there; nothing here talks to a real shell and no socket is opened.
"""

import io
import json
import os
import urllib.error
import urllib.request

import pytest

from server import assistant_config, native_bridge
from server.features import assistant_feature


class Shell:
    """A fake opener standing in for the shell's bridge. Records every request."""

    def __init__(self, reply=None):
        self.reply = {"ok": True, "applying": True} if reply is None else reply
        self.calls = []

    def __call__(self, request, timeout=None):
        body = request.data.decode("utf-8") if request.data else None
        self.calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "auth": request.headers.get("Authorization"),
            "body": json.loads(body) if body else None,
            "timeout": timeout,
        })
        return io.BytesIO(json.dumps(self.reply).encode("utf-8"))


class Unreachable:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def __call__(self, request, timeout=None):
        self.calls += 1
        raise self.exc


def _write_pointer(repo, token="secret-token"):
    path = os.path.join(repo, "console", ".cache", "desktop", "bridge.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"base_url": "http://127.0.0.1:1234", "token": token,
                   "pid": 4242, "started": 0}, fh)


def _no_network(monkeypatch):
    """Any real socket attempt from here is a test failure, not a slow test."""
    def boom(*a, **kw):
        raise AssertionError("a real network call was attempted")
    monkeypatch.setattr(urllib.request, "urlopen", boom)


class _Req:
    def __init__(self, body=None):
        self.body = body or {}
        self.query = {}
        self.client_addr = ""
        self.user_agent = ""


@pytest.fixture
def settings_post(repo, monkeypatch):
    # Backends are looked up by `shutil.which` only (the conftest rows are
    # CLIs), so nothing here touches a network.
    from server import agent_backends
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    return assistant_feature.handlers(repo)["assistant.settings_post"]


class Spy:
    """Stands in for `native_bridge.settings_refresh`; records each call and
    what the stored settings said at that moment."""

    def __init__(self, repo, result=None, raises=None):
        self.repo = repo
        self.result = {"ok": True} if result is None else result
        self.raises = raises
        self.calls = []
        self.seen_at_call = []

    def __call__(self, repo_root, opener=None):
        self.calls.append(repo_root)
        self.seen_at_call.append(assistant_config.settings(self.repo)["reply_chars"])
        if self.raises is not None:
            raise self.raises
        return self.result


class TestTheHelper:
    def test_it_posts_to_settings_refresh_with_the_bearer_token_and_a_short_timeout(self, repo):
        _write_pointer(repo)
        shell = Shell()
        answer = native_bridge.settings_refresh(repo, opener=shell)
        assert answer["ok"] is True
        (call,) = shell.calls
        assert call["url"] == "http://127.0.0.1:1234/settings/refresh"
        assert call["method"] == "POST"
        assert call["auth"] == "Bearer secret-token"
        assert call["timeout"] is not None and call["timeout"] <= 1.0
        assert native_bridge.REFRESH_TIMEOUT <= 1.0

    def test_it_returns_the_shells_own_answer(self, repo):
        _write_pointer(repo)
        answer = native_bridge.settings_refresh(
            repo, opener=Shell({"ok": True, "applying": True}))
        assert answer == {"ok": True, "applying": True}

    def test_no_pointer_is_not_running_and_no_connection_is_made(self, repo, monkeypatch):
        _no_network(monkeypatch)
        refusing = Unreachable(AssertionError("must not be called"))
        assert native_bridge.settings_refresh(repo, opener=refusing) == {
            "ok": False, "reason": "shell not running"}
        assert native_bridge.settings_refresh(repo) == {
            "ok": False, "reason": "shell not running"}
        assert refusing.calls == 0

    @pytest.mark.parametrize("exc", [
        ConnectionRefusedError("nope"), TimeoutError("timed out"),
        OSError("half-open socket")])
    def test_an_unreachable_or_slow_shell_reads_as_not_running_and_never_raises(self, repo, exc):
        _write_pointer(repo)
        answer = native_bridge.settings_refresh(repo, opener=Unreachable(exc))
        assert answer == {"ok": False, "reason": "shell not running"}

    def test_a_shell_without_the_route_reports_its_own_reason(self, repo):
        _write_pointer(repo)

        def old_shell(request, timeout=None):
            body = json.dumps({"ok": False, "error": "not_found",
                               "message": "no such route"}).encode("utf-8")
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {},
                                         io.BytesIO(body))
        answer = native_bridge.settings_refresh(repo, opener=old_shell)
        assert answer == {"ok": False, "reason": "no such route"}


class TestSettingsPost:
    def test_an_accepted_write_nudges_the_shell_exactly_once(self, repo, settings_post, monkeypatch):
        spy = Spy(repo)
        monkeypatch.setattr(native_bridge, "settings_refresh", spy)
        answer = settings_post(_Req({"reply_chars": 120}))
        assert answer["settings"]["reply_chars"] == 120
        assert spy.calls == [repo]

    def test_the_new_value_is_already_stored_when_the_shell_is_nudged(self, repo, settings_post, monkeypatch):
        # The shell re-reads on the nudge, so a nudge sent before the write
        # landed would make it re-apply the OLD value.
        spy = Spy(repo)
        monkeypatch.setattr(native_bridge, "settings_refresh", spy)
        settings_post(_Req({"reply_chars": 333}))
        assert spy.seen_at_call == [333]

    @pytest.mark.parametrize("body", [
        {"not_a_setting": 1},
        {"reply_chars": 0},
        {"input_device": "a\x00b"},
        {"backend": "not-a-backend"},
        {},
    ])
    def test_a_rejected_write_nudges_nothing(self, repo, settings_post, monkeypatch, body):
        spy = Spy(repo)
        monkeypatch.setattr(native_bridge, "settings_refresh", spy)
        with pytest.raises(ValueError):
            settings_post(_Req(body))
        assert spy.calls == []

    @pytest.mark.parametrize("make", [
        lambda repo: Spy(repo, raises=RuntimeError("the helper blew up")),
        lambda repo: Spy(repo, raises=TimeoutError("slow shell")),
        lambda repo: Spy(repo, result={"ok": False, "reason": "shell not running"}),
        lambda repo: Spy(repo, result={"ok": False, "reason": "no such route"}),
    ], ids=["raises", "times-out", "not-running", "refused"])
    def test_a_failing_nudge_still_returns_the_merged_settings(self, repo, settings_post, monkeypatch, make):
        spy = make(repo)
        monkeypatch.setattr(native_bridge, "settings_refresh", spy)
        answer = settings_post(_Req({"reply_chars": 150}))
        assert answer["settings"]["reply_chars"] == 150
        assert len(spy.calls) == 1
        # And the write really happened.
        assert assistant_config.settings(repo)["reply_chars"] == 150

    def test_with_a_real_pointer_and_a_dead_shell_the_write_still_succeeds(self, repo, settings_post, monkeypatch):
        # Not a spy: the real helper, the real pointer file, a socket that
        # times out. Proves the wiring and the 1 s cap end to end.
        _write_pointer(repo)
        seen = []

        def hung(request, timeout=None):
            seen.append((request.full_url, timeout))
            raise TimeoutError("timed out")
        monkeypatch.setattr(urllib.request, "urlopen", hung)
        answer = settings_post(_Req({"reply_chars": 175}))
        assert answer["settings"]["reply_chars"] == 175
        assert seen == [("http://127.0.0.1:1234/settings/refresh",
                         native_bridge.REFRESH_TIMEOUT)]
        assert seen[0][1] <= 1.0

    def test_with_no_shell_at_all_no_socket_is_opened(self, repo, settings_post, monkeypatch):
        _no_network(monkeypatch)
        answer = settings_post(_Req({"reply_chars": 90}))
        assert answer["settings"]["reply_chars"] == 90

    def test_the_cli_path_still_works_and_nudges_once(self, repo, monkeypatch):
        from server import agent_backends
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        spy = Spy(repo)
        monkeypatch.setattr(native_bridge, "settings_refresh", spy)
        answer = assistant_feature.call(
            repo, "assistant.settings_post", {"reply_chars": 210})
        assert answer["settings"]["reply_chars"] == 210
        assert len(spy.calls) == 1

    def test_the_cli_path_without_a_shell_is_a_plain_success(self, repo, monkeypatch):
        from server import agent_backends
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        _no_network(monkeypatch)
        answer = assistant_feature.call(
            repo, "assistant.settings_post", {"input_device": "Headset"})
        assert answer["settings"]["input_device"] == "Headset"
