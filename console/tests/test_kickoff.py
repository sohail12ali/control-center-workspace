"""C6: the `kickoff` verb — mirrors the `kickoff` skill's 3 steps (BR-5).

No real PowerShell process in most of these tests: `_render_templates`'s
`runner` seam stands in for `subprocess.run`, matching the fake-opener idiom
used elsewhere in this ticket. The one test that DOES shell out for real
(`TestRenderedTemplateEncoding`) is the regression guard for the
`New-FromTemplate.ps1` double-encoding fix and is honestly skipped where
Windows PowerShell 5.1 doesn't apply.
"""

import os
import shutil
import subprocess

import pytest

from server import kickoff, tickets


def _make_template_dir(repo, names=("summary", "plan")):
    d = os.path.join(repo, "knowledge-center", "artifacts", "_template")
    os.makedirs(d, exist_ok=True)
    for name in names:
        with open(os.path.join(d, "%s.md" % name), "w", encoding="utf-8") as fh:
            fh.write("---\nticket: \"{ID}\"\n---\n\n# {ID}: {TITLE}\n")
    return d


def _make_artifact_map(repo, body="# Artifact Map\n\n## Active\n\n## Blocked\n\n"
                       "## Completed\n\n## Archived\n\n---\n"):
    path = os.path.join(repo, "knowledge-center", "artifact-map.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


#: The real script this workspace ships — copied into the throwaway `repo`
#: fixture for the one test that needs to run it for real (below), rather
#: than exercising the real checkout's own `.claude/` tree.
REAL_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".claude", "skills", "template", "scripts", "New-FromTemplate.ps1")


def _copy_real_render_script(repo):
    dest = os.path.join(repo, kickoff.RENDER_SCRIPT_REL)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(REAL_SCRIPT, dest)
    # The script also shells out to _shared/scripts/Get-RepoRoot.ps1.
    shared_src = os.path.join(os.path.dirname(REAL_SCRIPT), "..", "..",
                              "_shared", "scripts", "Get-RepoRoot.ps1")
    shared_dest = os.path.join(repo, ".claude", "skills", "_shared", "scripts",
                              "Get-RepoRoot.ps1")
    os.makedirs(os.path.dirname(shared_dest), exist_ok=True)
    shutil.copyfile(shared_src, shared_dest)


def _fake_ps_runner(recorded=None):
    """Stands in for `subprocess.run` + a working `New-FromTemplate.ps1`:
    writes a minimal rendered file at `-OutputPath` and reports success."""
    def run(argv, **kw):
        out_path = argv[argv.index("-OutputPath") + 1]
        ticket_id = argv[argv.index("-Ticket") + 1]
        title = argv[argv.index("-Title") + 1]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("---\nticket: \"%s\"\n---\n\n# %s: %s\n" % (ticket_id, ticket_id, title))
        if recorded is not None:
            recorded.append(argv)

        class Result:
            returncode = 0
            stdout = "Created: %s" % out_path
            stderr = ""
        return Result()
    return run


class TestNextTicketId:
    def test_no_prior_tickets_starts_at_001(self, repo):
        assert kickoff.next_ticket_id(repo) == "T-001"

    def test_continues_from_the_highest_existing_id(self, repo):
        for n in (1, 2, 4):
            os.makedirs(os.path.join(repo, "knowledge-center", "artifacts",
                                     "T-%03d" % n), exist_ok=True)
        assert kickoff.next_ticket_id(repo) == "T-005"

    def test_a_different_prefix_is_tracked_independently(self, repo):
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "T-001"),
                   exist_ok=True)
        assert kickoff.next_ticket_id(repo, prefix="BUG-") == "BUG-001"

    def test_non_matching_directories_are_ignored(self, repo):
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "_template"),
                   exist_ok=True)
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"),
                   exist_ok=True)
        assert kickoff.next_ticket_id(repo) == "T-001"


class TestCreateTicket:
    def test_produces_ticket_toml_and_rendered_templates(self, repo):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        result = kickoff.create_ticket(repo, "A new thing",
                                       runner=_fake_ps_runner())
        assert result["id"] == "T-001"
        assert tickets.load(repo, "T-001") is not None
        for path in result["rendered"]:
            assert os.path.isfile(path)
        assert len(result["rendered"]) == 2  # summary.md + plan.md

    def test_an_empty_title_is_refused(self, repo):
        with pytest.raises(ValueError):
            kickoff.create_ticket(repo, "   ", runner=_fake_ps_runner())

    def test_powershell_unavailable_raises_a_distinguishable_error(
            self, repo, monkeypatch):
        _make_template_dir(repo)
        monkeypatch.setattr(kickoff, "_powershell_exe", lambda: None)
        with pytest.raises(kickoff.PowerShellUnavailable):
            kickoff.create_ticket(repo, "A new thing")
        # The ticket.toml step still happened — same partial state a human
        # running the skill by hand would be left in if step 2 failed.
        assert tickets.load(repo, "T-001") is not None

    def test_a_render_failure_is_a_plain_runtime_error(self, repo):
        _make_template_dir(repo)

        def failing_runner(argv, **kw):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "Template not found"
            return Result()

        with pytest.raises(RuntimeError, match="Template not found"):
            kickoff.create_ticket(repo, "A new thing", runner=failing_runner)


