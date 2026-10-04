"""T-013: the tone note appended to every chat this console starts.

An agent chat gets no persona — the CLI's own system prompt decides how it
writes, and "it talks like a robot" is a fair complaint about that default.
`system_append` is the one channel the console has into it, so this is
deliberately small and deliberately capped.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import agents  # noqa: E402


def _write(tmp_path, text):
    cfg = tmp_path / "console" / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "house-style.md").write_text(text, encoding="utf-8")


class TestHouseStyle:
    def test_only_what_is_below_the_rule_is_sent(self, tmp_path):
        # Everything above `---` explains the file to whoever opens it. Sending
        # that to a model would spend its context on instructions about a file
        # it cannot see.
        _write(tmp_path, "# House style\n\nNotes for a human.\n\n---\n\nBe brief.\n")
        assert agents.house_style(str(tmp_path)) == "Be brief."

    def test_a_file_with_no_rule_is_sent_whole(self, tmp_path):
        _write(tmp_path, "Be brief.")
        assert agents.house_style(str(tmp_path)) == "Be brief."

    def test_an_empty_file_switches_it_off(self, tmp_path):
        # The documented way to turn this off, so it needs to actually work.
        _write(tmp_path, "# House style\n\nnotes\n\n---\n\n   \n")
        assert agents.house_style(str(tmp_path)) == ""

    def test_no_file_at_all_is_not_an_error(self, tmp_path):
        assert agents.house_style(str(tmp_path)) == ""

    def test_a_runaway_file_is_capped_and_says_so(self, tmp_path):
        # This text is prepended to someone else's system prompt; a page of
        # tone instructions would crowd out the task.
        _write(tmp_path, "---\n" + ("word " * 2000))
        out = agents.house_style(str(tmp_path))
        assert len(out) <= agents.HOUSE_STYLE_CAP + 40
        assert "truncated" in out

    def test_a_new_chat_actually_carries_it(self):
        """The wiring, not just the reader: `chat_new` has to pass it as
        `system_append`, which is the console's one channel into how a CLI
        agent writes. Asserted against the source because building a live
        chat here would start a real process."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "server", "features", "agents_feature.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        assert "system_append=agents_mod.house_style(repo_root)" in source

    def test_the_shipped_file_is_short_and_says_something(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root = os.path.dirname(root)
        text = agents.house_style(root)
        assert text, "the shipped house style should not be empty"
        assert len(text) <= agents.HOUSE_STYLE_CAP
        # The specific failure it exists to prevent.
        assert "announce" in text.lower()
