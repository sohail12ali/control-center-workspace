"""close-check: a read-only verdict on whether a ticket's evidence supports closing it
(T-021 FR-8). Never writes, never runs a subprocess or git, never raises.

`accepted` means a cited file, line, test name or Run EXISTS. It does not mean the
claim is true or that a test passed; every result states `basis: "existence"`.

Evidence reference grammar, read from the Evidence cell of a verification table only:
    dir/file.ext[:N[-M]][::name]      a file path (a slash, a file extension) under the repo root, else under the ticket dir
    T-018-decision-log.md             an artifact name in the ticket dir (or its own ticket's)
    run:<12 hex>                      a Run that exists and is in state `done`
Everything else (bare file names, commands, counts, timings, prose, backslash or
absolute paths, anything inside a URL, anything leaving the repo) is `unverifiable`:
never accepted, never missing.
"""

import os
import re

from . import runs as runs_mod
from . import tickets as tickets_mod

BASIS = "existence"
ACCEPTED, MISSING, UNVERIFIABLE = "accepted", "missing", "unverifiable"
PASS, DESCOPED, NOT_PASS = "pass", "descoped", "not_pass"

_PASS_WORDS = ("PASS", "PASSED", "MET")
_DESCOPED_WORDS = ("DEFERRED", "CUT", "DROPPED")
_FAIL_WORDS = ("PENDING", "PARTIAL", "FAIL", "FAILED", "BLOCKED")

_DIR = r"\.?[\w\-]+"
_FILE = r"[\w\-]+(?:\.[\w\-]+)*\.[A-Za-z]\w{0,5}(?!\w)"
_NAME = r"(?:::[\w\[\].\-]+)+"
_PATH = r"(?P<path>(?:%s/)+%s)(?::(?P<n>\d+)(?:-(?P<m>\d+))?)?(?P<name>%s)?" % (_DIR, _FILE, _NAME)
_ARTIFACT = r"(?P<art>(?:CC-)?T-?\d+-[\w\-]+\.md)"
_RUN = r"(?P<run>run:[0-9a-f]{12})"
# A match may not start inside a longer token: not after a word char, `.`, `-`,
# `/`, `\` or `:` (that rules out URLs, absolute and Windows paths).
_START = r"(?<![\w.\-/\\:])"
_REF_RE = re.compile(_START + "(?:%s|%s|%s)" % (_RUN, _ARTIFACT, _PATH))
_FULL_RE = re.compile("(?:%s|%s|%s)\\Z" % (_RUN, _ARTIFACT, _PATH))


def _split_row(line):
    """Cells of one markdown table row; a `|` inside backticks does not split."""
    cells, cur, tick = [], [], False
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and body[i + 1:i + 2] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "`":
            tick = not tick
        if ch == "|" and not tick:
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def _is_separator(cells):
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) or c == "" for c in cells)


def parse_verification_tables(text):
    """Rows of every table that has `Status` and `Evidence` columns:
    [{line, id, criterion, status, evidence}]. Other tables are ignored."""
    rows, header = [], None
    for number, line in enumerate((text or "").splitlines(), 1):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _split_row(line)
        if header is None:
            names = [re.sub(r"[*`_]", "", c).strip().lower() for c in cells]
            idx = {k: next((i for i, n in enumerate(names) if n.startswith(k)), None)
                   for k in ("status", "evidence")}
            header = idx if None not in idx.values() else False
            header = dict(header, crit=1 if len(cells) > 1 else 0) if header else False
            continue
        if not header or _is_separator(cells):
            continue
        cell = lambda i: cells[i] if i < len(cells) else ""
        rows.append({"line": number, "id": cell(0), "criterion": cell(header["crit"]),
                     "status": cell(header["status"]), "evidence": cell(header["evidence"])})
    return rows


def classify_status(cell):
    """`pass`, `descoped` or `not_pass` from a Status cell (markdown stripped)."""
    up = re.sub(r"[*`_~]", "", cell or "").strip().upper()
    words = re.findall(r"[A-Z]+", up)
    if up.startswith("N/A") or (words and words[0] in _DESCOPED_WORDS):
        return DESCOPED
    if words and words[0] in _PASS_WORDS and not any(w in _FAIL_WORDS for w in words):
        return PASS
    return NOT_PASS


