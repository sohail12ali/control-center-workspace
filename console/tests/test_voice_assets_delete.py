"""Delete (T-031-12; AC-27, 28, 29, NFR-3).

A destructive action with its own safety rules: refusals that explain
themselves, an OS lock reported as a sentence (never a 5xx) with nothing
half-deleted, names that must match the inventory, and confinement to
`desktop/stt` and `desktop/tts`. Synthetic bytes, no network, no process.
"""

import hashlib
import io
import json
import os

import pytest

from server import voice_assets
from server.voice_assets import (Asset, AssetFile, Catalog, Downloader, Job, Manager,
                                 delete_asset, inventory)

TINY = b"t" * 1000
BASE = b"b" * 2000
CFG = b"{}" * 25
ONNX = b"o" * 3000
SETTINGS = {"stt_model": "base.en", "speak_voice": "a-other"}


def spec(name, data):
    return AssetFile(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     url="https://huggingface.co/a/b/resolve/%s/%s" % ("c" * 40, name),
                     hash_source="hf-lfs-oid")


CATALOG = Catalog(assets=(
    Asset("tiny.en", "stt", "tiny", "a/b", "c" * 40, "1 KiB", "mit",
          (spec("ggml-tiny.en.bin", TINY),)),
    Asset("base.en", "stt", "base", "a/b", "c" * 40, "2 KiB", "mit",
          (spec("ggml-base.en.bin", BASE),)),
    Asset("v-one-medium", "voice", "v1", "a/b", "c" * 40, "3 KiB", "see url",
          (spec("v-one-medium.onnx.json", CFG), spec("v-one-medium.onnx", ONNX))),
))


@pytest.fixture
def root(tmp_path):
    return str(tmp_path / "ws")


def stt_dir(root):
    return os.path.join(root, "desktop", "stt")


def tts_dir(root):
    return os.path.join(root, "desktop", "tts")


def place(directory, name, data):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "wb") as fh:
        fh.write(data)


def listing(directory):
    return sorted(os.listdir(directory)) if os.path.isdir(directory) else []


def state_of(root, asset_id):
    rows = {r["id"]: r for r in inventory(root, CATALOG, settings=SETTINGS)["assets"]}
    return rows[asset_id]["state"]


def delete(root, name, **kw):
    kw.setdefault("settings", SETTINGS)
    return delete_asset(root, name, catalog=CATALOG, **kw)


def install_tiny_with_manifest_and_part(root):
    place(stt_dir(root), "ggml-tiny.en.bin", TINY)
    assert Downloader().verify_existing(CATALOG.get("tiny.en"), stt_dir(root))["ok"]
    place(stt_dir(root), "ggml-tiny.en.bin.part", b"stale")
    place(stt_dir(root), "ggml-base.en.bin", BASE)       # base is the model in use


# --- AC-27 -------------------------------------------------------------------

def test_delete_removes_the_final_the_manifest_and_the_part_and_the_row_reads_not_installed(root):
    install_tiny_with_manifest_and_part(root)
    result = delete(root, "tiny.en")
    assert result["ok"] and result["removed"] == [
        "ggml-tiny.en.bin", "ggml-tiny.en.bin.manifest.json", "ggml-tiny.en.bin.part"]
    assert listing(stt_dir(root)) == ["ggml-base.en.bin"], "nothing else touched, no tombstones"
    assert state_of(root, "tiny.en") == "not_installed"
    assert state_of(root, "base.en") == "installed"


def test_a_file_name_works_as_well_as_an_id_and_custom_files_can_be_deleted(root):
    install_tiny_with_manifest_and_part(root)
    place(stt_dir(root), "ggml-custom.bin", b"c" * 9)
    assert delete(root, "ggml-tiny.en.bin")["ok"]
    assert delete(root, "custom")["ok"]
    assert listing(stt_dir(root)) == ["ggml-base.en.bin"]


