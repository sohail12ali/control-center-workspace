"""Sequenced pub/sub over one live agent session.

A one-shot run could be polled: the process wrote to a buffer and the UI asked
for it every couple of seconds. A live conversation emits hundreds of events
per turn (token deltas, tool calls, thinking blocks), and the browser has to
see them as they happen — which means a push channel, and over `http.server`
that means Server-Sent Events.

SSE reconnects. A laptop sleeps, a tab reloads mid-turn. So every event carries
a monotonic `seq` and a subscriber resumes with `?from=<seq>`, receiving
exactly what it missed, in order, once. That property is the reason this module
exists; the rest is bookkeeping around it.

Two stores, deliberately different:

    the ring    the last RING_MAX events, in memory, for reconnect
    the jsonl   every event, on disk, for replay after the process is gone

A reconnect inside the ring is exact. One from before the ring's start cannot
be — those events are on disk but the ring no longer proves they're contiguous
with what follows — so `subscribe()` emits a `stream.reset` telling the client
to re-fetch the transcript and resubscribe from the head. Being honest about
the gap is cheaper than a UI that quietly loses a tool call.

Threading: one writer (the session's reader thread), any number of readers
(one per open SSE request, each on its own ThreadingHTTPServer thread). Every
mutation notifies the condition — including `close()`, so a reader blocked on
an idle session wakes when the session ends instead of sitting until timeout.
"""

import json
import threading
from collections import deque

# Enough to cover a reload during a long turn without letting one runaway
# session hold the whole board's memory. Overrunning it is recoverable: the
# client re-fetches the transcript (see stream.reset).
RING_MAX = 4000

# Proxies and browsers both drop an idle connection; an SSE comment costs
# nothing and keeps it open.
HEARTBEAT_SECS = 20.0


def replay_file(path):
    """Parse a transcript off disk, tolerating a torn final line.

    A killed process leaves a half-written last line; everything before it is
    still good, so a bad line is skipped rather than failing the whole replay.
    """
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out


def sse_pack(event):
    """One event as an SSE frame. `id:` is what the browser sends back as
    Last-Event-ID, which is how a reconnect knows where it got to."""
    return "id: %d\ndata: %s\n\n" % (event.get("seq", 0), json.dumps(event, ensure_ascii=False))


class Stream:
    """The event log of one session: append-only, sequenced, resumable."""

    def __init__(self, session_id, path=None):
        self.session_id = session_id
        self.path = path
        self._cv = threading.Condition()
        self._ring = deque(maxlen=RING_MAX)
        self._seq = 0
        self._closed = False
        # The seq of the oldest event still in the ring. Cheaper than
        # inspecting the deque, and correct while empty.
        self._first_in_ring = 1
        self._fh = None
        if path is not None:
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Line-buffered append: one JSON object per line, so a crashed
            # board still leaves a readable prefix.
            self._fh = open(path, "a", encoding="utf-8", buffering=1)

    # -- write ---------------------------------------------------------------
    def publish(self, event):
        """Stamp `event` with the next seq, persist it, wake subscribers."""
        with self._cv:
            if self._closed:
                # A late event from a reader thread that hasn't noticed the
                # close. Dropping it is right: every subscriber has already
                # observed the stream's final seq.
                return event
            self._seq += 1
            event = dict(event)
            event["seq"] = self._seq
            # Against the deque's OWN maxlen, so a stream with a different
            # ring size still tracks what it dropped.
            if len(self._ring) == self._ring.maxlen:
                self._first_in_ring += 1
            self._ring.append(event)
            if self._fh is not None:
                try:
                    self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
                except (OSError, ValueError):
                    # Losing the durable copy must not stop the live stream —
                    # the UI is watching, and that's the urgent half.
                    pass
            self._cv.notify_all()
            return event

    def close(self):
        """No more events will ever arrive. Wakes every blocked subscriber."""
        with self._cv:
            if self._closed:
                return
            self._closed = True
            if self._fh is not None:
                try:
                    self._fh.close()
                except OSError:
                    pass
                self._fh = None
            self._cv.notify_all()

    # -- read ----------------------------------------------------------------
    @property
    def head(self):
        with self._cv:
            return self._seq

    @property
    def closed(self):
        with self._cv:
            return self._closed

    def since(self, from_seq):
        """`(events after from_seq, gap)` — a snapshot, without blocking."""
        with self._cv:
            if from_seq < self._first_in_ring - 1:
                return [], True
            return [e for e in self._ring if e["seq"] > from_seq], False

    def subscribe(self, from_seq=0):
        """Yield SSE frames for every event after `from_seq`, blocking until
        the stream closes. Emits a heartbeat comment while idle so an
        intermediary doesn't reap the connection."""
        missed, gap = self.since(from_seq)
        if gap:
            yield sse_pack({"type": "stream.reset", "seq": from_seq,
                            "reason": "reconnect predates the retained ring"})
            missed, _ = self.since(0)
        for ev in missed:
            yield sse_pack(ev)
            from_seq = max(from_seq, ev["seq"])

        while True:
            with self._cv:
                if self._closed and self._seq <= from_seq:
                    return
                pending = [e for e in self._ring if e["seq"] > from_seq]
                if not pending:
                    self._cv.wait(timeout=HEARTBEAT_SECS)
                    pending = [e for e in self._ring if e["seq"] > from_seq]
                    if not pending:
                        if self._closed:
                            return
                        yield ": ping\n\n"
                        continue
            for ev in pending:
                yield sse_pack(ev)
                from_seq = max(from_seq, ev["seq"])
