"""Job queue.

Three properties are load-bearing: gates are checked when a job is *submitted*
(while the caller is still there to be told), records on disk are the truth, and
a job orphaned by a dead process is reported as `interrupted` — not as done, and
not as failed.
"""

import json
import os

import pytest

from server import jobs, tickets, verbs

VERBS = """\
[[verb]]
id = "ok"
label = "Fine"
handler = "verb_handlers.open_todos"

[[verb]]
id = "boom"
label = "Explodes"
handler = "verb_handlers.ticket_context"
needs_ticket = true

[[verb]]
id = "guarded"
label = "Needs confirmation"
handler = "verb_handlers.open_todos"
needs_confirm = true
"""


@pytest.fixture
def wired(repo):
    with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(VERBS)
    verbs._cache.clear()
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()


@pytest.fixture
def q(wired):
    queue = jobs.JobQueue(wired, max_concurrent=2).start()
    yield queue
    queue.stop()


class TestSubmission:
    def test_a_submitted_job_runs_and_records_its_result(self, q):
        job = q.submit("ok")
        done = q.wait(job["id"])
        assert done["state"] == jobs.DONE
        assert done["result"] == {"items": []}

    def test_a_record_is_written_immediately(self, q):
        job = q.submit("ok")
        assert os.path.isfile(os.path.join(q.dir, job["id"] + ".json"))

    def test_gates_are_checked_at_submission_not_at_run(self, q):
        # The caller is still there to be told. Accepting a doomed job and
        # failing it later, unwatched, is the outcome this prevents.
        with pytest.raises(verbs.VerbError):
            q.submit("guarded")
        assert q.list_jobs() == []

    def test_a_confirmed_guarded_job_is_accepted(self, q):
        assert q.wait(q.submit("guarded", confirm=True)["id"])["state"] == jobs.DONE

    def test_unknown_verb_is_refused(self, q):
        with pytest.raises(verbs.VerbError):
            q.submit("no-such-verb")

    def test_ticket_and_args_are_carried_through(self, q):
        job = q.wait(q.submit("boom", ticket="CC-T001")["id"])
        assert job["state"] == jobs.DONE
        assert job["result"]["ticket"]["id"] == "CC-T001"


class TestFailure:
    def test_a_handler_error_becomes_the_job_outcome(self, q):
        # Bad arguments pass submission (gates are about state, not signature)
        # and fail when the handler is finally called — a genuine run-time
        # failure, which is what a job's `error` state is for.
        failed = q.wait(q.submit("ok", args={"nonsense": 1})["id"])
        assert failed["state"] == jobs.ERROR
        assert "nonsense" in failed["error"]

    def test_one_failing_job_does_not_kill_the_worker(self, wired):
        # A worker that dies on a bad job takes every later job with it, and
        # the queue silently stops working.
        queue = jobs.JobQueue(wired, max_concurrent=1).start()
        try:
            failed = queue.wait(queue.submit("ok", args={"bad": 1})["id"])
            assert failed["state"] == jobs.ERROR

            after = queue.submit("ok")
            assert queue.wait(after["id"])["state"] == jobs.DONE
        finally:
            queue.stop()

    def test_a_failure_records_the_exception_type(self, q):
        failed = q.wait(q.submit("ok", args={"nope": 1})["id"])
        assert "VerbError" in failed["error"]


class TestCancellation:
    def test_a_queued_job_can_be_cancelled(self, wired):
        queue = jobs.JobQueue(wired, max_concurrent=1)   # not started
        job = queue.submit("ok")
        assert queue.cancel(job["id"])["state"] == jobs.CANCELLED

    def test_a_cancelled_job_is_not_run_when_workers_start(self, wired):
        queue = jobs.JobQueue(wired, max_concurrent=1)
        job = queue.submit("ok")
        queue.cancel(job["id"])
        queue.start()
        try:
            queue.wait(job["id"], timeout=1.0)
            assert queue.get(job["id"])["state"] == jobs.CANCELLED
        finally:
            queue.stop()

    def test_a_finished_job_cannot_be_cancelled(self, q):
        job = q.wait(q.submit("ok")["id"])
        with pytest.raises(ValueError):
            q.cancel(job["id"])

    def test_unknown_job_raises(self, q):
        with pytest.raises(KeyError):
            q.cancel("deadbeef")