def test_a_partial_download_is_deleted_like_any_other_file_and_nothing_to_delete_is_harmless(root):
    place(stt_dir(root), "ggml-tiny.en.bin.part", b"half")
    place(stt_dir(root), "ggml-base.en.bin", BASE)
    assert state_of(root, "tiny.en") == "partial"
    assert delete(root, "tiny.en")["removed"] == ["ggml-tiny.en.bin.part"]
    result = delete(root, "tiny.en")
    assert result["ok"] and result["removed"] == []


def test_a_voice_is_removed_with_its_config_and_manifest(root):
    place(tts_dir(root), "a-other.onnx", b"x")                      # the voice in use
    place(tts_dir(root), "v-one-medium.onnx", ONNX)
    place(tts_dir(root), "v-one-medium.onnx.json", CFG)
    assert Downloader().verify_existing(CATALOG.get("v-one-medium"), tts_dir(root))["ok"]
    result = delete(root, "v-one-medium")
    assert result["ok"] and len(result["removed"]) == 3
    assert listing(tts_dir(root)) == ["a-other.onnx"]


# --- AC-28: refusals ------------------------------------------------------------

def test_refusals_say_why_and_delete_nothing(root):
    install_tiny_with_manifest_and_part(root)
    before = listing(stt_dir(root))
    # In use: the configured model.
    refused = delete(root, "base.en")
    assert not refused["ok"] and refused["error"] == "refused"
    assert "ggml-base.en.bin" in refused["reason"] and "in use" in refused["reason"]
    # Loaded in the engine (a swap pending: tiny is loaded though base is configured).
    pointer = os.path.join(root, "console", ".cache", "desktop", "bridge.json")
    os.makedirs(os.path.dirname(pointer))
    with open(pointer, "w", encoding="utf-8") as fh:
        json.dump({"base_url": "http://127.0.0.1:1234", "token": "t"}, fh)

    def shell(request, timeout=None):
        body = {"ok": True, "caps": {"loaded_model": "ggml-tiny.en.bin"}}
        return io.BytesIO(json.dumps(body).encode("utf-8"))

    loaded = delete(root, "tiny.en", opener=shell)
    assert not loaded["ok"] and loaded["error"] == "refused" and "loaded" in loaded["reason"]
    assert listing(stt_dir(root)) == before


def test_a_downloading_asset_cannot_be_deleted(root):
    place(stt_dir(root), "ggml-base.en.bin", BASE)
    manager = Manager(root, catalog=CATALOG)
    manager._jobs["tiny.en"] = Job(CATALOG.get("tiny.en"), lambda: 0.0)    # a live job, no thread
    place(stt_dir(root), "ggml-tiny.en.bin.part", b"half")
    refused = delete(root, "tiny.en", manager=manager)
    assert not refused["ok"] and "being downloaded" in refused["reason"]
    assert os.path.exists(os.path.join(stt_dir(root), "ggml-tiny.en.bin.part"))


@pytest.mark.parametrize("fail_on_call", [1, 2, 3])
def test_an_os_lock_is_a_sentence_not_a_5xx_and_nothing_is_half_deleted(root, fail_on_call):
    place(tts_dir(root), "a-other.onnx", b"x")
    place(tts_dir(root), "v-one-medium.onnx", ONNX)
    place(tts_dir(root), "v-one-medium.onnx.json", CFG)
    assert Downloader().verify_existing(CATALOG.get("v-one-medium"), tts_dir(root))["ok"]
    before = {n: open(os.path.join(tts_dir(root), n), "rb").read() for n in listing(tts_dir(root))}
    calls = []

    def locked(src, dst):
        calls.append(os.path.basename(src))
        if len(calls) == fail_on_call:
            raise PermissionError(13, "Access is denied")
        return os.rename(src, dst)

    result = delete(root, "v-one-medium", rename=locked)        # returns, does not raise
    assert result["ok"] is False and result["error"] == "locked"
    assert os.path.basename(calls[fail_on_call - 1]) in result["reason"]
    assert "Nothing was changed" in result["reason"] and "Access is denied" in result["reason"]
    after = {n: open(os.path.join(tts_dir(root), n), "rb").read() for n in listing(tts_dir(root))}
    assert after == before, "every file is back with its bytes; no tombstone remains"


