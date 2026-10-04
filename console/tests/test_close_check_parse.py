"""T-021 FR-8 grammar: verification tables, status classes, evidence refs."""

import os

import pytest

from conftest import _write
from server import close_check as cc
from server import runs, tickets

T = "T-001"


class TestTables:
    TEXT = (
        "## Acceptance\n\n| # | Criterion | Status | Evidence |\n|---|---|---|---|\n"
        "| 1 | does x | **PASS** | `console/x.py:3` |\n"
        "| 2 | does `a | b` | PASS | prose |\n\n"
        "| Command | Result |\n|---|---|\n| pytest | ok |\n\n"
        "| FR | Task | Code | Test |\n|---|---|---|---|\n| 1 | 2 | a | b |\n")

    def test_only_status_and_evidence_tables_are_kept(self):
        rows = cc.parse_verification_tables(self.TEXT)
        assert [r["id"] for r in rows] == ["1", "2"]
        assert rows[0]["status"] == "**PASS**" and rows[0]["evidence"] == "`console/x.py:3`"
        assert rows[0]["line"] == 5

    def test_pipe_inside_backticks_does_not_split_the_cell(self):
        assert cc.parse_verification_tables(self.TEXT)[1]["criterion"] == "does `a | b`"

    def test_no_table_gives_no_rows(self):
        assert cc.parse_verification_tables("# nothing\n") == []

    def test_short_row_pads_missing_cells_empty(self):
        text = "| # | Status | Evidence |\n|---|---|---|\n| 1 | PASS |\n"
        assert cc.parse_verification_tables(text)[0]["evidence"] == ""


class TestStatusClass:
    @pytest.mark.parametrize("cell,want", [
        ("**PASS**", "pass"), ("PASS — static only", "pass"), ("PASSED", "pass"),
        ("MET", "pass"), ("pass (with one worded caveat)", "pass"),
        ("PASS / PENDING", "not_pass"), ("NOT MET", "not_pass"), ("FAILED", "not_pass"),
        ("PARTIAL", "not_pass"), ("PASS but BLOCKED", "not_pass"), ("PENDING", "not_pass"),
        ("", "not_pass"), ("???", "not_pass"),
        ("DEFERRED", "descoped"), ("CUT", "descoped"), ("dropped", "descoped"),
        ("N/A", "descoped"), ("**DEFERRED** to T-9", "descoped"),
    ])
    def test_table(self, cell, want):
        assert cc.classify_status(cell) == want


@pytest.fixture
def tree(repo):
    _write(os.path.join(repo, "console", "x.py"), "a = 1\nb = 2\nc = 3\n")
    _write(os.path.join(repo, "console", "tests", "test_y.py"),
           "class TestA:\n    def test_y(self):\n        pass\n\n\ndef test_z():\n    pass\n")
    tickets.create(repo, T, "A ticket")
    _write(os.path.join(tickets.dir_for(repo, T), "T-001-decision-log.md"), "# d\n")
    return repo


def res(tree, ref):
    return cc.resolve_ref(tree, T, ref)


class TestRefs:
    @pytest.mark.parametrize("ref,want", [
        ("console/x.py", "accepted"), ("console/x.py:3", "accepted"),
        ("console/x.py:2-3", "accepted"), ("console/tests/test_y.py::test_y", "accepted"),
        ("console/tests/test_y.py::TestA::test_y", "accepted"),
        ("console/tests/test_y.py::test_z[param]", "accepted"),
        ("T-001-decision-log.md", "accepted"),
        ("console/nope.py", "missing"), ("console/x.py:4", "missing"),
        ("console/x.py:2-9", "missing"), ("console/tests/test_y.py::test_absent", "missing"),
        ("run:aaaaaaaaaaaa", "missing"), ("T-001-absent.md", "missing"),
        ("tray.rs", "unverifiable"), ("pytest 1406 passed", "unverifiable"),
        ("2 947 ms to 4 ms", "unverifiable"), ("console\\server\\x.py", "unverifiable"),
        ("/tmp/x.py", "unverifiable"), ("https://example.com/a/b.md", "unverifiable"),
        ("../outside/x.py", "unverifiable"), ("", "unverifiable"),
        ("console/server/", "unverifiable"), ("0/7", "unverifiable"),
        ("held/unknown", "unverifiable"), ("qwen/qwen3.8-27b", "unverifiable"),
        ("agents.toml/console.toml/schedules.toml", "unverifiable"),
    ])
    def test_resolution_table(self, tree, ref, want):
        assert res(tree, ref) == want

    def test_run_resolves_only_when_done(self, tree):
        done = runs.create(tree, executor="chat", executor_id="c", ticket=T, state="done")
        live = runs.create(tree, executor="chat", executor_id="c", ticket=T, state="running")
        assert res(tree, "run:" + done["id"]) == "accepted"
        assert res(tree, "run:" + live["id"]) == "missing"

    def test_path_under_ticket_dir_is_found(self, tree):
        _write(os.path.join(tickets.dir_for(tree, T), "ticket-scripts", "s.py"), "x\n")
        assert res(tree, "ticket-scripts/s.py") == "accepted"

    def test_extract_refs_from_a_cell(self):
        cell = ("`console/x.py:3` and console/tests/test_y.py::test_y, T-001-decision-log.md, "
                "run:0123456789ab; https://example.com/a/b.md /tmp/x.py tray.rs 3/3 more.")
        got = cc.extract_refs(cell)
        assert "console/x.py:3" in got and "console/tests/test_y.py::test_y" in got
        assert "T-001-decision-log.md" in got and "run:0123456789ab" in got
        assert not any("example.com" in r or "tmp" in r or r == "tray.rs" for r in got)

    def test_extract_refs_trailing_period_is_not_part_of_the_path(self):
        assert cc.extract_refs("see console/server/x.py.") == ["console/server/x.py"]


def test_basis_constant():
    assert cc.BASIS == "existence"


def test_no_subprocess_no_git_no_write():
    import ast
    tree = ast.parse(open(cc.__file__, encoding="utf-8").read())
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                for a in n.names}
    imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.level == 0}
    assert not imported & {"subprocess", "shutil", "socket", "urllib"}
    calls = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(tree)
             if isinstance(n, ast.Call)}
    assert not calls & {"system", "atomic_write", "atomic_update", "write", "remove", "makedirs"}
