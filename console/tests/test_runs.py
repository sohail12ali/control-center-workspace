"""T-016 Run store and launch-role fail-closed."""

import json
import threading

import pytest

from server import runs, tickets, verbs
from server.paths import find_repo_root
import os
import shutil


class TestRunStore:
    def test_create_list_get(self, repo):
        rec = runs.create(repo, ticket="T-001", role="work", executor="chat",
                          executor_id="abc", backend="claude")
        assert rec["state"] == "running"
        assert rec["executor"] == "chat"
        got = runs.get(repo, rec["id"])
        assert got["executor_id"] == "abc"
        listed = runs.list_runs(repo, ticket="T-001")
        assert len(listed) == 1

    def test_set_state_interrupted(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        out = runs.set_state(repo, rec["id"], "interrupted")
        assert out["state"] == "interrupted"
        assert runs.get(repo, rec["id"])["state"] == "interrupted"

    def test_bad_executor_refused(self, repo):
        with pytest.raises(ValueError):
            runs.create(repo, executor="sidecar")

    def test_ticket_filter(self, repo):
        runs.create(repo, ticket="T-001", executor="chat", executor_id="a")
        runs.create(repo, ticket="T-002", executor="job", executor_id="b")
        assert len(runs.list_runs(repo, ticket="T-001")) == 1

    def test_worktree_fields_default_empty(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="a")
        assert (rec["worktree_path"], rec["worktree_branch"], rec["worktree_error"]) == ("", "", "")

    def test_worktree_fields_round_trip(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="a",
                          worktree_path="/repo/.claude/worktrees/T-001",
                          worktree_branch="agent/T-001", worktree_error="")
        got = runs.get(repo, rec["id"])
        assert got["worktree_path"] == "/repo/.claude/worktrees/T-001"
        assert got["worktree_branch"] == "agent/T-001"

    def test_worktree_error_round_trips(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="a",
                          worktree_error="T-001 is not a git repository")
        assert runs.get(repo, rec["id"])["worktree_error"] == "T-001 is not a git repository"


def _install_shipped_verbs(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    dest = os.path.join(repo, "console", "config", "verbs.toml")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    verbs._cache.clear()


@pytest.fixture
def wired(repo):
    _install_shipped_verbs(repo)
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


class TestLaunchRole:
    def test_unknown_role(self, wired):
        out = verbs.run(wired, "launch-role", ticket="T-001", confirm=True,
                        args={"role": "intern"})
        assert out["ok"] is False
        assert "analyst" in out["error"]

    def test_missing_cursor_agent_does_not_use_claude(self, wired):
        out = verbs.run(wired, "launch-role", ticket="T-001", confirm=True,
                        args={"role": "analyst"})
        assert out["ok"] is False
        assert "fallen through" in out["error"]
        assert runs.list_runs(wired) == []

    def test_run_list_empty(self, wired):
        out = verbs.run(wired, "run-list", ticket="T-001")
        assert out["count"] == 0


class TestDelegateWrap:
    def test_successful_delegate_writes_a_run(self, wired, monkeypatch):
        from server import verb_handlers

        class FakeBackend:
            gated_tools = ()
            transport = "openai_api"
            id = "work-bot"

        captured = {}

        def fake_create(repo_root, backend_id, task, **kw):
            captured["backend"] = backend_id
            captured["task"] = task
            return {"id": "chat-xyz", "model": "m"}

        monkeypatch.setattr(verb_handlers.agent_backends, "registry",
                            lambda root: {"work-bot": FakeBackend()})
        monkeypatch.setattr(verb_handlers.assistant_config,
                            "resolve_work_backend",
                            lambda *a, **k: "work-bot")
        monkeypatch.setattr(verb_handlers.agent_backends, "get",
                            lambda root, bid: FakeBackend())
        monkeypatch.setattr(verb_handlers.agent_manager, "server_port",
                            lambda: 8790)
        monkeypatch.setattr(verb_handlers.agent_manager, "create", fake_create)

        out = verb_handlers.delegate(wired, ticket="T-001", task="do the thing")
        assert out["ok"] is True
        assert out["run"]
        rec = runs.get(wired, out["run"])
        assert rec["executor_id"] == "chat-xyz"
        assert rec["role"] == "work"
        assert rec["executor"] == "chat"


class TestLaunchRoleSuccess:
    def test_creates_cursor_agent_run(self, wired, monkeypatch):
        from server import verb_handlers

        class FakeBackend:
            installed = True
            unavailable_reason = ""

        captured = {}

        def fake_create(repo_root, backend_id, task, **kw):
            captured["backend"] = backend_id
            captured["persona"] = kw.get("persona")
            return {"id": "chat-role"}

        monkeypatch.setattr(verb_handlers.agent_backends, "get",
                            lambda root, bid: FakeBackend())
        monkeypatch.setattr(verb_handlers.agent_manager, "server_port",
                            lambda: 8790)
        monkeypatch.setattr(verb_handlers.agent_manager, "create", fake_create)

        out = verb_handlers.launch_role(wired, ticket="T-001", role="analyst")
        assert out["ok"] is True
        assert captured["backend"] == "cursor-agent"
        assert captured["persona"] == "analyst"
        rec = runs.get(wired, out["run"])
        assert rec["role"] == "analyst"
        assert rec["backend"] == "cursor-agent"


# -- T-020 FR-1 / FR-2: the Run lifecycle ------------------------------------

# A record exactly as pre-T-020 `runs.create` wrote it: none of the new keys.
OLD_RECORD = {
    "id": "oldrun000001", "ticket": "T-001", "role": "work", "executor": "chat",
    "executor_id": "c1", "backend": "claude", "state": "running",
    "created": "2026-09-01T10:00:00Z", "updated": "2026-09-01T10:00:00Z",
    "worktree_path": "", "worktree_branch": "", "worktree_error": "",
}

NEW_KEY_DEFAULTS = {
    "attempt": 1, "attempts": [], "failure_class": "", "failure_detail": "",
    "retry_not_before": "", "retry_due": "", "retry_of": "", "end_reason": "",
    "ended": "", "last_output_at": "",
    "liveness": {"state": "", "reason": ""},
}


def _plant(repo, record):
    """Write a record straight to disk, the way an older build left it."""
    path = os.path.join(runs.runs_dir(repo), record["id"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    return path


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


class TestRunStates:
    def test_states_are_old_six_plus_two_and_partitioned(self):
        assert set(runs.STATES) == {"queued", "running", "needs-approval", "done",
                                    "failed", "interrupted", "timed_out",
                                    "scheduled_retry"}
        assert len(runs.STATES) == 8
        assert runs.TERMINAL == {"done", "failed", "interrupted", "timed_out"}
        assert runs.ACTIVE == {"queued", "running", "needs-approval", "scheduled_retry"}
        assert runs.TERMINAL | runs.ACTIVE == set(runs.STATES)
        assert not runs.TERMINAL & runs.ACTIVE

    def test_done_to_running_raises_and_file_unchanged(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        runs.set_state(repo, rec["id"], "done")
        path = os.path.join(runs.runs_dir(repo), rec["id"] + ".json")
        before = _bytes(path)
        with pytest.raises(ValueError):
            runs.set_state(repo, rec["id"], "running")
        assert _bytes(path) == before
        assert runs.get(repo, rec["id"])["state"] == "done"

    def test_existing_running_record_loads_and_lists_unchanged(self, repo):
        _plant(repo, OLD_RECORD)
        got = runs.get(repo, OLD_RECORD["id"])
        listed = runs.list_runs(repo)
        assert len(listed) == 1
        for rec in (got, listed[0]):
            for key, value in OLD_RECORD.items():
                assert rec[key] == value


class TestRunDefaults:
    def test_pre_t020_record_returns_every_new_key_with_default(self, repo):
        _plant(repo, OLD_RECORD)
        got = runs.get(repo, OLD_RECORD["id"])
        listed = runs.list_runs(repo)[0]
        for rec in (got, listed):
            for key, value in NEW_KEY_DEFAULTS.items():
                assert rec[key] == value, key

    def test_a_stored_value_is_never_replaced_by_its_default(self, repo):
        _plant(repo, dict(OLD_RECORD, failure_class="quota", attempt=2))
        got = runs.get(repo, OLD_RECORD["id"])
        assert got["failure_class"] == "quota" and got["attempt"] == 2

    def test_mutable_defaults_are_not_shared_between_reads(self, repo):
        _plant(repo, OLD_RECORD)
        runs.get(repo, OLD_RECORD["id"])["attempts"].append({"n": 1})
        assert runs.get(repo, OLD_RECORD["id"])["attempts"] == []


EIGHT_FIELDS = {
    "attempt": 3, "failure_class": "quota", "failure_detail": "limit hit",
    "retry_not_before": "2026-10-01T12:00:00Z", "retry_due": "2026-10-01T12:01:00Z",
    "retry_of": "prevrun", "end_reason": "x", "last_output_at": "2026-10-01T11:59:00Z",
}


class TestRunUpdate:
    @pytest.mark.parametrize("round_", range(20))
    def test_eight_threads_no_lost_update(self, repo, round_):
        rec = runs.create(repo, executor="chat", executor_id="x")
        barrier = threading.Barrier(len(EIGHT_FIELDS))
        errors = []

        def worker(key, value):
            try:
                barrier.wait(timeout=5)
                runs.update(repo, rec["id"], **{key: value})
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=kv) for kv in EIGHT_FIELDS.items()]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        assert errors == []
        got = runs.get(repo, rec["id"])
        for key, value in EIGHT_FIELDS.items():
            assert got[key] == value, key

    def test_terminal_with_annotations_one_write_then_refused_byte_identical(
            self, repo, monkeypatch):
        rec = runs.create(repo, executor="chat", executor_id="x")
        writes = []
        real_write = runs._write
        monkeypatch.setattr(runs, "_write",
                            lambda path, record: (writes.append(record), real_write(path, record)))
        out = runs.update(repo, rec["id"], state="done",
                          liveness={"state": "completed", "reason": "ok"},
                          ended="2026-10-01T12:00:00Z", end_reason="completed")
        assert len(writes) == 1
        assert writes[0]["state"] == "done"
        assert writes[0]["liveness"] == {"state": "completed", "reason": "ok"}
        assert writes[0]["ended"] == "2026-10-01T12:00:00Z"
        assert out["state"] == "done"

        path = os.path.join(runs.runs_dir(repo), rec["id"] + ".json")
        before = _bytes(path)
        with pytest.raises(ValueError):
            runs.update(repo, rec["id"], failure_class="late")
        with pytest.raises(ValueError):
            runs.update(repo, rec["id"], state="done")
        assert _bytes(path) == before
        assert len(writes) == 1

    def test_failure_detail_truncated_with_marker(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        out = runs.update(repo, rec["id"], failure_detail="a" * 900)
        detail = runs.get(repo, rec["id"])["failure_detail"]
        assert detail == out["failure_detail"]
        assert len(detail) == 500
        assert detail.endswith(runs.TRUNCATION_MARKER)
        assert detail.startswith("a" * 100)
        # At the limit is stored whole, no marker.
        runs.update(repo, rec["id"], failure_detail="b" * 500)
        assert runs.get(repo, rec["id"])["failure_detail"] == "b" * 500

    def test_failure_detail_is_scrubbed_of_credential_shapes_when_stored(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        raw = ("401 for sk-ant-api03-abcdefghij0123 and ghp_abcdefghij0123456789 "
               "header Authorization: Bearer eyJhbGciOi.abc-def_1 done")
        runs.update(repo, rec["id"], failure_detail=raw)
        detail = runs.get(repo, rec["id"])["failure_detail"]
        for secret in ("sk-ant", "ghp_abc", "eyJhbGci"):
            assert secret not in detail
        assert detail.count("[redacted]") == 3 and detail.startswith("401 for")

    def test_attempts_keeps_the_last_ten(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        entries = [{"n": n, "started": "", "ended": "", "failure_class": ""}
                   for n in range(1, 15)]
        runs.update(repo, rec["id"], attempts=entries)
        got = runs.get(repo, rec["id"])["attempts"]
        assert [e["n"] for e in got] == list(range(5, 15))

    def test_unknown_field_refused(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        path = os.path.join(runs.runs_dir(repo), rec["id"] + ".json")
        before = _bytes(path)
        for bad in ("bogus", "id", "created", "executor_id", "updated"):
            with pytest.raises(ValueError):
                runs.update(repo, rec["id"], **{bad: "x"})
        assert _bytes(path) == before

    def test_bad_state_and_missing_run_refused(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        with pytest.raises(ValueError):
            runs.update(repo, rec["id"], state="paused")
        with pytest.raises(FileNotFoundError):
            runs.update(repo, "nosuchrun000", state="done")
        # A refused update must not leave a lock file behind to block the next one.
        runs.update(repo, rec["id"], failure_class="ok")

    def test_reader_hammering_get_never_breaks_writer(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        stop = threading.Event()
        reader_errors = []

        def reader():
            while not stop.is_set():
                try:
                    # An existing Run must never read as missing or torn.
                    if runs.get(repo, rec["id"]) is None:
                        reader_errors.append("get returned None")
                    if len(runs.list_runs(repo)) != 1:
                        reader_errors.append("list_runs lost the run")
                except Exception as exc:  # noqa: BLE001
                    reader_errors.append(exc)

        t = threading.Thread(target=reader)
        t.start()
        try:
            for n in range(60):
                runs.update(repo, rec["id"], attempt=n + 1)
        finally:
            stop.set()
            t.join(timeout=10)
        assert reader_errors == []
        assert runs.get(repo, rec["id"])["attempt"] == 60

    def test_find_active_chat_run_ignores_terminal_and_other_executors(self, repo):
        done = runs.create(repo, executor="chat", executor_id="chat-1", state="done")
        runs.create(repo, executor="job", executor_id="chat-1")
        runs.create(repo, executor="chat", executor_id="chat-2")
        assert runs.find_active_chat_run(repo, "chat-1") is None
        live = runs.create(repo, executor="chat", executor_id="chat-1",
                           state="scheduled_retry")
        found = runs.find_active_chat_run(repo, "chat-1")
        assert found["id"] == live["id"] and found["id"] != done["id"]
        assert runs.find_active_chat_run(repo, "no-such-chat") is None
