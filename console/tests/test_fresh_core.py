"""T-039: the panel-freshness helpers in core.js.

The helpers are pure and self-contained, so when `node` exists they are sliced
out of the file by name and run (AC-7.2, AC-9.2). Without node those tests skip
and the source tests below still pin that the functions exist; the browser
behaviour is a separate [BROWSER] check (T-039-12).
"""

import json
import os
import re
import shutil
import subprocess

import pytest

from server.paths import find_repo_root

_NODE = shutil.which("node")
_HELPERS = ("freshParse", "freshState", "freshThreshold", "freshAge")


def _read(rel):
    with open(os.path.join(find_repo_root(), *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def core():
    return _read("console/static/core.js")


def _slice(core, name):
    m = re.search(r"\n  function %s\(.*?\n  \}\n" % name, core, re.S)
    assert m, "core.js has no `function %s(`" % name
    return m.group(0)


def _run(core, expr):
    source = "".join(_slice(core, n) for n in _HELPERS) + "\nconsole.log(JSON.stringify(%s));" % expr
    out = subprocess.run([_NODE, "-e", source], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_the_helpers_exist_as_named_functions(core):
    for name in _HELPERS:
        _slice(core, name)


def test_the_helpers_sit_outside_the_reload_holds_block(core):
    # test_reload_source.py pins that block as timer-free.
    block = core[core.index("/* ---------------- reload holds"):core.index("/* ---------------- fetch")]
    assert "freshState" not in block


def test_the_preference_key_is_in_core_and_not_read_by_the_server(core):
    assert "staleAfterSecs" in core
    server = os.path.join(find_repo_root(), "console", "server")
    for base, _dirs, files in os.walk(server):
        for name in files:
            if name.endswith(".py"):
                with open(os.path.join(base, name), encoding="utf-8") as fh:
                    assert "staleAfterSecs" not in fh.read(), name


def test_no_arrow_function_even_in_a_comment(core):
    assert "=>" not in core


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_ac72_the_threshold_is_stale_at_the_limit_not_below_it(core):
    got = _run(core, "[freshState(0, 299000, 300).stale, freshState(0, 300000, 300).stale,"
                     " freshState(0, 300000, 300).ageSecs]")
    assert got == [False, True, 300]


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_ac72_a_future_time_has_age_zero_and_nan_is_stale(core):
    got = _run(core, "[freshState(5000, 1000, 300), freshState(NaN, 1000, 300),"
                     " freshState(null, 1000, 300).stale, freshState(undefined, 1000, 300).stale]")
    assert got == [{"ageSecs": 0, "stale": False}, {"ageSecs": None, "stale": True}, True, True]


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_ac92_a_bad_preference_means_the_default(core):
    got = _run(core, "[freshThreshold(29), freshThreshold(86401), freshThreshold('abc'),"
                     " freshThreshold(NaN), freshThreshold(null), freshThreshold(undefined),"
                     " freshThreshold(30), freshThreshold(86400), freshThreshold(120)]")
    assert got == [300, 300, 300, 300, 300, 300, 30, 86400, 120]


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_a_panels_own_threshold_wins_over_the_preference(core):
    assert _run(core, "[freshThreshold(120, 45), freshThreshold(120, 0), freshThreshold(120, 'x')]") == [45, 120, 120]


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_ac74_the_age_text_steps(core):
    got = _run(core, "[freshAge(0), freshAge(59), freshAge(60), freshAge(3599), freshAge(3600),"
                     " freshAge(48 * 3600 - 1), freshAge(48 * 3600), freshAge(null)]")
    assert got == ["just now", "just now", "1 min ago", "59 min ago", "1 h ago",
                   "47 h ago", "2 days ago", "unknown"]


@pytest.mark.skipif(not _NODE, reason="node is not installed")
def test_parse_takes_iso_strings_and_epoch_numbers(core):
    got = _run(core, "[freshParse('2026-10-06T00:00:00Z'), freshParse(1000), freshParse('nope') !== freshParse('nope'),"
                     " freshParse(undefined) !== freshParse(undefined)]")
    assert got == [1791244800000, 1000, True, True]
