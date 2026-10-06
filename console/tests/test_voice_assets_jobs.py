"""The job manager (T-031-10; AC-9, 10, 11, 18, 19, 20).

One background job per asset id, pause/resume/cancel, progress, and recovery
after a restart. Deterministic: the clock is injected (`FakeClock`), pacing
comes from the server's `gate` hook (a semaphore the test releases chunk by
chunk), waits are on events or conditions, and no assertion is about wall time.
No real network (local server), and no thread outlives its test.
"""

import logging
import os
import random
import threading
import time

import pytest

from voice_assets_server import Body, RangeServer
from server import voice_assets
from server.voice_assets import (Asset, AssetFile, Catalog, Downloader, Manager,
                                 read_manifest)

CHUNK = 65536
NAME = "ggml-test.bin"
PATH = "/m/" + NAME
VOICE = "en_US-test-medium"


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def make_body(size, seed=4):
    return Body(random.Random(seed).randbytes(size))


def wait_until(predicate, timeout=10.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "timed out waiting for the condition"
        time.sleep(0.002)


def file_spec(server, path, name, body):
    return AssetFile(name=name, url=server.url(path), size=body.size,
                     sha256=body.sha256(), hash_source="hf-lfs-oid")


def stt_asset(server, body):
    return Asset(id="test.en", kind="stt", label="t", repo="a/b", commit="c" * 40,
                 hint="1 MiB / 1 MB", license="mit",
                 files=(file_spec(server, PATH, NAME, body),))


def voice_asset(server, cfg, onnx):
    return Asset(id=VOICE, kind="voice", label="v", repo="a/b", commit="c" * 40,
                 hint="1 MiB / 1 MB", license="mit",
                 files=(file_spec(server, "/v/%s.onnx.json" % VOICE, VOICE + ".onnx.json", cfg),
                        file_spec(server, "/v/%s.onnx" % VOICE, VOICE + ".onnx", onnx)))


class Gate:
    """Lets the server send one chunk per `release()`."""

    def __init__(self):
        self.sem = threading.Semaphore(0)

    def __call__(self, sent):
        assert self.sem.acquire(timeout=10), "the test never released the server"

    def release(self, n=1):
        self.sem.release(n)


@pytest.fixture
def world(tmp_path):
    """Servers and managers a test creates; all stopped at teardown."""
    servers, managers = [], []

    class World:
        root = str(tmp_path)
        clock = FakeClock()

        def server(self, files, **kw):
            kw.setdefault("chunk", CHUNK)
            s = RangeServer(files, **kw).start()
            servers.append(s)
            return s

        def manager(self, assets, root=None, **kw):
            dl = Downloader(allow_loopback_http=True, sleep=lambda s: None,
                            disk_free=lambda p: 1 << 40)
            m = Manager(root or self.root, catalog=Catalog(assets=tuple(assets)), downloader=dl,
                        clock=kw.get("clock", self.clock))
            managers.append(m)
            return m

        def stt_dir(self):
            return os.path.join(self.root, "desktop", "stt")

        def final(self):
            return os.path.join(self.stt_dir(), NAME)

    yield World()
    for m in managers:
        m.stop_all()
    for s in servers:
        s.stop()
    alive = [t.name for t in threading.enumerate()
             if t.name.startswith("voice-asset-") and t.is_alive()]
    assert alive == [], "a job thread outlived its test: %s" % alive


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


# --- AC-9 --------------------------------------------------------------------

def test_a_download_goes_downloading_verifying_installed_with_a_manifest_and_no_part(world):
    body = make_body(400_000)
    server = world.server({PATH: body})
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    assert job.wait_state("installed")
    assert job.history == ["downloading", "verifying", "installed"]
    assert read(world.final()) == body.data
    assert read_manifest(world.final())["sha256"] == body.sha256()
    assert not os.path.exists(world.final() + ".part")
    snap = manager.snapshot("test.en")
    assert snap["state"] == "installed" and snap["done"] == snap["total"] == body.size


# --- AC-10 -------------------------------------------------------------------

def test_progress_is_live_non_decreasing_with_speed_and_eta_and_null_eta_at_zero_speed(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    first = job.snapshot()
    assert first["speed_bps"] == 0 and first["eta_s"] is None, "nothing moved yet"
    seen = []
    for step in range(1, 5):
        world.clock.advance(0.2)
        gate.release()
        wait_until(lambda: job.snapshot()["done"] >= step * CHUNK)
        seen.append(job.snapshot())
    dones = [s["done"] for s in seen]
    assert dones == sorted(dones) and dones[-1] == 4 * CHUNK
    assert all(s["state"] == "downloading" and s["total"] == body.size for s in seen)
    assert all(s["file"] == NAME and s["resumed_from"] == 0 for s in seen)
    moving = seen[-1]
    assert 200_000 < moving["speed_bps"] < 500_000, "about one chunk per 0.2 s of clock time"
    assert moving["eta_s"] is not None and moving["eta_s"] > 0
    world.clock.advance(voice_assets.SPEED_WINDOW + 1)      # nothing arrives for a long while
    stalled = job.snapshot()
    assert stalled["speed_bps"] == 0 and stalled["eta_s"] is None
    gate.release(50)
    assert job.wait_state("installed")


# --- AC-11 -------------------------------------------------------------------

def test_a_second_download_returns_the_same_job_and_one_transfer_happens(world):
    body = make_body(4 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    again, third = manager.download("test.en"), manager.download("test.en")
    assert manager.job("test.en") is job
    assert again["state"] == third["state"] == "downloading"
    gate.release(50)
    assert job.wait_state("installed")
    assert [r["range"] for r in server.gets()] == [None], "exactly one non-Range transfer"


# --- AC-18 -------------------------------------------------------------------

def test_pause_closes_the_connection_stops_done_and_resume_completes_by_range(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    manager.pause("test.en")
    gate.release(50)                    # let the server notice the closed socket
    assert job.wait_state("paused")
    wait_until(lambda: server.connections_open == 0)
    paused_at = job.snapshot()["done"]
    assert paused_at == os.path.getsize(world.final() + ".part") and 0 < paused_at < body.size
    time.sleep(0.05)
    assert job.snapshot()["done"] == paused_at, "done stops while paused"
    assert not job.thread.is_alive()
    manager.resume("test.en")
    assert job.wait_state("installed")
    assert server.gets()[-1]["range"] == "bytes=%d-" % paused_at
    assert read(world.final()) == body.data
    assert job.snapshot()["resumed_from"] == paused_at


# --- AC-19 -------------------------------------------------------------------

def test_cancel_while_active_ends_the_thread_and_removes_the_part(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    manager.cancel("test.en")
    gate.release(50)
    job.thread.join(10)
    assert not job.thread.is_alive()
    assert not os.path.exists(world.final() + ".part") and not os.path.exists(world.final())
    assert manager.snapshot("test.en")["state"] == "not_installed"
    assert manager.job("test.en") is None


def test_cancel_while_paused_removes_the_part_and_the_state_is_not_installed(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    job = manager.job("test.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    manager.pause("test.en")
    gate.release(50)
    assert job.wait_state("paused")
    assert os.path.exists(world.final() + ".part")
    manager.cancel("test.en")
    job.thread.join(10)
    assert not job.thread.is_alive()
    assert not os.path.exists(world.final() + ".part")
    assert manager.snapshot("test.en")["state"] == "not_installed"


# --- AC-20 -------------------------------------------------------------------

def test_a_new_manager_over_a_part_reports_partial_and_download_resumes_by_range(world):
    body = make_body(500_000)
    server = world.server({PATH: body})
    os.makedirs(world.stt_dir())
    with open(world.final() + ".part", "wb") as fh:
        fh.write(body.data[:123_456])
    manager = world.manager([stt_asset(server, body)])
    snap = manager.snapshot("test.en")
    assert snap["state"] == "partial" and snap["done"] == 123_456
    manager.download("test.en")
    job = manager.job("test.en")
    assert job.wait_state("installed")
    assert server.gets()[0]["range"] == "bytes=123456-"
    assert job.snapshot()["resumed_from"] == 123_456
    assert read(world.final()) == body.data


def test_cancel_on_a_partial_with_no_job_discards_the_part(world):
    body = make_body(100_000)
    server = world.server({PATH: body})
    os.makedirs(world.stt_dir())
    with open(world.final() + ".part", "wb") as fh:
        fh.write(body.data[:1000])
    manager = world.manager([stt_asset(server, body)])
    assert manager.cancel("test.en")["state"] == "not_installed"
    assert not os.path.exists(world.final() + ".part")


# --- failures persist, then resume --------------------------------------------

def test_a_failed_job_keeps_its_error_and_the_part_and_a_second_download_resumes(world):
    body = make_body(300_000)
    server = world.server({PATH: body}, status_script=[404])
    os.makedirs(world.stt_dir())
    with open(world.final() + ".part", "wb") as fh:
        fh.write(body.data[:100_000])
    manager = world.manager([stt_asset(server, body)])
    manager.download("test.en")
    failed = manager.job("test.en")
    assert failed.wait_state("failed")
    snap = manager.snapshot("test.en")
    assert snap["state"] == "failed" and "404" in snap["error"]
    assert os.path.getsize(world.final() + ".part") == 100_000
    manager.download("test.en")
    second = manager.job("test.en")
    assert second is not failed and second.wait_state("installed")
    assert server.gets()[-1]["range"] == "bytes=100000-"
    assert read(world.final()) == body.data


# --- voices: progress spans both files -----------------------------------------

def test_a_two_file_voice_reports_progress_across_both_files(world, monkeypatch):
    cfg, onnx = make_body(6_000, seed=8), make_body(300_000, seed=9)
    server = world.server({"/v/%s.onnx.json" % VOICE: cfg, "/v/%s.onnx" % VOICE: onnx})
    manager = world.manager([voice_asset(server, cfg, onnx)])
    calls = []
    original = voice_assets.Job.on_progress

    def record(self, done, total, name):
        calls.append((done, total, name))
        return original(self, done, total, name)

    monkeypatch.setattr(voice_assets.Job, "on_progress", record)
    assert manager.snapshot(VOICE)["file"] == ""
    manager.download(VOICE)
    job = manager.job(VOICE)
    assert job.wait_state("installed")
    total = cfg.size + onnx.size
    assert {c[1] for c in calls} == {total}
    dones = [c[0] for c in calls]
    assert dones == sorted(dones) and dones[-1] == total
    names = [c[2] for c in calls]
    assert names[0] == VOICE + ".onnx.json" and names[-1] == VOICE + ".onnx"
    first_onnx = names.index(VOICE + ".onnx")
    assert calls[first_onnx][0] >= cfg.size, "done already includes the whole config file"
    assert job.history == ["downloading", "verifying", "downloading", "verifying", "installed"]
    assert read_manifest(os.path.join(world.root, "desktop", "tts", VOICE + ".onnx"))["id"] == VOICE


# --- logging, ids, installed ----------------------------------------------------

def test_one_log_record_per_job_start_retry_finish_and_failure(world, caplog):
    body = make_body(100_000)
    server = world.server({PATH: body}, status_script=[503])
    manager = world.manager([stt_asset(server, body)])
    with caplog.at_level(logging.INFO, logger="console.voice_assets"):
        manager.download("test.en")
        assert manager.job("test.en").wait_state("installed")
    messages = [r.getMessage() for r in caplog.records]
    assert sum("download started" in m for m in messages) == 1
    assert sum("retry 1" in m for m in messages) == 1
    assert sum("finished" in m for m in messages) == 1

    caplog.clear()
    bad = world.server({PATH: body}, status_script=[403])
    other = world.manager([stt_asset(bad, body)], root=os.path.join(world.root, "second"))
    with caplog.at_level(logging.INFO, logger="console.voice_assets"):
        other.download("test.en")
        assert other.job("test.en").wait_state("failed")
    failures = [r.getMessage() for r in caplog.records if "failed" in r.getMessage()]
    assert len(failures) == 1 and "403" in failures[0]


@pytest.mark.parametrize("bad_id", ["nope", "https://huggingface.co/x.bin", "../x", "", None, 7])
def test_an_unknown_id_is_refused_without_any_request(world, bad_id):
    body = make_body(1000)
    server = world.server({PATH: body})
    manager = world.manager([stt_asset(server, body)])
    for verb in (manager.download, manager.pause, manager.resume, manager.cancel, manager.snapshot):
        with pytest.raises(KeyError):
            verb(bad_id)
    assert server.requests == []


def test_download_of_an_already_installed_asset_starts_nothing(world):
    body = make_body(1000)
    server = world.server({PATH: body})
    os.makedirs(world.stt_dir())
    with open(world.final(), "wb") as fh:
        fh.write(b"hand placed")
    manager = world.manager([stt_asset(server, body)])
    assert manager.download("test.en")["state"] == "installed"
    assert manager.job("test.en") is None and server.requests == []
    assert read(world.final()) == b"hand placed", "never silently replaced"
