"""Reads the EXISTING per-author daily log files that `log-work`/`work-summary`
already define (`knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{slug}.md`) and
turns them into structured timesheet data for the Work/Analytics tabs.

This does not introduce a second storage format — it's a deterministic-code
implementation of the hour-allocation algorithm `work-summary/SKILL.md`
already specifies in prose ("user overrides -> weight 1-5 -> proportional
split -> round 0.25h -> sum >= --hours"), so the console and the skill agree
on one answer instead of the LLM re-deriving it by hand each time.
"""

import glob
import os
import re

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_FIELD_RE = re.compile(r"^([a-zA-Z_]+):\s*(.*)$")
_WORK_LINE_RE = re.compile(
    r"^-\s*\*\*([^*]+)\*\*\s*\[([^\]]+)\]\s*(?:~([\d.]+)h\s*)?(.*)$"
)

DEFAULT_DAY_FLOOR = 8.0


def _parse_frontmatter(text):
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        fm = _FIELD_RE.match(line.strip())
        if fm:
            fields[fm.group(1)] = fm.group(2).strip().strip('"')
    return fields


def parse_log_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    fm = _parse_frontmatter(text)
    entries = []
    in_work = False
    for line in text.splitlines():
        if line.strip() == "## Work":
            in_work = True
            continue
        if in_work and line.startswith("## "):
            in_work = False
        if not in_work:
            continue
        m = _WORK_LINE_RE.match(line.strip())
        if m:
            ticket, category, hours, activity_text = m.groups()
            entries.append(
                {
                    "ticket": ticket.strip(),
                    "category": category.strip(),
                    "hours": float(hours) if hours else None,
                    "text": activity_text.strip(),
                }
            )
    return {
        "date": fm.get("date", ""),
        "author": fm.get("author", ""),
        "author_slug": fm.get("author_slug", ""),
        "path": path,
        "entries": entries,
    }


def _log_dir(repo_root):
    return os.path.join(repo_root, "knowledge-center", "logs")


def find_log_files(repo_root, start_date=None, end_date=None, author_slug=None):
    """start_date/end_date are 'YYYY-MM-DD' strings, inclusive. None means
    unbounded on that side."""
    pattern = os.path.join(_log_dir(repo_root), "*", "*.md")
    files = []
    for path in glob.glob(pattern):
        name = os.path.basename(path)
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\.(.+)\.md$", name)
        if not m:
            continue
        date, slug = m.group(1), m.group(2)
        if start_date and date < start_date:
            continue
        if end_date and date > end_date:
            continue
        if author_slug and slug != author_slug:
            continue
        files.append(path)
    return sorted(files)


def known_authors(repo_root):
    """Every author slug that has at least one log file, with the display name
    from the newest file that carries one. Lets the Work tab offer a real
    author filter instead of asking the user to type a slug."""
    seen = {}
    for path in find_log_files(repo_root):
        name = os.path.basename(path)
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\.(.+)\.md$", name)
        if not m:
            continue
        date, slug = m.group(1), m.group(2)
        prior = seen.get(slug)
        if prior and prior["last_seen"] >= date:
            continue
        parsed = parse_log_file(path)
        seen[slug] = {
            "slug": slug,
            "name": parsed.get("author") or slug,
            "last_seen": date,
        }
    return sorted(seen.values(), key=lambda a: a["name"].lower())


def _round_quarter(value):
    return round(value * 4) / 4.0


