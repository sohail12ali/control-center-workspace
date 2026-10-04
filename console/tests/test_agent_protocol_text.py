"""T-020 FR-25: the verifier and fixer protocols use the review-round counter.
Reads the agent files as text; edits to existing files only."""

import os
import re

from server.paths import find_repo_root

ROOT = find_repo_root()
AGENTS = os.path.join(ROOT, ".claude", "agents")


def read(name):
    with open(os.path.join(AGENTS, name + ".md"), encoding="utf-8") as fh:
        return fh.read()


def step(text, n):
    m = re.search(r"^%d\. (.*(?:\n(?!\d+\. |\n|#).*)*)" % n, text, re.M)
    assert m, "protocol step %d not found" % n
    return m.group(1)


def test_verifier_and_fixer_mention_review_round_and_escalated_stop_rule():
    verifier, fixer = read("verifier"), read("fixer")
    ten = step(verifier, 10)
    assert "review-round" in ten and "changes_requested" in ten and "approved" in ten
    assert "escalate" in ten and "stop" in ten.lower()
    assert "review.escalated" in verifier and "review.escalated" in fixer
    one = step(fixer, 1)
    assert "review.escalated" in one and "human_decision" in one
    assert "review.escalated" in step(verifier, 1)


def test_output_contract_blocks_intact():
    for name, header, last in (
            ("verifier", "── Verifier ──", "❓ Respond: APPROVED (close-work) / FIX (@fixer) / REVISE (@planner) / REJECT"),
            ("fixer", "── Fixer ──", "❓ Respond: APPROVED (re-verify → @verifier) / SKIP / REVISE / REJECT")):
        text = read(name)
        block = text.split("# Output contract", 1)[1]
        assert header in block and last in block
        assert block.count("```") == 2
        assert text.startswith("---\nname: %s\n" % name)


def test_no_new_agent_or_skill_files():
    agents = [f for f in os.listdir(AGENTS) if f.endswith(".md")]
    base = os.path.join(ROOT, ".claude", "skills")
    skills = [d for d in os.listdir(base)
              if os.path.isfile(os.path.join(base, d, "SKILL.md"))]
    assert len(agents) == 7
    assert len(skills) == 39
