"""Minimal, dependency-free TOML read/write for the console's own file shapes.

Deliberately not a general TOML implementation. It supports exactly what
ticket.toml / tracker .toml / board config files use: [section] tables,
[[array]] array-of-tables, and scalar values (quoted strings, bool, int,
float, bare ISO dates/datetimes stored as strings). No inline tables, no
multi-line strings, no nesting beyond one level. Stdlib-only, no Python
version floor — this is what lets the console stay drop-in-anywhere instead
of depending on tomllib (3.11+) or a third-party package.

Round-trips cleanly for anything *this* module wrote; do not point it at
hand-authored TOML using features outside the subset above.
"""

import os
import re
import time

_STR_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
_ARRAY_RE = re.compile(r'^\[(.*)\]$')
_SECTION_RE = re.compile(r'^\[([A-Za-z0-9_.-]+)\]$')
_ARRAY_TABLE_RE = re.compile(r'^\[\[([A-Za-z0-9_.-]+)\]\]$')
_KV_RE = re.compile(r'^([A-Za-z0-9_.-]+)\s*=\s*(.+)$')


class TomlError(ValueError):
    pass


def _unescape(s):
    return s.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n')


def _escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def _split_array(inner):
    """Split an array body on top-level commas only.

    A naive inner.split(",") tears any element whose quoted string contains a
    comma — and because _dump_scalar happily writes such a value, that made
    the pair a silent write-then-read corruption, not merely a parse quirk.
    (Hit for real by an [agents.backends.*] args entry, which the config file
    advertises as editable without touching code.)
    """
    parts, buf = [], []
    in_string = escaped = False
    for ch in inner:
        if escaped:
            buf.append(ch)
            escaped = False
        elif in_string and ch == "\\":
            buf.append(ch)
            escaped = True
        elif ch == '"':
            in_string = not in_string
            buf.append(ch)
        elif ch == "," and not in_string:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if in_string:
        raise TomlError(f"unterminated string in array: [{inner}]")
    parts.append("".join(buf))
    return parts


def _parse_scalar(raw):
    raw = raw.strip()
    m = _STR_RE.match(raw)
    if m:
        return _unescape(m.group(1))
    if raw == "true":
        return True
    if raw == "false":
        return False
    m = _ARRAY_RE.match(raw)
    if m:
        inner = m.group(1).strip()
        if not inner:
            return []
        items = []
        for part in _split_array(inner):
            part = part.strip()
            if part:
                items.append(_parse_scalar(part))
        return items
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    # Bare token (date, datetime, or unquoted identifier) — keep as string.
    return raw


def _navigate_tables(root, dotted_name, lineno):
    """Walk/create nested dicts for every segment but the last of a dotted
    table path (e.g. 'agents.backends' in 'agents.backends.claude'),
    returning (parent_dict, last_segment).

    A segment that is an array-of-tables resolves to its LAST element, which
    is what makes `[[backend]]` followed by `[backend.mode_blurbs]` attach the
    sub-table to the row just opened rather than erroring. That is standard
    TOML behaviour and the shape config files actually get written in.
    """
    parts = dotted_name.split(".")
    node = root
    for part in parts[:-1]:
        nxt = node.setdefault(part, {})
        if isinstance(nxt, list):
            if not nxt:
                raise TomlError(
                    f"line {lineno}: '{part}' in '{dotted_name}' has no [[{part}]] row yet"
                )
            nxt = nxt[-1]
        if not isinstance(nxt, dict):
            raise TomlError(f"line {lineno}: '{part}' in '{dotted_name}' is not a table")
        node = nxt
    return node, parts[-1]


def _join_multiline_arrays(text):
    """Fold a `key = [` … `]` block onto one logical line.

    Config that lists argv templates is unreadable on a single line, and a
    parser that refuses the wrapped form pushes the ugliness onto every file
    that uses it. Bracket depth is tracked outside string literals so a `]`
    inside a quoted value doesn't end the array early.
    """
    out = []
    buf = None
    depth = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if buf is None:
            if stripped.startswith("#") or "=" not in stripped:
                out.append(raw_line)
                continue
            depth = _bracket_delta(stripped)
            if depth > 0:
                buf = [stripped]
            else:
                out.append(raw_line)
            continue
        # Inside a wrapped array: strip comments-only lines, keep content.
        if stripped.startswith("#"):
            continue
        buf.append(stripped)
        depth += _bracket_delta(stripped)
        if depth <= 0:
            out.append(" ".join(buf))
            buf = None
            depth = 0
    if buf is not None:
        out.append(" ".join(buf))
    return "\n".join(out)


def _bracket_delta(line):
    """Net `[` minus `]` outside string literals."""
    depth = 0
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
        elif ch == "#":
            break
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        i += 1
    return depth


def loads(text):
    """Parse TOML text (our subset) into a plain dict."""
    root = {}
    current = root
    for lineno, raw_line in enumerate(_join_multiline_arrays(text).splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ARRAY_TABLE_RE.match(line)
        if m:
            name = m.group(1)
            parent, last = _navigate_tables(root, name, lineno)
            parent.setdefault(last, [])
            if not isinstance(parent[last], list):
                raise TomlError(f"line {lineno}: '{name}' is not an array-of-tables")
            new_entry = {}
            parent[last].append(new_entry)
            current = new_entry
            continue
        m = _SECTION_RE.match(line)
        if m:
            name = m.group(1)
            parent, last = _navigate_tables(root, name, lineno)
            parent.setdefault(last, {})
            if not isinstance(parent[last], dict):
                raise TomlError(f"line {lineno}: '{name}' is not a table")
            current = parent[last]
            continue
        m = _KV_RE.match(line)
        if m:
            key, raw_val = m.group(1), m.group(2)
            current[key] = _parse_scalar(raw_val)
            continue
        raise TomlError(f"line {lineno}: cannot parse: {raw_line!r}")
    return root


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return loads(f.read())


def _dump_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_dump_scalar(v) for v in value) + "]"
    return '"' + _escape(str(value)) + '"'


def dumps(data):
    """Render a plain dict (our subset) back to TOML text."""
    lines = []

    # Top-level scalars first (rare, but keep them valid TOML if present).
    for key, value in data.items():
        if isinstance(value, dict) or isinstance(value, list):
            continue
        lines.append(f"{key} = {_dump_scalar(value)}")
    if lines:
        lines.append("")

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"[{key}]")
            for k, v in value.items():
                lines.append(f"{k} = {_dump_scalar(v)}")
            lines.append("")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for entry in value:
                lines.append(f"[[{key}]]")
                for k, v in entry.items():
                    lines.append(f"{k} = {_dump_scalar(v)}")
                lines.append("")
        elif isinstance(value, list):
            # Array of scalars at top level — already emitted above if so;
            # array-of-tables handled just above. Nothing else to do here.
            pass

    return "\n".join(lines).rstrip() + "\n"


def dump(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(data))


def atomic_write(path, data, timeout=5.0):
    """Write with a lock + temp-file-then-rename so concurrent CLI/HTTP
    writers (e.g. two agent worktrees) never interleave partial writes."""
    lock_path = str(path) + ".lock"
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"could not acquire lock: {lock_path}")
            time.sleep(0.05)
    try:
        tmp_path = str(path) + ".tmp"
        dump(tmp_path, data)
        os.replace(tmp_path, path)
    finally:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass
