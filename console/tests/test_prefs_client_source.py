"""T-036: the browser half of preferences, pinned from source.

There is no JS runner in CI and no Node on the CI image, so these are
source-regexp tests in the pattern of `test_plugins.py:227-285`. They pin that
the contract exists and that the shape that makes it safe has not been lost; they
do not run the code. What it does in a browser is a [BROWSER] criterion that a
person or a driven browser has to check, and the task's progress entry says so.

Task 07 (this file starts here) is the read side of `C.prefs` in `core.js`.
Later tasks extend this file: write-through (08), migration and Reset (09), the
router in `app.js` (10).
"""

import os
import re

import pytest

from server.paths import find_repo_root


def _read(rel):
    with open(os.path.join(find_repo_root(), *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def core():
    return _read("console/static/core.js")


@pytest.fixture(scope="module")
def prefs_block(core):
    """The `var prefs = {...};` object, which is where the public members live."""
    m = re.search(r"\n  var prefs = \{\n(.*?)\n  \};\n", core, re.S)
    assert m, "core.js no longer has a `var prefs = {...};` block"
    return m.group(1)


def test_ac37_the_old_three_keep_their_signatures(prefs_block):
    # Every caller in the tabs is written against these; changing one is a
    # change to the whole console.
    assert "get: function (key, fallback)" in prefs_block
    assert "set: function (key, val)" in prefs_block
    assert "del: function (key)" in prefs_block


def test_ac37_the_new_members_exist(prefs_block):
    # AC-37 in full: the old three plus everything the page needs from the store.
    for member in ("hydrate", "refresh", "all", "keys", "reset", "mode", "rev",
                   "onChange", "pending", "flush"):
        assert re.search(r"\n    %s: " % member, "\n" + prefs_block), \
            "C.prefs has no `%s`" % member


def test_prefs_stays_exported_unchanged(core):
    assert re.search(r"\n    prefs: prefs,", core), "C.prefs is no longer exported as `prefs`"


def test_ac74_the_bound_and_the_server_limits_are_mirrored(core):
    # The server refuses keys and values outside these (prefs_store.py), so the
    # page carries the same numbers and never sends one it knows will be a 400.
    assert "var HYDRATE_BOUND_MS = 3000;" in core
    assert "/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/" in core
    assert "var PREF_MAX_BYTES = 32768;" in core


def test_the_mirrored_limits_match_the_servers():
    from server import prefs_store
    core = _read("console/static/core.js")
    assert prefs_store.KEY_PATTERN in core, "core.js key pattern drifted from prefs_store.KEY_PATTERN"
    assert re.search(r"PREF_MAX_BYTES = %d;" % prefs_store.MAX_VALUE_BYTES, core), \
        "core.js value cap drifted from prefs_store.MAX_VALUE_BYTES"


def test_ac44_get_hands_out_a_json_round_trip_and_layout_is_not_special(core, prefs_block):
    # A caller mutates what it gets and `set`s it back (`panelOpen`, `modelByBackend`);
    # without a copy the first mutation edits the stored value in place.
    assert "JSON.parse(text)" in core and "JSON.stringify(val)" in core
    assert "prefRound(prefMap[key])" in prefs_block, "server-mode get no longer returns a copy"
    # T-037's `layout` is an ordinary key: no code path may name it.
    assert "layout" not in prefs_block
    assert "\"layout\"" not in core


def test_local_mode_is_the_old_behaviour_against_console_keys(prefs_block):
    # Static exports and an older server run on this path, so it must stay
    # byte-for-byte what it was.
    assert 'localStorage.getItem("console." + key)' in prefs_block
    assert 'localStorage.setItem("console." + key, JSON.stringify(val))' in prefs_block
    assert 'localStorage.removeItem("console." + key)' in prefs_block
    assert "return raw === null ? fallback : JSON.parse(raw);" in prefs_block


def test_server_mode_is_on_now_that_the_client_is_complete(core):
    # CR-27: the gate stayed shut while write-through, migration and Reset were
    # missing (a client in server mode without them would silently lose every
    # change). The migration task opened it, as the last step of that task, and
    # this test moved from asserting `false` to asserting `true`. The gate
    # itself stays, as the one switch that puts every page back in local mode.
    assert "var SERVER_PREFS = true;" in core
    assert "var SERVER_PREFS = false;" not in core
    assert re.search(r"if \(!SERVER_PREFS \|\| IS_STATIC\) return Promise\.resolve\(\"local\"\);", core)


def test_hydration_is_bounded_and_never_rejects(core):
    m = re.search(r"function prefHydrate\(\) \{\n(.*?)\n  \}\n", core, re.S)
    assert m, "prefHydrate is gone"
    body = m.group(1)
    assert "setTimeout(" in body and "HYDRATE_BOUND_MS" in body
    # The promise is only ever resolved: no reject callback, no throw out of it.
    assert "reject" not in body
    assert 'get("/api/prefs")' in body
    assert ".catch(function ()" in body


def test_br13_no_preference_is_read_while_the_script_is_evaluated(core):
    # The map is empty until hydrate() settles. `C.prefs.get/set` may only be
    # called from inside a function (indented past the IIFE's own body).
    offenders = []
    for n, line in enumerate(core.splitlines(), 1):
        if re.search(r"\bprefs\.(get|set|del)\(", line):
            indent = len(line) - len(line.lstrip(" "))
            if indent < 4:
                offenders.append("core.js:%d: %s" % (n, line.strip()))
    assert not offenders, "preference access at script-evaluation time: %s" % offenders
    # And nothing calls hydrate at the top level of core.js (app.js owns that).
    assert not re.search(r"(?m)^  (prefs\.hydrate|prefHydrate)\(", core)


def test_get_api_prefs_is_issued_from_hydrate_and_refresh_only(core):
    # AC-66 part: reads of the shared copy happen at boot and on a heartbeat
    # mismatch, nowhere else, so the version/prefs check adds no polling.
    assert core.count('get("/api/prefs")') == 2
    assert 'get("/api/prefs")' in _function(core, "prefHydrate")
    assert 'get("/api/prefs")' in _function(core, "prefRefresh")


# ---------------------------------------------------------------- task 08
# Write-through. Source tests pin that the pieces exist and are ordered the way
# that makes them safe; that coalescing and retry actually work was shown by a
# scratch Node smoke (not committed) and is a [BROWSER] check for AC-42/71/72.

@pytest.fixture(scope="module")
def section(core):
    """The whole preferences section: the `var prefs` object and what follows it."""
    start = core.index("/* ---------------- preferences")
    end = core.index("/* One glyph per status.")
    return core[start:end]


def _function(src, name):
    m = re.search(r"\n  function %s\(.*?\) \{\n(.*?)\n  \}\n" % re.escape(name), src, re.S)
    assert m, "core.js has no function %s" % name
    return m.group(1)


def test_ac39_page_hide_flushes_with_keepalive_and_the_csrf_header(section):
    # sendBeacon cannot carry X-Console-Request (httpd.py answers 403 without
    # it), so the page-hide flush is a keepalive fetch.
    assert "keepalive: true" in section
    assert '"X-Console-Request": "1"' in section
    assert 'window.addEventListener("pagehide", prefFlushOnHide)' in section
    assert 'document.addEventListener("visibilitychange"' in section
    assert 'document.visibilityState === "hidden"' in section


def test_ac39_sendbeacon_is_used_nowhere_in_the_console_ui():
    base = os.path.join(find_repo_root(), "console", "static")
    offenders = []
    for name in sorted(os.listdir(base)):
        if name.endswith((".js", ".html")):
            with open(os.path.join(base, name), encoding="utf-8") as fh:
                if "sendBeacon" in fh.read():
                    offenders.append(name)
    assert not offenders, "sendBeacon cannot send the CSRF header: %s" % offenders


def test_ac74_the_write_through_numbers_and_the_rev_rule_exist(section):
    assert "var FLUSH_MS = 250;" in section
    assert "var KEEPALIVE_MAX_BYTES = 60000;" in section
    assert "PREF_KEY_RE.test(key)" in section and "PREF_MAX_BYTES" in section
    # D-21: the rev from the page's own POST is adopted only when it followed
    # the rev the page knew.
    assert "res.prev === prefRev" in section
    # The connection coming back is a retry point, registered once at init.
    assert section.count("onConnection(") == 1
    assert re.search(r"\n  onConnection\(function \(online\) \{ if \(online\) prefFlush\(\); \}\);", section)


def test_post_carries_the_status_and_is_otherwise_what_it_was(core):
    body = _function(core, "post")
    assert "{ status: res.status }" in body
    # Everything callers depend on is still there.
    for kept in ('"X-Console-Request": "1"', "JSON.stringify(body || {})", "setOnline(true)",
                 "setOnline(false)", 'data.error || res.status + " " + res.statusText',
                 "This is a static export"):
        assert kept in body, "post() lost %r" % kept
    assert re.search(r"\n  function post\(path, body\) \{", core)


def test_core_adds_no_interval(core):
    # NFR-5/AC-66: the debounce and the hydrate bound are one-shot timeouts.
    # T-039 (PC-1, FR-12): the one shared freshness timer is the only interval,
    # and it lives in its own block; the prefs code still adds none.
    start = core.index("/* ---------------- panel freshness")
    end = core.index("/* A collapsible block INSIDE a panel")
    assert core.count("setInterval(") == 1
    assert core[start:end].count("setInterval(") == 1
    assert "setInterval(" not in core[:start] + core[end:]


def test_set_and_del_go_through_one_staging_function(prefs_block):
    assert "prefStage(key, val, false)" in prefs_block
    assert "prefStage(key, null, true)" in prefs_block
    assert "pending: prefPending," in prefs_block
    assert "flush: prefFlush," in prefs_block


def test_ac42_a_key_or_value_the_server_would_refuse_is_never_queued(section):
    body = _function(section, "prefStage")
    refused = body.index("if (problem) {")
    queued = body.index("prefQueue[key] = ")
    # The refusal branch ends in a return before anything is queued, and it
    # drops an older queued value for the key so memory and the wire agree.
    branch = body[refused:queued]
    assert "delete prefQueue[key];" in branch and "return;" in branch
    # Once per key per page lifetime, naming the key and the cause.
    assert "prefWarned[key]" in branch
    assert 'is kept for this window only: " + problem' in branch
    # An equal value queues nothing.
    assert "prefCanon(prefMap[key]) === prefCanon(v)" in body
    # The cap is measured in UTF-8 bytes like the server's, not characters.
    assert "prefBytes(JSON.stringify(v))" in _function(section, "prefProblem")


def test_ac71_failure_keeps_deltas_a_400_drops_them_and_sends_are_serial(section):
    send = _function(section, "prefSend")
    drop = send.index("err.status === 400")
    keep = send.index("if (!prefOwn(prefQueue, k)) prefQueue[k] = batch[k];")
    assert drop < keep, "a 400 must be handled before deltas are put back"
    assert "return;" in send[drop:keep]
    flush = _function(section, "prefFlush")
    # One request at a time, and the queue is swapped out so a write made while
    # it is out stays queued instead of being lost with the ack.
    assert "prefSending.length" in flush
    assert flush.index("var batch = prefQueue;") < flush.index("prefQueue = {};") < flush.index("prefSend(batch, false)")


def test_ac72_the_hide_flush_splits_by_size_and_resends_what_was_on_the_wire(section):
    hide = _function(section, "prefFlushOnHide")
    assert "prefSending.forEach" in hide, "a batch on the wire may be cancelled by the unload"
    assert "KEEPALIVE_MAX_BYTES" in hide
    # Per-key fallback: one request each, keepalive only while it fits.
    assert re.search(r"keys\.forEach\(function \(k\) \{.*?prefSend\(one, prefBytes\(JSON\.stringify\(prefBody\(one\)\)\) <= KEEPALIVE_MAX_BYTES\)", hide, re.S)


def test_pre_hydration_writes_become_queued_deltas_and_leave_no_local_copy(section):
    adopt = _function(section, "prefAdopt")
    assert "prefStage(k, touched[k].val, touched[k].del)" in adopt
    # The local copy is removed so the migration cannot take a just-made choice
    # for an old conflicting value.
    assert 'localStorage.removeItem("console." + k)' in adopt


def test_static_export_registers_no_page_hide_listener(section):
    guarded = re.search(r"if \(!IS_STATIC\) \{\n(.*?)\n  \}\n", section, re.S)
    assert guarded and "pagehide" in guarded.group(1) and "visibilitychange" in guarded.group(1)
    assert "IS_STATIC" in _function(section, "prefFlush") and "IS_STATIC" in _function(section, "prefFlushOnHide")


# ---------------------------------------------------------------- task 09
# Migration, the closed window, Reset and refresh. A scratch Node smoke (not
# committed) showed the behaviour; these pin the strings and the order that
# make it safe. AC-50/51/76/79/81/45 are [BROWSER] criteria.

def test_ac50_the_migration_talks_to_the_two_endpoints_and_says_what_it_did(section):
    assert '"/api/prefs/import"' in section and '"/api/prefs/reset"' in section
    # The closed-window sentence, word for word (D-16).
    assert ('var PREF_CLOSED_SENTENCE = "Old settings in this browser were discarded '
            'because preferences were reset.";') in section
    # One sentence per skipped key (key and this browser's value) and per rejected key (key and reason).
    assert "already had a shared value, so this browser's" in section
    assert "could not be moved to the shared copy: \" + r.reason" in section
    assert "res.skipped" in section and "res.rejected" in section and "res.closed" in section


def test_cr29_the_migration_runs_inside_the_hydrate_chain(core):
    body = _function(core, "prefHydrate")
    adopt = body.index("prefAdopt(res, bounded);")
    migrate = body.index("return prefMigrate(function () { return bounded; });")
    catch = body.index(".catch(function ()")
    resolve = body.index("resolve(prefMode);", catch)
    # The import is returned into the chain, so hydrate() does not resolve until
    # it ends, and the timer is cleared only after both (same 3 s bound for both).
    assert adopt < migrate < catch < body.index("clearTimeout(timer);", catch) < resolve


def test_ac51_local_copies_go_only_after_the_server_acknowledges(core):
    body = _function(core, "prefMigrate")
    post = body.index('post("/api/prefs/import"')
    # The one drop before the request is the closed-window branch (nothing is
    # imported then); every other drop is inside the success handler.
    assert body[:post].count("prefLocalDrop(") == 1 and "!prefImportOpen" in body[:post]
    assert body.index("prefLocalDrop(done)") > post
    # A failed or unusable import keeps the keys for the next boot, silently.
    assert re.search(r"\.catch\(function \(\) \{ /\* keys stay; the next boot tries again \*/ \}\);", body)
    # The map is replaced with the server's reply before anything is deleted.
    assert body.index("prefReplace(res, isLate());") < body.index("prefLocalDrop(done)")


def test_br16_an_entry_that_does_not_parse_is_dropped_without_a_word(core):
    body = _function(core, "prefLegacy")
    assert 'name.indexOf("console.") !== 0' in body and "PREF_KEY_RE.test(key)" in body
    assert "prefLocalDrop(dead);" in body
    assert "prefSay" not in body and "toast" not in body


def test_in_flight_changes_survive_a_replaced_map_ac81(core):
    # What the page has not sent yet (queued, or on the wire) is laid back over
    # whatever the server returned: an import, a refresh or a reset.
    assert "prefMap = prefOverlay(prefRound(res.prefs), prefSending.concat([prefQueue]));" in _function(core, "prefReplace")
    assert "prefOverlay({}, [prefQueue])" in _function(core, "prefReset")


def test_reset_discards_queued_deltas_before_it_posts(core):
    body = _function(core, "prefReset")
    post = body.index('post("/api/prefs/reset"')
    assert body.index("prefQueue = {};") < post, "queued deltas must be discarded before the request"
    assert body.index("clearTimeout(prefTimer)") < post, "the debounce must be cancelled before the request"
    assert body.index("prefEpoch++;") < post
    # Local mode never posts; success clears the legacy keys and closes the window;
    # failure rejects and puts the discarded changes back.
    assert "prefLocalClear();" in body[:post] and "prefImportOpen = false;" in body[post:]
    assert body.index("prefLocalClear();", post) > post
    assert "throw err;" in body[post:] and "dropped" in body[post:]
    # A batch on the wire when Reset began is not retried after it fails.
    assert "if (epoch !== prefEpoch) return;" in _function(core, "prefSend")


def test_refresh_returns_without_a_request_while_changes_are_pending(core):
    body = _function(core, "prefRefresh")
    guard = 'if (prefMode !== "server" || prefPending()) return Promise.resolve();'
    assert guard in body and body.index(guard) < body.index('get("/api/prefs")')
    assert "prefReplace(res, true);" in body, "listeners must hear which keys changed"
    assert ".catch(function ()" in body, "refresh never rejects"


def test_ac53_core_half_the_own_rev_is_adopted_only_when_prev_matches(core):
    # D-21: the same rule that gates adoption of the page's own write.
    assert "res.prev === prefRev" in _function(core, "prefSend")


# ---------------------------------------------------------------- task 10
# The router half: boot waits on hydration, the heartbeat picks up changes, the
# nav's key handler is bound once. [BROWSER] AC-41/52/77/79 need a real page.

@pytest.fixture(scope="module")
def app():
    return _read("console/static/app.js")


def _app_function(app, name):
    m = re.search(r"\n  function %s\(.*?\) \{\n(.*?)\n  \}\n" % re.escape(name), app, re.S)
    assert m, "app.js has no function %s" % name
    return m.group(1)


def test_ac38_boot_waits_on_hydration_before_the_first_theme_read(app):
    boot = 'Promise.all([C.get("/api/config"), C.prefs.hydrate()])'
    assert app.count(boot) == 1
    assert 'C.get("/api/config").then(function (cfg)' not in app, "the old boot opener is back"
    start = app.index(boot)
    catch = app.index("}).catch(function (err) {", start)
    chain = app[start:catch]
    assert "var cfg = res[0];" in chain
    # The first read of a preference is after hydration and before the nav and
    # the first tab are drawn, so the first render is already themed.
    theme = chain.index('applyTheme(C.prefs.get("theme", "system"));')
    assert theme < chain.index("buildNav();") < chain.index("go(ids.indexOf(wanted)")


def test_ac53_the_heartbeat_compares_prefs_rev_with_not_equal_only(app):
    assert 'C.get("/api/config").then(onHeartbeat).catch(function () {});' in app
    body = _app_function(app, "onHeartbeat")
    pending = body.index("C.prefs.pending()")
    flush = body.index("C.prefs.flush()")
    refresh = body.index("C.prefs.refresh()")
    # Pending changes are retried and never pulled over; only then is a pull considered.
    assert pending < flush < refresh
    assert "cfg.prefs_rev !== undefined" in body and "cfg.prefs_rev !== C.prefs.rev()" in body
    # A revision is an identity, not an order.
    code = re.sub(r"/\*.*?\*/", "", app, flags=re.S)
    assert not re.search(r"prefs_rev\s*[<>]|[<>]=?\s*cfg\.prefs_rev|rev\(\)\s*[<>]|[<>]=?\s*C\.prefs\.rev\(\)", code)


def test_ac66_part_this_task_adds_no_timer_and_no_extra_prefs_reads(app, core):
    # The counts recorded at task 00 (progress.md): 2 setInterval, 1 setTimeout.
    assert app.count("setInterval(") == 2
    assert app.count("setTimeout(") == 1
    # The shared copy is read at boot and on a heartbeat mismatch, nowhere else.
    assert core.count('get("/api/prefs")') == 2
    assert 'get("/api/prefs")' not in app


def test_ac77_source_half_the_nav_key_handler_is_bound_once(app):
    body = _app_function(app, "buildNav")
    assert body.count('addEventListener("keydown"') == 1
    guard = body.index('if (!nav.hasAttribute("data-keys-bound")) {')
    mark = body.index('nav.setAttribute("data-keys-bound", "1");')
    add = body.index('nav.addEventListener("keydown"')
    assert guard < mark < add, "the marker must be set before the listener is added, inside the guard"
    # Nothing binds it outside the guard.
    assert 'addEventListener("keydown"' not in body[:guard]
    assert 'addEventListener("keydown"' not in body[add + len('nav.addEventListener("keydown"'):]


def test_pickup_applies_theme_and_hidden_tabs_and_never_rerenders_the_active_tab(app):
    assert app.count("C.prefs.onChange(") == 1
    body = _app_function(app, "bindPrefs")
    assert 'applyTheme(C.prefs.get("theme", "system"))' in body
    # hiddenTabs rebuilds the nav only when the value differs from what the nav last used.
    assert 'JSON.stringify(C.prefs.get("hiddenTabs", [])) !== navHidden' in body
    assert "buildNav()" in body
    assert "navHidden = JSON.stringify(hidden);" in _app_function(app, "buildNav")
    # go() is what re-renders a tab and wipes a draft; pickup must never call it.
    assert not re.search(r"\bgo\(", body)
    boot = app[app.index('Promise.all([C.get("/api/config")'):]
    assert boot.index("bindPrefs();") < boot.index("buildNav();"), "registered once at boot, before the first nav build"
    assert app.count("bindPrefs();") == 1


def test_nothing_is_added_to_the_consoleapp_export(app):
    export = re.search(r"window\.ConsoleApp = \{(.*?)\};", app, re.S).group(1)
    for name in ("onHeartbeat", "bindPrefs", "navHidden", "prefs"):
        assert name not in export, "ConsoleApp export must not carry %s" % name


def test_other_tickets_hunks_in_app_js_are_still_there(app):
    # The onboarding open call, setTitle and the export were already in the
    # working tree when this ticket started; none of them may be edited here.
    assert "window.ConsoleOnboarding.maybeOpen();" in app
    assert "function setTitle(title) {" in app and "setTitle: setTitle," in app
    # Exact text, when the task-00 snapshot of those hunks is on this machine
    # (it lives in the gitignored console/.cache, so CI skips this part).
    snap = os.path.join(find_repo_root(), "console", ".cache", "t036-prebuild", "app.js.diff")
    if not os.path.exists(snap):
        pytest.skip("no task-00 snapshot on this machine")
    with open(snap, encoding="utf-8") as fh:
        added = [ln[1:] for ln in fh.read().splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    assert added, "the snapshot holds no added lines"
    missing = [ln for ln in added if ln not in app]
    assert not missing, "foreign lines changed or gone: %s" % missing
