"""Owns every chat session for the life of the server process.

Sessions are process-memory state: a chat is a child process, and nothing
re-attaches to it after a restart. The event transcript is durable on disk, so
a past chat still replays read-only — it just can't be spoken to, and the UI
says so rather than offering a reply box that would fail.

Storage layout (all gitignored — a transcript can contain anything the agent
read, so it is deliberately NOT committed):

    console/.cache/agent-chats/{id}.events.jsonl   normalised event log
    console/.cache/agent-chats/{id}.log            raw CLI stdout/stderr
"""

import glob
import json
import os
import threading
import uuid

import time

from . import agent_approvals, agent_backends, agent_session
from .agent_events import replay_file


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

CHATS_REL = os.path.join("console", ".cache", "agent-chats")

_sessions = {}
_lock = threading.Lock()


def chats_dir(repo_root):
    d = os.path.join(repo_root, CHATS_REL)
    os.makedirs(d, exist_ok=True)
    return d


def _paths(repo_root, sid):
    base = os.path.join(chats_dir(repo_root), sid)
    return base + ".log", base + ".events.jsonl"


#: The port this console is bound to, set once by the agents plugin. A chat
#: started from somewhere with no request context — a verb, the scheduler —
#: still needs it, because it is what the approval hook calls home to. Without
#: it a gated tool has nowhere to raise its card.
_SERVER_PORT = 0


def set_server_port(port):
    global _SERVER_PORT
    _SERVER_PORT = int(port or 0)


def server_port():
    return _SERVER_PORT


def create(repo_root, backend_id, prompt, *, mode="", model="", skill="",
           persona="", title="", server_port=0, ticket="",
           system_append="", extra=""):
    """Start a chat and send its opening message."""
    backend = agent_backends.get(repo_root, backend_id)
    if not backend.installed:
        # The backend knows why it is unusable, and "not on PATH" is simply
        # wrong for a provider that has no binary — it sends someone off to
        # install something when the real problem is an unset key or a server
        # that is not running.
        raise ValueError("%s Pick another backend, or fix that."
                         % backend.unavailable_reason)
    text = (prompt or "").strip()
    if not text:
        raise ValueError("an opening message is required")

    sid = uuid.uuid4().hex[:12]
    log_path, _events = _paths(repo_root, sid)

    # Approval gate: a stream_json backend with gated tools gets a per-session
    # settings file installing the PreToolUse hook. Needs the server's bound
    # port so the hook can call home; without one (e.g. a CLI-launched run
    # with no live server) the gate is skipped rather than half-installed.
    settings_path = ""
    if backend.transport == "stream_json" and backend.gated_tools and server_port:
        settings_path = agent_approvals.write_settings(
            chats_dir(repo_root), sid, backend.gated_tools, server_port,
            timeout=backend.approval_timeout)

    def _on_exit(sess):
        # Unblock any question still parked on this chat — the hook processes
        # are blocked too, and a dead session can never answer them.
        agent_approvals.REGISTRY.forget(sess.id)

    sess = agent_session.build(
        sid, backend, repo_root, log_path=log_path,
        title=title or text[:80], model=model, mode=mode,
        skill=skill, persona=persona, on_exit=_on_exit,
        settings_path=settings_path, ticket=ticket,
        system_append=system_append, extra=extra)

    with _lock:
        _sessions[sid] = sess
    sess.start()

    wire = backend.compose_prompt(text, skill=skill, persona=persona,
                                  repo_root=repo_root)
    if system_append and not backend.supports_system_append_flag:
        # No flag to carry it, so the first turn's prompt has to. Only the
        # opening message needs this — everything after it is a normal
        # continuation of the same conversation, which already has the text.
        wire = system_append + "\n\n" + wire
    sess.send(wire, mode="auto", display=text)
    return sess.snapshot()


def get(sid):
    with _lock:
        return _sessions.get(sid)


def require(sid):
    sess = get(sid)
    if sess is None:
        raise FileNotFoundError(
            "no live session %r — it ended with a previous server run. Its "
            "transcript can still be replayed." % sid)
    return sess


