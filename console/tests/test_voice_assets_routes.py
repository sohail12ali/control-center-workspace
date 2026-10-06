"""T-031 task 14: the voice-asset HTTP surface (AC-12, AC-33; NFR-3, NFR-4).

Seven routes on the Assistant plugin: `GET /api/assistant/voice/assets` and
`POST .../assets/{download,pause,resume,cancel,delete,verify}`. The engine
behind them (catalog, downloader, jobs, inventory, delete) has its own test
files; what is tested here is the seam: that a request can only NAME an asset,
that every mutation is audited once, that a refusal is a 400 and never a 5xx,
that jobs outlive a request, and that listing stays quick with downloads
running.

No real network: a local range-capable server, an injected downloader, and
`urllib.request.urlopen` patched to fail wherever a test claims "no call".
"""

import inspect
import json
import os
import random
import re
import threading
import time
import types
import urllib.request

import pytest

from voice_assets_server import Body, RangeServer
from server import audit, voice_assets
from server.features import assistant_feature
from server.voice_assets import Asset, AssetFile, Catalog, Downloader, Manager

CHUNK = 65536
NAME = "ggml-one.bin"
PATH = "/m/" + NAME


class Req:
    def __init__(self, body=None):
        self.body = body if body is not None else {}
        self.query = {}
        self.client_addr = "10.0.0.5"
        self.user_agent = "pytest"


class Gate:
    """Lets the server send one chunk per `release()`."""

    def __init__(self):
        self.sem = threading.Semaphore(0)

    def __call__(self, sent):
        assert self.sem.acquire(timeout=10), "the test never released the server"

    def release(self, n=1):
        self.sem.release(n)


def make_body(size, seed=4):
    return Body(random.Random(seed).randbytes(size))


def wait_until(predicate, timeout=10.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "timed out waiting for the condition"
        time.sleep(0.002)


def make_asset(server, asset_id="one.en", path=PATH, name=NAME, body=None):
    return Asset(id=asset_id, kind="stt", label=asset_id, repo="a/b", commit="c" * 40,
                 hint="1 MiB / 1 MB", license="mit",
                 files=(AssetFile(name=name, url=server.url(path), size=body.size,
                                  sha256=body.sha256(), hash_source="hf-lfs-oid"),))


@pytest.fixture
def world(repo):
    servers, gates = [], []
    routes = assistant_feature.handlers(repo)

    class World:
        root = repo

        def server(self, files, gate=None, **kw):
            s = RangeServer(files, chunk=CHUNK, gate=gate, **kw).start()
            servers.append(s)
            if gate is not None:
                gates.append(gate)
            return s

        def install(self, assets, opener=None):
            """Seed the registry with a manager over these assets, so the
            routes (which look it up per request) use it."""
            def factory(root):
                downloader = Downloader(opener=opener, allow_loopback_http=True,
                                        sleep=lambda s: None,
                                        disk_free=lambda p: 1 << 40)
                return Manager(root, catalog=Catalog(assets=tuple(assets)),
                               downloader=downloader)
            return voice_assets.manager_for(repo, factory=factory)

        def act(self, action, body=None):
            return routes["assistant.voice_asset_" + action](Req(body))

        def assets(self):
            return routes["assistant.voice_assets"](Req())

        def row(self, asset_id):
            (found,) = [r for r in self.assets()["assets"] if r["id"] == asset_id]
            return found

        def stt_dir(self):
            return os.path.join(repo, "desktop", "stt")

        def place(self, name, data, directory=None):
            directory = directory or self.stt_dir()
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, name), "wb") as fh:
                fh.write(data)

        def audit(self, action):
            return audit.read(repo, action="assistant.voice_asset." + action)

    yield World()
    for gate in gates:
        gate.release(10_000)
    voice_assets.drop_manager(repo)
    for server in servers:
        server.stop()
    alive = [t.name for t in threading.enumerate()
             if t.name.startswith("voice-asset-") and t.is_alive()]
    assert alive == [], "a job thread outlived its test: %s" % alive


