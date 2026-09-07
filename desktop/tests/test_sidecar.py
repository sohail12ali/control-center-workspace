"""Sidecar start/reuse/stop. Uses an ephemeral port against this checkout."""

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
