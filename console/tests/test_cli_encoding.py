"""The CLI must not die on its own output.

`kanban.py context T-031` crashed with `'charmap' codec can't encode character
'\\u2192'` whenever stdout was a pipe or redirect on Windows without UTF-8 mode:
Python picks the ANSI code page (cp1252) there, and cp1252 has no arrow. Ticket
text is full of arrows and em dashes, and `context` is read at the start of
every agent turn, so the fix lives at CLI entry (`kanban._utf8_output`) rather
than in any one verb or in the digest's wording.
"""

import io
import os
import subprocess
import sys

import pytest

import kanban
from server import tickets

CONSOLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANBAN = os.path.join(CONSOLE_DIR, "kanban.py")

# U+2192 is the character from the field report; cp1252 cannot encode it.
ARROW = "→"

PROGRESS = """\
# Progress: CC-T001

## Dated Log

### 2026-10-05
- Done: Stage: kickoff %s GROUND (handoff pass)
""" % ARROW


@pytest.fixture
def ticket(repo):
    tickets.create(repo, "CC-T001", "A ticket", owner="Sam")
    folder = tickets.dir_for(repo, "CC-T001")
    with open(os.path.join(folder, "CC-T001-progress.md"), "w",
              encoding="utf-8") as fh:
        fh.write(PROGRESS)
    return repo


def _run_cli(repo, *argv):
    """Run the real script the way an agent's shell does: a child process with
    piped stdio, the legacy Windows code page forced, UTF-8 mode off."""
    env = dict(os.environ)
    env.update({"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0",
                "CONSOLE_REPO_ROOT": repo})
    return subprocess.run([sys.executable, KANBAN, *argv], cwd=repo, env=env,
                          capture_output=True, timeout=120)


class TestCliUnderLegacyCodePage:
    def test_context_exits_zero_and_emits_the_arrow_as_utf8(self, ticket):
        proc = _run_cli(ticket, "context", "CC-T001")
        stderr = proc.stderr.decode("utf-8", "replace")
        assert proc.returncode == 0, stderr
        assert "charmap" not in stderr
        out = proc.stdout.decode("utf-8")
        assert "kickoff %s GROUND" % ARROW in out

    def test_error_text_reaches_stderr_as_utf8_not_escaped(self, ticket):
        # stderr never raised (it backslash-escapes), but an escaped id is
        # unreadable — and agents read this line to decide what to do next.
        proc = _run_cli(ticket, "context", "X%sY" % ARROW)
        assert proc.returncode == 1
        err = proc.stderr.decode("utf-8")
        assert "X%sY" % ARROW in err
        assert "\\u2192" not in err


class TestUtf8Output:
    @staticmethod
    def _cp1252_stream():
        raw = io.BytesIO()
        return raw, io.TextIOWrapper(raw, encoding="cp1252", newline="\n")

    def test_a_cp1252_stdout_is_switched_to_utf8(self, monkeypatch):
        raw, stream = self._cp1252_stream()
        monkeypatch.setattr(sys, "stdout", stream)
        # Control: this is the crash, before the helper runs.
        with pytest.raises(UnicodeEncodeError):
            stream.write(ARROW)
            stream.flush()
        raw.seek(0)
        raw.truncate()

        kanban._utf8_output()
        print(ARROW)
        stream.flush()
        assert raw.getvalue() == (ARROW + "\n").encode("utf-8")

    def test_stderr_is_switched_too(self, monkeypatch):
        raw, stream = self._cp1252_stream()
        monkeypatch.setattr(sys, "stderr", stream)
        kanban._utf8_output()
        print(ARROW, file=sys.stderr)
        stream.flush()
        assert raw.getvalue() == (ARROW + "\n").encode("utf-8")

    def test_an_unencodable_character_degrades_instead_of_raising(self, monkeypatch):
        raw, stream = self._cp1252_stream()
        monkeypatch.setattr(sys, "stdout", stream)
        kanban._utf8_output()
        print("a\ud800b")  # a lone surrogate cannot be UTF-8 encoded
        stream.flush()
        assert raw.getvalue() == b"a?b\n"

    def test_a_stream_that_cannot_reconfigure_is_left_alone(self, monkeypatch):
        sink = io.StringIO()  # what an in-process redirect looks like
        monkeypatch.setattr(sys, "stdout", sink)
        kanban._utf8_output()  # must not raise
        print(ARROW)
        assert sink.getvalue() == ARROW + "\n"
