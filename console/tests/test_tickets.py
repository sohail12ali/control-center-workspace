"""Ticket lifecycle. These are the writes the whole board depends on, so the
cases here are mostly about what must be *refused*: a bad id, a lane that
doesn't exist on that board, an edit to an identity field."""

import os
import threading

import pytest

from server import tickets, tomlio


def _create(repo, tid="CC-T001", **kw):
    return tickets.create(repo, tid, kw.pop("title", "A ticket"), **kw)


class TestCreate:
    def test_seeds_first_lane_and_defaults(self, repo):
        t = _create(repo, owner="Sam")
        assert t["stage"] == "open"          # first lane in board order
        assert t["status"] == "active"
        assert t["priority"] == "medium"
        assert t["owner"] == "Sam"
        assert t["tags"] == [] and t["links"] == []

    def test_writes_ticket_toml_where_the_board_looks(self, repo):
        _create(repo)
        path = os.path.join(repo, "knowledge-center", "artifacts", "CC-T001", "ticket.toml")
        assert tomlio.load(path)["ticket"]["id"] == "CC-T001"

    def test_scaffolds_all_three_trackers(self, repo):
        _create(repo)
        folder = os.path.join(repo, "knowledge-center", "artifacts", "CC-T001")
        for kind in ("questions", "bugs", "todos"):
            assert os.path.isfile(os.path.join(folder, "CC-T001-%s.toml" % kind))

    def test_refuses_duplicate(self, repo):
        _create(repo)
        with pytest.raises(FileExistsError):
            _create(repo)

    @pytest.mark.parametrize("bad", ["lower", "1TICKET", "A", "Has Space", "", "x" * 40])
    def test_rejects_ids_outside_the_pattern(self, repo, bad):
        with pytest.raises(ValueError):
            tickets.create(repo, bad, "t")

    def test_rejects_unknown_board_kind(self, repo):
        with pytest.raises(ValueError):
            _create(repo, kind="nonexistent")

    def test_garbage_priority_normalises_rather_than_raising(self, repo):
        # A hand-edited typo must not produce an un-renderable card.
        assert _create(repo, priority="URGENT!!")["priority"] == "medium"

    def test_priority_is_case_insensitive(self, repo):
        assert _create(repo, priority="HIGH")["priority"] == "high"


class TestMove:
    def test_moves_between_configured_lanes(self, repo):
        _create(repo)
        assert tickets.move(repo, "CC-T001", "in-progress")["stage"] == "in-progress"
        assert tickets.load(repo, "CC-T001")["stage"] == "in-progress"

    def test_rejects_a_lane_the_board_does_not_have(self, repo):
        _create(repo)
        with pytest.raises(ValueError) as exc:
            tickets.move(repo, "CC-T001", "verify")
        assert "valid" in str(exc.value)      # the error lists the real lanes

    def test_missing_ticket_raises(self, repo):
        with pytest.raises(FileNotFoundError):
            tickets.move(repo, "CC-T999", "open")


class TestEdit:
    def test_set_field_writes_through(self, repo):
        _create(repo)
        tickets.set_field(repo, "CC-T001", "owner", "Alex")
        assert tickets.load(repo, "CC-T001")["owner"] == "Alex"

    def test_set_field_rejects_unknown_field(self, repo):
        _create(repo)
        with pytest.raises(ValueError):
            tickets.set_field(repo, "CC-T001", "nonsense", "x")

    def test_patch_sets_several_at_once(self, repo):
        _create(repo)
        out = tickets.patch(repo, "CC-T001", {"owner": "Alex", "priority": "high"})
        assert (out["owner"], out["priority"]) == ("Alex", "high")

    @pytest.mark.parametrize("field", ["id", "kind", "created", "stage"])
    def test_patch_refuses_identity_and_stage_fields(self, repo, field):
        # stage has its own validated move(); id/kind/created are identity.
        _create(repo)
        with pytest.raises(ValueError):
            tickets.patch(repo, "CC-T001", {field: "x"})

    def test_patch_refuses_empty_title(self, repo):
        _create(repo)
        with pytest.raises(ValueError):
            tickets.patch(repo, "CC-T001", {"title": "   "})

    def test_patch_is_all_or_nothing(self, repo):
        _create(repo, owner="Sam")
        with pytest.raises(ValueError):
            tickets.patch(repo, "CC-T001", {"owner": "Alex", "id": "OTHER"})
        assert tickets.load(repo, "CC-T001")["owner"] == "Sam"


