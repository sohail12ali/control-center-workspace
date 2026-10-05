"""T-021 FR-2: the task-boundary rule lives once in plan/SKILL.md and
breakdown-tasks points to it. Text-only checks over the real skill files."""

import hashlib
import os

from server import harness_lint

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAN = os.path.join(ROOT, ".claude", "skills", "plan", "SKILL.md")
BREAKDOWN = os.path.join(ROOT, ".claude", "skills", "breakdown-tasks", "SKILL.md")

LABELS = ("Fewest tasks", "Qualifying boundaries", "Reason per task",
          "Merge-back pass", "Re-read before done")

# sha256 of each `description:` line (right-stripped), captured before the edit.
DESCRIPTION_SHA = {
    PLAN: "c371b110358862cce69c18af94a381e022df533bde6987877bd78c33a250ca9f",
    BREAKDOWN: "4461f209b0e77d5aca97b91e8f948826f67e6fd3f02eb9e76041f7ee98560bbb",
}


def _text(path):
    return harness_lint._read(path)


def test_plan_has_heading_five_labels_and_size_caps():
    text = _text(PLAN)
    assert "Task boundary rule" in text
    for label in LABELS:
        assert "**%s**" % label in text, label
    assert "1-4h" in text
    assert "0.5/1/1.5/2/3h" in text


def test_breakdown_points_to_plan_and_drops_old_phrase():
    text = _text(BREAKDOWN)
    assert ".claude/skills/plan/SKILL.md" in text
    assert "ideally one component per task" not in text
    assert "0.5/1/1.5/2/3h" in text


def test_descriptions_byte_identical():
    for path, want in DESCRIPTION_SHA.items():
        line = next(l for l in _text(path).splitlines() if l.startswith("description:"))
        assert hashlib.sha256(line.rstrip().encode("utf-8")).hexdigest() == want, path


def test_roster_line_still_39_skills_7_agents():
    findings, summary = harness_lint.lint(ROOT)
    assert (summary["skills"], summary["agents"]) == (39, 7)
    assert summary["errors"] == 0
