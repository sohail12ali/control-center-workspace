"""T-024 AC-5a..5f: an API chat in a worktree splits its two roots.

Console verbs (tracker state) must follow the MAIN repo; file tools must stay
confined to the worktree the agent was given. Driven through the `ApiSession`
seam (scripted provider, real `agent_tools.dispatch`), so it does not depend on
the signature of `dispatch` itself.

AC-5a is written red first (T-024-01): `ApiSession` dispatches with
`self.cwd`, so a verb from a worktree chat mutates the worktree's copy of the
tracker. AC-5b is the guard against the naive fix (swap `cwd` for `repo_root`
everywhere), which would let the agent write into the main tree: it passes today
and must keep passing.
"""

import json
import os
import shutil
import threading
import time

import pytest

from server import (agent_approvals, agent_backends, agent_session, agent_tools, multimodal,
                    notify, trackers, verbs)

# `api` is the shared fixture (workspace + openai_api backend + ticket CC-T001).
from test_api_session import Provider, api, await_approval, call_tool, events, run, say  # noqa: F401

COMMENT_VERB = """\
[[verb]]
id = "comment"
label = "Add comment"
handler = "verb_handlers.ticket_comment"
needs_ticket = true
needs_confirm = true
"""


def _same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


@pytest.fixture
def split(api, tmp_path):
    """(main, worktree): the worktree is a copy of the committed workspace, as a
    real git worktree is — config and the ticket exist in both trees, so a verb
    run against either one succeeds and the only question is which one it hits."""
    main = api
    with open(os.path.join(main, "console", "config", "verbs.toml"), "a",
              encoding="utf-8") as fh:
        fh.write("\n" + COMMENT_VERB)
    wt = str(tmp_path / "wt")
    shutil.copytree(main, wt)
    verbs._cache.clear()
    return main, wt


def build_split(main, wt, provider):
    backend = agent_backends.get(main, "api")
    session = agent_session.build("sid-api", backend, wt, model="test/model",
                                  repo_root=main)
    original = session.client.stream

    def stream(messages, **kw):
        kw["opener"] = provider
        return original(messages, **kw)

    session.client.stream = stream
    session.start()
    return session


def comments(root):
    return [c.get("text") for c in trackers.list_items(root, "CC-T001", "comments")]


class TestApiSessionSplitRoots:
    def test_ac5a_a_verb_from_a_worktree_chat_mutates_main(self, split):
        main, wt = split
        assert not _same(main, wt)
        provider = Provider(
            call_tool("console_comment", {"ticket": "CC-T001", "text": "from-wt",
                                          "confirm": True}),
            say("done"))
        session = build_split(main, wt, provider)
        run(session, "comment on the ticket")

        assert comments(main) == ["from-wt"], (
            "main's tracker did not get the comment; main=%r worktree=%r"
            % (comments(main), comments(wt)))
        assert comments(wt) == [], (
            "the comment landed in the worktree copy: %r" % comments(wt))

    def test_ac5b_write_file_still_lands_in_the_worktree(self, split):
        main, wt = split
        provider = Provider(
            call_tool("write_file", {"path": "x.txt", "content": "hi"}),
            say("written"))
        session = build_split(main, wt, provider)
        session.send("write a file")
        pending = await_approval(session)
        agent_approvals.REGISTRY.decide(pending.key, "allow", by="test")
        session._turn_thread.join(timeout=10)

        assert os.path.isfile(os.path.join(wt, "x.txt")), "file missing from the worktree"
        assert not os.path.exists(os.path.join(main, "x.txt")), (
            "the agent wrote into the MAIN tree, bypassing its worktree")


def _approve(session):
    pending = await_approval(session)
    agent_approvals.REGISTRY.decide(pending.key, "allow", by="test")
    session._turn_thread.join(timeout=10)


def _tool_results(provider):
    """The `tool` messages on the last request the model was sent."""
    return [m["content"] for m in provider.requests[-1]["messages"]
            if m.get("role") == "tool"]


