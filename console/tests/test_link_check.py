"""Link checker (T-041).

Every rule is proved to FIRE on a planted fault and to stay quiet on a clean
tree; a checker that reports nothing is indistinguishable from one that cannot.
Fixtures are tmp workspaces (the `repo` fixture), never the real vault.
"""

import os

import pytest

from server import link_check, tickets, vault


# --- helpers ---------------------------------------------------------------

def _vault(repo):
    return os.path.join(repo, "knowledge-center")


def _put(repo, rel, text, newline="\n"):
    """Write `text` under the vault; `rel` is vault-relative with `/`."""
    path = os.path.join(_vault(repo), *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", newline))
    return path


def _codes(findings):
    return sorted(f.code for f in findings)


def _of(findings, code):
    return [f for f in findings if f.code == code]


def _index(*rels):
    return link_check.build_index(list(rels))


# --- 01: extractor ---------------------------------------------------------

class TestExtract:
    def test_forms_alias_anchor_and_same_file_anchor(self):
        text = "[[x]] [[x|alias]] [[x#h]] [[x#h|alias]] [[#h]] [[ y ]]\n"
        assert link_check.extract_links(text) == [
            ("x", 1), ("x", 1), ("x", 1), ("x", 1), ("y", 1)]

    def test_code_is_ignored_outside_it_counts(self):
        text = ("`[[a]]` and ``[[b]]``\n"
                "```\n[[c]]\n```\n"
                "~~~\n[[d]]\n~~~\n"
                "  ```text\n[[e]]\n  ```\n"
                "[[f]]\n")
        assert link_check.extract_links(text) == [("f", 11)]

    def test_longer_fence_is_not_closed_by_a_shorter_one(self):
        text = "````\n```\n[[a]]\n```\n````\n[[b]]\n"
        assert link_check.extract_links(text) == [("b", 6)]

    def test_unclosed_fence_runs_to_the_end(self):
        assert link_check.extract_links("```\n[[a]]\n[[b]]\n") == []

    def test_unmatched_backtick_is_literal(self):
        assert link_check.extract_links("a ` [[x]]\n") == [("x", 1)]

    def test_unclosed_brackets_do_not_swallow_the_next_line(self):
        text = "see [[x and more\n[[real-dangling]]\n"
        assert link_check.extract_links(text) == [("real-dangling", 2)]

    def test_second_open_bracket_on_one_line(self):
        assert link_check.extract_links("[[x [[y]]\n") == [("y", 1)]

    def test_bom_does_not_hide_a_first_line_link(self):
        assert link_check.extract_links("\ufeff[[x]]\n") == [("x", 1)]

    def test_line_numbers_agree_across_line_endings(self):
        base = "a\n[[one]]\n\n[[two]]\n"
        want = link_check.extract_links(base)
        assert want == [("one", 2), ("two", 4)]
        for nl in ("\r\n", "\r"):
            assert link_check.extract_links(base.replace("\n", nl)) == want
        assert link_check.extract_links("a\r\n[[one]]\n\r[[two]]") == [("one", 2), ("two", 4)]

    def test_unicode_line_separator_is_not_a_line_break(self):
        assert link_check.extract_links("a\u2028b\n[[x]]\n") == [("x", 2)]

    def test_empty_target_is_ignored(self):
        assert link_check.extract_links("[[]] [[|x]] [[ #h]]\n") == []


# --- 01: resolver ----------------------------------------------------------

class TestResolve:
    def test_bare_basename_resolves_anywhere_in_the_vault(self):
        ix = _index("a/b/T-041-summary.md", "wiki/x.md")
        assert link_check.resolve(ix, "T-041-summary") == ("ok", ["a/b/T-041-summary.md"], "")
        assert link_check.resolve(ix, "x")[0] == "ok"

    def test_case_difference_is_dangling_with_a_note(self):
        ix = _index("a/T-041-summary.md")
        status, hits, note = link_check.resolve(ix, "t-041-summary")
        assert (status, hits) == ("dangling", [])
        assert "T-041-summary" in note and "case" in note

    def test_md_suffix_and_folder_prefix_resolve_as_a_form(self):
        ix = _index("a/x.md")
        assert link_check.resolve(ix, "x.md")[0] == "form"
        assert link_check.resolve(ix, "artifacts/T-1/x")[0] == "form"
        assert link_check.resolve(ix, "artifacts/T-1/x.md")[0] == "form"

    def test_toml_and_parent_targets_are_dangling(self):
        ix = _index("a/x.md", "CLAUDE.md")
        assert link_check.resolve(ix, "x.toml")[0] == "dangling"
        assert link_check.resolve(ix, "a/x.toml")[0] == "dangling"
        assert link_check.resolve(ix, "../../CLAUDE.md")[0] == "dangling"
        assert link_check.resolve(ix, "..")[0] == "dangling"

    def test_ambiguous_basename_resolves_to_every_file(self):
        ix = _index("a/x.md", "b/x.md")
        assert link_check.resolve(ix, "x") == ("ok", ["a/x.md", "b/x.md"], "")

    def test_a_dotted_basename_matches_exactly(self):
        assert link_check.resolve(_index("a/v1.2.md"), "v1.2")[0] == "ok"

    def test_resolver_never_opens_a_file(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("resolver touched the filesystem")
        monkeypatch.setattr("builtins.open", boom)
        monkeypatch.setattr(os.path, "exists", boom)
        monkeypatch.setattr(os, "stat", boom)
        ix = _index("a/x.md")
        for target in ("x", "../../CLAUDE.md", "C:/Windows/win.ini", "x.toml", "/etc/passwd"):
            link_check.resolve(ix, target)


# --- 01: drift guard against vault.build_graph -----------------------------

class TestDriftGuardAgainstTheVaultGraph:
    def test_resolved_pairs_equal_the_graph_wikilink_edges(self, repo):
        _put(repo, "artifacts/T-1/T-1-summary.md",
             "# S\n[[T-1-plan]] [[T-1-plan|alias]] [[T-1-plan#h]] [[wiki-a]] [[ghost]] [[T-1-summary]]\n")
        _put(repo, "artifacts/T-1/T-1-plan.md", "[[T-1-summary]]\n[[#same]] [[wiki-a#x|y]]\n")
        _put(repo, "wiki/wiki-a.md", "[[T-1-plan]]\n[[also-here]]\n")
        _put(repo, "docs/also-here.md", "no links\n")
        _put(repo, "docs/dup.md", "x\n")
        _put(repo, "wiki/dup.md", "[[dup]]\n[[docs-only]]\n")
        _put(repo, "logs/2026-10/d.md", "[[dup]]\n")

        edges = {(e["source"], e["target"])
                 for e in vault.build_graph(repo)["edges"] if e["type"] == "wikilink"}

        files = link_check.walk_md(_vault(repo))
        ix = link_check.build_index([rel for rel, _ in files])
        mine = set()
        for rel, full in files:
            for target, _line in link_check.extract_links(link_check._read(full)):
                status, hits, _note = link_check.resolve(ix, target)
                if status != "ok":
                    continue
                mine.update((rel, hit) for hit in hits if hit != rel)

        assert mine == edges
        assert len(edges) >= 6  # the fixture must exercise real edges


# --- fixtures for the scan rules -------------------------------------------

def _links(*names):
    return "## Links\n- " + " · ".join("[[%s]]" % n for n in names) + "\n"


def _ticket(repo, tid, artifacts=("summary", "plan"), title=None, stage=None, bodies=None):
    """Create ticket `tid` with mutually linked artifacts; `bodies` overrides the
    full text of a named artifact (key = artifact suffix)."""
    tickets.create(repo, tid, title or "Title " + tid)
    if stage:
        tickets.move(repo, tid, stage)
    names = ["%s-%s" % (tid, a) for a in artifacts]
    for art, name in zip(artifacts, names):
        text = (bodies or {}).get(art)
        if text is None:
            text = "# %s\n\n%s" % (name, _links(*names))
        _put(repo, "artifacts/%s/%s.md" % (tid, name), text)
    return names


def _map(repo, *rows):
    """Write artifact-map.md from `(section, line)` pairs, sections in order."""
    out = "# Artifact Map\n\n"
    for section in ("Active", "Blocked", "Completed", "Archived"):
        out += "## %s\n\n" % section
        out += "".join(line + "\n" for sec, line in rows if sec == section)
        out += "\n"
    _put(repo, "artifact-map.md", out)


def _row(tid, title=None, label="Open", owner="Me", date="2026-10-06"):
    return "- [[%s-summary]] — %s — %s — %s — %s" % (tid, title or "Title " + tid, label, owner, date)


@pytest.fixture
def clean(repo):
    """Two tickets, mutually linked artifacts, a consistent map, and the exempt
    corners (`_template`, `_shared`, `ticket-scripts`, a wiki page)."""
    _ticket(repo, "T-001")
    _ticket(repo, "T-002")
    _map(repo, ("Active", _row("T-001")), ("Active", _row("T-002")))
    _put(repo, "artifacts/_template/summary.md", "# {ID}\n[[{ID}-plan]] [[ghost]]\n")
    _put(repo, "artifacts/_shared/notes.md", "# shared\nno block here\n")
    _put(repo, "artifacts/T-001/ticket-scripts/README.md", "# scripts\n")
    _put(repo, "artifacts/T-001/notes-readme.md", "# readme\n")
    _put(repo, "wiki/page.md", "# page\n[[T-001-summary]] and [[summary]]\n")
    return repo


def _scan(repo):
    return link_check.scan(repo)[0]


# --- 02: scan scope --------------------------------------------------------

class TestScanScope:
    def test_clean_tree_has_no_findings_and_counts(self, clean):
        findings, stats = link_check.scan(clean)
        assert findings == []
        assert stats["tickets"] == 2
        # 4 artifacts + map + 3 exempt ticket-dir/shared files + wiki; _template excluded
        assert stats["files"] == 9

    def test_only_ticket_artifacts_get_links_block_rules(self, clean):
        _put(clean, "artifacts/_shared/notes.md", "# shared\n[[nope]]\n")
        found = _scan(clean)
        assert _codes(found) == ["body-dangling"]
        assert found[0].path == "artifacts/_shared/notes.md"
        # _template placeholders and a missing block there are not findings,
        # yet `summary` (a _template file) is in the resolution index
        assert not [f for f in _scan(clean) if "_template" in f.path]

    def test_relocated_vault_is_scanned_not_the_default_folder(self, repo):
        os.makedirs(os.path.join(repo, "elsewhere", "artifacts"))
        with open(os.path.join(repo, "workspace.toml"), "w", encoding="utf-8") as fh:
            fh.write('vault = "./elsewhere"\nconsole = "./console"\n')
        from server import paths
        assert paths.vault_dir(repo).endswith("elsewhere")
        tickets.create(repo, "T-001", "Title T-001")
        path = os.path.join(repo, "elsewhere", "artifacts", "T-001", "T-001-summary.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# S\n\n## Links\n- [[moved-away]]\n")
        decoy = os.path.join(repo, "knowledge-center", "wiki", "decoy.md")
        os.makedirs(os.path.dirname(decoy))
        with open(decoy, "w", encoding="utf-8") as fh:
            fh.write("[[decoy-ghost]]\n")
        found = _scan(repo)
        assert [f.path for f in _of(found, "links-dangling")] == ["artifacts/T-001/T-001-summary.md"]
        assert not [f for f in found if "decoy" in f.path or "decoy-ghost" in f.message]

    def test_dot_directories_and_non_md_files_are_skipped(self, clean):
        _put(clean, ".obsidian/x.md", "[[ghost]]\n")
        _put(clean, "wiki/data.toml", "[[ghost]]\n")
        _put(clean, "wiki/.hidden.md", "[[ghost]]\n")
        assert _scan(clean) == []


# --- 02: Links-block form --------------------------------------------------

class TestLinksBlock:
    def _one(self, repo, text):
        try:
            _ticket(repo, "T-001", artifacts=("summary", "plan"), bodies={"plan": text})
        except FileExistsError:  # a second call in one test: rewrite the artifact
            _put(repo, "artifacts/T-001/T-001-plan.md", text)
        return [f for f in _scan(repo) if f.path.endswith("T-001-plan.md")
                and not f.code.startswith(("map-", "one-way", "links-incomplete"))]

    def test_missing_block(self, repo):
        found = self._one(repo, "# Plan\nbody\n")
        assert _codes(found) == ["links-missing"]
        assert (found[0].level, found[0].line) == ("error", 1)

    def test_duplicate_blocks_report_the_second(self, repo):
        text = "# P\n## Links\n- [[T-001-summary]]\n\n## Links\n- [[T-001-plan]]\n"
        found = self._one(repo, text)
        assert _codes(found) == ["links-duplicate"]
        assert found[0].line == 5

    @pytest.mark.parametrize("text", [
        "# P\n## Links- [[T-001-summary]]\n",
        "# P\n## Links text\n- [[T-001-summary]]\n",
        "# P\nsome text ## Links\n- [[T-001-summary]]\n",
        "# P\n##Links\n- [[T-001-summary]]\n",
    ])
    def test_malformed_heading_is_one_finding_not_also_missing(self, repo, text):
        found = self._one(repo, text)
        assert _codes(found) == ["links-malformed"]
        assert found[0].level == "error"

    def test_trailing_spaces_on_the_heading_are_accepted(self, repo):
        assert self._one(repo, "# P\n## Links   \n- [[T-001-summary]]\n") == []
        assert self._one(repo, "# P\n## Links\t\n- [[T-001-summary]]\n") == []

    def test_heading_after_the_block_is_links_not_last(self, repo):
        found = self._one(repo, "# P\n## Links\n- [[T-001-summary]]\n\n## Appendix\n")
        assert _codes(found) == ["links-not-last"]
        assert (found[0].level, found[0].line) == ("warn", 5)

    def test_level_three_heading_after_the_block_is_still_inside_it(self, repo):
        assert self._one(repo, "# P\n## Links\n- [[T-001-summary]]\n### Related\n- [[T-001-plan]]\n") == []

    def test_a_links_heading_in_code_is_not_a_block(self, repo):
        text = "# P\n```\n## Links\n```\nuse `## Links` here\n"
        assert _codes(self._one(repo, text)) == ["links-missing"]

    def test_line_endings_do_not_change_the_findings(self, repo):
        _ticket(repo, "T-001", artifacts=("summary", "plan"))
        base = "# P\n## Links\n- [[T-001-summary]] [[ghost]]\n"
        want = None
        for nl in ("\n", "\r\n", "\r"):
            _put(repo, "artifacts/T-001/T-001-plan.md", base, newline=nl)
            got = [(f.code, f.line) for f in _scan(repo) if f.path.endswith("plan.md")]
            want = want or got
            assert got == want
        assert ("links-dangling", 3) in want


# --- 02: dangling, form, case ----------------------------------------------

class TestDangling:
    def test_block_dangling_is_an_error_with_file_and_line(self, repo):
        _ticket(repo, "T-001", bodies={"plan": "# P\ntext\n\n## Links\n- [[T-001-summary]]\n- [[ghost]]\n"})
        found = _of(_scan(repo), "links-dangling")
        assert [(f.level, f.path, f.line) for f in found] == [
            ("error", "artifacts/T-001/T-001-plan.md", 6)]
        assert "[[ghost]]" in found[0].message

    def test_prose_dangling_is_a_warning_and_so_is_a_placeholder(self, repo):
        _ticket(repo, "T-001", bodies={
            "plan": "# P\n[[ghost]] and [[…]]\n\n## Links\n- [[T-001-summary]]\n"})
        found = [f for f in _scan(repo) if f.code in ("body-dangling", "links-dangling")]
        assert [(f.code, f.level, f.line) for f in found] == [
            ("body-dangling", "warn", 2), ("body-dangling", "warn", 2)]

    def test_dossier_links_block_is_an_error_and_has_no_other_rule(self, clean):
        _put(clean, "investigations/INV-1.md", "# i\n[[prose-ghost]]\n\n## Links\n- [[CLAUDE]]\n")
        _put(clean, "investigations/INV-2.md", "# no block, no sibling rule\n")
        found = _scan(clean)
        assert sorted((f.code, f.line) for f in found) == [("body-dangling", 2), ("links-dangling", 5)]

    def test_frozen_files_are_not_exempt(self, repo):
        _ticket(repo, "T-001", bodies={
            "plan": "---\nfreeze_status: frozen\n---\n# P\n\n## Links\n- [[T-001-summary]] · [[renamed-away]]\n"})
        found = _of(_scan(repo), "links-dangling")
        assert [(f.path, f.line) for f in found] == [("artifacts/T-001/T-001-plan.md", 7)]

    def test_case_only_difference_is_named(self, repo):
        _ticket(repo, "T-001", bodies={"plan": "# P\n\n## Links\n- [[T-001-summary]] · [[t-001-SUMMARY]]\n"})
        found = _of(_scan(repo), "links-dangling")
        assert len(found) == 1 and "case" in found[0].message

    def test_link_forms_resolve_with_a_warning(self, repo):
        _ticket(repo, "T-001", bodies={"plan": (
            "# P\n\n## Links\n- [[T-001-summary.md]] · [[artifacts/T-001/T-001-summary]] · [[T-001-plan]]\n")})
        found = [f for f in _scan(repo) if f.path.endswith("plan.md")]
        assert [(f.code, f.level) for f in found if f.code == "link-form"] == [("link-form", "warn")] * 2
        assert not _of(found, "links-dangling")

    def test_toml_and_parent_targets_are_dangling(self, repo):
        _ticket(repo, "T-001", bodies={"plan": (
            "# P\n\n## Links\n- [[ticket.toml]] · [[../../CLAUDE.md]] · [[T-001-summary]]\n")})
        assert len(_of(_scan(repo), "links-dangling")) == 2

    def test_unclosed_bracket_does_not_hide_a_real_dangling_link(self, repo):
        _ticket(repo, "T-001", bodies={"plan": (
            "# P\n\n## Links\n- [[T-001-summary]] and [[broken\n- [[ghost]]\n")})
        found = _of(_scan(repo), "links-dangling")
        assert [f.line for f in found] == [5]

    def test_invalid_utf8_does_not_abort_the_run(self, clean):
        path = os.path.join(_vault(clean), "wiki", "bad.md")
        with open(path, "wb") as fh:
            fh.write(b"# bad \xff\xfe\n[[ghost]]\n")
        assert [f.line for f in _of(_scan(clean), "body-dangling")] == [2]


# --- 02: sibling rules -----------------------------------------------------

def _trio(repo, **bodies):
    """T-001 with summary, plan, notes; each links every sibling unless overridden."""
    return _ticket(repo, "T-001", artifacts=("summary", "plan", "notes"), bodies=bodies)


class TestSiblings:
    def test_mutual_links_give_no_one_way(self, repo):
        _trio(repo)
        assert _of(_scan(repo), "one-way-link") == []

    def test_one_way_link_is_reported_at_the_file_that_lacks_the_back_link(self, repo):
        _trio(repo, summary="# S\n\n## Links\n- [[T-001-plan]] · [[T-001-notes]]\n",
              plan="# P\n\n## Links\n- [[T-001-notes]]\n",
              notes="# N\n\n## Links\n- [[T-001-summary]] · [[T-001-plan]]\n")
        found = _of(_scan(repo), "one-way-link")
        assert [(f.level, f.path, f.line) for f in found] == [
            ("warn", "artifacts/T-001/T-001-plan.md", 3)]
        assert "T-001-summary" in found[0].message

    def test_self_link_and_other_tickets_are_not_one_way(self, repo):
        _ticket(repo, "T-001", bodies={
            "summary": "# S\n\n## Links\n- [[T-001-summary]] · [[T-001-plan]] · [[T-002-summary]]\n"})
        _ticket(repo, "T-002")
        found = _scan(repo)
        assert _of(found, "one-way-link") == []
        assert _of(found, "links-incomplete") == []

    def test_a_sibling_without_a_links_block_links_nothing(self, repo):
        _ticket(repo, "T-001", bodies={"plan": "# P\nno block\n"})
        found = [f for f in _scan(repo) if not f.code.startswith("map-")]
        assert [(f.code, f.path, f.line) for f in found if f.code == "one-way-link"] == [
            ("one-way-link", "artifacts/T-001/T-001-plan.md", 1)]
        assert _codes([f for f in found if f.path.endswith("plan.md")]) == ["links-missing", "one-way-link"]

    def test_incomplete_block_lists_the_missing_siblings_once(self, repo):
        _trio(repo, summary="# S\n\n## Links\n- [[T-001-plan]]\n",
              plan="# P\n\n## Links\n- [[T-001-summary]] · [[T-001-notes]]\n",
              notes="# N\n\n## Links\n- [[T-001-summary]] · [[T-001-plan]]\n")
        inc = _of(_scan(repo), "links-incomplete")
        assert [(f.path, f.line) for f in inc] == [("artifacts/T-001/T-001-summary.md", 3)]
        assert "T-001-notes" in inc[0].message and "T-001-plan" not in inc[0].message

    def test_duplicate_blocks_count_as_their_union(self, repo):
        _trio(repo, summary="# S\n\n## Links\n- [[T-001-plan]]\n\n## Links\n- [[T-001-notes]]\n")
        found = _scan(repo)
        assert _codes([f for f in found if f.path.endswith("summary.md")]) == ["links-duplicate"]

    def test_malformed_heading_counts_as_linking_nothing(self, repo):
        _trio(repo, notes="# N\n## Links- [[T-001-summary]] · [[T-001-plan]]\n")
        found = _scan(repo)
        assert _codes([f for f in found if f.path.endswith("notes.md")]) == [
            "links-malformed", "one-way-link", "one-way-link"]


# --- 02: one home, deterministic subset ------------------------------------

class TestOneHome:
    def test_artifact_with_another_tickets_prefix_is_misplaced(self, repo):
        _ticket(repo, "T-001")
        _ticket(repo, "T-002")
        _put(repo, "artifacts/T-001/T-002-notes.md", "# n\n\n## Links\n- [[T-001-summary]]\n")
        _put(repo, "artifacts/T-001/notes-readme.md", "# not an artifact\n")
        found = _of(_scan(repo), "misplaced-artifact")
        assert [(f.level, f.path) for f in found] == [("warn", "artifacts/T-001/T-002-notes.md")]

    def test_same_basename_twice_is_one_finding_naming_both_and_still_resolves(self, clean):
        _put(clean, "wiki/dup.md", "# a\n")
        _put(clean, "docs/dup.md", "# b\n[[dup]]\n")
        found = _scan(clean)
        assert _codes(found) == ["ambiguous-basename"]
        assert "docs/dup.md" in found[0].message and "wiki/dup.md" in found[0].message


# --- 03: artifact map against ticket.toml ----------------------------------

def _map_only(findings):
    return [f for f in findings if f.code.startswith("map-")]


class TestMapRows:
    def test_parse_map_reads_only_bullets_that_begin_with_a_link(self):
        text = ("# Artifact Map\n\n## Active\n\n"
                "- [[T-001-summary]] — A title — Open — Me — 2026-10-06\n"
                "- **IDs:** `T###` and [[T-002-summary]] in prose\n"
                "`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`\n"
                "## Completed\n"
                "- [[T-003-summary]] — Has — a dash — Complete — Me — 2026-10-06\n")
        rows = link_check.parse_map(link_check.normalize(text))
        assert [(r["line"], r["target"], r["section"]) for r in rows] == [
            (5, "T-001-summary", "Active"), (9, "T-003-summary", "Completed")]
        assert rows[1]["fields"] == ("Has — a dash", "Complete", "Me", "2026-10-06")

    def test_well_formed_rows_yield_nothing(self, clean):
        assert _map_only(_scan(clean)) == []

    def test_non_row_bullets_are_ignored(self, clean):
        path = os.path.join(_vault(clean), "artifact-map.md")
        with open(path, "a", encoding="utf-8", newline="") as fh:
            fh.write("\n## Conventions\n\n- **IDs:** `T###`\n`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`\n")
        assert _scan(clean) == []

    @pytest.mark.parametrize("row", [
        "- [[T-001-summary]] — Title T-001 — Open — Me",              # no date
        "- [[T-001-summary]] — Title T-001 — Open — Me — 06/10/2026",  # not ISO
        "- [[T-001-summary]] - Title T-001 - Open - Me - 2026-10-06",   # hyphens, not em dashes
        "- [[T-001-summary]]",
    ])
    def test_malformed_row_is_a_warning_and_no_drift_is_guessed(self, repo, row):
        _ticket(repo, "T-001")
        _map(repo, ("Active", row))
        found = _scan(repo)
        assert _codes(_map_only(found)) == ["map-row-format"]
        assert _map_only(found)[0].level == "warn"

    def test_title_with_a_dash_matches_when_ticket_toml_has_it(self, repo):
        _ticket(repo, "T-001", title="Make it fast — and honest")
        _map(repo, ("Active", _row("T-001", title="Make it fast — and honest")))
        assert _map_only(_scan(repo)) == []


class TestMapAgainstTheFiles:
    def test_no_map_file_is_one_error_and_no_other_map_finding(self, clean):
        os.remove(os.path.join(_vault(clean), "artifact-map.md"))
        found = _scan(clean)
        assert _codes(found) == ["map-missing"]
        assert found[0].level == "error"

    def test_row_whose_target_is_absent_is_map_dangling_only(self, clean):
        _map(clean, ("Active", _row("T-001")), ("Active", _row("T-002")),
             ("Active", _row("T-099")))
        found = _scan(clean)
        assert _codes(found) == ["map-dangling"]
        assert found[0].line == 7  # heading, blank, heading, blank, 3 rows -> third row

    def test_row_pointing_at_a_real_file_that_is_not_a_ticket_summary(self, clean):
        _map(clean, ("Active", _row("T-001")), ("Active", _row("T-002")),
             ("Active", "- [[page]] — Wiki — Open — Me — 2026-10-06"),
             ("Active", "- [[T-001-plan]] — Plan — Open — Me — 2026-10-06"))
        found = _scan(clean)
        assert _codes(found) == ["map-unknown-ticket", "map-unknown-ticket"]
        assert all(f.level == "error" for f in found)

    def test_ticket_without_a_row_and_ticket_with_two_rows(self, clean):
        _map(clean, ("Active", _row("T-001")), ("Completed", _row("T-001")))
        found = _map_only(_scan(clean))
        assert sorted((f.code, f.level) for f in found) == [
            ("map-duplicate-row", "error"), ("map-missing-row", "error"),
            ("map-section-drift", "error")]  # the Completed copy is also in the wrong section
        assert "T-002" in _of(found, "map-missing-row")[0].message
        assert "T-001" in _of(found, "map-duplicate-row")[0].message

    def test_other_kind_tickets_need_no_row(self):
        board = {"T-001": ("open", "T1")}
        text = "## Active\n- [[T-001-summary]] — T1 — Open — Me — 2026-10-06\n"
        ix = _index("a/T-001-summary.md", "b/INV-1-summary.md")
        assert link_check.map_findings(text, ix, {"T-001", "INV-1"}, board) == []


class TestMapDrift:
    def _drift(self, stage, section, label, title="Title", map_title="Title"):
        board = {"T-001": (stage, title)}
        text = "## %s\n- [[T-001-summary]] — %s — %s — Me — 2020-01-01\n" % (section, map_title, label)
        found = link_check.map_findings(text, _index("a/T-001-summary.md"), {"T-001"}, board)
        return _codes(found)

    def test_consistent_rows_for_every_stage_yield_nothing(self):
        assert self._drift("open", "Active", "Open") == []
        assert self._drift("in-progress", "Active", "In Progress") == []
        assert self._drift("verify", "Active", "Verify") == []
        assert self._drift("blocked", "Blocked", "Blocked") == []
        assert self._drift("done", "Completed", "Complete") == []

    def test_verify_row_reading_open_is_status_drift(self):
        assert self._drift("verify", "Active", "Open") == ["map-status-drift"]

    def test_done_ticket_under_active_is_section_drift(self):
        assert self._drift("done", "Active", "Complete") == ["map-section-drift"]

    def test_title_difference_is_title_drift(self):
        assert self._drift("open", "Active", "Open", title="New", map_title="Old") == ["map-title-drift"]

    def test_status_and_section_can_both_drift(self):
        assert self._drift("done", "Active", "Open") == ["map-section-drift", "map-status-drift"]

    def test_archived_rows_and_unknown_stages_are_skipped(self):
        assert self._drift("open", "Archived", "Whatever", map_title="Other") == []
        assert self._drift("weird-stage", "Active", "Whatever") == []

    def test_message_names_the_row_label_and_the_stage(self):
        board = {"T-001": ("verify", "Title")}
        text = "## Active\n- [[T-001-summary]] — Title — Open — Me — 2020-01-01\n"
        (f,) = link_check.map_findings(text, _index("a/T-001-summary.md"), {"T-001"}, board)
        assert "'Open'" in f.message and "verify" in f.message and f.line == 2

    def test_stage_moves_in_a_real_workspace_show_up_as_drift(self, clean):
        tickets.move(clean, "T-001", "in-progress")
        tickets.move(clean, "T-002", "done")
        found = _map_only(_scan(clean))
        assert sorted((f.code, f.line) for f in found) == [
            ("map-section-drift", 6), ("map-status-drift", 5), ("map-status-drift", 6)]

    def test_owner_and_date_are_not_compared(self, repo):
        _ticket(repo, "T-001")
        _map(repo, ("Active", _row("T-001", owner="Somebody Else", date="1999-01-01")))
        assert _map_only(_scan(repo)) == []


# --- 04: contract: check, scoping, exit codes, output -----------------------

def _plant(repo, code):
    """Plant exactly the fault for `code` on the clean tree (returns nothing)."""
    plan = "artifacts/T-001/T-001-plan.md"
    summary = "artifacts/T-001/T-001-summary.md"
    full = "# P\n\n" + _links("T-001-summary", "T-001-plan")
    if code == "map-missing":
        os.remove(os.path.join(_vault(repo), "artifact-map.md"))
    elif code == "links-missing":
        _put(repo, plan, "# P\n")
    elif code == "links-duplicate":
        _put(repo, plan, full + "\n" + _links("T-001-summary"))
    elif code == "links-malformed":
        _put(repo, plan, "# P\n## Links- [[T-001-summary]]\n")
    elif code == "links-dangling":
        _put(repo, plan, full + "- [[ghost]]\n")
    elif code == "map-dangling":
        _map(repo, ("Active", _row("T-001")), ("Active", _row("T-002")), ("Active", _row("T-099")))
    elif code == "map-unknown-ticket":
        _map(repo, ("Active", _row("T-001")), ("Active", _row("T-002")),
             ("Active", "- [[page]] — Wiki — Open — Me — 2026-10-06"))
    elif code == "map-missing-row":
        _map(repo, ("Active", _row("T-001")))
    elif code == "map-duplicate-row":
        _map(repo, ("Active", _row("T-001")), ("Active", _row("T-001")), ("Active", _row("T-002")))
    elif code == "map-status-drift":
        tickets.move(repo, "T-001", "in-progress")
    elif code == "map-section-drift":
        _map(repo, ("Completed", _row("T-001")), ("Active", _row("T-002")))
    elif code == "map-title-drift":
        _map(repo, ("Active", _row("T-001", title="Old name")), ("Active", _row("T-002")))
    elif code == "one-way-link":
        _put(repo, plan, "# P\n\n" + _links("T-001-plan"))
    elif code == "links-incomplete":
        _put(repo, "artifacts/T-001/T-001-notes.md",
             "# N\n\n" + _links("T-001-summary", "T-001-plan"))
    elif code == "links-not-last":
        _put(repo, plan, full + "\n## Appendix\n")
    elif code == "body-dangling":
        _put(repo, plan, "# P\n[[ghost]]\n\n" + _links("T-001-summary", "T-001-plan"))
    elif code == "link-form":
        _put(repo, plan, "# P\n\n" + _links("T-001-summary.md", "T-001-plan"))
    elif code == "ambiguous-basename":
        _put(repo, "wiki/page.md", "# dup of the wiki page\n")
        _put(repo, "docs/page.md", "# second\n")
    elif code == "misplaced-artifact":
        _put(repo, "artifacts/T-001/T-002-notes.md", "# n\n\n" + _links("T-001-summary"))
    elif code == "map-row-format":
        _map(repo, ("Active", _row("T-001") + " — extra"), ("Active", "- [[T-002-summary]] — T"))
    else:
        raise AssertionError("no fixture for %s" % code)


class TestCodes:
    def test_the_code_constant_is_the_twenty_codes_of_fr9(self):
        assert len(link_check.ALL_CODES) == 20
        assert len(set(link_check.ALL_CODES)) == 20
        assert not set(link_check.ERROR_CODES) & set(link_check.WARN_CODES)
        assert len(link_check.ERROR_CODES) == 12 and len(link_check.WARN_CODES) == 8
        assert set(link_check.ALL_CODES) == {
            "map-missing", "links-missing", "links-duplicate", "links-malformed",
            "links-dangling", "map-dangling", "map-unknown-ticket", "map-missing-row",
            "map-duplicate-row", "map-status-drift", "map-section-drift", "map-title-drift",
            "one-way-link", "links-incomplete", "links-not-last", "body-dangling",
            "link-form", "ambiguous-basename", "misplaced-artifact", "map-row-format"}

    def test_the_clean_fixture_fires_none_of_them(self, clean):
        assert link_check.check(clean) == ([], {"tickets": 2, "files": 9, "errors": 0, "warnings": 0})

    @pytest.mark.parametrize("code", link_check.ALL_CODES)
    def test_every_code_has_a_firing_fixture_with_its_level(self, clean, code):
        _plant(clean, code)
        findings, _summary = link_check.check(clean)
        got = _of(findings, code)
        assert got, "%s did not fire; got %s" % (code, _codes(findings))
        expected = "error" if code in link_check.ERROR_CODES else "warn"
        assert {f.level for f in got} == {expected}


class TestCheck:
    def test_summary_counts_equal_the_findings(self, clean):
        _plant(clean, "links-dangling")
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        findings, summary = link_check.check(clean)
        assert summary["errors"] == len([f for f in findings if f.level == "error"]) >= 1
        assert summary["warnings"] == len([f for f in findings if f.level == "warn"]) >= 1
        assert (summary["tickets"], summary["files"]) == (2, 9)

    def test_missing_vault_directory_could_not_run(self, repo):
        import shutil
        shutil.rmtree(_vault(repo))
        with pytest.raises(link_check.LinkCheckError, match="vault"):
            link_check.check(repo)

    def test_unknown_ticket_could_not_run(self, clean):
        with pytest.raises(link_check.LinkCheckError, match="T-999"):
            link_check.check(clean, ticket="T-999")

    def test_findings_are_ordered_by_level_path_line_code(self, clean):
        _plant(clean, "links-dangling")
        _plant(clean, "map-status-drift")
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        findings, _ = link_check.check(clean)
        keys = [f.sort_key() for f in findings]
        assert keys == sorted(keys)
        levels = [f.level for f in findings]
        assert levels == sorted(levels, key=lambda lv: lv != "error")
        assert levels[0] == "error"

    def test_two_runs_are_identical_in_text_and_json(self, clean):
        import json
        _plant(clean, "links-dangling")
        _plant(clean, "one-way-link")
        runs = []
        for _ in range(2):
            findings, summary = link_check.check(clean)
            runs.append((link_check.format_report(findings, summary),
                         json.dumps(link_check.as_json(findings, summary), indent=2)))
        assert runs[0] == runs[1]


class TestExitCodes:
    def test_clean_warnings_only_strict_and_errors(self, clean):
        _f, summary = link_check.check(clean)
        assert link_check.exit_code(summary) == 0
        assert link_check.exit_code(summary, strict=True) == 0
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        _f, summary = link_check.check(clean)
        assert (summary["errors"], summary["warnings"]) == (0, 1)
        assert link_check.exit_code(summary) == 0
        assert link_check.exit_code(summary, strict=True) == 1
        _plant(clean, "links-dangling")
        _f, summary = link_check.check(clean)
        assert link_check.exit_code(summary) == 1


class TestScope:
    def _two_faulty(self, repo):
        _ticket(repo, "T-001", bodies={"plan": "# P\n[[prose-ghost]]\n\n" + _links("T-001-summary", "ghost-one")})
        _ticket(repo, "T-002", bodies={"plan": "# P\n\n" + _links("T-002-summary", "ghost-two")})
        _map(repo, ("Active", _row("T-001", label="Verify")), ("Active", _row("T-002", label="Verify")))
        _put(repo, "wiki/x.md", "# x\n[[wiki-ghost]]\n")

    def test_only_that_tickets_files_and_map_row(self, repo):
        self._two_faulty(repo)
        findings, summary = link_check.check(repo, ticket="T-001")
        assert findings
        assert all(f.path.startswith("artifacts/T-001/") or f.path == "artifact-map.md"
                   for f in findings)
        assert "ghost-two" not in " ".join(f.message for f in findings)
        assert [f.code for f in findings if f.path == "artifact-map.md"] == ["map-status-drift"]
        assert "T-001" in _of(findings, "map-status-drift")[0].message
        assert (summary["tickets"], summary["files"]) == (1, 2)
        assert summary["errors"] == 2 and summary["warnings"] == 1  # dangling, drift, prose

    def test_the_full_run_still_sees_both(self, repo):
        self._two_faulty(repo)
        findings, summary = link_check.check(repo)
        assert summary["tickets"] == 2
        msgs = " ".join(f.message for f in findings)
        assert "ghost-one" in msgs and "ghost-two" in msgs and "wiki-ghost" in msgs

    def test_ambiguous_basename_follows_a_file_in_the_ticket_directory(self, repo):
        _ticket(repo, "T-001")
        _ticket(repo, "T-002")
        _map(repo, ("Active", _row("T-001")), ("Active", _row("T-002")))
        _put(repo, "wiki/T-001-plan.md", "# twin of a ticket artifact\n")
        for ticket, want in (("T-001", 1), ("T-002", 0)):
            found, _ = link_check.check(repo, ticket=ticket)
            assert len(_of(found, "ambiguous-basename")) == want

    def test_scoped_run_for_a_clean_ticket_is_empty(self, clean):
        _plant(clean, "links-missing")  # T-001 only
        findings, summary = link_check.check(clean, ticket="T-002")
        assert findings == [] and summary["tickets"] == 1


def _warn(n, code="one-way-link"):
    return [link_check.Finding(code, "artifacts/T-1/T-1-f%03d.md" % i, 3, "msg %d" % i)
            for i in range(n)]


class TestFormat:
    SUMMARY = {"tickets": 3, "files": 9, "errors": 2, "warnings": 25}

    def test_errors_first_ascii_and_the_last_line_is_the_summary(self):
        err = [link_check.Finding("links-dangling", "a/é.md", 7, "title — arrow → end")]
        out = link_check.format_report(_warn(3) + err, {"tickets": 1, "files": 2,
                                                       "errors": 1, "warnings": 3})
        out.encode("ascii")
        lines = out.split("\n")
        assert lines[0].startswith("ERROR links-dangling")
        assert "a/\\xe9.md:7" in lines[0]
        assert "\\u2014" in out and "\\u2192" in out
        assert out.index("ERROR") < out.index("WARN")
        assert lines[-1] == "1 tickets, 2 files | 1 error(s), 3 warning(s)"

    def test_warnings_are_capped_at_20_per_code_with_a_more_line(self):
        findings = _warn(25) + _warn(2, "links-incomplete")
        out = link_check.format_report(findings, self.SUMMARY)
        assert out.count("WARN  one-way-link ") == 21  # 20 findings + the "+5 more" line
        assert "+5 more (use --all)" in out
        assert out.count("links-incomplete") == 2  # under the cap: no more line
        assert "f024" not in out and "f019" in out

    def test_all_lifts_the_cap(self):
        out = link_check.format_report(_warn(25), self.SUMMARY, show_all=True)
        assert "f024" in out and "more (use --all)" not in out

    def test_errors_are_never_capped(self):
        errs = _warn(30, "links-dangling")
        out = link_check.format_report(errs, {"tickets": 1, "files": 1, "errors": 30, "warnings": 0})
        assert out.count("ERROR links-dangling") == 30 and "more (use --all)" not in out

    def test_a_real_run_escapes_non_ascii_titles(self, repo):
        _ticket(repo, "T-001", title="Fast — and honest → done")
        _map(repo, ("Active", _row("T-001", title="Other")))
        findings, summary = link_check.check(repo)
        out = link_check.format_report(findings, summary)
        out.encode("ascii")
        assert "map-title-drift" in out and "\\u2014" in out


class TestJson:
    def test_shape_counts_and_every_field(self, clean):
        import json
        _plant(clean, "links-dangling")
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        findings, summary = link_check.check(clean)
        doc = json.loads(json.dumps(link_check.as_json(findings, summary), indent=2))
        assert set(doc) == {"summary", "findings"}
        assert doc["summary"] == summary
        assert doc["summary"]["errors"] + doc["summary"]["warnings"] == len(doc["findings"])
        for row in doc["findings"]:
            assert set(row) == {"level", "code", "path", "line", "message"}
            assert isinstance(row["line"], int) and "\\" not in row["path"]

    def test_json_is_uncapped(self):
        doc = link_check.as_json(_warn(30), {"tickets": 1, "files": 1, "errors": 0, "warnings": 30})
        assert len(doc["findings"]) == 30


# --- 05: hardening for the non-functional requirements -----------------------

MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "server", "link_check.py")
REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _module_tree():
    import ast
    with open(MODULE_PATH, encoding="utf-8") as fh:
        return ast.parse(fh.read())


class TestStdlibOnly:
    def test_imports_are_stdlib_or_sibling_server_modules(self):
        import ast
        import sys
        stdlib = sys.stdlib_module_names
        bad = []
        for node in ast.walk(_module_tree()):
            if isinstance(node, ast.Import):
                bad += [a.name for a in node.names if a.name.split(".")[0] not in stdlib]
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and (node.module or "").split(".")[0] not in stdlib | {"server"}:
                    bad.append(node.module)
        assert bad == []


class TestReadonlyCode:
    FORBIDDEN_ATTRS = {"remove", "unlink", "rename", "renames", "makedirs", "mkdir",
                       "rmdir", "removedirs", "rmtree", "move", "copy", "copyfile", "copy2",
                       "write_text", "write_bytes", "truncate", "utime", "chmod", "symlink",
                       "link", "touch", "mkstemp", "mkdtemp", "NamedTemporaryFile"}

    def test_no_write_mode_open_and_no_mutating_calls(self):
        import ast
        problems = []
        for node in ast.walk(_module_tree()):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                if any(n.split(".")[0] in ("shutil", "tempfile") for n in names):
                    problems.append("imports %s at line %d" % (names, node.lineno))
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            os_replace = (name == "replace" and isinstance(func, ast.Attribute)
                          and getattr(func.value, "id", "") == "os")  # not str.replace
            if name in self.FORBIDDEN_ATTRS or os_replace:
                problems.append("%s() at line %d" % (name, node.lineno))
            if name == "open":
                mode = node.args[1] if len(node.args) > 1 else next(
                    (k.value for k in node.keywords if k.arg == "mode"), None)
                if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)
                        and not set(mode.value) & set("wax+")):
                    problems.append("open() with a non-read mode at line %d" % node.lineno)
        assert problems == []


