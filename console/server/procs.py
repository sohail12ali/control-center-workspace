"""Windows no-window spawn hygiene, applied at every Python process-spawn
site that could otherwise flash a console window under a windowless GUI
parent (the desktop shell).

Defensive hygiene, not a fix — see `T-003-decision-log.md` § "Cause B scope":
Phase 0 smoke found the sites this module touches do not currently reproduce
a stray console (children already inherit the sidecar's hidden console).
This guards against a windowless-parent scenario the probe didn't hit,
without overclaiming a defect was fixed.

No-op on POSIX: every function here returns `0`/`{}` off Windows, so a caller
can always add `creationflags=no_window_flags(...)` or `**popen_kwargs()`
unconditionally.
"""

from __future__ import annotations

import os
import signal
import subprocess

#: Win32 CREATE_NO_WINDOW — suppresses the console window a spawned child
#: would otherwise get from a windowless (or hidden-console) parent.
CREATE_NO_WINDOW = 0x08000000

#: Win32 CREATE_NEW_PROCESS_GROUP, spelled out because `subprocess` only has
#: the name on Windows.
CREATE_NEW_PROCESS_GROUP = 0x00000200


def no_window_flags(extra=0):
    """`extra` OR'd with `CREATE_NO_WINDOW` on Windows; `extra` unchanged
    elsewhere. Callers keep any flags they already pass (e.g.
    `CREATE_NEW_PROCESS_GROUP`)."""
    if os.name == "nt":
        return extra | CREATE_NO_WINDOW
    return extra


def popen_kwargs():
    """kwargs to splat into `subprocess.Popen`/`subprocess.run` — only ever
    `creationflags` on `nt`, so a caller's own stdio/cwd/etc. choices are
    untouched. `{}` on POSIX."""
    if os.name == "nt":
        return {"creationflags": CREATE_NO_WINDOW}
    return {}


def tree_spawn_kwargs():
    """Popen kwargs that make an agent child the root of its own tree, so
    `kill_tree` can reach its descendants. POSIX: its own session (and so its
    own process group). Windows: a new process group, no console window."""
    if os.name == "nt":
        return {"creationflags": CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW}
    return {"start_new_session": True}


def clean_env(repo_root=None):
    """`os.environ` minus the `[runs].env_strip` deny list (session-identity and
    nesting variables), for every agent child. Names only; values are never
    read or logged.

    When `repo_root` is given the child also gets `CONSOLE_REPO_ROOT` (T-024),
    the main repo that `paths.find_repo_root` anchors to even when the child's
    cwd is a ticket worktree. Set after the strip, so it is never stripped and
    a stale inherited value is overwritten."""
    from . import run_config  # lazy: run_config imports boards, procs is imported early
    strip = set(run_config.runs_cfg(repo_root)["env_strip"])
    env = {k: v for k, v in os.environ.items() if k not in strip}
    if repo_root:
        env["CONSOLE_REPO_ROOT"] = os.path.abspath(repo_root)
    return env


def _taskkill(pid, force):
    argv = ["taskkill", "/PID", str(pid), "/T"] + (["/F"] if force else [])
    try:
        subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=CREATE_NO_WINDOW, check=False)
    except OSError:
        pass  # taskkill missing: `proc.wait` below decides whether it worked


def _exited(proc, timeout):
    try:
        proc.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def kill_tree(proc, grace=5.0):
    """End `proc` and its descendants: ask, wait `grace`, force, reap (BR-11).

    No-op if it already exited. Windows: `taskkill /T` then `/T /F`. POSIX: a
    group signal only when the child leads its own group (see
    `tree_spawn_kwargs`); otherwise the single process is signalled, never
    ours. A descendant whose parent already exited is out of reach of
    `taskkill /T`. Every OS error is swallowed; the reap decides."""
    if proc is None or proc.poll() is not None:
        return
    pid = proc.pid
    if os.name == "nt":
        _taskkill(pid, False)
        if _exited(proc, grace):
            return
        _taskkill(pid, True)
        _exited(proc, 5.0)
        return
    try:
        own_group = os.getpgid(pid) == pid
    except OSError:
        own_group = False
    hard = getattr(signal, "SIGKILL", 9)
    for sig, single, wait in ((signal.SIGTERM, proc.terminate, grace), (hard, proc.kill, 5.0)):
        try:
            if own_group:
                os.killpg(pid, sig)
            else:
                single()
        except OSError:
            pass
        if _exited(proc, wait):
            return


#: Appended to a line that hit the cap.
LINE_TRUNCATED = " ...[line truncated]"


def iter_capped_lines(stream, max_chars):
    """Yield the lines of a text-mode `stream` (each as `readline` returns it,
    newline kept), holding at most `max_chars` + 1 characters at a time.

    An over-long line is yielded once, cut to `max_chars` and ending in
    `LINE_TRUNCATED` + newline; the rest of it is read in cap-sized chunks and
    discarded, so the next yield is the next real line. The cap counts decoded
    characters, not bytes: the agent pipes are text mode (T-020 CR-37)."""
    nl = chr(10)
    while True:
        chunk = stream.readline(max_chars + 1)
        if not chunk:
            return
        if len(chunk) <= max_chars or chunk.endswith(nl):
            yield chunk
            continue
        yield chunk[:max_chars] + LINE_TRUNCATED + nl
        while not chunk.endswith(nl):
            chunk = stream.readline(max_chars + 1)
            if not chunk:
                return
