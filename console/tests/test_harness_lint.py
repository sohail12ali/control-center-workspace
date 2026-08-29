"""Harness lint.

A linter that reports nothing is indistinguishable from a linter that cannot
report anything, so every check here is proved to FIRE on a planted fault and
to stay quiet on a clean tree. The clean-tree case is the one that would
otherwise rot silently.
"""

import os

import pytest

from server import harness_lint

SKILL = """\
---
name: %s
description: %s
---

# /%s
"""

AGENT = """\
---
name: %s
description: Does a thing.
tools: Read, Grep
---

# Role
"""


def _skill(repo, skill_id, name=None, description="Does a thing.", body=""):
    path = os.path.join(repo, ".claude", "skills", skill_id)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(SKILL % (name if name is not None else skill_id, description, skill_id))
        fh.write(body)
    return path


def _agent(repo, name, frontmatter_name=None, body="", tools=True):
    path = os.path.join(repo, ".claude", "agents")
    os.makedirs(path, exist_ok=True)
    text = AGENT % (frontmatter_name if frontmatter_name is not None else name)
    if not tools:
        text = "\n".join(l for l in text.splitlines() if not l.startswith("tools:")) + "\n"
    with open(os.path.join(path, name + ".md"), "w", encoding="utf-8") as fh:
        fh.write(text + body)


def _codes(findings, level=None):
    return [f.code for f in findings if level is None or f.level == level]


@pytest.fixture
def harness(repo):
    """A clean two-skill, one-agent harness the agent actually references."""
    _skill(repo, "alpha")
    _skill(repo, "beta")
    _agent(repo, "worker", body="Runs `alpha` then `beta`.\n")
    return repo


class TestCleanTree:
    def test_reports_nothing(self, harness):
        findings, summary = harness_lint.lint(harness)
        assert findings == [] or _codes(findings) == []
        assert (summary["errors"], summary["warnings"]) == (0, 0)

    def test_counts_what_is_there(self, harness):
        _, summary = harness_lint.lint(harness)
        assert (summary["skills"], summary["agents"]) == (2, 1)


class TestFrontmatter:
    def test_missing_frontmatter_fires(self, harness):
        path = os.path.join(harness, ".claude", "skills", "alpha", "SKILL.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# /alpha\nno frontmatter here\n")
        assert "missing-frontmatter" in _codes(harness_lint.lint(harness)[0])

    def test_name_disagreeing_with_directory_fires(self, harness):
        _skill(harness, "alpha", name="not-alpha")
        findings, _ = harness_lint.lint(harness)
        assert "name-mismatch" in _codes(findings, harness_lint.ERROR)

    def test_missing_description_fires(self, harness):
        _skill(harness, "alpha", description="")
        assert "missing-description" in _codes(harness_lint.lint(harness)[0])

    def test_agent_name_disagreeing_with_filename_fires(self, harness):
        _agent(harness, "worker", frontmatter_name="wrkr")
        assert "name-mismatch" in _codes(harness_lint.lint(harness)[0])

    def test_agent_without_tools_warns_but_does_not_error(self, harness):
        _agent(harness, "worker", tools=False, body="Runs `alpha`, `beta`.\n")
        findings, summary = harness_lint.lint(harness)
        assert "no-tools-declared" in _codes(findings, harness_lint.WARN)
        assert summary["errors"] == 0


class TestReferences:
    def test_path_to_a_skill_that_does_not_exist_fires(self, harness):
        _agent(harness, "worker",
               body="See .claude/skills/ghost/SKILL.md and `alpha`, `beta`.\n")
        assert "dead-skill-path" in _codes(harness_lint.lint(harness)[0])

    def test_path_to_a_missing_file_inside_a_real_skill_fires(self, harness):
        _agent(harness, "worker",
               body="See .claude/skills/alpha/absent.md — also `beta`.\n")
        assert "dead-skill-file" in _codes(harness_lint.lint(harness)[0])

    def test_path_to_a_missing_agent_fires(self, harness):
        _skill(harness, "alpha", body="\nDelegates to .claude/agents/ghost.md\n")
        assert "dead-agent-path" in _codes(harness_lint.lint(harness)[0])

    def test_nested_path_resolves_to_a_real_file(self, harness):
        # Regression: a `<skill>/scripts/x.ps1` reference was truncated at the
        # first slash, so the linter looked for a *file* named `scripts`.
        scripts = os.path.join(harness, ".claude", "skills", "alpha", "scripts")
        os.makedirs(scripts)
        open(os.path.join(scripts, "Run.ps1"), "w").close()
        _agent(harness, "worker",
               body="Run .claude/skills/alpha/scripts/Run.ps1 then `beta`.\n")
        assert _codes(harness_lint.lint(harness)[0], harness_lint.ERROR) == []

    def test_trailing_punctuation_is_not_part_of_the_path(self, harness):
        _agent(harness, "worker",
               body="Defined in .claude/skills/alpha/SKILL.md. Also `beta`.\n")
        assert _codes(harness_lint.lint(harness)[0], harness_lint.ERROR) == []


