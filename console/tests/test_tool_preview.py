"""What a gated call would do, computed before it does it.

The behaviour under test is really a claim about people: a card showing escaped
JSON gets approved unread. So these tests check that the preview answers "what
changes?" directly — and that it says so plainly when it cannot.
"""

import os

import pytest

from server import tool_preview


@pytest.fixture
def ws(repo):
    with open(os.path.join(repo, "app.py"), "w", encoding="utf-8") as fh:
        fh.write("def main():\n    return 1\n\n\nprint(main())\n")
    return repo


def kinds(preview):
    return [line["kind"] for line in preview["lines"]]


class TestWrite:
    def test_an_overwrite_shows_added_and_removed_lines(self, ws):
        preview = tool_preview.build(ws, "write_file", {
            "path": "app.py",
            "content": "def main():\n    return 2\n\n\nprint(main())\n"})
        assert preview["kind"] == "diff"
        assert (preview["added"], preview["removed"]) == (1, 1)
        assert preview["creating"] is False

    def test_a_new_file_is_flagged_as_such(self, ws):
        preview = tool_preview.build(ws, "write_file",
                                     {"path": "brand/new.py", "content": "x = 1\n"})
        assert preview["creating"] is True
        assert preview["removed"] == 0

    def test_the_claude_tool_name_works_too(self, ws):
        # Calls arrive from two worlds: the CLI hook and this console's own
        # tool loop. One preview implementation has to serve both.
        preview = tool_preview.build(ws, "Write", {
            "file_path": "app.py", "content": "def main():\n    return 3\n"})
        assert preview["kind"] == "diff" and preview["added"] >= 1

    def test_an_identical_write_shows_no_changes(self, ws):
        with open(os.path.join(ws, "app.py"), encoding="utf-8") as fh:
            same = fh.read()
        preview = tool_preview.build(ws, "write_file",
                                     {"path": "app.py", "content": same})
        assert (preview["added"], preview["removed"]) == (0, 0)

    def test_the_path_is_relative_to_the_workspace(self, ws):
        preview = tool_preview.build(ws, "write_file",
                                     {"path": "app.py", "content": "x"})
        assert preview["path"] == "app.py"

    def test_a_huge_diff_is_capped_and_says_how_much_is_missing(self, ws):
        preview = tool_preview.build(ws, "write_file", {
            "path": "app.py",
            "content": "\n".join("line %d" % i for i in range(2000))})
        assert preview["truncated"] is True
        assert preview["omitted"] > 0
        assert len(preview["lines"]) == tool_preview.MAX_DIFF_LINES

    def test_non_string_content_yields_no_preview(self, ws):
        assert tool_preview.build(ws, "write_file",
                                  {"path": "app.py", "content": {"a": 1}}) is None


class TestEdit:
    def test_a_found_edit_previews_exactly(self, ws):
        preview = tool_preview.build(ws, "edit_file", {
            "path": "app.py", "find": "return 1", "replace": "return 99"})
        assert preview["kind"] == "diff"
        assert (preview["added"], preview["removed"]) == (1, 1)
        added = [l["text"] for l in preview["lines"] if l["kind"] == "add"]
        assert "    return 99" in added

    def test_text_that_is_not_there_is_reported_before_approval(self, ws):
        # Approving a call that is going to fail wastes a round trip and the
        # person's attention; better to say so on the card.
        preview = tool_preview.build(ws, "edit_file", {
            "path": "app.py", "find": "nowhere", "replace": "x"})
        assert preview["kind"] == "note"
        assert "will fail" in preview["text"]

    def test_an_ambiguous_edit_warns_which_occurrence_wins(self, ws):
        with open(os.path.join(ws, "dup.py"), "w") as fh:
            fh.write("a = 1\nb = 1\n")
        preview = tool_preview.build(ws, "edit_file", {
            "path": "dup.py", "find": "1", "replace": "2"})
        assert "appears 2 times" in preview["warning"]

    def test_a_missing_file_says_so_rather_than_guessing(self, ws):
        preview = tool_preview.build(ws, "edit_file", {
            "path": "ghost.py", "find": "x", "replace": "y"})
        assert preview["kind"] == "note"
        assert "does not exist" in preview["text"]

    def test_the_claude_edit_shape_works(self, ws):
        preview = tool_preview.build(ws, "Edit", {
            "file_path": "app.py", "old_string": "return 1",
            "new_string": "return 7"})
        assert preview["kind"] == "diff" and preview["added"] == 1


class TestCommand:
    def test_the_command_is_surfaced_plainly(self, ws):
        preview = tool_preview.build(ws, "run_command",
                                     {"command": "rm -rf build/"})
        assert preview == {"kind": "command", "command": "rm -rf build/", "cwd": "."}

    def test_the_working_directory_is_shown(self, ws):
        preview = tool_preview.build(ws, "Bash",
                                     {"command": "ls", "cwd": "src"})
        assert preview["cwd"] == "src"

    def test_an_empty_command_yields_nothing(self, ws):
        assert tool_preview.build(ws, "Bash", {"command": "   "}) is None


class TestUnknownTools:
    def test_an_unrecognised_tool_returns_none(self, ws):
        # None is an answer: the card falls back to arguments, which is no
        # worse than before and honest about knowing nothing extra.
        assert tool_preview.build(ws, "WebFetch", {"url": "https://x"}) is None

    def test_missing_arguments_return_none_rather_than_raising(self, ws):
        assert tool_preview.build(ws, "write_file", {}) is None
        assert tool_preview.build(ws, "edit_file", {"path": "app.py"}) is None


class TestGateIntegration:
    def test_the_request_event_carries_the_preview(self, ws):
        from server import agent_approvals
        published = []

        def publish(event):
            published.append(event)
            # Answer immediately so the calling thread does not park.
            agent_approvals.REGISTRY.decide(event["key"], "allow", by="test")

        agent_approvals.REGISTRY.request(
            "chat1", "write_file", {"path": "app.py", "content": "x = 1\n"},
            "tu1", publish, timeout=5, repo_root=ws)

        request = published[0]
        assert request["preview"]["kind"] == "diff"
        assert request["preview"]["path"] == "app.py"

    def test_without_a_repo_root_the_preview_is_absent_not_broken(self, ws):
        from server import agent_approvals
        published = []

        def publish(event):
            published.append(event)
            agent_approvals.REGISTRY.decide(event["key"], "allow", by="test")

        agent_approvals.REGISTRY.request(
            "chat2", "write_file", {"path": "app.py", "content": "x"},
            "tu2", publish, timeout=5)
        assert published[0]["preview"] is None

    def test_a_preview_failure_still_asks_the_question(self, ws, monkeypatch):
        # A gated tool must never run unreviewed because the diff crashed.
        from server import agent_approvals
        monkeypatch.setattr(tool_preview, "build",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        published = []

        def publish(event):
            published.append(event)
            agent_approvals.REGISTRY.decide(event["key"], "deny", by="test")

        decision, _reason = agent_approvals.REGISTRY.request(
            "chat3", "write_file", {"path": "app.py", "content": "x"},
            "tu3", publish, timeout=5, repo_root=ws)
        assert published and published[0]["preview"] is None
        assert decision == "deny"
