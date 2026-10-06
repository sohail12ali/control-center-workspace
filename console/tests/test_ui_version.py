"""T-036 task 05: the UI version stamp (`server/ui_version.py`).

The stamp is what lets a page that has been open for days notice that the
console's UI changed under it. Two properties matter more than any single
value: it must move when a served file or the route table changes, and it must
stay still for everything else (an editor's temp file, a repeated call) --
a stamp that wobbles reloads people's pages for nothing, and one that never
moves is no stamp. These tests build throwaway static directories under
`tmp_path`; the one test that reads the shipped `console/static` only lists it.
"""

import builtins
import os
import re

import pytest

from server import export, httpd, ui_version
from server.paths import find_repo_root

HEX12 = re.compile(r"^[0-9a-f]{12}$")
MANIFEST = "m" * 64


@pytest.fixture
def static_dir(tmp_path):
    """A small stand-in for `console/static`: one file per stamped kind."""
    root = tmp_path / "static"
    root.mkdir()
    for name, body in (("index.html", "<html></html>"), ("app.js", "var a = 1;"),
                       ("styles.css", "body {}"), ("icon.png", "png-bytes")):
        (root / name).write_text(body, encoding="utf-8")
    return str(root)


def _stamp(static_dir, manifest=MANIFEST):
    return ui_version.compute(static_dir, manifest)


def _set_mtime(path, delta_s):
    """Move a file's mtime without touching its size or content."""
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + int(delta_s * 1_000_000_000)))


def test_ac1_stamp_is_twelve_lowercase_hex(static_dir):
    assert HEX12.match(_stamp(static_dir))


def test_ac1_shipped_static_dir_has_a_stamp():
    # Reads only: lists and stats the real directory, writes nothing.
    assert HEX12.match(ui_version.compute(ui_version.STATIC_DIR, MANIFEST))


def test_ac2_two_calls_without_a_change_agree(static_dir):
    assert _stamp(static_dir) == _stamp(static_dir)


@pytest.mark.parametrize("change", ["size", "mtime", "added", "removed"])
def test_ac3_a_matching_file_change_moves_the_stamp(static_dir, change):
    before = _stamp(static_dir)
    target = os.path.join(static_dir, "app.js")
    if change == "size":
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("var b = 2;")
    elif change == "mtime":
        _set_mtime(target, 5)  # same bytes, same size: only the mtime differs
    elif change == "added":
        with open(os.path.join(static_dir, "extra.js"), "w", encoding="utf-8") as fh:
            fh.write("")
    else:
        os.remove(target)
    after = _stamp(static_dir)
    assert HEX12.match(after) and after != before


def test_ac3_mtime_only_change_keeps_size(static_dir):
    # Guards the test above: it must really be a mtime-only edit.
    target = os.path.join(static_dir, "app.js")
    size = os.stat(target).st_size
    before = _stamp(static_dir)
    _set_mtime(target, 5)
    assert os.stat(target).st_size == size
    assert _stamp(static_dir) != before


