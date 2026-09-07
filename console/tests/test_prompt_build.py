"""System prompt assembly.

For a backend with no slash-command system, "choose a skill" means "put the
skill's text in the prompt". The failure to guard against is a silent
truncation: the agent believes it has its instructions, follows the half it
received, and nothing in the transcript says why it went wrong.
"""

import os

import pytest

from server import prompt_build


def _write(repo, rel, text):
    path = os.path.join(repo, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture
def harness(repo):
    _write(repo, ".claude/skills/harness-standards/core.md",
           "---\nname: harness-standards\n---\n\nBE HONEST. Six gates apply.\n")
    _write(repo, ".claude/agents/builder.md",
           "---\nname: builder\ntools: Read, Edit\n---\n\nYou implement one task at a time.\n")
    _write(repo, ".claude/skills/plan/SKILL.md",
           "---\nname: plan\ndescription: Planning.\n---\n\nDecompose into atomic tasks.\n")
    return repo


class TestAssembly:
    def test_core_persona_and_skill_all_land(self, harness):
        text, report = prompt_build.build(harness, persona="builder", skill="plan")
        assert "BE HONEST" in text
        assert "You implement one task at a time" in text
        assert "Decompose into atomic tasks" in text
        assert report["missing"] == []

    def test_frontmatter_is_stripped(self, harness):
        # It is loader metadata; sending it spends tokens describing a tools
        # list the model does not control.
        text, _ = prompt_build.build(harness, persona="builder", skill="plan")
        assert "tools: Read, Edit" not in text
        assert "description: Planning." not in text

    def test_the_core_applies_even_with_no_persona_or_skill(self, harness):
        text, _ = prompt_build.build(harness)
        assert "BE HONEST" in text

    def test_orientation_names_the_workspace_and_the_cheap_path(self, harness):
        text, _ = prompt_build.build(harness)
        assert "console_context" in text
        assert "sixteen times smaller" in text

    def test_the_ticket_is_named_when_given(self, harness):
        text, _ = prompt_build.build(harness, ticket="CC-T001")
        assert "CC-T001" in text

    def test_it_warns_against_hand_editing_toml(self, harness):
        text, _ = prompt_build.build(harness)
        assert "Never hand-edit" in text


class TestMissingFiles:
    def test_a_missing_skill_is_reported(self, harness):
        text, report = prompt_build.build(harness, skill="ghost")
        assert "skill:ghost" in report["missing"]
        assert "no SKILL.md found" in text      # visible to the model too

    def test_a_missing_persona_is_reported(self, harness):
        _text, report = prompt_build.build(harness, persona="ghost")
        assert "persona:ghost" in report["missing"]

    def test_an_absent_core_is_not_fatal(self, repo):
        text, report = prompt_build.build(repo)
        assert "Workspace" in text          # orientation still assembles
        assert report["chars"] > 0


class TestBudget:
    def test_a_prompt_within_budget_is_not_truncated(self, harness):
        _text, report = prompt_build.build(harness, persona="builder", skill="plan")
        assert report["truncated"] == []

    def test_an_oversized_section_is_cut_and_named(self, harness):
        _write(harness, ".claude/skills/huge/SKILL.md",
               "---\nname: huge\n---\n\n" + ("word " * 20000))
        text, report = prompt_build.build(harness, skill="huge", budget=2000)
        assert "skill: huge" in report["truncated"]
        assert "cut here to fit" in text

    def test_the_cut_is_announced_at_the_end_too(self, harness):
        # A model that reads only the tail should still learn it was truncated.
        _write(harness, ".claude/skills/huge/SKILL.md",
               "---\nname: huge\n---\n\n" + ("word " * 20000))
        text, _ = prompt_build.build(harness, skill="huge", budget=2000)
        assert "Prompt budget note" in text
        assert "Treat" in text and "unread" in text

    def test_the_budget_is_respected(self, harness):
        _write(harness, ".claude/skills/huge/SKILL.md",
               "---\nname: huge\n---\n\n" + ("word " * 20000))
        text, report = prompt_build.build(harness, skill="huge", budget=2000)
        # The budget governs the content sections; the closing note is added
        # after, and is a handful of characters.
        assert report["chars"] < 2600

    def test_orientation_and_core_come_first_so_they_survive_a_squeeze(self, harness):
        _write(harness, ".claude/skills/huge/SKILL.md",
               "---\nname: huge\n---\n\n" + ("word " * 20000))
        text, report = prompt_build.build(harness, skill="huge", budget=1200)
        assert "orientation" in report["included"]
        assert "harness core" in report["included"]

    def test_report_counts_characters(self, harness):
        text, report = prompt_build.build(harness, persona="builder")
        assert report["chars"] == len(text)


class TestConsoleOwnedPersonaSecondRoot:
    """T-004 `persona-console-owned-second-root`: `console/config/{persona}.md`
    is tried before `.claude/agents/{persona}.md`, so the Assistant's persona
    is console-owned rather than a synthetic 8th agent file (BR-3)."""

    def test_a_console_owned_persona_is_found(self, repo):
        _write(repo, "console/config/assistant.md",
              "---\nname: assistant\n---\n\nYou are the Assistant.\n")
        assert "You are the Assistant." in prompt_build.persona_text(repo, "assistant")

    def test_the_console_owned_root_wins_over_the_agents_fallback(self, repo):
        _write(repo, "console/config/dup.md", "CONSOLE-OWNED TEXT")
        _write(repo, ".claude/agents/dup.md", "AGENT-FILE TEXT")
        assert prompt_build.persona_text(repo, "dup") == "CONSOLE-OWNED TEXT"

    def test_the_existing_agent_persona_mechanism_is_unaffected(self, harness):
        # "builder" has no console/config/builder.md — must still resolve via
        # the pre-existing .claude/agents/ fallback, unchanged.
        assert "You implement one task at a time" in prompt_build.persona_text(
            harness, "builder")


class TestPersonaCap:
    """BR-7: persona text is capped at 4,000 chars, truncated+stated (never
    silent), and the cut is audited — enforced once, in `persona_text`
    itself, so every caller (an `openai_api` build, a CLI's `system_append`)
    inherits the same guarantee."""

    def test_a_persona_within_the_cap_is_untouched(self, repo):
        _write(repo, "console/config/short.md", "a short persona")
        assert prompt_build.persona_text(repo, "short") == "a short persona"

    def test_an_oversized_persona_is_cut_and_stated(self, repo):
        _write(repo, "console/config/huge.md", "x" * 4500)
        text = prompt_build.persona_text(repo, "huge")
        assert len(text) < 4500
        assert text.startswith("x" * 4000)
        assert "cut here" in text
        assert "4,000-char cap" in text or "4000-char cap" in text

    def test_an_oversized_persona_is_audited(self, repo):
        from server import audit
        _write(repo, "console/config/huge.md", "y" * 4500)
        prompt_build.persona_text(repo, "huge")
        rows = audit.read(repo, action="assistant.persona_truncated")
        assert rows and rows[0]["target"] == "persona:huge"
