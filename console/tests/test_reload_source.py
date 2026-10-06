"""T-036: the reload-when-safe half of the page, pinned from source.

Same pattern and the same limits as `test_prefs_client_source.py`: no JS
runner in CI and no Node on the CI image, so these are source-regexp tests
(pattern of `test_plugins.py:227-285`). They pin that the seams exist and that
the shape that makes them safe has not been lost; they do not run the code.
What it does in a browser (AC-10 .. AC-16, AC-68) is a [BROWSER] criterion that
a person or a driven browser has to check, and the progress entries say so.

Task 15 (this file starts here): the hold registry in `core.js` and its two
registrants. Task 16 adds the version compare and the notice in `app.js`;
tasks 17 and 18 add the busy predicate and the loop guard.
"""

import os
import re

import pytest

from server.paths import find_repo_root


def _read(rel):
    with open(os.path.join(find_repo_root(), *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


def _static_js():
    """Every shipped script as {name: source}."""
    folder = os.path.join(find_repo_root(), "console", "static")
    out = {}
    for name in sorted(os.listdir(folder)):
        if name.endswith(".js"):
            out[name] = _read("console/static/" + name)
    return out


def _depth_at(src, index):
    """Brace depth just before `index`, ignoring comments and string literals.

    Returns (depth_at_index, depth_at_end). A caller that sees depth_at_end != 0
    knows the scanner lost its place (a regex literal holding a lone brace is
    the usual cause) and must not trust depth_at_index.
    """
    depth, at, i, n = 0, None, 0, len(src)
    while i < n:
        if i == index:
            at = depth
        two = src[i:i + 2]
        ch = src[i]
        if two == "//":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if two == "/*":
            end = src.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            while i < n and src[i] != quote:
                i += 2 if src[i] == "\\" else 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return at, depth


def _skip_literal(src, i):
    """If a comment or string literal starts at `i`: (index just past it, is_comment)."""
    two, n = src[i:i + 2], len(src)
    if two == "//":
        end = src.find("\n", i)
        return (n if end < 0 else end), True
    if two == "/*":
        end = src.find("*/", i + 2)
        return (n if end < 0 else end + 2), True
    if src[i] in "\"'`":
        j = i + 1
        while j < n and src[j] != src[i]:
            j += 2 if src[j] == "\\" else 1
        return j + 1, False
    return None


def _strip_comments(src):
    """The code with comments removed and string literals kept."""
    out, i = [], 0
    while i < len(src):
        lit = _skip_literal(src, i)
        if lit is None:
            out.append(src[i])
            i += 1
        else:
            if not lit[1]:
                out.append(src[i:lit[0]])
            i = lit[0]
    return "".join(out)


def _function_body(src, name):
    """The comment-free text between the braces of `function name(...) {...}`."""
    start = src.index("function %s(" % name)
    i = src.index("{", start)
    depth, j = 0, i
    while j < len(src):
        lit = _skip_literal(src, j)
        if lit is not None:
            j = lit[0]
            continue
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return _strip_comments(src[i + 1:j])
        j += 1
    raise AssertionError("no closing brace for function %s" % name)


def _squash(text):
    return re.sub(r"\s+", " ", text).strip()


@pytest.fixture(scope="module")
def core():
    return _read("console/static/core.js")


@pytest.fixture(scope="module")
def app():
    return _read("console/static/app.js")


@pytest.fixture(scope="module")
def version_section(app):
    """The `new UI version` section of app.js, comments removed."""
    start = app.index("/* ---------------- new UI version")
    end = app.index("/* ---------------- global keys")
    return _strip_comments(app[start:end])


# --------------------------------------------------------------------------
# Task 15: the hold registry
# --------------------------------------------------------------------------

def test_ac17_holdreload_is_defined_once_and_only_in_core():
    defined = {}
    pattern = re.compile(r"function\s+holdReload\b|\bholdReload\s*=\s*function\b|\bholdReload\s*:\s*function\b")
    for name, src in _static_js().items():
        found = pattern.findall(src)
        if found:
            defined[name] = len(found)
    assert defined == {"core.js": 1}, defined


def test_the_registry_is_exported_on_console_not_on_consoleapp(core, app):
    # D-11: tab scripts load before app.js creates ConsoleApp, so the registry
    # has to be on the kernel they already receive as `C`.
    export = core[core.rindex("\n  return {"):]
    assert re.search(r"\bholdReload: holdReload\b", export)
    assert re.search(r"\breloadHeld: reloadHeld\b", export)
    assert "ConsoleApp.holdReload" not in app
    assert "ConsoleApp.reloadHeld" not in app
    # Nothing was added to the ConsoleApp export for it either.
    m = re.search(r"window\.ConsoleApp\s*=\s*\{(.*?)\};", app, re.S)
    assert m, "app.js no longer exports window.ConsoleApp"
    assert "holdReload" not in m.group(1) and "reloadHeld" not in m.group(1)


@pytest.mark.parametrize("name,hold_id,state", [
    ("agents.js", "agents.drafts", "st.drafts"),
    ("todos.js", "todos.new", "st.newText"),
])
def test_ac17_each_tab_registers_one_hold_at_iife_top_level(name, hold_id, state):
    src = _static_js()[name]
    calls = [m.start() for m in re.finditer(r"\bholdReload\(", src)]
    assert len(calls) == 1, "%s must call holdReload( exactly once, found %d" % (name, len(calls))
    call = re.search(r'C\.holdReload\("%s",' % re.escape(hold_id), src)
    assert call, "%s does not register the id %r through C.holdReload" % (name, hold_id)
    # IIFE top level = brace depth 1 (inside `(function (C) {` only), so the
    # call runs while the script loads, before app.js exists.
    at, end = _depth_at(src, call.start())
    assert end == 0, "the scanner lost its place in %s (end depth %d)" % (name, end)
    assert at == 1, "%s registers its hold inside a function (depth %d)" % (name, at)
    # After `st` is defined, and over the state it names.
    assert src.index("var st = {") < call.start()
    body = src[call.start():src.index("\n\n", call.start())]   # the statement, up to the blank line
    assert state in body, "%s's hold does not read %s" % (name, state)
    assert ".trim()" in body, "%s's hold must treat blank text as not held" % name


def test_ac17_core_loads_before_the_tabs_and_the_router():
    html = _read("console/static/index.html")
    order = re.findall(r'<script src="([^"]+)"', html)
    for later in ("agents.js", "todos.js", "app.js"):
        assert later in order, "index.html does not load %s" % later
        assert order.index("core.js") < order.index(later), \
            "core.js must load before %s or its top-level holdReload throws" % later
    # app.js is last: it is the one that needs every tab registered.
    assert order.index("agents.js") < order.index("app.js")
    assert order.index("todos.js") < order.index("app.js")


def test_a_second_registration_with_the_same_id_replaces_the_first(core):
    # Idempotent by id: a keyed store, not a list that grows on every call.
    m = re.search(r"function holdReload\(id, fn\) \{(.*?)\}", core, re.S)
    assert m, "core.js no longer has `function holdReload(id, fn)`"
    assert re.search(r"_holds\[id\]\s*=\s*fn", m.group(1))
    assert ".push(" not in m.group(1)


def test_the_registry_reader_treats_a_throwing_hold_as_not_held(core):
    m = re.search(r"function reloadHeld\(\) \{(.*?)\n  \}\n", core, re.S)
    assert m, "core.js no longer has `function reloadHeld()`"
    body = m.group(1)
    assert ".some(" in body, "reloadHeld must be true when ANY hold is"
    assert re.search(r"try \{ return !!_holds\[id\]\(\); \} catch \(e\) \{ return false; \}", body), body


def test_the_kernel_has_no_timer_for_holds(core):
    # The registry is pulled by app.js on its existing heartbeat; it must not
    # grow a timer of its own (D-25).
    block = core[core.index("/* ---------------- reload holds"):core.index("/* ---------------- fetch")]
    assert "setTimeout(" not in block and "setInterval(" not in block


# --------------------------------------------------------------------------
# Task 16: record the boot stamp, compare, show the notice
# --------------------------------------------------------------------------

def test_ac8_the_boot_stamp_and_the_answers_are_both_read(app):
    check = _squash(_function_body(app, "checkVersion"))
    assert "versionOf(state.cfg)" in check, "the boot stamp is not read from state.cfg"
    assert "versionOf(cfg)" in check, "the stamp in the answer is not read"
    # The heartbeat no longer discards the payload: the handler runs the check
    # first, before the pending-writes early return can skip it.
    beat = _squash(_function_body(app, "onHeartbeat"))
    assert beat.startswith("checkVersion(cfg);"), beat
    assert beat.index("checkVersion(cfg)") < beat.index("C.prefs.pending()")
    # Every /api/config request is the boot one or hands its answer to onHeartbeat.
    code = _strip_comments(app)
    asks = [m.start() for m in re.finditer(r'C\.get\("/api/config"\)', code)]
    assert len(asks) == 2, "expected the boot request and probe(), found %d" % len(asks)
    boots = [a for a in asks if code[:a].rstrip().endswith("Promise.all([")]
    beats = [a for a in asks if code[a:].startswith('C.get("/api/config").then(onHeartbeat)')]
    assert len(boots) == 1 and len(beats) == 1, "one boot request and one that hands its answer to onHeartbeat"
    # Read lazily from state.cfg: the boot chain itself is not touched.
    chain = code[code.index("Promise.all(["):code.index(".catch(function (err)")]
    assert "ui_version" not in chain and "checkVersion" not in chain


def test_ac9_connection_and_visibility_drive_probe_after_the_static_return(app, version_section):
    watch = _squash(_function_body(app, "watchConnection"))
    assert watch.index("if (C.IS_STATIC)") < watch.index("watchVersion()"), \
        "watchVersion() must come after the static early return, so an export registers nothing"
    assert "setInterval(probe, HEARTBEAT_MS)" in watch, "the heartbeat must use probe()"
    inside = _squash(_function_body(app, "watchVersion"))
    assert "C.onConnection(function (online) { if (online) probe(); })" in inside
    assert 'document.addEventListener("visibilitychange", function () { if (!document.hidden) probe(); })' in inside
    # Registered once even if watchConnection runs twice (boot failing after it ran).
    assert inside.startswith("if (versionWatched) return; versionWatched = true;")
    code = _strip_comments(app)
    assert len(re.findall(r"(?<!function )\bwatchVersion\(\)", code)) == 1, "watchVersion() has one caller"
    assert code.count("visibilitychange") == 1
    # The comparison itself is inert in a static export too (defence in depth).
    assert _squash(_function_body(app, "checkVersion")).startswith("if (C.IS_STATIC || !state.cfg) return;")


def test_d13_absent_then_present_and_the_other_cases_are_all_in_the_comparison(app):
    check = _squash(_function_body(app, "checkVersion"))
    # In order: nothing to compare when static or before boot; an answer with
    # no stamp is ignored (present-then-absent and absent-both-times); a boot
    # stamp that was absent makes the first stamp a change; otherwise compare.
    order = [
        "if (C.IS_STATIC || !state.cfg) return;",
        "var now = versionOf(cfg);",
        "if (!now) return;",
        "var boot = versionOf(state.cfg);",
        "if (!boot) versionPending = true;",
        "else versionPending = now !== boot;",
    ]
    at = -1
    for step in order:
        nxt = check.find(step, at + 1)
        assert nxt > at, "%r is missing or out of order in checkVersion: %s" % (step, check)
        at = nxt
    # A stamp is an identity, not an ordering; and an absent answer never clears
    # a pending change (nothing assigns false before the early return).
    assert "<" not in check and ">" not in check
    assert check.index("if (!now) return;") < check.index("versionPending =")
    version_of = _squash(_function_body(app, "versionOf"))
    assert 'typeof cfg.ui_version === "string"' in version_of and 'return cfg &&' in version_of


def test_ac69_the_notice_is_a_status_region_with_a_reload_now_button_and_no_toast(app, version_section):
    assert "Reload now" in app
    assert 'role: "status"' in app
    assert 'class: "ui-notice"' in app
    build = _squash(_function_body(app, "buildNotice"))
    # A real button (keyboard-operable by construction), wired to reloadNow.
    assert 'C.el("button", { class: "btn sm", type: "button", text: "Reload now", onclick: reloadNow })' in build
    # Appended to the page once, and text set after it is in the page.
    assert build.count("document.body.appendChild(notice)") == 1
    assert build.index("document.body.appendChild(notice)") < build.index('setNoticeText("ready")')
    show = _squash(_function_body(app, "showNotice"))
    assert "if (!notice) buildNotice();" in show
    # Not a toast: nothing in the section goes near C.toast or the toast host.
    assert "toast" not in version_section.lower()


def test_the_notice_wording_and_its_three_states(app, version_section):
    texts = dict(re.findall(r'\n\s+(ready|busy|paused): "([^"]+)"', version_section))
    assert set(texts) == {"ready", "busy", "paused"}, texts
    assert texts["ready"] == "A new version of the console is ready. It reloads when you pause."
    # D-20: while busy the notice says what Reload now would cost.
    assert "Unsaved text will be lost" in texts["busy"]
    assert "paused" in texts["paused"] and "Reload now" in texts["paused"]
    setter = _squash(_function_body(app, "setNoticeText"))
    assert "NOTICE_TEXT[mode]" in setter
    # Only on a real change, so a status region does not re-announce every beat.
    assert "if (noticeText.textContent !== text) noticeText.textContent = text;" in setter


def test_ac69_the_notice_style_exists_once_and_before_the_onboarding_block():
    css = _read("console/static/styles.css")
    rules = [m.start() for m in re.finditer(r"(?m)^\.ui-notice\s*\{", css)]
    assert len(rules) == 1, "`.ui-notice` must be defined exactly once at the top level"
    first_ob = re.search(r"\.ob-[a-z]", css)
    assert first_ob and rules[0] < first_ob.start(), \
        "the notice rule must sit mid-file, before the appended `.ob-*` block"
    # Stacking: above the sticky headers (20), below the drawer's scrim and panel
    # (so it can never cover the drawer's close button) and below the toasts.
    def z(selector):
        m = re.search(r"(?m)^%s\s*\{[^}]*?z-index:\s*(\d+)" % re.escape(selector), css, re.S)
        assert m, "no z-index on %s" % selector
        return int(m.group(1))
    notice = z(".ui-notice")
    assert z(".topbar") < notice < min(z(".scrim"), z(".drawer"), z(".toasts"))
    # Every hyphenated class the notice code applies has a rule.
    app = _read("console/static/app.js")
    for cls in re.findall(r'class:\s*"(ui-[a-z-]+)"', app):
        assert "." + cls in css, "%s is applied by app.js but has no rule" % cls


def test_ac66_the_version_check_adds_no_timer_and_no_request(app, version_section):
    # The same two timers app.js had at task 00: the heartbeat and refreshBadges
    # (setInterval), the search debounce (setTimeout).
    code = _strip_comments(app)
    assert code.count("setInterval(") == 2, code.count("setInterval(")
    assert code.count("setTimeout(") == 1, code.count("setTimeout(")
    for banned in ("setTimeout(", "setInterval(", "C.post(", "fetch(", "XMLHttpRequest", "sendBeacon", "EventSource"):
        assert banned not in version_section, "the version check must not use %s" % banned
    # The only request is the one the heartbeat already makes.
    assert re.findall(r"C\.get\(([^)]*)\)", version_section) == ['"/api/config"']


def test_reload_now_reloads_at_once_and_a_mismatch_alone_never_reloads(app, version_section):
    body = _squash(_function_body(app, "reloadNow"))
    assert body == "window.location.reload();", body     # no busy rule, no guard (BR-15, D-20)
    # Two reload calls in the section: this one and autoReload (task 17). A
    # mismatch alone calls neither; only the click or the idle rules do.
    assert version_section.count("location.reload(") == 2
    assert "sessionStorage" not in body


def test_nothing_of_the_version_check_leaks_onto_the_consoleapp_export(app):
    m = re.search(r"window\.ConsoleApp\s*=\s*\{(.*?)\};", app, re.S)
    assert m, "app.js no longer exports window.ConsoleApp"
    for name in ("checkVersion", "probe", "versionPending", "versionOf", "watchVersion",
                 "showNotice", "setNoticeText", "reloadNow", "NOTICE_TEXT"):
        assert name not in m.group(1), "%s must stay private to app.js" % name


# --------------------------------------------------------------------------
# Task 17: idle tracker, busy predicate, reload scheduler
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def reload_rules(app):
    """The reload-by-itself part of the section, comments removed."""
    start = app.index("/* ---- reloading by itself")
    end = app.index("/* ---------------- global keys")
    return _strip_comments(app[start:end])


def test_the_idle_constant_and_the_four_activity_events_without_pointermove(app, reload_rules):
    assert re.search(r"var IDLE_MS = 30000;", reload_rules)
    m = re.search(r"\[(.*?)\]\.forEach", _function_body(app, "watchActivity"), re.S)
    assert m
    assert re.findall(r'"([a-z]+)"', m.group(1)) == ["keydown", "pointerdown", "wheel", "touchstart"]
    assert "pointermove" not in _strip_comments(app)
    # Capture phase, so a handler that stops propagation cannot hide the person.
    assert re.search(r"lastActive = Date\.now\(\); \}, true\)", _squash(_function_body(app, "watchActivity")))


def test_the_typed_input_record_needs_a_trusted_event_and_a_weakset(app, reload_rules):
    assert "new WeakSet()" in reload_rules
    body = _squash(_function_body(app, "watchActivity"))
    m = re.search(r'addEventListener\("input", function \(e\) \{(.*?)\}, true\)', body)
    assert m, body
    assert "e.isTrusted" in m.group(1) and "typedInto.add(" in m.group(1)


def test_ac78_a_textarea_with_text_is_busy_without_the_typed_record(app):
    body = _function_body(app, "draftOpen")
    first = body[:body.index('"input, [contenteditable]"')]
    assert 'querySelectorAll("textarea")' in first and "hasText(" in first
    assert "typedInto" not in first      # dictation and the picker fire no input event


def test_ac70_inputs_count_only_when_typed_and_focus_counts_when_filled(app):
    body = _squash(_function_body(app, "draftOpen"))
    assert 'querySelectorAll("input, [contenteditable]")' in body
    assert "typedInto.has(list[i]) && isTextField(list[i]) && hasText(list[i])" in body
    assert "document.activeElement" in body and "isTextField(focused) && hasText(focused)" in body


def test_ac70_no_default_value_comparison_anywhere_in_app_js(app):
    assert "defaultValue" not in _strip_comments(app)


def test_every_busy_source_is_read_by_isbusy(app):
    body = _function_body(app, "isBusy")
    for needle in ("draftOpen()", '".drawer"', '".ob-scrim"', '".cp-scrim.on"', "ConsoleVoice",
                   "listening()", "speaking()", "C.reloadHeld()"):
        assert needle in body, needle


def test_the_busy_selectors_match_the_files_that_own_them():
    # CR-37: a rename in the owner must fail here, not in front of a user.
    wizard = os.path.join(find_repo_root(), "console", "static", "onboarding-wizard.js")
    if not os.path.exists(wizard):
        pytest.skip("onboarding-wizard.js is not in this checkout")
    assert 'class: "ob-scrim"' in _read("console/static/onboarding-wizard.js")
    palette = _read("console/static/palette.js")
    assert 'class: "cp-scrim"' in palette
    assert 'classList.add("on")' in palette and 'classList.remove("on")' in palette
    assert 'class: "drawer"' in _read("console/static/app.js")
    voice = _read("console/static/voice.js")
    assert "window.ConsoleVoice = " in voice
    assert re.search(r"listening: listening", voice) and re.search(r"speaking: speaking", voice)


def test_ac18_a_hidden_window_goes_at_the_next_check_with_idle_as_the_fallback(app):
    body = _squash(_function_body(app, "maybeReload"))
    assert "document.hidden || Date.now() - lastActive >= IDLE_MS" in body
    # Busy is decided first: hidden never overrides unsaved text.
    assert body.index("isBusy()") < body.index("document.hidden")
    assert '"busy"' in body and '"ready"' in body


def test_ac22_the_reload_primitive_is_location_reload(app):
    assert _squash(_function_body(app, "autoReload")).endswith("window.location.reload();")


def test_the_scheduler_runs_from_the_heartbeat_only_and_ignores_stampless_answers(app):
    beat = _squash(_function_body(app, "onHeartbeat"))
    assert beat.index("checkVersion(cfg);") < beat.index("maybeReload(cfg);") < beat.index("C.prefs.pending()")
    assert _strip_comments(app).count("maybeReload(") == 2     # the definition and that one call
    # An answer without a stamp (server flapping, older server) never reloads.
    assert "!versionOf(cfg)" in _function_body(app, "maybeReload")
    assert "versionPending" in _function_body(app, "maybeReload")


def test_ac66_the_scheduler_adds_no_timer_and_no_request(app, reload_rules):
    code = _strip_comments(app)
    assert code.count("setInterval(") == 2 and code.count("setTimeout(") == 1
    for banned in ("setTimeout(", "setInterval(", "C.post(", "C.get(", "fetch(", "XMLHttpRequest", "sendBeacon"):
        assert banned not in reload_rules, banned


def test_activity_listeners_register_only_after_the_static_return(app):
    watch = _squash(_function_body(app, "watchVersion"))
    assert "watchActivity();" in watch
    conn = _squash(_function_body(app, "watchConnection"))
    assert conn.index("C.IS_STATIC") < conn.index("watchVersion();")



# --------------------------------------------------------------------------
# Task 18: the loop guard
# --------------------------------------------------------------------------
def test_ac19_the_guard_counts_three_in_five_minutes_in_session_storage(app):
    code = _strip_comments(app)
    assert 'var RELOAD_KEY = "console-reload";' in code
    assert "var RELOAD_LIMIT = 3;" in code and "var RELOAD_WINDOW_MS = 300000;" in code
    body = _squash(_function_body(app, "recentReloads"))
    assert "window.sessionStorage.getItem(RELOAD_KEY)" in body
    assert "now - at < RELOAD_WINDOW_MS" in body                 # old entries fall out
    assert "JSON.parse(" in body and "Array.isArray(list)" in body  # corrupt or odd values read as none


def test_ac19_the_pause_branch_comes_before_the_reload_and_stores_before_reloading(app):
    body = _squash(_function_body(app, "autoReload"))
    pause = body.index("recent.length >= RELOAD_LIMIT")
    assert pause < body.index("setItem(") < body.index("window.location.reload();")
    assert 'setNoticeText("paused"); return;' in body[pause:body.index("recent.push(")]
    assert body.endswith("window.location.reload();")


def test_ac19_unreadable_or_unwritable_storage_does_not_reload(app):
    # A guard that cannot count cannot bound a loop, and an in-memory count dies
    # with the page it is counting: so no automatic reload at all.
    read = _squash(_function_body(app, "recentReloads"))
    assert "catch (e) { return null; }" in read
    body = _squash(_function_body(app, "autoReload"))
    assert "if (!recent ||" in body
    assert re.search(r'catch \(e\) \{ setNoticeText\("paused"\); return; \}', body)
    assert "!recent ||" in _function_body(app, "reloadPaused")


def test_d14_the_guard_compares_no_target_version(app):
    guard = _strip_comments(app[app.index("/* ---- the loop guard ----"):app.index("/* ---------------- global keys")])
    assert not re.search(r"\.to\b|\bto\s*:", guard)
    assert "ui_version" not in guard and "versionOf" not in guard


def test_a_manual_reload_never_touches_the_guard_and_the_notice_keeps_its_button(app, version_section):
    body = _function_body(app, "reloadNow")
    for name in ("RELOAD_KEY", "RELOAD_LIMIT", "sessionStorage", "autoReload", "recentReloads", "reloadPaused"):
        assert name not in body, name
    assert 'paused: "' in version_section and "Automatic reload is paused" in version_section
    # Only the scheduler reaches autoReload; the button is reloadNow.
    assert _strip_comments(app).count("autoReload(") == 2     # definition + the scheduler's call
    assert "onclick: reloadNow" in version_section


def test_the_paused_wording_is_kept_while_busy_or_waiting_so_the_text_does_not_flap(app):
    body = _squash(_function_body(app, "maybeReload"))
    assert body.count('reloadPaused() ? "paused" :') == 2
