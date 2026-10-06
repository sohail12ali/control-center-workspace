"""The inventory (T-031-11; AC-4, 5, 6, 7, 8, 22 state half, 72 files half).

What exists on disk, whether it was verified, which file the shell will use and
which one it has loaded, with the shell up or down. Read-only, no outbound
internet call. Synthetic bytes stand in for models; the one fault-injected
install uses the local range server.
"""

import hashlib
import io
import json
import os
import socket
import urllib.request

import pytest

from voice_assets_server import Body, RangeServer
from server import native_bridge, voice_assets
from server.voice_assets import (Asset, AssetFile, Catalog, Downloader, Manager,
                                 inventory, manifest_path)

TINY = b"t" * 1000
BASE = b"b" * 2000
CFG = b"{}" * 25
ONNX = b"o" * 3000
SETTINGS = {"stt_model": "base.en", "speak_voice": ""}


def spec(name, data, url=None):
    return AssetFile(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     url=url or "https://huggingface.co/a/b/resolve/%s/%s" % ("c" * 40, name),
                     hash_source="hf-lfs-oid")


def fixture_catalog(server=None):
    def url(path):
        return server.url(path) if server else None
    return Catalog(assets=(
        Asset("tiny.en", "stt", "tiny", "a/b", "c" * 40, "1 KiB", "mit",
              (spec("ggml-tiny.en.bin", TINY, url("/tiny")),)),
        Asset("base.en", "stt", "base", "a/b", "c" * 40, "2 KiB", "mit",
              (spec("ggml-base.en.bin", BASE, url("/base")),)),
        Asset("v-one-medium", "voice", "v1", "a/b", "c" * 40, "3 KiB", "see url",
              (spec("v-one-medium.onnx.json", CFG, url("/v1.json")),
               spec("v-one-medium.onnx", ONNX, url("/v1.onnx")))),
    ))


@pytest.fixture
def root(tmp_path):
    return str(tmp_path)


def stt_dir(root):
    return os.path.join(root, "desktop", "stt")


def tts_dir(root):
    return os.path.join(root, "desktop", "tts")


def place(directory, name, data):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "wb") as fh:
        fh.write(data)


def rows_by_id(result):
    return {r["id"]: r for r in result["assets"]}


class FakeBridge:
    """Stands in for `urlopen` to the shell and records what it was asked."""

    def __init__(self, caps=None):
        self.caps = caps if caps is not None else {}
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append({"url": request.full_url, "timeout": timeout})
        body = {"ok": True, "version": "0.1.0", "pid": 1, "caps": self.caps}
        return io.BytesIO(json.dumps(body).encode("utf-8"))