def _snapshot(root):
    """Every path under `root` with its size, mtime and bytes."""
    snap = {}
    for here, dirs, files in os.walk(root):
        for name in dirs + files:
            full = os.path.join(here, name)
            st = os.stat(full)
            body = open(full, "rb").read() if os.path.isfile(full) else None
            snap[os.path.relpath(full, root)] = (st.st_size, st.st_mtime_ns, body)
    return snap


class TestReadonlyRun:
    def test_the_tree_is_identical_before_and_after_a_run_with_findings(self, clean):
        _plant(clean, "links-dangling")
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        before = _snapshot(clean)
        findings, summary = link_check.check(clean)
        link_check.check(clean, ticket="T-001")
        link_check.format_report(findings, summary)
        assert summary["errors"] and summary["warnings"]
        assert _snapshot(clean) == before


class TestPerf:
    def test_synthetic_2000_file_vault_scans_in_under_10_seconds(self, repo):
        import time
        _ticket(repo, "T-001")
        _map(repo, ("Active", _row("T-001")))
        for group in range(21):
            os.makedirs(os.path.join(_vault(repo), "wiki", "g%02d" % group))
        for i in range(2100):  # direct writes: the fixture, not the checker, is slow
            path = os.path.join(_vault(repo), "wiki", "g%02d" % (i // 100), "page-%04d.md" % i)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("# p\n[[page-%04d]] [[T-001-summary]] [[ghost-%d]]\n\n## Links\n- [[page-%04d]]\n"
                         % ((i + 1) % 2100, i, (i + 7) % 2100))
        # Brand-new files cost the OS (virus scanner) on their FIRST read, about
        # 15 ms each on this Windows machine: 18 s of the 18.3 s a cold run took,
        # against 0.3 s of checker. That is the fixture's cost, not the rule's, so
        # read every file once before timing.
        for here, _dirs, names in os.walk(_vault(repo)):
            for name in names:
                with open(os.path.join(here, name), "rb") as fh:
                    fh.read()
        started = time.perf_counter()
        findings, summary = link_check.check(repo)
        elapsed = time.perf_counter() - started
        assert summary["files"] >= 2000
        assert findings
        assert elapsed < 10, "2,000 files took %.1f s" % elapsed

    def test_real_repo_smoke_run_under_5_seconds(self):
        import time
        if not os.path.isdir(os.path.join(REAL_ROOT, "knowledge-center")):
            pytest.skip("no knowledge-center in this checkout")
        started = time.perf_counter()
        findings, summary = link_check.check(REAL_ROOT)
        elapsed = time.perf_counter() - started
        assert summary["files"] > 0 and summary["errors"] + summary["warnings"] == len(findings)
        assert elapsed < 5, "the real vault took %.1f s" % elapsed


class TestEndings:
    BASE = ("[[ghost-first]]\n# P\ntext [[ghost-prose]]\n\n## Links\n"
            "- [[T-001-summary]] · [[ghost-block]]\n")

    def _run(self, repo, raw):
        path = os.path.join(_vault(repo), "artifacts", "T-001", "T-001-plan.md")
        with open(path, "wb") as fh:
            fh.write(raw)
        return [(f.code, f.path, f.line) for f in link_check.check(repo)[0]
                if f.path.endswith("plan.md")]

    def test_every_ending_and_a_bom_give_the_lf_findings(self, repo):
        _ticket(repo, "T-001")
        _map(repo, ("Active", _row("T-001")))
        lf = self.BASE.encode("utf-8")
        want = self._run(repo, lf)
        assert ("body-dangling", "artifacts/T-001/T-001-plan.md", 1) in want  # first line, not hidden
        assert ("links-dangling", "artifacts/T-001/T-001-plan.md", 6) in want
        lines = self.BASE.split("\n")
        mixed = "\r\n".join(lines[:3]) + "\n" + "\r".join(lines[3:5]) + "\r" + "\n".join(lines[5:])
        variants = {
            "crlf": self.BASE.replace("\n", "\r\n").encode("utf-8"),
            "lone-cr": self.BASE.replace("\n", "\r").encode("utf-8"),
            "mixed": mixed.encode("utf-8"),
            "bom-lf": b"\xef\xbb\xbf" + lf,
            "bom-crlf": b"\xef\xbb\xbf" + self.BASE.replace("\n", "\r\n").encode("utf-8"),
        }
        for label, raw in variants.items():
            assert self._run(repo, raw) == want, label


def _make_dir_link(kind, link, target):
    """True when a `kind` ("symlink" or "junction") directory link was made."""
    if kind == "symlink":
        try:
            os.symlink(target, link, target_is_directory=True)
            return True
        except (OSError, NotImplementedError):
            return False
    if os.name != "nt":
        return False
    import subprocess
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                          capture_output=True, text=True)
    return proc.returncode == 0 and os.path.isdir(link)


