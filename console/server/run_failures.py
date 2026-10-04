"""Run failure policy, pure (T-020 FR-11..FR-15). No I/O, no clock reads.

`classify` turns the evidence a finished turn leaves behind into one failure
class. Markers are ported from Paperclip's claude-local adapter
(`packages/adapters/claude-local/src/server/parse.ts`) and applied only to the
terminal fields of a FAILED turn, never to assistant prose, so a successful
reply that merely says "unauthorized" or "rate limit" is not a failure.
"""

import re
import zoneinfo
from datetime import datetime, timedelta, timezone

#: Every class a Run can end with. `output_cap` and `stalled` are set by their
#: own detectors (the per-turn cap, the watchdog); `classify` never returns them.
CLASSES = (
    "auth_required", "model_not_found", "max_turns", "unknown_session",
    "poisoned_session", "image_error", "refusal", "quota", "transient_upstream",
    "process_lost", "output_cap", "stalled", "unclassified",
)

#: The only classes a retry may follow (FR-15 table); everything else is final.
RETRYABLE = frozenset({"quota", "transient_upstream", "max_turns", "process_lost"})
NON_RETRYABLE = frozenset(CLASSES) - RETRYABLE

DETAIL_MAX = 200

_I = re.IGNORECASE
_LOGIN = re.compile(
    r"not\s+logged\s+in|please\s+log\s+in|please\s+run\s+(?:`?claude\s+login`?|/login)"
    r"|login\s+required|requires\s+login|unauthorized|authentication\s+required"
    r"|invalid\s+api\s+key", _I)
_AUTH_TOKEN = re.compile(
    r"authentication[_\s-](?:failed|error)|failed\s+to\s+authenticate|invalid\s+bearer\s+token"
    r"|(?:invalid|expired|revoked).{0,40}(?:bearer|oauth|access)\s+token"
    r"|(?:bearer|oauth|access)\s+token.{0,40}(?:is\s+)?(?:invalid|expired|revoked)",
    _I | re.DOTALL)
_MODEL = re.compile(
    r"model[\s_-]*(?:not[\s_-]*found|does not exist|unknown|invalid)|unknown[\s_-]*model", _I)
_UNKNOWN_SESSION = re.compile(
    r"no conversation found with session id|unknown session|session .* not found"
    r"|not a valid UUID|--resume requires a valid session|is not a UUID"
    r"|does not match any session title", _I)
_POISONED = re.compile(r"diagnostics\.previous_message_id.*starts with `msg_`", _I)
_IMAGE = re.compile(r"could not process image", _I)
_QUOTA = re.compile(
    r"you(?:'|\u2019)ve\s+hit\s+your\s+(?:\w+\s+)?limit|session\s+limit\s+(?:reached|exceeded)"
    r"|out\s+of\s+extra\s+usage|extra\s+usage\b|claude\s+usage\s+limit\s+reached"
    r"|5[-\s]?hour\s+limit\s+reached|weekly\s+limit\s+reached|usage\s+limit\s+reached"
    r"|usage\s+cap\s+reached|servicequotaexceededexception"
    r"|at\s+capacity|capacity\s+limit", _I)
_TRANSIENT = re.compile(
    r"rate[-\s]?limit(?:ed)?|rate_limit_error|too\s+many\s+requests|\b429\b"
    r"|overloaded(?:_error)?|server\s+overloaded|service\s+unavailable|\b503\b|\b529\b"
    r"|high\s+demand|try\s+again\s+later|temporarily\s+unavailable|temporary\s+errors"
    r"|throttl(?:ed|ing)|throttlingexception", _I)

_MAX_TURNS_STOPS = frozenset({"max_turns", "error_max_turns"})
_TRANSIENT_STATUS = frozenset({429, 503, 529})


def _failed(turn_end, exit_code):
    """True when the turn or its process ended badly. A synthetic
    `process_exit` turn with exit 0 is neither a success nor a failure."""
    if turn_end and turn_end.get("subtype") == "process_exit":
        return bool(exit_code)
    if exit_code:
        return True
    if turn_end is None:
        return exit_code is None
    return bool(turn_end.get("is_error")) or (turn_end.get("subtype") or "success") != "success"


def _terminal_text(turn_end):
    """The result and error fields of the final turn, nothing else."""
    parts = [turn_end.get("result") or "", turn_end.get("error") or ""]
    parts += [str(e) for e in turn_end.get("errors") or []]
    return "\n".join(p for p in parts if p)


