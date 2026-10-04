"""T-021 FR-11: close protocol text names close-check and forbids an agent override.

Reads the real files. Description lines are pinned to their pre-edit hashes so a
protocol edit cannot quietly rewrite a skill or agent description.
"""

import hashlib
import os

from server import prompt_build
from server.paths import find_repo_root

ROOT = find_repo_root()

#: sha256 of the `description:` line before the FR-11 edit.
DESCRIPTION_SHA = {
    ".claude/skills/close-work/SKILL.md":
        "35f1a28841de91963fac3e10fdc67e9cc3d2cbc4d7b9e5702f431b62e051577e",
    ".claude/agents/harness.md":
        "28842f2b1c0985c75e3b97ff507a85b3f1adb88580df1a0944e6e3246d6b7d5d",
    ".claude/agents/builder.md":
        "13bb725c51b0fdd34bd24e91c7d1cdec68fb83e5c43ddf1b35c14e088b1cead6",
    ".claude/agents/verifier.md":
        "b501415cec032456f9c1da2df253532c7d19074fea99e95e82881bc03b456a6d",
}

#: harness.md size before the routing-row edit. Growth stays inside the persona cap.
HARNESS_BYTES_BEFORE = 4088


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def description_line(text):
    for line in text.splitlines():
        if line.startswith("description:"):
            return line
    raise AssertionError("no description line")


def test_close_work_mentions_close_check_close_override_and_forbids_agent_reason():
    text = read(".claude/skills/close-work/SKILL.md")
    assert "verb run close-check --ticket {id}" in text
    assert "ok: false" in text
    assert "The guard runs `close-check` again" in text
    assert "never edit `verification.md` only to satisfy `close-check`" in text.lower()
    assert "never call `close-override`" in text.lower()
    assert "only the user supplies one" in text.lower()


def test_harness_row_has_close_check_and_growth_within_378():
    text = read(".claude/agents/harness.md")
    assert "`close-check`, then `close-work` only on `ok`" in text
    growth = len(text.encode("utf-8")) - HARNESS_BYTES_BEFORE
    assert 0 <= growth <= 378, growth
    assert len(prompt_build.persona_text(ROOT, "harness")) <= prompt_build.PERSONA_CAP


def test_builder_has_claim_step():
    text = read(".claude/agents/builder.md")
    assert "verb run claim --ticket {id} agent=<identity>" in text
    assert "re-claim" in text


def test_claude_md_verifier_row_has_close_check():
    text = read("CLAUDE.md")
    row = next(line for line in text.splitlines() if line.startswith("| `verifier`"))
    assert "`close-check`" in row
    assert "`harness` runs `close-work`" in row


def test_contract_headers_intact():
    assert "── Builder ──" in read(".claude/agents/builder.md")
    assert "── Harness ──" in read(".claude/agents/harness.md")
    assert "── Verifier ──" in read(".claude/agents/verifier.md")


def test_descriptions_byte_identical():
    for rel, digest in DESCRIPTION_SHA.items():
        line = description_line(read(rel))
        assert hashlib.sha256(line.encode("utf-8")).hexdigest() == digest, rel


def test_every_persona_within_cap():
    agents = os.path.join(ROOT, ".claude", "agents")
    names = sorted(f[:-3] for f in os.listdir(agents) if f.endswith(".md"))
    assert len(names) == 7
    for name in names:
        text = prompt_build.persona_text(ROOT, name)
        assert len(text) <= prompt_build.PERSONA_CAP, (name, len(text))


def test_verifier_step_10_has_close_check_and_no_close_work_instruction():
    text = read(".claude/agents/verifier.md")
    step = next(line for line in text.splitlines() if line.startswith("10. "))
    assert "close-check" in step
    assert "Do not run `close-work`" in step
    assert "then `close-work`" not in step


def test_verifier_contract_has_disposition_and_header():
    text = read(".claude/agents/verifier.md")
    assert "── Verifier ──" in text
    assert "Disposition: ready_to_close | needs_fix | blocked | needs_human" in text


def test_verifier_keeps_t020_fr25_phrase():
    text = read(".claude/agents/verifier.md")
    step = next(line for line in text.splitlines() if line.startswith("10. "))
    assert "review-round outcome=approved" in step
    assert "review-round outcome=changes_requested agent=verifier" in step
    assert "escalate" in step and "review.escalated" in step
    assert "review.escalated" in text.split("10. ", 1)[0]


def test_verifier_description_byte_identical():
    line = description_line(read(".claude/agents/verifier.md"))
    digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
    assert digest == DESCRIPTION_SHA[".claude/agents/verifier.md"]
