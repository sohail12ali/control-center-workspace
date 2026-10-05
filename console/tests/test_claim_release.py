"""T-020 FR-22: the `claim-release` verb and its audited force path (BR-13)."""

import io
import json
import os
import shutil
from datetime import datetime, timezone

import pytest

from server import audit, mcp, tickets, trackers, verbs
from server.paths import find_repo_root

OLD = "2026-01-01T00:00:00Z"


@pytest.fixture
def wired(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    shutil.copyfile(src, os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


def fresh_claim(repo, by="holder"):
    tickets.set_claim(repo, "T-001", by,
                      claimed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      claimed_run="r1")


def release(repo, agent, **args):
    return verbs.run(repo, "claim-release", ticket="T-001", confirm=True,
                     args=dict(agent=agent, **args))


class TestRelease:
    def test_holder_release_clears_all_three_fields(self, wired):
        fresh_claim(wired)
        out = release(wired, "holder")
        assert out["ok"] is True
        t = tickets.load(wired, "T-001")
        assert (t["claimed_by"], t["claimed_at"], t["claimed_run"]) == ("", "", "")
        rows = audit.read(wired, action="ticket.claim.release")
        assert len(rows) == 1 and rows[0]["detail"]["previous_holder"] == "holder"

    def test_non_holder_release_of_held_claim_refused_claim_kept(self, wired):
        fresh_claim(wired)
        out = release(wired, "other")
        assert out["ok"] is False
        assert "force" in out["error"]
        assert tickets.load(wired, "T-001")["claimed_by"] == "holder"
        rows = audit.read(wired, action="ticket.claim.release")
        assert rows[0]["outcome"].startswith("error:")

    def test_stale_claim_released_by_third_identity_audit_has_basis(self, wired):
        tickets.set_claim(wired, "T-001", "holder", claimed_at=OLD)
        out = release(wired, "third")
        assert out["ok"] is True
        assert tickets.load(wired, "T-001")["claimed_by"] == ""
        d = audit.read(wired, action="ticket.claim.release")[0]["detail"]
        assert d["basis"] == "ttl" and d["agent"] == "third"
        assert d["previous_holder"] == "holder" and d["previous_claimed_at"] == OLD

    @pytest.mark.parametrize("reason", ["", "short", "         x   "])
    def test_force_with_empty_or_five_char_reason_refused(self, wired, reason):
        fresh_claim(wired)
        out = release(wired, "other", force="true", reason=reason)
        assert out["ok"] is False and "10" in out["error"]
        assert tickets.load(wired, "T-001")["claimed_by"] == "holder"
        assert audit.read(wired, action="ticket.claim.force_release")[0]["outcome"] \
            .startswith("error:")

    def test_force_with_reason_succeeds_audits_previous_holder_and_comments(self, wired):
        fresh_claim(wired)
        out = release(wired, "human", force="true", reason="agent crashed, host rebooted")
        assert out["ok"] is True and out["forced"] is True
        assert tickets.load(wired, "T-001")["claimed_by"] == ""
        row = audit.read(wired, action="ticket.claim.force_release")[0]
        d = row["detail"]
        assert row["outcome"] == "ok"
        assert d["previous_holder"] == "holder" and d["agent"] == "human"
        assert d["reason"] == "agent crashed, host rebooted"
        assert d["previous_claimed_run"] == "r1" and d["basis"] == "run_grace"
        comments = trackers.list_items(wired, "T-001", "comments")
        assert len(comments) == 1 and "agent crashed" in comments[0]["text"]
        assert comments[0]["author"] == "human"

    def test_missing_agent_and_unclaimed_ticket(self, wired):
        assert release(wired, "")["ok"] is False
        out = release(wired, "anyone")
        assert out["ok"] is True and out["released"] is False

    def test_in_cli_list_and_mcp_tool_list_and_needs_confirm(self, wired):
        assert any(v["id"] == "claim-release" for v in verbs.list_verbs(wired))
        buf = io.StringIO()
        mcp.Server(wired, stdout=buf, stderr=io.StringIO()).handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = {t["name"]: t for t in json.loads(buf.getvalue())["result"]["tools"]}
        assert "confirm" in tools["claim-release"]["inputSchema"]["required"]
        assert "reason" in tools["claim-release"]["inputSchema"]["properties"]
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "claim-release", ticket="T-001", args={"agent": "x"})
