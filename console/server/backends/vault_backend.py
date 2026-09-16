"""`VaultBackend` — the sole Backend SPI adapter (T-017 FR-5, 2b).

Delegation only, per `base.py`'s own docstring: every method forwards to the
existing `tickets.py`/`trackers.py` logic, none of it duplicated or
rewritten here. This is the one and only adapter registered in this ticket
(BR-4) — no Jira/Azure/Linear/GitHub Issues code exists anywhere in this
module or this ticket's diff (2b-6).

## `ready` and `claim`: schema already exists, verb wiring is Phase 3

`claimed_by`/`claimed_at` (1d-1) and the non-blocking `comments` tracker kind
(1d-4) both landed in Phase 1. `ready`'s unblocked-and-unclaimed filter and
`claim`'s race-safety guard are real logic, not thin passthroughs, so they
live here now even though the `ready`/`claim` *verb handlers* that call this
backend don't land until Phase 3's 3a — a verb handler with nothing behind it
yet would be a stub, and this ticket has none of those left after Phase 1.
`claim`'s race-safety (task 3a-5, Risk R2) now lives in `tickets.set_claim`
itself — a `tomlio.atomic_update` read-modify-write under one lock file,
replacing the plain last-write-wins `load()`+`_save()` pair this method
originally delegated to. `VaultBackend.claim` stays thin delegation either
way; only `tickets.set_claim`'s implementation changed.

## A future non-vault adapter (2b-7)

A Jira/Azure/Linear/GitHub Issues adapter, if one is ever built, would sync
identity/status/comments *alongside* the vault — the vault stays the durable
source of ticket artifacts and this SPI's `create`/`move`/`set` — not replace
this lane. (plan.md line 176.)
"""

from datetime import date

from . import base
from .. import tickets as tickets_mod
from .. import trackers as trackers_mod


class VaultBackend(base.Backend):
    def list(self, repo_root, kind=None, stage=None, owner=None):
        return tickets_mod.list_tickets(repo_root, kind=kind, stage=stage, owner=owner)

    def show(self, repo_root, ticket_id):
        return tickets_mod.load(repo_root, ticket_id)

    def create(self, repo_root, ticket_id, title, **fields):
        return tickets_mod.create(repo_root, ticket_id, title, **fields)

    def move(self, repo_root, ticket_id, stage):
        return tickets_mod.move(repo_root, ticket_id, stage)

    def set(self, repo_root, ticket_id, field, value):
        return tickets_mod.set_field(repo_root, ticket_id, field, value)

    def comment(self, repo_root, ticket_id, text, **fields):
        return trackers_mod.add(repo_root, ticket_id, "comments", text, **fields)

    def ready(self, repo_root, kind=None, stage=None, owner=None):
        """Unblocked and unclaimed (FR-7, decision-log a6) — blocked comes
        from the same `trackers.blockers` every other blocker-aware surface
        (e.g. the board card) already reads; claimed comes from the
        `claimed_by` field 1d-1 added. An empty result is a plain empty list,
        never an error (Edge Case §8)."""
        out = []
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind, stage=stage, owner=owner):
            if ticket.get("claimed_by"):
                continue
            if trackers_mod.blockers(repo_root, ticket["id"]):
                continue
            out.append(ticket)
        return out

    def claim(self, repo_root, ticket_id, claimed_by):
        """Thin delegation to `tickets.set_claim` (2b scope). Race-safety
        against two concurrent claims lives in `set_claim` itself (3a-5);
        a conflicting claim propagates as `tickets.ClaimConflictError`."""
        return tickets_mod.set_claim(repo_root, ticket_id, claimed_by,
                                     claimed_at=date.today().isoformat())


#: The one adapter this ticket registers (2b-3, BR-4). A module-level
#: singleton, matching `bus.default()`'s shape — every caller wants the same
#: vault, not a fresh instance per call.
_default = VaultBackend()


def default():
    return _default
