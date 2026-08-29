"""Questions / bugs / todos.

The one behaviour worth stating out loud: `blockers()` is what a release gate
reads, and each kind decides for itself what blocking means — a critical
question blocks until answered, a critical bug blocks until verified, and a
todo never blocks at all. Those three rules are the point of this file.
"""

import pytest

from server import tickets, trackers


@pytest.fixture
def ticket(repo):
    tickets.create(repo, "CC-T001", "A ticket")
    return repo


class TestAdd:
    @pytest.mark.parametrize("kind,prefix", [
        ("questions", "Q"), ("bugs", "D-"), ("todos", "TD-"),
    ])
    def test_ids_follow_the_kind_format_and_increment(self, ticket, kind, prefix):
        first = trackers.add(ticket, "CC-T001", kind, "one")
        second = trackers.add(ticket, "CC-T001", kind, "two")
        assert first["id"] == prefix + "1"
        assert second["id"] == prefix + "2"

    def test_ids_do_not_reuse_after_removal(self, ticket):
        # Reusing D-2 would silently re-point any artifact that cited it.
        trackers.add(ticket, "CC-T001", "bugs", "one")
        trackers.add(ticket, "CC-T001", "bugs", "two")
        trackers.remove(ticket, "CC-T001", "bugs", "D-2")
        assert trackers.add(ticket, "CC-T001", "bugs", "three")["id"] == "D-3"

    def test_ids_do_not_reuse_after_removing_every_item(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "one")
        trackers.remove(ticket, "CC-T001", "questions", "Q1")
        assert trackers.list_items(ticket, "CC-T001", "questions") == []
        assert trackers.add(ticket, "CC-T001", "questions", "two")["id"] == "Q2"

    def test_counter_survives_a_reload(self, ticket):
        trackers.add(ticket, "CC-T001", "todos", "one")
        trackers.remove(ticket, "CC-T001", "todos", "TD-1")
        # Fresh read from disk — the counter must be persisted, not in memory.
        assert trackers.load(ticket, "CC-T001", "todos")["meta"]["seq"] == 1
        assert trackers.add(ticket, "CC-T001", "todos", "two")["id"] == "TD-2"

    def test_legacy_file_without_a_counter_resumes_above_max(self, ticket):
        # A tracker written before the counter existed still must not collide.
        data = trackers.load(ticket, "CC-T001", "bugs")
        data["items"] = [{"id": "D-7", "status": "open", "text": "old"}]
        data["meta"].pop("seq", None)
        trackers._save(ticket, "CC-T001", "bugs", data)
        assert trackers.add(ticket, "CC-T001", "bugs", "new")["id"] == "D-8"

    def test_each_kind_gets_its_own_field_shape(self, ticket):
        q = trackers.add(ticket, "CC-T001", "questions", "why?")
        b = trackers.add(ticket, "CC-T001", "bugs", "broken")
        t = trackers.add(ticket, "CC-T001", "todos", "tidy")
        assert "answer" in q and "severity" not in q
        assert "expected" in b and "actual" in b
        assert "due" in t and "context" in t

    def test_everything_starts_open(self, ticket):
        for kind in trackers.VALID_KINDS:
            assert trackers.add(ticket, "CC-T001", kind, "x")["status"] == "open"

    def test_extra_fields_are_honoured(self, ticket):
        b = trackers.add(ticket, "CC-T001", "bugs", "x", severity="critical", phase="build")
        assert b["severity"] == "critical" and b["phase"] == "build"

    @pytest.mark.parametrize("kind", ["gaps", "critique", "nonsense"])
    def test_reserved_and_unknown_kinds_are_refused(self, ticket, kind):
        with pytest.raises(ValueError):
            trackers.add(ticket, "CC-T001", kind, "x")


class TestListAndUpdate:
    def test_status_filter(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "one")
        trackers.add(ticket, "CC-T001", "questions", "two")
        trackers.update(ticket, "CC-T001", "questions", "Q1", status="resolved")

        assert len(trackers.list_items(ticket, "CC-T001", "questions")) == 2
        open_ = trackers.list_items(ticket, "CC-T001", "questions", status="open")
        assert [i["id"] for i in open_] == ["Q2"]

    def test_update_persists(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "why?")
        trackers.update(ticket, "CC-T001", "questions", "Q1",
                        status="resolved", answer="because")
        stored = trackers.list_items(ticket, "CC-T001", "questions")[0]
        assert stored["answer"] == "because"

    def test_update_unknown_item_raises(self, ticket):
        with pytest.raises(KeyError):
            trackers.update(ticket, "CC-T001", "bugs", "D-99", status="fixed")

    def test_remove_returns_the_removed_item(self, ticket):
        trackers.add(ticket, "CC-T001", "todos", "tidy")
        assert trackers.remove(ticket, "CC-T001", "todos", "TD-1")["text"] == "tidy"
        assert trackers.list_items(ticket, "CC-T001", "todos") == []

    def test_remove_unknown_item_raises(self, ticket):
        with pytest.raises(KeyError):
            trackers.remove(ticket, "CC-T001", "todos", "TD-99")


class TestBlockers:
    def test_clean_ticket_has_none(self, ticket):
        assert trackers.blockers(ticket, "CC-T001") == {}

    def test_non_critical_items_never_block(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "minor", priority="medium")
        trackers.add(ticket, "CC-T001", "bugs", "cosmetic", severity="low")
        assert trackers.blockers(ticket, "CC-T001") == {}

    def test_critical_open_question_blocks(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "which db?", priority="critical")
        assert list(trackers.blockers(ticket, "CC-T001")) == ["questions"]

    def test_answering_a_critical_question_clears_it(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "which db?", priority="critical")
        trackers.update(ticket, "CC-T001", "questions", "Q1", status="resolved")
        assert trackers.blockers(ticket, "CC-T001") == {}

    def test_critical_bug_blocks_until_verified_not_merely_fixed(self, ticket):
        # "fixed" is a claim; "verified" is evidence. The gate wants evidence.
        trackers.add(ticket, "CC-T001", "bugs", "data loss", severity="critical")
        trackers.update(ticket, "CC-T001", "bugs", "D-1", status="fixed")
        assert list(trackers.blockers(ticket, "CC-T001")) == ["bugs"]

        trackers.update(ticket, "CC-T001", "bugs", "D-1", status="verified")
        assert trackers.blockers(ticket, "CC-T001") == {}

    def test_todos_never_block_even_when_critical(self, ticket):
        trackers.add(ticket, "CC-T001", "todos", "rewrite everything", priority="critical")
        assert trackers.blockers(ticket, "CC-T001") == {}

    def test_reports_every_blocking_kind_at_once(self, ticket):
        trackers.add(ticket, "CC-T001", "questions", "q", priority="critical")
        trackers.add(ticket, "CC-T001", "bugs", "b", severity="critical")
        assert set(trackers.blockers(ticket, "CC-T001")) == {"questions", "bugs"}
