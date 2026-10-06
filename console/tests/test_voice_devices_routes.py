"""T-031 task 25: the console side of devices, tests and preview (AC-46, AC-50,
AC-62, AC-65; BR-6, D-17).

Every test runs against a FAKE shell: `urllib.request.urlopen` is replaced by a
recording callable, and the bridge pointer lives in the temp workspace. The real
shell and the real `console/.cache/desktop/bridge.json` are never touched.
"""

import io
import json
import os
import urllib.error
import urllib.request

import pytest

from server import assistant_config, voice_assets
from server.features import assistant_feature


class Req:
    def __init__(self, body=None):
        self.body = body if body is not None else {}
        self.query = {}
        self.client_addr = "10.0.0.5"
        self.user_agent = "pytest"


DEVICES = {
    "ok": True,
    "inputs": ["Mic A", "Mic B"], "outputs": ["Spk A"],
    "default_input": "Mic A", "default_output": "Spk A",
    "input": {"configured": "Mic B", "resolved": "Mic B", "match": "exact",
              "fallback": False, "candidates": []},
    "output": {"configured": "Gone", "resolved": "Spk A", "match": "none",
               "fallback": True, "candidates": ["Spk A"]},
}


class FakeShell:
    """Answers like the real bridge, including a 4xx with the reason in the body."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    def __call__(self, request, timeout=None):
        endpoint = "/" + request.full_url.split("127.0.0.1:1234/", 1)[-1]
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        self.calls.append({"endpoint": endpoint, "method": request.get_method(),
                           "body": body, "timeout": timeout})
        if endpoint == "/health":
            return io.BytesIO(b'{"ok": true, "caps": {}}')
        status, payload = self.routes.get(endpoint, (200, {"ok": True}))
        raw = json.dumps(payload).encode("utf-8")
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "err", {},
                                         io.BytesIO(raw))
        return io.BytesIO(raw)

    def to(self, endpoint):
        return [c for c in self.calls if c["endpoint"] == endpoint]


def _pointer(repo):
    path = os.path.join(repo, "console", ".cache", "desktop", "bridge.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"base_url": "http://127.0.0.1:1234", "token": "t", "pid": 1}, fh)


@pytest.fixture
def shell(repo, monkeypatch):
    _pointer(repo)
    fake = FakeShell({"/audio/devices": (200, DEVICES)})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake


@pytest.fixture
def routes(repo):
    return assistant_feature.handlers(repo)


def _voices(repo, *names):
    tts = os.path.join(repo, "desktop", "tts")
    os.makedirs(tts, exist_ok=True)
    for n in names:
        with open(os.path.join(tts, n + ".onnx"), "wb") as fh:
            fh.write(b"x")


def _overrides_bytes(repo):
    path = os.path.join(repo, assistant_config.OVERRIDE_REL)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


class TestDevices:
    def test_returns_the_shell_shape_and_adds_configured(self, repo, shell, routes):
        assistant_config.update(repo, {"input_device": "Mic B", "output_device": "Gone"})
        out = routes["assistant.voice_devices"](Req())
        assert out["ok"] is True
        for key in ("inputs", "outputs", "default_input", "default_output"):
            assert out[key] == DEVICES[key]
        assert out["configured"] == {"input": "Mic B", "output": "Gone"}

    def test_verdict_fields_come_from_the_shell_untouched(self, repo, shell, routes):
        # The console's configured value differs from the shell's applied one;
        # the verdict must be the shell's, not recomputed (BR-6, D-17).
        assistant_config.update(repo, {"input_device": "Totally Else"})
        out = routes["assistant.voice_devices"](Req())
        assert out["input"] == DEVICES["input"]
        assert out["output"]["fallback"] is True
        assert out["output"]["match"] == "none"
        assert out["output"]["candidates"] == ["Spk A"]
        assert out["configured"]["input"] == "Totally Else"

    def test_asks_the_shell_with_a_short_timeout(self, repo, shell, routes):
        routes["assistant.voice_devices"](Req())
        assert shell.to("/audio/devices")[0]["timeout"] == 2.0

    def test_shell_down_is_ok_false_with_a_reason(self, repo, routes):
        # No pointer file: nothing to call.
        out = routes["assistant.voice_devices"](Req())
        assert out == {"ok": False, "reason": "shell not running"}

    def test_a_refusing_shell_is_ok_false_not_an_exception(self, repo, monkeypatch, routes):
        _pointer(repo)

        def refuse(request, timeout=None):
            raise ConnectionRefusedError("nope")
        monkeypatch.setattr(urllib.request, "urlopen", refuse)
        out = routes["assistant.voice_devices"](Req())
        assert out["ok"] is False and out["reason"]


class TestMicAndSpeakerTests:
    def test_mic_test_forwards_and_returns_at_once(self, repo, shell, routes):
        shell.routes["/audio/test/mic"] = (200, {"ok": True, "started": True})
        out = routes["assistant.voice_test_mic"](Req())
        assert out["started"] is True
        assert shell.to("/audio/test/mic")[0]["method"] == "POST"
        assert shell.to("/audio/test/mic")[0]["timeout"] == 2.0
        # No polling: the one forwarded call and nothing else.
        assert [c["endpoint"] for c in shell.calls] == ["/audio/test/mic"]

    def test_mic_test_busy_carries_the_shells_reason(self, repo, shell, routes):
        shell.routes["/audio/test/mic"] = (409, {
            "ok": False, "error": "busy", "message": "a take is in progress"})
        out = routes["assistant.voice_test_mic"](Req())
        assert out == {"ok": False, "reason": "a take is in progress"}

    def test_speaker_test_forwards_and_returns_the_device(self, repo, shell, routes):
        shell.routes["/audio/test/speaker"] = (200, {
            "ok": True, "playing": True, "device": "Spk A"})
        out = routes["assistant.voice_test_speaker"](Req())
        assert out["playing"] is True and out["device"] == "Spk A"
        assert [c["endpoint"] for c in shell.calls] == ["/audio/test/speaker"]

    def test_unresolved_output_is_ok_false_with_reason(self, repo, shell, routes):
        shell.routes["/audio/test/speaker"] = (503, {
            "ok": False, "error": "unavailable", "message": "no output device resolves"})
        out = routes["assistant.voice_test_speaker"](Req())
        assert out == {"ok": False, "reason": "no output device resolves"}

    def test_shell_down_for_both_tests(self, repo, routes):
        for name in ("assistant.voice_test_mic", "assistant.voice_test_speaker"):
            out = routes[name](Req())
            assert out["ok"] is False and out["reason"] == "shell not running"


class TestVoiceStatePassThrough:
    def test_mic_test_and_swap_error_appear_with_no_console_code(self, repo, shell, routes):
        state = {"ok": True, "level": 0.1,
                 "mic_test": {"active": True, "peak": 0.4, "result": None},
                 "swap_error": ""}
        shell.routes["/listen/state"] = (200, state)
        out = routes["assistant.voice_state"](Req())
        assert out["mic_test"] == state["mic_test"]
        assert out["swap_error"] == ""


class TestPreview:
    def test_forwards_voice_and_rate_unchanged(self, repo, shell, routes):
        _voices(repo, "en_US-amy-medium")
        out = routes["assistant.voice_preview"](
            Req({"voice": "en_US-amy-medium", "rate_percent": 130}))
        assert out == {"ok": True}
        body = shell.to("/speak")[0]["body"]
        assert body["voice"] == "en_US-amy-medium"
        assert body["rate_percent"] == 130
        assert body["text"] == assistant_feature.PREVIEW_SAMPLE

    def test_blank_voice_means_automatic_and_sends_no_voice(self, repo, shell, routes):
        routes["assistant.voice_preview"](Req({"voice": "  "}))
        body = shell.to("/speak")[0]["body"]
        assert "voice" not in body and "rate_percent" not in body

    @pytest.mark.parametrize("rate", [49, 201, "fast", True, [50]])
    def test_a_bad_rate_is_a_400(self, repo, shell, routes, rate):
        with pytest.raises(ValueError):
            routes["assistant.voice_preview"](Req({"rate_percent": rate}))
        assert shell.to("/speak") == []

    def test_boundaries_50_and_200_are_accepted(self, repo, shell, routes):
        for rate in (50, 200):
            assert routes["assistant.voice_preview"](Req({"rate_percent": rate}))["ok"]

    def test_an_uninstalled_voice_is_a_400(self, repo, shell, routes):
        _voices(repo, "en_US-amy-medium")
        with pytest.raises(ValueError):
            routes["assistant.voice_preview"](Req({"voice": "en_US-ghost-low"}))
        assert shell.to("/speak") == []

    def test_a_path_like_voice_is_refused(self, repo, shell, routes):
        with pytest.raises(ValueError):
            routes["assistant.voice_preview"](Req({"voice": "../../x"}))

    def test_writes_no_setting(self, repo, shell, routes):
        _voices(repo, "en_US-amy-medium")
        assistant_config.update(repo, {"speak_rate_percent": 90})
        before = _overrides_bytes(repo)
        assert before is not None
        routes["assistant.voice_preview"](
            Req({"voice": "en_US-amy-medium", "rate_percent": 160}))
        assert _overrides_bytes(repo) == before
        assert assistant_config.settings(repo)["speak_rate_percent"] == 90

    def test_writes_nothing_even_when_no_override_file_exists(self, repo, shell, routes):
        routes["assistant.voice_preview"](Req({"rate_percent": 120}))
        assert _overrides_bytes(repo) is None

    def test_shell_down_is_ok_false(self, repo, routes):
        out = routes["assistant.voice_preview"](Req({"rate_percent": 100}))
        assert out["ok"] is False and out["reason"] == "shell not running"

    def test_a_shell_refusal_is_ok_false_with_its_reason(self, repo, shell, routes):
        shell.routes["/speak"] = (503, {"ok": False, "message": "no voice installed"})
        out = routes["assistant.voice_preview"](Req({}))
        assert out == {"ok": False, "reason": "no voice installed"}


class TestInstalledVoices:
    def test_lists_only_onnx_voices_sorted(self, repo):
        _voices(repo, "b-voice", "a-voice")
        tts = os.path.join(repo, "desktop", "tts")
        for junk in ("a-voice.onnx.json", "c.onnx.part", "notes.txt"):
            open(os.path.join(tts, junk), "wb").close()
        assert voice_assets.installed_voices(repo) == ["a-voice", "b-voice"]

    def test_no_directory_is_empty(self, repo):
        assert voice_assets.installed_voices(repo) == []