def _forbid_network(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("a network call was made")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    return forbidden, calls


# --- AC-12: a request names an asset, nothing else ----------------------------

@pytest.mark.parametrize("action", ["download", "pause", "resume", "cancel",
                                    "verify", "delete"])
def test_an_unknown_id_is_refused_with_no_network_call(world, monkeypatch, action):
    forbidden, calls = _forbid_network(monkeypatch)
    body = make_body(1000)
    server = world.server({PATH: body})
    world.install([make_asset(server, body=body)], opener=forbidden)
    with pytest.raises(ValueError, match="no model or voice"):
        world.act(action, {"id": "no-such.en"})
    assert calls == []
    assert server.requests == []


@pytest.mark.parametrize("bad", [
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    "http://127.0.0.1:9/evil.bin", "../../etc/passwd", "..\\..\\x", "C:\\Windows\\x",
    "a/b", "", "   ", None, 5, ["one.en"], {"id": "one.en"}])
def test_something_that_is_not_a_catalog_id_is_refused_by_every_route(world, monkeypatch, bad):
    forbidden, calls = _forbid_network(monkeypatch)
    body = make_body(1000)
    server = world.server({PATH: body})
    world.install([make_asset(server, body=body)], opener=forbidden)
    world.place(NAME, body.data)                  # something a delete could hit
    for action in ("download", "pause", "resume", "cancel", "verify", "delete"):
        with pytest.raises(ValueError):
            world.act(action, {"id": bad})
    assert calls == [] and server.requests == []
    assert os.listdir(world.stt_dir()) == [NAME]


def test_an_empty_body_names_nothing_and_is_refused(world):
    body = make_body(1000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    for action in ("download", "pause", "resume", "cancel", "verify", "delete"):
        with pytest.raises(ValueError, match="say which model or voice"):
            world.act(action, {})


def test_url_path_file_and_filename_in_the_body_change_nothing(world):
    body = make_body(300_000)
    server = world.server({PATH: body})
    decoy = world.server({"/evil.bin": make_body(1000, seed=9)})
    manager = world.install([make_asset(server, body=body)])
    answer = world.act("download", {
        "id": "one.en", "url": decoy.url("/evil.bin"), "path": "../../../evil.bin",
        "file": "evil.bin", "filename": "ggml-evil.bin", "dest": "C:\\evil",
        "source_url": decoy.url("/evil.bin")})
    assert answer["ok"] is True and answer["asset"]["id"] == "one.en"
    assert manager.job("one.en").wait_state("installed")
    assert [r["path"] for r in server.gets()] == [PATH], "the URL is the catalog's"
    assert decoy.requests == [], "the body's URL was never contacted"
    assert sorted(os.listdir(world.stt_dir())) == [NAME, NAME + ".manifest.json"]
    assert not os.path.exists(os.path.join(world.root, "evil.bin"))


# --- the happy path, through the routes ---------------------------------------

def test_download_through_the_route_installs_a_verified_file_and_the_list_shows_it(world):
    body = make_body(400_000)
    manager = world.install([make_asset(world.server({PATH: body}), body=body)])
    assert world.row("one.en")["state"] == "not_installed"
    answer = world.act("download", {"id": "one.en"})
    assert answer["ok"] is True and answer["asset"]["state"] in ("downloading", "verifying", "installed")
    assert manager.job("one.en").wait_state("installed")
    row = world.row("one.en")
    assert row["state"] == "installed" and row["verified"] is True
    assert row["done"] == row["total"] == body.size
    with open(os.path.join(world.stt_dir(), NAME), "rb") as fh:
        assert fh.read() == body.data


def test_pause_and_resume_work_through_the_routes(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    world.act("download", {"id": "one.en"})
    job = manager.job("one.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    paused = world.act("pause", {"id": "one.en"})
    assert paused["ok"] is True
    gate.release(50)
    assert job.wait_state("paused")
    assert world.row("one.en")["state"] == "paused"
    resumed = world.act("resume", {"id": "one.en"})
    assert resumed["ok"] is True
    assert job.wait_state("installed")
    assert server.gets()[-1]["range"] is not None, "resume reconnects with Range"
    assert world.row("one.en")["verified"] is True


def test_cancel_through_the_route_removes_the_partial_file(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    world.act("download", {"id": "one.en"})
    job = manager.job("one.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    world.act("cancel", {"id": "one.en"})
    gate.release(50)
    job.thread.join(10)
    assert not job.thread.is_alive()
    assert world.row("one.en")["state"] == "not_installed"
    assert not os.path.exists(os.path.join(world.stt_dir(), NAME + ".part"))


# --- AC-33: one audit record per action, with the id as the target ------------

def test_download_writes_exactly_one_audit_record_and_pause_resume_and_get_write_none(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    world.assets()
    world.act("download", {"id": "one.en"})
    job = manager.job("one.en")
    gate.release(2)
    wait_until(lambda: job.snapshot()["done"] >= 2 * CHUNK)
    world.act("pause", {"id": "one.en"})
    gate.release(50)
    assert job.wait_state("paused")
    world.act("resume", {"id": "one.en"})
    assert job.wait_state("installed")
    world.assets()
    (record,) = world.audit("download")
    assert record["action"] == "assistant.voice_asset.download"
    assert record["target"] == "one.en"
    assert record["actor"]["addr"] == "10.0.0.5"
    assert audit.read(world.root, limit=50, action="assistant.voice_asset.pause") == []
    assert audit.read(world.root, limit=50, action="assistant.voice_asset.resume") == []
    every = [r for r in audit.read(world.root, limit=50)
             if r["action"].startswith("assistant.voice_asset.")]
    assert len(every) == 1, "pause, resume and the listing are not audited"


def test_cancel_writes_exactly_one_audit_record_with_the_id(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    world.act("download", {"id": "one.en"})
    job = manager.job("one.en")
    gate.release(1)
    wait_until(lambda: job.snapshot()["done"] >= CHUNK)
    world.act("cancel", {"id": "one.en"})
    gate.release(50)
    job.thread.join(10)
    (record,) = world.audit("cancel")
    assert record["target"] == "one.en" and record["outcome"] == "ok"
    assert len(world.audit("download")) == 1


def test_delete_removes_the_asset_and_writes_exactly_one_audit_record(world):
    body = make_body(300_000)
    manager = world.install([make_asset(world.server({PATH: body}), body=body)])
    world.act("download", {"id": "one.en"})
    assert manager.job("one.en").wait_state("installed")
    # A smaller model on disk is what the shell falls back to, so `one.en`
    # is not the one in use and may be deleted.
    world.place("ggml-fallback.bin", b"x" * 10)
    answer = world.act("delete", {"id": "one.en"})
    assert answer["ok"] is True
    assert sorted(answer["removed"]) == [NAME, NAME + ".manifest.json"]
    assert os.listdir(world.stt_dir()) == ["ggml-fallback.bin"]
    assert world.row("one.en")["state"] == "not_installed"
    (record,) = world.audit("delete")
    assert record["target"] == "one.en" and record["outcome"] == "ok"
    assert record["detail"]["removed"] == answer["removed"]


def test_delete_of_an_asset_in_use_is_a_400_with_the_reason_and_deletes_nothing(world):
    body = make_body(5000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place(NAME, body.data)                  # the only model, so in use
    with pytest.raises(ValueError, match="in use"):
        world.act("delete", {"id": "one.en"})
    assert os.listdir(world.stt_dir()) == [NAME]
    (record,) = world.audit("delete")
    assert record["target"] == "one.en" and record["outcome"] == "refused"


def test_delete_accepts_an_inventory_name_for_a_file_the_catalog_does_not_list(world):
    body = make_body(5000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place("ggml-aaa.bin", b"x" * 10)        # smallest: the one in use
    world.place("ggml-mine.bin", b"y" * 500)      # custom, not in use
    answer = world.act("delete", {"name": "ggml-mine.bin"})
    assert answer["ok"] is True and answer["removed"] == ["ggml-mine.bin"]
    assert os.listdir(world.stt_dir()) == ["ggml-aaa.bin"]
    (record,) = world.audit("delete")
    assert record["target"] == "ggml-mine.bin"


def test_a_traversal_name_is_refused_deletes_nothing_and_is_not_audited(world):
    body = make_body(5000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    canary = os.path.join(world.root, "canary.txt")
    with open(canary, "w", encoding="utf-8") as fh:
        fh.write("keep")
    world.place("ggml-aaa.bin", b"x" * 10)
    for name in ("../canary.txt", "..\\..\\canary.txt", "canary.txt", "a/b",
                 os.path.abspath(canary)):
        with pytest.raises(ValueError):
            world.act("delete", {"id": name})
        with pytest.raises(ValueError):
            world.act("delete", {"name": name})
    assert os.path.isfile(canary)
    assert os.listdir(world.stt_dir()) == ["ggml-aaa.bin"]
    assert world.audit("delete") == [], "a name that matches no asset is not an asset event"


def test_verify_writes_the_manifest_for_a_matching_hand_placed_file_and_audits_it(world):
    body = make_body(50_000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place(NAME, body.data)
    row = world.row("one.en")
    assert row["state"] == "installed" and row["verified"] is False
    answer = world.act("verify", {"id": "one.en"})
    assert answer["ok"] is True and answer["id"] == "one.en"
    assert os.path.isfile(os.path.join(world.stt_dir(), NAME + ".manifest.json"))
    assert world.row("one.en")["verified"] is True
    (record,) = world.audit("verify")
    assert record["target"] == "one.en" and record["outcome"] == "ok"


def test_verify_reports_a_mismatch_as_a_result_and_leaves_the_file_alone(world):
    body = make_body(50_000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place(NAME, b"z" * body.size)           # right length, wrong bytes
    path = os.path.join(world.stt_dir(), NAME)
    before = os.stat(path).st_mtime_ns
    answer = world.act("verify", {"id": "one.en"})        # not an exception
    assert answer["ok"] is False and "sha256 mismatch" in answer["message"]
    assert os.stat(path).st_mtime_ns == before
    with open(path, "rb") as fh:
        assert fh.read() == b"z" * body.size
    assert not os.path.exists(path + ".manifest.json")
    assert world.row("one.en")["verified"] is False
    (record,) = world.audit("verify")
    assert record["outcome"] == "mismatch"


def test_verify_of_a_file_the_os_will_not_let_us_read_is_a_400_not_a_5xx(world, monkeypatch):
    body = make_body(5000)
    world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place(NAME, body.data)

    def locked(path, on_bytes=None):
        raise PermissionError(13, "Permission denied", path)
    monkeypatch.setattr(voice_assets, "sha256_of", locked)
    with pytest.raises(ValueError, match="could not read one.en"):
        world.act("verify", {"id": "one.en"})
    assert world.audit("verify") == []


def test_verify_is_refused_while_the_asset_is_downloading(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    world.act("download", {"id": "one.en"})
    gate.release(1)
    wait_until(lambda: manager.job("one.en").snapshot()["done"] >= CHUNK)
    with pytest.raises(ValueError, match="being downloaded"):
        world.act("verify", {"id": "one.en"})
    assert world.audit("verify") == []


# --- the listing --------------------------------------------------------------

def test_get_assets_equals_the_inventory_and_carries_no_url_or_path(world):
    body = make_body(5000)
    manager = world.install([make_asset(world.server({PATH: body}), body=body)])
    world.place("ggml-mine.bin", b"y" * 500)
    answer = world.assets()
    expected = voice_assets.inventory(world.root, manager.catalog, manager=manager)
    # Free disk space moves between two calls; everything else is identical.
    assert isinstance(answer.pop("free_bytes"), int)
    expected.pop("free_bytes")
    assert answer == expected
    assert sorted(answer) == ["assets", "shell"]
    assert answer["shell"]["reachable"] is False
    assert [r["id"] for r in answer["assets"]] == ["one.en", "mine"]
    text = json.dumps(answer)
    assert "http" not in text and "desktop" not in text


def test_get_assets_p95_is_under_250_ms_with_two_active_downloads_and_no_shell(world):
    real = voice_assets.load_catalog()
    bodies = {"slow1.en": make_body(8 * CHUNK, seed=1), "slow2.en": make_body(8 * CHUNK, seed=2)}
    gates = {key: Gate() for key in bodies}
    extra = []
    for key, body in bodies.items():
        server = world.server({"/m/ggml-%s.bin" % key: body}, gate=gates[key])
        extra.append(make_asset(server, key, "/m/ggml-%s.bin" % key, "ggml-%s.bin" % key, body))
    manager = world.install(list(real.assets) + extra)
    for key in bodies:
        world.act("download", {"id": key})
        gates[key].release(2)
    wait_until(lambda: all(manager.snapshot(k)["done"] >= 2 * CHUNK for k in bodies))
    times = []
    for _ in range(50):
        started = time.perf_counter()
        answer = world.assets()
        times.append(time.perf_counter() - started)
    assert answer["shell"]["reachable"] is False
    assert len(answer["assets"]) == len(real.assets) + 2
    states = {r["id"]: r["state"] for r in answer["assets"]}
    assert states["slow1.en"] == states["slow2.en"] == "downloading"
    times.sort()
    p95 = times[int(len(times) * 0.95)]
    print("GET assets x%d, two downloads active: median %.1f ms, p95 %.1f ms, max %.1f ms"
          % (len(times), times[len(times) // 2] * 1000, p95 * 1000, times[-1] * 1000))
    assert p95 < 0.25, "p95 %.1f ms, max %.1f ms" % (p95 * 1000, times[-1] * 1000)
    for key in bodies:
        world.act("cancel", {"id": key})
        gates[key].release(100)
        manager.job(key).thread.join(10)


# --- jobs outlive a request; the registry ------------------------------------

def test_the_cli_path_shares_one_manager_so_a_job_outlives_a_call(world):
    body = make_body(8 * CHUNK)
    gate = Gate()
    server = world.server({PATH: body}, gate=gate)
    manager = world.install([make_asset(server, body=body)])
    # `call` rebuilds the capture ctx (and so every closure) each time.
    started = assistant_feature.call(world.root, "assistant.voice_asset_download",
                                     {"id": "one.en"})
    assert started["ok"] is True
    gate.release(2)
    wait_until(lambda: manager.snapshot("one.en")["done"] >= 2 * CHUNK)
    listed = assistant_feature.call(world.root, "assistant.voice_assets")
    (row,) = [r for r in listed["assets"] if r["id"] == "one.en"]
    assert row["state"] == "downloading" and row["done"] >= 2 * CHUNK
    assert voice_assets.manager_for(world.root) is manager
    assert len(server.gets()) == 1, "one transfer, not one per call"
    assistant_feature.call(world.root, "assistant.voice_asset_cancel", {"id": "one.en"})
    gate.release(100)
    manager.job("one.en").thread.join(10)


def test_manager_for_is_one_per_root_and_drop_manager_stops_it(tmp_path):
    stopped = []
    first_root, second_root = str(tmp_path / "a"), str(tmp_path / "b")
    made = []

    def factory(root):
        manager = types.SimpleNamespace(root=root, stop_all=lambda: stopped.append(root))
        made.append(manager)
        return manager

    a = voice_assets.manager_for(first_root, factory=factory)
    assert voice_assets.manager_for(first_root) is a
    assert voice_assets.manager_for(os.path.join(first_root, ".")) is a, "same root, same manager"
    b = voice_assets.manager_for(second_root, factory=factory)
    assert b is not a and len(made) == 2
    voice_assets.drop_manager(first_root)
    voice_assets.drop_manager(second_root)
    voice_assets.drop_manager(second_root)       # dropping twice is harmless
    assert stopped == [first_root, second_root]
    c = voice_assets.manager_for(first_root, factory=factory)
    assert c is not a, "a dropped root gets a fresh manager"
    voice_assets.drop_manager(first_root)


# --- the plugin surface -------------------------------------------------------

def test_each_url_resolves_to_exactly_its_own_route_through_the_real_router(repo):
    """The other tests call handlers directly; this one proves the URL regexes."""
    from server.plugins.base import PluginContext, Router
    router = Router()
    assistant_feature.apply(PluginContext(repo, {}, router))
    table = router.describe()

    def names(method, path):
        return [r["name"] for r in table
                if r["method"] == method and re.match(r["pattern"], path)]

    assert names("GET", "/api/assistant/voice/assets") == ["assistant.voice_assets"]
    assert names("GET", "/api/assistant/voice/assets/") == ["assistant.voice_assets"]
    for action in ("download", "pause", "resume", "cancel", "delete", "verify"):
        url = "/api/assistant/voice/assets/" + action
        assert names("POST", url) == ["assistant.voice_asset_" + action], action
        assert names("GET", url) == [], "%s is POST only" % action
    assert names("POST", "/api/assistant/voice/assets") == [], "the listing is GET only"
    assert names("POST", "/api/assistant/voice/assets/bogus") == []
    assert names("POST", "/api/assistant/voice/assets/download/x") == []
    assert names("GET", "/api/assistant/voice") == ["assistant.voice_state"], \
        "the diagnostics route is untouched"


def test_handlers_still_build_with_the_capture_ctx_and_no_new_ctx_method(repo):
    names = assistant_feature.handlers(repo)
    wanted = {"assistant.voice_assets"} | {
        "assistant.voice_asset_" + a
        for a in ("download", "pause", "resume", "cancel", "delete", "verify")}
    assert wanted <= set(names)
    # What `apply` asks of its ctx; the CLI's capture ctx implements only these.
    used = set(re.findall(r"\bctx\.(\w+)", inspect.getsource(assistant_feature.apply)))
    assert used <= {"get", "post", "register_tab", "repo_root"}, used
    capture = {n for n in vars(assistant_feature._CaptureCtx) if not n.startswith("_")}
    assert capture == {"get", "post", "register_tab"}
