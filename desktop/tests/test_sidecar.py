"""Sidecar start/reuse/stop. Uses an ephemeral port against this checkout."""

import json
import os
import socket
import subprocess
import sys

import pytest

DESKTOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(DESKTOP)
if DESKTOP not in sys.path:
    sys.path.insert(0, DESKTOP)

import sidecar  # noqa: E402


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestParseBind:
    def test_defaults_when_empty(self):
        assert sidecar.parse_bind("") == ("127.0.0.1", 8790)

    def test_reads_quoted_host_and_port(self):
        text = '[general]\nhost           = "10.0.0.8"\nport           = 9001\n'
        assert sidecar.parse_bind(text) == ("10.0.0.8", 9001)

    def test_ignores_commented_host(self):
        text = '# host = "1.2.3.4"\nport = 8123\n'
        host, port = sidecar.parse_bind(text)
        assert host == "127.0.0.1"
        assert port == 8123


class TestViewHost:
    def test_wildcard_becomes_loopback(self):
        assert sidecar.view_host("0.0.0.0") == "127.0.0.1"
        assert sidecar.view_host("::") == "127.0.0.1"


class TestRepoRoot:
    def test_finds_this_workspace(self):
        root = sidecar.find_repo_root(DESKTOP)
        assert os.path.isfile(os.path.join(root, "console", "kanban.py"))
        assert os.path.isdir(os.path.join(root, "knowledge-center"))

    def test_missing_root_raises(self):
        import tempfile
        outside = tempfile.mkdtemp(prefix="dc-sidecar-")
        try:
            with pytest.raises(sidecar.SidecarError):
                sidecar.find_repo_root(outside)
        finally:
            os.rmdir(outside)



class TestConsoleStaysStdlib:
    def test_no_package_managers_inside_console(self):
        console = os.path.join(REPO, "console")
        assert not os.path.isfile(os.path.join(console, "Cargo.toml"))
        assert not os.path.isfile(os.path.join(console, "package.json"))
        assert not os.path.isfile(os.path.join(console, "requirements.txt"))
        assert not os.path.isdir(os.path.join(console, "node_modules"))


class TestServeLogCapture:
    """`sidecar.py:124-130` — serve stdout/stderr land in `serve.log`
    instead of vanishing into DEVNULL."""

    def test_spawn_serve_redirects_to_the_log_file(self, monkeypatch, tmp_path):
        calls = []

        class _FakeProc:
            pid = 4242

        def fake_popen(cmd, **kwargs):
            calls.append(kwargs)
            return _FakeProc()

        monkeypatch.setattr(sidecar.subprocess, "Popen", fake_popen)
        root = str(tmp_path)
        os.makedirs(os.path.join(root, "console"), exist_ok=True)
        with open(os.path.join(root, "console", "kanban.py"), "w") as fh:
            fh.write("")

        sidecar.spawn_serve(root, "127.0.0.1", 8790)

        assert calls, "Popen was not called"
        kw = calls[0]
        assert kw["stdout"] is not subprocess.DEVNULL
        assert kw["stdout"] is kw["stderr"]
        assert kw["stdout"].name == os.path.join(root, sidecar.SERVE_LOG_REL)
        kw["stdout"].close()

    def test_a_log_directory_that_cannot_be_made_falls_back_to_devnull(
        self, monkeypatch, tmp_path
    ):
        def boom(*a, **kw):
            raise OSError("no permission")

        monkeypatch.setattr(sidecar.os, "makedirs", boom)
        handle = sidecar._serve_log_handle(str(tmp_path))
        assert handle is subprocess.DEVNULL


