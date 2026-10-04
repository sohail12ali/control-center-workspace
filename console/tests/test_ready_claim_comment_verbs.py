"""T-017 Phase 3 (3a): the `ready`/`claim`/`comment` verbs — FR-7/FR-8/FR-9.

Mirrors test_mutation_verbs.py's shape: verbs are installed from the shipped
verbs.toml and run through `verbs.run`, the same path the CLI (`verb run`),
MCP (`tools/call`), and HTTP (`POST /api/verbs/{id}/run`) all dispatch
through — so a test at this layer exercises all three surfaces' shared logic
(one-api rule) without needing three separate harnesses.
"""

import os
import shutil
import threading

import pytest

from server import audit, bus, tickets, trackers, verbs
from server.paths import find_repo_root


def _install_shipped_verbs(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    dest = os.path.join(repo, "console", "config", "verbs.toml")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    verbs._cache.clear()


@pytest.fixture
def wired(repo):
    _install_shipped_verbs(repo)
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


class TestReady:
    def test_empty_when_no_tickets_available(self, wired):
        # T-001 is unblocked and unclaimed, so it IS available; claim it out
        # of the way to exercise the true-empty case (Edge Case §8: empty
        # list, never an error).
        tickets.set_claim(wired, "T-001", "agent-1")
        out = verbs.run(wired, "ready")
        assert out == {"count": 0, "tickets": []}

    def test_excludes_claimed(self, wired):
        tickets.set_claim(wired, "T-001", "agent-1")
        out = verbs.run(wired, "ready")
        assert out["tickets"] == []

    def test_excludes_blocked(self, wired):
        trackers.add(wired, "T-001", "questions", "Why?", priority="critical")
        out = verbs.run(wired, "ready")
        assert out["tickets"] == []

    def test_includes_unblocked_unclaimed(self, wired):
        out = verbs.run(wired, "ready")
        assert out["count"] == 1
        assert out["tickets"][0]["id"] == "T-001"

    def test_no_ticket_or_confirm_required(self, wired):
        # A read: neither gate applies, unlike claim/comment below.
        verbs.run(wired, "ready")  # would raise VerbError if a gate fired


class TestClaim:
    def test_needs_confirm(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "claim", ticket="T-001", args={"agent": "agent-1"})

    def test_needs_ticket(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "claim", confirm=True, args={"agent": "agent-1"})

    def test_sets_claimed_by_and_at(self, wired):
        out = verbs.run(wired, "claim", ticket="T-001", confirm=True,
                        args={"agent": "agent-1"})
        assert out["ok"] is True
        assert out["ticket"]["claimed_by"] == "agent-1"
        assert tickets.load(wired, "T-001")["claimed_by"] == "agent-1"

    def test_missing_agent_is_a_named_refusal_not_a_crash(self, wired):
        out = verbs.run(wired, "claim", ticket="T-001", confirm=True, args={})
        assert out["ok"] is False
        assert "agent" in out["error"]

    def test_conflicting_claim_is_refused_not_overwritten(self, wired):
        verbs.run(wired, "claim", ticket="T-001", confirm=True,
                 args={"agent": "agent-1"})
        out = verbs.run(wired, "claim", ticket="T-001", confirm=True,
                        args={"agent": "agent-2"})
        assert out["ok"] is False
        assert "agent-1" in out["error"]
        assert tickets.load(wired, "T-001")["claimed_by"] == "agent-1"

    def test_claim_is_audited(self, wired):
        verbs.run(wired, "claim", ticket="T-001", confirm=True,
                 args={"agent": "agent-1"})
        rows = audit.read(wired, action="ticket.claim")
        assert len(rows) == 1
        assert rows[0]["target"] == "T-001"
        assert rows[0]["detail"]["agent"] == "agent-1"
        assert rows[0]["outcome"] == "ok"

    def test_refused_claim_is_also_audited(self, wired):
        verbs.run(wired, "claim", ticket="T-001", confirm=True,
                 args={"agent": "agent-1"})
        verbs.run(wired, "claim", ticket="T-001", confirm=True,
                 args={"agent": "agent-2"})
        rows = audit.read(wired, action="ticket.claim")
        assert len(rows) == 2
        outcomes = {r["detail"]["agent"]: r["outcome"] for r in rows}
        assert outcomes["agent-1"] == "ok"
        assert outcomes["agent-2"].startswith("error:")

    def test_claim_publishes_a_bus_notification(self, wired):
        session_id = "sess-1"
        bus.default().subscribe(session_id, "ticket://T-001")
        verbs.run(wired, "claim", ticket="T-001", confirm=True,
                 args={"agent": "agent-1"})
        pending = bus.default().drain(session_id)
        assert any(p["uri"] == "ticket://T-001" for p in pending)

    def test_concurrent_claims_by_different_agents_exactly_one_succeeds(self, wired):
        n = 6
        results = [None] * n

        def _try(i):
            out = verbs.run(wired, "claim", ticket="T-001", confirm=True,
                            args={"agent": "agent-%d" % i})
            results[i] = out["ok"]

        threads = [threading.Thread(target=_try, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(True) == 1
        assert results.count(False) == n - 1


class TestComment:
    def test_needs_confirm(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "comment", ticket="T-001", args={"text": "hi"})

    def test_appends_attributed_timestamped_comment(self, wired):
        item = verbs.run(wired, "comment", ticket="T-001", confirm=True,
                         args={"text": "Looks good", "author": "agent-1"})
        assert item["id"] == "C1"
        assert item["text"] == "Looks good"
        assert item["author"] == "agent-1"
        assert item["posted_on"]

    def test_readable_via_tracker_list(self, wired):
        verbs.run(wired, "comment", ticket="T-001", confirm=True,
                 args={"text": "Looks good"})
        items = trackers.list_items(wired, "T-001", "comments")
        assert len(items) == 1 and items[0]["text"] == "Looks good"

    def test_never_blocks(self, wired):
        verbs.run(wired, "comment", ticket="T-001", confirm=True,
                 args={"text": "Looks good"})
        assert not trackers.blockers(wired, "T-001")

    def test_empty_text_is_a_named_refusal(self, wired):
        out = verbs.run(wired, "comment", ticket="T-001", confirm=True,
                        args={"text": "  "})
        assert out["ok"] is False

    def test_comment_is_audited(self, wired):
        verbs.run(wired, "comment", ticket="T-001", confirm=True,
                 args={"text": "Looks good", "author": "agent-1"})
        rows = audit.read(wired, action="ticket.comment")
        assert len(rows) == 1
        assert rows[0]["target"] == "T-001"
        assert rows[0]["detail"]["author"] == "agent-1"

    def test_comment_publishes_a_bus_notification(self, wired):
        session_id = "sess-2"
        bus.default().subscribe(session_id, "ticket://T-001")
        verbs.run(wired, "comment", ticket="T-001", confirm=True,
                 args={"text": "Looks good"})
        pending = bus.default().drain(session_id)
        assert any(p["uri"] == "ticket://T-001" for p in pending)


class TestOneApi:
    """FR-7/8/9: reachable identically via CLI/MCP/HTTP because they are
    ordinary verbs dispatched through `verbs.run` — the same registry every
    surface already shares (Phase 1's 1a/1b). Confirmed here by checking they
    appear in the MCP tool catalogue and the generic verb registry, rather
    than re-testing each transport (already covered by test_mcp.py /
    test_mcp_http.py / test_ui_endpoints.py for the shared dispatch path)."""

    def test_registered_in_verb_registry(self, wired):
        reg = verbs.registry(wired)
        assert {"ready", "claim", "comment"} <= set(reg)

    def test_exposed_as_mcp_tools(self, wired):
        from server import agent_tools
        names = {d["function"]["name"] for d in agent_tools.tool_definitions(wired)}
        assert {"console_ready", "console_claim", "console_comment"} <= names
