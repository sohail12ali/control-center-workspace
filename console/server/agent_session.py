"""A chat session — the console's channel to one agent conversation.

Two transports behind one interface, because the CLIs are not equally capable:

    LiveSession    transport=stream_json. ONE process for the whole
                   conversation with stdin held open, so a message can arrive
                   mid-turn: steering and a true interrupt are possible.
    TurnSession    transport=resume/oneshot. ONE process PER TURN, continued
                   with a resume flag. It streams output just as well, but
                   there is no open channel to write to, so a message can only
                   be QUEUED for the next turn.

`BaseSession` holds everything that doesn't depend on that difference — the
queue, the snapshot the UI lists, cost/turn accounting, the exit handshake —
so the two can't drift into behaving differently for no reason.

## Steer vs queue

Two gestures, and the difference is real rather than cosmetic:

    steer   written to stdin the moment you send it, while the turn is still
            running. Use it to correct a run in flight.
    queue   held here, and written only once the turn has ended. Use it to
            line up the follow-up you already know you want.

`send()` picks when the caller doesn't: idle → sent now; mid-turn → queued,
because silently steering a run someone thought they were replying to would be
a surprising default. The UI asks explicitly and hides "steer" entirely on a
transport that cannot do it.

What "immediately" buys you: the console writes a steer at once, but the CLI
admits it at the next *step* boundary, not mid-token. A long agentic turn has a
boundary between every tool call, so a steer lands within seconds; a single
block of prose generation has none until it finishes.

## Lifetime

A session dies with the console — it is a child process and nothing
re-attaches after a restart. The transcript on disk is durable, so a past
session still replays read-only; it just cannot be spoken to. The UI says so
rather than offering a reply box that would fail.
"""

import json
import os
import signal
import subprocess
import threading
import time
import uuid