class TestKillTreeFlags:
    """`sidecar.py:152-159` — taskkill keeps its own inline
    `CREATE_NO_WINDOW`-equivalent constant, no import of `procs.py`."""

    def test_taskkill_carries_the_no_window_flag_on_nt(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(sidecar.subprocess, "run", fake_run)
        monkeypatch.setattr(sidecar.os, "name", "nt")
        sidecar.kill_tree(4242)
        assert calls
        assert calls[0]["creationflags"] & sidecar.CREATE_NO_WINDOW

    def test_module_does_not_import_procs(self):
        # A standalone-importable file must not reach into console/server —
        # the Tauri host shells it out with no console/ on sys.path.
        assert "procs" not in dir(sidecar)


class TestEnsureLive:
    def test_probe_closed_port_is_down(self):
        port = _free_port()
        assert sidecar.is_up("127.0.0.1", port) is False

    def test_spawn_answers_then_stop_frees_port(self):
        port = _free_port()
        handle = sidecar.ensure(REPO, host="127.0.0.1", port=port, wait_sec=60)
        try:
            assert handle.owned is True
            assert handle.pid
            assert sidecar.is_up("127.0.0.1", port)
            url = sidecar.server_url("127.0.0.1", port)
            assert handle.url == url
        finally:
            handle.stop()
        assert sidecar.is_up("127.0.0.1", port) is False

    def test_second_ensure_reuses_and_does_not_kill(self):
        port = _free_port()
        first = sidecar.ensure(REPO, host="127.0.0.1", port=port, wait_sec=60)
        try:
            second = sidecar.ensure(REPO, host="127.0.0.1", port=port, wait_sec=5)
            assert second.owned is False
            assert second.pid is None
            second.stop()
            assert sidecar.is_up("127.0.0.1", port) is True
        finally:
            first.stop()
        assert sidecar.is_up("127.0.0.1", port) is False


class TestBreakawayFallback:
    """A job object can forbid breakaway, and asking for it anyway fails the
    whole spawn with ERROR_ACCESS_DENIED — the server never starts.

    Found on GitHub's Windows runners, which put every process in such a job;
    the same applies to some managed corporate environments. It cannot be
    reproduced on an ordinary desktop, so these drive the fallback directly.
    """

    def _denied_once(self):
        """A Popen that refuses breakaway exactly as Windows does."""
        calls = []

        def popen(cmd, **kw):
            calls.append(kw.get("creationflags", 0))
            if kw.get("creationflags", 0) & sidecar.CREATE_BREAKAWAY_FROM_JOB:
                err = OSError("Access is denied")
                err.winerror = 5
                raise err
            return "spawned"

        return popen, calls

    @pytest.mark.skipif(os.name != "nt", reason="Windows creation flags")
    def test_a_refused_breakaway_retries_without_it(self, monkeypatch):
        popen, calls = self._denied_once()
        monkeypatch.setattr(sidecar.subprocess, "Popen", popen)
        base = sidecar.subprocess.CREATE_NEW_PROCESS_GROUP | sidecar.CREATE_NO_WINDOW
        out = sidecar._spawn_with_breakaway_fallback(
            ["x"], {"creationflags": base | sidecar.CREATE_BREAKAWAY_FROM_JOB}, base)
        assert out == "spawned", "the server must still start"
        assert len(calls) == 2, "it should have retried"
        assert not calls[1] & sidecar.CREATE_BREAKAWAY_FROM_JOB
        # The flags that matter for hygiene survive the retry.
        assert calls[1] & sidecar.CREATE_NO_WINDOW

    @pytest.mark.skipif(os.name != "nt", reason="Windows creation flags")
    def test_an_unrelated_error_is_not_retried(self, monkeypatch):
        def popen(cmd, **kw):
            err = OSError("no such file")
            err.winerror = 2
            raise err

        monkeypatch.setattr(sidecar.subprocess, "Popen", popen)
        base = sidecar.CREATE_NO_WINDOW
        with pytest.raises(OSError):
            sidecar._spawn_with_breakaway_fallback(
                ["x"], {"creationflags": base | sidecar.CREATE_BREAKAWAY_FROM_JOB}, base)

    @pytest.mark.skipif(os.name != "nt", reason="Windows creation flags")
    def test_a_retry_that_also_fails_reports_the_original_cause(self, monkeypatch):
        def popen(cmd, **kw):
            err = OSError("Access is denied")
            err.winerror = 5
            raise err

        monkeypatch.setattr(sidecar.subprocess, "Popen", popen)
        base = sidecar.CREATE_NO_WINDOW
        with pytest.raises(OSError) as caught:
            sidecar._spawn_with_breakaway_fallback(
                ["x"], {"creationflags": base | sidecar.CREATE_BREAKAWAY_FROM_JOB}, base)
        assert caught.value.winerror == 5


class _FakeConfig:
    """A loopback server that answers `/api/config` with a fixed body, so
    `ensure()`'s attach path runs against something that is not a real
    console. `body` is raw bytes; `None` answers 404."""

    def __init__(self, body):
        import http.server
        import threading

        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                if outer.body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(outer.body)

            def log_message(self, *args):
                pass

        self.body = body
        self.hits = 0
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake():
    made = []

    def make(payload):
        body = payload if isinstance(payload, (bytes, type(None))) else json.dumps(payload).encode("utf-8")
        srv = _FakeConfig(body)
        made.append(srv)
        return srv

    yield make
    for srv in made:
        srv.close()


class TestWorkspaceCheck:
    """T-036 task 20: do not attach to a server that serves another checkout."""

    def test_different_workspace_is_refused_with_both_ids(self, fake):
        srv = fake({"workspace": "000000000000"})
        with pytest.raises(sidecar.SidecarError) as err:
            sidecar.ensure(REPO, host="127.0.0.1", port=srv.port, wait_sec=2)
        msg = str(err.value)
        assert "different workspace" in msg
        assert "000000000000" in msg and sidecar.workspace_id(REPO) in msg
        assert str(srv.port) in msg

    def test_equal_workspace_attaches_without_owning(self, fake):
        srv = fake({"workspace": sidecar.workspace_id(REPO)})
        handle = sidecar.ensure(REPO, host="127.0.0.1", port=srv.port, wait_sec=2)
        assert handle.owned is False and handle.pid is None
        assert handle.url == sidecar.server_url("127.0.0.1", srv.port)

    def test_absent_workspace_attaches_an_older_server(self, fake):
        srv = fake({"title": "old console"})
        handle = sidecar.ensure(REPO, host="127.0.0.1", port=srv.port, wait_sec=2)
        assert handle.owned is False

    @pytest.mark.parametrize("body", [b"not json at all", b"[1, 2]", b'{"workspace": 7}', b'{"workspace": ""}'])
    def test_unreadable_or_malformed_answer_attaches(self, fake, body):
        srv = fake(body)
        assert sidecar.served_workspace("127.0.0.1", srv.port) is None
        assert sidecar.ensure(REPO, host="127.0.0.1", port=srv.port, wait_sec=2).owned is False

    def test_is_up_and_probe_stay_pure_liveness_probes(self, fake):
        srv = fake({"workspace": "000000000000"})
        assert sidecar.is_up("127.0.0.1", srv.port) is True
        assert srv.hits == 1, "is_up must make one request and no workspace comparison"
        assert sidecar.is_up("127.0.0.1", _free_port()) is False
        import inspect
        assert "workspace" not in inspect.getsource(sidecar.is_up)
        if hasattr(sidecar, "probe"):
            assert "workspace" not in inspect.getsource(sidecar.probe)

    def test_cli_ensure_prints_the_refusal_on_stderr_and_exits_nonzero(self, fake):
        # What the Tauri shell reads (sidecar.rs:110-121): stderr, trimmed.
        srv = fake({"workspace": "000000000000"})
        run = subprocess.run(
            [sys.executable, os.path.join(DESKTOP, "sidecar.py"), "ensure",
             "--root", REPO, "--host", "127.0.0.1", "--port", str(srv.port)],
            capture_output=True, text=True, timeout=30)
        assert run.returncode != 0
        assert "different workspace" in run.stderr
        assert run.stdout.strip() == ""

    def test_workspace_id_matches_the_servers_helper(self, tmp_path):
        sys.path.insert(0, os.path.join(REPO, "console"))
        try:
            from server.features import shell_feature
        finally:
            sys.path.remove(os.path.join(REPO, "console"))
        for root in (REPO, str(tmp_path)):
            assert sidecar.workspace_id(root) == shell_feature._workspace_id(root)

    def test_sidecar_source_imports_nothing_from_console(self):
        import re as _re
        with open(os.path.join(DESKTOP, "sidecar.py"), encoding="utf-8") as fh:
            src = fh.read()
        assert not _re.search(r"^\s*(import|from)\s+(server|console)", src, _re.M)

    def test_live_server_reports_the_checkout_id_ensure_compares_against(self):
        port = _free_port()
        first = sidecar.ensure(REPO, host="127.0.0.1", port=port, wait_sec=60)
        try:
            assert sidecar.served_workspace("127.0.0.1", port) == sidecar.workspace_id(REPO)
        finally:
            first.stop()
