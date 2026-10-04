"""Minimal change-notification bus, scoped to MCP resource subscribers only
(T-017 FR-3 / A5, decision-log a8 — task 1e-4, greenfield: no prior
change-bus mechanism exists in this codebase).

## Scope: MCP only, never the console board UI

a8 confirms UI live-sync (EventSource/WebSocket push to the board) is
out of scope for T-017. This bus exists so an MCP client that has called
`resources/subscribe` on a ticket learns its context changed, nothing more —
the board's own refresh mechanism is untouched and does not read this module.

## Why pull, not push

The stdio transport this ticket ships (Phase 1) is one blocking read loop —
`Server.serve_forever` reads a line, handles it, writes a reply, repeats.
There is no idle-connection thread to push an unsolicited notification down
mid-wait. So a subscription records interest, a mutation records a change,
and the *next* time that session's own request loop turns over, it drains and
forwards whatever accumulated. Phase 2's HTTP transport (2a, SSE) is exactly
the case that lets a session be notified between requests; this bus's shape
(subscribe/publish/drain) does not need to change to support that later — it
already stores changes independently of when they are collected.

## Process-local, one instance per running console process

A stdio MCP session already is a whole process, so a module-level singleton
is the right scope. An HTTP-served console (Phase 2's 2a) is one process
handling multiple sessions, and the same shared bus is precisely what lets a
mutation from session A reach a subscriber in session B.
"""

import threading
import time


class Bus:
    """Subscribe a session to a URI; publish a change to a URI; drain what
    accumulated for one session since its last drain."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subscriptions = {}  # session_id -> {uri, ...}
        self._pending = {}        # session_id -> [{"uri": ..., "ts": ...}, ...]

    def subscribe(self, session_id, uri):
        with self._lock:
            self._subscriptions.setdefault(session_id, set()).add(uri)

    def unsubscribe(self, session_id, uri=None):
        """Drop one subscription, or (uri=None) every subscription for this
        session — e.g. on session end."""
        with self._lock:
            if uri is None:
                self._subscriptions.pop(session_id, None)
            else:
                self._subscriptions.get(session_id, set()).discard(uri)

    def subscribed(self, session_id, uri):
        with self._lock:
            return uri in self._subscriptions.get(session_id, set())

    def publish(self, uri):
        """Record that `uri` changed, for every session currently subscribed
        to it. A publish with no subscribers is a no-op, not an error — most
        mutations in a console with no MCP client attached have nobody to
        tell."""
        with self._lock:
            now = time.time()
            for session_id, uris in self._subscriptions.items():
                if uri in uris:
                    self._pending.setdefault(session_id, []).append(
                        {"uri": uri, "ts": now})

    def drain(self, session_id):
        """Everything queued for `session_id` since its last drain, oldest
        first. Clears the queue — a notification is delivered at most once."""
        with self._lock:
            return self._pending.pop(session_id, [])


#: The process-wide bus every MCP `Server` session (and any future HTTP
#: transport sharing the process, per 2a) publishes to and drains from.
_default = Bus()


def default():
    return _default
