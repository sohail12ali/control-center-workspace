"""Read-only link checker over the vault's signposts (T-041).

Artifact-map rows and every ticket's `## Links` block are the vault's
signposts. Nothing compiles them, so a renamed file leaves a dangling link, a
fresh artifact is linked one way, and the map says "Open" for a ticket that has
been in `verify` for a week. This module is the missing check. It never writes
a file.

## What is and is not an error

ERROR is reserved for a broken signpost: a Links entry or map row that points
at nothing, a ticket artifact with no (or a malformed, or a duplicated) Links
block, and an artifact-map row that disagrees with `ticket.toml`, the machine
truth. These can be fixed in one edit and fail the run.

WARN is hygiene: a one-way sibling link, an incomplete sibling list, a prose
link that dangles, a non-canonical link form, an ambiguous basename, a misplaced
artifact, a malformed map row. Debt of this kind is large on day one (templates
create one-way links by construction), and a check that is red every night for a
reason nobody can fix in a night gets ignored, which hides the errors that
matter (the failure mode `harness_lint.py` warns about). `--strict` turns
warnings into a failure.

## Resolution rule

The vault's own `vault.build_graph` is NOT reusable for this: its extractor is a
bare regex that does not strip code and runs across lines, and it silently drops
unresolved links. So this module has its own extractor and resolver, and a
drift-guard test keeps the resolution rule identical: a target resolves iff it
equals, case-sensitively, the basename without extension of a `.md` file
anywhere in the vault. A `.md` suffix or a folder prefix still resolves (WARN
`link-form`); a non-`.md` extension or `..` does not. A target is never turned
into a path to open.
"""

import os
import re

from . import boards, paths, tickets

ERROR = "error"
WARN = "warn"

# The codes, in one place. A flip of one-way-link to ERROR (decision D-4) is
# moving that string from WARN_CODES to ERROR_CODES.
ERROR_CODES = (
    "map-missing", "links-missing", "links-duplicate", "links-malformed",
    "links-dangling", "map-dangling", "map-unknown-ticket", "map-missing-row",
    "map-duplicate-row", "map-status-drift", "map-section-drift",
    "map-title-drift",
)
WARN_CODES = (
    "one-way-link", "links-incomplete", "links-not-last", "body-dangling",
    "link-form", "ambiguous-basename", "misplaced-artifact", "map-row-format",
)
ALL_CODES = ERROR_CODES + WARN_CODES

MAP_FILE = "artifact-map.md"
TEMPLATE_DIR = "_template"

# ticket stage -> (artifact-map section, status label). `blocked` is an
# assumption: no ticket is blocked today, so no real row confirms its shape.
STAGE_MAP = {
    "open": ("Active", "Open"),
    "in-progress": ("Active", "In Progress"),
    "verify": ("Active", "Verify"),
    "blocked": ("Blocked", "Blocked"),
    "done": ("Completed", "Complete"),
}
ARCHIVED_SECTION = "Archived"

_BOM = "\ufeff"
_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
_BACKTICK_RUN_RE = re.compile(r"`+")
_LINK_RE = re.compile(r"\[\[([^\[\]]*)\]\]")
_H12_RE = re.compile(r"^#{1,2}(?:[ \t]|$)")
_LINKS_EXACT_RE = re.compile(r"^## Links[ \t]*$")
_LINKS_MALFORMED_RE = re.compile(r"^##(?!#)[ \t]*Links(?![A-Za-z])")
_LINKS_FUSED_RE = re.compile(r"(?<!#)##(?!#)[ \t]*Links(?![A-Za-z])")
_H2_RE = re.compile(r"^##[ \t]+(.*?)[ \t]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FOREIGN_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-[A-Za-z]*\d+-")


class Finding:
    # `refs` is what else the finding is about, for `--ticket` scoping: ticket
    # ids (map findings) or vault paths (ambiguous-basename). Never printed.
    __slots__ = ("level", "code", "path", "line", "message", "refs")

    def __init__(self, code, path, line, message, refs=()):
        self.level = ERROR if code in ERROR_CODES else WARN
        self.code = code
        self.path = path
        self.line = line
        self.message = message
        self.refs = tuple(refs)

    def as_dict(self):
        return {"level": self.level, "code": self.code, "path": self.path,
                "line": self.line, "message": self.message}

    def sort_key(self):
        return (0 if self.level == ERROR else 1, self.path, self.line, self.code)

    def __repr__(self):
        return "Finding(%s %s %s:%s)" % (self.level, self.code, self.path, self.line)


