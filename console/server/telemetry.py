"""Per-turn token and cost records.

Why this exists: two of the harness's stated goals — spend fewer tokens, and
retire skills that are no longer earning their place — are both unfalsifiable
without measurement. Before this module there was no number to argue with, so
"the workflow is leaner now" and "nobody uses that skill" were opinions.

## Shape

One JSON object per **turn**, appended to `{telemetry_dir}/{YYYY-MM}.jsonl`.
Append-only JSONL, not TOML: this is an event log, written from a live session
thread while a chat is streaming, and rewriting a whole document per turn would
be both slow and a corruption risk. Monthly files keep any one file small
enough to scan without an index.

## Cost, and refusing to invent it

`cost_usd` is recorded only when it is known:

- the backend reported it (Claude Code's result event carries `total_cost_usd`);
- or the model appears in `console/config/pricing.toml` and the rate is applied.

Neither -> the field is `null`, and every total that includes such a turn is
reported as **partial**, naming how many turns were unpriced. A missing rate
must never read as a free turn: silently substituting 0.0 makes an incomplete
total look like a cheap one, which is the exact opposite of the truth and would
send every decision this data exists to inform in the wrong direction.

## What is not here

No prompt text, no tool arguments, no file contents — a token count and a model
id, nothing that would make the log sensitive to read or unsafe to commit.
"""

import json
import os
import threading
from datetime import datetime, timezone

from . import boards as boards_mod
from . import tomlio

DEFAULT_DIR = os.path.join("knowledge-center", "telemetry")
PRICING_REL = os.path.join("console", "config", "pricing.toml")

_write_lock = threading.Lock()
_pricing_cache = {}

#: Every field a record carries. Kept explicit so a reader can rely on the
#: shape and an aggregate can never silently drop a column.
FIELDS = ("ts", "session", "backend", "model", "mode", "ticket", "skill",
          "persona", "input_tokens", "output_tokens", "cost_usd",
          "cost_source", "duration_ms", "is_error")


def telemetry_dir(repo_root):
    cfg = boards_mod.load_console_config(repo_root)
    rel = cfg.get("telemetry", {}).get("dir") or DEFAULT_DIR
    return os.path.join(repo_root, rel)


# --------------------------------------------------------------- pricing ----

def load_pricing(repo_root, force=False):
    """model id -> {input, output} in USD per million tokens."""
    if not force and repo_root in _pricing_cache:
        return _pricing_cache[repo_root]
    path = os.path.join(repo_root, PRICING_REL)
    table = {}
    if os.path.isfile(path):
        data = tomlio.load(path)
        for row in data.get("model", []):
            mid = str(row.get("id", "")).strip()
            if not mid:
                continue
            table[mid] = {
                "input": float(row.get("input_per_mtok", 0) or 0),
                "output": float(row.get("output_per_mtok", 0) or 0),
            }
    _pricing_cache[repo_root] = table
    return table


def price(repo_root, model, input_tokens, output_tokens):
    """(cost, source) — cost is None when the model has no published rate.

    Matching is exact, then longest-prefix: a pinned `claude-opus-5` and a
    dated `claude-opus-5-20260114` should price the same without the table
    needing a row per release. An alias like `opus` matches only if the table
    lists it, because an alias points at a different model over time and
    guessing which one would produce a confidently wrong number.
    """
    model = (model or "").strip()
    if not model:
        return None, "unknown"
    table = load_pricing(repo_root)
    row = table.get(model)
    if row is None:
        candidates = [k for k in table if model.startswith(k)]
        if candidates:
            row = table[max(candidates, key=len)]
    if row is None:
        return None, "unknown"
    cost = (input_tokens / 1_000_000.0) * row["input"] + \
           (output_tokens / 1_000_000.0) * row["output"]
    return round(cost, 6), "table"


# --------------------------------------------------------------- writing ----

def _month_path(repo_root, when):
    return os.path.join(telemetry_dir(repo_root), when.strftime("%Y-%m") + ".jsonl")


