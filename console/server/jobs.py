"""A durable queue for work the console runs on your behalf.

## What it is for

Today a verb runs inline and an agent run is a subprocess nobody is tracking.
That is fine while a person is sitting in front of it. It stops being fine the
moment work is scheduled, triggered remotely, or simply takes longer than the
patience of whoever started it — and those are exactly the next things this
roadmap builds. A job record is how work becomes something you can ask about
later: what ran, when, with what arguments, and how it ended.

## Records are the source of truth, memory is a cache

Every state change is written to disk before it is announced. The in-memory
dict exists so a running process does not re-read a directory on every poll,
never as the authority. This matters for one specific failure: a process that
dies mid-job leaves a record saying `running` that will never be updated by
anyone.

## An interrupted job is not a failed job, and not a finished one

On startup, a record left in `running` by a dead process is moved to
`interrupted`. It is tempting to call it `error` — it is certainly not success —
but that would assert the work failed, when the truth is that nobody knows how
far it got. A job that half-applied a change and then lost its process is a
situation a person has to look at, and the state name should say so rather than
filing it under a heading that invites ignoring it.

## Concurrency

A cap, enforced by the number of worker threads. Excess submissions stay
`queued` in submission order. The cap exists because the work these jobs do —
agent runs, git operations — competes for the same disk and the same API rate
limits, and running ten at once is slower than running two, not faster.
"""

import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timezone

from . import boards as boards_mod
from . import verbs as verbs_mod

DEFAULT_DIR = os.path.join("console", ".cache", "jobs")
DEFAULT_MAX_CONCURRENT = 2

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
ERROR = "error"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"