class TestOrphans:
    def test_unreferenced_skill_warns(self, harness):
        _skill(harness, "lonely")
        findings, summary = harness_lint.lint(harness)
        assert "orphan-skill" in _codes(findings, harness_lint.WARN)
        assert summary["errors"] == 0        # never an error — it's evidence

    @pytest.mark.parametrize("mention", [
        "run `lonely` at the end",
        "invoke /lonely when stuck",
        "see [[lonely]]",
        "reads .claude/skills/lonely/SKILL.md",
    ])
    def test_any_invocation_form_clears_it(self, harness, mention):
        _skill(harness, "lonely")
        _agent(harness, "worker", body="Runs `alpha`, `beta`. %s\n" % mention)
        assert "orphan-skill" not in _codes(harness_lint.lint(harness)[0])

    def test_the_bare_word_alone_does_not_clear_it(self, harness):
        # The check that matters: ids like `plan` and `verify` are ordinary
        # English, so prose containing the word is not evidence of a reference.
        _skill(harness, "lonely")
        _agent(harness, "worker",
               body="Runs `alpha`, `beta`. Do not feel lonely about it.\n")
        assert "orphan-skill" in _codes(harness_lint.lint(harness)[0])

    def test_a_skill_referencing_itself_is_still_an_orphan(self, harness):
        _skill(harness, "lonely", body="\nSee `lonely` above.\n")
        assert "orphan-skill" in _codes(harness_lint.lint(harness)[0])


class TestReferenceBundles:
    def test_a_bundle_is_not_counted_as_a_skill(self, harness):
        # challenge-standards/ holds rules.md and no SKILL.md — real material,
        # but nothing can invoke it, so the roster count must not include it.
        bundle = os.path.join(harness, ".claude", "skills", "shared-rules")
        os.makedirs(bundle)
        with open(os.path.join(bundle, "rules.md"), "w", encoding="utf-8") as fh:
            fh.write("# Rules\n")
        findings, summary = harness_lint.lint(harness)
        assert summary["skills"] == 2
        assert _codes(findings, harness_lint.ERROR) == []

    def test_a_reference_into_a_bundle_resolves(self, harness):
        bundle = os.path.join(harness, ".claude", "skills", "shared-rules")
        os.makedirs(bundle)
        with open(os.path.join(bundle, "rules.md"), "w", encoding="utf-8") as fh:
            fh.write("# Rules\n")
        _agent(harness, "worker",
               body="Obeys .claude/skills/shared-rules/rules.md. `alpha` `beta`\n")
        assert _codes(harness_lint.lint(harness)[0], harness_lint.ERROR) == []

    def test_a_truly_empty_directory_errors(self, harness):
        os.makedirs(os.path.join(harness, ".claude", "skills", "hollow"))
        assert "empty-skill-dir" in _codes(harness_lint.lint(harness)[0])


class TestDeclaredCounts:
    def _claude_md(self, repo, text):
        with open(os.path.join(repo, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_stale_count_warns(self, harness):
        self._claude_md(harness, "This workspace has 9 skills and 4 agents.\n")
        findings, _ = harness_lint.lint(harness)
        assert "stale-count" in _codes(findings, harness_lint.WARN)

    def test_accurate_count_is_quiet(self, harness):
        self._claude_md(harness, "This workspace has 2 skills and 1 agents.\n")
        assert "stale-count" not in _codes(harness_lint.lint(harness)[0])