# --- text: lines, code masking, links -------------------------------------

def normalize(text):
    """Lines of `text`, 1-based by position, BOM stripped. Splits on CRLF, LF
    or a lone CR (each one break) and nothing else: `str.splitlines()` also
    breaks on U+2028 and friends, which would shift line numbers."""
    if text.startswith(_BOM):
        text = text[1:]
    lines = _LINE_BREAK_RE.split(text)
    if len(lines) > 1 and lines[-1] == "":
        lines.pop()  # the newline that ends the file is not another line
    return lines


def _mask_spans(line):
    """Blank out inline code spans (a backtick run closed by a run of the same
    length on the same line). An unmatched run is literal."""
    runs = [(m.start(), m.end()) for m in _BACKTICK_RUN_RE.finditer(line)]
    if len(runs) < 2:
        return line
    out, pos, i = [], 0, 0
    while i < len(runs):
        start, end = runs[i]
        width = end - start
        close = next((j for j in range(i + 1, len(runs))
                      if runs[j][1] - runs[j][0] == width), None)
        if close is None:
            i += 1
            continue
        out.append(line[pos:start])
        out.append(" " * (runs[close][1] - start))
        pos = runs[close][1]
        i = close + 1
    out.append(line[pos:])
    return "".join(out)


def mask_code(lines):
    """`lines` with fenced code blocks (backtick or tilde) and inline code
    spans blanked, same line count. A fence may be indented (nested lists); an
    unclosed fence runs to the end of the file."""
    out, fence = [], None
    for line in lines:
        match = _FENCE_RE.match(line)
        if fence:
            if (match and match.group(1)[0] == fence[0]
                    and len(match.group(1)) >= fence[1] and not match.group(2).strip()):
                fence = None
            out.append("")
            continue
        if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            fence = (match.group(1)[0], len(match.group(1)))
            out.append("")
            continue
        out.append(_mask_spans(line))
    return out


def _target(inner):
    cut = len(inner)
    for sep in "|#":
        at = inner.find(sep)
        if at != -1:
            cut = min(cut, at)
    return inner[:cut].strip()


def extract_links(text):
    """`(target, line)` for every wikilink outside code. `[[x|a]]`, `[[x#h]]`
    and `[[x#h|a]]` give `x`; `[[#h]]` (same-file anchor) gives nothing. A `[[`
    with no `]]` on its line is not a link and never reaches the next line."""
    return _links_in(mask_code(normalize(text)))


def _links_in(masked):
    out = []
    for number, line in enumerate(masked, 1):
        if "[[" not in line:
            continue
        for match in _LINK_RE.finditer(line):
            target = _target(match.group(1))
            if target:
                out.append((target, number))
    return out


# --- resolution -----------------------------------------------------------

class Index:
    """Basename (no extension) -> sorted vault-relative paths of the `.md` files
    that have it. Built from directory listings only; `os.path.exists` is never
    used for name matching because it is case-insensitive on Windows."""

    def __init__(self, md_paths):
        self.by_name = {}
        for rel in sorted(md_paths):
            self.by_name.setdefault(_stem(rel), []).append(rel)
        self.by_lower = {}
        for name in self.by_name:
            self.by_lower.setdefault(name.lower(), []).append(name)


def _stem(rel):
    base = rel.rsplit("/", 1)[-1]
    return base[:-3] if base.endswith(".md") else base


def build_index(md_paths):
    return Index(md_paths)


def resolve(index, target):
    """`(status, paths, note)`. status is "ok", "form" (resolves, but not the
    canonical bare basename) or "dangling". `note` says why a dangling target
    dangles when there is something useful to say (a case-only difference)."""
    if ".." in target:
        return "dangling", [], "a target with `..` is never resolved"
    exact = index.by_name.get(target)
    if exact:
        return "ok", list(exact), ""
    last = target.rsplit("/", 1)[-1]
    suffixed = last.endswith(".md")
    if suffixed:
        last = last[:-3]
    if ("/" in target or suffixed) and last in index.by_name:
        return "form", list(index.by_name[last]), ""
    near = index.by_lower.get(last.lower())
    if near:
        return "dangling", [], "a file named %s exists; the names differ only in case" % near[0]
    return "dangling", [], ""


# --- one parsed document --------------------------------------------------

def _is_fused(line):
    """A  that follows other text on its line (a heading fused onto
    the end of the previous paragraph)."""
    if line.startswith("#"):
        return False
    hit = _LINKS_FUSED_RE.search(line)
    return bool(hit and line[:hit.start()].strip())


