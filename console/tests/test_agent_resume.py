"""T-011: picking a dead chat back up.

Sessions have always died with the console — `agent_session`'s own docstring
said so, and the Agents tab listed past chats as replay-only. The CLIs hand out
a session id precisely so that a conversation can be continued, and the console
was already writing that id into every transcript. These tests are about the
way back in, and about the two ways it must refuse rather than quietly start a
fresh chat: no id recorded, or a backend whose row does not say how.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import agent_backends, agent_events, agent_manager  # noqa: E402


def _write_transcript(root, sid, events):
    path = os.path.join(agent_manager.chats_dir(root), sid + ".events.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    return path


def _started(**over):
    ev = {"seq": 1, "type": "session.started", "id": "x", "title": "A chat",
          "agent": "claude", "model": "claude-sonnet-5", "mode": "plan",
          "cwd": "D:/somewhere", "at": "2026-09-07T10:00:00"}
    ev.update(over)
    return ev


class TestWhatTheTranscriptGivesBack:
    def test_the_cli_session_id_is_recovered(self, tmp_path):
        path = _write_transcript(str(tmp_path), "abc", [
            _started(),
            {"seq": 2, "type": "turn.start", "session_id": "sess-111"},
            {"seq": 3, "type": "turn.end", "num_turns": 1, "cost_usd": 0.02},
        ])
        meta = agent_manager._meta_from_transcript(path)
        assert meta["native_session_id"] == "sess-111"
        assert meta["cwd"] == "D:/somewhere"
        assert meta["seq"] == 3

    def test_the_last_id_wins(self, tmp_path):
        # A resumed chat can be issued a new id; it is the current one that
        # can be resumed again.
        path = _write_transcript(str(tmp_path), "abc", [
            _started(),
            {"seq": 2, "type": "turn.start", "session_id": "old"},
            {"seq": 3, "type": "turn.start", "session_id": "new"},
        ])
        assert agent_manager._meta_from_transcript(path)["native_session_id"] == "new"

    def test_a_transcript_with_no_id_reports_none(self, tmp_path):
        path = _write_transcript(str(tmp_path), "abc", [_started()])
        assert agent_manager._meta_from_transcript(path)["native_session_id"] == ""


class TestRefusals:
    """Both of these must raise. A resume that quietly starts a new chat is
    indistinguishable, in a chat window, from one that worked — and the user
    finds out several turns later when the model has forgotten everything."""

    def test_a_chat_with_no_recorded_id_is_refused(self, tmp_path):
        _write_transcript(str(tmp_path), "abc", [_started()])
        with pytest.raises(ValueError, match="nothing to resume"):
            agent_manager.resume(str(tmp_path), "abc")

    def test_a_backend_that_cannot_resume_is_refused(self, tmp_path, monkeypatch):
        _write_transcript(str(tmp_path), "abc", [
            _started(agent="nores"),
            {"seq": 2, "type": "turn.start", "session_id": "sess-1"},
        ])

        class Fake:
            id = "nores"
            label = "No Resume"
            can_resume = False
            installed = True

        monkeypatch.setattr(agent_backends, "get", lambda *a, **k: Fake())
        with pytest.raises(ValueError, match="cannot resume"):
            agent_manager.resume(str(tmp_path), "abc")

    def test_a_missing_transcript_is_refused(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            agent_manager.resume(str(tmp_path), "nope")


class TestListing:
    def test_a_past_chat_says_whether_it_can_be_resumed(self, tmp_path, monkeypatch):
        _write_transcript(str(tmp_path), "abc", [
            _started(),
            {"seq": 2, "type": "turn.start", "session_id": "sess-1"},
        ])
        _write_transcript(str(tmp_path), "def", [_started()])  # no id

        class Fake:
            can_resume = True

        monkeypatch.setattr(agent_backends, "get", lambda *a, **k: Fake())
        by_id = {c["id"]: c for c in agent_manager.list_chats(str(tmp_path))}
        assert by_id["abc"]["resumable"] is True
        assert by_id["def"]["resumable"] is False, "no id means no resume"


class TestArgv:
    """The flags are a claim about a CLI, so they are read off the config row
    rather than assembled here.

    `command = "python"` only because `session_argv` resolves the executable
    on PATH, and these tests are about the ARGUMENTS.
    """

    def test_a_resume_id_selects_the_resume_template(self):
        b = agent_backends.Backend({
            "id": "x", "command": "python", "transport": "stream_json",
            "session_args": ["-p", "--model", "{model}"],
            "resume_session_args": ["-p", "--resume", "{resume_id}",
                                    "--model", "{model}"],
        })
        assert "--resume" not in b.session_argv(model="m")
        argv = b.session_argv(model="m", resume_id="sess-9")
        assert argv[argv.index("--resume") + 1] == "sess-9"

    def test_without_a_template_the_plain_args_are_used(self):
        b = agent_backends.Backend({
            "id": "x", "command": "python", "transport": "stream_json",
            "session_args": ["-p"],
        })
        assert b.can_resume is False
        assert "--resume" not in b.session_argv(resume_id="sess-9")

    def test_the_shipped_claude_row_can_resume(self, monkeypatch):
        """A claim about the CONFIG, not about this machine.

        It used to build the argv, which resolves the executable on PATH — so
        it passed here and failed in CI, where Claude Code is not installed.
        The row's flags are the thing worth pinning; `_exe` is stubbed so the
        assertion is about `agents.toml` rather than about what happens to be
        on the runner.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root = os.path.dirname(root)
        registry = agent_backends.registry(root)
        claude = registry["claude"]
        assert claude.can_resume, "claude's agents.toml row lost its resume flags"

        monkeypatch.setattr(type(claude), "_exe", lambda self: "claude")
        argv = claude.session_argv(resume_id="sess-42", model="m")
        assert "--resume" in argv and "sess-42" in argv


