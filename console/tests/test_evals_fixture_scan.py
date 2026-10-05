"""Committed fixtures stay free of paths and key-shaped strings."""

import os

from evals.runner import scan_fixture_text

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "evals", "fixtures")


def test_scan_flags_user_profile_paths():
    assert "profile" in scan_fixture_text(r"wrote C:\Users\someone\note")
    assert "profile" in scan_fixture_text("see /Users/someone")
    assert "profile" in scan_fixture_text("see /home/someone")


def test_scan_flags_key_like_strings():
    assert "key" in scan_fixture_text("sk-" + "a" * 16)
    assert "key" in scan_fixture_text("ghp_" + "b" * 16)
    assert scan_fixture_text("sk-short") == []


def test_scan_flags_openrouter_and_bearer():
    assert "token" in scan_fixture_text("OPENROUTER_API_KEY")
    assert "token" in scan_fixture_text("Authorization: Bearer secret")


def test_committed_fixtures_are_clean():
    names = [n for n in os.listdir(FIX) if n.endswith(".jsonl")]
    assert len(names) >= 20
    for name in names:
        text = open(os.path.join(FIX, name), encoding="utf-8").read()
        assert scan_fixture_text(text) == [], name
