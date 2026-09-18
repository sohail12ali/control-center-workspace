"""Backend SPI — the ticket-storage abstraction (T-017 FR-5, decision-log a4).

## Why this, and why its own module

GROUND-stage reading of two existing modules confirmed neither is this:

- `console/server/plugins/registry.py` loads UI/HTTP *feature* modules
  (`apply(ctx)` against a `PluginContext`) — a different axis entirely
  (what the console's HTTP surface offers), not where ticket data lives.
- `console/server/trackers.py` is the CRUD *implementation* for
  questions/bugs/todos/comments against the vault's TOML files — a concrete
  backend, not the interface a backend implements.

"Backend SPI" names the abstraction those two are not: one small interface a
ticket-storage backend implements, with exactly one adapter registered today
(`VaultBackend`, delegating to `tickets.py`/`trackers.py` — lands in Phase
2's 2b). A future non-vault adapter (Jira, Azure DevOps, Linear, GitHub
Issues — none of which are implemented in this ticket) would satisfy the same
8 methods without either existing module changing shape.

## Shape

Mirrors `plugins/base.py`'s "one tiny contract" pattern rather than extending
it: a plugin's contract is `apply(ctx)`; a backend's contract is these 8
operations. Reusing `Plugin`/`PluginContext` here would wire ticket storage
into the UI-feature system it has nothing to do with.

Phase 1 (this module): the interface only, enforced by `abc.ABC` — a subclass
missing any method cannot be instantiated at all, which is a stronger and
earlier guarantee than a runtime `NotImplementedError`. Phase 2 (2b) adds the
one real implementation, `VaultBackend`.
"""

from abc import ABC, abstractmethod


class BackendError(ValueError):
    """A Backend operation failed in a way its caller should report by name
    (e.g. a conflicting claim), distinct from a bug in the interface itself."""


class Backend(ABC):
    """A ticket-storage backend: list/show/create/move/set the ticket
    itself, plus the three verb-shaped mutations (comment/ready/claim) that
    read or write alongside it. Every method takes `repo_root` first, matching
    every other module in this package — a backend is handed a workspace root,
    not a persistent connection it manages itself.
    """

    @abstractmethod
    def list(self, repo_root, kind=None, stage=None, owner=None):
        """Tickets matching the given filters. Mirrors `tickets.list_tickets`."""

    @abstractmethod
    def show(self, repo_root, ticket_id):
        """One ticket's full record, or None if it doesn't exist. Mirrors
        `tickets.load`."""

    @abstractmethod
    def create(self, repo_root, ticket_id, title, **fields):
        """Create a new ticket. Mirrors `tickets.create`."""

    @abstractmethod
    def move(self, repo_root, ticket_id, stage):
        """Move a ticket to a board lane. Mirrors `tickets.move`."""

    @abstractmethod
    def set(self, repo_root, ticket_id, field, value):
        """Set one editable ticket field. Mirrors `tickets.set_field`."""

    @abstractmethod
    def comment(self, repo_root, ticket_id, text, **fields):
        """Append a comment (T-017 FR-9). Mirrors `trackers.add(..., "comments", ...)`."""

    @abstractmethod
    def ready(self, repo_root, **filters):
        """Tickets that are unblocked and unclaimed (T-017 FR-7, decision-log a6)."""

    @abstractmethod
    def claim(self, repo_root, ticket_id, claimed_by):
        """Claim a ticket for `claimed_by`, race-safe (T-017 FR-8). Mirrors
        `tickets.set_claim`."""
