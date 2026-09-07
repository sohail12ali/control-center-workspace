"""The native-bridge client: how the console talks to the desktop shell.

Fake-opener idiom matching `test_api_session.py` and `agent_backends._probe`'s
own tests: no network, a callable stands in for `urllib.request.urlopen`.

The contract these tests pin is T-005's, and it differs from the T-004 stub's
on purpose — the stub existed so the fast-command table could be finished
against something honest before the shell could answer at all. What has NOT
changed is the property that mattered then and matters more now: **nothing
here raises into a turn**. A tool that throws ends the turn; a tool that
returns its reason lets the model say what went wrong.
"""

import io
import json
import os

import pytest

from server import native_bridge


class Bridge:
    """A fake opener that behaves like the real shell: JSON bytes, an `ok`
    flag, and a record of what it was asked so a test can assert on headers
    and bodies."""

    def __init__(self, payloads=None, caps=None):
        self.payloads = payloads or {}
        self.caps = caps if caps is not None else {"capture": True, "ocr": False}
        self.calls = []

    def __call__(self, request, timeout=None):
        endpoint = request.full_url.split("127.0.0.1:1234", 1)[-1] or request.full_url
        body = request.data.decode("utf-8") if request.data else None
        self.calls.append({
            "endpoint": endpoint,
            "method": request.get_method(),
            "auth": request.headers.get("Authorization"),
            "body": json.loads(body) if body else None,
            "timeout": timeout,
        })
        if endpoint == "/health":
            payload = {"ok": True, "version": "0.1.0", "pid": 1, "caps": self.caps}
        else:
            payload = dict(self.payloads.get(endpoint, {"ok": True}))
            payload.setdefault("ok", True)
        return io.BytesIO(json.dumps(payload).encode("utf-8"))


class Refusing:
    """Nothing listening on that port."""

    def __call__(self, request, timeout=None):
        raise ConnectionRefusedError("nope")


class Erroring:
    """A bridge that answers with a 4xx and a reason in the body — the shape
    the real one uses for a bad request."""

    def __init__(self, status=400, message="a window capture needs window_title"):
        self.status = status
        self.message = message

    def __call__(self, request, timeout=None):
        import urllib.error
        body = json.dumps({"ok": False, "error": "bad_request",
                           "message": self.message}).encode("utf-8")
        raise urllib.error.HTTPError(
            request.full_url, self.status, "Bad Request", {},
            io.BytesIO(body))


@pytest.fixture
def repo(tmp_path):
    return str(tmp_path)


def _write_pointer(repo, base_url="http://127.0.0.1:1234", token="secret-token"):
    path = os.path.join(repo, "console", ".cache", "desktop", "bridge.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = {"base_url": base_url, "pid": 4242, "started": 0}
    if token is not None:
        record["token"] = token
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    return path


class TestAvailability:
    def test_no_pointer_file_is_honestly_unavailable(self, repo):
        ok, reason = native_bridge.available(repo)
        assert ok is False
        assert reason == "shell not running"

    def test_a_pointer_with_no_base_url_is_still_unavailable(self, repo):
        path = _write_pointer(repo)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"token": "x"}, fh)
        ok, _reason = native_bridge.available(repo)
        assert ok is False

    def test_a_corrupt_pointer_file_is_treated_as_absent(self, repo):
        path = _write_pointer(repo)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        ok, reason = native_bridge.available(repo)
        assert (ok, reason) == (False, "shell not running")

    def test_a_pointer_that_answers_is_available(self, repo):
        _write_pointer(repo)
        ok, reason = native_bridge.available(repo, opener=Bridge())
        assert (ok, reason) == (True, "")

    def test_a_stale_pointer_reads_the_same_as_no_pointer(self, repo):
        """A shell that died leaves its pointer behind. "Shell not running" is
        the truth either way, and a different message would send someone
        hunting for a port problem that is not there."""
        _write_pointer(repo)
        ok, reason = native_bridge.available(repo, opener=Refusing())
        assert (ok, reason) == (False, "shell not running")

    def test_availability_never_raises(self, repo):
        _write_pointer(repo)
        native_bridge.available(repo, opener=Refusing())


class TestAuth:
    def test_the_token_is_sent_as_a_bearer_header(self, repo):
        _write_pointer(repo, token="secret-token")
        bridge = Bridge()
        native_bridge.list_windows(repo, opener=bridge)
        assert bridge.calls[-1]["auth"] == "Bearer secret-token"

    def test_a_pointer_without_a_token_still_calls(self, repo):
        """An older or hand-written pointer has no token. The bridge will
        refuse it, and that refusal is the bridge's to make — the client does
        not invent a token or refuse locally."""
        _write_pointer(repo, token=None)
        bridge = Bridge()
        native_bridge.list_windows(repo, opener=bridge)
        assert bridge.calls[-1]["auth"] is None


