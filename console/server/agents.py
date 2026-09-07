"""Agents CLI backend: launches a configured CLI as a headless subprocess and
tracks its output.

Backends come from `console/config/agents.toml` via `agent_backends`, the SAME
registry the Agents tab reads. That was not always true: this module used to
read a second `[agents.backends]` table in console.toml, so `kanban agents
launch claude` and the tab's claude could disagree about the command, the
model, and the permission mode with nothing to flag it. One registry now, two
consumers.

A one-shot launch needs a one-shot argv, which is a per-backend fact: it comes
from that row's `oneshot_args` (or `turn_args`, for a backend whose per-turn
form already is one). A backend that declares neither cannot be launched this
way and says so, rather than being handed a guess at its flags.

This is the one-shot path behind the `agents *` CLI verbs. The Agents *tab*
uses the live-chat stack instead (agent_manager/agent_session: steering over
stdin, SSE push, and a PreToolUse-hook approval gate — see
agent_approvals.py). This module documents its own remaining gaps rather than
silently pretending to have parity:

- No live steering — a running job can be watched and stopped, not talked
  to mid-turn.
- No worktree isolation — every job runs directly in the target directory.
  Don't launch two jobs against the same ticket/repo concurrently. (True of
  the live chats too.)
- No approval-hook gate on THIS one-shot path — a launched command runs with
  whatever permission mode its own config/args grant it. That is why a row's
  `oneshot_args` should pass `{mode}` and why `launch()` defaults the mode to
  the backend's own `default_mode` (`plan` for both bundled rows) instead of
  leaving it unset. Live chats DO gate: `gated_tools` in agents.toml installs
  the hook.

Jobs are process-memory state (a dict keyed by job id) plus a best-effort
JSON snapshot on disk (console/.cache/agent-runs/, gitignored) written when
a job finishes, for the record to survive past that request. A server
restart while a job is mid-flight loses live tracking of it (the OS
subprocess itself is unaffected either way).
"""

import glob
import json
import os
import subprocess
import threading
import time
import uuid

from . import agent_backends
from . import boards as boards_mod
from . import procs
from . import tickets as tickets_mod
from .paths import find_repo_root

_JOBS = {}
_JOBS_LOCK = threading.Lock()
MAX_BUFFERED_CHARS = 200_000


#: A tone note appended to every chat this console starts (T-013).
HOUSE_STYLE_REL = os.path.join("console", "config", "house-style.md")

#: A cap, because this text is prepended to someone else's system prompt. A
#: page of tone instructions would crowd out the actual task, and the fix for
#: wanting more than this is usually a persona, not a longer style note.
HOUSE_STYLE_CAP = 1200


def house_style(repo_root):
    """The workspace's tone note, or "" when there is none.

    Exists because an agent chat gets no persona at all: the CLI's own system
    prompt decides how it writes, and "it talks like a robot" is a fair
    complaint about a default. This is the one channel the console has into
    that — `system_append` — used sparingly.

    Everything above the `---` in the file is documentation for whoever opens
    it; only what follows is sent.
    """
    path = os.path.join(repo_root, HOUSE_STYLE_REL)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    _, sep, body = text.partition(chr(10) + "---" + chr(10))
    body = (body if sep else text).strip()
    if len(body) > HOUSE_STYLE_CAP:
        body = body[:HOUSE_STYLE_CAP].rstrip() + " [house style truncated]"
    return body


def _jobs_cache_dir(repo_root):
    d = os.path.join(repo_root, "console", ".cache", "agent-runs")
    os.makedirs(d, exist_ok=True)
    return d