class Doc:
    """What the rules need from one file: links, `## Links` blocks as
    (heading_line, last_line), malformed heading lines, level 1-2 headings."""

    def __init__(self, text):
        self.masked = mask_code(normalize(text))
        self.links = _links_in(self.masked)
        self.headings = [n for n, line in enumerate(self.masked, 1) if _H12_RE.match(line)]
        self.blocks, self.malformed = [], []
        total = len(self.masked)
        for number, line in enumerate(self.masked, 1):
            if _LINKS_EXACT_RE.match(line):
                after = [h for h in self.headings if h > number]
                self.blocks.append((number, (after[0] - 1) if after else total))
            elif (_LINKS_MALFORMED_RE.match(line)
                  or _is_fused(line)):
                self.malformed.append(number)

    def in_block(self, line):
        return any(start < line <= end for start, end in self.blocks)

    def total(self):
        return len(self.masked)


# --- filesystem: junction-safe walker -------------------------------------

def _is_reparse_dir(entry):
    """A symlink or Windows junction/reparse-point directory (never followed)."""
    try:
        if entry.is_symlink():
            return True
        isjunction = getattr(os.path, "isjunction", None)
        if isjunction and isjunction(entry.path):
            return True
        attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
        return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except OSError:
        return True


def walk_md(root):
    """Sorted `(rel, full)` for every `.md` file under `root`: skips dot
    entries, symlinks and junctions, never follows a link out of the tree."""
    found = []
    stack = [("", root)]
    while stack:
        rel_dir, full_dir = stack.pop()
        try:
            with os.scandir(full_dir) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith("."):
                continue
            rel = rel_dir + "/" + entry.name if rel_dir else entry.name
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if not _is_reparse_dir(entry):
                    stack.append((rel, entry.path))
            elif is_file and entry.name.endswith(".md"):
                found.append((rel, entry.path))
    found.sort()
    return found


def _read(path):
    """Text of `path`; undecodable bytes become replacement characters and an
    unreadable file reads as empty, so one bad file never aborts the run."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            return fh.read()
    except OSError:
        return ""


# --- ticket artifact classification ---------------------------------------

def _data_rel(repo_root, vault):
    """Where the ticket directories live, relative to the vault with `/`, or
    None when the console's data root is outside the vault."""
    config = boards.load_console_config(repo_root)
    data = os.path.normcase(os.path.abspath(paths.artifacts_dir(repo_root, config)))
    base = os.path.normcase(os.path.abspath(vault))
    try:
        rel = os.path.relpath(data, base)
    except ValueError:
        return None
    if rel == "." or rel == ".." or rel.startswith(".." + os.sep):
        return None
    return rel.replace(os.sep, "/")


def classify(rel, data_rel, ticket_ids):
    """One of: "template", "artifact" (`{T}-*.md` at the root of ticket dir T),
    "misplaced" (another ticket's prefix in this directory), "other"."""
    if data_rel is None or not rel.startswith(data_rel + "/"):
        return "other"
    parts = rel[len(data_rel) + 1:].split("/")
    if parts[0] == TEMPLATE_DIR:
        return "template"
    if len(parts) != 2 or parts[0] not in ticket_ids:
        return "other"
    ticket, name = parts
    if name.startswith(ticket + "-"):
        return "artifact"
    if _FOREIGN_ID_RE.match(name) or any(name.startswith(i + "-") for i in ticket_ids):
        return "misplaced"
    return "other"


# --- the rules ------------------------------------------------------------

def _dangling_message(target, note):
    base = ("[[%s]] does not resolve to any .md file in the vault; "
            "fix the name or remove the link" % target)
    return base + (" (%s)" % note if note else "")


def link_findings(rel, doc, index, skip_lines=()):
    """`links-dangling` / `body-dangling` / `link-form` for every link in a file."""
    out = []
    for target, line in doc.links:
        if line in skip_lines:
            continue
        status, _paths, note = resolve(index, target)
        if status == "dangling":
            code = "links-dangling" if doc.in_block(line) else "body-dangling"
            out.append(Finding(code, rel, line, _dangling_message(target, note)))
        elif status == "form":
            canonical = target.rsplit("/", 1)[-1]
            canonical = canonical[:-3] if canonical.endswith(".md") else canonical
            out.append(Finding("link-form", rel, line,
                               "[[%s]] resolves but is not the bare basename; write [[%s]]"
                               % (target, canonical)))
    return out