class TestHelpersDegradeHonestly:
    @pytest.mark.parametrize("call", [
        lambda repo: native_bridge.state(repo),
        lambda repo: native_bridge.list_windows(repo),
        lambda repo: native_bridge.list_monitors(repo),
        lambda repo: native_bridge.capture(repo),
        lambda repo: native_bridge.clipboard_peek(repo),
        lambda repo: native_bridge.clipboard_read(repo),
        lambda repo: native_bridge.clipboard_write(repo, "x"),
    ])
    def test_every_helper_reports_unavailable_with_no_shell(self, repo, call):
        result = call(repo)
        assert result == {"ok": False, "reason": "shell not running"}

    def test_capabilities_reports_unavailable_with_no_shell(self, repo):
        assert native_bridge.capabilities(repo)["ok"] is False

    def test_a_bad_request_surfaces_the_bridge_s_own_message(self, repo):
        # The model reads this text and fixes its next call, so the reason has
        # to be the bridge's, not "HTTP 400".
        _write_pointer(repo)
        result = native_bridge.capture(repo, target="window", opener=Erroring())
        assert result["ok"] is False
        assert "window_title" in result["reason"]

    def test_a_transport_failure_reads_as_shell_not_running(self, repo):
        class FlakyAfterHealth:
            def __init__(self):
                self.seen = 0

            def __call__(self, request, timeout=None):
                self.seen += 1
                if request.full_url.endswith("/health"):
                    return io.BytesIO(json.dumps({"ok": True, "caps": {}}).encode())
                raise TimeoutError("slow")

        _write_pointer(repo)
        result = native_bridge.clipboard_read(repo, opener=FlakyAfterHealth())
        assert result["ok"] is False
        # A transport failure reads as "shell not running", the same as a
        # missing pointer: the shell is not answering either way, and two
        # different messages for one condition sends the reader hunting.
        assert result["reason"] == "shell not running"

    def test_a_non_json_answer_is_reported_not_raised(self, repo):
        class Garbage:
            def __call__(self, request, timeout=None):
                return io.BytesIO(b"<html>nope</html>")

        _write_pointer(repo)
        result = native_bridge.list_windows(repo, opener=Garbage())
        assert result["ok"] is False
        assert "not JSON" in result["reason"]


class TestCalls:
    def test_capture_defaults_to_the_screen(self, repo):
        _write_pointer(repo)
        bridge = Bridge({"/capture": {"capture": {"path": "x.png"}}})
        native_bridge.capture(repo, opener=bridge)
        call = bridge.calls[-1]
        assert call["endpoint"] == "/capture"
        assert call["method"] == "POST"
        assert call["body"] == {"target": "screen"}

    def test_a_window_capture_names_the_window(self, repo):
        _write_pointer(repo)
        bridge = Bridge()
        native_bridge.capture(repo, target="window", window_title="Notepad",
                              max_side=800, opener=bridge)
        assert bridge.calls[-1]["body"] == {
            "target": "window", "window_title": "Notepad", "max_side": 800}

    def test_a_region_capture_sends_the_rectangle(self, repo):
        _write_pointer(repo)
        bridge = Bridge()
        native_bridge.capture(repo, target="region",
                              region={"x": 1, "y": 2, "width": 3, "height": 4},
                              opener=bridge)
        body = bridge.calls[-1]["body"]
        assert body == {"target": "region", "x": 1, "y": 2, "width": 3, "height": 4}

    def test_a_capture_gets_the_long_timeout(self, repo):
        """A screen grab plus a PNG encode is not a 5-second operation on a
        4K display, and a timeout that fires mid-capture looks to the model
        like the shell is broken."""
        _write_pointer(repo)
        bridge = Bridge()
        native_bridge.capture(repo, opener=bridge)
        assert bridge.calls[-1]["timeout"] == native_bridge.LONG_TIMEOUT
        native_bridge.clipboard_peek(repo, opener=bridge)
        assert bridge.calls[-1]["timeout"] == native_bridge.DEFAULT_TIMEOUT

    def test_clipboard_write_sends_the_text(self, repo):
        _write_pointer(repo)
        bridge = Bridge({"/clipboard/write": {"chars": 5}})
        result = native_bridge.clipboard_write(repo, "hello", opener=bridge)
        assert bridge.calls[-1]["body"] == {"text": "hello"}
        assert result["chars"] == 5

    def test_clipboard_write_of_none_sends_an_empty_string(self, repo):
        _write_pointer(repo)
        bridge = Bridge()
        native_bridge.clipboard_write(repo, None, opener=bridge)
        assert bridge.calls[-1]["body"] == {"text": ""}

    def test_peek_is_a_get_and_read_is_a_post(self, repo):
        # Read is a POST because it has a side effect worth logging as one:
        # a human approved it. Peek is metadata and carries no approval.
        _write_pointer(repo)
        bridge = Bridge()
        native_bridge.clipboard_peek(repo, opener=bridge)
        assert bridge.calls[-1]["method"] == "GET"
        native_bridge.clipboard_read(repo, opener=bridge)
        assert bridge.calls[-1]["method"] == "POST"

    def test_capabilities_returns_what_the_shell_admits_to(self, repo):
        # The shell reports a capability as false when the ROUTE is missing,
        # not when the platform lacks it, so the console can tell a model
        # "this build has no OCR" instead of letting it call and fail.
        _write_pointer(repo)
        bridge = Bridge(caps={"capture": True, "ocr": False, "speak": False})
        result = native_bridge.capabilities(repo, opener=bridge)
        assert result["ok"] is True
        assert result["caps"]["ocr"] is False
        assert result["caps"]["capture"] is True
