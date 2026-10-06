"""Verify and atomic install (T-031-09; AC-21, 22, 23, 24, 30, 32).

The integrity boundary: a shell-visible name (`ggml-*.bin`, `*.onnx`) must never
exist for incomplete or unverified bytes. Everything runs against the local
range server with an injected `sleep` and `disk_free`; no real network.
"""

import errno
import os

import pytest

from voice_assets_server import Body, RangeServer
from server import voice_assets
from server.voice_assets import (Asset, AssetFile, Downloader, InstallError,
                                 TransferError, manifest_path, read_manifest)

NAME = "ggml-test.bin"
PATH = "/m/" + NAME
VOICE = "en_US-test-medium"


def make_body(size, seed=3):
    import random
    return Body(random.Random(seed).randbytes(size))


def file_spec(server, path, name, body, **kw):
    fields = dict(name=name, url=server.url(path), size=body.size,
                  sha256=body.sha256(), hash_source="hf-lfs-oid")
    fields.update(kw)
    return AssetFile(**fields)


def stt_asset(server, body, **kw):
    return Asset(id="test.en", kind="stt", label="t", repo="a/b", commit="c" * 40,
                 hint="1 MiB / 1 MB", license="mit",
                 files=(file_spec(server, PATH, NAME, body, **kw),))


def voice_asset(server, json_body, onnx_body, **onnx_kw):
    return Asset(id=VOICE, kind="voice", label="v", repo="a/b", commit="c" * 40,
                 hint="1 MiB / 1 MB", license="mit",
                 files=(file_spec(server, "/v/%s.onnx.json" % VOICE, VOICE + ".onnx.json", json_body),
                        file_spec(server, "/v/%s.onnx" % VOICE, VOICE + ".onnx", onnx_body, **onnx_kw)))


def downloader(**kw):
    kw.setdefault("allow_loopback_http", True)
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("disk_free", lambda path: 1 << 40)
    return Downloader(**kw)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


@pytest.fixture
def dest(tmp_path):
    return str(tmp_path / "stt")


def final_of(dest, name=NAME):
    return os.path.join(dest, name)


# --- AC-21: wrong bytes, right length -------------------------------------------

def test_wrong_bytes_with_the_right_length_fail_on_sha256_and_leave_no_final_name(dest):
    good, bad = make_body(300_000, seed=1), make_body(300_000, seed=2)
    assert good.size == bad.size
    with RangeServer({PATH: bad}) as server:
        asset = stt_asset(server, bad, sha256=good.sha256())
        with pytest.raises(InstallError) as caught:
            downloader().download(asset, dest)
    message = str(caught.value)
    assert "sha256" in message
    assert good.sha256()[:12] in message and bad.sha256()[:12] in message
    assert not os.path.exists(final_of(dest)), "the final name never existed"
    assert not os.path.exists(final_of(dest) + ".part"), ".part removed"
    assert not os.path.exists(manifest_path(final_of(dest)))
    assert len(server.gets()) == 1, "no automatic retry after a hash mismatch"


# --- AC-22: the four-point fault matrix -----------------------------------------

def run_recording(dest, server, body, fail_at=None):
    """Run an install, recording the file system at each fault point."""
    events = []
    final = final_of(dest)

    def fault(point, name):
        events.append((point, name, os.path.exists(final), os.path.exists(manifest_path(final))))
        if point == fail_at:
            raise RuntimeError("injected fault at " + point)

    result = None
    error = None
    try:
        result = downloader(fault=fault).download(stt_asset(server, body), dest)
    except RuntimeError as err:
        error = err
    return events, result, error


def test_without_a_fault_the_final_name_appears_only_after_verification_and_the_manifest_is_last(dest):
    body = make_body(500_000)
    with RangeServer({PATH: body}) as server:
        events, manifest, error = run_recording(dest, server, body)
    assert error is None
    assert [(e[0], e[2], e[3]) for e in events] == [
        ("after_last_byte", False, False),     # all bytes in, still only .part
        ("after_hash", False, False),          # verified, not yet renamed
        ("after_replace", True, False),         # renamed, manifest not yet
        ("during_manifest", True, False),       # manifest being written
    ]
    final = final_of(dest)
    assert read(final) == body.data
    assert not os.path.exists(final + ".part")
    stored = read_manifest(final)
    assert stored == manifest
    assert stored["id"] == "test.en" and stored["sha256"] == body.sha256()
    assert stored["size"] == body.size and stored["commit"] == "c" * 40
    assert stored["source_url"].endswith(PATH) and stored["installed_at"].endswith("Z")
    assert sorted(os.listdir(dest)) == [NAME, NAME + ".manifest.json"], "no .tmp or .part left"