def write_pointer(root):
    path = os.path.join(root, "console", ".cache", "desktop", "bridge.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"base_url": "http://127.0.0.1:1234", "token": "t", "pid": 1, "started": 0}, fh)


# --- AC-4 --------------------------------------------------------------------

def test_empty_and_absent_directories_give_all_not_installed_and_a_free_space_figure(root):
    for variant in ("absent", "empty"):
        if variant == "empty":
            os.makedirs(stt_dir(root))
            os.makedirs(tts_dir(root))
        result = inventory(root, fixture_catalog(), settings=SETTINGS, disk_free=lambda p: 12345)
        assert [r["state"] for r in result["assets"]] == ["not_installed"] * 3
        assert result["free_bytes"] == 12345
        assert all(not r["verified"] and not r["in_use"] and not r["loaded"] for r in result["assets"])
        assert [r["custom"] for r in result["assets"]] == [False] * 3
    assert json.dumps(result), "the answer is JSON-ready"
    assert not any("url" in r for r in result["assets"]), "no URL leaves the console"


def test_free_space_is_read_from_a_directory_that_exists(root):
    seen = []
    inventory(root, fixture_catalog(), settings=SETTINGS,
              disk_free=lambda p: seen.append(p) or 1)
    assert os.path.isdir(seen[0])


# --- AC-5 --------------------------------------------------------------------

def test_final_with_manifest_is_verified_final_alone_is_not_and_a_part_is_partial(root):
    catalog = fixture_catalog()
    place(stt_dir(root), "ggml-tiny.en.bin", TINY)
    assert Downloader().verify_existing(catalog.get("tiny.en"), stt_dir(root))["ok"]
    place(stt_dir(root), "ggml-base.en.bin", BASE)                    # no manifest
    place(tts_dir(root), "v-one-medium.onnx.part", ONNX[:1234])        # half a voice
    rows = rows_by_id(inventory(root, catalog, settings=SETTINGS))
    assert (rows["tiny.en"]["state"], rows["tiny.en"]["verified"]) == ("installed", True)
    assert (rows["base.en"]["state"], rows["base.en"]["verified"]) == ("installed", False)
    assert rows["base.en"]["size"] == len(BASE)
    assert rows["v-one-medium"]["state"] == "partial" and rows["v-one-medium"]["size"] == 1234
    assert not rows["v-one-medium"]["verified"]


def test_a_manifest_that_disagrees_with_the_catalog_or_the_file_is_not_verified(root):
    catalog = fixture_catalog()
    place(stt_dir(root), "ggml-tiny.en.bin", TINY)
    final = os.path.join(stt_dir(root), "ggml-tiny.en.bin")
    Downloader().verify_existing(catalog.get("tiny.en"), stt_dir(root))
    with open(manifest_path(final), encoding="utf-8") as fh:
        good = json.load(fh)
    for change in ({"sha256": "f" * 64}, {"size": len(TINY) + 1}):
        with open(manifest_path(final), "w", encoding="utf-8") as fh:
            json.dump(dict(good, **change), fh)
        assert not rows_by_id(inventory(root, catalog, settings=SETTINGS))["tiny.en"]["verified"]
    with open(manifest_path(final), "w", encoding="utf-8") as fh:
        fh.write("not json")
    assert not rows_by_id(inventory(root, catalog, settings=SETTINGS))["tiny.en"]["verified"]
    with open(manifest_path(final), "w", encoding="utf-8") as fh:
        json.dump(good, fh)
    assert rows_by_id(inventory(root, catalog, settings=SETTINGS))["tiny.en"]["verified"]


# --- AC-6 --------------------------------------------------------------------

def test_uncatalogued_models_and_voices_are_custom_and_other_files_are_not_listed(root):
    place(stt_dir(root), "ggml-tiny.en.bin", TINY)
    place(stt_dir(root), "ggml-custom.bin", b"c" * 77)
    place(stt_dir(root), "ggml-custom.bin.part", b"x")
    place(stt_dir(root), "ggml-custom.bin.manifest.json", b"{}")
    place(stt_dir(root), "notes.bin", b"x")             # not a ggml-* file: the shell ignores it
    place(stt_dir(root), "README.txt", b"x")
    place(tts_dir(root), "en_US-mine-medium.onnx", b"o" * 55)
    place(tts_dir(root), "en_US-mine-medium.onnx.json", b"{}")
    place(tts_dir(root), "readme.md", b"x")
    result = inventory(root, fixture_catalog(), settings=SETTINGS)
    custom = {r["name"]: r for r in result["assets"] if r["custom"]}
    assert sorted(custom) == ["en_US-mine-medium.onnx", "ggml-custom.bin"]
    assert custom["ggml-custom.bin"]["id"] == "custom" and custom["ggml-custom.bin"]["kind"] == "stt"
    assert custom["ggml-custom.bin"]["size"] == 77 and custom["ggml-custom.bin"]["state"] == "installed"
    assert custom["en_US-mine-medium.onnx"]["id"] == "en_US-mine-medium"
    assert not custom["ggml-custom.bin"]["verified"]
    names = [r["name"] for r in result["assets"]]
    assert len(names) == len(set(names)) == 5, "3 catalog rows + 2 custom, nothing else"


# --- AC-7 --------------------------------------------------------------------

@pytest.mark.parametrize("wanted, installed, expected", [
    ("base.en", ["tiny.en", "base.en"], "base.en"),          # the named file
    ("tiny.en", ["tiny.en", "base.en"], "tiny.en"),
    ("small.en", ["tiny.en", "base.en"], "tiny.en"),         # configured but absent: the smallest
    ("", ["base.en", "tiny.en"], "tiny.en"),                 # blank: the smallest
    ("base.en", [], None),                                   # nothing installed
])
def test_in_use_follows_the_shells_model_resolution(root, wanted, installed, expected):
    data = {"tiny.en": TINY, "base.en": BASE}
    for name in installed:
        place(stt_dir(root), "ggml-%s.bin" % name, data[name])
    rows = rows_by_id(inventory(root, fixture_catalog(),
                                settings={"stt_model": wanted, "speak_voice": ""}))
    in_use = [i for i in ("tiny.en", "base.en") if rows[i]["in_use"]]
    assert in_use == ([expected] if expected else [])


def test_a_blank_or_missing_voice_means_the_first_sorted_installed_one(root):
    place(tts_dir(root), "zz-last.onnx", b"z")
    place(tts_dir(root), "v-one-medium.onnx", ONNX)
    place(tts_dir(root), "v-one-medium.onnx.json", CFG)
    for wanted, expected in (("", "v-one-medium"), ("nope", "v-one-medium"), ("zz-last", "zz-last")):
        result = inventory(root, fixture_catalog(), settings={"stt_model": "", "speak_voice": wanted})
        in_use = [r["id"] for r in result["assets"] if r["kind"] == "voice" and r["in_use"]]
        assert in_use == [expected], wanted


# --- the shell: loaded, down, timeout, no outbound call ---------------------------

def test_loaded_comes_from_the_shell_and_its_caps_are_passed_on(root):
    place(stt_dir(root), "ggml-tiny.en.bin", TINY)
    place(stt_dir(root), "ggml-base.en.bin", BASE)
    write_pointer(root)
    bridge = FakeBridge({"loaded_model": "ggml-base.en.bin", "stt_model": "ggml-base.en.bin",
                         "speak_backend": "piper", "speak_voice_in_use": "v-one-medium.onnx",
                         "ocr": True})
    result = inventory(root, fixture_catalog(), settings=SETTINGS, opener=bridge)
    rows = rows_by_id(result)
    assert rows["base.en"]["loaded"] and not rows["tiny.en"]["loaded"]
    assert result["shell"] == {"reachable": True, "speak_backend": "piper",
                               "speak_voice_in_use": "v-one-medium.onnx",
                               "stt_model": "ggml-base.en.bin", "loaded_model": "ggml-base.en.bin"}


def test_with_the_shell_down_the_answer_is_normal_and_says_so(root):
    place(stt_dir(root), "ggml-base.en.bin", BASE)
    result = inventory(root, fixture_catalog(), settings=SETTINGS)       # no pointer file
    assert result["shell"] == {"reachable": False, "reason": "shell not running"}
    rows = rows_by_id(result)
    assert rows["base.en"]["state"] == "installed" and not rows["base.en"]["loaded"]
    assert rows["base.en"]["in_use"], "in_use needs no shell"


def test_a_stale_pointer_reads_as_shell_down_and_the_bridge_call_is_capped_at_1_5_s(root):
    write_pointer(root)
    calls = []

    def refuse(request, timeout=None):
        calls.append(timeout)
        raise ConnectionRefusedError("nothing listening")

    result = inventory(root, fixture_catalog(), settings=SETTINGS, opener=refuse)
    assert result["shell"]["reachable"] is False
    assert calls and all(t <= 1.5 for t in calls)
    bridge = FakeBridge()
    inventory(root, fixture_catalog(), settings=SETTINGS, opener=bridge)
    assert bridge.calls[0]["timeout"] <= 1.5


def test_the_inventory_makes_no_outbound_call(root, monkeypatch):
    place(stt_dir(root), "ggml-base.en.bin", BASE)
    write_pointer(root)

    attempts = []

    def forbidden(*args, **kwargs):
        # Recorded, not just raised: the bridge client swallows transport errors,
        # so an exception alone could hide an attempt.
        attempts.append(args)
        raise OSError("an outbound call was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    bridge = FakeBridge({"loaded_model": "ggml-base.en.bin"})
    result = inventory(root, fixture_catalog(), settings=SETTINGS, opener=bridge)
    assert result["shell"]["reachable"] and len(bridge.calls) == 1
    assert "127.0.0.1:1234/health" in bridge.calls[0]["url"], "only the shell was asked"
    assert attempts == [], "nothing but the injected bridge opener was used"
    # And with no pointer at all, nothing is attempted either.
    os.remove(os.path.join(root, "console", ".cache", "desktop", "bridge.json"))
    assert not inventory(root, fixture_catalog(), settings=SETTINGS)["shell"]["reachable"]
    assert attempts == []


def test_capabilities_keeps_its_default_timeout_and_accepts_an_override(root):
    write_pointer(root)
    bridge = FakeBridge()
    native_bridge.capabilities(root, opener=bridge)
    native_bridge.capabilities(root, opener=bridge, timeout=1.5)
    assert [c["timeout"] for c in bridge.calls] == [native_bridge.DEFAULT_TIMEOUT, 1.5]


# --- AC-72 files half, AC-22 state half ---------------------------------------------

def test_files_placed_by_a_script_read_installed_but_not_verified_until_verify_runs(root):
    catalog = fixture_catalog()
    place(stt_dir(root), "ggml-base.en.bin", BASE)                     # as get-whisper.ps1 would
    place(tts_dir(root), "v-one-medium.onnx", ONNX)
    place(tts_dir(root), "v-one-medium.onnx.json", CFG)
    rows = rows_by_id(inventory(root, catalog, settings=SETTINGS))
    for asset_id in ("base.en", "v-one-medium"):
        assert (rows[asset_id]["state"], rows[asset_id]["verified"]) == ("installed", False)
    assert Downloader().verify_existing(catalog.get("v-one-medium"), tts_dir(root))["ok"]
    assert rows_by_id(inventory(root, catalog, settings=SETTINGS))["v-one-medium"]["verified"]


def test_a_rename_before_manifest_leftover_reads_installed_and_unverified(root):
    body = Body(BASE)
    with RangeServer({"/base": body}) as server:
        catalog = fixture_catalog(server)

        def fault(point, name):
            if point == "after_replace":
                raise RuntimeError("power cut")

        downloader = Downloader(allow_loopback_http=True, sleep=lambda s: None,
                                disk_free=lambda p: 1 << 40, fault=fault)
        with pytest.raises(RuntimeError):
            downloader.download(catalog.get("base.en"), stt_dir(root))
    row = rows_by_id(inventory(root, catalog, settings=SETTINGS))["base.en"]
    assert (row["state"], row["verified"]) == ("installed", False)
    assert os.path.exists(os.path.join(stt_dir(root), "ggml-base.en.bin"))


# --- job state is layered on the disk state -------------------------------------------

def test_a_failed_job_shows_failed_with_its_error_and_progress_fields(root):
    with RangeServer({"/base": Body(BASE)}, status_script=[404]) as server:
        catalog = fixture_catalog(server)
        manager = Manager(root, catalog=catalog,
                          downloader=Downloader(allow_loopback_http=True, sleep=lambda s: None,
                                                disk_free=lambda p: 1 << 40))
        try:
            manager.download("base.en")
            assert manager.job("base.en").wait_state("failed")
            row = rows_by_id(inventory(root, catalog, manager=manager, settings=SETTINGS))["base.en"]
        finally:
            manager.stop_all()
    assert row["state"] == "failed" and "404" in row["error"]
    for key in ("done", "total", "speed_bps", "eta_s", "resumed_from", "file"):
        assert key in row
