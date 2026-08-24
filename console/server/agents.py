"""Agents tab backend: launches a configured CLI (claude/cursor-agent, or
whatever a fork adds to console/config/console.toml's [agents.backends])
as a headless subprocess and tracks its output.

This is the LEGACY one-shot path behind the `agents *` CLI verbs. The Agents
*tab* uses the live-chat stack instead (agent_manager/agent_session: steering
over stdin, SSE push, and a PreToolUse-hook approval gate — see
agent_approvals.py). This module documents its own remaining gaps rather than
silently pretending to have parity:

- No live steering — a running job can be watched and stopped, not talked
  to mid-turn.
- No worktree isolation — every job runs directly in the target directory.
  Don't launch two jobs against the same ticket/repo concurrently. (True of
  the live chats too.)
- No approval-hook gate on THIS one-shot path — a launched command runs with
  whatever permission mode its own config/args grant it. The default `claude`
  backend in console.toml uses `--permission-mode plan` for that reason.
  Live chats DO gate: `gated_tools` in agents.toml installs the hook.

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

from . import boards as boards_mod
from .paths import find_repo_root

_JOBS = {}
_JOBS_LOCK = threading.Lock()
MAX_BUFFERED_CHARS = 200_000


def _jobs_cache_dir(repo_root):
    d = os.path.join(repo_root, "console", ".cache", "agent-runs")
    os.makedirs(d, exist_ok=True)
    return d


def list_backends(repo_root=None):
    repo_root = repo_root or find_repo_root()
    cfg = boards_mod.load_console_config(repo_root)
    backends = cfg.get("agents", {}).get("backends", {})
    return {
        key: {"label": val.get("label", key), "command": val.get("command", key)}
        for key, val in backends.items()
    }


def list_catalog(repo_root=None):
    """Skills and personas (agent role files) discovered live off disk —
    no hardcoded menu, matches this template's own skills/agents roster."""
    repo_root = repo_root or find_repo_root()
    skills = sorted(
        os.path.basename(os.path.dirname(p))
        for p in glob.glob(os.path.join(repo_root, ".claude", "skills", "*", "SKILL.md"))
    )
    personas = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(repo_root, ".claude", "agents", "*.md"))
    )
    return {"skills": skills, "personas": personas}


def _build_argv(backend_cfg, prompt):
    command = backend_cfg.get("command")
    if not command:
        raise ValueError("backend config is missing 'command'")
    args = [a.replace("{prompt}", prompt) for a in backend_cfg.get("args", [])]
    return [command] + args


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


def compose_prompt(prompt, skill=None, persona=None):
    """Prefix the user's text with a skill invocation and/or persona mention.

    Kept as its own function (and applied before argv building) so the
    composition rule is one testable thing rather than string-fiddling
    scattered through the launcher. Both parts are optional — a bare prompt
    passes through untouched.
    """
    parts = []
    if persona:
        parts.append(f"@{persona}")
    if skill:
        parts.append(f"/{skill}")
    prefix = " ".join(parts)
    return f"{prefix} {prompt}".strip() if prefix else prompt


def launch(repo_root, backend_id, prompt, cwd=None, skill=None, persona=None):
    repo_root = repo_root or find_repo_root()
    backends = boards_mod.load_console_config(repo_root).get("agents", {}).get("backends", {})
    backend_cfg = backends.get(backend_id)
    if not backend_cfg:
        raise ValueError(f"unknown agent backend: {backend_id!r}; configured: {list(backends)}")
    if not (prompt or "").strip():
        raise ValueError("prompt is empty")
    prompt = compose_prompt(prompt, skill=skill, persona=persona)

    run_cwd = os.path.join(repo_root, cwd) if cwd else repo_root
    run_cwd = os.path.abspath(run_cwd)
    if not run_cwd.startswith(os.path.abspath(repo_root)):
        raise ValueError("cwd must stay inside the workspace root")
    if not os.path.isdir(run_cwd):
        raise FileNotFoundError(f"cwd does not exist: {cwd!r}")

    argv = _build_argv(backend_cfg, prompt)
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
