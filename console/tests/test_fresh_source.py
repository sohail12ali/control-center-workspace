"""T-039: the JS-side [PY] acceptance criteria, pinned from source.

No JS runner in CI beyond the optional node slice in `test_fresh_core.py`, so
these read `overview.js`, `app.js`, `about.js`, `core.js`, `styles.css`,
`index.html` and pin that the seams exist and the safe shape is kept. They do
not run the code; what the page does in a browser is a [BROWSER] criterion
(T-039-12) and is NOT verified here.
"""

import os
import re

from server.paths import find_repo_root


def _read(rel):
    with open(os.path.join(find_repo_root(), *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


def _fn(src, name):
    """Source of the top-level `function name(` of an IIFE, up to its closing brace."""
    m = re.search(r"\n  function %s\(.*?\n  \}\n" % name, src, re.S)
    assert m, "no `function %s(`" % name
    return m.group(0)


OVERVIEW = _read("console/static/overview.js")
CORE = _read("console/static/core.js")
APP = _read("console/static/app.js")


def test_ac23_attention_rows_only_navigate():
    # The row builder, the "and N more" row and the key handler never write or clear.
    for name in ("attnGroup", "moreRow", "rowNav", "ofType"):
        body = _fn(OVERVIEW, name)
        assert "C.post(" not in body, name
        assert not re.search(r"dismiss|clear|done", body, re.I), name
    # The one POST in the file is the Jobs cancel button.
    assert OVERVIEW.count("C.post(") == 1
    assert OVERVIEW.index("C.post(") > OVERVIEW.index("function jobRow(")
    assert OVERVIEW.index("C.post(") < OVERVIEW.index("function jobsPanel(")


def test_enter_on_the_refresh_button_is_not_swallowed_by_rownav():
    # D-A: Enter on a button / inside the as-of row must not click the highlighted row.
    body = _fn(OVERVIEW, "rowNav")
    click = body.index("rows[idx].click()")
    guard = body[:click]
    assert re.search(r"tagName === \"BUTTON\"", guard), "no button-target guard before the click"
    assert re.search(r"closest\(\s*\"\.fresh-row\"\s*\)", guard), "no .fresh-row guard before the click"
    # The earlier guards are kept.
    assert "\"INPUT\"" in guard and "\"TEXTAREA\"" in guard
    assert re.search(r"closest\(\s*\"header\"\s*\)", guard)
    assert re.search(r"contains\(\s*\"collapsed\"\s*\)", guard)


def test_ac51_two_attention_panels_and_seven_overview_ids():
    ids = re.findall(r"collapse:\s*\{\s*id:\s*\"(ov\.[\w-]+)\"", OVERVIEW)
    assert sorted(ids) == sorted(
        ["ov.glance", "ov.needsyou", "ov.attention", "ov.flow", "ov.recent", "ov.jobs", "ov.schedules"])
    assert OVERVIEW.index("var needsPanel") < OVERVIEW.index("var attnPanel")
    assert '"Needs you"' in OVERVIEW and '"Needs repair"' in OVERVIEW
    assert "Needs attention" not in OVERVIEW


def test_ac55_about_names_needs_you():
    about = _read("console/static/about.js")
    line = next(l for l in about.splitlines() if l.strip().startswith("overview:"))
    assert "Needs you" in line
    assert "blocked, stale and unowned work" not in line


def test_ac61_the_badge_counts_needs_you_only():
    start = APP.index('if (hasTab("overview"))')
    block = APP[start:APP.index('if (hasTab("todos"))', start)]
    assert "needs_you" in block
    for old in ("c.blocked", "c.stale", "c.unowned", "c.runs", "c.approvals", "c.questions"):
        assert old not in block, old
    assert "item needs you" in block and "items need you" in block
    assert "aria-label" in APP
    # AC-6.3: the badge loop is the existing one.
    assert "setInterval(refreshBadges, 30000)" in APP


def test_ac101_overview_adds_no_timer():
    assert "setInterval" not in OVERVIEW and "setTimeout" not in OVERVIEW


def test_refresh_fetches_first_and_never_blanks_the_page():
    body = _fn(OVERVIEW, "refresh")
    assert 'C.get("/api/overview")' in body and "C.load(" not in body
    # The page is cleared only inside the success callback, before paint.
    assert body.index("C.clear(host)") > body.index(".then(function (d)")
    assert body.index("C.clear(host)") < body.index("paint(host, d, api)")
    assert "C.toast(" in body
    # No Refresh button in a static export.
    assert "C.IS_STATIC ? null" in _fn(OVERVIEW, "paint")


def test_ac81_each_panel_gets_its_own_as_of_source():
    paint = _fn(OVERVIEW, "paint")
    assert "asOf: d.generated_at" in paint
    assert len(re.findall(r"fresh: fresh\b", paint)) == 5      # glance, you, repair, flow, recent
    assert "asOf: fetchedAt" in _fn(OVERVIEW, "jobsPanel") and "Date.now()" in _fn(OVERVIEW, "jobsPanel")
    assert "asOf: fetchedAt" in _fn(OVERVIEW, "schedulesPanel")


def test_ac91_the_threshold_preference_is_read_in_core():
    assert re.search(r"prefs\.get\(\s*\"staleAfterSecs\"\s*\)", CORE)


def test_ac121_exactly_one_freshness_interval_with_a_stop_path():
    assert len(re.findall(r"setInterval\(", CORE)) == 1
    start = CORE.index("function freshStart")
    assert CORE.index("setInterval(") > CORE.index("panel freshness (T-039)")
    assert CORE.index("setInterval(") - start < 200, "the interval is not in freshStart"
    assert re.search(r"function freshStart\(\) \{ if \(freshTimer === null\) freshTimer = setInterval\(", CORE), "no double-start guard"
    assert re.search(r"function freshStop\(\) \{ if \(freshTimer !== null\) \{ clearInterval\(freshTimer\); freshTimer = null;", CORE)
    tick = _fn(CORE, "freshTick")
    for request in ("fetch(", "rawGet(", "post(", "XMLHttpRequest"):
        assert request not in tick, request
    assert re.findall(r"\w+\.get\(", tick) == ["prefs.get("]


def test_ac131_time_element_and_status_role():
    build = _fn(CORE, "freshBuild")
    assert 'el("time")' in build and 'role: "status"' in build
    assert 'setAttribute("datetime"' in _fn(CORE, "freshPaint")


def test_the_marks_have_css_rules():
    css = _read("console/static/styles.css")
    for cls in ("fresh-mark", "fresh-row"):
        assert re.search(r"\.%s\b" % cls, css), cls


def test_nfr3_no_new_script_and_order_kept():
    html = _read("console/static/index.html")
    srcs = re.findall(r"<script src=\"([^\"]+)\"", html)
    assert not [s for s in srcs if "fresh" in s]
    assert not [n for n in os.listdir(os.path.join(find_repo_root(), "console", "static")) if "fresh" in n]
    assert srcs.index("core.js") < srcs.index("overview.js") < srcs.index("app.js")
    assert len(srcs) == len(set(srcs))


def test_nfr5_no_new_dependency():
    req = _read("console/requirements-dev.txt")
    pkgs = [l.strip() for l in req.splitlines() if l.strip() and not l.startswith("#")]
    assert pkgs == ["pytest>=8.0"]
    root = find_repo_root()
    assert not os.path.exists(os.path.join(root, "console", "package.json"))
