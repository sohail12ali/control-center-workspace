"""Real-process proof that `procs.kill_tree` reaches a whole agent tree (T-020
FR-9, NFR-3, NFR-11). The fake CLI is `sys.executable` running a small script:
root -> child -> grandchild, each sleeping a bounded 30 s, each recording its
pid in a file and carrying a unique `T020-TREE-<uuid>` marker in its command
line, so a leftover is findable:

    Get-CimInstance Win32_Process | Where-Object CommandLine -match 'T020-TREE'

Reach limit: a grandchild whose parent exited BEFORE the kill is out of reach
of `taskkill /T` (the parent link is gone). These tests kill while the whole
chain is alive.

Safety: every recorded pid is force-killed in fixture teardown, even when the
test aborts. Only pids this test started are ever touched.
"""

import os
import subprocess
import sys
import time
import uuid

import pytest

from server import agent_session, procs
from server.agent_events import Stream

_SCRIPT = r"""
import os, subprocess, sys, time
role, pidfile = sys.argv[1], sys.argv[2]
flags = 0x08000000 if os.name == "nt" else 0
with open(pidfile, "a") as f:
    f.write("%s %d\n" % (role, os.getpid()))
nxt = {"root": "child", "child": "grandchild"}.get(role)
if nxt:
    subprocess.Popen([sys.executable, __file__, nxt, pidfile, sys.argv[3]],
                     creationflags=flags)
time.sleep(30)
"""


def _alive(pid):
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        h = k32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code))) \
                and code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(ctypes.c_void_p(h))
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    # A zombie still answers signal 0; treat it as gone.
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def _force_kill(pid):
    if not _alive(pid):
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=procs.CREATE_NO_WINDOW, check=False)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _pids(pidfile):
    try:
        with open(pidfile) as f:
            return dict(line.split() for line in f.read().splitlines() if line.strip())
    except OSError:
        return {}


def _wait(cond, secs):
    end = time.monotonic() + secs
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


class _PidAdapter:
    """Just enough of a Popen for `kill_tree`, for a process we did not spawn."""

    def __init__(self, pid):
        self.pid = pid

    def poll(self):
        return None if _alive(self.pid) else 0

    def wait(self, timeout=None):
        if not _wait(lambda: not _alive(self.pid), timeout or 0):
            raise subprocess.TimeoutExpired("pid %d" % self.pid, timeout)
        return 0


class _Backend:
    id = "fake"
    label = "Fake"
    transport = "stream_json"
    default_mode = "default"
    resumable = False

    def __init__(self, argv):
        self._argv = argv

    def session_argv(self, **kw):
        return list(self._argv)


@pytest.fixture
def tree(tmp_path):
    marker = "T020-TREE-" + uuid.uuid4().hex
    script = tmp_path / "fake_cli.py"
    script.write_text("# %s\n%s" % (marker, _SCRIPT), encoding="utf-8")
    pidfile = str(tmp_path / "pids.txt")
    argv = [sys.executable, str(script), "root", pidfile, marker]
    spawned = []
    yield argv, pidfile, spawned
    # Teardown runs on pass, fail and abort: kill the recorded tree, then
    # every recorded pid, then anything we spawned directly.
    for p in spawned:
        try:
            procs.kill_tree(p, grace=0.5)
        except Exception:
            pass
    for pid in _pids(pidfile).values():
        _force_kill(int(pid))


class TestProcessTree:
    def test_kill_tree_leaves_no_orphan_root_child_or_grandchild(self, tree, tmp_path):
        argv, pidfile, _ = tree
        sess = agent_session.LiveSession(
            "t020", _Backend(argv), str(tmp_path), Stream("t020"))
        sess.start()
        assert _wait(lambda: len(_pids(pidfile)) == 3, 5), _pids(pidfile)
        pids = {k: int(v) for k, v in _pids(pidfile).items()}
        assert all(_alive(p) for p in pids.values())

        sess.kill_process(grace=1.0)

        assert _wait(lambda: not any(_alive(p) for p in pids.values()), 10), \
            {k: _alive(p) for k, p in pids.items()}

    @pytest.mark.skipif(os.name != "nt", reason="Windows has no process-group kill")
    def test_windows_control_plain_kill_leaves_grandchild_alive(self, tree):
        argv, pidfile, spawned = tree
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                **procs.tree_spawn_kwargs())
        spawned.append(proc)
        assert _wait(lambda: len(_pids(pidfile)) == 3, 5), _pids(pidfile)
        pids = {k: int(v) for k, v in _pids(pidfile).items()}

        proc.kill()  # the old behaviour: root only
        proc.wait(timeout=5)

        assert _alive(pids["grandchild"]), "plain kill unexpectedly took the grandchild"
        # Clean up through the real tree kill on the surviving child.
        procs.kill_tree(_PidAdapter(pids["child"]), grace=1.0)
        assert _wait(lambda: not any(_alive(p) for p in pids.values()), 10)