#: States in which a job will never change again without a new submission.
FINAL = (DONE, ERROR, CANCELLED, INTERRUPTED)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _config(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("jobs", {}) or {}
    try:
        cap = int(cfg.get("max_concurrent", DEFAULT_MAX_CONCURRENT))
    except (TypeError, ValueError):
        cap = DEFAULT_MAX_CONCURRENT
    return {"dir": cfg.get("dir") or DEFAULT_DIR, "max_concurrent": max(1, cap)}


def jobs_dir(repo_root):
    return os.path.join(repo_root, _config(repo_root)["dir"])


class JobQueue:
    """Durable job records plus a bounded worker pool.

    Construct one per repo root. `start()` spawns the workers; without it the
    queue still accepts submissions and still persists them — they simply wait,
    which is what a CLI process that only wants to *record* a job needs.
    """

    def __init__(self, repo_root, max_concurrent=None):
        self.repo_root = repo_root
        cfg = _config(repo_root)
        self.dir = os.path.join(repo_root, cfg["dir"])
        self.max_concurrent = max_concurrent or cfg["max_concurrent"]
        self._jobs = {}
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._workers = []
        self._stopping = threading.Event()
        # Submission order needs its own counter. `submitted` is an ISO
        # timestamp at second granularity, and this queue will routinely accept
        # several jobs within one second — sorting by it alone leaves their
        # order undefined, which shows up as a job list that reshuffles itself.
        self._seq = 0
        os.makedirs(self.dir, exist_ok=True)
        self._reconcile()

    # -- persistence -------------------------------------------------------
    def _path(self, job_id):
        return os.path.join(self.dir, "%s.json" % job_id)

    def _write(self, job):
        """Persist one record. Returns False if it could not be written.

        Never raises. This runs on a worker thread, and an exception escaping
        here kills that worker — which silently takes every job still queued
        behind it, because the worker loop is what pulls them. Losing one
        record is bad; losing the queue is worse and much harder to notice.
        """
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self._path(job["id"]) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(job, fh, indent=2, default=str)
            os.replace(tmp, self._path(job["id"]))
            return True
        except (OSError, ValueError, TypeError):
            return False

    def _load_all(self):
        out = {}
        if not os.path.isdir(self.dir):
            return out
        for name in os.listdir(self.dir):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.dir, name), "r", encoding="utf-8") as fh:
                    job = json.load(fh)
            except (OSError, ValueError):
                continue  # a truncated record must not hide the rest
            if job.get("id"):
                out[job["id"]] = job
        return out

    def _reconcile(self):
        """Adopt records from disk, and mark orphaned `running` jobs.

        Anything still `running` belongs to a process that is gone — this
        constructor only runs at startup. Reporting it as `done` would be a
        lie and as `error` would be a guess, so it becomes `interrupted`.
        """
        self._jobs = self._load_all()
        self._seq = max([int(j.get("seq") or 0) for j in self._jobs.values()] or [0])
        for job in self._jobs.values():
            if job.get("state") == RUNNING:
                job["state"] = INTERRUPTED
                job["finished"] = _now()
                job["error"] = ("the process running this job exited before it "
                                "reported an outcome; how far it got is unknown")
                self._write(job)
            elif job.get("state") == QUEUED:
                # Requeue: it was accepted and never run, which is a promise
                # this process can still keep.
                self._queue.put(job["id"])

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        if self._workers:
            return self
        for i in range(self.max_concurrent):
            t = threading.Thread(target=self._worker, name="job-%d" % i, daemon=True)
            t.start()
            self._workers.append(t)
        return self

    def stop(self, timeout=5.0):
        self._stopping.set()
        for _ in self._workers:
            self._queue.put(None)
        for t in self._workers:
            t.join(timeout=timeout)
        self._workers = []

    # -- submission --------------------------------------------------------
    def submit(self, verb, *, ticket=None, args=None, confirm=False,
               submitted_by=""):
        """Record a job and queue it. Gates are checked NOW, not at run time.

        Checking on submission is what makes the queue honest: a job that would
        fail its own gate is refused while the caller is still there to be told,
        instead of being accepted, sitting in a queue, and failing later with
        nobody watching.
        """
        verb_obj = verbs_mod.get(self.repo_root, verb)
        verbs_mod.check_gates(self.repo_root, verb_obj, ticket=ticket,
                              confirm=confirm)
        with self._lock:
            self._seq += 1
            seq = self._seq
        job = {
            "id": uuid.uuid4().hex[:12],
            "seq": seq,
            "verb": verb,
            "ticket": ticket or "",
            "args": dict(args or {}),
            "confirm": bool(confirm),
            "state": QUEUED,
            "submitted": _now(),
            "submitted_by": submitted_by,
            "started": "",
            "finished": "",
            "result": None,
            "error": "",
        }
        with self._lock:
            self._jobs[job["id"]] = job
            self._write(job)
        self._queue.put(job["id"])
        return dict(job)

    def cancel(self, job_id):
        """Cancel a queued job. A running one cannot be cancelled here.

        Killing work mid-flight needs the worker's cooperation and a handler
        that can be interrupted safely; claiming to cancel a running job while
        it keeps running would be worse than refusing.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError("no job %r" % job_id)
            if job["state"] == RUNNING:
                raise ValueError(
                    "job %s is already running and cannot be cancelled; "
                    "stop the console to end it" % job_id)
            if job["state"] in FINAL:
                raise ValueError("job %s already finished as %r"
                                 % (job_id, job["state"]))
            job["state"] = CANCELLED
            job["finished"] = _now()
            self._write(job)
            return dict(job)

    # -- execution ---------------------------------------------------------
    def _worker(self):
        while not self._stopping.is_set():
            job_id = self._queue.get()
            if job_id is None:
                break
            try:
                self._run_one(job_id)
            except BaseException:  # noqa: BLE001
                # Last line of defence. `_run_one` already turns a handler
                # failure into the job's outcome, so reaching here means the
                # bookkeeping itself broke. Even then the worker must survive:
                # it is the only thing pulling the rest of the queue.
                pass

    def _run_one(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["state"] != QUEUED:
                return  # cancelled, or already claimed
            job["state"] = RUNNING
            job["started"] = _now()
            self._write(job)

        try:
            result = verbs_mod.run(self.repo_root, job["verb"],
                                   ticket=job["ticket"] or None,
                                   confirm=job["confirm"], args=job["args"])
            state, error = DONE, ""
        except Exception as exc:  # noqa: BLE001
            # Any handler failure is the job's outcome, not the worker's death.
            # A worker that dies takes every later job in the queue with it.
            result, state, error = None, ERROR, "%s: %s" % (type(exc).__name__, exc)

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["state"] = state
            job["error"] = error
            job["result"] = result
            job["finished"] = _now()
            self._write(job)

    # -- reading -----------------------------------------------------------
    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list_jobs(self, state=None, ticket=None, limit=50):
        with self._lock:
            rows = [dict(j) for j in self._jobs.values()]
        if state:
            rows = [j for j in rows if j["state"] == state]
        if ticket:
            rows = [j for j in rows if j["ticket"] == ticket]
        rows.sort(key=lambda j: int(j.get("seq") or 0), reverse=True)
        return rows[:limit]

    def wait(self, job_id, timeout=30.0, poll=0.02):
        """Block until a job reaches a final state. Returns it, or None on timeout.

        For a CLI that submits one job and wants its answer, and for tests.
        A server never calls this — it streams state instead.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get(job_id)
            if job and job["state"] in FINAL:
                return job
            time.sleep(poll)
        return None

    @property
    def pending(self):
        with self._lock:
            return sum(1 for j in self._jobs.values() if j["state"] == QUEUED)


def format_list(rows):
    if not rows:
        return "No jobs."
    lines = ["%-12s %-11s %-16s %-10s %s"
             % ("ID", "STATE", "VERB", "TICKET", "SUBMITTED")]
    for job in rows:
        lines.append("%-12s %-11s %-16s %-10s %s" % (
            job["id"], job["state"], job["verb"], job["ticket"] or "-",
            job["submitted"]))
        if job.get("error"):
            lines.append("             %s" % job["error"])
    return "\n".join(lines)
