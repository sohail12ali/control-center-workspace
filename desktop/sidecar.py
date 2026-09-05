"""Start, probe, and stop `python console/kanban.py serve` for the desktop shell.

Stdlib only. The GUI host (Tauri) shells out to this file so spawn
and shutdown stay in one place and can be tested without a window.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790
READY_PATH = "/api/config"
READY_TIMEOUT_SEC = 45.0
PROBE_TIMEOUT_SEC = 0.5


class SidecarError(RuntimeError):
    pass


def _walk_to_root(start):
    path = os.path.abspath(start)
    while True:
        kanban = os.path.join(path, "console", "kanban.py")
        kc = os.path.join(path, "knowledge-center")
        if os.path.isfile(kanban) and os.path.isdir(kc):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise SidecarError(
                "no workspace root found (need knowledge-center/ and console/kanban.py)"
            )
        path = parent


def find_repo_root(start=None):
    """A root is knowledge-center/ plus console/kanban.py as siblings.

    When `start` is set, only that path is walked (so tests can point at an
    empty tree). Otherwise cwd, then this file's directory.
    """
    if start:
        return _walk_to_root(start)
    here = os.path.dirname(os.path.abspath(__file__))
    errors = []
    for candidate in (os.getcwd(), here, os.path.dirname(here)):
        try:
            return _walk_to_root(candidate)
        except SidecarError as err:
            errors.append(err)
    raise errors[-1]


def parse_bind(toml_text):
    """Host and port from console.toml [general]. Missing keys → defaults."""
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    m = re.search(r'(?m)^\s*host\s*=\s*"([^"]*)"', toml_text)
    if m:
        host = m.group(1).strip() or DEFAULT_HOST
    m = re.search(r"(?m)^\s*port\s*=\s*(\d+)", toml_text)
    if m:
        port = int(m.group(1))
    return host, port


def read_bind(repo_root):
    path = os.path.join(repo_root, "console", "config", "console.toml")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return parse_bind(fh.read())
    except OSError:
        return DEFAULT_HOST, DEFAULT_PORT


def view_host(bind_host):
    if bind_host in ("0.0.0.0", "::", "*"):
        return "127.0.0.1"
    return bind_host or DEFAULT_HOST


def server_url(bind_host, port):
    return "http://%s:%d" % (view_host(bind_host), int(port))


def is_up(bind_host, port, timeout=PROBE_TIMEOUT_SEC):
    url = server_url(bind_host, port) + READY_PATH
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
        return False


def python_cmd():
    env = os.environ.get("PYTHON")
    if env:
        return [env]
    return [sys.executable]


def spawn_serve(repo_root, bind_host, port):
    kanban = os.path.join(repo_root, "console", "kanban.py")
    if not os.path.isfile(kanban):
        raise SidecarError("missing %s" % kanban)
    cmd = python_cmd() + [
        kanban, "serve",
        "--host", view_host(bind_host),
        "--port", str(int(port)),
    ]
    flags = 0
    popen_kw = dict(
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    if os.name == "nt":
        CREATE_NO_WINDOW = 0x08000000
        CREATE_BREAKAWAY_FROM_JOB = 0x01000000
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | CREATE_NO_WINDOW
            | CREATE_BREAKAWAY_FROM_JOB
        )
        popen_kw["creationflags"] = flags
    else:
        popen_kw["start_new_session"] = True
    try:
        return subprocess.Popen(cmd, **popen_kw)
    except OSError as e:
        raise SidecarError("could not start serve: %s" % e) from e


def kill_tree(pid):
    if not pid:
        return
    pid = int(pid)
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


class Handle:
    __slots__ = ("url", "owned", "pid", "bind_host", "port")

    def __init__(self, url, owned, pid, bind_host, port):
        self.url = url
        self.owned = bool(owned)
        self.pid = pid
        self.bind_host = bind_host
        self.port = int(port)

    def stop(self):
        if self.owned and self.pid:
            kill_tree(self.pid)
            self.owned = False

    def to_json(self):
        return {
            "url": self.url,
            "owned": self.owned,
            "pid": self.pid,
            "host": view_host(self.bind_host),
            "port": self.port,
        }


def ensure(repo_root=None, host=None, port=None, wait_sec=READY_TIMEOUT_SEC):
    root = find_repo_root(repo_root)
    file_host, file_port = read_bind(root)
    bind_host = host if host is not None else file_host
    bind_port = int(port if port is not None else file_port)
    url = server_url(bind_host, bind_port)
    if is_up(bind_host, bind_port):
        return Handle(url, False, None, bind_host, bind_port)
    proc = spawn_serve(root, bind_host, bind_port)
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if is_up(bind_host, bind_port):
            return Handle(url, True, proc.pid, bind_host, bind_port)
        if proc.poll() is not None:
            raise SidecarError(
                "serve exited before it was ready (exit %s)" % proc.returncode
            )
        time.sleep(0.15)
    kill_tree(proc.pid)
    raise SidecarError("serve did not become ready at %s within %ss" % (url, wait_sec))


def _cmd_ensure(args):
    handle = ensure(args.root, host=args.host, port=args.port)
    print(json.dumps(handle.to_json(), separators=(",", ":")))
    return 0


def _cmd_stop(args):
    kill_tree(args.pid)
    return 0


def _cmd_probe(args):
    host = args.host or DEFAULT_HOST
    port = args.port if args.port is not None else DEFAULT_PORT
    print(json.dumps({"up": is_up(host, port), "url": server_url(host, port)}))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Delivery Console desktop sidecar")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("ensure", help="start serve if needed; print JSON handle")
    e.add_argument("--root")
    e.add_argument("--host")
    e.add_argument("--port", type=int)
    e.set_defaults(func=_cmd_ensure)

    s = sub.add_parser("stop", help="kill a serve process tree by pid")
    s.add_argument("--pid", type=int, required=True)
    s.set_defaults(func=_cmd_stop)

    pr = sub.add_parser("probe", help="check whether serve is answering")
    pr.add_argument("--host")
    pr.add_argument("--port", type=int)
    pr.set_defaults(func=_cmd_probe)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except SidecarError as err:
        print(str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
