"""Shared view-state preferences: one JSON file per machine.

The desktop app and every browser tab used to keep their own `localStorage`,
so a theme chosen in one never reached the other (T-036). This holds the
single copy, in `console/.cache/prefs.json` (gitignored, per machine, like the
other `.cache` state files).

## Pure and stdlib-only

No HTTP, no plugin registry: `features/prefs_feature.py` and
`features/shell_feature.py` are the only callers. Nothing on the server reads a
preference to decide behaviour. These are view settings, writable by any page
that can send the CSRF header on an unauthenticated port, so anything the
server must act on keeps its own validated setting (the `notify.py` stance).

## Why JSON and not TOML

`tomlio` has one table level and no `null`, so it cannot hold an arbitrary
value such as the layout object. Only its `_replace` is reused, for the
Windows-safe retry when a reader briefly holds the target open.

## Shape

    {"v": 1, "rev": N, "prefs": {key: any JSON}, "import_closed": false}

`rev` is a counter that moves only when stored state actually changed, so a
client can tell "someone else wrote" from "nothing happened" by comparing one
integer. `import_closed` is set by `reset` so a stale browser cannot bring back
values the user deliberately cleared (see `import_values`).

## Never raises on read

A missing, empty, non-UTF-8, non-JSON or wrong-shape file reads as an empty
store, and the next write replaces it. A preference file must never be able to
take the console down, and the page already copes with "no preferences".
"""

import json
import os
import re
import threading

from . import tomlio
from .paths import resolve_rel

STORE_REL = os.path.join("console", ".cache", "prefs.json")

#: Client mirrors (`core.js`) carry the same three numbers and the same pattern
#: text, so a value the server would refuse is never sent. Change them together.
KEY_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"
MAX_VALUE_BYTES = 32768
MAX_KEYS = 128
MAX_FILE_BYTES = 262144

_KEY_RE = re.compile(KEY_PATTERN)

#: One lock for reads and writes. The server is a `ThreadingHTTPServer`, so two
#: requests can arrive together; reads take it too because on Windows a reader
#: that opens the file mid-replace can get a PermissionError, which would read
#: as "empty" and look to a client like a reset.
_lock = threading.Lock()


def _empty():
    return {"v": 1, "rev": 0, "prefs": {}, "import_closed": False}


def _no_constant(name):
    # `json.loads` accepts NaN/Infinity by default; a hand-edited file holding
    # one could never be written back (`allow_nan=False`), so call it corrupt.
    raise ValueError("non-finite number %s" % name)


def _path(repo_root):
    return resolve_rel(repo_root, STORE_REL)


def _load(repo_root):
    """Parse the file, or the empty store. Caller holds `_lock`."""
    try:
        with open(_path(repo_root), "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"), parse_constant=_no_constant)
    except (OSError, ValueError, RecursionError):
        return _empty()
    if not isinstance(data, dict) or not isinstance(data.get("prefs"), dict):
        return _empty()
    rev = data.get("rev")
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
        return _empty()
    return {"v": 1, "rev": rev, "prefs": data["prefs"],
            "import_closed": data.get("import_closed") is True}


def _text(value):
    """The serialised form of one value; `ValueError` when it has none.

    `ensure_ascii=False` so the byte count is the UTF-8 length of what a
    browser's `JSON.stringify` would produce, which is what the client mirrors.
    """
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("it is not a finite JSON value (%s)" % exc)


def _same(a, b):
    # Compared as JSON text, not with `==`: in Python `1 == True` and
    # `1 == 1.0`, which would swallow a real change from `true` to `1`.
    return _text(a) == _text(b)


def _key_error(key):
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        return ("%r is not a valid preference key: start with a letter, then up "
                "to 63 letters, digits, '.', '_' or '-'" % (key,))
    return None


def _value_error(key, value):
    """A sentence naming the key and the cause, or None when the value is fine."""
    try:
        size = len(_text(value).encode("utf-8"))
    except ValueError as exc:
        return "preference %r was refused: %s" % (key, exc)
    if size > MAX_VALUE_BYTES:
        return ("preference %r was refused: its value is %d bytes and the limit "
                "is %d" % (key, size, MAX_VALUE_BYTES))
    return None