def block_findings(rel, doc):
    """Links-block form for one ticket artifact (FR-6, plan P-3 and P-4)."""
    out = []
    for line in doc.malformed:
        out.append(Finding("links-malformed", rel, line,
                           "the Links heading must be exactly `## Links` on its own line"))
    if not doc.blocks:
        if not doc.malformed:
            out.append(Finding("links-missing", rel, 1,
                               "no `## Links` block; add one as the last section "
                               "listing every sibling artifact"))
        return out
    if len(doc.blocks) > 1:
        lines = ", ".join(str(b[0]) for b in doc.blocks)
        out.append(Finding("links-duplicate", rel, doc.blocks[1][0],
                           "%d `## Links` blocks (lines %s); keep one, as the last section"
                           % (len(doc.blocks), lines)))
    last_end = doc.blocks[-1][1]
    if last_end < doc.total():
        out.append(Finding("links-not-last", rel, last_end + 1,
                           "a heading follows the Links block; move `## Links` to the end"))
    return out


def sibling_findings(ticket, docs, index):
    """`one-way-link` and `links-incomplete` for the artifacts of one ticket.
    `docs` is {rel: Doc} for its ticket artifacts. A file without a Links block
    (missing or malformed) links nothing and gets no `links-incomplete`: its
    own `links-missing` / `links-malformed` already says so."""
    names = {_stem(rel): rel for rel in docs}
    linked = {}
    for rel, doc in docs.items():
        got = set()
        for target, line in doc.links:
            if doc.in_block(line):
                for hit in resolve(index, target)[1]:
                    if _stem(hit) in names:
                        got.add(_stem(hit))
        got.discard(_stem(rel))
        linked[rel] = got
    out = []
    for rel in sorted(docs):
        doc, me = docs[rel], _stem(rel)
        anchor = doc.blocks[0][0] if doc.blocks else 1
        for other_name in sorted(names):
            if other_name == me:
                continue
            if me in linked[names[other_name]] and other_name not in linked[rel]:
                out.append(Finding("one-way-link", rel, anchor,
                                   "%s links to %s but this file does not link back; "
                                   "add [[%s]] to the Links block" % (other_name, me, other_name)))
        if doc.blocks:
            missing = sorted(n for n in names if n != me and n not in linked[rel])
            if missing:
                out.append(Finding("links-incomplete", rel, anchor,
                                   "the Links block omits %d sibling(s): %s"
                                   % (len(missing), ", ".join(missing))))
    return out


def ambiguous_findings(index):
    out = []
    for name in sorted(index.by_name):
        hits = index.by_name[name]
        if len(hits) > 1:
            out.append(Finding("ambiguous-basename", hits[0], 1,
                               "[[%s]] could be any of %d files (%s); filenames must be "
                               "unique in the vault, rename one" % (name, len(hits), ", ".join(hits)),
                               refs=hits))
    return out


# --- artifact map ---------------------------------------------------------

def parse_map(lines):
    """Rows of the artifact map: dicts with `line`, `target`, `section` and
    `fields` (`(title, status, owner, date)` or None when the row is not in the
    documented shape). Only bullets beginning `- [[` are rows."""
    rows, section = [], ""
    for number, line in enumerate(lines, 1):
        head = _H2_RE.match(line)
        if head:
            section = head.group(1)
            continue
        if not line.startswith("- [["):
            continue
        match = _LINK_RE.search(line)
        if not match:
            continue
        rest = line[match.end():]
        fields = None
        if rest.startswith(" — "):
            parts = rest[3:].split(" — ")
            if len(parts) >= 4:
                title = " — ".join(parts[:-3]).strip()
                status, owner, date = (p.strip() for p in parts[-3:])
                if title and status and owner and _DATE_RE.match(date):
                    fields = (title, status, owner, date)
        rows.append({"line": number, "target": _target(match.group(1)),
                     "section": section, "fields": fields})
    return rows