class TestSymlinkNotFollowed:
    # A junction is not a symlink: `DirEntry.is_dir(follow_symlinks=False)` is
    # still True for it, so only the reparse-point test keeps the walker out.
    @pytest.mark.parametrize("kind", ["symlink", "junction"])
    def test_a_link_to_a_directory_outside_the_vault_is_skipped(self, clean, tmp_path, kind):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret-note.md").write_text("[[outside-ghost]]\n", encoding="utf-8")
        link = os.path.join(_vault(clean), "wiki", "portal")
        if not _make_dir_link(kind, link, str(outside)):
            pytest.skip("this OS or user cannot create a %s here" % kind)
        _put(clean, "wiki/uses.md", "# u\n[[secret-note]]\n")
        found = _scan(clean)
        assert not [f for f in found if "portal" in f.path or "outside-ghost" in f.message]
        # not indexed either: the link to its name dangles instead of resolving through the portal
        assert [f.code for f in found] == ["body-dangling"]
        assert "secret-note" in found[0].message
        assert not [r for r, _p in link_check.walk_md(_vault(clean)) if "portal" in r]


class TestUtf8:
    def test_invalid_utf8_does_not_abort_check_and_still_reports_the_summary(self, clean):
        with open(os.path.join(_vault(clean), "wiki", "bad.md"), "wb") as fh:
            fh.write(b"\xff\xfe\x00 [[ghost]] \xc3(\n")
        findings, summary = link_check.check(clean)
        assert [f.code for f in findings] == ["body-dangling"]
        assert summary["warnings"] == 1 and summary["errors"] == 0