def _serialise(state):
    return json.dumps(state, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _too_big(prefs):
    """The reason `prefs` cannot be stored as a whole, or None."""
    if len(prefs) > MAX_KEYS:
        return "the %d-key limit would be exceeded" % MAX_KEYS
    state = {"v": 1, "rev": 0, "prefs": prefs, "import_closed": False}
    # Headroom for a larger `rev`, so a write that fits now cannot be refused
    # only because the counter grew a digit.
    if len(_serialise(state)) + 16 > MAX_FILE_BYTES:
        return "the %d-byte file limit would be exceeded" % MAX_FILE_BYTES
    return None


def _commit(repo_root, state):
    """Write the whole file: temp file, then replace, so a reader sees the old
    file or the new one and never half of either. Caller holds `_lock`."""
    path = _path(repo_root)
    data = _serialise(state)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("preferences were not saved: the file would be %d bytes "
                         "and the limit is %d" % (len(data), MAX_FILE_BYTES))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    tomlio._replace(tmp, path)


def read(repo_root):
    """The stored state, or the empty store. Never raises."""
    with _lock:
        return _load(repo_root)


def snapshot(repo_root):
    """What `GET /api/prefs` returns."""
    state = read(repo_root)
    return {"prefs": state["prefs"], "rev": state["rev"],
            "import_open": not state["import_closed"]}


def rev(repo_root):
    return read(repo_root)["rev"]


def apply(repo_root, set=None, delete=None):
    """Set and delete keys. Returns `{rev, prev}`.

    All-or-nothing: every key and value is checked before anything is read or
    written, so one bad key in a request stores none of it. A key named in both
    `set` and `delete` ends up deleted; the client coalesces so it never sends
    that, and "delete wins" is the safer answer to an ambiguous request.

    `prev` is the revision before this call. A client adopts `rev` as its own
    only when `prev` is the revision it last knew; otherwise another client
    wrote in between and the client must pull instead of believing it is
    current (D-21).
    """
    sets = set
    if sets is None:
        sets = {}
    if not isinstance(sets, dict):
        raise ValueError("set must be an object of key/value pairs")
    dels = [] if delete is None else delete
    if not isinstance(dels, list):
        raise ValueError("del must be a list of keys")
    for key in list(sets) + dels:
        problem = _key_error(key)
        if problem:
            raise ValueError(problem)
    for key, value in sets.items():
        problem = _value_error(key, value)
        if problem:
            raise ValueError(problem)

    with _lock:
        state = _load(repo_root)
        old = state["prefs"]
        new = dict(old)
        new.update(sets)
        for key in dels:
            new.pop(key, None)
        prev = state["rev"]
        if _same(new, old):
            return {"rev": prev, "prev": prev}
        added = [k for k in sets if k not in old and k in new]
        if added and len(new) > MAX_KEYS:
            raise ValueError("preference %r was refused: the %d-key limit would "
                             "be exceeded" % (added[0], MAX_KEYS))
        state["prefs"] = new
        state["rev"] = prev + 1
        _commit(repo_root, state)
        return {"rev": state["rev"], "prev": prev}


def import_values(repo_root, values):
    """Move one browser's legacy `localStorage` values onto the server.

    One-time, per client, per key, and never overwriting: the first value the
    server holds for a key wins (BR-3). That is deterministic, idempotent and
    loses nothing in the realistic case, where the app held none of the keys
    the browser did. Last-writer-wins was rejected: `localStorage` values carry
    no timestamps, so whichever client launched last would clobber the other.

    Returns `{prefs, rev, imported, skipped, rejected, closed}`:

    - `imported`: stored now, or already stored with an equal value (so a retry
      or two tabs importing at once report the same thing and move `rev` once);
    - `skipped`: the server holds a *different* value, which stays;
    - `rejected`: `[{key, reason}]`, a key or value the store cannot hold, or
      the overflow once a key-count or file-size cap is reached (earlier keys
      are kept, the later ones are what is refused);
    - `closed`: `reset` closed the window, nothing was imported (BR-4).
    """
    if not isinstance(values, dict):
        raise ValueError("values must be an object of key/value pairs")
    with _lock:
        state = _load(repo_root)
        prefs = dict(state["prefs"])
        out = {"imported": [], "skipped": [], "rejected": []}
        if state["import_closed"]:
            return {"prefs": prefs, "rev": state["rev"], "closed": True, **out}
        changed = False
        for key, value in values.items():
            reason = _key_error(key) or _value_error(key, value)
            if reason:
                out["rejected"].append({"key": str(key), "reason": reason})
            elif key in prefs:
                out["imported" if _same(prefs[key], value) else "skipped"].append(key)
            else:
                prefs[key] = value
                full = _too_big(prefs)
                if full:
                    del prefs[key]
                    out["rejected"].append({"key": key, "reason": full})
                else:
                    out["imported"].append(key)
                    changed = True
        if changed:
            state["prefs"] = prefs
            state["rev"] += 1
            _commit(repo_root, state)
        return {"prefs": prefs, "rev": state["rev"], "closed": False, **out}


def reset(repo_root):
    """Empty every preference and close the import window.

    Closing it is what makes Reset stick: without it a browser that still held
    its old `localStorage` keys would import them back on its next boot.
    """
    with _lock:
        state = _load(repo_root)
        if not state["prefs"] and state["import_closed"]:
            return {"prefs": {}, "rev": state["rev"], "closed": True}
        state["prefs"] = {}
        state["import_closed"] = True
        state["rev"] += 1
        _commit(repo_root, state)
        return {"prefs": {}, "rev": state["rev"], "closed": True}
