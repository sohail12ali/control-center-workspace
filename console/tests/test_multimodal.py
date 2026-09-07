"""T-007: getting a screenshot's pixels to a model that can see them.

The gap: `desktop_screenshot` returns a PATH. A Claude or Cursor backend opens
it with its own file tools; an `openai_api` backend has no file tools at all,
so a path is a string it can do nothing with. These tests pin the three
outcomes that matter — pixels for a vision model, an instruction for a
text-only one, and a refusal for anything that is not a capture.

The last of those is the security-shaped one: the path arrives inside a tool
result, which is text a model influenced.
"""

import base64
import json
import os
import struct
import zlib

import pytest

from server import multimodal


def _png(path, width=4, height=4):
    """A real, tiny PNG — the encoder is four lines and beats a fixture."""
    raw = b"".join(b"\x00" + bytes([255, 0, 0, 255] * width) for _ in range(height))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)
    return blob


@pytest.fixture
def capture(repo):
    """A capture on disk, and its repo-relative path."""
    rel = os.path.join(multimodal.CAPTURE_DIR_REL, "abc123.png").replace("\\", "/")
    _png(os.path.join(repo, rel))
    return rel


VISION = ["*vl*", "gpt-4o*", "claude*", "*vision*"]


class TestVisionDetection:
    @pytest.mark.parametrize("model", [
        "qwen2.5vl:7b", "gpt-4o-mini", "claude-sonnet-5", "llama-3.2-vision",
        "QWEN2.5VL:7B",
    ])
    def test_a_vision_model_is_recognised(self, model):
        assert multimodal.is_vision_model(model, VISION)

    @pytest.mark.parametrize("model", ["llama3", "mistral", "gpt-3.5-turbo", ""])
    def test_a_text_only_model_is_not(self, model):
        assert not multimodal.is_vision_model(model, VISION)

    def test_no_configured_globs_means_assume_not(self):
        """Guessing yes produces a model asked to look at something it cannot
        see, which reads as a broken feature rather than an unset one."""
        assert not multimodal.is_vision_model("gpt-4o", [])
        assert not multimodal.is_vision_model("gpt-4o", None)


class TestCapturePath:
    def test_reads_the_path_out_of_a_tool_result(self):
        result = json.dumps({"ok": True, "capture": {
            "capture_id": "abc123",
            "path": "console/.cache/desktop-captures/abc123.png"}})
        assert multimodal.capture_path(result) == "console/.cache/desktop-captures/abc123.png"

    def test_a_failed_capture_yields_nothing_to_attach(self):
        assert multimodal.capture_path(json.dumps({"ok": False, "reason": "shell not running"})) is None

    def test_a_bare_path_still_works(self):
        # Tolerated so a tool that changed shape does not silently stop
        # attaching pictures.
        assert multimodal.capture_path("console/.cache/desktop-captures/x.png").endswith("x.png")

    @pytest.mark.parametrize("junk", ["", "   ", "not json", "{}", "[]", None])
    def test_anything_else_is_nothing(self, junk):
        assert multimodal.capture_path(junk) is None


class TestConfinement:
    """The path arrives inside a tool result — text a model influenced. It is
    resolved against the captures directory and refused if it escapes."""

    def test_a_real_capture_resolves(self, repo, capture):
        assert multimodal.resolve_capture(repo, capture) is not None

    @pytest.mark.parametrize("escape", [
        "../../.env",
        "console/.cache/desktop-captures/../../../.env",
        "/etc/passwd",
        "console/.cache/assistant/memory.md",
        "",
    ])
    def test_anything_outside_the_captures_directory_is_refused(self, repo, escape):
        assert multimodal.resolve_capture(repo, escape) is None

    def test_a_path_inside_the_directory_that_does_not_exist_is_refused(self, repo):
        rel = os.path.join(multimodal.CAPTURE_DIR_REL, "nope.png")
        assert multimodal.resolve_capture(repo, rel) is None

    def test_an_escape_in_a_tool_result_becomes_a_refusal_not_an_attachment(self, repo):
        result = json.dumps({"ok": True, "capture": {"path": "../../.env"}})
        msg = multimodal.after_capture(
            repo, "console_desktop_screenshot", result, "gpt-4o", VISION)
        assert isinstance(msg["content"], str)
        assert "not a file in the captures directory" in msg["content"]


class TestFollowUpMessage:
    def test_a_vision_model_gets_the_pixels(self, repo, capture):
        result = json.dumps({"ok": True, "capture": {"path": capture}})
        msg = multimodal.after_capture(
            repo, "console_desktop_screenshot", result, "qwen2.5vl:7b", VISION)
        assert msg["role"] == "user"
        parts = msg["content"]
        assert isinstance(parts, list)
        kinds = [p["type"] for p in parts]
        assert "image_url" in kinds
        url = [p for p in parts if p["type"] == "image_url"][0]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        # The bytes really are the file's.
        blob = base64.b64decode(url.split(",", 1)[1])
        assert blob[:8] == b"\x89PNG\r\n\x1a\n"

    def test_a_text_only_model_is_told_to_use_ocr(self, repo, capture):
        """Silence here is the worst outcome this feature can produce: a
        confident description of a screen nobody looked at."""
        result = json.dumps({"ok": True, "capture": {"path": capture}})
        msg = multimodal.after_capture(
            repo, "console_desktop_screenshot", result, "llama3", VISION)
        assert isinstance(msg["content"], str)
        assert "desktop_ocr" in msg["content"]
        assert "cannot see images" in msg["content"]

    def test_it_asks_the_model_to_say_it_used_ocr(self, repo, capture):
        result = json.dumps({"ok": True, "capture": {"path": capture}})
        msg = multimodal.after_capture(repo, "console_desktop_screenshot",
                                       result, "llama3", VISION)
        assert "say plainly" in msg["content"]

    def test_a_non_capture_tool_gets_no_follow_up(self, repo):
        for tool in ("console_desktop_windows", "read_file", "run_command", ""):
            assert multimodal.after_capture(
                repo, tool, '{"ok": true}', "gpt-4o", VISION) is None

    def test_a_failed_capture_gets_no_follow_up(self, repo):
        result = json.dumps({"ok": False, "reason": "shell not running"})
        assert multimodal.after_capture(
            repo, "console_desktop_screenshot", result, "gpt-4o", VISION) is None

    def test_the_mcp_spelling_is_recognised_too(self, repo, capture):
        # The same verb reaches a model under two names depending on
        # transport; missing one would silently skip the attachment.
        result = json.dumps({"ok": True, "capture": {"path": capture}})
        msg = multimodal.after_capture(
            repo, "mcp__console__desktop-screenshot", result, "gpt-4o", VISION)
        assert isinstance(msg["content"], list)

    def test_an_oversized_capture_is_refused_with_its_size(self, repo, monkeypatch):
        rel = os.path.join(multimodal.CAPTURE_DIR_REL, "big.png").replace("\\", "/")
        _png(os.path.join(repo, rel))
        monkeypatch.setattr(multimodal, "MAX_IMAGE_BYTES", 10)
        result = json.dumps({"ok": True, "capture": {"path": rel}})
        msg = multimodal.after_capture(
            repo, "console_desktop_screenshot", result, "gpt-4o", VISION)
        assert "over the" in msg["content"]
        assert "desktop_ocr" in msg["content"], "it must still say what to do instead"