class TestArtifactMapInsertion:
    """(task 2-6-6) Insertion is heading-relative — never "after the last
    ticket-shaped row" — which is exactly the bug this guards: a map whose
    `## Completed` section is non-empty and whose `## Active` section is
    EMPTY must still land the new row under `## Active`."""

    def test_inserts_directly_under_active_when_active_is_empty(self, repo):
        fixture = (
            "# Artifact Map\n\n"
            "## Active\n\n"
            "## Blocked\n\n"
            "## Completed\n\n"
            "- [[T-001-summary]] — Old ticket — Complete — Someone — 2026-01-01\n\n"
            "## Archived\n\n---\n"
        )
        row = "- [[T-002-summary]] — New ticket — Open — Someone — 2026-09-06"
        out = kickoff._insert_under_active(fixture, row)

        lines = out.splitlines()
        active_idx = lines.index("## Active")
        completed_idx = lines.index("## Completed")
        active_span = lines[active_idx:completed_idx]
        assert row in active_span, (
            "the new row must land under ## Active, not fall through to "
            "wherever the last ticket-shaped row happened to be")
        # And it must NOT have landed under Completed.
        completed_span = lines[completed_idx:lines.index("## Archived")]
        assert row not in completed_span

    def test_inserts_after_existing_active_rows(self, repo):
        fixture = ("## Active\n\n- [[T-001-summary]] — First — Open — A — 2026-01-01\n\n"
                   "## Blocked\n\n## Completed\n\n## Archived\n\n---\n")
        row = "- [[T-002-summary]] — Second — Open — B — 2026-09-06"
        out = kickoff._insert_under_active(fixture, row)
        active_body = out.splitlines()[
            out.splitlines().index("## Active") + 1:
            out.splitlines().index("## Blocked")]
        assert [l for l in active_body if l.startswith("-")] == [
            "- [[T-001-summary]] — First — Open — A — 2026-01-01", row]

    def test_missing_active_heading_is_refused(self):
        with pytest.raises(ValueError):
            kickoff._insert_under_active("# Map\n\n## Blocked\n", "- row")

    def test_end_to_end_via_create_ticket(self, repo):
        _make_template_dir(repo)
        map_path = os.path.join(repo, "knowledge-center", "artifact-map.md")
        with open(map_path, "w", encoding="utf-8") as fh:
            fh.write("# Artifact Map\n\n## Active\n\n## Blocked\n\n"
                     "## Completed\n\n- [[T-999-summary]] — Old — Complete — X — 2026-01-01\n\n"
                     "## Archived\n\n---\n")
        kickoff.create_ticket(repo, "A brand new thing", runner=_fake_ps_runner())
        with open(map_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        lines = text.splitlines()
        active_body = lines[lines.index("## Active") + 1:lines.index("## Blocked")]
        assert any("T-001-summary" in l for l in active_body)


class TestRenderedTemplateEncoding:
    """(task 2-6-7) Regression guard for the `New-FromTemplate.ps1`
    double-encoding fix: ANSI `Get-Content -Raw` + BOM `Set-Content -Encoding
    UTF8` under Windows PowerShell 5.1 was producing BOM'd, mangled-dash
    output. Windows-only — an honest skip elsewhere, since PS 5.1's
    ANSI-vs-UTF8 default doesn't apply on macOS/Linux."""

    MISENCODED = ("Â·", "â€”", "â€™")  # Â· â€" â€™

    def test_a_real_rendered_ticket_is_clean_utf8(self, repo):
        if os.name != "nt":
            pytest.skip("Windows PowerShell 5.1 ANSI-encoding regression — N/A off Windows")
        exe = shutil.which("powershell") or shutil.which("powershell.exe")
        if not exe:
            pytest.skip("PowerShell not on PATH in this environment")

        template_dir = _make_template_dir(repo, names=("summary",))
        _make_artifact_map(repo)
        _copy_real_render_script(repo)
        # Use a template body with the real punctuation that was mis-encoded.
        with open(os.path.join(template_dir, "summary.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nticket: \"{ID}\"\n---\n\n"
                     "# {ID}: {TITLE}\n\nAn em dash — a middot · a curly quote's mark\n")

        result = kickoff.create_ticket(repo, "Encoding check")
        rendered = result["rendered"]
        assert rendered, "at least one file must have been rendered"
        for path in rendered:
            with open(path, "rb") as fh:
                raw = fh.read()
            assert not raw.startswith(b"\xef\xbb\xbf"), (
                "%s starts with a UTF-8 BOM" % path)
            assert raw.startswith(b"---"), path
            text = raw.decode("utf-8")  # must not raise
            for bad in self.MISENCODED:
                assert bad not in text, (
                    "%s contains the mis-encoded sequence %r" % (path, bad))