def list_chats(repo_root):
    """Live sessions first, then any transcript on disk from a previous run.

    A past chat is listed as `replayable` so the UI can show it read-only
    instead of pretending it can be continued.
    """
    out = []
    seen = set()
    with _lock:
        for sid, sess in _sessions.items():
            snap = sess.snapshot()
            snap["replayable"] = True
            out.append(snap)
            seen.add(sid)

    for path in glob.glob(os.path.join(chats_dir(repo_root), "*.events.jsonl")):
        sid = os.path.basename(path)[: -len(".events.jsonl")]
        if sid in seen:
            continue
        meta = _meta_from_transcript(path)
        meta.update({"id": sid, "alive": False, "busy": False, "queued": [],
                     "replayable": True, "orphaned": True,
                     "resumable": _can_resume(repo_root, meta)})
        out.append(meta)

    out.sort(key=lambda s: s.get("started") or "", reverse=True)
    return out


def _meta_from_transcript(path):
    """Reconstruct enough of a dead session's identity to list it, by reading
    only the events that carry it — cheaper than replaying the whole log."""
    meta = {"title": "(recovered chat)", "agent": "", "model": "", "mode": "",
            "started": "", "ended": "", "cost_usd": 0.0, "num_turns": 0,
            "transport": "", "steerable": False,
            # What it takes to start the same conversation again: where it ran
            # and what the CLI calls it. Both were already in the transcript;
            # nothing read them back out.
            "cwd": "", "native_session_id": "", "seq": 0}
    for ev in replay_file(path):
        t = ev.get("type")
        try:
            meta["seq"] = max(meta["seq"], int(ev.get("seq") or 0))
        except (TypeError, ValueError):
            pass
        # The CLI's own id for this conversation, as seen on any event that
        # carried it. The LAST one wins: a resumed chat is issued a new id by
        # some CLIs, and it is the current one that can be resumed again.
        if ev.get("session_id"):
            meta["native_session_id"] = ev["session_id"]
        if t == "session.started":
            meta["title"] = ev.get("title") or meta["title"]
            meta["agent"] = ev.get("agent") or ""
            meta["model"] = ev.get("model") or ""
            meta["mode"] = ev.get("mode") or ""
            meta["started"] = ev.get("at") or ""
            meta["cwd"] = ev.get("cwd") or meta["cwd"]
        elif t == "turn.end":
            meta["cost_usd"] = round(meta["cost_usd"] + float(ev.get("cost_usd") or 0.0), 4)
            meta["num_turns"] += int(ev.get("num_turns") or 0)
        elif t == "session.exit":
            meta["ended"] = ev.get("at") or ""
    return meta


def _can_resume(repo_root, meta):
    """Both halves have to be true: the CLI gave us an id for this
    conversation, and its backend row says how to hand that id back."""
    if not meta.get("native_session_id"):
        return False
    try:
        return agent_backends.get(repo_root, meta.get("agent") or "").can_resume
    except (ValueError, KeyError):
        return False


def resume(repo_root, sid, *, server_port=0):
    """Pick a dead chat back up, in place.

    The same session id, the same transcript file, the same working directory
    — and the CLI's own session id handed back to it, which is what makes the
    model remember the conversation rather than being told about it. Sessions
    have always died with the console; everything needed to undo that was
    already on disk.

    Raises rather than silently starting a fresh chat: "it resumed" and "it
    began again with no memory" look identical in a chat window, and only one
    of them is what was asked for.
    """
    live = get(sid)
    if live is not None and live.alive:
        return live.snapshot()

    _log, events_path = _paths(repo_root, sid)
    if not os.path.isfile(events_path):
        raise FileNotFoundError("no transcript for %r" % sid)
    meta = _meta_from_transcript(events_path)
    if not meta.get("native_session_id"):
        raise ValueError(
            "this chat has no CLI session id in its transcript, so there is "
            "nothing to resume — start a new chat instead")
    backend = agent_backends.get(repo_root, meta.get("agent") or "")
    if not backend.can_resume:
        raise ValueError(
            "%s cannot resume a past chat: no resume flags in its "
            "console/config/agents.toml row" % backend.label)
    if not backend.installed:
        raise ValueError(backend.unavailable_reason)

    settings_path = ""
    if backend.transport == "stream_json" and backend.gated_tools and server_port:
        settings_path = agent_approvals.write_settings(
            chats_dir(repo_root), sid, backend.gated_tools, server_port,
            timeout=backend.approval_timeout)

    def _on_exit(sess):
        agent_approvals.REGISTRY.forget(sess.id)

    sess = agent_session.build(
        sid, backend, meta.get("cwd") or repo_root, log_path=_log,
        title=meta.get("title") or "(resumed chat)",
        model=meta.get("model", ""), mode=meta.get("mode", ""),
        on_exit=_on_exit, settings_path=settings_path,
        # Numbering continues where the dead session stopped, so the client's
        # catch-up still works against one file.
        start_seq=meta.get("seq", 0),
        resume_id=meta["native_session_id"])
    with _lock:
        _sessions[sid] = sess
    sess.start()
    # Recorded in the transcript itself: a reader should be able to see where
    # one process ended and the next took over the same conversation.
    sess.stream.publish({
        "type": "session.resumed", "id": sid, "at": _now(),
        "resumed": meta["native_session_id"], "agent": backend.id,
    })
    return sess.snapshot()


