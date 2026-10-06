"""The shared preference store (T-036, `server/prefs_store.py`).

Every test runs against the `repo` fixture's throwaway workspace. Nothing here
may touch the real checkout's `console/.cache/prefs.json`: `test_ac31_*` pins
that the store path is derived from the root it is handed.
"""

import json
import os
import threading

import pytest

from server import prefs_store as ps
from server import tomlio
from server.paths import find_repo_root


def _file(repo):
    return os.path.join(repo, "console", ".cache", "prefs.json")


def _on_disk(repo):
    with open(_file(repo), encoding="utf-8") as fh:
        return json.load(fh)


def _write_raw(repo, data):
    os.makedirs(os.path.dirname(_file(repo)), exist_ok=True)
    with open(_file(repo), "wb") as fh:
        fh.write(data)


def _value_of_bytes(n):
    """A JSON string whose serialised form is exactly `n` bytes (two quotes)."""
    return "a" * (n - 2)


class TestRead:
    def test_ac24_no_file_reads_empty_and_import_open(self, repo):
        assert not os.path.exists(_file(repo))
        assert ps.snapshot(repo) == {"prefs": {}, "rev": 0, "import_open": True}
        assert ps.rev(repo) == 0
        assert ps.read(repo) == {"v": 1, "rev": 0, "prefs": {}, "import_closed": False}
        # A read must not create the file: GET /api/prefs is on the heartbeat path.
        assert not os.path.exists(_file(repo))

    @pytest.mark.parametrize("raw", [
        b"",
        b"\xff\xfe\x00\x01",
        b"not json at all",
        b"[1, 2, 3]",
        b'{"prefs": 3}',
        b'{"rev": "x", "prefs": {}}',
        b'{"rev": true, "prefs": {}}',
        b'{"rev": -4, "prefs": {}}',
        b'{"rev": 2, "prefs": {"a": NaN}}',
    ])
    def test_ac29_unreadable_file_reads_empty_and_next_write_replaces_it(self, repo, raw):
        _write_raw(repo, raw)
        assert ps.snapshot(repo) == {"prefs": {}, "rev": 0, "import_open": True}
        assert ps.apply(repo, set={"theme": "dark"}) == {"rev": 1, "prev": 0}
        assert _on_disk(repo)["prefs"] == {"theme": "dark"}
        assert ps.snapshot(repo)["prefs"] == {"theme": "dark"}


