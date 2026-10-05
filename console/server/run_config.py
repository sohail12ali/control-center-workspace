"""T-020 NFR-10: Run-layer thresholds read from `console.toml`, code defaults.

Sections: `[runs]`, `[runs.retry]`, `[claims]`, `[review]`. Read-only: nothing here
writes a config file (BR-12). A bad value never raises; it falls back to the
default and warns once per (section, key, value) on stderr.
"""

import math
import sys

from . import boards

# Session-identity / nesting variables. Never auth or user-intent variables
# (decision a5): ANTHROPIC_*, CLAUDE_CODE_OAUTH_*, CLAUDE_CODE_USE_*,
# CLAUDE_CODE_MAX_OUTPUT_TOKENS are not listed.
DEFAULT_ENV_STRIP = (
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION",
    "CLAUDE_CODE_PARENT_SESSION", "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_HOST_SESSION_ID",
    "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_EXECPATH", "CLAUDE_PID",
)

_warned = set()


def reset_warnings():
    _warned.clear()


def _warn(section, key, value, default, why):
    mark = (section, key, repr(value))
    if mark in _warned:
        return
    _warned.add(mark)
    print(f"console.toml [{section}] {key} = {value!r} {why}; using {default!r}",
          file=sys.stderr)


def _num_ok(v, integer, minimum):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    if isinstance(v, float) and (integer or not math.isfinite(v)):
        return False
    return v >= minimum


def _number(cfg, section, key, default, *, integer=False, minimum=0):
    if key not in cfg:
        return default
    v = cfg[key]
    if _num_ok(v, integer, minimum):
        return v
    _warn(section, key, v, default, "is not a valid number")
    return default


def _flag(cfg, section, key, default):
    if key not in cfg:
        return default
    if isinstance(cfg[key], bool):
        return cfg[key]
    _warn(section, key, cfg[key], default, "is not true or false")
    return default


def _list(cfg, section, key, default, item_ok, *, allow_empty):
    if key not in cfg:
        return list(default)
    v = cfg[key]
    if isinstance(v, list) and (v or allow_empty) and all(item_ok(i) for i in v):
        return list(v)
    _warn(section, key, v, list(default), "is not a valid list")
    return list(default)


def _section(repo_root, name):
    try:
        data = boards.load_console_config(repo_root)
    except (OSError, ValueError) as exc:
        _warn("console", "console.toml", str(exc), {}, "is unreadable")
        return {}
    sect = data.get(name, {})
    if isinstance(sect, dict):
        return sect
    _warn(name, name, sect, {}, "is not a table")
    return {}


def _is_name(v):
    return isinstance(v, str) and bool(v)


def _is_delay(v):
    return _num_ok(v, False, 0)


def runs_cfg(repo_root=None):
    c = _section(repo_root, "runs")
    out = {
        "stall_suspect_secs": _number(c, "runs", "stall_suspect_secs", 600),
        "stall_kill_secs": _number(c, "runs", "stall_kill_secs", 1800),
        "watch_interval_secs": _number(c, "runs", "watch_interval_secs", 15),
        "watchdog_enabled": _flag(c, "runs", "watchdog_enabled", True),
        "max_line_bytes": _number(c, "runs", "max_line_bytes", 1048576, integer=True),
        "max_turn_output_bytes": _number(c, "runs", "max_turn_output_bytes",
                                         67108864, integer=True),
        "linger_grace_secs": _number(c, "runs", "linger_grace_secs", 5),
        "quota_parse_horizon_secs": _number(c, "runs", "quota_parse_horizon_secs", 8 * 86400),
        "env_strip": _list(c, "runs", "env_strip", DEFAULT_ENV_STRIP, _is_name,
                           allow_empty=True),
    }
    # 0 means flag-only (never kill); otherwise the kill must come after the flag.
    if out["stall_kill_secs"] and out["stall_kill_secs"] <= out["stall_suspect_secs"]:
        _warn("runs", "stall_kill_secs", out["stall_kill_secs"], 1800,
              "is not above stall_suspect_secs")
        out["stall_suspect_secs"], out["stall_kill_secs"] = 600, 1800
    return out


_RETRY_CLASSES = {
    "transient_upstream": (2, [30, 120]),
    "quota": (2, [60]),
    "max_turns": (2, [1]),
    "process_lost": (1, [10]),
}


def retry_cfg(repo_root=None):
    runs = _section(repo_root, "runs")
    c = runs.get("retry", {})
    if not isinstance(c, dict):
        _warn("runs", "retry", c, {}, "is not a table")
        c = {}
    classes = {}
    for name, (dmax, ddelays) in _RETRY_CLASSES.items():
        classes[name] = {
            "max": _number(c, "runs.retry", f"{name}_max", dmax, integer=True),
            "delays": _list(c, "runs.retry", f"{name}_delays", ddelays, _is_delay,
                            allow_empty=False),
        }
    return {
        "max_total_retries": _number(runs, "runs", "max_total_retries", 3, integer=True),
        "quota_max_wait_secs": _number(c, "runs.retry", "quota_max_wait_secs", 21600),
        "classes": classes,
    }


def claims_cfg(repo_root=None):
    c = _section(repo_root, "claims")
    return {
        "ttl_secs": _number(c, "claims", "ttl_secs", 28800),
        "dead_grace_secs": _number(c, "claims", "dead_grace_secs", 60),
    }


def review_cfg(repo_root=None):
    c = _section(repo_root, "review")
    return {"max_rounds": _number(c, "review", "max_rounds", 3, integer=True, minimum=1)}