@pytest.mark.parametrize("point", list(voice_assets.FAULT_POINTS))
def test_a_fault_at_each_point_never_leaves_an_unverified_final_name(dest, point):
    body = make_body(500_000)
    with RangeServer({PATH: body}) as server:
        events, _manifest, error = run_recording(dest, server, body, fail_at=point)
        assert error is not None and point in str(error)
        final = final_of(dest)
        if point in ("after_last_byte", "after_hash"):
            assert not os.path.exists(final), "no shell-visible name before verification"
            assert os.path.getsize(final + ".part") == body.size, "the verified-able bytes are kept"
            before = len(server.gets())
            result = downloader().download(stt_asset(server, body), dest)
            assert len(server.gets()) == before, "the next run reuses the complete .part"
            assert read(final) == body.data and result["sha256"] == body.sha256()
        else:
            # Renamed but no manifest: installed, unverified (task 11 reads the state).
            assert read(final) == body.data
            assert not os.path.exists(manifest_path(final))
            assert not os.path.exists(final + ".part")
            assert not any(n.endswith(".tmp") for n in os.listdir(dest))


# --- AC-23: voices install .onnx.json first, .onnx last --------------------------

def test_a_voice_installs_its_config_before_its_model_and_the_manifest_last(dest):
    cfg, onnx = make_body(4_000, seed=5), make_body(400_000, seed=6)
    seen = []
    cfg_final = os.path.join(dest, VOICE + ".onnx.json")
    onnx_final = os.path.join(dest, VOICE + ".onnx")

    def fault(point, name):
        seen.append((point, name, os.path.exists(cfg_final), os.path.exists(onnx_final)))

    with RangeServer({"/v/%s.onnx.json" % VOICE: cfg, "/v/%s.onnx" % VOICE: onnx}) as server:
        manifest = downloader(fault=fault).download(voice_asset(server, cfg, onnx), dest)
        paths = [r["path"] for r in server.gets()]
    assert paths == ["/v/%s.onnx.json" % VOICE, "/v/%s.onnx" % VOICE]
    by_point = {(p, n): (c, o) for p, n, c, o in seen}
    assert by_point[("after_hash", VOICE + ".onnx.json")] == (False, False), "json verified first"
    assert by_point[("after_last_byte", VOICE + ".onnx")] == (True, False), "json already in place"
    assert by_point[("after_hash", VOICE + ".onnx")] == (True, False), ".onnx last"
    assert by_point[("after_replace", VOICE + ".onnx")] == (True, True)
    assert manifest["id"] == VOICE and manifest["sha256"] == onnx.sha256()
    assert read_manifest(onnx_final)["files"][VOICE + ".onnx.json"] == cfg.sha256()
    assert not os.path.exists(manifest_path(cfg_final)), "one manifest, next to the .onnx"


def test_a_failed_onnx_leaves_no_onnx_and_removes_the_config_this_job_created(dest):
    cfg, good, bad = make_body(4_000, seed=5), make_body(200_000, seed=6), make_body(200_000, seed=7)
    with RangeServer({"/v/%s.onnx.json" % VOICE: cfg, "/v/%s.onnx" % VOICE: bad}) as server:
        asset = voice_asset(server, cfg, bad, sha256=good.sha256())
        with pytest.raises(InstallError):
            downloader().download(asset, dest)
    assert os.listdir(dest) == [], "no .onnx, no .onnx.json, no .part, no manifest"


def test_a_config_that_was_already_there_is_not_removed_when_the_onnx_fails(dest):
    cfg, good, bad = make_body(4_000, seed=5), make_body(200_000, seed=6), make_body(200_000, seed=7)
    os.makedirs(dest)
    with open(os.path.join(dest, VOICE + ".onnx.json"), "wb") as fh:
        fh.write(b"hand placed")
    with RangeServer({"/v/%s.onnx.json" % VOICE: cfg, "/v/%s.onnx" % VOICE: bad}) as server:
        with pytest.raises(InstallError):
            downloader().download(voice_asset(server, cfg, bad, sha256=good.sha256()), dest)
    assert not os.path.exists(os.path.join(dest, VOICE + ".onnx"))
    assert os.path.exists(os.path.join(dest, VOICE + ".onnx.json")), "pre-existing file kept"


# --- AC-24: Verify a hand-placed file ----------------------------------------------

def test_verify_writes_the_manifest_when_a_hand_placed_file_matches(dest):
    body = make_body(200_000)
    os.makedirs(dest)
    with open(final_of(dest), "wb") as fh:
        fh.write(body.data)
    with RangeServer({}) as server:
        result = downloader().verify_existing(stt_asset(server, body), dest)
    assert result["ok"] and read_manifest(final_of(dest))["sha256"] == body.sha256()
    assert read(final_of(dest)) == body.data