def _verdict(cls, detail=""):
    return {"class": cls, "retryable_class": cls in RETRYABLE,
            "detail": (detail or "").strip()[:DETAIL_MAX], "retry_not_before": ""}


#: Quota marker, then "resets [at] <time> [(zone)]" (Paperclip `parse.ts`).
_RESET_PROSE = re.compile(
    r"(?:" + _QUOTA.pattern + r").{0,120}?\bresets?\s+(?:at\s+)?([^\n()]+?)"
    r"(?:\s*\(([^)]+)\))?(?:[.!]|\n|$)", _I | re.DOTALL)
#: Codex says "try again at 5pm" rather than "resets at 5pm".
_TRY_AGAIN = re.compile(
    r"\btry\s+again\s+at\s+([^\n()]+?)(?:\s*\(([^)]+)\))?(?:[.!]|\n|$)", _I)
_CLOCK = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\.?", _I)
#: Epoch values above this are milliseconds.
_MS_THRESHOLD = 1e11
_DEFAULT_HORIZON = 8 * 86400


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _in_window(when, now, cfg):
    horizon = (cfg or {}).get("quota_parse_horizon_secs", _DEFAULT_HORIZON)
    return now < when <= now + timedelta(seconds=horizon)


def _notice_reset(rate_limit, now, cfg):
    if (rate_limit or {}).get("status") != "rejected":
        return ""
    raw = rate_limit.get("resets_at")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw <= 0:
        return ""
    secs = raw / 1000 if raw > _MS_THRESHOLD else raw
    try:
        when = datetime.fromtimestamp(secs, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return _iso(when) if _in_window(when, now, cfg) else ""


def _prose_reset(text, now, cfg, zone):
    found = _RESET_PROSE.search(text or "") or _TRY_AGAIN.search(text or "")
    if not found:
        return ""
    clock = _CLOCK.fullmatch(found.group(1).strip())
    if not clock:
        return ""
    hour, minute, ampm = int(clock.group(1)), int(clock.group(2) or 0), clock.group(3).lower()
    if not 1 <= hour <= 12 or minute > 59:
        return ""
    hour = hour % 12 + (12 if ampm == "p" else 0)
    name = (found.group(2) or "").strip()
    if not name:
        tz = now.astimezone().tzinfo  # host-local
    elif name.upper() in ("UTC", "GMT"):
        tz = timezone.utc  # no tz database needed
    else:
        try:
            tz = (zone or zoneinfo.ZoneInfo)(name)
        except (KeyError, ValueError, OSError, TypeError):
            return ""  # unknown or unavailable zone: unknown reset, class stays quota
    here = now.astimezone(tz)
    when = here.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if when <= here:
        when += timedelta(days=1)  # wall-clock arithmetic in the zone
    return _iso(when) if _in_window(when.astimezone(timezone.utc), now, cfg) else ""


def parse_reset(rate_limit, text, now, cfg, _zone=None):
    """UTC ISO `...Z` of when a quota window reopens, or "" when unknown.

    (a) a `rejected` rate_limit notice's `resets_at` (epoch seconds or ms);
    (b) "resets [at] 4pm (Zone)" prose after a quota marker, next occurrence of
    that wall-clock time. Accepted only inside `(now, now + horizon]`. `now` is
    an aware datetime; `_zone` replaces `zoneinfo.ZoneInfo` (test seam)."""
    return _notice_reset(rate_limit, now, cfg) or _prose_reset(text, now, cfg, _zone)


def _timed(verdict, rate_limit, text, now, cfg):
    if now is not None:
        verdict["retry_not_before"] = parse_reset(rate_limit, text, now, cfg)
    return verdict


def classify(turn_end, rate_limit, exit_code, stderr_tail, now=None, cfg=None):
    """`{class, retryable_class, detail, retry_not_before}` for one finished
    turn. `class` is "" when the turn did not fail. `retry_not_before` is ""
    unless `now` (aware datetime) is given: then quota/transient carry the
    `parse_reset` result (FR-12)."""
    te = turn_end or {}
    stop = (te.get("stop_reason") or "").lower()
    failed = _failed(turn_end, exit_code)
    refused = stop == "refusal" or (te.get("subtype") or "").lower() == "refusal"
    if not failed and not refused:
        return _verdict("")
    text = _terminal_text(te)
    detail = text or (stderr_tail or "").strip() or "exit %s" % exit_code
    status = te.get("api_error_status")
    wide = text + "\n" + (stderr_tail or "")  # structured fields plus stderr

    if failed:
        if status == 401 or _LOGIN.search(text) or _AUTH_TOKEN.search(text):
            return _verdict("auth_required", detail)
        if _MODEL.search(wide):
            return _verdict("model_not_found", detail)
        if te.get("subtype") == "error_max_turns" or stop in _MAX_TURNS_STOPS:
            return _verdict("max_turns", detail)
        if _UNKNOWN_SESSION.search(wide):
            return _verdict("unknown_session", detail)
        if _POISONED.search(wide):
            return _verdict("poisoned_session", detail)
        if _IMAGE.search(wide):
            return _verdict("image_error", detail)
    # Structured refusal counts even on a clean exit (FR-11).
    if refused:
        return _verdict("refusal", detail)
    if _QUOTA.search(wide) or (rate_limit or {}).get("status") == "rejected":
        return _timed(_verdict("quota", detail), rate_limit, wide, now, cfg)
    if status in _TRANSIENT_STATUS or _TRANSIENT.search(wide):
        return _timed(_verdict("transient_upstream", detail), rate_limit, wide, now, cfg)
    if turn_end is None or te.get("subtype") == "process_exit":
        return _verdict("process_lost", detail)
    return _verdict("unclassified", detail)


# -- FR-13: liveness of a clean turn -----------------------------------------

LIVENESS_STATES = ("completed", "advanced", "plan_only", "empty", "blocked", "failed")
REASON_MAX = 200

#: Tools that change files. `Bash` is deliberately absent: it is how an agent
#: looks at things as often as it changes them, so it is never evidence.
FILE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
#: Console verbs that change tickets or trackers; the same verb reaches a model
#: as `mcp__console__<id>` (CLI backends) or `console_<id with _>` (API).
MUTATING_VERBS = frozenset({
    "ticket-move", "ticket-set", "claim", "comment", "tracker-add",
    "tracker-update", "kickoff", "delegate",
})
_MUTATING_NAMES = frozenset(
    {"mcp__console__" + v for v in MUTATING_VERBS}
    | {"console_" + v.replace("-", "_") for v in MUTATING_VERBS})

_PLAN_VERBS = (r"(?:inspect|check|review|look|investigate|analy[sz]e|open|read|start|begin"
               r"|work on|implement|fix|test|update|create|add)")
#: Planning-only opening (ported from Paperclip `run-liveness.ts:65`), anchored
#: to the START of the reply: "the next update will ship" in the middle of a
#: genuine summary must not read as a plan.
PLANNING_ONLY = re.compile(
    r"\A\s*(?:(?:ok(?:ay)?|sure|alright|right)[,.!]?\s+)?"
    r"(?:i(?:'ll|\u2019ll|\s+will|'m\s+going\s+to|\s+am\s+going\s+to)|let\s+me|i\s+need\s+to"
    r"|my\s+next\s+step\s+is|the\s+next\s+step\s+is|next,?\s+i(?:'ll|\s+will))"
    r"\s+(?:first\s+)?" + _PLAN_VERBS + r"\b", _I)
#: A reply that is a "Next steps:" / "Plan:" header line.
NEXT_STEPS = re.compile(r"^\s*(?:next\s+steps?|plan)\s*:", _I | re.MULTILINE)
_BLOCKER = re.compile(
    r"\b(?:blocked|can(?:'|\u2019)?t\s+proceed|cannot\s+proceed|unable\s+to\s+proceed|waiting\s+on"
    r"|need(?:s|ed)?\s+.{0,80}\b(?:approval|access|credentials?|secret|api\s+key|token|input|clarification)"
    r"|requires?\s+.{0,80}\b(?:approval|access|credentials?|secret|api\s+key|token|input|clarification))\b",
    _I)
_NOT_BLOCKED = re.compile(r"\b(?:not\s+blocked|no\s+blockers?|unblocked)\b", _I)
_READ_ONLY_MODES = frozenset({"plan", "ask"})


def tool_evidence(tools):
    """`{tools, count}` from a turn's tool-name counter: file-mutating tools and
    console mutating verbs only (counted by call), never `Bash` or reads."""
    n = 0
    for name, times in (tools or {}).items():
        if name in FILE_TOOLS or name in _MUTATING_NAMES:
            n += int(times or 0)
    return {"tools": n, "count": n, "critical_question": False}


def _reason(text):
    return " ".join(str(text or "").split())[:REASON_MAX]


def liveness(turn, mode, evidence, ticket_state, text):
    """`{state, reason}` for a turn that ended. Durable evidence beats prose.

    `evidence` is `{count, critical_question}` (see `tool_evidence` and
    `run_sync.collect_evidence`); `ticket_state` is the ticket's lane or "".
    Order: failed turn, structural blocker (lane or a new critical question),
    evidence (advanced, or completed when the ticket is done), then prose: an
    empty reply is `empty`, a planning-only opening in a writing mode is
    `plan_only`, a stated blocker is `blocked`, anything else `completed`. In
    `plan` / `ask` mode a non-empty reply is `advanced` and never `plan_only`
    (BR-10): reading and proposing is the whole job there.
    """
    ev = evidence or {}
    reply = (text or "").strip()
    if turn and (turn.get("is_error") or str(turn.get("subtype") or "").startswith("error")):
        return {"state": "failed", "reason": _reason(turn.get("subtype") or "turn error")}
    count = int(ev.get("count") or 0)
    if ticket_state == "blocked":
        return {"state": "blocked", "reason": "ticket lane is blocked"}
    if ev.get("critical_question"):
        return {"state": "blocked", "reason": "a new critical question is open"}
    if count:
        if ticket_state == "done":
            return {"state": "completed", "reason": "%d durable action(s); ticket is done" % count}
        return {"state": "advanced", "reason": "%d durable action(s)" % count}
    if not reply:
        return {"state": "empty", "reason": "no reply text and no durable action"}
    if mode in _READ_ONLY_MODES:
        return {"state": "advanced", "reason": "reply in %s mode: %s" % (mode, _reason(reply))}
    if _BLOCKER.search(reply) and not _NOT_BLOCKED.search(reply):
        return {"state": "blocked", "reason": _reason(reply)}
    if PLANNING_ONLY.search(reply) or NEXT_STEPS.search(reply):
        return {"state": "plan_only", "reason": "reply only plans: " + _reason(reply)}
    return {"state": "completed", "reason": _reason(reply)}



# -- FR-15: retry table -------------------------------------------------------

ATTEMPTS_KEPT = 10
_QUOTA_PAD_SECS = 60  # after the window reopens, before the retry fires


def _parse_utc(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _retry_delay(cls, prior, failure, now, cfg):
    """Seconds to wait before retry number `prior + 1`, or None when this
    failure may not be retried at all (budget used, or a quota whose reset is
    unknown or beyond `quota_max_wait_secs`). Fail closed (BR-2, BR-3)."""
    row = cfg["classes"].get(cls)
    if not row or prior >= row["max"]:
        return None
    delays = row["delays"]
    delay = delays[min(prior, len(delays) - 1)]
    if cls == "quota":
        reset = _parse_utc(failure.get("retry_not_before"))
        if reset is None:
            return None
        until = (reset - now).total_seconds()
        if until > cfg["quota_max_wait_secs"]:
            return None
        delay = max(delay, until + _QUOTA_PAD_SECS)
    return delay


def decide(run, failure, now, cfg):
    """The patch for a failed attempt: schedule a retry or fail for good.

    `failure` is a `classify` verdict, `now` an aware datetime, `cfg` the
    `run_config.retry_cfg` dict. Retryable only for the four table classes,
    bounded per class and in total, and never due before `retry_not_before`
    (BR-4). The patch carries the attempt history (last 10) either way."""
    cls = failure.get("class") or "unclassified"
    reset = failure.get("retry_not_before") or ""
    attempt = int(run.get("attempt") or 1)
    history = list(run.get("attempts") or [])
    prior = sum(1 for a in history if a.get("failure_class") == cls)
    stamp = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    started = history[-1].get("ended") if history else run.get("created", "")
    history.append({"n": attempt, "started": started or "", "ended": stamp,
                    "failure_class": cls})
    patch = {"failure_class": cls, "failure_detail": failure.get("detail", ""),
             "retry_not_before": reset, "attempts": history[-ATTEMPTS_KEPT:]}

    budget_left = attempt - 1 < cfg["max_total_retries"]
    delay = (_retry_delay(cls, prior, failure, now, cfg)
             if cls in RETRYABLE and budget_left else None)
    if delay is not None:
        due = max(now + timedelta(seconds=delay), _parse_utc(reset) or now)
        patch.update(state="scheduled_retry", attempt=attempt,
                     retry_due=due.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return patch
    spent = prior >= cfg["classes"].get(cls, {}).get("max", 0)
    exhausted = cls in RETRYABLE and (not budget_left or spent)
    patch.update(state="failed", ended=stamp,
                 end_reason="retry_exhausted" if exhausted else cls)
    return patch