class TestClaim:
    """T-017 FR-8 / decision-log a3: `claimed_by`/`claimed_at` are a distinct
    field pair from `owner`, set only through `set_claim`."""

    def test_created_ticket_starts_unclaimed(self, repo):
        t = _create(repo, owner="Sam")
        assert t["claimed_by"] == "" and t["claimed_at"] == ""

    def test_set_claim_sets_both_fields(self, repo):
        _create(repo)
        out = tickets.set_claim(repo, "CC-T001", "agent-1", "2026-09-16T00:00:00Z")
        assert out["claimed_by"] == "agent-1"
        assert out["claimed_at"] == "2026-09-16T00:00:00Z"

    def test_set_claim_leaves_owner_untouched(self, repo):
        _create(repo, owner="Sam")
        out = tickets.set_claim(repo, "CC-T001", "agent-1", "2026-09-16T00:00:00Z")
        assert out["owner"] == "Sam"

    def test_empty_claimed_by_releases_the_claim(self, repo):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", "2026-09-16T00:00:00Z")
        out = tickets.set_claim(repo, "CC-T001", "")
        assert out["claimed_by"] == "" and out["claimed_at"] == ""

    def test_an_older_ticket_toml_without_claim_fields_still_loads(self, repo):
        _create(repo)
        path = os.path.join(repo, "knowledge-center", "artifacts", "CC-T001", "ticket.toml")
        data = tomlio.load(path)
        del data["ticket"]["claimed_by"]
        del data["ticket"]["claimed_at"]
        tomlio.atomic_write(path, data)
        t = tickets.load(repo, "CC-T001")
        assert t["claimed_by"] == "" and t["claimed_at"] == ""

    def test_conflicting_claim_is_refused_by_name(self, repo):
        """3a-5: a second identity claiming an already-claimed ticket is
        refused, not silently overwritten."""
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1")
        with pytest.raises(tickets.ClaimConflictError) as exc:
            tickets.set_claim(repo, "CC-T001", "agent-2")
        assert "agent-1" in str(exc.value)
        # The original claim is untouched, not half-overwritten.
        assert tickets.load(repo, "CC-T001")["claimed_by"] == "agent-1"

    def test_reclaim_by_same_identity_is_a_no_op_success(self, repo):
        """3a-6: re-claiming by the identity that already holds it does not
        error, and refreshes claimed_at."""
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", "2026-09-16T00:00:00Z")
        out = tickets.set_claim(repo, "CC-T001", "agent-1", "2026-09-16T01:00:00Z")
        assert out["claimed_by"] == "agent-1"
        assert out["claimed_at"] == "2026-09-16T01:00:00Z"

    def test_concurrent_claims_by_different_identities_exactly_one_succeeds(self, repo):
        """3a-5/3a-8: race-safety under real concurrent calls, not just a
        sequential check — two threads hammer the same unclaimed ticket with
        different identities; exactly one must win and the other must see
        ClaimConflictError, deterministically, every run."""
        _create(repo)
        n = 8
        results = [None] * n

        def _try_claim(i):
            try:
                tickets.set_claim(repo, "CC-T001", "agent-%d" % i)
                results[i] = "ok"
            except tickets.ClaimConflictError:
                results[i] = "conflict"

        threads = [threading.Thread(target=_try_claim, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count("ok") == 1
        assert results.count("conflict") == n - 1
        final = tickets.load(repo, "CC-T001")
        winner = "agent-%d" % results.index("ok")
        assert final["claimed_by"] == winner


class TestList:
    def test_lists_and_filters(self, repo):
        _create(repo, "CC-T001", owner="Sam")
        _create(repo, "CC-T002", owner="Alex")
        tickets.move(repo, "CC-T002", "blocked")

        assert len(tickets.list_tickets(repo)) == 2
        assert [t["id"] for t in tickets.list_tickets(repo, owner="Alex")] == ["CC-T002"]
        assert [t["id"] for t in tickets.list_tickets(repo, stage="open")] == ["CC-T001"]
        assert tickets.list_tickets(repo, kind="investigations") == []

    def test_skips_underscore_dirs(self, repo):
        # _template/ and _shared/ are conventions, not tickets.
        os.makedirs(os.path.join(repo, "knowledge-center", "artifacts", "_template"))
        _create(repo)
        assert [t["id"] for t in tickets.list_tickets(repo)] == ["CC-T001"]

    def test_empty_artifacts_dir_is_not_an_error(self, repo):
        assert tickets.list_tickets(repo) == []

    def test_load_missing_ticket_returns_none(self, repo):
        assert tickets.load(repo, "CC-T404") is None