class TestApply:
    def test_ac25_set_is_stored_and_del_is_applied_with_prev(self, repo):
        assert ps.apply(repo, set={"theme": "dark", "voice": {"autoRead": True}}) == \
            {"rev": 1, "prev": 0}
        snap = ps.snapshot(repo)
        assert snap["prefs"] == {"theme": "dark", "voice": {"autoRead": True}}
        assert snap["rev"] == 1

        assert ps.apply(repo, delete=["theme"]) == {"rev": 2, "prev": 1}
        assert ps.snapshot(repo)["prefs"] == {"voice": {"autoRead": True}}

    def test_ac25_an_equal_set_leaves_rev_equal_to_prev(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        result = ps.apply(repo, set={"theme": "dark"})
        assert result["rev"] == result["prev"] == 1
        # Deleting a key that is not there changes nothing either.
        assert ps.apply(repo, delete=["absent"]) == {"rev": 1, "prev": 1}

    def test_ac25_true_and_one_are_different_values(self, repo):
        # Python says `1 == True`; a preference that flips between them changed.
        ps.apply(repo, set={"flag": 1})
        assert ps.apply(repo, set={"flag": True}) == {"rev": 2, "prev": 1}
        assert ps.snapshot(repo)["prefs"]["flag"] is True

    def test_set_and_delete_of_one_key_in_a_call_ends_deleted(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        ps.apply(repo, set={"theme": "light"}, delete=["theme"])
        assert ps.snapshot(repo)["prefs"] == {}

    @pytest.mark.parametrize("key", ["theme", "a.b-c_d", "A", "x" * 64])
    def test_ac26_valid_keys_are_accepted(self, repo, key):
        assert ps.apply(repo, set={key: 1})["rev"] == 1
        assert key in ps.snapshot(repo)["prefs"]

    @pytest.mark.parametrize("key", ["", "1x", "a b", "../x", "x" * 65, "theme\n", "-a", "é"])
    def test_ac26_invalid_keys_are_refused_and_nothing_is_written(self, repo, key):
        with pytest.raises(ValueError) as err:
            ps.apply(repo, set={key: 1})
        assert "not a valid preference key" in str(err.value)
        assert not os.path.exists(_file(repo))
        with pytest.raises(ValueError):
            ps.apply(repo, delete=[key])
        assert not os.path.exists(_file(repo))

    def test_ac26_a_non_string_key_is_refused(self, repo):
        with pytest.raises(ValueError):
            ps.apply(repo, delete=[3])
        assert not os.path.exists(_file(repo))

    def test_ac27_value_size_boundary_is_32768_bytes(self, repo):
        assert len(json.dumps(_value_of_bytes(32768)).encode()) == 32768
        ps.apply(repo, set={"big": _value_of_bytes(32768)})
        with pytest.raises(ValueError) as err:
            ps.apply(repo, set={"big": _value_of_bytes(32769)})
        assert "'big'" in str(err.value) and "32768" in str(err.value)
        assert ps.snapshot(repo)["prefs"]["big"] == _value_of_bytes(32768)

    def test_ac27_the_size_is_utf8_bytes_not_characters(self, repo):
        # 11000 three-byte characters = 33000 bytes of text, 11002 characters.
        with pytest.raises(ValueError):
            ps.apply(repo, set={"cjk": "中" * 11000})
        ps.apply(repo, set={"cjk": "中" * 10000})

    def test_ac27_the_129th_key_is_refused(self, repo):
        ps.apply(repo, set={"k%03d" % i: i for i in range(128)})
        assert len(ps.snapshot(repo)["prefs"]) == 128
        with pytest.raises(ValueError) as err:
            ps.apply(repo, set={"one-too-many": 1})
        assert "'one-too-many'" in str(err.value) and "128" in str(err.value)
        assert len(ps.snapshot(repo)["prefs"]) == 128
        # Replacing an existing key at the cap is not growth.
        assert ps.apply(repo, set={"k000": "again"})["rev"] == 2

    def test_ac27_a_write_past_262144_bytes_is_refused(self, repo):
        for i in range(8):
            ps.apply(repo, set={"f%d" % i: _value_of_bytes(32000)})
        assert os.path.getsize(_file(repo)) <= 262144
        with pytest.raises(ValueError) as err:
            ps.apply(repo, set={"f8": _value_of_bytes(32000)})
        assert "262144" in str(err.value)
        assert sorted(ps.snapshot(repo)["prefs"]) == ["f%d" % i for i in range(8)]
        assert os.path.getsize(_file(repo)) <= 262144

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_ac27_nan_and_infinity_are_refused(self, repo, bad):
        with pytest.raises(ValueError) as err:
            ps.apply(repo, set={"n": bad})
        assert "'n'" in str(err.value)
        with pytest.raises(ValueError):
            ps.apply(repo, set={"n": {"deep": [bad]}})
        assert not os.path.exists(_file(repo))

    @pytest.mark.parametrize("sets", [["a"], "theme", 3, [("a", 1)]])
    def test_ac27_a_non_object_set_is_refused(self, repo, sets):
        with pytest.raises(ValueError):
            ps.apply(repo, set=sets)

    @pytest.mark.parametrize("dels", ["theme", {"a": 1}, 3, ("a",)])
    def test_ac27_a_non_list_del_is_refused(self, repo, dels):
        with pytest.raises(ValueError):
            ps.apply(repo, delete=dels)

    def test_ac28_one_valid_and_one_invalid_key_writes_neither(self, repo):
        ps.apply(repo, set={"keep": 1})
        before = _on_disk(repo)
        with pytest.raises(ValueError):
            ps.apply(repo, set={"theme": "dark", "bad key": 1})
        with pytest.raises(ValueError):
            ps.apply(repo, set={"theme": "dark", "n": float("nan")})
        with pytest.raises(ValueError):
            ps.apply(repo, set={"theme": "dark"}, delete=["../x"])
        assert _on_disk(repo) == before
        assert "theme" not in ps.snapshot(repo)["prefs"]


class TestConcurrencyAndPlacement:
    def test_ac30_eight_threads_each_setting_a_key_keep_all_eight(self, repo):
        barrier = threading.Barrier(8)
        errors = []

        def work(i):
            try:
                barrier.wait()
                ps.apply(repo, set={"t%d" % i: {"n": i}})
            except Exception as exc:  # surfaced by the assert below
                errors.append(exc)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        on_disk = _on_disk(repo)  # valid JSON, or this raises
        assert on_disk["prefs"] == {"t%d" % i: {"n": i} for i in range(8)}
        assert on_disk["rev"] == 8

    def test_ac30_tomlio_replace_is_the_call_that_lands_the_file(self, repo, monkeypatch):
        calls = []
        real = tomlio._replace

        def recording(src, dst):
            calls.append((os.path.basename(src), os.path.basename(dst)))
            real(src, dst)

        monkeypatch.setattr(tomlio, "_replace", recording)
        ps.apply(repo, set={"theme": "dark"})
        ps.apply(repo, set={"theme": "dark"})  # unchanged: no write at all
        ps.apply(repo, set={"theme": "light"})
        assert calls == [("prefs.json.tmp", "prefs.json")] * 2
        assert not os.path.exists(_file(repo) + ".tmp")

    def test_ac31_store_path_is_under_console_cache_of_the_root_it_is_given(self, repo):
        path = ps._path(repo)
        assert os.path.normpath(path) == os.path.normpath(_file(repo))
        assert os.path.normpath(path).startswith(os.path.normpath(repo) + os.sep)
        assert os.path.normpath(os.path.dirname(path)).endswith(
            os.path.join("console", ".cache"))
        real = find_repo_root()
        with open(os.path.join(real, ".gitignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.read().splitlines()]
        assert "console/.cache/" in lines

    def test_ac31_a_write_creates_the_cache_directory_in_the_scratch_root(self, repo):
        assert not os.path.isdir(os.path.dirname(_file(repo)))
        ps.apply(repo, set={"theme": "dark"})
        assert os.path.isfile(_file(repo))


class TestLayoutContract:
    def test_ac44_a_32kb_layout_object_is_stored_returned_and_deleted(self, repo):
        pad = _value_of_bytes(32000)
        layout = {"v": 1, "panes": {"agents": 320}, "pad": pad}
        assert len(json.dumps(layout, sort_keys=True).encode()) <= 32768
        ps.apply(repo, set={"layout": layout})
        assert ps.snapshot(repo)["prefs"]["layout"] == layout
        ps.apply(repo, delete=["layout"])
        assert "layout" not in ps.snapshot(repo)["prefs"]
        assert ps.snapshot(repo)["rev"] == 2


class TestImport:
    """The one-time move of a browser's legacy `localStorage` onto the server."""

    def test_ac46_an_empty_server_imports_every_valid_key_and_repeating_is_a_noop(self, repo):
        values = {"theme": "dark", "voice": {"autoRead": False}, "panelOpen": {"a": 1}}
        first = ps.import_values(repo, values)
        assert first["imported"] == ["theme", "voice", "panelOpen"]
        assert first["skipped"] == [] and first["rejected"] == []
        assert first["closed"] is False
        assert first["prefs"] == values and first["rev"] == 1
        again = ps.import_values(repo, values)
        assert again["imported"] == first["imported"]
        assert again["skipped"] == [] and again["rejected"] == []
        assert again["rev"] == 1  # equal values are reported, not re-stored

    def test_ac47_a_different_server_value_is_skipped_and_stays(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        result = ps.import_values(repo, {"theme": "light", "voice": {"autoRead": True}})
        assert result["imported"] == ["voice"]
        assert result["skipped"] == ["theme"]
        assert result["rejected"] == []
        assert ps.snapshot(repo)["prefs"] == {"theme": "dark", "voice": {"autoRead": True}}
        assert result["prefs"]["theme"] == "dark"
        assert result["rev"] == 2

    def test_ac47_a_batch_that_stores_nothing_new_leaves_rev_alone(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        result = ps.import_values(repo, {"theme": "light"})
        assert result["skipped"] == ["theme"] and result["rev"] == 1

    def test_one_import_bumps_rev_once_however_many_keys_it_stores(self, repo):
        result = ps.import_values(repo, {"a": 1, "b": 2, "c": 3})
        assert result["rev"] == 1 and _on_disk(repo)["rev"] == 1

    def test_ac48_after_reset_import_is_closed_and_stores_nothing(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        ps.reset(repo)
        result = ps.import_values(repo, {"theme": "light", "voice": 1})
        assert result["closed"] is True
        assert result["imported"] == [] and result["skipped"] == [] and result["rejected"] == []
        assert result["prefs"] == {}
        assert ps.snapshot(repo) == {"prefs": {}, "rev": 2, "import_open": False}

    def test_ac75_invalid_key_oversize_value_and_a_valid_key_in_one_call(self, repo):
        result = ps.import_values(repo, {
            "1x": "bad key",
            "big": _value_of_bytes(32769),
            "theme": "dark",
        })
        assert result["imported"] == ["theme"]
        assert result["skipped"] == []
        assert [r["key"] for r in result["rejected"]] == ["1x", "big"]
        assert all(r["reason"] for r in result["rejected"])
        assert "32768" in result["rejected"][1]["reason"]
        assert ps.snapshot(repo)["prefs"] == {"theme": "dark"}

    def test_ac75_an_unserialisable_value_is_rejected_not_raised(self, repo):
        result = ps.import_values(repo, {"n": float("nan"), "ok": 1})
        assert result["imported"] == ["ok"]
        assert [r["key"] for r in result["rejected"]] == ["n"]

    def test_ac75_file_overflow_rejects_the_overflow_keys_not_the_earlier_ones(self, repo):
        values = {"f%d" % i: _value_of_bytes(32000) for i in range(10)}
        result = ps.import_values(repo, values)
        assert result["imported"] == ["f%d" % i for i in range(8)]
        assert [r["key"] for r in result["rejected"]] == ["f8", "f9"]
        assert "262144" in result["rejected"][0]["reason"]
        assert sorted(ps.snapshot(repo)["prefs"]) == ["f%d" % i for i in range(8)]
        assert os.path.getsize(_file(repo)) <= 262144

    def test_ac75_key_count_overflow_rejects_the_overflow_keys_not_the_earlier_ones(self, repo):
        values = {"k%03d" % i: i for i in range(130)}
        result = ps.import_values(repo, values)
        assert len(result["imported"]) == 128
        assert result["imported"][0] == "k000" and result["imported"][-1] == "k127"
        assert [r["key"] for r in result["rejected"]] == ["k128", "k129"]
        assert "128" in result["rejected"][0]["reason"]
        assert len(ps.snapshot(repo)["prefs"]) == 128

    def test_a_non_object_import_is_refused(self, repo):
        for bad in (["a"], "theme", None, 3):
            with pytest.raises(ValueError):
                ps.import_values(repo, bad)
        assert not os.path.exists(_file(repo))

    def test_ac80_two_threads_importing_the_same_values_end_in_one_state(self, repo):
        values = {"theme": "dark", "voice": {"autoRead": True}, "panelOpen": {"x": 1},
                  "agentLane": "all", "hiddenTabs": ["vault"]}
        barrier = threading.Barrier(2)
        results, errors = [], []

        def work():
            try:
                barrier.wait()
                results.append(ps.import_values(repo, values))
            except Exception as exc:  # surfaced by the assert below
                errors.append(exc)

        threads = [threading.Thread(target=work) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert len(results) == 2
        assert results[0]["imported"] == results[1]["imported"] == list(values)
        assert results[0]["prefs"] == results[1]["prefs"] == values
        assert results[0]["rev"] == results[1]["rev"] == 1
        on_disk = _on_disk(repo)
        assert on_disk["prefs"] == values and on_disk["rev"] == 1


class TestReset:
    def test_ac49_reset_empties_bumps_rev_and_closes_the_import_window(self, repo):
        ps.apply(repo, set={"theme": "dark", "layout": {"a": 1}})
        assert ps.reset(repo) == {"prefs": {}, "rev": 2, "closed": True}
        on_disk = _on_disk(repo)
        assert on_disk["prefs"] == {} and on_disk["rev"] == 2
        assert on_disk["import_closed"] is True
        assert ps.snapshot(repo)["import_open"] is False

    def test_ac49_reset_of_a_missing_file_still_closes_the_window(self, repo):
        assert ps.reset(repo) == {"prefs": {}, "rev": 1, "closed": True}
        assert ps.snapshot(repo) == {"prefs": {}, "rev": 1, "import_open": False}

    def test_a_second_reset_changes_nothing(self, repo):
        ps.apply(repo, set={"theme": "dark"})
        ps.reset(repo)
        assert ps.reset(repo) == {"prefs": {}, "rev": 2, "closed": True}

    def test_writes_after_a_reset_are_stored_and_the_window_stays_closed(self, repo):
        ps.reset(repo)
        assert ps.apply(repo, set={"theme": "dark"}) == {"rev": 2, "prev": 1}
        assert ps.snapshot(repo) == {"prefs": {"theme": "dark"}, "rev": 2, "import_open": False}
