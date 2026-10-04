"""`VaultBackend` (T-017 FR-5, 2b) — the sole Backend SPI adapter, round-tripped
against real vault fixtures (2b-5) for all 8 methods, plus the ticket_move
verb-handler rewiring (2b-4) and the zero-other-adapters check (2b-6)."""

import os

from server import backends, tickets, trackers, verb_handlers
from server.backends import Backend, VaultBackend, default_backend


class TestAllEightMethodsRoundTrip:
    def test_is_a_backend_and_the_registered_default(self):
        assert isinstance(default_backend(), Backend)
        assert isinstance(default_backend(), VaultBackend)
        # Same singleton every call — one adapter instance, not one per call.
        assert default_backend() is default_backend()

    def test_create_then_show_round_trips(self, repo):
        backend = VaultBackend()
        created = backend.create(repo, "T-900", "A backend-created ticket")
        shown = backend.show(repo, "T-900")
        assert shown["id"] == "T-900"
        assert shown["title"] == created["title"]

    def test_show_missing_ticket_is_none(self, repo):
        assert VaultBackend().show(repo, "T-nope") is None

    def test_list_matches_tickets_module(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-901", "One")
        backend.create(repo, "T-902", "Two")
        assert [t["id"] for t in backend.list(repo)] == \
            [t["id"] for t in tickets.list_tickets(repo)]

    def test_move_writes_through_to_ticket_toml(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-903", "Movable")
        backend.move(repo, "T-903", "in-progress")
        assert tickets.load(repo, "T-903")["stage"] == "in-progress"

    def test_set_writes_through(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-904", "Settable")
        backend.set(repo, "T-904", "owner", "sohail")
        assert tickets.load(repo, "T-904")["owner"] == "sohail"

    def test_comment_appends_to_the_comments_tracker(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-905", "Commentable")
        backend.comment(repo, "T-905", "hello", author="agent")
        items = trackers.list_items(repo, "T-905", "comments")
        assert len(items) == 1
        assert items[0]["text"] == "hello"
        assert items[0]["author"] == "agent"

    def test_claim_sets_claimed_by_and_at(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-906", "Claimable")
        backend.claim(repo, "T-906", "agent-1")
        loaded = tickets.load(repo, "T-906")
        assert loaded["claimed_by"] == "agent-1"
        assert loaded["claimed_at"]

    def test_ready_excludes_claimed_and_blocked(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-907", "Ready one")
        backend.create(repo, "T-908", "Claimed one")
        backend.create(repo, "T-909", "Blocked one")
        backend.claim(repo, "T-908", "agent-1")
        trackers.add(repo, "T-909", "bugs", "breaks everything", severity="critical")
        ready_ids = {t["id"] for t in backend.ready(repo)}
        assert ready_ids == {"T-907"}

    def test_ready_is_an_empty_list_not_an_error_when_none_available(self, repo):
        backend = VaultBackend()
        backend.create(repo, "T-910", "Only ticket")
        backend.claim(repo, "T-910", "agent-1")
        assert backend.ready(repo) == []


class TestTicketMoveUsesTheBackend(object):
    def test_ticket_move_verb_handler_routes_through_vault_backend(self, repo, monkeypatch):
        tickets.create(repo, "T-911", "Routed")
        calls = []
        real_move = VaultBackend.move

        def spy(self, repo_root, ticket_id, stage):
            calls.append((ticket_id, stage))
            return real_move(self, repo_root, ticket_id, stage)

        monkeypatch.setattr(VaultBackend, "move", spy)
        result = verb_handlers.ticket_move(repo, ticket="T-911", stage="in-progress")
        assert calls == [("T-911", "in-progress")]
        assert result["stage"] == "in-progress"


class TestNoOtherAdapterExists:
    """2b-6: a grep-based check that no Jira/Azure/Linear/GitHub Issues code
    exists anywhere in the backends package — vault is the only adapter."""

    def test_backends_package_defines_no_other_adapter_class(self):
        """The docstrings *name* Jira/Azure/Linear/GitHub Issues (to say they
        are future, unimplemented possibilities) — that's documentation, not
        an adapter. What must never exist is a `class ...Backend` for any of
        them, or a second registration alongside `VaultBackend`."""
        backends_dir = os.path.dirname(os.path.abspath(backends.__file__))
        forbidden = ("jira", "azure", "linear", "github")
        for name in os.listdir(backends_dir):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(backends_dir, name), encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip().lower()
                    if stripped.startswith("class ") and "backend" in stripped:
                        for word in forbidden:
                            assert word not in stripped, (
                                "%s defines a forbidden adapter class: %s" % (name, line))

    def test_exactly_one_backend_subclass_in_the_package(self):
        import inspect

        from server.backends import base as base_mod
        from server.backends import vault_backend as vault_backend_mod

        modules = (base_mod, vault_backend_mod)
        subclasses = set()
        for mod in modules:
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Backend) and obj is not Backend:
                    subclasses.add(obj)
        assert subclasses == {VaultBackend}