def allocate_hours(entries, day_floor=DEFAULT_DAY_FLOOR):
    """Per-entry hours: explicit ~{h} values stand; entries without one
    split (day_floor - explicit_sum) evenly, rounded to 0.25h with a
    largest-remainder adjustment so the weightless entries' sum lands
    exactly on the remaining floor. Entries are mutated in place with an
    'allocated_hours' key and returned."""
    explicit = [e for e in entries if e["hours"] is not None]
    weightless = [e for e in entries if e["hours"] is None]

    for e in explicit:
        e["allocated_hours"] = e["hours"]

    if not weightless:
        return entries

    explicit_sum = sum(e["hours"] for e in explicit)
    remaining = max(0.0, day_floor - explicit_sum)
    share = remaining / len(weightless) if weightless else 0.0
    rounded = [_round_quarter(share) for _ in weightless]

    # Largest-remainder-style fixup: nudge entries by 0.25h until the
    # weightless sum matches `remaining` as closely as a 0.25h grid allows.
    target_ticks = round(remaining / 0.25)
    current_ticks = sum(round(r / 0.25) for r in rounded)
    diff = target_ticks - current_ticks
    i = 0
    while diff != 0 and rounded:
        idx = i % len(rounded)
        if diff > 0:
            rounded[idx] += 0.25
            diff -= 1
        elif rounded[idx] > 0:
            rounded[idx] -= 0.25
            diff += 1
        i += 1
        if i > 10000:
            break

    for e, hours in zip(weightless, rounded):
        e["allocated_hours"] = hours

    return entries


def day_timesheet(repo_root, date, author_slug=None, day_floor=DEFAULT_DAY_FLOOR):
    """Returns one timesheet per author found for that date (a list, since
    multiple authors can have logs on the same day)."""
    files = find_log_files(repo_root, start_date=date, end_date=date, author_slug=author_slug)
    sheets = []
    for path in files:
        parsed = parse_log_file(path)
        allocate_hours(parsed["entries"], day_floor)
        by_category = {}
        for e in parsed["entries"]:
            cat = by_category.setdefault(e["category"], {"total": 0.0, "tickets": {}})
            cat["total"] += e["allocated_hours"]
            t = cat["tickets"].setdefault(
                e["ticket"], {"hours": 0.0, "activities": [], "pinned": False}
            )
            t["hours"] += e["allocated_hours"]
            t["activities"].append(e["text"])
            # An explicitly stated ~Nh is a different claim from an allocated
            # share of the day floor; the UI marks it so the two aren't
            # presented as equally precise.
            if e["hours"] is not None:
                t["pinned"] = True
        total = sum(c["total"] for c in by_category.values())
        sheets.append(
            {
                "date": parsed["date"] or date,
                "author": parsed["author"],
                "author_slug": parsed["author_slug"],
                "total_hours": round(total, 2),
                "by_category": by_category,
            }
        )
    return sheets


def range_summary(repo_root, start_date, end_date, author_slug=None, day_floor=DEFAULT_DAY_FLOOR):
    """Aggregates across a date range for the Analytics tab: hours by day,
    by author, by ticket, and category split. Does not double-count — each
    day/author file contributes its own allocation independently."""
    files = find_log_files(repo_root, start_date, end_date, author_slug)
    hours_by_day = {}
    hours_by_author = {}
    hours_by_ticket = {}
    category_totals = {}

    for path in files:
        parsed = parse_log_file(path)
        allocate_hours(parsed["entries"], day_floor)
        day_total = sum(e["allocated_hours"] for e in parsed["entries"])
        date = parsed["date"]
        author = parsed["author"] or parsed["author_slug"]

        hours_by_day[date] = hours_by_day.get(date, 0.0) + day_total
        hours_by_author[author] = hours_by_author.get(author, 0.0) + day_total

        for e in parsed["entries"]:
            hours_by_ticket[e["ticket"]] = hours_by_ticket.get(e["ticket"], 0.0) + e["allocated_hours"]
            category_totals[e["category"]] = category_totals.get(e["category"], 0.0) + e["allocated_hours"]

    def _round_map(d):
        return {k: round(v, 2) for k, v in d.items()}

    return {
        "hours_by_day": _round_map(hours_by_day),
        "hours_by_author": _round_map(hours_by_author),
        "hours_by_ticket": _round_map(hours_by_ticket),
        "category_split": _round_map(category_totals),
        "files_scanned": len(files),
    }
