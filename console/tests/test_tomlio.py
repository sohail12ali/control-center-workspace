"""tomlio is a deliberate TOML *subset*, so these tests pin the subset — what
it must round-trip, and where it must fail loudly rather than guess."""

import os
import threading

import pytest

from server import tomlio


def _round_trip(data):
    return tomlio.loads(tomlio.dumps(data))


class TestRoundTrip:
    def test_scalars_survive_their_types(self):
        data = {"t": {"s": "hello", "b": True, "n": 42, "f": 1.5, "empty": ""}}
        assert _round_trip(data) == data

    def test_bool_does_not_degrade_to_string(self):
        # The failure this guards is silent: a card with status false would
        # render as the truthy string "false" everywhere downstream.
        out = _round_trip({"t": {"flag": False}})
        assert out["t"]["flag"] is False

    def test_arrays_of_strings(self):
        data = {"t": {"tags": ["a", "b", "c"], "empty": []}}
        assert _round_trip(data) == data

    def test_array_of_tables(self):
        data = {"item": [{"id": "Q1", "text": "one"}, {"id": "Q2", "text": "two"}]}
        assert _round_trip(data) == data

    def test_comma_inside_a_quoted_array_element(self):
        # Regression: a naive split(",") tore this element in half, so the
        # value written was not the value read back.
        data = {"t": {"args": ["--flag", "a,b", "-p", "{prompt}"]}}
        assert _round_trip(data)["t"]["args"] == ["--flag", "a,b", "-p", "{prompt}"]

    def test_quotes_and_backslashes_escape(self):
        data = {"t": {"s": 'he said "hi"\\done'}}
        assert _round_trip(data) == data

    def test_newline_in_string(self):
        data = {"t": {"s": "line one\nline two"}}
        assert _round_trip(data) == data

    def test_dates_stay_strings(self):
        # Bare ISO dates are stored as strings by design — nothing downstream
        # wants a date object it would have to re-serialise.
        parsed = tomlio.loads('[t]\nd = 2026-08-29\n')
        assert parsed["t"]["d"] == "2026-08-29"

    def test_multiline_array_is_joined(self):
        text = '[t]\nargs = [\n  "a",\n  "b",\n]\n'
        assert tomlio.loads(text)["t"]["args"] == ["a", "b"]


class TestParsing:
    def test_comments_and_blank_lines_ignored(self):
        text = '# lead\n\n[t]\n# inner\nk = "v"  \n'
        assert tomlio.loads(text) == {"t": {"k": "v"}}

    def test_malformed_line_raises(self):
        with pytest.raises(tomlio.TomlError):
            tomlio.loads("[t]\nthis is not a pair\n")

    def test_unclosed_section_header_raises(self):
        with pytest.raises(tomlio.TomlError):
            tomlio.loads("[unclosed\nk = 1\n")


class TestFileIO:
    def test_atomic_write_then_load(self, tmp_path):
        path = str(tmp_path / "a.toml")
        data = {"ticket": {"id": "T1", "tags": ["x"]}}
        tomlio.atomic_write(path, data)
        assert tomlio.load(path) == data

    def test_atomic_write_leaves_no_temp_files(self, tmp_path):
        path = str(tmp_path / "a.toml")
        tomlio.atomic_write(path, {"t": {"k": "v"}})
        assert os.listdir(tmp_path) == ["a.toml"]

    def test_atomic_write_overwrites_in_place(self, tmp_path):
        path = str(tmp_path / "a.toml")
        tomlio.atomic_write(path, {"t": {"k": "one"}})
        tomlio.atomic_write(path, {"t": {"k": "two"}})
        assert tomlio.load(path)["t"]["k"] == "two"

    def test_concurrent_writers_do_not_corrupt(self, tmp_path):
        # The console writes the same ticket.toml from the CLI, the HTTP API,
        # and agent hooks. A torn file here is a lost ticket, so the guarantee
        # under test is "always parseable", not "last writer wins".
        path = str(tmp_path / "a.toml")
        tomlio.atomic_write(path, {"t": {"k": "seed"}})

        def writer(n):
            for _ in range(20):
                tomlio.atomic_write(path, {"t": {"k": "w%d" % n}})

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert tomlio.load(path)["t"]["k"].startswith("w")
