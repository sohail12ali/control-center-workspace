"""Named jobs on a clock. The running console is the clock.

## No daemon

`kanban serve` is already a long-lived process, so it can tick. That avoids
asking anyone to install cron, register a systemd unit, or configure Task
Scheduler — three different answers to the same question, none of which belong
in a workspace template. The cost is honest and stated: **nothing fires while
the console is not running.** A schedule is a convenience for a machine you
already leave a board open on, not a guarantee.

## Catch-up is deliberately not attempted

When the console starts after a gap, missed firings are *skipped*, not replayed.
A scheduler that catches up would, after a weekend, run every job dozens of
times at once — and these jobs submit real work to a real queue. The first tick
after startup establishes a baseline and fires nothing.

## Cron subset

Five fields — minute, hour, day-of-month, month, day-of-week — local time.
Supported per field: `*`, `N`, `A-B`, `*/S`, `A-B/S`, and comma-separated lists
of those. Day-of-week is 0-6 with Sunday 0, and 7 is accepted as Sunday too
because half the world writes it that way.

Not supported: `@daily`-style nicknames, `L`, `W`, `#`, or the day-of-month /
day-of-week OR-semantics that real cron applies when both are restricted. Both
being restricted here means AND, which is the reading people expect when they
have not memorised the POSIX rule. An expression using an unsupported feature is
**rejected at load with its schedule id**, never silently treated as `*`.
"""

import os
import re
import threading
from datetime import datetime, timedelta

from . import tomlio

CONFIG_REL = os.path.join("console", "config", "schedules.toml")

FIELDS = ("minute", "hour", "day", "month", "weekday")
RANGES = {"minute": (0, 59), "hour": (0, 23), "day": (1, 31),
          "month": (1, 12), "weekday": (0, 6)}

_PART_RE = re.compile(r"^(?:(\*)|(\d+)(?:-(\d+))?)(?:/(\d+))?$")

_cache = {}


class ScheduleError(ValueError):
    pass


def _parse_field(name, text, schedule_id):
    low, high = RANGES[name]
    allowed = set()
    for part in str(text).split(","):
        part = part.strip()
        match = _PART_RE.match(part)
        if not match:
            raise ScheduleError(
                "schedule %r: %r is not a supported %s expression. Supported: "
                "*, N, A-B, */S, A-B/S and comma-separated lists."
                % (schedule_id, part, name))
        star, start, end, step = match.groups()
        step = int(step) if step else 1
        if step < 1:
            raise ScheduleError("schedule %r: step must be 1 or more in %r"
                                % (schedule_id, part))
        if star:
            first, last = low, high
        else:
            first = int(start)
            last = int(end) if end else first
        if name == "weekday":
            # Sunday is 0, but 7 is common enough that rejecting it would be
            # pedantry rather than safety.
            first = 0 if first == 7 else first
            last = 0 if last == 7 else last
            if last < first:
                first, last = last, first
        if first < low or last > high or last < first:
            raise ScheduleError(
                "schedule %r: %s value %r is outside %d-%d"
                % (schedule_id, name, part, low, high))
        allowed.update(range(first, last + 1, step))
    return allowed


class Schedule:
    __slots__ = ("id", "label", "expr", "verb", "ticket", "args", "enabled",
                 "confirm", "fields", "raw")

    def __init__(self, row):
        self.id = (row.get("id") or "").strip()
        if not self.id:
            raise ScheduleError("schedules.toml: a [[schedule]] row needs an id")
        self.label = row.get("label", self.id)
        self.expr = (row.get("expr") or "").strip()
        self.verb = (row.get("verb") or "").strip()
        if not self.verb:
            raise ScheduleError("schedule %r has no verb" % self.id)
        self.ticket = row.get("ticket", "") or ""
        self.args = dict(row.get("args", {}) or {})
        self.enabled = bool(row.get("enabled", True))
        # A scheduled job runs with nobody watching, so a verb that would ask
        # for confirmation has to be granted it here, deliberately, in a file
        # somebody committed.
        self.confirm = bool(row.get("confirm", False))
        self.raw = row
        self.fields = self._parse()

    def _parse(self):
        parts = self.expr.split()
        if len(parts) != 5:
            raise ScheduleError(
                "schedule %r: expr must have 5 fields (minute hour day month "
                "weekday), got %d in %r" % (self.id, len(parts), self.expr))
        return {name: _parse_field(name, part, self.id)
                for name, part in zip(FIELDS, parts)}

    def matches(self, when):
        """Whether this schedule should fire at `when` (to the minute)."""
        return (when.minute in self.fields["minute"]
                and when.hour in self.fields["hour"]
                and when.day in self.fields["day"]
                and when.month in self.fields["month"]
                # Python: Monday 0 .. Sunday 6. Cron: Sunday 0 .. Saturday 6.
                and ((when.weekday() + 1) % 7) in self.fields["weekday"])

    def next_after(self, when, limit_days=366):
        """The next firing strictly after `when`, or None within the horizon.

        Minute-by-minute rather than clever: a year of minutes is half a
        million cheap comparisons, run at most once per config change, and the
        clever version is where cron implementations get their bugs.
        """
        cursor = when.replace(second=0, microsecond=0) + timedelta(minutes=1)
        end = when + timedelta(days=limit_days)
        while cursor <= end:
            if self.matches(cursor):
                return cursor
            cursor += timedelta(minutes=1)
        return None

    def describe(self, now=None):
        now = now or datetime.now()
        nxt = self.next_after(now) if self.enabled else None
        return {"id": self.id, "label": self.label, "expr": self.expr,
                "verb": self.verb, "ticket": self.ticket, "args": dict(self.args),
                "enabled": self.enabled, "confirm": self.confirm,
                "next_run": nxt.strftime("%Y-%m-%d %H:%M") if nxt else ""}