class TestContained:
    def test_a_parent_path_target_never_opens_a_file_outside_the_vault(self, clean, monkeypatch):
        import builtins
        outside = os.path.join(clean, "CLAUDE.md")  # the trip-wire a `..` link would reach
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write("# claude\n")
        _put(clean, "wiki/escape.md",
             "# e\n[[../../CLAUDE.md]] [[../CLAUDE]] [[/etc/passwd]] [[C:/Windows/win.ini]] [[CLAUDE.md]]\n")
        real_open, opened = builtins.open, []

        def spy(file, *args, **kwargs):
            opened.append(os.path.normcase(os.path.abspath(os.fspath(file))))
            return real_open(file, *args, **kwargs)
        monkeypatch.setattr(builtins, "open", spy)
        findings, _summary = link_check.check(clean)
        monkeypatch.setattr(builtins, "open", real_open)
        assert os.path.normcase(os.path.abspath(outside)) not in opened
        assert not [p for p in opened if p.endswith("passwd") or p.endswith("win.ini")]
        assert len([f for f in findings if f.code == "body-dangling"]) == 5


class TestCouldNotRun:
    def test_a_missing_console_configuration_is_exit_2_not_a_traceback(self, repo):
        os.remove(os.path.join(repo, "console", "config", "console.toml"))
        from server import boards
        boards._console_cache.clear()
        with pytest.raises(link_check.LinkCheckError, match="console configuration"):
            link_check.check(repo)


