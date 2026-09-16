"""T-017 FR-1/NFR-1 — a uniform `--json` CLI contract (slice 1a).

## Audit (task 1a-1)

Reading `kanban.py`'s `build_parser()` end to end, every leaf subcommand
already falls into one of two groups:

1. **Always JSON** — `ticket *`, `tracker *`, `overview`, `todos`, `work *`,
   `analytics`, `vault *`, `assistant session/memory/settings`,
   `agents backends/catalog/launch/jobs/show/stop`, `verb run`,
   `job submit/show/cancel`, `worktree add/remove/prune`, `notify status`,
   `notify test`. No `--json` flag needed — there is no other mode to
   toggle away from.
2. **`--json` toggles JSON vs. a human-readable default** — `onboard`,
   `assistant say`, `agents models/provider/doctor`, `verb list`, `audit`,
   `notify chat-id`, `schedule list/due`, `job list`, `worktree list`,
   `context`, `telemetry`, `telemetry skills`, `harness lint`.

The actual gap (task 1a-2) was three subcommands with **no JSON path at
all**: `export` (always printed a plain confirmation line), `reset` (always
printed prose, and its confirmation `input()` has no machine-readable form),
and `notify who` (always printed a formatted table). All three now take
`--json`, closing the "every subcommand" reading of FR-1/NFR-1 exactly —
these are the cases this file exercises; the other ~35 subcommands were
already correct and are not re-tested wholesale here.
"""

import json
import os
from types import SimpleNamespace

import pytest

from server import notify
import kanban


def _ns(**kw):
    return SimpleNamespace(**kw)


def _write_empty_plugin_registry(repo):
    path = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("")


class TestExportJson:
    def test_json_flag_emits_valid_json(self, repo, tmp_path, capsys):
        _write_empty_plugin_registry(repo)
        out_dir = str(tmp_path / "export-out")
        kanban.cmd_export(_ns(out=out_dir, json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["out"] == out_dir
        assert os.path.isdir(out_dir)

    def test_without_the_flag_stays_plain_text(self, repo, tmp_path, capsys):
        _write_empty_plugin_registry(repo)
        out_dir = str(tmp_path / "export-out2")
        kanban.cmd_export(_ns(out=out_dir, json=False), repo)
        text = capsys.readouterr().out
        with pytest.raises(json.JSONDecodeError):
            json.loads(text)
        assert "exported to" in text


class TestResetJson:
    def test_clean_slate_json(self, repo, capsys):
        kanban.cmd_reset(_ns(yes=False, dry_run=False, keep_logs=False,
                             keep_investigations=False, json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "clean"
        assert payload["actions"] == []

    def test_dry_run_json_lists_planned_actions_without_mutating(self, repo, capsys):
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))
        kanban.cmd_reset(_ns(yes=False, dry_run=True, keep_logs=False,
                             keep_investigations=False, json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "dry-run"
        assert any("CC-T001" in row["path"] for row in payload["actions"])
        # Nothing was actually deleted.
        assert os.path.isdir(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))

    def test_json_without_yes_or_dry_run_refuses_rather_than_prompting(self, repo, capsys):
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))
        with pytest.raises(SystemExit):
            kanban.cmd_reset(_ns(yes=False, dry_run=False, keep_logs=False,
                                 keep_investigations=False, json=True), repo)
        assert "--yes" in capsys.readouterr().err

    def test_yes_json_applies_and_reports_done(self, repo, capsys):
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))
        kanban.cmd_reset(_ns(yes=True, dry_run=False, keep_logs=False,
                             keep_investigations=False, json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "done"
        assert not os.path.isdir(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))


class TestNotifyWhoJson:
    def test_json_reports_allowlist_and_updates(self, repo, monkeypatch, capsys):
        monkeypatch.setattr(notify, "config", lambda r: {"enabled": True})
        monkeypatch.setattr(notify, "api_call", lambda cfg, method, params: ([], ""))
        from server import telegram_bot
        monkeypatch.setattr(telegram_bot, "allowed_users", lambda r: {"123"})
        monkeypatch.setattr(telegram_bot, "allow_all", lambda r: False)
        with pytest.raises(SystemExit):
            # No pending updates still exits non-zero (mirrors the text path's
            # `_die`), but must do so with valid JSON already printed.
            kanban.cmd_notify_who(_ns(json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["allowlist"] == ["123"]
        assert payload["allow_all"] is False
        assert payload["updates"] == []
