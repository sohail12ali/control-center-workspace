"""Codex CLI backend: argv, stdin prompt, JSONL, isolated auth, quota class.

No live `codex` process. Spawn is a fake; credentials are a temp directory.
"""

import json
import os
from datetime import datetime, timezone

import pytest

from server import agent_backends, agent_normalize, agent_session, codex_auth, run_sync, tomlio
from server.agent_events import Stream

SHIPPED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "config", "agents.toml")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _row():
    return next(r for r in tomlio.load(SHIPPED).get("backend", []) if r.get("id") == "codex")


class _Stdin:
    def __init__(self):
        self.buf = ""
        self.closed = False

    def write(self, text):
        self.buf += text

    def close(self):
        self.closed = True


class _Proc:
    def __init__(self):
        self.stdin = _Stdin()
        self.stdout = None
        self.pid = 7

    def poll(self):
        return None


class _Backend:
    id = "codex"
    prompt_via = "stdin"
    auth = "codex"
    default_mode = "default"

    def turn_argv(self, prompt, **kw):
        assert prompt == ""
        return ["codex", "exec", "--json", "-"]

    def child_env(self, repo_root, session_id):
        return codex_auth.child_env(repo_root, session_id)


def test_shipped_row_is_stdin_resume_without_bypass(monkeypatch):
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "C:\\codex.cmd")
    row = _row()
    assert row["prompt_via"] == "stdin"
    assert row["auth"] == "codex"
    assert row["transport"] == "resume"
    joined = " ".join(row["turn_args"] + row["resume_args"])
    assert "dangerously" not in joined
    assert 'sandbox_mode="workspace-write"' in joined
    assert row["resume_args"][-3:] == ["resume", "{resume_id}", "-"]
    backend = agent_backends.Backend(row)
    argv = backend.turn_argv("ignored", model="gpt-5.4", resume_id="thread_1")
    assert argv[1:] == [
        "exec", "--json", "-c", 'sandbox_mode="workspace-write"',
        "--model", "gpt-5.4", "resume", "thread_1", "-",
    ]
    fresh = backend.turn_argv("ignored", model="")
    assert "resume" not in fresh
    assert fresh[-1] == "-"
    assert "--model" not in fresh


def test_turn_writes_the_prompt_to_stdin_and_isolates_the_key(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-codex-test")
    made = []

    def fake(*args, **kwargs):
        proc = _Proc()
        made.append((args, kwargs, proc))
        return proc

    class _QuietThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

    repo = str(tmp_path)
    sess = agent_session.TurnSession(
        "chat1", _Backend(), repo, Stream("chat1"), repo_root=repo)
    monkeypatch.setattr(agent_session.subprocess, "Popen", fake)
    monkeypatch.setattr(agent_session.threading, "Thread", _QuietThread)
    sess._busy = True
    sess._deliver("fix the gate")
    argv, proc_kw, proc = made[0]
    assert proc_kw["stdin"] is agent_session.subprocess.PIPE
    assert proc_kw["env"]["CODEX_HOME"].endswith(os.path.join("codex-homes", "chat1"))
    written = json.loads(open(os.path.join(proc_kw["env"]["CODEX_HOME"], "auth.json"),
                              encoding="utf-8").read())
    assert written == {"OPENAI_API_KEY": "sk-codex-test"}
    assert proc.stdin.closed and proc.stdin.buf == "fix the gate\n"
    assert "fix the gate" not in argv[0]


def test_missing_credentials_are_named_apart_from_a_missing_binary(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(codex_auth, "host_auth_file", lambda: os.path.join("no", "such", "auth.json"))
    row = _row()
    backend = agent_backends.Backend(row)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: None)
    assert backend.installed is False
    assert "not on PATH" in backend.unavailable_reason
    assert backend.credential_reason == ""
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "C:\\codex.cmd")
    assert backend.installed is True
    assert "OPENAI_API_KEY" in backend.credential_reason
    assert "auth.json" in backend.credential_reason


def test_jsonl_becomes_session_text_tool_and_turn_end():
    norm = agent_normalize.Normalizer()
    events = []
    for line in (
        '{"type":"thread.started","thread_id":"thread_9"}',
        '{"type":"item.completed","item":{"id":"c1","type":"command_execution","command":"git status","aggregated_output":"clean","exit_code":0,"status":"completed"}}',
        '{"type":"item.completed","item":{"id":"m1","type":"agent_message","text":"done"}}',
        '{"type":"turn.completed","usage":{"input_tokens":3,"output_tokens":1}}',
    ):
        events.extend(norm.feed(json.loads(line)))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "session.init" and events[0]["session_id"] == "thread_9"
    assert "tool.start" in kinds and "tool.result" in kinds
    assert any(e["type"] == "text.done" and e["text"] == "done" for e in events)
    end = events[-1]
    assert end["type"] == "turn.end" and end["is_error"] is False
    assert end["input_tokens"] == 3 and end["output_tokens"] == 1
    failed = norm.feed({"type": "turn.failed", "error": {"message": "You've hit your usage limit. Try again at 5pm."}})
    assert failed[-1]["is_error"] is True
    assert "usage limit" in failed[-1]["error"]


def test_codex_quota_text_schedules_a_retry():
    turn = {"subtype": "error", "is_error": True, "result": "",
            "error": "You've hit your usage limit. Resets at 1pm (UTC).",
            "errors": [], "api_error_status": None, "stop_reason": "",
            "rate_limit": "", "tools": {}}
    view = {"alive": True, "busy": False, "queued": 0, "last_turn": turn,
            "turn_count": 1, "last_output_at": "", "stop_requested": False,
            "started_utc": "", "watchable": True, "exit_code": 1, "stderr": "",
            "pending_approvals": []}
    rec = {"id": "r1", "executor": "chat", "executor_id": "c1", "state": "running",
           "backend": "codex", "created": "2026-10-01T11:00:00Z", "attempt": 1,
           "attempts": []}
    patch = run_sync.sync_run(rec, view, "2026-10-01T12:00:00Z")
    assert patch["failure_class"] == "quota"
    assert patch["state"] == "scheduled_retry"
    assert patch["retry_due"]