def transcript(repo_root, sid):
    """Every event for a chat, live or dead. The client calls this on first
    open and after a `stream.reset`."""
    sess = get(sid)
    _log, events_path = _paths(repo_root, sid)
    # The FILE first, whenever there is one, because it holds the whole
    # conversation while the ring holds only what this process has published.
    # For a resumed chat those differ by everything that happened before the
    # resume — opening it would have shown two events and an empty history.
    if os.path.isfile(events_path):
        events = replay_file(events_path)
        return {"id": sid, "events": events,
                "head": events[-1].get("seq", 0) if events else 0,
                "snapshot": sess.snapshot() if sess is not None else None}
    if sess is not None:
        # A session with no transcript on disk (nothing outside tests builds
        # one, but the ring is still the truth for it).
        events, _gap = sess.stream.since(0)
        return {"id": sid, "events": events, "head": sess.stream.head,
                "snapshot": sess.snapshot()}
    raise FileNotFoundError("no transcript for %r" % sid)


def subscribe(repo_root, sid, from_seq=0, types=None):
    """SSE frames for a live chat. A dead chat has nothing to push, so this
    refuses rather than opening a stream that will never emit. `types`
    narrows to a subset of event types — see `agent_events.Stream.subscribe`."""
    sess = require(sid)
    return sess.stream.subscribe(from_seq, types=types)


def send(sid, text, mode="auto"):
    """One message into a running chat.

    `sess.cwd` IS the workspace root (chats run there — see `create`), and
    passing it is what makes an inline `/skill`, `@agent` or `#file` work
    mid-conversation. Without it this call resolved nothing, so a skill could
    only ever be chosen at the moment a chat was started.

    `display` keeps what the user typed, so the transcript shows `#src/app.py`
    while the wire carries whatever this backend needed it to become.
    """
    sess = require(sid)
    backend = sess.backend
    wire = backend.compose_prompt(text, skill="", persona="", repo_root=sess.cwd)
    return {"result": sess.send(wire, mode=mode, display=text)}


def interrupt(sid):
    sess = require(sid)
    return {"interrupted": sess.interrupt()}


def unqueue(sid, item_id):
    sess = require(sid)
    return {"removed": sess.unqueue(item_id)}


def stop(sid):
    sess = require(sid)
    agent_approvals.REGISTRY.forget(sid)
    sess.stop()
    return {"stopped": True, "id": sid}


def delete(repo_root, sid):
    """Forget a chat entirely, including its transcript on disk."""
    sess = get(sid)
    if sess is not None:
        agent_approvals.REGISTRY.forget(sid)
        try:
            sess.stop()
        except Exception:  # noqa: BLE001
            pass
        with _lock:
            _sessions.pop(sid, None)
    removed = []
    for path in _paths(repo_root, sid) + (os.path.join(chats_dir(repo_root), sid + ".settings.json"),):
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed.append(os.path.basename(path))
            except OSError:
                pass
    return {"deleted": sid, "files": removed}


def rename(sid, title):
    sess = require(sid)
    sess.title = (title or "").strip()[:120] or sess.title
    return {"id": sid, "title": sess.title}


def shutdown_all():
    """Stop every session. Called when the server exits so child processes
    don't outlive it."""
    with _lock:
        sessions = list(_sessions.values())
    for sess in sessions:
        try:
            sess.stop()
        except Exception:  # noqa: BLE001
            pass
