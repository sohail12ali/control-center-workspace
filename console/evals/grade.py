"""Transcript view and the five deterministic graders.

Imports stay at json, re, and the existing Normalizer. No clock, no random,
no network, no process. Usage is read from the raw result object by the
runner, never from the Normalizer's zero-collapsed turn.end.
"""

import json
import re

from server.agent_normalize import Normalizer

GRADER_VERSION = 1
KINDS = ("call", "first_call", "order", "text", "end")
CLASSES = ("grading", "infra", "product", "model")
PRECEDENCE = ("grading", "infra", "product", "model")

BAD_SCENARIO = "bad_scenario"
BAD_FIXTURE = "bad_fixture"
CHECK_ERROR = "check_error"
GOLDEN_FAILED = "golden_failed"
MUST_FAIL_PASSED = "must_fail_passed"
SPAWN_ERROR = "spawn_error"
NO_RESULT = "no_result"
TIMEOUT = "timeout"
API_ERROR = "api_error"
AUTH = "auth"
RATE_LIMIT = "rate_limit"
OVERLOADED = "overloaded"
BUDGET_CAP = "budget_cap"
EMPTY_TURN = "empty_turn"
CLI_ERROR = "cli_error"
RULE_MOVED = "rule_moved"
SUBJECT_MISSING = "subject_missing"
BEHAVIOUR = "behaviour"
MAX_TURNS = "max_turns"
TOOL_CAP = "tool_cap"

_EXIT_PLAN = ("exitplanmode", "exit_plan_mode")
_PATH_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


class GradingError(Exception):
    """A scenario, fixture, or check that cannot be graded."""

    def __init__(self, reason, detail, file="", key=""):
        self.reason = reason
        self.detail = detail
        self.file = file
        self.key = key
        where = ""
        if file or key:
            where = "%s key %s: " % (file or "?", key or "?")
        super().__init__("%s%s: %s" % (where, reason, detail))


class Problem:
    """One classified failure. `cls` is the taxonomy class."""

    def __init__(self, cls, reason, detail, evidence=""):
        self.cls = cls
        self.reason = reason
        self.detail = detail or ""
        self.evidence = (evidence or self.detail)[:200]

    def as_dict(self):
        return {"class": self.cls, "reason": self.reason,
                "detail": self.detail, "evidence": self.evidence}


def canonical(call):
    """The one string a `call` regex is searched against."""
    name = call.get("name") or ""
    args = call.get("args") if isinstance(call.get("args"), dict) else {}
    if name == "Bash":
        argtext = str(args.get("command") or "")
    elif name in _PATH_TOOLS:
        path = args.get("file_path") or args.get("notebook_path") or ""
        argtext = str(path).replace("\\", "/")
    elif name == "Skill":
        skill = str(args.get("skill") or "")
        extra = str(args.get("args") or "")
        argtext = (skill + " " + extra).strip() if extra else skill
    else:
        argtext = json.dumps(args, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False)
    return "%s %s" % (name, argtext)


def _json_line(line):
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


class TranscriptView:
    """What the graders see. Tool results are ignored on purpose."""

    def __init__(self):
        self.calls = []
        self.text_blocks = []
        self.plans = []
        self.noise = 0
        self.turn_end = None
        self.raw_result = None
        self.model = ""
        self._norm = Normalizer()
        self._seen = set()
        self._plans_seen = set()

    def feed(self, line, strict=False):
        """One physical line. `strict` is for fixtures; live counts noise."""
        if not isinstance(line, str):
            raw = line
        else:
            stripped = line.strip()
            if not stripped:
                return
            raw = _json_line(stripped)
            if raw is None:
                if strict:
                    raise GradingError(BAD_FIXTURE, "non-json line", key="fixture")
                self.noise += 1
                return
        if not isinstance(raw, dict):
            if strict:
                raise GradingError(BAD_FIXTURE, "line is not an object", key="fixture")
            self.noise += 1
            return
        if raw.get("type") == "result":
            self.raw_result = raw
        for ev in self._norm.feed(raw):
            self._take(ev)

    def _take(self, ev):
        kind = ev.get("type")
        if kind == "tool.result":
            return
        if kind == "tool.start":
            name = ev.get("name") or ""
            if name.lower() in _EXIT_PLAN:
                return
            tid = ev.get("id") or ""
            if tid:
                if tid in self._seen:
                    return
                self._seen.add(tid)
            call = {"id": tid, "name": name,
                    "args": ev.get("args") if isinstance(ev.get("args"), dict) else {},
                    "index": len(self.calls)}
            call["canonical"] = canonical(call)
            self.calls.append(call)
            return
        if kind == "plan":
            pid = ev.get("id") or ""
            text = ev.get("plan") or ""
            if pid:
                if pid in self._plans_seen:
                    return
                self._plans_seen.add(pid)
            if text:
                self.plans.append(text)
            return
        if kind == "text.done":
            text = ev.get("text") or ""
            if text:
                self.text_blocks.append(text)
            return
        if kind == "session.init" and ev.get("model"):
            self.model = ev["model"]
            return
        if kind == "turn.end":
            self.turn_end = ev

    @classmethod
    def from_lines(cls, lines, strict=False):
        if isinstance(lines, str):
            return parse_lines(lines, strict)
        view = cls()
        for line in lines:
            view.feed(line if isinstance(line, str) else json.dumps(line), strict=strict)
        return view

    @property
    def final(self):
        for text in reversed(self.text_blocks):
            if text.strip():
                return text
        raw = self.raw_result or {}
        return raw.get("result") or ""

    @property
    def disposition(self):
        if not self.turn_end:
            return "no_result"
        return "error" if self.turn_end.get("is_error") else "completed"