class TestTranscriptAfterResume:
    def test_the_whole_conversation_comes_back_not_just_the_new_part(self, tmp_path):
        """The bug this exists to prevent: `transcript` preferred the live
        session's in-memory ring, which for a resumed chat holds only what
        happened AFTER the resume. Opening it showed two events and no
        history — the conversation was on disk the whole time."""
        _write_transcript(str(tmp_path), "abc", [
            _started(),
            {"seq": 2, "type": "text.done", "text": "before the restart"},
            {"seq": 3, "type": "session.exit"},
        ])

        class FakeSess:
            id = "abc"

            class stream:
                head = 99

                @staticmethod
                def since(_):
                    return ([{"seq": 5, "type": "session.resumed"}], False)

            @staticmethod
            def snapshot():
                return {"id": "abc", "alive": True}

        agent_manager._sessions["abc"] = FakeSess()
        try:
            out = agent_manager.transcript(str(tmp_path), "abc")
        finally:
            agent_manager._sessions.pop("abc", None)
        texts = [e.get("text") for e in out["events"] if e.get("text")]
        assert "before the restart" in texts
        assert out["snapshot"]["alive"] is True, (
            "a resumed chat must present as live, not as the exit in its history")


class TestSeqNumbering:
    def test_a_resumed_stream_continues_the_numbering(self, tmp_path):
        # Two events numbered 1 in one file would make the client's catch-up
        # after a reconnect silently wrong.
        path = str(tmp_path / "t.events.jsonl")
        first = agent_events.Stream("s", path=path)
        first.publish({"type": "a"})
        first.publish({"type": "b"})
        assert agent_events.last_seq(path) == 2

        second = agent_events.Stream("s", path=path,
                                     start_seq=agent_events.last_seq(path))
        second.publish({"type": "c"})
        seqs = [e["seq"] for e in agent_events.replay_file(path)]
        assert seqs == [1, 2, 3]