def list_backends(repo_root=None):
    """id -> {label, command, installed, launchable} for every configured row.

    `launchable` is the field that matters here and nowhere else: a backend the
    Agents *tab* drives happily (claude, over a long-lived stream) still has no
    one-shot argv unless its row declares one, and saying so up front beats
    failing at spawn time.
    """
    repo_root = repo_root or find_repo_root()
    out = {}
    for bid, backend in agent_backends.registry(repo_root).items():
        out[bid] = {
            "label": backend.label,
            "command": backend.command,
            "transport": backend.transport,
            "installed": backend.installed,
            "launchable": bool(backend.raw.get("oneshot_args")
                               or backend.raw.get("turn_args")),
        }
    return out


def list_catalog(repo_root=None):
    """What the composer can offer: skills, personas, and open tickets.

    All three are read live off disk rather than hardcoded, so the menu is this
    checkout's real roster and cannot rot. The HTTP catalog route calls this —
    it used to reimplement the globs, which meant the tab and the CLI could
    show different rosters.

    Tickets are here so a chat can say which ticket it is working on, which is
    what makes its telemetry attributable. Terminal lanes are excluded: you do
    not start new work on a closed ticket, and offering one invites a misfile.
    """
    repo_root = repo_root or find_repo_root()
    skills = sorted(
        os.path.basename(os.path.dirname(p))
        for p in glob.glob(os.path.join(repo_root, ".claude", "skills", "*", "SKILL.md"))
    )
    personas = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(repo_root, ".claude", "agents", "*.md"))
    )
    return {"skills": skills, "personas": personas,
            "tickets": _open_tickets(repo_root)}


def _open_tickets(repo_root):
    """[{id, title, stage}] for every ticket not sitting in a terminal lane."""
    out = []
    for ticket in tickets_mod.list_tickets(repo_root):
        kind = ticket.get("kind") or "tickets"
        try:
            lanes = {l["id"]: l for l in boards_mod.lanes_for(kind, repo_root)}
        except ValueError:
            continue  # a ticket whose board config is gone is not offerable
        lane = lanes.get(ticket.get("stage") or "")
        if lane and lane.get("terminal"):
            continue
        out.append({"id": ticket.get("id", ""),
                    "title": ticket.get("title", ""),
                    "stage": ticket.get("stage", "")})
    return out


def _build_argv(backend, prompt, mode="", model=""):
    """One-shot argv from the backend's own template.

    `Backend.turn_argv` picks `turn_args` or `oneshot_args` and resolves the
    command to a full path — the latter matters on Windows, where a CLI is
    often a .CMD shim that CreateProcess will not find by bare name.
    """
    if not (backend.raw.get("oneshot_args") or backend.raw.get("turn_args")):
        raise ValueError(
            "backend %r declares no oneshot_args/turn_args, so it cannot be "
            "launched one-shot; use the Agents tab (transport %r) or add a "
            "oneshot_args row to console/config/agents.toml"
            % (backend.id, backend.transport))
    return backend.turn_argv(prompt, mode=mode, model=model)


def _reader_thread(job_id, proc, repo_root):
    job = _JOBS[job_id]
    try:
        for line in proc.stdout:
            with job["lock"]:
                job["buffer"].append(line)
                total_len = sum(len(x) for x in job["buffer"])
                if total_len > MAX_BUFFERED_CHARS:
                    job["buffer"] = job["buffer"][-1000:]
                    job["truncated"] = True
        proc.wait()
    finally:
        with job["lock"]:
            job["status"] = "done" if proc.returncode == 0 else "error"
            job["exit_code"] = proc.returncode
            job["finished_at"] = time.time()
        _persist_job(repo_root, job_id)