def parse_lines(text, strict=False):
    """Split a transcript. A torn last line (no trailing newline, not JSON)
    is ignored in live mode and is a grading error when strict."""
    if text is None:
        text = ""
    if isinstance(text, list):
        return TranscriptView.from_lines(text, strict)
    ended = text.endswith("\n") or text.endswith("\r")
    lines = text.splitlines()
    view = TranscriptView()
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        if (not strict and last and not ended and line.strip()
                and _json_line(line.strip()) is None):
            continue
        view.feed(line, strict=strict)
    return view


def _row(ok, detail, excerpt, index):
    text = excerpt or ""
    if len(text) > 200:
        text = text[:200]
    return {"ok": bool(ok), "detail": detail,
            "evidence": {"index": index, "excerpt": text}}


def _compile(pattern, key):
    try:
        return re.compile(pattern or "")
    except re.error as exc:
        raise GradingError(CHECK_ERROR, "bad regex: %s" % exc, key=key)


def _matched(view, pattern, key):
    rx = _compile(pattern, key)
    return [c for c in view.calls if rx.search(c["canonical"])]


def _check_call(view, check):
    matched = _matched(view, check.get("match") or "", "match")
    n = len(matched)
    mx = check.get("max", None)
    if mx == 0:
        ok = n == 0
    else:
        mn = check.get("min", 1)
        ok = n >= mn and (mx is None or n <= mx)
    src = matched[0] if matched else None
    return _row(ok, "matched %d" % n,
                src["canonical"] if src else "",
                src["index"] if src else -1)


def _check_first(view, check):
    if not view.calls:
        return _row(False, "no call", "", -1)
    first = view.calls[0]
    rx = _compile(check.get("match") or "", "match")
    ok = bool(rx.search(first["canonical"]))
    return _row(ok, "first is %s" % first["name"], first["canonical"], first["index"])


def _check_order(view, check):
    first_rx = _compile(check.get("first") or "", "first")
    before_rx = _compile(check.get("before") or "", "before")
    befores = [c for c in view.calls if before_rx.search(c["canonical"])]
    if not befores:
        return _row(True, "no before call", "", -1)
    for b in befores:
        earlier = any(first_rx.search(c["canonical"]) and c["index"] < b["index"]
                      for c in view.calls)
        if not earlier:
            return _row(False, "before call has no earlier first",
                        b["canonical"], b["index"])
    return _row(True, "first precedes before", befores[0]["canonical"], befores[0]["index"])


def _corpus(view, scope):
    texts = list(view.text_blocks) + list(view.plans)
    if scope == "final":
        return view.final
    if scope == "any":
        texts = texts + [c["canonical"] for c in view.calls]
    return "\n".join(texts)


def _check_text(view, check):
    scope = check.get("scope") or "final"
    corpus = _corpus(view, scope)
    rx = _compile(check.get("match") or "", "match")
    found = bool(rx.search(corpus or ""))
    present = check.get("present", True)
    ok = found if present else not found
    excerpt = ""
    if found and corpus:
        m = rx.search(corpus)
        excerpt = corpus[max(0, m.start() - 40):m.end() + 40] if m else corpus[:200]
    return _row(ok, "scope %s present=%s" % (scope, present), excerpt or corpus[:200], -1)