class TestRestart:
    def test_an_orphaned_running_job_becomes_interrupted(self, wired):
        # Not `done` (a lie) and not `error` (a guess) — nobody knows how far
        # it got, and the state name has to say that so a person looks.
        first = jobs.JobQueue(wired, max_concurrent=1)
        job = first.submit("ok")
        path = os.path.join(first.dir, job["id"] + ".json")
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
        record["state"] = jobs.RUNNING
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh)

        second = jobs.JobQueue(wired, max_concurrent=1)
        recovered = second.get(job["id"])
        assert recovered["state"] == jobs.INTERRUPTED
        assert "unknown" in recovered["error"]

    def test_a_queued_job_survives_a_restart_and_runs(self, wired):
        first = jobs.JobQueue(wired, max_concurrent=1)   # never started
        job = first.submit("ok")
        assert first.get(job["id"])["state"] == jobs.QUEUED

        second = jobs.JobQueue(wired, max_concurrent=1).start()
        try:
            assert second.wait(job["id"])["state"] == jobs.DONE
        finally:
            second.stop()

    def test_finished_jobs_are_read_back_unchanged(self, wired):
        first = jobs.JobQueue(wired, max_concurrent=1).start()
        job = first.wait(first.submit("ok")["id"])
        first.stop()

        second = jobs.JobQueue(wired, max_concurrent=1)
        assert second.get(job["id"])["state"] == jobs.DONE

    def test_a_corrupt_record_does_not_hide_the_others(self, wired):
        first = jobs.JobQueue(wired, max_concurrent=1).start()
        good = first.wait(first.submit("ok")["id"])
        first.stop()
        with open(os.path.join(first.dir, "broken.json"), "w") as fh:
            fh.write("{ not json")

        second = jobs.JobQueue(wired, max_concurrent=1)
        assert second.get(good["id"]) is not None


class TestConcurrency:
    def test_the_cap_comes_from_config(self, wired):
        path = os.path.join(wired, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n[jobs]\nmax_concurrent = 5\n")
        from server import boards
        boards._console_cache.clear()
        assert jobs.JobQueue(wired).max_concurrent == 5

    def test_a_nonsense_cap_falls_back_rather_than_crashing(self, wired):
        path = os.path.join(wired, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('\n[jobs]\nmax_concurrent = "lots"\n')
        from server import boards
        boards._console_cache.clear()
        assert jobs.JobQueue(wired).max_concurrent == jobs.DEFAULT_MAX_CONCURRENT

    def test_every_submission_eventually_runs(self, q):
        ids = [q.submit("ok")["id"] for _ in range(6)]
        assert all(q.wait(i, timeout=15)["state"] == jobs.DONE for i in ids)


class TestListing:
    def test_filters_by_state_and_ticket(self, q):
        q.wait(q.submit("ok")["id"])
        q.wait(q.submit("boom", ticket="CC-T001")["id"])
        assert len(q.list_jobs()) == 2
        assert len(q.list_jobs(state=jobs.DONE)) == 2
        assert [j["verb"] for j in q.list_jobs(ticket="CC-T001")] == ["boom"]

    def test_newest_first_even_within_the_same_second(self, q):
        # `submitted` is second-granularity and this queue routinely takes
        # several jobs per second, so ordering rides on the sequence number.
        ids = [q.submit("ok")["id"] for _ in range(4)]
        for job_id in ids:
            q.wait(job_id)
        assert [j["id"] for j in q.list_jobs()] == list(reversed(ids))

    def test_order_survives_a_restart(self, wired):
        first = jobs.JobQueue(wired, max_concurrent=1).start()
        ids = [first.submit("ok")["id"] for _ in range(3)]
        for job_id in ids:
            first.wait(job_id)
        first.stop()

        second = jobs.JobQueue(wired, max_concurrent=1)
        assert [j["id"] for j in second.list_jobs()] == list(reversed(ids))
        # And a job submitted after the restart still sorts newest.
        new = second.submit("ok")
        assert second.list_jobs()[0]["id"] == new["id"]


class TestWorkerSurvival:
    """A worker that dies takes every job still queued behind it, and nothing
    says so — the queue simply stops working."""

    def test_an_unwritable_record_does_not_kill_the_worker(self, wired, monkeypatch):
        queue = jobs.JobQueue(wired, max_concurrent=1).start()
        try:
            calls = {"n": 0}
            real_open = jobs.open if hasattr(jobs, "open") else open

            def flaky(path, *a, **kw):
                calls["n"] += 1
                if calls["n"] == 2:      # fail one write, mid-flight
                    raise OSError("disk went away")
                return real_open(path, *a, **kw)

            monkeypatch.setattr("builtins.open", flaky)
            first = queue.submit("ok")
            queue.wait(first["id"], timeout=5)
            monkeypatch.undo()

            after = queue.submit("ok")
            assert queue.wait(after["id"], timeout=5)["state"] == jobs.DONE
        finally:
            queue.stop()

    def test_write_reports_failure_instead_of_raising(self, wired, monkeypatch):
        queue = jobs.JobQueue(wired, max_concurrent=1)
        monkeypatch.setattr("builtins.open",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
        assert queue._write({"id": "abc"}) is False
