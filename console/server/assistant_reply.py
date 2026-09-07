"""T-006: the reply watcher — what makes a reply audible and copyable.

This is FR-8, deferred out of T-004 because speaking a reply is only testable
once there is something to speak with. Two jobs, and the second is the one
that fixes a visible gap:

1. **Speak the finished reply**, through the desktop shell's synthesiser, when
   the user has not muted it.
2. **Record it as the last reply**, which is what `copy that` reads. Until
   now `assistant.write_last_reply` had no caller at all, so that command
   could only ever answer "there is no last reply to copy yet" — honestly, but
   uselessly.

## Why it polls instead of subscribing

`Stream.subscribe` yields SSE-*formatted* frames, because its consumer is an
HTTP response. A watcher inside the server wants the events themselves, and
re-parsing text this process just serialised would be a silly round trip.
`Stream.since(seq)` returns the raw events, so the watcher polls it on a short
interval. One assistant chat produces a handful of events per turn, so the
cost is nil, and the alternative — a second subscriber API on `Stream` — would
be new surface to keep in step with the tested one.

## Why it publishes a `reply` event

The trimmed, spoken form of a reply is this module's own product: it is not in
the transcript and no other event carries it. Publishing it puts it on the
same stream everything else uses, so the tray and any future UI read one
source rather than two.
"""

import threading
import time

from . import agent_manager, assistant, assistant_config, native_bridge

#: How often to look for new events. A turn's reply arrives once, so latency
#: here is the delay before speech starts — a quarter second is imperceptible
#: and costs one dictionary lookup.
POLL_SECONDS = 0.25

#: Give up on a chat this long after it stops being alive, so a watcher never
#: outlives what it was watching.
IDLE_EXIT_SECONDS = 5.0

#: One watcher per chat id. A second `say` to the same chat must not start a
#: second watcher, or every reply would be spoken twice.
_watchers = {}
_lock = threading.Lock()


def spoken_form(text, cap):
    """The part of a reply worth hearing.

    First paragraph only, markdown stripped, capped. A model asked to be
    terse still emits headings and bullet lists, and reading `##` and `*`
    aloud is worse than reading nothing.
    """
    if not text:
        return ""
    para = text.strip().split("\n\n", 1)[0]
    out = []
    for line in para.splitlines():
        line = line.strip()
        # Leading markdown furniture: headings, list bullets, quotes.
        while line[:1] in ("#", ">", "-", "*", "+"):
            line = line[1:].lstrip()
        out.append(line)
    plain = " ".join(p for p in out if p)
    # Inline emphasis and code fences, left as their text.
    for ch in ("**", "__", "`", "*", "_"):
        plain = plain.replace(ch, "")
    plain = " ".join(plain.split())
    if cap and len(plain) > cap:
        cut = plain[:cap]
        stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        plain = cut[: stop + 1] if stop > cap // 2 else cut
    return plain.strip()


def watch(repo_root, sid):
    """Start watching `sid`, unless it is already watched."""
    with _lock:
        if sid in _watchers and _watchers[sid].is_alive():
            return False
        thread = threading.Thread(
            target=_run, args=(repo_root, sid), name="assistant-reply-%s" % sid,
            daemon=True)
        _watchers[sid] = thread
        thread.start()
        return True


def watching(sid):
    with _lock:
        t = _watchers.get(sid)
        return bool(t and t.is_alive())


def _run(repo_root, sid):
    seq = 0
    gone_since = None
    while True:
        session = agent_manager.get(sid)
        if session is None:
            return
        if not session.alive:
            # Drain what is left, then stop: a reply that landed as the
            # session ended still deserves to be spoken and recorded.
            gone_since = gone_since or time.time()
            if time.time() - gone_since > IDLE_EXIT_SECONDS:
                return
        try:
            events, _gap = session.stream.since(seq)
        except Exception:  # noqa: BLE001
            return
        for event in events:
            seq = max(seq, event.get("seq", seq))
            try:
                _handle(repo_root, session, event)
            except Exception:  # noqa: BLE001
                # A watcher that dies takes speech and `copy that` with it for
                # the rest of the session, which is a worse outcome than
                # skipping one event.
                pass
        time.sleep(POLL_SECONDS)


def _handle(repo_root, session, event):
    kind = event.get("type")
    if kind != "text.done":
        return
    text = event.get("text") or ""
    if not text.strip():
        return

    # Recorded first, and unconditionally: `copy that` must work whether or
    # not the reply was spoken, and whether or not a shell is running.
    assistant.write_last_reply(repo_root, text)

    settings = assistant_config.settings(repo_root)
    spoken = spoken_form(text, settings.get("reply_chars") or 0)
    session.stream.publish({"type": "reply", "text": spoken, "full_chars": len(text)})

    if not settings.get("speak"):
        return
    if not spoken:
        return
    result = native_bridge.speak(repo_root, spoken)
    if not result.get("ok"):
        # Not an error worth interrupting anything for: no shell, or no
        # synthesiser. The reply is still on screen and still copyable.
        session.stream.publish({
            "type": "notice",
            "text": "Could not read the reply aloud: %s" % result.get("reason", "unknown"),
        })