from . import telemetry
from .agent_events import Stream
from .agent_normalize import Normalizer


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class BaseSession:
    """Everything about a chat that doesn't depend on its transport."""

    steerable = True

    def __init__(self, sid, backend, cwd, stream, *, log_path=None, title="",
                 model="", mode="", skill="", persona="", on_exit=None,
                 settings_path="", ticket=""):
        self.id = sid
        self.backend = backend
        self.agent = backend.id
        self.cwd = cwd
        self.stream = stream
        self.log_path = log_path
        self.title = title
        self.model = model
        self.mode = mode or backend.default_mode
        self.skill = skill
        self.persona = persona
        self.on_exit = on_exit
        self.settings_path = settings_path
        # Which ticket this chat is working on, for telemetry attribution.
        # Optional: an exploratory chat belongs to no ticket, and recording it
        # against one would corrupt that ticket's cost.
        self.ticket = ticket

        self.proc = None
        self.native_session_id = ""
        self.started = ""
        self.ended = ""
        self.exit_code = None
        self.cost_usd = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.num_turns = 0
        self._turn_in = 0
        self._turn_out = 0

        self._norm = Normalizer()
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._busy = False
        self._queue = []
        self._ctl = 0
        self._log_fh = None
        self._stopping = False

    # -- transport seam ------------------------------------------------------
    def start(self):
        raise NotImplementedError

    @property
    def alive(self):
        raise NotImplementedError

    def _deliver(self, text):
        raise NotImplementedError

    def interrupt(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    # -- state ---------------------------------------------------------------
    @property
    def busy(self):
        with self._state_lock:
            return self._busy

    def snapshot(self):
        with self._state_lock:
            queued = [dict(m) for m in self._queue]
            busy = self._busy
        return {
            "id": self.id, "title": self.title, "agent": self.agent,
            "backend_label": self.backend.label,
            "steerable": self.steerable, "transport": self.backend.transport,
            "skill": self.skill, "persona": self.persona, "ticket": self.ticket,
            "cwd": self.cwd, "model": self.model, "mode": self.mode,
            "native_session_id": self.native_session_id,
            "alive": self.alive, "busy": busy, "queued": queued,
            "started": self.started, "ended": self.ended,
            "exit_code": self.exit_code, "cost_usd": round(self.cost_usd, 4),
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "num_turns": self.num_turns, "head": self.stream.head,
            "pid": self.proc.pid if self.proc else None,
        }

    # -- speaking ------------------------------------------------------------
    def send(self, text, mode="auto", display=""):
        """Deliver `text`. Returns "sent" or "queued"."""
        text = (text or "").strip()
        if not text:
            raise ValueError("an empty message cannot be sent")
        if mode not in ("auto", "steer", "queue"):
            raise ValueError("unknown send mode %r" % mode)
        if not self.alive and not self.backend.resumable:
            raise RuntimeError("session has ended — start a new one")
        if mode == "steer" and not self.steerable:
            # Refuse rather than quietly queue: someone who chose "steer"
            # wants it to land now, and silently doing something else is worse
            # than saying the transport cannot.
            raise ValueError(
                "%s runs one process per turn, so there is no open channel to "
                "steer down — queue the message instead" % self.agent)

        with self._state_lock:
            busy = self._busy
            if mode == "queue" or (mode == "auto" and busy):
                item = {"id": uuid.uuid4().hex[:8], "text": text}
                self._queue.append(item)
                depth = len(self._queue)
                self.stream.publish({"type": "queue.add", "item": item, "depth": depth})
                return "queued"
            if not busy:
                self._busy = True

        shown = (display or "").strip() or text
        extra = {"wire": text} if shown != text else {}
        if not busy:
            self.stream.publish({"type": "turn.start", "text": shown, "steered": False, **extra})
        else:
            self.stream.publish({"type": "turn.steer", "text": shown, **extra})
        self._deliver(text)
        return "sent"

    def unqueue(self, item_id):
        with self._state_lock:
            before = len(self._queue)
            self._queue = [m for m in self._queue if m["id"] != item_id]
            removed = len(self._queue) != before
            depth = len(self._queue)
        if removed:
            self.stream.publish({"type": "queue.remove", "id": item_id, "depth": depth})
        return removed

    def _drain(self):
        """Send the next queued message, if any. Called at a turn boundary."""
        with self._state_lock:
            if not self._queue or self._stopping:
                self._busy = False
                return
            item = self._queue.pop(0)
            depth = len(self._queue)
            self._busy = True
        self.stream.publish({"type": "queue.drain", "item": item, "depth": depth})
        self.stream.publish({"type": "turn.start", "text": item["text"], "steered": False})
        try:
            self._deliver(item["text"])
        except (RuntimeError, OSError) as e:
            with self._state_lock:
                self._busy = False
            self.stream.publish({"type": "error", "text": str(e)})

    # -- observing -----------------------------------------------------------
    def _handle_line(self, line):
        if self._log_fh is not None:
            try:
                self._log_fh.write(line.encode("utf-8") + b"\n")
                # Flush per line. Without it the raw CLI log only materialises
                # when the session closes, which is precisely when it is least
                # useful — a live session being debugged shows an empty file.
                self._log_fh.flush()
            except (OSError, ValueError):
                pass
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON — a backend printing plain text. Surface it as content
            # rather than dropping it.
            for ev in self._norm.feed({"text": line}):
                self.stream.publish(ev)
            return
        for ev in self._norm.feed(raw):
            # Publish BEFORE observing: `_observe` reacts to turn.end by
            # draining, and draining publishes turn.start — observing first
            # would open the next turn at a lower seq than the turn it follows.
            self.stream.publish(ev)
            self._observe(ev)

    def _observe(self, ev):
        t = ev.get("type")
        if t == "session.init":
            self.native_session_id = ev.get("session_id") or self.native_session_id
            if ev.get("model"):
                self.model = ev["model"]
        elif t == "usage":
            # Mid-turn running total for THIS turn, not a session delta — a
            # CLI re-reports the turn's cumulative usage as it goes.
            self._turn_in = max(self._turn_in, int(ev.get("input_tokens") or 0))
            self._turn_out = max(self._turn_out, int(ev.get("output_tokens") or 0))
        elif t == "turn.end":
            self.cost_usd += float(ev.get("cost_usd") or 0.0)
            self.num_turns += int(ev.get("num_turns") or 0)
            # A backend may report the turn's usage in its result event, or
            # incrementally as `usage` events, or both. Take the larger of the
            # two for this turn and add THAT to the session totals: summing
            # both would double-count, and carrying a max across turns would
            # lose every turn but the biggest.
            turn_in = max(self._turn_in, int(ev.get("input_tokens") or 0))
            turn_out = max(self._turn_out, int(ev.get("output_tokens") or 0))
            self.tokens_in += turn_in
            self.tokens_out += turn_out
            self._turn_in = self._turn_out = 0
            self._record_turn(ev, turn_in, turn_out)
            self._on_turn_end()

    def _record_turn(self, ev, turn_in, turn_out):
        """Persist this turn's measurement.

        Recorded per turn rather than per session because a session can run for
        hours and a session-level total cannot answer "which stage cost that" —
        which is the only question the data exists to answer. `self.cwd` is the
        repo root the manager built this session with.

        Cost is taken from the backend when it reported one and left to the
        pricing table otherwise; `cost_usd=None` means unknown, and telemetry
        reports it as unpriced rather than as zero.
        """
        reported = ev.get("cost_usd")
        try:
            telemetry.record_turn(
                self.cwd,
                session=self.id,
                backend=self.agent,
                model=self.model,
                mode=self.mode,
                ticket=self.ticket,
                skill=self.skill,
                persona=self.persona,
                input_tokens=turn_in,
                output_tokens=turn_out,
                cost_usd=float(reported) if reported else None,
                duration_ms=ev.get("duration_ms") or 0,
                is_error=bool(ev.get("is_error")),
            )
        except Exception:  # noqa: BLE001
            # Measurement must never be able to kill the chat it measures.
            pass

    def _on_turn_end(self):
        """Drain on its own thread: `_drain` writes to the agent, and doing
        that from the reader thread risks blocking the very pipe being read."""
        threading.Thread(target=self._drain, daemon=True).start()

    def _finish(self):
        self.ended = _now()
        with self._state_lock:
            self._busy = False
            dropped = len(self._queue)
            self._queue.clear()
        if self._log_fh is not None:
            try:
                self._log_fh.close()
            except OSError:
                pass
            self._log_fh = None
        self.stream.publish({
            "type": "session.exit", "id": self.id, "exit_code": self.exit_code,
            "cost_usd": round(self.cost_usd, 4), "num_turns": self.num_turns,
            "dropped_queued": dropped, "at": self.ended,
        })
        if self.on_exit is not None:
            try:
                self.on_exit(self)
            except Exception:  # noqa: BLE001
                # A failing callback must not stop the stream closing, or
                # every subscriber hangs on a session that is already gone.
                pass
        self.stream.close()

    def _open_log(self):
        if self.log_path:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            self._log_fh = open(self.log_path, "ab")


class LiveSession(BaseSession):
    """One long-lived process, stdin held open for the whole chat."""

    steerable = True

    def start(self):
        self._open_log()
        argv = self.backend.session_argv(
            mode=self.mode, model=self.model, persona=self.persona,
            settings_path=self.settings_path)
        self.proc = subprocess.Popen(
            argv, cwd=self.cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._log_fh or subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        self.started = _now()
        self.stream.publish({
            "type": "session.started", "id": self.id, "pid": self.proc.pid,
            "cmd": argv, "cwd": self.cwd, "title": self.title,
            "model": self.model, "agent": self.agent, "steerable": True,
            "mode": self.mode, "at": self.started,
        })
        threading.Thread(target=self._read, name="sess-" + self.id, daemon=True).start()

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _write(self, obj):
        """One JSON line to stdin, serialised against every other writer —
        HTTP requests arrive on their own threads, so two sends could
        otherwise interleave halfway through a line and corrupt both."""
        if not self.alive or self.proc is None or self.proc.stdin is None:
            raise RuntimeError("session is not running")
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        with self._write_lock:
            try:
                self.proc.stdin.write(line)
                self.proc.stdin.flush()
            except (OSError, ValueError) as e:
                raise RuntimeError("session stdin closed: %s" % e) from e

    def _deliver(self, text):
        self._write({"type": "user", "message": {
            "role": "user", "content": [{"type": "text", "text": text}]}})

    def interrupt(self):
        """Stop the turn in flight, keeping the session alive. The control
        request is the documented transport; a signal to the process group is
        the fallback for a build that doesn't answer it."""
        if not self.alive:
            return False
        self._ctl += 1
        try:
            self._write({"type": "control_request",
                         "request_id": "%s-int-%d" % (self.id, self._ctl),
                         "request": {"subtype": "interrupt"}})
            self.stream.publish({"type": "turn.interrupt", "via": "control"})
            for ev in self._norm.reset_turn():
                self.stream.publish(ev)
            with self._state_lock:
                self._busy = False
            return True
        except RuntimeError:
            pass
        try:
            sig = getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)
            os.kill(self.proc.pid, sig)
            self.stream.publish({"type": "turn.interrupt", "via": "signal"})
            return True
        except (OSError, AttributeError):
            return False

    def stop(self):
        """End the session. Closing stdin is how this CLI is asked to exit."""
        self._stopping = True
        if self.proc is None:
            return
        with self._state_lock:
            self._queue.clear()
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                with self._write_lock:
                    self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def _read(self):
        """Own the stdout pipe for the life of the process. Must always reach
        `_finish`, which publishes the last event and closes the stream."""
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if line:
                    self._handle_line(line)
        except (OSError, ValueError) as e:
            self.stream.publish({"type": "error", "text": "stream read failed: %s" % e})
        finally:
            if self.proc is not None:
                try:
                    self.exit_code = self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.exit_code = None
            self._finish()


class TurnSession(BaseSession):
    """One process per turn, continued with a resume flag.

    "Alive" here means "can accept another turn", which is true between turns
    even though no process exists — that's the whole point of resume. The
    session ends only when someone stops it, so `stop()` is what closes the
    stream rather than a process exit.
    """

    steerable = False

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ended = False
        self._turn_proc = None

    def start(self):
        self._open_log()
        self.started = _now()
        self.stream.publish({
            "type": "session.started", "id": self.id, "pid": None,
            "cmd": [self.backend.command], "cwd": self.cwd, "title": self.title,
            "model": self.model, "agent": self.agent, "steerable": False,
            "mode": self.mode, "at": self.started,
            "note": "one process per turn — messages queue, they cannot steer",
        })

    @property
    def alive(self):
        return not self._ended

    def _deliver(self, text):
        argv = self.backend.turn_argv(
            text, mode=self.mode, model=self.model, resume_id=self.native_session_id)
        try:
            self._turn_proc = subprocess.Popen(
                argv, cwd=self.cwd,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except FileNotFoundError as e:
            with self._state_lock:
                self._busy = False
            raise RuntimeError("backend command not found: %s (%s)" % (argv[0], e)) from None
        self.proc = self._turn_proc
        threading.Thread(target=self._read_turn, args=(self._turn_proc,), daemon=True).start()

    def _read_turn(self, proc):
        """One turn's output. Ends with a synthetic turn.end if the CLI didn't
        emit a result event, so the queue still drains and the UI stops showing
        the turn as in-flight."""
        saw_end = {"v": False}
        original_observe = self._observe

        def observe(ev):
            if ev.get("type") == "turn.end":
                saw_end["v"] = True
            original_observe(ev)

        self._observe = observe
        try:
            for line in proc.stdout:
                line = line.strip()
                if line:
                    self._handle_line(line)
        except (OSError, ValueError) as e:
            self.stream.publish({"type": "error", "text": "stream read failed: %s" % e})
        finally:
            self._observe = original_observe
            try:
                code = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                code = None
            if not saw_end["v"]:
                for ev in self._norm.reset_turn():
                    self.stream.publish(ev)
                synthetic = {"type": "turn.end", "subtype": "process_exit",
                             "is_error": bool(code), "exit_code": code,
                             "num_turns": 1}
                self.stream.publish(synthetic)
                # Route it through _observe as well: publishing alone skips the
                # accounting that _handle_line normally performs, which left a
                # completed turn showing num_turns 0 in the snapshot.
                original_observe(synthetic)

    def interrupt(self):
        """Kill the turn in flight; the session survives for the next one."""
        proc = self._turn_proc
        if proc is None or proc.poll() is not None:
            return False
        try:
            proc.terminate()
        except OSError:
            return False
        self.stream.publish({"type": "turn.interrupt", "via": "terminate"})
        return True

    def stop(self):
        self._stopping = True
        self._ended = True
        proc = self._turn_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()
                except OSError:
                    pass
        self.exit_code = 0
        self._finish()


def build(sid, backend, cwd, *, log_path=None, title="", model="", mode="",
          skill="", persona="", on_exit=None, settings_path="", ticket=""):
    """Pick the transport the backend declared. The only place that decision
    is made, so a new transport is one branch here plus a class."""
    if backend.transport == "openai_api":
        # Imported here, not at module scope: ApiSession subclasses BaseSession
        # from this module, so a top-level import would be circular.
        from .agent_api_session import ApiSession
        cls = ApiSession
    elif backend.transport == "stream_json":
        cls = LiveSession
    else:
        cls = TurnSession
    stream = Stream(sid, path=log_path.replace(".log", ".events.jsonl") if log_path else None)
    return cls(sid, backend, cwd, stream, log_path=log_path, title=title,
               model=model, mode=mode, skill=skill, persona=persona,
               on_exit=on_exit, settings_path=settings_path, ticket=ticket)
