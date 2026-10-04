"""T-020 FR-20: the stale-claim rule (BR-6, BR-7), over an injected clock."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from server import run_config, runs, tickets

NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def t(repo):
    tickets.create(repo, "T-001", "A ticket")
    return repo


def claim(repo, age, run="", by="agent-1"):
    """Claim T-001, `age` before NOW (None -> empty claimed_at)."""
    tickets.set_claim(repo, "T-001", by,
                      claimed_at="" if age is None else stamp(NOW - age),
                      claimed_run=run)


def make_run(repo, state="running", ended_ago=None, ticket="T-001", executor="chat"):
    rec = runs.create(repo, executor=executor, executor_id="c", ticket=ticket,
                      state="running")
    fields = {"state": state}
    if ended_ago is not None:
        fields["ended"] = stamp(NOW - ended_ago)
    if state != "running":
        runs.update(repo, rec["id"], **fields)
    return rec["id"]


def status(repo, **kw):
    return tickets.claim_status(repo, "T-001", now=NOW, **kw)


class TestClaimStatus:
    def test_every_branch_with_injected_clock(self, t):
        # free
        out = status(t)
        assert (out["state"], out["holder"]) == ("free", "")

        # linked live Run + claim 3 days old -> held/run_live (BR-6)
        live = make_run(t, "running")
        claim(t, timedelta(days=3), run=live)
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "run_live")
        assert out["age_secs"] == 3 * 86400 and out["claimed_run"] == live
        tickets.set_claim(t, "T-001", "")

        # linked Run terminal 61 s ago -> stale/run_dead; 30 s ago -> held
        dead = make_run(t, "done", ended_ago=timedelta(seconds=61))
        claim(t, timedelta(hours=1), run=dead)
        out = status(t)
        assert (out["state"], out["basis"]) == ("stale", "run_dead")
        tickets.set_claim(t, "T-001", "")
        recent = make_run(t, "failed", ended_ago=timedelta(seconds=30))
        claim(t, timedelta(hours=1), run=recent)
        assert status(t)["state"] == "held"
        tickets.set_claim(t, "T-001", "")

        # linked id with no record, claim 2 min old -> stale/run_missing
        claim(t, timedelta(minutes=2), run="nosuchrun")
        out = status(t)
        assert (out["state"], out["basis"]) == ("stale", "run_missing")
        # ... but with an unknown claim time it never expires (BR-7)
        claim(t, None, run="nosuchrun")
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "unknown")
        tickets.set_claim(t, "T-001", "")

    def test_unlinked_branches(self, t):
        # unlinked, a different ACTIVE Run exists -> held/run_live
        claim(t, timedelta(hours=9))
        other = make_run(t, "running")
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "run_live")
        runs.update(t, other, state="done", ended="2026-10-02T11:00:00Z")
        # no Runs active, claim 9 h old -> stale/ttl
        out = status(t)
        assert (out["state"], out["basis"]) == ("stale", "ttl")
        # 7 h old -> held
        claim(t, timedelta(hours=7))
        assert status(t)["state"] == "held"
        # ttl_secs=0 disables expiry
        claim(t, timedelta(hours=9))
        cfg = dict(run_config.claims_cfg(t), ttl_secs=0)
        out = tickets.evaluate_claim(tickets.load(t, "T-001"), [], NOW, cfg)
        assert out["state"] == "held"
        # empty claimed_at -> held/unknown
        claim(t, None)
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "unknown")
        assert out["age_secs"] is None

    def test_planner_done_builder_live_is_stale_run_dead(self, t):
        planner = make_run(t, "done", ended_ago=timedelta(minutes=5))
        make_run(t, "running")  # the builder's own Run
        claim(t, timedelta(minutes=30), run=planner, by="planner")
        out = status(t)
        assert (out["state"], out["basis"], out["holder"]) == ("stale", "run_dead", "planner")

    def test_scheduled_retry_counts_as_active(self, t):
        rid = make_run(t, "scheduled_retry")
        claim(t, timedelta(days=2), run=rid)
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "run_live")

    def test_config_from_claims_section_invalid_falls_back_with_one_warning(
            self, t, capsys):
        path = os.path.join(t, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('\n[claims]\nttl_secs = "soon"\ndead_grace_secs = 5\n')
        tickets.boards_mod._console_cache.clear()
        run_config.reset_warnings()
        claim(t, timedelta(hours=9))
        assert status(t)["basis"] == "ttl"  # default 8 h used
        status(t)
        err = capsys.readouterr().err
        assert err.count("ttl_secs") == 1
        assert run_config.claims_cfg(t)["dead_grace_secs"] == 5

    def test_read_error_returns_held_unknown(self, t, monkeypatch):
        claim(t, timedelta(hours=9))

        def boom(*a, **k):
            raise OSError("disk gone")
        monkeypatch.setattr(runs, "list_runs", boom)
        out = status(t)
        assert (out["state"], out["basis"]) == ("held", "unknown")
        assert "disk gone" in out["reason"]
