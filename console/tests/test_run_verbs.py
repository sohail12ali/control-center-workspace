"""T-020 FR-18: the `run-watch` and `run-retry` verbs, through the verb layer,
the MCP tool list and the HTTP route pattern. Fakes only; no real agent."""

import io
import os
import re
import shutil

import pytest

from server import agent_manager, mcp, run_config, run_watchdog, runs, verbs
from server.paths import find_repo_root


@pytest.fixture
def wired(repo, monkeypatch):
    monkeypatch.setattr(agent_manager, "_owns_registry", False)  # a CLI process, unless a test says so
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    shutil.copyfile(src, os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    run_watchdog.reset()
    run_config.reset_warnings()
    yield repo
    run_watchdog.reset()
    verbs._cache.clear()


def mk(repo, state="failed", chat="c1", **kw):
    rec = runs.create(repo, executor="chat", executor_id=chat, backend="claude",
                      ticket="T-001", role="builder")
    return runs.update(repo, rec["id"], state=state, **kw)


def retry(repo, run_id):
    return verbs.run(repo, "run-retry", confirm=True, args={"run_id": run_id})


def raw(repo, rid):
    with open(runs._path(repo, rid), "rb") as fh:
        return fh.read()


def active_chat_run(repo, chat="c1", **kw):
    return runs.create(repo, executor="chat", executor_id=chat, backend="claude", **kw)


class TestRunWatch:
    def test_cli_process_skips_and_leaves_active_run_untouched(self, wired):
        # The verifier's scenario: an active chat Run, an empty registry (this
        # process is the CLI/stdio MCP, not the server), `run-watch` from it.
        rec = active_chat_run(wired)
        before = raw(wired, rec["id"])
        out = verbs.run(wired, "run-watch", confirm=True)
        assert out["ok"] is True and out["skipped"] == "no live session registry in this process"
        assert {k: out[k] for k in ("synced", "suspicious", "killed", "retried", "errors")} ==             {"synced": 0, "suspicious": 0, "killed": 0, "retried": 0, "errors": 0}
        assert runs.get(wired, rec["id"])["state"] == "running" and raw(wired, rec["id"]) == before

    def test_cli_process_never_resumes_a_scheduled_retry(self, wired):
        old = mk(wired)
        new = retry(wired, old["id"])["run"]
        verbs.run(wired, "run-watch", confirm=True)
        assert runs.get(wired, new["id"])["state"] == "scheduled_retry"

    def test_server_process_ticks_but_never_sweeps_startup(self, wired, monkeypatch):
        monkeypatch.setattr(agent_manager, "_owns_registry", True)
        rec = active_chat_run(wired)
        out = verbs.run(wired, "run-watch", confirm=True)
        assert "skipped" not in out and out["errors"] == 0 and out["last_tick"]
        assert runs.get(wired, rec["id"])["state"] == "running"  # no session: left to the sweep

    def test_start_watchdog_marks_the_process_as_registry_owner(self, wired):
        assert agent_manager.owns_registry() is False
        try:
            agent_manager.start_watchdog(wired)
            assert agent_manager.owns_registry() is True
        finally:
            agent_manager.shutdown_all()
        assert agent_manager.owns_registry() is False

    def test_counts_and_no_mutation_when_no_runs(self, wired, monkeypatch):
        monkeypatch.setattr(agent_manager, "_owns_registry", True)
        out = verbs.run(wired, "run-watch", confirm=True)
        assert {k: out[k] for k in ("synced", "suspicious", "killed", "retried", "errors")} == \
            {"synced": 0, "suspicious": 0, "killed": 0, "retried": 0, "errors": 0}
        assert out["last_tick"] and runs.list_runs(wired) == []

    def test_requires_confirmation(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "run-watch")


class TestRunRetry:
    def test_done_run_refused(self, wired):
        rec = mk(wired, state="done")
        out = retry(wired, rec["id"])
        assert out["ok"] is False and "done" in out["error"]
        assert len(runs.list_runs(wired)) == 1

    def test_unknown_id_refused(self, wired):
        out = retry(wired, "nope")
        assert out["ok"] is False and "nope" in out["error"]
        assert retry(wired, "")["ok"] is False

    @pytest.mark.parametrize("state", ["failed", "timed_out", "interrupted"])
    def test_failed_run_creates_one_new_run_old_file_byte_identical(self, wired, state):
        old = mk(wired, state=state)
        before = raw(wired, old["id"])
        out = retry(wired, old["id"])
        assert out["ok"] is True
        new = runs.get(wired, out["run"]["id"])
        assert new["id"] != old["id"] and new["retry_of"] == old["id"]
        assert new["state"] == "scheduled_retry" and new["retry_due"]
        assert (new["ticket"], new["executor_id"], new["role"]) == ("T-001", "c1", "builder")
        assert len(runs.list_runs(wired)) == 2 and raw(wired, old["id"]) == before

    def test_second_call_while_new_run_active_refused_creates_nothing(self, wired):
        old = mk(wired)
        assert retry(wired, old["id"])["ok"] is True
        out = retry(wired, old["id"])
        assert out["ok"] is False and "active" in out["error"].lower()
        assert len(runs.list_runs(wired)) == 2

    def test_retry_allowed_again_once_the_new_run_ended(self, wired):
        old = mk(wired)
        first = retry(wired, old["id"])["run"]["id"]
        runs.update(wired, first, state="failed")
        assert retry(wired, old["id"])["ok"] is True

    def test_created_run_is_executed_by_the_same_tick(self, wired):
        class Sess:
            alive, busy, stop_requested = True, False, False
            id = "c1"
            def snapshot(self):
                return {"alive": True, "busy": False, "queued": [], "last_turn": None,
                        "turn_count": 0, "last_output_at": "", "started_utc": "",
                        "exit_code": None, "transport": "stream_json", "mode": ""}
            class backend:  # noqa: N801
                is_api = False

        class Reg:
            sent = []
            def get(self, sid): return Sess()
            def send(self, sid, text, mode="auto"): self.sent.append((sid, text))

        class Appr:
            def pending_for(self, chat): return []

        old = mk(wired)
        new = retry(wired, old["id"])["run"]
        reg = Reg()
        out = run_watchdog.tick(wired, registry=reg, approvals=Appr(), startup=False)
        assert out["retried"] == 1 and reg.sent[0][0] == "c1"
        assert runs.get(wired, new["id"])["state"] == "running"


class TestOneApi:
    def test_both_verbs_in_mcp_tool_list_with_derived_schema_and_http_route(self, wired):
        out = io.StringIO()
        server = mcp.Server(wired, stdout=out, stderr=io.StringIO())
        server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        import json
        tools = {t["name"]: t for t in json.loads(out.getvalue())["result"]["tools"]}
        watch, rerun = tools["run-watch"], tools["run-retry"]
        assert "confirm" in watch["inputSchema"]["required"]
        assert "run_id" in rerun["inputSchema"]["properties"]
        assert "confirm" in rerun["inputSchema"]["required"]
        feature = os.path.join(find_repo_root(), "console", "server", "features", "verbs_feature.py")
        pattern = re.search(r'ctx\.post\(r"([^"]+/run/\?\$)"', open(feature, encoding="utf-8").read())
        for vid in ("run-watch", "run-retry"):
            assert re.match(pattern.group(1), "/api/verbs/%s/run" % vid)
            assert any(v["id"] == vid for v in verbs.list_verbs(wired))