def record_turn(repo_root, *, session="", backend="", model="", mode="",
                ticket="", skill="", persona="", input_tokens=0,
                output_tokens=0, cost_usd=None, duration_ms=0, is_error=False,
                when=None):
    """Append one turn. Returns the record, or None if it could not be written.

    Never raises. This is called from a live session's reader thread while a
    chat is streaming: losing a measurement is a cost worth paying, killing the
    chat that produced it is not.
    """
    when = when or datetime.now(timezone.utc)
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)

    if cost_usd is None:
        cost_usd, source = price(repo_root, model, input_tokens, output_tokens)
    else:
        cost_usd, source = round(float(cost_usd), 6), "backend"

    record = {
        "ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": session,
        "backend": backend,
        "model": model,
        "mode": mode,
        "ticket": ticket,
        "skill": skill,
        "persona": persona,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "cost_source": source,
        "duration_ms": int(duration_ms or 0),
        "is_error": bool(is_error),
    }
    try:
        path = _month_path(repo_root, when)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        line = json.dumps(record, separators=(",", ":")) + "\n"
        with _write_lock:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
    except OSError:
        return None
    return record


# --------------------------------------------------------------- reading ----

def read_records(repo_root, since=None, until=None):
    """Every record, oldest first. A corrupt line is skipped, not fatal —
    a truncated final line from a killed process must not hide the month."""
    folder = telemetry_dir(repo_root)
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(folder, name), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                ts = rec.get("ts", "")
                if since and ts < since:
                    continue
                if until and ts > until:
                    continue
                out.append(rec)
    out.sort(key=lambda r: r.get("ts", ""))
    return out


GROUPS = ("ticket", "model", "skill", "persona", "backend", "day")


def _group_key(record, group):
    if group == "day":
        return (record.get("ts") or "")[:10] or "(unknown)"
    return record.get(group) or "(none)"


def summarize(repo_root, group="ticket", ticket=None, skill=None,
              since=None, until=None):
    """Totals per group, plus an explicit account of what could not be priced.

    `unpriced` is not a footnote: a total drawn from records where a third of
    turns had no rate is a different number from a complete one, and the caller
    has to be able to tell them apart.
    """
    if group not in GROUPS:
        raise ValueError("unknown group %r; valid: %s" % (group, ", ".join(GROUPS)))

    records = read_records(repo_root, since=since, until=until)
    if ticket:
        records = [r for r in records if r.get("ticket") == ticket]
    if skill:
        records = [r for r in records if r.get("skill") == skill]

    rows = {}
    for rec in records:
        key = _group_key(rec, group)
        row = rows.setdefault(key, {
            "key": key, "turns": 0, "input_tokens": 0, "output_tokens": 0,
            "cost_usd": 0.0, "unpriced_turns": 0, "errors": 0,
        })
        row["turns"] += 1
        row["input_tokens"] += int(rec.get("input_tokens") or 0)
        row["output_tokens"] += int(rec.get("output_tokens") or 0)
        if rec.get("is_error"):
            row["errors"] += 1
        cost = rec.get("cost_usd")
        if cost is None:
            row["unpriced_turns"] += 1
        else:
            row["cost_usd"] += float(cost)

    for row in rows.values():
        row["cost_usd"] = round(row["cost_usd"], 4)
        row["tokens"] = row["input_tokens"] + row["output_tokens"]
        row["cost_complete"] = row["unpriced_turns"] == 0

    ordered = sorted(rows.values(), key=lambda r: (-r["tokens"], r["key"]))
    total_unpriced = sum(r["unpriced_turns"] for r in ordered)
    return {
        "group": group,
        "rows": ordered,
        "totals": {
            "turns": sum(r["turns"] for r in ordered),
            "input_tokens": sum(r["input_tokens"] for r in ordered),
            "output_tokens": sum(r["output_tokens"] for r in ordered),
            "tokens": sum(r["tokens"] for r in ordered),
            "cost_usd": round(sum(r["cost_usd"] for r in ordered), 4),
            "unpriced_turns": total_unpriced,
            "cost_complete": total_unpriced == 0,
        },
    }


