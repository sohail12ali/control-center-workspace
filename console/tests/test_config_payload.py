"""T-036 task 06: `/api/config` carries `ui_version` and `prefs_rev`.

That endpoint is three things at once: the nav manifest the page boots from, the
15 s heartbeat, and the desktop sidecar's readiness probe. So the two new fields
have to be strictly additive (the five old keys keep their shape) and strictly
optional (a stamp that cannot be computed, or a disabled prefs plugin, costs a
field and never the payload).

`App`, `build_app` and `call()` are a local copy of `test_prefs_routes.py`,
itself a copy of `test_ui_endpoints.py:30-75`, for the reason given in D-31:
`conftest.py` is shared and other tickets edit it. Every workspace is the `repo`
fixture's throwaway root; nothing here writes the real checkout.
"""

import json
import os
import re

import pytest

from server import boards, export, httpd, prefs_store, ui_version
from server.features import shell_feature
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry

HEX12 = re.compile(r"^[0-9a-f]{12}$")
OLD_KEYS = {"title", "subtitle", "tabs", "boards", "stale_days"}


class App:
    def __init__(self, repo_root, router, ctx):
        self.repo_root = repo_root
        self.router = router
        self.ctx = ctx


def _shipped_plugins_text():
    src = os.path.join(find_repo_root(), "console", "config", "plugins.toml")
    with open(src, encoding="utf-8") as fh:
        return fh.read()


def build_app(repo, plugins_text):
    dst = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(plugins_text)
    boards._console_cache.clear()
    config = boards.load_console_config(repo)
    ctx, router = plugin_registry.build(repo, config)
    return App(repo, router, ctx)


def _prefs_off_text():
    text = _shipped_plugins_text()
    marker = 'id = "prefs"\nmodule = "features.prefs_feature"\nenabled = true'
    assert marker in text
    return text.replace(marker, marker.replace("true", "false"))


def call(app, method, path, query=None, body=None):
    """Dispatch one request the way httpd does, returning the handler's data."""
    handler, args = app.router.resolve(method, path)
    assert handler is not None, "no route for %s %s" % (method, path)
    req = httpd.Request(method, path, query or {}, body, app.repo_root,
                        client_addr="100.64.0.9", user_agent="pytest")
    return handler(req, *args)


def config(app):
    return call(app, "GET", "/api/config")


@pytest.fixture
def app(repo):
    """The shipped plugin set against a throwaway workspace, over the real
    `console/static` (read only: the stamp lists and stats it)."""
    return build_app(repo, _shipped_plugins_text())


@pytest.fixture
def scratch_static(tmp_path, monkeypatch):
    """A private static directory the test may edit. `shell_feature` reads its
    module-level `STATIC_DIR` when a plugin set is built, so this is applied
    before `static_app` builds one."""
    d = tmp_path / "static"
    d.mkdir()
    (d / "index.html").write_text("<html></html>", encoding="utf-8")
    (d / "app.js").write_text("var a = 1;", encoding="utf-8")
    monkeypatch.setattr(shell_feature, "STATIC_DIR", str(d))
    return str(d)


@pytest.fixture
def static_app(repo, scratch_static):
    return build_app(repo, _shipped_plugins_text())


def test_ac1_ui_version_is_present_and_twelve_hex(app):
    assert HEX12.match(config(app)["ui_version"])


def test_ac1_the_five_existing_keys_keep_their_shape(app):
    cfg = config(app)
    assert OLD_KEYS <= set(cfg)
    assert isinstance(cfg["title"], str) and cfg["title"]
    assert isinstance(cfg["subtitle"], str)
    assert isinstance(cfg["stale_days"], int)
    assert isinstance(cfg["tabs"], list) and cfg["tabs"]
    assert all({"id", "label"} <= set(t) for t in cfg["tabs"])
    assert {t["id"] for t in cfg["tabs"]} >= {"about", "settings"}
    assert all(set(b) == {"kind", "label"} for b in cfg["boards"])
    # Additive means exactly these new keys, nothing else (`workspace`: task 19).
    assert set(cfg) == OLD_KEYS | {"ui_version", "prefs_rev", "workspace"}


def test_ac1_two_calls_without_a_change_agree(static_app):
    # Over the private directory: the real console/static may be edited by
    # another session between the two calls.
    assert config(static_app)["ui_version"] == config(static_app)["ui_version"]


def test_ac1_the_served_value_is_the_stamp_of_static_and_manifest(static_app, scratch_static):
    expected = ui_version.compute(
        scratch_static,
        ui_version.manifest_digest(static_app.ctx.tabs(), static_app.router.describe()))
    assert config(static_app)["ui_version"] == expected


