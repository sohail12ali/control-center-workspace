"""T-036: the Settings panel and the statements that stopped being true.

Preferences used to live in one browser, so the Settings panel, the About page,
the README and a few comments all said "this browser only". They are now one
saved copy shared by the desktop app and every browser tab, and a Reset reaches
all of them. These are source and text tests (there is no JS runner in CI, see
`test_prefs_client_source.py`): they pin that the new wording is present, that
the old sentences that would now be false are gone, and that the panel reads
and resets through `C.prefs` rather than the browser's own storage. What a
person sees in the panel is a [BROWSER] criterion and is not checked here.

Task 11 (this file starts here) is the panel itself; task 12 adds the one-line
statements in `settings.js`, `about.js` and `core.js`; task 13 the README,
`plugins.toml` and `registry.py`.
"""

import os
import re

import pytest

from server.paths import find_repo_root


def _read(rel):
    with open(os.path.join(find_repo_root(), *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def settings():
    return _read("console/static/settings.js")


@pytest.fixture(scope="module")
def storage_body(settings):
    """`function storage(repaint) {...}`: the panel, which also holds two other
    tickets' rows (the "Setup wizard" row and the "Getting started card" row)."""
    m = re.search(r"\n  function storage\(repaint\) \{\n(.*?)\n  \}\n", settings, re.S)
    assert m, "settings.js no longer has `function storage(repaint) {...}`"
    return m.group(1)


SERVER_SENTENCE = ("Shared by the desktop app and every browser tab on this machine. "
                   "Kept on the server in console/.cache/prefs.json; not committed.")
LOCAL_SENTENCE = "Stored in this browser only."
CONFIRM_SENTENCE = ("Reset every saved preference for the app and all browser tabs? "
                    "Tickets, chats and other data are not touched.")
SERVER_HINT = "Also clears the shared copy on the server, so the app and every open tab return to defaults."
LOCAL_HINT = "Clears this browser's saved preferences."


def test_ac54_the_panel_is_retitled_and_carries_the_new_wording(storage_body):
    assert 'C.panel("Saved preferences"' in storage_body
    # Each sentence is a single string literal, so a text check finds it as written.
    for sentence in (SERVER_SENTENCE, LOCAL_SENTENCE, CONFIRM_SENTENCE, SERVER_HINT, LOCAL_HINT):
        assert '"%s"' % sentence in storage_body, "missing or split across strings: %s" % sentence
    assert "Reset all preferences" in storage_body
    # The help note says what Reset leaves alone.
    assert "tickets, chats and other data are not touched" in storage_body


def test_ac54_the_old_panel_wording_is_gone(settings):
    assert "Affects this browser only. No server data is touched." not in settings
    assert 'C.panel("Stored in this browser"' not in settings
    assert "touches no server state" not in settings


def test_ac54_the_sentence_follows_the_mode(storage_body):
    # Server mode says shared, local mode (a static export, or a server that
    # cannot be reached) says this browser; the hint follows the same switch.
    assert 'C.prefs.mode() === "server"' in storage_body
    assert "server ? MODE_SERVER : MODE_LOCAL" in storage_body
    assert "server ? RESET_HINT_SERVER : RESET_HINT_LOCAL" in storage_body


def test_ac55_the_panel_reads_and_resets_through_c_prefs(storage_body):
    assert "localStorage" not in storage_body
    assert "C.prefs.all()" in storage_body
    assert "C.prefs.reset()" in storage_body


def test_ac55_the_key_list_is_sorted_and_shows_each_value_as_json(storage_body):
    assert "Object.keys(all).sort()" in storage_body
    assert "JSON.stringify(all[k])" in storage_body
    # No second sort and no raw string read at render time.
    assert storage_body.count(".sort()") == 1


def test_ac54_reset_asks_first_and_cancel_does_nothing(storage_body):
    ask = storage_body.index("window.confirm(")
    assert ask < storage_body.index("C.prefs.reset()"), "Reset runs before it asks"
    assert "if (!window.confirm(RESET_ASK)) return;" in storage_body
    # The sentence the person reads is the one the plan fixed, not a lookalike.
    assert 'var RESET_ASK = "%s";' % CONFIRM_SENTENCE in storage_body


def test_ac54_reset_success_applies_defaults_in_order_then_repaints(storage_body):
    m = re.search(r"C\.prefs\.reset\(\)\.then\(function \(\) \{\n(.*?)\n        \}, function \(err\) \{\n(.*?)\n        \}\);",
                  storage_body, re.S)
    assert m, "the reset is no longer `reset().then(onOk, onError)`"
    ok, failed = m.group(1), m.group(2)
    order = ['window.ConsoleApp.applyTheme("system");', "window.ConsoleApp.rebuildNav();",
             'C.toast("Preferences reset", "ok");', "repaint();"]
    at = [ok.index(step) for step in order]
    assert at == sorted(at), "success steps are out of order: %s" % at
    # A failed reset says so, keeps the list as it was and can be tried again.
    assert 'C.toast("Could not reset preferences: "' in failed and '"err"' in failed
    assert "reset.disabled = false;" in failed
    assert "repaint()" not in failed and "Preferences reset" not in failed
    assert "applyTheme" not in failed and "rebuildNav" not in failed


def test_the_other_tickets_rows_are_still_in_the_panel(storage_body):
    # The onboarding work's "Setup wizard" row and the "Getting started card"
    # row sit inside this function; rewriting the panel must not take them.
    for text in ("Setup wizard", "Run setup again", "Getting started card", "Show again",
                 "Name, providers, editor files, and default models",
                 "window.ConsoleOnboarding.open()", 'C.prefs.del("hideOnboarding")'):
        assert text in storage_body, "lost: %s" % text
    # Both rows are still children of the panel, ahead of the key list.
    panel = storage_body[storage_body.index('C.panel("Saved preferences"'):]
    assert panel.index("again,") < panel.index("restore,") < panel.index("keys.length")


def test_the_panel_adds_no_class_the_stylesheet_lacks(storage_body):
    # No new CSS in this task: every class the panel uses is an existing one.
    css = _read("console/static/styles.css")
    used = set()
    for literal in re.findall(r'class: "([^"]+)"', storage_body):
        used.update(literal.split())
    assert used, "no classes found; the pattern is stale"
    for cls in sorted(used):
        assert re.search(r"\.%s\b" % re.escape(cls), css), "class %r has no rule in styles.css" % cls


# ---- Task 12: the one-line statements in settings.js, about.js and core.js ----

# The phrases that were true while preferences lived in one browser and are not
# true now. The single sentence that is still true (local mode: a static export or
# a server that cannot be reached) is the panel's own and is removed before the scan.
STALE_PHRASES = ("this browser only", "stored in this browser", "browser-local",
                 "invisible to everyone else", "browser only", "your browser's")


def _joined(text):
    """Source with `"a" + "b"` string joins closed up, so a sentence the author
    wrapped across lines can be found as one piece of text."""
    return re.sub(r'"\s*\n\s*\+ "', "", text)


def test_ac55_settings_js_never_touches_the_browsers_own_storage(settings):
    # AC-55 final: the whole file, comments included, not only `storage()`.
    assert "localStorage" not in settings


def test_ac54_no_settings_statement_still_says_the_toggles_are_one_browser(settings):
    rest = settings.replace('"%s"' % LOCAL_SENTENCE, "")
    assert rest != settings, "the local-mode sentence is gone, so the scan below proves nothing"
    low = rest.lower()
    for phrase in STALE_PHRASES:
        assert phrase not in low, "settings.js still says %r" % phrase


def test_ac54_the_settings_toggles_are_described_as_shared_saved_preferences(settings):
    head = settings[:settings.index("(function (C) {")]
    assert "saved" in head and "shared through the server" in head
    # The real distinction survives: plugins.toml is the committed switch.
    assert "`enabled = false` in console/config/plugins.toml is a" in head
    assert "committed, server-side decision" in head
    # Theme, tabs and the agent-CLI picker each say they are saved and shared.
    joined = _joined(settings)
    assert "so the desktop app and every browser tab show the same theme" in joined
    assert "so the desktop app and every browser tab hide the same tabs" in joined
    assert "saved preference, shared by the app and every browser tab" in joined


def test_ac54_the_agent_cli_note_keeps_its_real_distinction(settings):
    m = re.search(r"/\* Agent CLIs — which backends the composer offers\.\n(.*?)\*/", settings, re.S)
    assert m, "the Agent CLIs comment moved or was rewritten"
    note = " ".join(m.group(1).split())
    assert "hides a CLI from the shared picker" in note
    # It hides a CLI from the picker; it does not take it off the server.
    assert "It does NOT remove it from the server" in note
    assert "console/config/agents.toml" in note and "`plugins.toml` can remove the whole Agents feature" in note
    # The panel's help still points at where the server's list is changed.
    assert 'C.el("code", {}, ["console/config/agents.toml"])' in settings


def test_ac54_about_js_no_longer_says_one_browser():
    about = _read("console/static/about.js")
    low = about.lower()
    for phrase in ("stored in this browser only", "in your browser only", "browser only", "localstorage"):
        assert phrase not in low, "about.js still says %r" % phrase
    joined = _joined(about)
    assert "saved preferences, shared by the app and every browser" in joined
    assert "they only hide a tab from view" in joined
    # plugins.toml is still the switch that applies to everyone.
    assert "that switch is committed and applies to everyone" in about


def test_ac55_the_collapsible_comment_in_core_js_does_not_name_localstorage():
    core = _read("console/static/core.js")
    m = re.search(r"(/\* Open/closed, remembered per id across reloads\..*?\*/)\n  function collapsible\(", core, re.S)
    assert m, "the comment above `collapsible` moved"
    assert "localStorage" not in m.group(1)
    assert "One preference object rather than a key per panel" in m.group(1)


def test_the_preferences_header_comment_in_core_js_is_still_true():
    # The header says what the server store does; write-through is part of it.
    core = _read("console/static/core.js")
    head = core[core.index("/* ---------------- preferences ----------------"):]
    head = head[:head.index("*/")]
    assert "a write reaches the server a moment later, in" in head
    assert "shared by the desktop app" in head


# ---- Task 13: README, plugins.toml header comment, registry.py docstring ----

def _two_switches_table(readme):
    start = readme.index("### Two different off switches")
    block = readme[start:readme.index("\n## ", start)]
    rows = [line for line in block.splitlines() if line.startswith("|")]
    return block, [[c.strip() for c in row.strip("|").split("|")] for row in rows]


def test_ac54_the_readme_two_switches_table_describes_saved_preferences():
    block, table = _two_switches_table(_read("console/README.md"))
    # Same shape as before: a header, a divider, four rows of three cells.
    assert len(table) == 6 and all(len(row) == 3 for row in table)
    assert table[0] == ["Question", "`config/plugins.toml`", "Settings tab"]
    by_question = {row[0]: row[2] for row in table[2:]}
    assert set(by_question) == {"Scope", "Stored in", "Effect", "Use it to say"}
    assert "One person's browser" not in block
    assert "saved preferences" in by_question["Scope"] and "every browser" in by_question["Scope"]
    stored = by_question["Stored in"]
    assert stored.startswith("The server, in `console/.cache/prefs.json`")
    assert stored != "`localStorage`"
    assert "static export" in stored       # the one place it is still the browser's own
    # The two lines that were already true stay as they were.
    assert by_question["Effect"] == "Tab hidden from the nav"
    assert by_question["Use it to say"] == '"I don\'t use that tab"'
    # The paragraph that follows still states the distinction it exists to state.
    assert "Hiding the Agents tab in Settings does **not** disable the launch endpoint." in block
    flat = " ".join(block.split())
    assert "`prefs` plugin keeps one copy on the server" in flat
    # What disabling the plugin does is part of the plugin's facts.
    assert "every client then falls back to its own `localStorage`" in flat


def test_ac54_the_readme_no_longer_calls_composer_prefs_browser_local():
    readme = _read("console/README.md")
    assert "Browser-local" not in readme and "browser-local" not in readme


def test_ac54_plugins_toml_header_says_the_toggles_are_shared_saved_preferences():
    toml = _read("console/config/plugins.toml")
    head = toml[:toml.index("\n[[plugin]]")]
    flat = " ".join(line.lstrip("# ").strip() for line in head.splitlines())
    assert "stored in one browser" not in flat and "from one person" not in flat
    assert "per-user saved preferences, kept on the server and shared by the desktop app and every browser on this machine" in flat
    assert "only hide a tab from view" in flat
    # The distinction the comment exists for survives.
    assert "This file is committed and applies to everyone who pulls the checkout" in flat
    assert "Don't unify them" in flat
    # Comment lines only: the shipped registry is still the one test_plugins checks.
    from server import tomlio
    rows = {r["id"]: r for r in tomlio.loads(toml)["plugin"]} if hasattr(tomlio, "loads") else None
    if rows is not None:
        assert rows["prefs"]["enabled"] is True and rows["prefs"]["module"] == "features.prefs_feature"


def test_ac54_the_registry_docstring_no_longer_says_browser_local():
    import ast
    doc = ast.get_docstring(ast.parse(_read("console/server/plugins/registry.py")))
    flat = " ".join(doc.split())
    assert "browser-local" not in flat
    assert "per-user saved preferences, kept on the server by the `prefs` plugin" in flat
    assert "shared by the desktop app and every browser on this machine" in flat
    # The point of the docstring is unchanged: two switches, kept apart.
    assert "Do not unify them: one is a deployment fact, the other is a preference." in flat