def skill_usage(repo_root, all_skills=None):
    """Invocation counts per skill, and — the point of the report — the skills
    that have never fired.

    A never-fired skill is a *candidate* for retirement, not a verdict: a skill
    invoked by a human typing `/name` in a terminal leaves no record here, and
    a skill added last week has had no chance. The caller is told the window
    the data covers so it can weigh that.
    """
    if all_skills is None:
        all_skills = _discover_skills(repo_root)
    records = read_records(repo_root)

    counts = {}
    for rec in records:
        name = rec.get("skill") or ""
        if not name:
            continue
        row = counts.setdefault(name, {"skill": name, "turns": 0, "tokens": 0})
        row["turns"] += 1
        row["tokens"] += int(rec.get("input_tokens") or 0) + \
            int(rec.get("output_tokens") or 0)

    fired = sorted(counts.values(), key=lambda r: (-r["turns"], r["skill"]))
    fired_names = set(counts)
    never = sorted(s for s in all_skills if s not in fired_names)
    unknown = sorted(fired_names - set(all_skills))

    window = ""
    if records:
        window = "%s .. %s" % (records[0].get("ts", ""), records[-1].get("ts", ""))

    return {
        "fired": fired,
        "never_fired": never,
        "unknown_skills": unknown,
        "total_skills": len(all_skills),
        "records": len(records),
        "window": window,
    }


def _discover_skills(repo_root):
    base = os.path.join(repo_root, ".claude", "skills")
    if not os.path.isdir(base):
        return []
    return sorted(
        name for name in os.listdir(base)
        if not name.startswith((".", "_"))
        and os.path.isfile(os.path.join(base, name, "SKILL.md"))
    )


# -------------------------------------------------------------- rendering ---

def format_summary(summary):
    group = summary["group"]
    rows = summary["rows"]
    if not rows:
        return "No telemetry recorded yet."

    width = max([len(r["key"]) for r in rows] + [len(group)])
    lines = ["%-*s %6s %12s %12s %10s" % (width, group.upper(), "TURNS",
                                          "IN", "OUT", "COST")]
    for row in rows:
        cost = "%.4f" % row["cost_usd"]
        if not row["cost_complete"]:
            cost += "*"
        lines.append("%-*s %6d %12d %12d %10s" % (
            width, row["key"], row["turns"], row["input_tokens"],
            row["output_tokens"], cost))

    totals = summary["totals"]
    lines.append("-" * (width + 44))
    total_cost = "%.4f" % totals["cost_usd"]
    if not totals["cost_complete"]:
        total_cost += "*"
    lines.append("%-*s %6d %12d %12d %10s" % (
        width, "TOTAL", totals["turns"], totals["input_tokens"],
        totals["output_tokens"], total_cost))
    if not totals["cost_complete"]:
        lines.append("")
        lines.append("* partial: %d turn(s) had no published rate for their "
                     "model and are excluded from cost." % totals["unpriced_turns"])
        lines.append("  Add the model to console/config/pricing.toml to price them.")
    return "\n".join(lines)


def format_skill_usage(report):
    lines = []
    if report["fired"]:
        width = max(len(r["skill"]) for r in report["fired"])
        lines.append("%-*s %6s %12s" % (width, "SKILL", "TURNS", "TOKENS"))
        for row in report["fired"]:
            lines.append("%-*s %6d %12d" % (width, row["skill"], row["turns"],
                                            row["tokens"]))
    else:
        lines.append("No skill invocations recorded yet.")

    lines.append("")
    lines.append("Never fired (%d of %d skills):"
                 % (len(report["never_fired"]), report["total_skills"]))
    for name in report["never_fired"]:
        lines.append("  %s" % name)
    if report["unknown_skills"]:
        lines.append("")
        lines.append("Recorded but no longer on disk: %s"
                     % ", ".join(report["unknown_skills"]))
    lines.append("")
    lines.append("From %d record(s)%s. A skill invoked by hand in a terminal "
                 "leaves no record here," % (report["records"],
                                             " covering " + report["window"]
                                             if report["window"] else ""))
    lines.append("so 'never fired' is a candidate for review, not a verdict.")
    return "\n".join(lines)