def map_findings(text, index, all_ids, board):
    """Artifact-map rules. `all_ids` is every ticket id; `board` maps the id of
    each ticket of kind `tickets` to `(stage, title)`. `text` None means the
    map file does not exist."""
    if text is None:
        return [Finding("map-missing", MAP_FILE, 1,
                        "%s does not exist; create it with one row per ticket" % MAP_FILE)]
    out, per_ticket = [], {}
    for row in parse_map(normalize(text)):
        line = row["line"]
        if row["fields"] is None:
            out.append(Finding("map-row-format", MAP_FILE, line,
                               "row does not match `- [[{T}-summary]] — {title} — "
                               "{status} — {owner} — {YYYY-MM-DD}`"))
        status, hits, note = resolve(index, row["target"])
        if status == "dangling":
            owner = row["target"][:-len("-summary")] if row["target"].endswith("-summary") else ""
            out.append(Finding("map-dangling", MAP_FILE, line,
                               _dangling_message(row["target"], note), refs=(owner,)))
            continue
        stem = _stem(hits[0])
        ticket = stem[:-len("-summary")] if stem.endswith("-summary") else None
        if ticket not in all_ids:
            out.append(Finding("map-unknown-ticket", MAP_FILE, line,
                               "[[%s]] is not the summary of any ticket; point the row at "
                               "[[{T}-summary]] or remove it" % row["target"]))
            continue
        per_ticket.setdefault(ticket, []).append(row)
    for ticket in sorted(board):
        stage, title = board[ticket]
        rows = per_ticket.get(ticket, [])
        if not rows:
            out.append(Finding("map-missing-row", MAP_FILE, 1,
                               "%s has no row in the artifact map; add one under its section"
                               % ticket, refs=(ticket,)))
            continue
        if len(rows) > 1:
            out.append(Finding("map-duplicate-row", MAP_FILE, rows[1]["line"],
                               "%s has %d rows (lines %s); keep one"
                               % (ticket, len(rows), ", ".join(str(r["line"]) for r in rows)),
                               refs=(ticket,)))
        expected = STAGE_MAP.get(stage)
        for row in rows:
            if expected is None or row["section"] == ARCHIVED_SECTION or row["fields"] is None:
                continue
            exp_section, exp_label = expected
            row_title, row_label = row["fields"][0], row["fields"][1]
            if row_label != exp_label:
                out.append(Finding("map-status-drift", MAP_FILE, row["line"],
                                   "%s reads %r but ticket.toml stage %r means %r; update the row"
                                   % (ticket, row_label, stage, exp_label), refs=(ticket,)))
            if row["section"] != exp_section:
                out.append(Finding("map-section-drift", MAP_FILE, row["line"],
                                   "%s sits under %r but stage %r belongs under %r; move the row"
                                   % (ticket, row["section"], stage, exp_section),
                                   refs=(ticket,)))
            if row_title != title:
                out.append(Finding("map-title-drift", MAP_FILE, row["line"],
                                   "%s row title differs from ticket.toml title %r; update the row"
                                   % (ticket, title), refs=(ticket,)))
    return out


# --- walking a vault ------------------------------------------------------

def scan(repo_root):
    """Run every rule over the vault of `repo_root`. Returns `(findings, stats)`
    with `stats = {"tickets": N, "files": M, "ids": [...], "per_ticket": {id: files}}`.
    Findings are not ordered or scoped here (see `check`), and nothing is
    written."""
    vault = paths.vault_dir(repo_root)
    data_rel = _data_rel(repo_root, vault)
    all_tickets = tickets.list_tickets(repo_root)
    ticket_ids = {t["id"] for t in all_tickets}
    board = {t["id"]: (t.get("stage", ""), t.get("title", ""))
             for t in all_tickets if t.get("kind") == "tickets"}

    files = walk_md(vault)
    index = build_index([rel for rel, _full in files])
    findings, groups, checked, per_ticket = [], {}, 0, {}
    map_text = None
    for rel, full in files:
        kind = classify(rel, data_rel, ticket_ids)
        if kind == "template":
            continue
        checked += 1
        if data_rel and rel.startswith(data_rel + "/") and rel.count("/") > data_rel.count("/") + 1:
            owner = rel[len(data_rel) + 1:].split("/")[0]
            per_ticket[owner] = per_ticket.get(owner, 0) + 1
        text = _read(full)
        if rel == MAP_FILE:
            map_text = text
        doc = Doc(text)
        skip = ()
        if rel == MAP_FILE:
            skip = {r["line"] for r in parse_map(doc.masked)}
        findings.extend(link_findings(rel, doc, index, skip))
        if kind == "misplaced":
            ticket_dir = rel.split("/")[-2]
            findings.append(Finding("misplaced-artifact", rel, 1,
                                    "filename does not start with %s-; move it to its own "
                                    "ticket directory or rename it" % ticket_dir))
        elif kind == "artifact":
            findings.extend(block_findings(rel, doc))
            groups.setdefault(rel.split("/")[-2], {})[rel] = doc
    for ticket in sorted(groups):
        findings.extend(sibling_findings(ticket, groups[ticket], index))
    findings.extend(ambiguous_findings(index))
    findings.extend(map_findings(map_text, index, ticket_ids, board))
    return findings, {"tickets": len(ticket_ids), "files": checked,
                      "ids": sorted(ticket_ids), "per_ticket": per_ticket}