def test_ac1_an_edit_to_a_served_file_changes_the_served_value(static_app, scratch_static):
    before = config(static_app)["ui_version"]
    with open(os.path.join(scratch_static, "app.js"), "a", encoding="utf-8") as fh:
        fh.write("var b = 2;")
    assert config(static_app)["ui_version"] != before


def test_ac1_an_editor_temp_file_does_not_change_the_served_value(static_app, scratch_static):
    before = config(static_app)["ui_version"]
    with open(os.path.join(scratch_static, "app.js.swp"), "w", encoding="utf-8") as fh:
        fh.write("scratch")
    assert config(static_app)["ui_version"] == before


def test_ac5_a_changed_route_table_changes_the_served_value(repo, scratch_static):
    # The reason the route table is in the stamp: a restart that adds or drops
    # an endpoint must read as a change, so a page on the older server moves.
    on = config(build_app(repo, _shipped_plugins_text()))["ui_version"]
    off = config(build_app(repo, _prefs_off_text()))["ui_version"]
    assert HEX12.match(on) and HEX12.match(off) and on != off


def test_ac35_prefs_rev_equals_the_store_rev_after_a_set(app):
    assert config(app)["prefs_rev"] == 0 == prefs_store.rev(app.repo_root)
    call(app, "POST", "/api/prefs", body={"set": {"theme": "dark"}})
    assert config(app)["prefs_rev"] == 1 == prefs_store.rev(app.repo_root)
    call(app, "POST", "/api/prefs", body={"set": {"theme": "dark"}})
    assert config(app)["prefs_rev"] == 1, "an equal set must not move the rev"
    call(app, "POST", "/api/prefs/reset", body={})
    assert config(app)["prefs_rev"] == 2 == prefs_store.rev(app.repo_root)


def test_ac35_prefs_rev_is_absent_when_the_plugin_is_disabled(repo):
    off = build_app(repo, _prefs_off_text())
    assert not off.ctx.has_provider("prefs")
    cfg = config(off)
    assert "prefs_rev" not in cfg
    assert OLD_KEYS <= set(cfg) and HEX12.match(cfg["ui_version"])


def test_ac67_an_unlistable_static_dir_drops_only_the_stamp(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(shell_feature, "STATIC_DIR", str(tmp_path / "does-not-exist"))
    cfg = config(build_app(repo, _shipped_plugins_text()))
    assert "ui_version" not in cfg
    assert OLD_KEYS <= set(cfg) and cfg["prefs_rev"] == 0


def test_ac67_a_static_dir_that_disappears_later_drops_the_stamp_not_the_payload(
        static_app, scratch_static):
    assert "ui_version" in config(static_app)
    for name in os.listdir(scratch_static):
        os.remove(os.path.join(scratch_static, name))
    os.rmdir(scratch_static)
    cfg = config(static_app)
    assert "ui_version" not in cfg and OLD_KEYS <= set(cfg)


def test_br7_the_static_export_manifest_carries_neither_field(app):
    # A snapshot has no server to compare against and no shared store.
    manifest, _kept, _dropped = export._export_manifest(app.repo_root)
    assert "ui_version" not in manifest and "prefs_rev" not in manifest
    assert manifest.get("static") is True


def test_the_payload_shell_feature_uses_the_modules_static_dir_constant():
    assert shell_feature.STATIC_DIR == ui_version.STATIC_DIR == export.STATIC_DIR


def test_ac57_workspace_is_twelve_lowercase_hex_and_constant_for_one_root(app):
    first = config(app)["workspace"]
    assert HEX12.match(first)
    assert config(app)["workspace"] == first
    assert first == shell_feature._workspace_id(app.repo_root)


def test_ac57_two_roots_with_distinct_names_get_distinct_ids(tmp_path):
    a, b = tmp_path / "checkout-a", tmp_path / "checkout-b"
    a.mkdir()
    b.mkdir()
    ida, idb = shell_feature._workspace_id(str(a)), shell_feature._workspace_id(str(b))
    assert HEX12.match(ida) and HEX12.match(idb) and ida != idb


def test_ac57_the_payload_carries_neither_the_root_path_nor_its_directory_name(app):
    text = json.dumps(config(app))
    root = os.path.realpath(app.repo_root)
    assert root not in text and app.repo_root not in text
    assert os.path.basename(root) not in text


def test_ac57_the_id_is_the_hash_of_the_normalised_real_path(tmp_path):
    import hashlib
    d = tmp_path / "ws"
    d.mkdir()
    want = hashlib.sha256(os.path.normcase(os.path.realpath(str(d))).encode("utf-8")).hexdigest()[:12]
    assert shell_feature._workspace_id(str(d)) == want


def test_br7_the_static_export_manifest_has_no_workspace(app):
    manifest, _kept, _dropped = export._export_manifest(app.repo_root)
    assert "workspace" not in manifest