# --- 06: verb, CLI, schedule -----------------------------------------------

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KANBAN = os.path.join(_ROOT, "console", "kanban.py")


@pytest.fixture
def vrepo(clean):
    """The clean tree with the SHIPPED verb registry copied in, so `verbs.run`
    dispatches the real `link-check` row against a throwaway vault."""
    import shutil
    from server import verbs
    shutil.copy(os.path.join(_ROOT, "console", "config", "verbs.toml"),
                os.path.join(clean, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    yield clean
    verbs._cache.clear()


class TestVerb:
    def test_shipped_row_is_read_only_and_resolves(self):
        from server import verbs
        from server.verb_handlers import link_check_verb
        verb = verbs.registry(_ROOT, force=True)["link-check"]
        assert verb.needs_confirm is False and verb.needs_ticket is False
        assert verb.resolve() is link_check_verb

    def test_clean_tree_is_ok_with_the_three_keys(self, vrepo):
        from server import verbs
        out = verbs.run(vrepo, "link-check")
        assert set(out) == {"ok", "summary", "findings"}
        assert out["ok"] is True and out["findings"] == []
        assert (out["summary"]["tickets"], out["summary"]["errors"]) == (2, 0)

    def test_errors_are_a_result_not_an_exception(self, vrepo):
        from server import verbs
        _plant(vrepo, "links-dangling")
        out = verbs.run(vrepo, "link-check")
        assert out["ok"] is False and out["summary"]["errors"] >= 1
        assert [f for f in out["findings"] if f["code"] == "links-dangling"]
        assert {"level", "code", "path", "line", "message"} <= set(out["findings"][0])

    def test_findings_are_not_capped_in_the_result(self, vrepo):
        from server import verbs
        _put(vrepo, "wiki/many.md", "# m\n" + "".join("[[ghost%d]]\n" % i for i in range(30)))
        out = verbs.run(vrepo, "link-check")
        assert len([f for f in out["findings"] if f["code"] == "body-dangling"]) == 30

    def test_strict_flips_ok_on_a_warnings_only_tree(self, vrepo):
        from server import verbs
        _plant(vrepo, "body-dangling")
        loose = verbs.run(vrepo, "link-check")
        assert (loose["summary"]["errors"], loose["ok"]) == (0, True) and loose["summary"]["warnings"]
        for flag in ("true", "1", "yes", "on"):
            assert verbs.run(vrepo, "link-check", args={"strict": flag})["ok"] is False
        assert verbs.run(vrepo, "link-check", args={"strict": "false"})["ok"] is True

    def test_ticket_scopes_and_an_unknown_ticket_is_refused_by_the_gate(self, vrepo):
        from server import verbs
        _plant(vrepo, "links-missing")  # T-001 only
        assert verbs.run(vrepo, "link-check", ticket="T-001")["summary"]["errors"] == 1
        assert verbs.run(vrepo, "link-check", ticket="T-002")["findings"] == []
        with pytest.raises(verbs.VerbError, match="no such ticket"):
            verbs.run(vrepo, "link-check", ticket="T-999")

    def test_could_not_run_raises_so_a_scheduled_job_ends_in_error(self, vrepo):
        import shutil
        from server import verbs
        from server.verb_handlers import link_check_verb
        with pytest.raises(link_check.LinkCheckError, match="no such ticket"):
            link_check_verb(vrepo, ticket="T-999")
        shutil.rmtree(_vault(vrepo))
        with pytest.raises(link_check.LinkCheckError, match="vault"):
            verbs.run(vrepo, "link-check")

    def test_the_verb_writes_nothing(self, vrepo):
        from server import verbs
        _plant(vrepo, "links-dangling")
        before = _snapshot(vrepo)
        verbs.run(vrepo, "link-check")
        assert _snapshot(vrepo) == before


class TestToolSurfaces:
    def test_mcp_and_agent_tools_list_the_verb(self):
        from server import agent_tools, mcp
        assert "link-check" in {t["name"] for t in mcp.tool_list(_ROOT)}
        names = {t["function"]["name"] for t in agent_tools.tool_definitions(_ROOT)}
        assert "console_link_check" in names


class TestSchedule:
    def test_the_nightly_row_is_parked_and_points_at_a_real_verb(self):
        from server import schedules, verbs
        schedules._cache.clear()
        row = schedules.registry(_ROOT, force=True)["link-check-nightly"]
        assert (row.verb, row.expr, row.enabled, row.confirm) == ("link-check", "30 2 * * *", False, False)
        assert row.verb in verbs.registry(_ROOT, force=True)


def _ns(**kw):
    from types import SimpleNamespace
    base = dict(json=False, strict=False, all=False, ticket=None)
    base.update(kw)
    return SimpleNamespace(**base)


class TestCli:
    def test_the_parser_takes_all_four_flags(self):
        import kanban
        args = kanban.build_parser().parse_args(
            ["vault", "links", "--json", "--strict", "--all", "--ticket", "T-001"])
        assert (args.json, args.strict, args.all, args.ticket) == (True, True, True, "T-001")
        assert args.func is kanban.cmd_vault_links
        bare = kanban.build_parser().parse_args(["vault", "links"])
        assert (bare.json, bare.strict, bare.all, bare.ticket) == (False, False, False, None)

    def test_clean_tree_prints_the_summary_and_returns(self, clean, capsys):
        import kanban
        kanban.cmd_vault_links(_ns(), clean)
        assert capsys.readouterr().out.strip().endswith("2 tickets, 9 files | 0 error(s), 0 warning(s)")

    def test_errors_exit_1_warnings_exit_1_only_when_strict(self, clean, capsys):
        import kanban
        _put(clean, "wiki/page.md", "# page\n[[ghost]]\n")
        kanban.cmd_vault_links(_ns(), clean)
        assert "WARN  body-dangling" in capsys.readouterr().out
        with pytest.raises(SystemExit) as ei:
            kanban.cmd_vault_links(_ns(strict=True), clean)
        assert ei.value.code == 1
        capsys.readouterr()
        _plant(clean, "links-dangling")
        with pytest.raises(SystemExit) as ei:
            kanban.cmd_vault_links(_ns(), clean)
        assert ei.value.code == 1
        out = capsys.readouterr().out
        assert out.index("ERROR links-dangling") < out.index("WARN  body-dangling")

    def test_json_has_summary_and_findings_with_a_line(self, clean, capsys):
        import json
        import kanban
        _plant(clean, "links-dangling")
        with pytest.raises(SystemExit):
            kanban.cmd_vault_links(_ns(json=True), clean)
        payload = json.loads(capsys.readouterr().out)
        assert set(payload) == {"summary", "findings"}
        assert all(isinstance(f["line"], int) for f in payload["findings"])

    def test_the_text_caps_warnings_and_all_lifts_the_cap(self, clean, capsys):
        import kanban
        _put(clean, "wiki/many.md", "# m\n" + "".join("[[ghost%d]]\n" % i for i in range(25)))
        kanban.cmd_vault_links(_ns(), clean)
        assert "+5 more (use --all)" in capsys.readouterr().out
        kanban.cmd_vault_links(_ns(all=True), clean)
        out = capsys.readouterr().out
        assert "more (use --all)" not in out and out.count("body-dangling") == 25

    def test_an_unknown_ticket_exits_2_on_stderr(self, clean, capsys):
        import kanban
        with pytest.raises(SystemExit) as ei:
            kanban.cmd_vault_links(_ns(ticket="T-999"), clean)
        assert ei.value.code == 2
        captured = capsys.readouterr()
        assert "T-999" in captured.err and captured.out == ""

    def test_a_scoped_run_reports_one_ticket(self, clean, capsys):
        import kanban
        kanban.cmd_vault_links(_ns(ticket="T-001"), clean)
        assert "1 tickets, 4 files" in capsys.readouterr().out

    def test_subprocess_under_cp1252_propagates_the_exit_code_in_ascii(self, clean):
        import subprocess
        import sys
        _put(clean, "artifacts/T-001/T-001-plan.md",
             "# P\n\n" + _links("T-001-summary", "T-001-plan", "ghöst → x"))
        env = dict(os.environ)
        env.update({"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "CONSOLE_REPO_ROOT": clean})

        def run(*argv):
            return subprocess.run([sys.executable, _KANBAN, "vault", "links", *argv],
                                  cwd=clean, env=env, capture_output=True, timeout=120)
        proc = run()
        assert proc.returncode == 1, proc.stderr.decode("utf-8", "replace")
        text = proc.stdout.decode("ascii")  # raises if anything non-ASCII leaked
        assert "ERROR links-dangling" in text and "\\xf6" in text and "\\u2192" in text
        assert run("--ticket", "T-999").returncode == 2
        assert run("--ticket", "T-002").returncode == 0