def test_ac4_non_matching_files_never_count(static_dir):
    before = _stamp(static_dir)
    names = ("core.js.swp", "notes.txt", ".#core.js")
    for name in names:
        path = os.path.join(static_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("scratch")
        assert _stamp(static_dir) == before, "adding %s moved the stamp" % name
        _set_mtime(path, 7)
        assert _stamp(static_dir) == before, "touching %s moved the stamp" % name
        os.remove(path)
        assert _stamp(static_dir) == before, "removing %s moved the stamp" % name


def test_ac4_only_regular_files_count(static_dir):
    # A directory whose name matches a pattern is not an asset (export would
    # fail copying it, and a stamp must not count what is never served).
    before = _stamp(static_dir)
    os.mkdir(os.path.join(static_dir, "vendor.js"))
    assert _stamp(static_dir) == before


def test_ac5_manifest_digest_follows_tabs_and_routes():
    tabs = {"overview": {"id": "overview", "label": "Overview"}}
    routes = [{"method": "GET", "pattern": "^/api/a$", "name": "a"}]
    base = ui_version.manifest_digest(tabs, routes)
    assert base == ui_version.manifest_digest(dict(tabs), list(routes))
    more_tabs = dict(tabs, about={"id": "about", "label": "About"})
    more_routes = routes + [{"method": "POST", "pattern": "^/api/prefs/?$", "name": "prefs.post"}]
    assert ui_version.manifest_digest(more_tabs, routes) != base
    assert ui_version.manifest_digest(tabs, more_routes) != base
    renamed = [{"method": "GET", "pattern": "^/api/a$", "name": "b"}]
    assert ui_version.manifest_digest(tabs, renamed) != base


def test_ac5_route_order_does_not_move_the_digest():
    # The digest answers "which endpoints exist", not "in what order did the
    # plugins register them", so a reordered plugins.toml alone reloads nobody.
    one = {"method": "GET", "pattern": "^/api/a$", "name": "a"}
    two = {"method": "GET", "pattern": "^/api/b$", "name": "b"}
    assert (ui_version.manifest_digest({}, [one, two])
            == ui_version.manifest_digest({}, [two, one]))


def test_ac5_manifest_half_changes_the_stamp(static_dir):
    assert _stamp(static_dir, "a" * 64) != _stamp(static_dir, "b" * 64)


def test_ac5_manifest_is_computed_once_per_process(static_dir):
    calls = []

    def manifest_fn():
        calls.append(1)
        return MANIFEST

    uv = ui_version.UiVersion(static_dir, manifest_fn)
    assert calls == [], "the manifest must be lazy: plugins have not all applied at construction"
    values = [uv.value() for _ in range(5)]
    assert calls == [1]
    assert len(set(values)) == 1 and HEX12.match(values[0])


def test_ac5_static_half_is_recomputed_every_call(static_dir):
    uv = ui_version.UiVersion(static_dir, lambda: MANIFEST)
    first = uv.value()
    with open(os.path.join(static_dir, "app.js"), "a", encoding="utf-8") as fh:
        fh.write("var b = 2;")
    assert uv.value() != first


def test_ac6_stamp_opens_no_file(static_dir, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("ui_version must not open a file")

    monkeypatch.setattr(builtins, "open", refuse)
    assert HEX12.match(_stamp(static_dir))
    assert HEX12.match(ui_version.UiVersion(static_dir, lambda: MANIFEST).value())


def test_ac6_module_source_never_calls_open():
    path = os.path.join(os.path.dirname(ui_version.__file__), "ui_version.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    assert "open(" not in source


def test_ac7_stamped_names_equal_what_export_copies(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    copied = set(export._copy_frontend(str(out)))
    stamped = {name for name, _size, _mtime in ui_version.fingerprint(export.STATIC_DIR)}
    assert stamped == copied
    assert stamped, "the shipped console/static has no assets at all"


def test_ac7_three_modules_point_at_one_static_dir():
    assert ui_version.STATIC_DIR == export.STATIC_DIR == httpd.STATIC_DIR


def test_ac7_export_does_not_know_the_stamp():
    # BR-7: a static snapshot has no server to compare against, so export.py
    # carries no stamp and is not edited for this ticket (D-28).
    with open(os.path.join(find_repo_root(), "console", "server", "export.py"),
              encoding="utf-8") as fh:
        assert "ui_version" not in fh.read()


def test_ac67_a_file_that_vanishes_after_the_listing_is_skipped(static_dir, monkeypatch):
    # The editor's save-by-rename window: glob saw the name, stat does not.
    real_glob = ui_version.glob.glob

    def glob_with_ghost(pattern):
        found = real_glob(pattern)
        if pattern.endswith("*.js"):
            found.append(os.path.join(static_dir, "ghost.js"))
        return found

    expected = _stamp(static_dir)
    monkeypatch.setattr(ui_version.glob, "glob", glob_with_ghost)
    assert _stamp(static_dir) == expected


def test_ac67_a_file_whose_stat_raises_is_skipped(static_dir, monkeypatch):
    real_stat = os.stat
    with_all = _stamp(static_dir)

    def flaky(path, *args, **kwargs):
        if os.path.basename(str(path)) == "app.js":
            raise FileNotFoundError(path)
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(ui_version.os, "stat", flaky)
    without_app = _stamp(static_dir)
    assert HEX12.match(without_app) and without_app != with_all
    monkeypatch.undo()
    os.remove(os.path.join(static_dir, "app.js"))
    assert _stamp(static_dir) == without_app, "skipping equals the file being absent"


def test_ac67_an_unlistable_directory_gives_none(tmp_path):
    missing = str(tmp_path / "nope")
    assert ui_version.fingerprint(missing) is None
    assert ui_version.compute(missing, MANIFEST) is None
    assert ui_version.UiVersion(missing, lambda: MANIFEST).value() is None


def test_ac67_a_file_in_place_of_the_directory_gives_none(tmp_path):
    plain = tmp_path / "static"
    plain.write_text("not a directory", encoding="utf-8")
    assert ui_version.compute(str(plain), MANIFEST) is None


def test_ac67_an_empty_directory_still_has_a_stamp(tmp_path):
    # Distinct from unlistable: listable and empty is a real state, so the stamp
    # exists and differs from a populated one (not a silent None).
    empty = tmp_path / "static"
    empty.mkdir()
    assert HEX12.match(ui_version.compute(str(empty), MANIFEST))