class TestWorkspaceStaysConfined:
    def test_ac5c_paths_outside_the_worktree_are_still_refused(self, split):
        main, wt = split
        with open(os.path.join(main, "x.txt"), "w", encoding="utf-8") as fh:
            fh.write("main file")
        for target in ("../x.txt", os.path.join(main, "x.txt")):
            provider = Provider(call_tool("read_file", {"path": target}), say("done"))
            session = build_split(main, wt, provider)
            run(session, "read it")
            results = _tool_results(provider)
            assert results and "outside the workspace" in results[0], (target, results)
            assert "main file" not in results[0]

    def test_ac5d_run_command_without_cwd_runs_in_the_worktree(self, split):
        main, wt = split
        provider = Provider(
            call_tool("run_command", {"command": "cd" if os.name == "nt" else "pwd"}),
            say("done"))
        session = build_split(main, wt, provider)
        session.send("where am i")
        _approve(session)

        out = _tool_results(provider)[0].split("\n", 1)[1].strip()
        assert _same(out, wt), "ran in %r, expected the worktree %r" % (out, wt)
        assert not _same(out, main)


class TestApprovalRoots:
    def test_ac5e_notify_goes_to_main_and_the_diff_reads_the_worktree_file(
            self, split, monkeypatch):
        main, wt = split
        with open(os.path.join(wt, "x.txt"), "w", encoding="utf-8") as fh:
            fh.write("old line\n")
        sent = []
        monkeypatch.setattr(notify, "send",
                            lambda root, kind, *a, **kw: sent.append((root, kind)))
        provider = Provider(
            call_tool("write_file", {"path": "x.txt", "content": "new line\n"}),
            say("written"))
        session = build_split(main, wt, provider)
        session.send("rewrite it")
        _approve(session)

        approvals = [root for root, kind in sent if kind == "approval"]
        assert len(approvals) == 1 and _same(approvals[0], main)
        request = [e for e in events(session) if e.get("type") == "approval.request"][0]
        preview = request["preview"]
        assert preview["creating"] is False, "the diff read the main tree, which has no x.txt"
        assert preview["removed"] == 1 and preview["added"] == 1

    def test_without_preview_root_the_preview_uses_repo_root(self, repo, monkeypatch):
        # The Claude hook caller passes no `preview_root`: unchanged behaviour.
        from server import tool_preview
        seen = []
        monkeypatch.setattr(tool_preview, "build",
                            lambda root, tool, tool_input: seen.append(root))
        monkeypatch.setattr(notify, "send", lambda *a, **kw: None)
        threading.Thread(target=lambda: agent_approvals.Approvals().request(
            "chat-1", "write_file", {"path": "a", "content": "b"}, "id",
            lambda event: None, timeout=1, repo_root=repo), daemon=True).start()
        deadline = time.time() + 5
        while not seen and time.time() < deadline:
            time.sleep(0.01)
        assert seen == [repo]


class TestCaptureFollowsMain:
    def test_ac5f_a_capture_written_under_main_reaches_the_model(self, split, monkeypatch):
        main, wt = split
        rel = os.path.join(multimodal.CAPTURE_DIR_REL, "e2e.png").replace("\\", "/")
        path = os.path.join(main, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        assert not os.path.exists(os.path.join(wt, rel))
        # Both trees carry the setting, so only the capture lookup is being tested.
        for root in (main, wt):
            with open(os.path.join(root, "console", "config", "assistant.toml"), "w",
                      encoding="utf-8") as fh:
                fh.write('[assistant]\nvision_models = ["*vl*"]\n')

        real = agent_tools.dispatch

        def fake(repo_root, name, arguments, workspace_root=None):
            if "desktop_screenshot" in name:
                return json.dumps({"ok": True, "capture": {"capture_id": "e2e", "path": rel}})
            return real(repo_root, name, arguments, workspace_root)

        monkeypatch.setattr(agent_tools, "dispatch", fake)
        provider = Provider(call_tool("console_desktop_screenshot", {"target": "screen"}),
                            say("seen"))
        session = build_split(main, wt, provider)
        session.model = "qwen2.5vl:7b"
        run(session, "look")

        users = [m["content"] for m in provider.requests[-1]["messages"]
                 if m.get("role") == "user" and isinstance(m["content"], list)]
        assert users, "no image part reached the wire; the capture lookup ran against the worktree"
        assert any(p["type"] == "image_url" for p in users[0])
