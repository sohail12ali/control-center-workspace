"""T-021 FR-3: docs state what config and code do now. Text-only checks."""

import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return re.sub(r"\s+", " ", fh.read())


def _openrouter():
    with open(os.path.join(ROOT, "console", "config", "agents.toml"), "rb") as fh:
        rows = tomllib.load(fh)["backend"]
    return next(r for r in rows if r["id"] == "openrouter")


def _backend(backend_id):
    with open(os.path.join(ROOT, "console", "config", "agents.toml"), "rb") as fh:
        rows = tomllib.load(fh)["backend"]
    return next(r for r in rows if r["id"] == backend_id)


def test_openai_row_matches_the_docs():
    row = _backend("openai")
    assert row["enabled"] is True
    assert row["transport"] == "openai_api"
    assert row["base_url"] == "https://api.openai.com/v1"
    assert row["api_key_env"] == "OPENAI_API_KEY"
    assert row["models"] == []
    readme = _read("console", "README.md")
    assert 'base_url = "https://api.openai.com/v1"' in readme
    assert "OPENAI_API_KEY" in readme
    assert "not the Assistant default" in readme
    skill = _read(".claude", "skills", "console", "SKILL.md")
    assert "OPENAI_API_KEY" in skill
    assert "not the Assistant default" in skill


def test_docs_agree_with_config():
    enabled = _openrouter().get("enabled")
    assert enabled is True
    for doc in (("console", "README.md"), (".claude", "skills", "console", "SKILL.md")):
        text = _read(*doc)
        assert "It ships disabled" not in text, doc
        assert "OpenRouter row ships `enabled = false`" not in text, doc
        assert "flip `enabled = true` on the `openrouter` row" not in text, doc


def test_stale_phrases_gone():
    assert "(True of the live chats too.)" not in _read("console", "server", "agents.py")
    readme = _read("console", "README.md")
    assert "**No worktree isolation.**" not in readme
    assert "**No live steering (one-shot launcher only).**" in readme
    cmp_text = _read("knowledge-center", "docs", "console-feature-comparison.md")
    for row in ("Worktree isolation", "Mechanical verbs", "Schedules"):
        cell = re.search(r"\| " + row + r"[^|]*\| ([^|]*)\|", cmp_text)
        assert cell and not cell.group(1).strip().startswith("❌"), row


def test_desktop_readme_says_assistant():
    text = _read("desktop", "README.md")
    assert "remote control of the live Agents chat" not in text
    assert "remote control of the Assistant" in text
    assert "features.toml" in text