def _persist_job(repo_root, job_id):
    job = _JOBS.get(job_id)
    if not job:
        return
    with job["lock"]:
        snapshot = {
            "id": job_id,
            "backend": job["backend"],
            "prompt": job["prompt"],
            "cwd": job["cwd"],
            "status": job["status"],
            "exit_code": job.get("exit_code"),
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
            "output": "".join(job["buffer"]),
            "truncated": job.get("truncated", False),
        }
    path = os.path.join(_jobs_cache_dir(repo_root), f"{job_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def launch(repo_root, backend_id, prompt, cwd=None, skill=None, persona=None,
           mode="", model=""):
    repo_root = repo_root or find_repo_root()
    backend = agent_backends.get(repo_root, backend_id)
    if not (prompt or "").strip():
        raise ValueError("prompt is empty")
    # How a skill/persona is referenced is the backend's own convention
    # (slash commands vs. naming the SKILL.md path), so the backend composes it.
    prompt = backend.compose_prompt(prompt, skill=skill or "",
                                    persona=persona or "", repo_root=repo_root)

    run_cwd = os.path.join(repo_root, cwd) if cwd else repo_root
    run_cwd = os.path.abspath(run_cwd)
    if not run_cwd.startswith(os.path.abspath(repo_root)):
        raise ValueError("cwd must stay inside the workspace root")
    if not os.path.isdir(run_cwd):
        raise FileNotFoundError(f"cwd does not exist: {cwd!r}")

    argv = _build_argv(backend, prompt, mode=mode, model=model)
    job_id = uuid.uuid4().hex[:12]

    try:
        proc = subprocess.Popen(
            argv,
            cwd=run_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            **procs.popen_kwargs(),
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"backend command not found on PATH: {argv[0]!r} ({exc})") from None

    job = {
        "backend": backend_id,
        "prompt": prompt,
        "cwd": cwd or "",
        "status": "running",
        "exit_code": None,
        "started_at": time.time(),
        "finished_at": None,
        "buffer": [],
        "truncated": False,
        "lock": threading.Lock(),
        "proc": proc,
    }
    with _JOBS_LOCK:
        _JOBS[job_id] = job

    thread = threading.Thread(target=_reader_thread, args=(job_id, proc, repo_root), daemon=True)
    thread.start()

    return {"id": job_id, "backend": backend_id, "status": "running", "argv": argv}


def get_job(repo_root, job_id):
    job = _JOBS.get(job_id)
    if job:
        with job["lock"]:
            return {
                "id": job_id,
                "backend": job["backend"],
                "prompt": job["prompt"],
                "status": job["status"],
                "exit_code": job.get("exit_code"),
                "started_at": job["started_at"],
                "finished_at": job.get("finished_at"),
                "output": "".join(job["buffer"]),
                "truncated": job.get("truncated", False),
            }
    # Fall back to the on-disk snapshot (e.g. after a server restart).
    path = os.path.join(_jobs_cache_dir(repo_root), f"{job_id}.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def list_jobs(repo_root):
    repo_root = repo_root or find_repo_root()
    seen = {}
    with _JOBS_LOCK:
        for job_id, job in _JOBS.items():
            with job["lock"]:
                seen[job_id] = {
                    "id": job_id,
                    "backend": job["backend"],
                    "prompt": job["prompt"][:120],
                    "status": job["status"],
                    "started_at": job["started_at"],
                    "finished_at": job.get("finished_at"),
                }
    for path in glob.glob(os.path.join(_jobs_cache_dir(repo_root), "*.json")):
        job_id = os.path.splitext(os.path.basename(path))[0]
        if job_id in seen:
            continue
        with open(path, "r", encoding="utf-8") as f:
            snap = json.load(f)
        seen[job_id] = {
            "id": job_id,
            "backend": snap["backend"],
            "prompt": snap["prompt"][:120],
            "status": snap["status"],
            "started_at": snap["started_at"],
            "finished_at": snap.get("finished_at"),
        }
    return sorted(seen.values(), key=lambda j: j["started_at"], reverse=True)


def stop_job(repo_root, job_id):
    job = _JOBS.get(job_id)
    if not job:
        raise KeyError(f"no running job {job_id!r} (already finished, or server restarted since it ran)")
    with job["lock"]:
        if job["status"] != "running":
            return {"id": job_id, "status": job["status"]}
        job["proc"].terminate()
    return {"id": job_id, "status": "stopping"}
