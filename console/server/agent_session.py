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
from datetime import datetime, timezone

from . import procs
from . import run_config
from . import telemetry
from .agent_events import Stream
from .agent_normalize import Normalizer


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _utc_now():
    """UTC `...Z`, for the Run layer. `_now()` is local-naive and shown to
    humans; comparing it with a UTC clock is wrong by the UTC offset (CR-24).
    A module function so a test can pin the clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#: Reply text kept in the `last_turn` summary (liveness reads its opening).
TURN_TEXT_MAX = 2000

#: Distinct tool names kept per turn in `last_turn["tools"]`, so a runaway turn
#: cannot grow a session's memory by inventing names. The rest count as "(other)".
TOOL_NAMES_MAX = 32


class BaseSession:
    """Everything about a chat that doesn't depend on its transport."""

    steerable = True

    def __init__(self, sid, backend, cwd, stream, *, log_path=None, title="",
                 model="", mode="", skill="", persona="", on_exit=None,
                 settings_path="", ticket="", system_append="", extra="",
                 repo_root="", on_limit=None):
        self.id = sid
        #: `on_limit(session, failure_class, detail)`, called before a cap kill
        #: so the Run is terminal before the exit it causes (CR-15, CR-21).
        self.on_limit = on_limit
        # Where console.toml lives: `cwd` is a worktree for a ticketed Run, so
        # it cannot stand in (T-020 CR-21). "" means "find it".
        self.repo_root = repo_root
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
        # Persona/context injection, additive to skill/persona above: a second
        # text a caller (the assistant feature) wants threaded to the backend
        # without overloading `persona`'s existing meaning as an agent-file id.
        # `system_append` is a raw string handed straight to a backend's own
        # system-prompt flag; `extra` is folded into `prompt_build.build`'s
        # "extra" section for the `openai_api` transport. Empty by default so
        # no existing chat changes at all.
        self.system_append = system_append
        self.extra = extra
        #: System text that still has to ride on the FIRST message, because
        #: this backend has no flag to carry it.
        #:
        #: `agent_manager.create` used to prepend it to the opening message it
        #: sent itself. A session opened with no message (`open=False`) has no
        #: such message, so the text would simply be lost — and losing a
        #: persona silently is the worst available outcome. Parked here and
        #: consumed by the first `send`, wherever that call comes from: the
        #: assistant feature talks to `send` directly rather than through
        #: `agent_manager.send`, so a fix in either caller alone would leave
        #: the other one broken.
        self._pending_system_prefix = ""

        self.proc = None
        self.native_session_id = ""
        self.started = ""
        self.ended = ""
        # What the Run layer reads (T-020 FR-4), kept as attributes because the
        # event ring can overflow inside one watchdog tick. "" / None mean
        # "never happened", never "now". `last_turn` is replaced whole at each
        # turn end, so a reader on another thread sees one consistent turn.
        self.started_utc = ""
        self.last_output_at = ""
        self._last_output_mono = 0.0
        self.last_turn = None
        self.turn_count = 0
        self._turn_rate_limit = None
        self._turn_tools = {}
        self.exit_code = None
        self.cost_usd = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.num_turns = 0
        self._turn_in = 0
        self._turn_out = 0
        # Output volume of the turn in flight, in decoded characters (the pipes
        # are text mode). Reset where `turn.start` is published.
        self._turn_chars = 0
        self._turn_cap = None
        self._cap_hit = False

        self._norm = Normalizer()
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._busy = False
        self._queue = []
        self._ctl = 0
        self._log_fh = None
        self._stopping = False

    def defer_system_prefix(self, text):
        """Have the first `send` carry `text` ahead of the message.

        For a session opened with no message on a backend that has no
        system-prompt flag of its own — see `_pending_system_prefix`.
        """
        with self._state_lock:
            self._pending_system_prefix = text or ""

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

    def _line_cap(self):
        return run_config.runs_cfg(self.repo_root or None)["max_line_bytes"]

    def kill_process(self, grace=5.0):
        """Tree-kill the current child (BR-11). Unlike `stop` it does not mark
        the session as human-stopped, so a watchdog or cap kill still reads as
        what it was."""
        procs.kill_tree(self.proc, grace)

    # -- state ---------------------------------------------------------------
    @property
    def busy(self):
        with self._state_lock:
            return self._busy

    @property
    def stop_requested(self):
        """A human asked this session to end. How the Run layer tells a stop
        from a crash (CR-16)."""
        return self._stopping

    def _last_turn_summary(self):
        lt = self.last_turn
        if lt is None:
            return None
        te = lt["turn_end"]
        # The bounded failure evidence (T-020 FR-10) rides along so the Run
        # layer can classify and judge liveness without the event ring.
        return {"subtype": te.get("subtype", ""),
                "is_error": bool(te.get("is_error")),
                "rate_limit": (lt["rate_limit"] or {}).get("status", ""),
                "resets_at": (lt["rate_limit"] or {}).get("resets_at") or 0,
                "tools": dict(lt["tools"]),
                "result": (te.get("result") or "")[:TURN_TEXT_MAX],
                "error": te.get("error") or "",
                "errors": list(te.get("errors") or []),
                "api_error_status": te.get("api_error_status"),
                "stop_reason": te.get("stop_reason") or ""}

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
            "started_utc": self.started_utc,
            "last_output_at": self.last_output_at,
            "turn_count": self.turn_count,
            "last_turn": self._last_turn_summary(),
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
        # Claimed under the state lock above, so two concurrent first sends
        # cannot both prepend it. Only the WIRE gets it; `shown` stays what the
        # user actually typed, which is the same split `display` already makes.
        with self._state_lock:
            prefix, self._pending_system_prefix = self._pending_system_prefix, ""
        if prefix:
            text = prefix + "\n\n" + text
        extra = {"wire": text} if shown != text else {}
        if not busy:
            self._reset_turn_output()
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
        self._reset_turn_output()
        self.stream.publish({"type": "turn.start", "text": item["text"], "steered": False})
        try:
            self._deliver(item["text"])
        except (RuntimeError, OSError) as e:
            with self._state_lock:
                self._busy = False
            self.stream.publish({"type": "error", "text": str(e)})

    # -- observing -----------------------------------------------------------
    def _reset_turn_output(self):
        self._turn_chars = 0
        self._cap_hit = False

    def _count_output(self, line):
        """Enforce `[runs].max_turn_output_bytes` for this turn (BR-9: applies
        to every chat). On the first breach: one notice, the `on_limit`
        callback, then the tree kill, in that order."""
        self._turn_chars += len(line) + 1
        if self._cap_hit:
            return
        if self._turn_cap is None:
            self._turn_cap = run_config.runs_cfg(self.repo_root or None)["max_turn_output_bytes"]
        if self._turn_chars <= self._turn_cap:
            return
        self._cap_hit = True
        detail = "turn output passed %d characters" % self._turn_cap
        self.stream.publish({"type": "notice", "kind": "output_cap", "limit": self._turn_cap})
        if self.on_limit is not None:
            try:
                self.on_limit(self, "output_cap", detail)
            except Exception:  # noqa: BLE001
                # The kill is the point; a bookkeeping bug must not skip it.
                pass
        self.kill_process(grace=2.0)

    def _handle_line(self, line):
        # Stamped before anything is parsed, so a backend printing plain text
        # still shows as alive to the watchdog.
        self._last_output_mono = time.monotonic()
        self.last_output_at = _utc_now()
        self._count_output(line)
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
            return False
        ended = False
        for ev in self._norm.feed(raw):
            # Publish BEFORE observing: `_observe` reacts to turn.end by
            # draining, and draining publishes turn.start — observing first
            # would open the next turn at a lower seq than the turn it follows.
            self.stream.publish(ev)
            self._observe(ev)
            ended = ended or ev.get("type") == "turn.end"
        return ended  # lets a reader see its own turn end without hooking `_observe`

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
        elif t == "notice" and ev.get("kind") == "rate_limit":
            self._turn_rate_limit = dict(ev)
        elif t == "tool.start":
            # A count of `tool.start` events, not of distinct calls: a CLI that
            # repeats a call in its final assistant message may count it twice.
            # Readers ask "was anything done", not "how many times".
            name = str(ev.get("name") or "tool")[:64]
            if name not in self._turn_tools and len(self._turn_tools) >= TOOL_NAMES_MAX:
                name = "(other)"
            self._turn_tools[name] = self._turn_tools.get(name, 0) + 1
        elif t == "turn.end":
            # Before anything below can start the drain thread: once the queue
            # drains, a reader sees an idle session and must find this turn.
            self.last_turn = {"turn_end": dict(ev), "rate_limit": self._turn_rate_limit,
                              "tools": self._turn_tools}
            self.turn_count += 1
            self._turn_rate_limit = None
            self._turn_tools = {}
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
            self._notify_turn_end(ev)
            self._on_turn_end()

    def _notify_turn_end(self, ev):
        """Tell a phone the run finished.

        Here rather than in either transport because every transport funnels
        through `_observe` — the CLI sessions by reading their own stream, and
        `agent_api_session` by calling this method directly — so one hook
        covers both kinds of agent.

        Best-effort and never raised: a notification that cannot be delivered
        must not fail the turn it is describing.
        """
        try:
            from . import notify
            notify.send(self.repo_root or self.cwd, "turn_end", notify.turn_end_message(
                self.title, self.agent, self.model,
                int(ev.get("num_turns") or 0), self.cost_usd,
                error=bool(ev.get("is_error"))))
        except Exception:  # noqa: BLE001
            pass

    def _record_turn(self, ev, turn_in, turn_out):
        """Persist this turn's measurement.

        Recorded per turn rather than per session because a session can run for
        hours and a session-level total cannot answer "which stage cost that" —
        which is the only question the data exists to answer. Written to the main
        repo (`self.repo_root`), not `self.cwd`: for a ticketed chat `cwd` is a
        worktree the Analytics tab never reads. Falls back to `cwd` when no
        `repo_root` was given.

        Cost is taken from the backend when it reported one and left to the
        pricing table otherwise; `cost_usd=None` means unknown, and telemetry
        reports it as unpriced rather than as zero.
        """
        reported = ev.get("cost_usd")
        try:
            telemetry.record_turn(
                self.repo_root or self.cwd,
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
                ttft_ms=ev.get("ttft_ms") or 0,
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
    #: Seconds `stop` waits after closing stdin before it kills the tree.
    stop_wait_secs = 10

    def start(self):
        self._open_log()
        argv = self.backend.session_argv(
            mode=self.mode, model=self.model, persona=self.persona,
            settings_path=self.settings_path, system_append=self.system_append,
            resume_id=self.native_session_id)
        self.proc = subprocess.Popen(
            argv, cwd=self.cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._log_fh or subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            env=procs.clean_env(self.repo_root or None),
            **procs.tree_spawn_kwargs(),
        )
        self.started = _now()
        self.started_utc = _utc_now()
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
            self.proc.wait(timeout=self.stop_wait_secs)
        except subprocess.TimeoutExpired:
            self.kill_process(grace=2.0)

    def _read(self):
        """Own the stdout pipe for the life of the process. Must always reach
        `_finish`, which publishes the last event and closes the stream."""
        try:
            for line in procs.iter_capped_lines(self.proc.stdout, self._line_cap()):
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
        self.started_utc = _utc_now()
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
        via_stdin = getattr(self.backend, "prompt_via", "argv") == "stdin"
        argv = self.backend.turn_argv(
            "" if via_stdin else text, mode=self.mode, model=self.model,
            resume_id=self.native_session_id)
        env = procs.clean_env(self.repo_root or None)
        extra = getattr(self.backend, "child_env", None)
        if callable(extra):
            env.update(extra(self.repo_root, self.id) or {})
        try:
            self._turn_proc = subprocess.Popen(
                argv, cwd=self.cwd,
                stdin=subprocess.PIPE if via_stdin else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=env,
                **procs.tree_spawn_kwargs(),
            )
        except FileNotFoundError as e:
            with self._state_lock:
                self._busy = False
            raise RuntimeError("backend command not found: %s (%s)" % (argv[0], e)) from None
        if via_stdin and self._turn_proc.stdin is not None:
            try:
                body = text or ""
                self._turn_proc.stdin.write(body if body.endswith("\n") else body + "\n")
            finally:
                self._turn_proc.stdin.close()
        self.proc = self._turn_proc
        threading.Thread(target=self._read_turn, args=(self._turn_proc,), daemon=True).start()

    def _read_turn(self, proc):
        """One turn's output. Ends with a synthetic turn.end if the CLI didn't
        emit a result event, so the queue still drains and the UI stops showing
        the turn as in-flight."""
        # Per reader, so an overlapping next-turn reader cannot clobber it
        # (CR-31); `_handle_line` reports a turn end instead of a `_observe` swap.
        saw_end = False
        linger = None
        try:
            for line in procs.iter_capped_lines(proc.stdout, self._line_cap()):
                line = line.strip()
                if line and self._handle_line(line) and not saw_end:
                    saw_end = True
                    linger = self._arm_linger(proc)
        except (OSError, ValueError) as e:
            self.stream.publish({"type": "error", "text": "stream read failed: %s" % e})
        finally:
            if linger is not None:
                linger.cancel()
            try:
                code = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                code = None
            if not saw_end:
                for ev in self._norm.reset_turn():
                    self.stream.publish(ev)
                synthetic = {"type": "turn.end", "subtype": "process_exit",
                             "is_error": bool(code), "exit_code": code,
                             "num_turns": 1}
                self.stream.publish(synthetic)
                # Route it through _observe as well: publishing alone skips the
                # accounting that _handle_line normally performs, which left a
                # completed turn showing num_turns 0 in the snapshot.
                self._observe(synthetic)

    def _arm_linger(self, proc):
        """FR-8: a per-turn process that has printed its result but not exited
        within `[runs].linger_grace_secs` is tree-killed. The timer holds the
        process it was armed for, never `self.proc` (a later turn's)."""
        grace = run_config.runs_cfg(self.repo_root or None)["linger_grace_secs"]
        timer = threading.Timer(grace, self._linger_kill, args=(proc,))
        timer.daemon = True
        timer.start()
        return timer

    def _linger_kill(self, proc):
        if proc.poll() is not None:
            return
        procs.kill_tree(proc, grace=2.0)
        self.stream.publish({"type": "notice", "level": "warn", "kind": "lingering_killed",
                             "text": "The agent process kept running after its result and was ended."})

    def interrupt(self):
        """Kill the turn in flight; the session survives for the next one."""
        proc = self._turn_proc
        if proc is None or proc.poll() is not None:
            return False
        procs.kill_tree(proc, grace=2.0)
        self.stream.publish({"type": "turn.interrupt", "via": "terminate"})
        return True

    def stop(self):
        self._stopping = True
        self._ended = True
        proc = self._turn_proc
        if proc is not None and proc.poll() is None:
            procs.kill_tree(proc, grace=2.0)
        self.exit_code = 0
        self._finish()


def build(sid, backend, cwd, *, log_path=None, title="", model="", mode="",
          skill="", persona="", on_exit=None, settings_path="", ticket="",
          system_append="", extra="", start_seq=0, resume_id="", repo_root="",
          on_limit=None):
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
    stream = Stream(sid,
                    path=log_path.replace(".log", ".events.jsonl") if log_path else None,
                    start_seq=start_seq)
    sess = cls(sid, backend, cwd, stream, log_path=log_path, title=title,
               model=model, mode=mode, skill=skill, persona=persona,
               on_exit=on_exit, settings_path=settings_path, ticket=ticket,
               system_append=system_append, extra=extra, repo_root=repo_root,
               on_limit=on_limit)
    # A resumed session already has an identity on the CLI's side. Carrying it
    # in before `start()` is what makes the process continue that conversation
    # instead of opening a new one.
    if resume_id:
        sess.native_session_id = resume_id
    return sess
