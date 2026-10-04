"""T-020 FR-21: adopting a stale claim, and `ready` listing it (NFR-6, NFR-8)."""

import os
import shutil
import threading
from datetime import datetime, timedelta, timezone

import pytest

from server import audit, runs, tickets, trackers, verbs
from server.backends import vault_backend
from server.paths import find_repo_root

OLD = "2026-01-01T00:00:00Z"  # far past any ttl


@pytest.fixture
def wired(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    shutil.copyfile(src, os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


def stale_claim(repo, by="old-agent", tid="T-001", run=""):
    tickets.set_claim(repo, tid, by, claimed_at=OLD, claimed_run=run)


def claim(repo, agent, **args):
    return verbs.run(repo, "claim", ticket="T-001", confirm=True,
                     args=dict(agent=agent, **args))


class TestAdopt:
    def test_two_threads_adopt_same_stale_claim_exactly_one_wins_final_holder_matches(
            self, wired):
        backend = vault_backend.default()
        for rnd in range(20):
            tickets.set_claim(wired, "T-001", "")
            stale_claim(wired)
            barrier = threading.Barrier(2)
            outcome = {}

            def go(name):
                barrier.wait()
                try:
                    backend.claim(wired, "T-001", name)
                    outcome[name] = True
                except tickets.ClaimConflictError:
                    outcome[name] = False

            threads = [threading.Thread(target=go, args=(n,)) for n in ("a", "b")]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            winners = [n for n, ok in outcome.items() if ok]
            assert len(winners) == 1, (rnd, outcome)
            assert tickets.load(wired, "T-001")["claimed_by"] == winners[0], rnd

    def test_audit_row_has_previous_holder_basis_age(self, wired):
        rid = runs.create(wired, executor="chat", executor_id="c", ticket="T-001")["id"]
        runs.update(wired, rid, state="done", ended="2026-01-01T00:10:00Z")
        stale_claim(wired, run=rid)
        out = claim(wired, "new-agent")
        assert out["ok"] is True
        assert tickets.load(wired, "T-001")["claimed_by"] == "new-agent"
        rows = audit.read(wired, action="ticket.claim.adopt")
        assert len(rows) == 1
        d = rows[0]["detail"]
        assert d["previous_holder"] == "old-agent"
        assert d["previous_claimed_at"] == OLD
        assert d["previous_claimed_run"] == rid
        assert d["basis"] == "run_dead"
        assert d["age_secs"] > 0 and d["agent"] == "new-agent"

    def test_comment_posted_by_adopter(self, wired):
        stale_claim(wired)
        claim(wired, "new-agent")
        items = trackers.list_items(wired, "T-001", "comments")
        assert len(items) == 1
        assert items[0]["author"] == "new-agent"
        assert "old-agent" in items[0]["text"]

    def test_held_claim_still_refused_and_error_names_holder_basis_release(self, wired):
        claim(wired, "agent-1")
        out = claim(wired, "agent-2")
        assert out["ok"] is False
        assert "agent-1" in out["error"] and "fresh" in out["error"]
        assert "claim-release" in out["error"]
        assert tickets.load(wired, "T-001")["claimed_by"] == "agent-1"
        assert audit.read(wired, action="ticket.claim.adopt") == []

    def test_same_identity_reclaim_refreshes_claimed_at(self, wired):
        stale_claim(wired, by="agent-1")
        out = claim(wired, "agent-1")
        assert out["ok"] is True
        assert out["ticket"]["claimed_at"] != OLD
        assert audit.read(wired, action="ticket.claim.adopt") == []

    def test_adopter_gets_its_own_run_link(self, wired):
        dead = runs.create(wired, executor="chat", executor_id="old", ticket="T-001")["id"]
        runs.update(wired, dead, state="done", ended=OLD)
        stale_claim(wired, run=dead)
        mine = runs.create(wired, executor="chat", executor_id="c", ticket="T-001")["id"]
        claim(wired, "new-agent")
        assert tickets.load(wired, "T-001")["claimed_run"] == mine

    def test_info_dict_filled_only_on_adoption(self, wired):
        info = {}
        tickets.set_claim(wired, "T-001", "a", claimed_at=OLD)
        tickets.set_claim(wired, "T-001", "b", adopt_stale=True, info=info,
                          claimed_at="2026-10-02T00:00:00Z",
                          now=datetime(2026, 10, 2, tzinfo=timezone.utc))
        assert info["previous_holder"] == "a" and info["basis"] == "ttl"
        with pytest.raises(tickets.ClaimConflictError):
            tickets.set_claim(wired, "T-001", "c", adopt_stale=False)


class TestReady:
    def test_stale_listed_with_claim_state_held_omitted(self, wired):
        tickets.create(wired, "T-002", "Held one")
        tickets.create(wired, "T-003", "Free one")
        stale_claim(wired, tid="T-001")
        tickets.set_claim(wired, "T-002", "x",
                          claimed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        out = verbs.run(wired, "ready")
        by_id = {t["id"]: t for t in out["tickets"]}
        assert set(by_id) == {"T-001", "T-003"}
        assert by_id["T-001"]["claim"]["state"] == "stale"
        assert by_id["T-001"]["claim"]["basis"] == "ttl"
        assert "claim" not in by_id["T-003"]

    def test_ready_reads_runs_once(self, wired, monkeypatch):
        tickets.create(wired, "T-002", "Another")
        stale_claim(wired, tid="T-001")
        stale_claim(wired, tid="T-002")
        calls = []
        real = runs.list_runs
        monkeypatch.setattr(runs, "list_runs",
                            lambda *a, **k: calls.append(1) or real(*a, **k))
        out = verbs.run(wired, "ready")
        assert out["count"] == 2
        assert len(calls) == 1
