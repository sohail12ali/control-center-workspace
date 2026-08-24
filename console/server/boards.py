"""Loads console.toml and per-board-kind config/boards/*.toml.

No hardcoded lane vocabulary and no hardcoded ticket-id prefix anywhere in
this module — every project-specific detail lives in the TOML files under
console/config/, so a fork edits config, not code.
"""

import os

from . import tomlio
from .paths import find_repo_root

_console_cache = {}
_board_cache = {}


def _config_dir(repo_root):
    return os.path.join(repo_root, "console", "config")


def load_console_config(repo_root=None):
    repo_root = repo_root or find_repo_root()
    if repo_root in _console_cache:
        return _console_cache[repo_root]
    path = os.path.join(_config_dir(repo_root), "console.toml")
    data = tomlio.load(path)
    _console_cache[repo_root] = data
    return data


def load_board_config(kind, repo_root=None):
    repo_root = repo_root or find_repo_root()
    key = (repo_root, kind)
    if key in _board_cache:
        return _board_cache[key]
    path = os.path.join(_config_dir(repo_root), "boards", f"{kind}.toml")
    if not os.path.isfile(path):
        raise ValueError(f"unknown board kind: {kind!r} (no config/boards/{kind}.toml)")
    data = tomlio.load(path)
    _board_cache[key] = data
    return data


def all_board_kinds(repo_root=None):
    repo_root = repo_root or find_repo_root()
    boards_dir = os.path.join(_config_dir(repo_root), "boards")
    return sorted(f[:-5] for f in os.listdir(boards_dir) if f.endswith(".toml"))


def enabled_boards(repo_root=None):
    cfg = load_console_config(repo_root)
    return list(cfg.get("general", {}).get("enabled_boards", []))


def lanes_for(kind, repo_root=None):
    """Lane list in board order. Optional per-lane flags, all defaulting off:

    - `terminal`  — work here is finished; excluded from "open work" counts
                    and from the nav badge, so a done column doesn't read as
                    a backlog.
    - `wip`       — soft limit; the UI warns above it rather than blocking,
                    because a board that refuses a move just gets bypassed.
    - `tone`      — a status colour name (ok/warn/danger/info) for the lane
                    header, so "Blocked" can look blocked.
    """
    cfg = load_board_config(kind, repo_root)
    out = []
    for lane in cfg.get("lanes", []):
        out.append(
            {
                "id": lane["id"],
                "label": lane["label"],
                "terminal": bool(lane.get("terminal", False)),
                "wip": lane.get("wip"),
                "tone": lane.get("tone", ""),
            }
        )
    return out


def board_label(kind, repo_root=None):
    cfg = load_board_config(kind, repo_root)
    return cfg.get("board", {}).get("label", kind)


def show_trackers_for(kind, repo_root=None):
    cfg = load_board_config(kind, repo_root)
    return list(cfg.get("card", {}).get("show_trackers", []))


def valid_stage(kind, stage, repo_root=None):
    return any(lane["id"] == stage for lane in lanes_for(kind, repo_root))