def _check_end(view, check):
    want = check.get("disposition") or ""
    if view.turn_end is None:
        return _row(False, "no_result", "", -1)
    is_error = bool(view.turn_end.get("is_error"))
    if want == "completed":
        ok = not is_error
    elif want == "error":
        ok = is_error
    else:
        ok = False
    return _row(ok, "is_error=%s subtype=%s" % (is_error, view.turn_end.get("subtype")),
                view.final[:200], -1)


def run_check(view, check):
    kind = check.get("kind")
    if kind not in KINDS:
        raise GradingError(CHECK_ERROR, "unknown kind %r" % kind, key="kind")
    if kind == "call":
        return _check_call(view, check)
    if kind == "first_call":
        return _check_first(view, check)
    if kind == "order":
        return _check_order(view, check)
    if kind == "text":
        return _check_text(view, check)
    return _check_end(view, check)


def grade(view, checks):
    out = []
    for check in checks:
        row = run_check(view, check)
        row["id"] = check.get("id") or ""
        out.append(row)
    return out


def _usable(view):
    if not view.turn_end or view.turn_end.get("is_error"):
        return False
    return bool(view.text_blocks or view.calls or view.plans)


def _message(raw):
    parts = [str(raw.get("result") or ""), str(raw.get("error") or ""),
             str(raw.get("message") or "")]
    return "\n".join(parts)


def classify(view, results=None, limits=None, problems=None):
    """Mechanical class for one transcript. Higher precedence wins in `primary`."""
    limits = limits or {}
    found = list(problems or [])
    results = results or []
    raw = view.raw_result or {}
    subtype = ""
    if view.turn_end:
        subtype = view.turn_end.get("subtype") or ""
    if not subtype:
        subtype = raw.get("subtype") or ""

    if limits.get("spawn_error"):
        found.append(Problem("infra", SPAWN_ERROR, limits.get("spawn_detail") or "spawn failed"))
    if limits.get("timed_out"):
        found.append(Problem("infra", TIMEOUT, "wall clock"))
    if (view.turn_end is None and not limits.get("spawn_error")
            and not limits.get("timed_out") and not limits.get("tool_cap")):
        found.append(Problem("infra", NO_RESULT, "no turn.end"))
    elif view.turn_end is not None:
        msg = _message(raw).lower()
        if subtype in ("error_max_turns",):
            found.append(Problem("model", MAX_TURNS, subtype))
        elif subtype in ("error_max_budget_usd", "error_max_budget"):
            found.append(Problem("infra", BUDGET_CAP, subtype))
        elif (raw.get("terminal_reason") == "api_error" or raw.get("api_error_status")
              or "failed to authenticate" in msg or "unauthorized" in msg
              or "invalid api key" in msg):
            found.append(Problem("infra", AUTH, "auth"))
        elif "rate limit" in msg or "rate_limit" in msg:
            found.append(Problem("infra", RATE_LIMIT, "rate limit"))
        elif "overloaded" in msg:
            found.append(Problem("infra", OVERLOADED, "overloaded"))
        elif view.turn_end.get("is_error"):
            found.append(Problem("infra", CLI_ERROR, subtype or "is_error"))
        elif not (view.text_blocks or view.calls or view.plans):
            found.append(Problem("infra", EMPTY_TURN, "no text and no call"))
        cap = limits.get("max_tool_calls")
        if cap is not None and len(view.calls) > cap:
            found.append(Problem("model", TOOL_CAP, "%d calls" % len(view.calls)))
        if _usable(view) and any(not r.get("ok") for r in results):
            found.append(Problem("model", BEHAVIOUR, "checks failed"))
    if limits.get("tool_cap"):
        found.append(Problem("model", TOOL_CAP, "stopped at the call cap"))
    expect = limits.get("fixture")
    if expect == "pass" and any(not r.get("ok") for r in results):
        found.append(Problem("grading", GOLDEN_FAILED, "golden fixture failed a check"))
    if expect == "fail":
        fail_ids = list(limits.get("fail_checks") or [])
        by_id = {r.get("id"): r for r in results}
        for fid in fail_ids:
            row = by_id.get(fid)
            if row is None or row.get("ok"):
                found.append(Problem("grading", MUST_FAIL_PASSED,
                                     "must-fail check %s passed" % fid))
    return found


def primary(problems):
    if not problems:
        return None
    rank = {name: i for i, name in enumerate(PRECEDENCE)}
    return sorted(problems, key=lambda p: (rank.get(p.cls, 99), p.reason))[0]
