"""Shared fixtures.

Every test runs against a throwaway workspace root under `tmp_path`, never the
real vault. That is not politeness: `tickets`/`trackers` write TOML through
`atomic_write`, and a test pointed at the checkout would mutate real tickets.

`paths.find_repo_root()` identifies a root by the presence of `knowledge-center/`
and `console/` as siblings, so a fixture root only has to create those two plus
the config files under test.
"""

import os
import sys

import pytest

CONSOLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CONSOLE_DIR not in sys.path:
    sys.path.insert(0, CONSOLE_DIR)

CONSOLE_TOML = """\
[general]
data_root      = "knowledge-center/artifacts"
id_pattern     = "^[A-Z][A-Za-z0-9-]{1,31}$"
host           = "127.0.0.1"
port           = 8790
enabled_boards = ["tickets"]
"""

TICKETS_BOARD = """\
[board]
kind    = "tickets"
label   = "Tickets"
enabled = true

[[lanes]]
id = "open"
label = "Open"

[[lanes]]
id = "in-progress"
label = "In Progress"
wip = 3

[[lanes]]
id = "blocked"
label = "Blocked"
tone = "danger"

[[lanes]]
id = "done"
label = "Done"
terminal = true

[card]
show_trackers = ["questions", "bugs"]
"""

# Two rows covering the transport axis that actually changes behaviour: a
# stream_json backend whose one-shot form is a separate template, and a resume
# backend whose per-turn form doubles as one.
AGENTS_TOML = """\
[[backend]]
id = "alpha"
label = "Alpha CLI"
command = "alpha-cli"
transport = "stream_json"
prompt_prefix_style = "slash"
session_args = ["-p", "--model", "{model}", "--permission-mode", "{mode}"]
oneshot_args = ["-p", "{prompt}", "--permission-mode", "{mode}", "--model", "{model}"]
add_dir_args = ["--add-dir", "{dir}"]
modes = ["plan", "default"]
default_mode = "plan"
models = ["big", "small"]
gated_tools = ["Bash", "Write"]

[backend.model_labels]
big = "Big Model"

[backend.mode_blurbs]
plan = "read-only"

[[backend]]
id = "beta"
label = "Beta CLI"
command = "beta-cli"
transport = "resume"
prompt_prefix_style = "inline"
turn_args = ["-p", "{prompt}", "--mode", "{mode}"]
resume_args = ["-p", "{prompt}", "--resume", "{resume_id}"]
modes = ["ask", "default"]
default_mode = "ask"

[[backend]]
id = "disabled-row"
label = "Off"
command = "nope"
transport = "oneshot"
enabled = false
oneshot_args = ["{prompt}"]
"""


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _clear_caches():
    """Config loaders memoise per repo root in module-level dicts. tmp_path
    gives each test a fresh root so collisions are unlikely, but a stale entry
    would be a maddening cross-test failure, so clear them explicitly."""
    from server import agent_backends, boards
    boards._console_cache.clear()
    boards._board_cache.clear()
    agent_backends._cache.clear()


@pytest.fixture
def repo(tmp_path):
    """A minimal but valid workspace root. Returns its path as a string."""
    root = str(tmp_path / "ws")
    os.makedirs(os.path.join(root, "knowledge-center", "artifacts"))
    _write(os.path.join(root, "console", "config", "console.toml"), CONSOLE_TOML)
    _write(os.path.join(root, "console", "config", "boards", "tickets.toml"), TICKETS_BOARD)
    _write(os.path.join(root, "console", "config", "agents.toml"), AGENTS_TOML)
    _clear_caches()
    yield root
    _clear_caches()
