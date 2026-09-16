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


class TestAtomicUpdate:
    """T-017 3a-5: the read-modify-write primitive `tickets.set_claim` reuses
    for race-safe claims — generic, so it is tested at this layer once rather
    than only through the ticket-claim scenario that motivated it."""

    def test_mutates_existing_contents(self, tmp_path):
        path = str(tmp_path / "a.toml")
        tomlio.atomic_write(path, {"t": {"k": "one", "n": 1}})

        def bump(data):
            data["t"]["n"] += 1

        tomlio.atomic_update(path, bump)
        assert tomlio.load(path)["t"]["n"] == 2

    def test_missing_file_starts_from_empty_dict(self, tmp_path):
        path = str(tmp_path / "new.toml")

        def seed(data):
            data["t"] = {"k": "v"}

        tomlio.atomic_update(path, seed)
        assert tomlio.load(path)["t"]["k"] == "v"

    def test_a_raise_inside_mutate_writes_nothing(self, tmp_path):
        path = str(tmp_path / "a.toml")
        tomlio.atomic_write(path, {"t": {"k": "seed"}})

        def boom(data):
            data["t"]["k"] = "changed"
            raise ValueError("refuse")

        with pytest.raises(ValueError):
            tomlio.atomic_update(path, boom)
        # Nothing written, and the lock was released (no leftover .lock file).
        assert tomlio.load(path)["t"]["k"] == "seed"
        assert os.listdir(tmp_path) == ["a.toml"]

    def test_concurrent_updates_do_not_corrupt_or_lose_writes(self, tmp_path):
        """A read-modify-write increment under real concurrency: if the
        read-then-write pair were not lock-guarded end to end, some
        increments would be lost. This is exactly the shape of the claim
        race the primitive was built to close."""
        path = str(tmp_path / "counter.toml")
        tomlio.atomic_write(path, {"t": {"n": 0}})

        def bump(data):
            data["t"]["n"] += 1

        def worker():
            for _ in range(15):
                tomlio.atomic_update(path, bump)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert tomlio.load(path)["t"]["n"] == 60