# --- the contract: check, exit code, output -------------------------------

class LinkCheckError(Exception):
    """The check could not run (exit 2): an unreadable vault, an unknown
    ticket. Findings never raise this."""


def _scope(findings, repo_root, ticket):
    """Keep what is about `ticket` (plan P-5): findings in its directory, map
    findings about its row, ambiguous basenames with a file in its directory."""
    vault = paths.vault_dir(repo_root)
    data_rel = _data_rel(repo_root, vault)
    prefix = "%s/%s/" % (data_rel, ticket) if data_rel else None

    def mine(f):
        if prefix and f.path.startswith(prefix):
            return True
        return any(r == ticket or (prefix and r.startswith(prefix)) for r in f.refs)
    return [f for f in findings if mine(f)]


def check(repo_root, ticket=None):
    """`(findings, summary)`: every rule over the vault, ordered by (level, path,
    line, code), optionally limited to one ticket. `summary` is
    `{"tickets", "files", "errors", "warnings"}`; `files` counts the `.md` files
    read for links (`_template/` excluded). Raises `LinkCheckError` when it
    could not run. `--ticket` is a post-filter on a full run: resolution needs
    the whole index anyway."""
    vault = paths.vault_dir(repo_root)
    try:
        with os.scandir(vault):
            pass
    except OSError as exc:
        raise LinkCheckError("cannot read the vault directory %s: %s"
                             % (vault, exc.strerror or exc)) from None
    try:
        findings, stats = scan(repo_root)
    except FileNotFoundError as exc:  # no console.toml: the data root is unknown
        raise LinkCheckError("cannot read the console configuration: %s"
                             % (exc.filename or exc)) from None
    tickets_n, files_n = stats["tickets"], stats["files"]
    if ticket:
        if ticket not in stats["ids"]:
            raise LinkCheckError("no such ticket: %s" % ticket)
        findings = _scope(findings, repo_root, ticket)
        tickets_n, files_n = 1, stats["per_ticket"].get(ticket, 0)
    findings.sort(key=lambda f: f.sort_key() + (f.message,))
    summary = {"tickets": tickets_n, "files": files_n,
               "errors": sum(1 for f in findings if f.level == ERROR),
               "warnings": sum(1 for f in findings if f.level == WARN)}
    return findings, summary


def exit_code(summary, strict=False):
    """0 no errors; 1 any error, or any warning under `strict`. (2, could not
    run, is `LinkCheckError`.) Warnings alone pass unless asked: a check that
    fails on a maybe gets switched off, taking the errors with it."""
    return 1 if summary["errors"] or (strict and summary["warnings"]) else 0


WARN_CAP = 20


def _ascii(text):
    return text.encode("ascii", "backslashreplace").decode("ascii")


def format_report(findings, summary, show_all=False):
    """Text report: errors, then warnings (at most `WARN_CAP` per code unless
    `show_all`), then one summary line. ASCII only: titles and paths hold em
    dashes and arrows that a Windows console renders as replacement characters."""
    lines, shown, hidden = [], {}, {}
    for level in (ERROR, WARN):
        for f in findings:
            if f.level != level:
                continue
            if level == WARN and not show_all:
                if shown.get(f.code, 0) >= WARN_CAP:
                    hidden[f.code] = hidden.get(f.code, 0) + 1
                    continue
                shown[f.code] = shown.get(f.code, 0) + 1
            lines.append("%-5s %-20s %s:%d\n      %s"
                         % (f.level.upper(), f.code, f.path, f.line, f.message))
    for code in ALL_CODES:
        if code in hidden:
            lines.append("%-5s %-20s +%d more (use --all)" % (WARN.upper(), code, hidden[code]))
    lines.append("")
    lines.append("%d tickets, %d files | %d error(s), %d warning(s)"
                 % (summary["tickets"], summary["files"], summary["errors"], summary["warnings"]))
    return _ascii("\n".join(lines))


def as_json(findings, summary):
    """The `harness lint --json` shape plus a `line` on each finding; uncapped."""
    return {"summary": dict(summary), "findings": [f.as_dict() for f in findings]}
