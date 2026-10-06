"""Load `.env` into the process environment. Stdlib only.

## Why not python-dotenv

The console has no runtime dependencies, and that is what lets it be dropped
into any workspace and just run. A `.env` parser is forty lines; a pip install
is a support burden on everyone who clones the template.

## The rule that prevents the worst surprise

**A variable already in the environment always wins.** If you exported
`OPENROUTER_API_KEY` in your shell, a stale value in `.env` will not silently
replace it — because the failure that causes is horrible to diagnose: the key
you can see in your own shell is not the key being used, and nothing says so.
File values fill gaps; they never override a deliberate act.

## Nothing here logs a value

`load()` returns the *names* it set and never the values, so a caller can say
"loaded 2 variables from .env" without putting a credential in a terminal
scrollback, a CI log, or a screenshot.

## The file is not readable by agents

`.env`, `.env.*` and friends are in `agent_tools.SECRET_PATTERNS`, so the
workspace tools refuse to read them and the search tool skips them — an agent
authenticating with a key should not be able to read that key back.
"""

import os
import re

DEFAULT_NAME = ".env"

#: Names the setup wizard may write. Anything else — a Telegram token, a
#: custom provider's variable, a name someone typed — is refused. The list
#: is the same one `.env.example` documents for model providers, so the
#: wizard cannot become a general secret store.
KEY_ALLOWLIST = frozenset({
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "LMSTUDIO_API_KEY",
})

#: `KEY=value`, tolerating a leading `export` and surrounding whitespace.
_LINE_RE = re.compile(r"""
    ^\s*
    (?:export\s+)?
    ([A-Za-z_][A-Za-z0-9_]*)      # name
    \s*=\s*
    (.*?)
    \s*$
""", re.VERBOSE)


def _unquote(value):
    """Strip one matching pair of quotes, and honour escapes only inside
    double quotes — the same shape shells and every dotenv library use, so a
    file that works elsewhere works here."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            return (inner.replace("\\n", "\n").replace("\\t", "\t")
                         .replace('\\"', '"').replace("\\\\", "\\"))
        return inner
    # Unquoted: an inline comment ends the value. Quoted values keep their `#`.
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at]
    return value.strip()


def parse(text):
    """`{name: value}` from the text of a .env file. Never raises.

    A malformed line is skipped rather than failing the load: one bad line
    should not cost you the other nine, and a file that refuses to load at all
    is a file people stop using.
    """
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        name, value = match.groups()
        out[name] = _unquote(value)
    return out


def path_for(repo_root, name=DEFAULT_NAME):
    return os.path.join(repo_root, name)


def load(repo_root, name=DEFAULT_NAME, override=False):
    """Load `.env` into `os.environ`. Returns the names it actually set.

    Returns names, never values — so callers can report what happened without
    printing a credential.
    """
    path = path_for(repo_root, name)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []

    applied = []
    for key, value in parse(text).items():
        if not override and os.environ.get(key):
            # Already set deliberately. Silently replacing it means the value
            # you can see in your shell is not the one in use.
            continue
        os.environ[key] = value
        applied.append(key)
    return sorted(applied)


def _assignment_suffix(rest):
    """A trailing `` # comment`` on an unquoted value, kept when the line is
    rewritten. Quoted values keep their ``#`` inside the quotes, so they
    have no separate suffix to preserve."""
    if len(rest) >= 2 and rest[0] in ("'", '"') and rest.rstrip().endswith(rest[0]):
        return ""
    at = rest.find(" #")
    if at == -1:
        return ""
    return rest[at:]


def _render_value(value):
    """Write a value the parser will read back as the same string.

    A bare token stays bare. Anything with a space, a hash, or a quote is
    double-quoted, so an inline comment on the way in is not eaten on the
    way out and a value is never split into a second assignment.
    """
    if value == "" or re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"%s"' % escaped


def set_keys(repo_root, updates, name=DEFAULT_NAME):
    """Set allowlisted names in `.env`, preserving every other line.

    Returns ``{"written", "applied"}`` — names only, never values. ``written``
    is what changed on disk. ``applied`` is the subset loaded into this
    process. A name already present in the environment is left alone: a shell
    export wins over the file, same rule as ``load``.

    Raises ValueError before touching the file when a name is not allowlisted
    or a value is not a single-line string. The message names the variable,
    never the value.
    """
    if not isinstance(updates, dict) or not updates:
        raise ValueError("no keys given")
    unknown = sorted(set(updates) - KEY_ALLOWLIST)
    if unknown:
        raise ValueError(
            "not an environment key this setup can write: %s" % ", ".join(unknown))

    cleaned = {}
    for key, value in updates.items():
        if not isinstance(value, str):
            raise ValueError("%s must be a string" % key)
        if "\n" in value or "\r" in value or "\x00" in value:
            raise ValueError("%s must be a single line" % key)
        cleaned[key] = value

    path = path_for(repo_root, name)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        text = ""

    # Match the raw line, not a stripped one, so a leading `export` and the
    # indentation around it survive the rewrite.
    assign = re.compile(
        r"^(?P<prefix>\s*(?:export\s+)?)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<rest>.*)$"
    )
    seen = set()
    new_lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        match = None if (not stripped or stripped.startswith("#")) else assign.match(line)
        if match and match.group("name") in cleaned:
            key = match.group("name")
            seen.add(key)
            new_lines.append(
                "%s%s=%s%s" % (
                    match.group("prefix"), key, _render_value(cleaned[key]),
                    _assignment_suffix(match.group("rest")),
                )
            )
        else:
            new_lines.append(line)
    for key in sorted(cleaned):
        if key not in seen:
            new_lines.append("%s=%s" % (key, _render_value(cleaned[key])))

    body = "\n".join(new_lines)
    if not text or text.endswith("\n") or text.endswith("\r"):
        body += "\n"

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    os.replace(tmp, path)

    applied = []
    for key in sorted(cleaned):
        # Already set deliberately — including by an earlier load() of this
        # same file. Replacing it here would make the value in the shell
        # disagree with the value in use, which is the failure load() exists
        # to prevent. The file still has the new value for the next start.
        if os.environ.get(key):
            continue
        os.environ[key] = cleaned[key]
        applied.append(key)
    return {"written": sorted(cleaned), "applied": applied}


def describe(repo_root, name=DEFAULT_NAME):
    """What a startup line needs: whether the file exists and which names it
    defines. Values are never included."""
    path = path_for(repo_root, name)
    if not os.path.isfile(path):
        return {"present": False, "path": path, "names": []}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            names = sorted(parse(fh.read()))
    except OSError:
        names = []
    return {"present": True, "path": path, "names": names}
