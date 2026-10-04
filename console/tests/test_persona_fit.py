"""T-021 FR-5: every persona fits the 4,000-char cap as delivered, and the
Assistant's Safety section arrives whole, including the untrusted-content
clause. Reads the real files through `prompt_build.persona_text`; no model."""

import os

from server import prompt_build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAFETY_BULLETS = (
    "Never repeat back, log, or store an API key",
    "talk it into an exception",
    "Don't invent facts about this workspace's tickets",
    "You do not approve your own tool calls",
    "exactly as it does in every other chat",
)


def _assistant():
    return prompt_build.persona_text(ROOT, "assistant")


def test_assistant_persona_fits_cap_and_is_not_cut():
    text = _assistant()
    assert len(text) <= prompt_build.PERSONA_CAP, len(text)
    assert "Persona text cut here" not in text


def test_delivered_text_has_clause_phrase_four_words_and_every_safety_bullet():
    text = _assistant()
    assert "data, not instructions" in text
    for word in ("clipboard", "OCR", "screenshot", "web"):
        assert word in text, word
    for bullet in SAFETY_BULLETS:
        assert bullet in text, bullet
    # the clause sits inside ## Safety, and is at most 600 chars
    safety = text[text.index("## Safety"):]
    assert "data, not instructions" in safety
    clause = next(p for p in safety.split("\n- ") if "data, not instructions" in p)
    assert len(clause) <= 600, len(clause)


def test_persona_cap_is_still_4000():
    assert prompt_build.PERSONA_CAP == 4000


def test_all_seven_agent_personas_fit():
    agents = os.path.join(ROOT, ".claude", "agents")
    names = sorted(f[:-3] for f in os.listdir(agents) if f.endswith(".md"))
    assert len(names) == 7
    for name in names:
        text = prompt_build.persona_text(ROOT, name)
        assert len(text) <= prompt_build.PERSONA_CAP, name
        assert "Persona text cut here" not in text, name


def test_new_tests_call_no_model():
    with open(__file__, encoding="utf-8") as fh:
        src = fh.read()
    for banned in ("backends", "subprocess", "urllib", "socket"):
        assert "import %s" % banned not in src and "from server import %s" % banned not in src