def extract_refs(cell):
    """Machine-checkable references in an Evidence cell, in order, without duplicates."""
    found = []
    for match in _REF_RE.finditer(cell or ""):
        text = match.group(0).rstrip(".")
        if text not in found:
            found.append(text)
    return found


def _lines(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace").splitlines()


def _artifact_dirs(repo_root, ticket_id, art):
    own = re.match(r"((?:CC-)?T-?\d+)-", art)
    for tid in (ticket_id, own.group(1) if own else None):
        if tid:
            try:
                yield tickets_mod.dir_for(repo_root, tid)
            except Exception:  # noqa: BLE001
                continue


def _resolve_path(repo_root, ticket_id, match):
    raw = match.group("path")
    if ".." in raw.split("/"):
        return UNVERIFIABLE
    roots = [repo_root]
    try:
        roots.append(tickets_mod.dir_for(repo_root, ticket_id))
    except Exception:  # noqa: BLE001
        pass
    full = next((os.path.join(r, *raw.split("/")) for r in roots
                 if os.path.exists(os.path.join(r, *raw.split("/")))), None)
    if full is None:
        return MISSING
    if match.group("n") or match.group("name"):
        if not os.path.isfile(full):
            return MISSING
        lines = _lines(full)
        n, m = match.group("n"), match.group("m")
        if n and (int(n) < 1 or int(n) > len(lines) or (m and (int(m) < int(n) or int(m) > len(lines)))):
            return MISSING
        if match.group("name"):
            last = re.sub(r"\[.*\]\Z", "", match.group("name").split("::")[-1])
            pattern = re.compile(r"\b(?:def|class)\s+%s\b" % re.escape(last))
            if not any(pattern.search(line) for line in lines):
                return MISSING
    return ACCEPTED


def resolve_ref(repo_root, ticket_id, ref):
    """`accepted`, `missing` or `unverifiable` for one reference string. Existence only."""
    match = _FULL_RE.match((ref or "").strip())
    if not match:
        return UNVERIFIABLE
    try:
        if match.group("run"):
            run = runs_mod.get(repo_root, match.group("run")[4:])
            return ACCEPTED if run and run.get("state") == "done" else MISSING
        if match.group("art"):
            art = match.group("art")
            return ACCEPTED if any(os.path.isfile(os.path.join(d, art))
                                   for d in _artifact_dirs(repo_root, ticket_id, art)) else MISSING
        return _resolve_path(repo_root, ticket_id, match)
    except OSError:
        return MISSING


# ---------------------------------------------------------------- verdict ----

def _block(code, message, ref=None):
    out = {"code": code, "message": message}
    if ref:
        out["ref"] = ref
    return out


def _warn(code, message, rows=None):
    out = {"code": code, "message": message}
    if rows:
        out["rows"] = rows[:20]
    return out


def _read_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _judge_rows(repo_root, ticket_id, rows, blocks, warnings, counts):
    soft = {"evidence_prose_only": [], "evidence_partial": [], "criterion_descoped": []}
    counts["rows"] = len(rows)
    for row in rows:
        ref, status = "line %d" % row["line"], classify_status(row["status"])
        if status == DESCOPED:
            soft["criterion_descoped"].append(row["line"])
        elif status == NOT_PASS:
            blocks.append(_block("criterion_not_pass", "criterion %s is %r, not a pass" % (
                row["id"] or "?", row["status"] or "empty"), ref))
        else:
            counts["pass_rows"] += 1
            _judge_evidence(repo_root, ticket_id, row, ref, blocks, soft, counts)
    messages = {
        "evidence_prose_only": "%d pass row(s) cite no file, test or run that can be checked",
        "evidence_partial": "%d pass row(s) cite some references that do not resolve",
        "criterion_descoped": "%d criterion row(s) are deferred, cut, dropped or n/a"}
    for code, lines in soft.items():
        if lines:
            warnings.append(_warn(code, messages[code] % len(lines), lines))


def _judge_evidence(repo_root, ticket_id, row, ref, blocks, soft, counts):
    if not row["evidence"].strip():
        counts["empty"] += 1
        blocks.append(_block("evidence_empty", "criterion %s passes with no evidence" % row["id"], ref))
        return
    results = [resolve_ref(repo_root, ticket_id, r) for r in extract_refs(row["evidence"])]
    results = [r for r in results if r != UNVERIFIABLE]
    if not results:
        counts["prose_only"] += 1
        soft["evidence_prose_only"].append(row["line"])
    elif ACCEPTED not in results:
        counts["phantom"] += 1
        blocks.append(_block("evidence_phantom",
                             "every file, test or run cited for criterion %s is missing" % row["id"], ref))
    elif MISSING in results:
        counts["partial"] += 1
        soft["evidence_partial"].append(row["line"])
    else:
        counts["accepted"] += 1


def _judge_ticket_state(repo_root, ticket_id, ticket, now, blocks, warnings):
    from . import context as context_mod
    from . import trackers as trackers_mod
    found = trackers_mod.blockers(repo_root, ticket_id)
    if found.get("questions"):
        blocks.append(_block("critical_question_open", "%d critical question(s) still open: %s" % (
            len(found["questions"]), ", ".join(str(q.get("id")) for q in found["questions"]))))
    if found.get("bugs"):
        blocks.append(_block("critical_bug_unverified", "%d critical bug(s) not verified: %s" % (
            len(found["bugs"]), ", ".join(str(b.get("id")) for b in found["bugs"]))))
    claim = tickets_mod.claim_status(repo_root, ticket_id, now=now)
    if claim["state"] == "stale":
        blocks.append(_block("claim_stale", "the claim by %s is stale (%s): release or refresh it" % (
            claim["holder"], claim.get("basis"))))
    elif claim["state"] == "held":
        warnings.append(_warn("claim_held", "claimed by %s; the closer's identity is unknown" % claim["holder"]))
    if ticket.get("review_escalated"):
        blocks.append(_block("review_escalated", "the review loop escalated; a human decision is pending"))
    plan = context_mod.plan_tasks(repo_root, ticket_id)
    open_tasks = [t["id"] for t in plan["tasks"] if not t["done"]]
    if open_tasks:
        blocks.append(_block("plan_open", "%d plan task(s) unchecked: %s" % (
            len(open_tasks), ", ".join(open_tasks[:10]))))


def evaluate(repo_root, ticket_id, now=None):
    """Verdict for closing `ticket_id`: {ticket, ok, blocks[], warnings[], evidence{}, basis}.
    `ok` is true iff `blocks` is empty. Total: any exception becomes one `check_error` block."""
    from datetime import datetime, timezone
    counts = dict.fromkeys(("rows", "pass_rows", "accepted", "partial", "prose_only", "phantom", "empty"), 0)
    blocks, warnings = [], []
    try:
        now = now or datetime.now(timezone.utc)
        ticket = tickets_mod.load(repo_root, ticket_id)
        if ticket is None:
            raise FileNotFoundError("no ticket.toml for %s" % ticket_id)
        folder = tickets_mod.dir_for(repo_root, ticket_id)
        rows = parse_verification_tables(_read_text(os.path.join(folder, "%s-verification.md" % ticket_id)))
        if rows:
            _judge_rows(repo_root, ticket_id, rows, blocks, warnings, counts)
        else:
            blocks.append(_block("no_verification",
                                 "no %s-verification.md with a Status and Evidence table" % ticket_id))
        _judge_ticket_state(repo_root, ticket_id, ticket, now, blocks, warnings)
    except Exception as exc:  # noqa: BLE001 - fail closed, never raise
        blocks = [_block("check_error", "cannot check %s: %s" % (ticket_id, exc))]
        warnings = []
    return {"ticket": ticket_id, "ok": not blocks, "blocks": blocks, "warnings": warnings,
            "evidence": counts, "basis": BASIS}