def test_a_tombstone_that_cannot_be_unlinked_does_not_undo_the_delete(root):
    install_tiny_with_manifest_and_part(root)

    def no_unlink(path):
        raise PermissionError(13, "Access is denied")

    result = delete(root, "tiny.en", remove=no_unlink)
    assert result["ok"]
    assert not os.path.exists(os.path.join(stt_dir(root), "ggml-tiny.en.bin"))
    assert state_of(root, "tiny.en") == "not_installed"


def test_deleting_forgets_a_finished_job_so_the_row_reads_from_the_disk(root):
    install_tiny_with_manifest_and_part(root)
    manager = Manager(root, catalog=CATALOG)
    job = Job(CATALOG.get("tiny.en"), lambda: 0.0)
    job._set_state("installed")
    manager._jobs["tiny.en"] = job
    assert delete(root, "tiny.en", manager=manager)["ok"]
    assert manager.job("tiny.en") is None


# --- AC-29: names and confinement --------------------------------------------------

@pytest.mark.parametrize("name", [
    "../outside.bin", "..\\outside.bin", "a/b", "a\\b", "..", ".", "",
    "C:\\Windows\\win.ini", "/etc/passwd", "ggml-tiny.en.bin\x00", "ggml tiny.bin",
    None, 5, ["tiny.en"],
    "ggml-ghost.bin",                       # a safe name that is not in the inventory
    "ggml-ghost.bin.part", "ggml-tiny.en.bin.manifest.json",
])
def test_names_that_are_not_inventory_entries_are_rejected_and_nothing_is_deleted(root, name):
    install_tiny_with_manifest_and_part(root)
    outside = os.path.join(root, "outside.bin")
    with open(outside, "wb") as fh:
        fh.write(b"keep me")
    before = listing(stt_dir(root))
    result = delete(root, name)
    assert result["ok"] is False and result["error"] in ("bad_name", "unknown")
    assert listing(stt_dir(root)) == before
    assert open(outside, "rb").read() == b"keep me"


def test_confinement_check_resolves_dot_dot_and_requires_a_strict_child(root):
    os.makedirs(stt_dir(root))
    inside = os.path.join(stt_dir(root), "ggml-x.bin")
    assert voice_assets._confined(inside, stt_dir(root))
    assert not voice_assets._confined(os.path.join(stt_dir(root), "..", "x.bin"), stt_dir(root))
    assert not voice_assets._confined(os.path.join(stt_dir(root), ".."), stt_dir(root))
    assert not voice_assets._confined(stt_dir(root), stt_dir(root))
    assert not voice_assets._confined(os.path.join(tts_dir(root), "x.onnx"), stt_dir(root))


def test_a_symlink_that_escapes_the_directory_is_refused_and_its_target_survives(root):
    install_tiny_with_manifest_and_part(root)
    outside = os.path.join(root, "outside.bin")
    with open(outside, "wb") as fh:
        fh.write(b"keep me")
    link = os.path.join(stt_dir(root), "ggml-evil.bin")
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError) as err:
        pytest.skip("SKIPPED LOUDLY: cannot create a symlink on this machine (%s); "
                    "the resolution logic is covered by the confinement test above" % err)
    rows = {r["name"]: r for r in inventory(root, CATALOG, settings=SETTINGS)["assets"]}
    assert "ggml-evil.bin" in rows, "the shell would see it, so the inventory lists it"
    result = delete(root, "ggml-evil.bin")
    assert result["ok"] is False and result["error"] == "outside"
    assert os.path.islink(link) and open(outside, "rb").read() == b"keep me"