def test_verify_reports_a_mismatch_and_leaves_bytes_and_mtime_untouched(dest):
    body, other = make_body(200_000, seed=1), make_body(200_000, seed=2)
    os.makedirs(dest)
    with open(final_of(dest), "wb") as fh:
        fh.write(other.data)
    before = os.stat(final_of(dest))
    with RangeServer({}) as server:
        result = downloader().verify_existing(stt_asset(server, body), dest)
    assert not result["ok"]
    assert body.sha256()[:12] in result["message"] and other.sha256()[:12] in result["message"]
    after = os.stat(final_of(dest))
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
    assert read(final_of(dest)) == other.data
    assert not os.path.exists(manifest_path(final_of(dest)))


def test_verify_of_a_voice_needs_both_files(dest):
    cfg, onnx = make_body(4_000, seed=5), make_body(100_000, seed=6)
    os.makedirs(dest)
    with open(os.path.join(dest, VOICE + ".onnx"), "wb") as fh:
        fh.write(onnx.data)
    with RangeServer({}) as server:
        asset = voice_asset(server, cfg, onnx)
        missing = downloader().verify_existing(asset, dest)
        assert not missing["ok"] and "onnx.json is not installed" in missing["message"]
        with open(os.path.join(dest, VOICE + ".onnx.json"), "wb") as fh:
            fh.write(cfg.data)
        assert downloader().verify_existing(asset, dest)["ok"]


# --- AC-30, AC-32: disk ----------------------------------------------------------

def test_a_short_disk_is_refused_before_any_connection(dest):
    body = make_body(300_000)
    with RangeServer({PATH: body}) as server:
        with pytest.raises(InstallError) as caught:
            downloader(disk_free=lambda path: body.size - 1).download(stt_asset(server, body), dest)
    assert "free disk space" in str(caught.value)
    assert server.requests == [], "zero requests: refused before connecting"
    assert os.listdir(dest) == []


def test_free_space_is_judged_against_the_bytes_still_to_fetch(dest):
    body = make_body(300_000)
    os.makedirs(dest)
    with open(final_of(dest) + ".part", "wb") as fh:
        fh.write(body.data[:250_000])
    with RangeServer({PATH: body}) as server:
        downloader(disk_free=lambda path: 50_000).download(stt_asset(server, body), dest)
    assert read(final_of(dest)) == body.data


class FullDisk:
    """A part file that runs out of space on its second write."""

    def __init__(self, path, mode):
        self.fh = open(path, mode)
        self.writes = 0

    def write(self, data):
        self.writes += 1
        if self.writes >= 2:
            raise OSError(errno.ENOSPC, "No space left on device")
        return self.fh.write(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fh.close()


def test_a_write_error_mid_transfer_fails_the_job_and_keeps_the_part(dest):
    body = make_body(3_500_000)
    sleeps = []
    with RangeServer({PATH: body}) as server:
        with pytest.raises(TransferError) as caught:
            downloader(open_part=FullDisk, sleep=sleeps.append).download(stt_asset(server, body), dest)
    assert "cannot write" in str(caught.value) and "space" in str(caught.value).lower()
    assert not caught.value.retryable and sleeps == [], "a full disk is not retried"
    assert 0 < os.path.getsize(final_of(dest) + ".part") < body.size
    assert not os.path.exists(final_of(dest))


def test_a_refused_rename_keeps_the_verified_part_and_a_later_run_installs_it(dest, monkeypatch):
    body = make_body(300_000)
    real_replace = os.replace

    def locked(src, dst):
        if str(dst).endswith(NAME):
            raise PermissionError(13, "the file is in use by another process")
        return real_replace(src, dst)

    with RangeServer({PATH: body}) as server:
        monkeypatch.setattr(voice_assets.os, "replace", locked)
        with pytest.raises(InstallError) as caught:
            downloader().download(stt_asset(server, body), dest)
        assert "in use" in str(caught.value) and not os.path.exists(final_of(dest))
        assert os.path.getsize(final_of(dest) + ".part") == body.size
        monkeypatch.undo()
        before = len(server.gets())
        downloader().download(stt_asset(server, body), dest)
        assert len(server.gets()) == before, "the kept part needed no new download"
    assert read(final_of(dest)) == body.data


def test_the_manifest_reader_returns_none_for_missing_or_damaged_files(dest):
    os.makedirs(dest)
    assert read_manifest(final_of(dest)) is None
    with open(manifest_path(final_of(dest)), "w") as fh:
        fh.write("{ not json")
    assert read_manifest(final_of(dest)) is None
