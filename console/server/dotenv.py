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