def load_config(repo_root, force=False):
    if not force and repo_root in _cache:
        return _cache[repo_root]
    path = os.path.join(repo_root, CONFIG_REL)
    data = tomlio.load(path) if os.path.isfile(path) else {"schedule": []}
    _cache[repo_root] = data
    return data


def registry(repo_root, force=False):
    """id -> Schedule for every row, enabled or not.

    Disabled rows are parsed too: a schedule parked with `enabled = false` is
    still config someone will re-enable, and finding out then that its
    expression never parsed is finding out too late.
    """
    out = {}
    for row in load_config(repo_root, force=force).get("schedule", []):
        schedule = Schedule(row)
        out[schedule.id] = schedule
    return out


def due(repo_root, when=None, since=None):
    """Enabled schedules matching this minute, excluding one already fired."""
    when = (when or datetime.now()).replace(second=0, microsecond=0)
    if since is not None and when <= since:
        return []
    return [s for s in registry(repo_root).values()
            if s.enabled and s.matches(when)]


class Ticker:
    """Fires due schedules onto a job queue, once a minute.

    Holds the last minute it processed so a tick that arrives twice within one
    minute — which happens, because the loop wakes on a timer and timers drift —
    cannot fire the same schedule twice.
    """

    def __init__(self, repo_root, queue, interval=30.0):
        self.repo_root = repo_root
        self.queue = queue
        self.interval = interval
        self._last_minute = None
        self._stop = threading.Event()
        self._thread = None
        self.fired = 0
        self.skipped = 0

    def tick(self, when=None):
        """Process one minute. Returns the job records it submitted."""
        when = (when or datetime.now()).replace(second=0, microsecond=0)
        if self._last_minute is None:
            # First tick establishes a baseline and fires nothing: catching up
            # after a gap would run every schedule dozens of times at once, and
            # these submit real work.
            self._last_minute = when
            return []
        if when <= self._last_minute:
            return []
        self._last_minute = when

        submitted = []
        for schedule in due(self.repo_root, when=when):
            try:
                job = self.queue.submit(
                    schedule.verb, ticket=schedule.ticket or None,
                    confirm=schedule.confirm, args=schedule.args,
                    submitted_by="schedule:%s" % schedule.id)
                submitted.append(job)
                self.fired += 1
            except Exception:  # noqa: BLE001
                # A schedule whose verb or gate is wrong must not stop the
                # others firing, and must not kill the ticker.
                self.skipped += 1
        return submitted

    def start(self):
        if self._thread:
            return self
        def loop():
            while not self._stop.wait(self.interval):
                try:
                    self.tick()
                except Exception:  # noqa: BLE001
                    pass
        self._thread = threading.Thread(target=loop, name="scheduler", daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout=3.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None


def format_list(rows):
    if not rows:
        return "No schedules configured."
    width = max(len(r["id"]) for r in rows)
    lines = ["%-*s %-16s %-16s %-10s %s"
             % (width, "ID", "EXPR", "VERB", "STATE", "NEXT")]
    for row in rows:
        lines.append("%-*s %-16s %-16s %-10s %s" % (
            width, row["id"], row["expr"], row["verb"],
            "enabled" if row["enabled"] else "parked",
            row["next_run"] or "-"))
        if row.get("label") and row["label"] != row["id"]:
            lines.append("%s %s" % (" " * width, row["label"]))
    return "\n".join(lines)
