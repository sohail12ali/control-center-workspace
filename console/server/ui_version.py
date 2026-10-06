"""A short stamp that changes when the UI the server would serve has changed.

A page that has been open for days keeps running the JS it booted with
(T-036). The server tells it what the UI is *now* with one field on
`/api/config`, which the page already polls every 15 s, so the page can compare
and reload at a safe moment. This module only computes that field.

## What is stamped

1. **The static assets**: the regular files in `console/static` matching
   `ASSET_PATTERNS`, as sorted `(basename, size, mtime_ns)`. Size and mtime, not
   content: hashing would read every byte of every asset on each heartbeat (or
   need a cache to invalidate), and what it buys is only skipping one harmless
   reload after a `git checkout` or a `touch`. A stat sweep of 29 files measured
   0.144 ms.
2. **A manifest digest** of the tab rows and the route table. A restart that
   adds an endpoint (such as `/api/prefs`) then looks like a change, which is
   what moves a page that booted against the older server onto it. A
   Python-only change that alters neither does not reload the UI, correctly.

## Why the patterns are copied, not imported

`ASSET_PATTERNS` repeats the tuple in `export._copy_frontend` and enumerates it
with `glob.glob` the same way, so an editor temp file (`*.swp`, `.#core.js`)
never counts here and never ships in an export. A test compares the two name
sets; `export.py` is not edited for this (D-28), so nothing about a static
snapshot changes and it carries no `ui_version`.

## Never raises, never reads a file

It opens no file, so a held lock or a half-written asset cannot make
`/api/config` slow or fail. That endpoint is also the desktop sidecar's
readiness probe, so the stamp degrades to "absent" (`None`) rather than raising:
an unlistable directory gives `None`, and a file that vanishes between the
listing and its `stat` (an editor's save-by-rename) is skipped.
"""

import glob
import hashlib
import json
import os
import stat

#: The directory `httpd.py` serves and `export.py` copies. Owned here so the
#: payload code names one constant; a test pins the three paths equal.
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

#: Same set `export._copy_frontend` copies (`export.py:90`).
ASSET_PATTERNS = ("*.html", "*.js", "*.css", "*.png")

#: Hex characters kept. 48 bits is plenty to tell "changed" from "not": the
#: value is compared for inequality between two nearby moments, never looked up.
DIGEST_LEN = 12


def fingerprint(static_dir):
    """Sorted `[(basename, size, mtime_ns)]` of the stamped assets, or `None`
    when the directory cannot be listed (not a directory, or `OSError`)."""
    try:
        # glob swallows a listing error and returns [], which would be
        # indistinguishable from an empty directory and would stamp a constant.
        os.listdir(static_dir)
    except OSError:
        return None
    entries = []
    for pattern in ASSET_PATTERNS:
        for path in glob.glob(os.path.join(static_dir, pattern)):
            try:
                st = os.stat(path)
            except OSError:
                continue  # vanished after the listing: skip it, do not fail
            if stat.S_ISREG(st.st_mode):
                entries.append((os.path.basename(path), st.st_size, st.st_mtime_ns))
    entries.sort()
    return entries


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_digest(tabs, routes):
    """Digest of the tab rows and the `(method, pattern, name)` route list.

    Routes are sorted, so the digest depends on which endpoints exist, not on
    the order plugins registered them in. `default=str` keeps this total: it
    runs inside `/api/config`, which must not fail over a stamp.
    """
    triples = sorted([r.get("method", ""), r.get("pattern", ""), r.get("name", "")] for r in routes)
    return _sha(json.dumps({"tabs": tabs, "routes": triples}, sort_keys=True, default=str))


def compute(static_dir, manifest):
    """The stamp: first `DIGEST_LEN` lowercase hex of sha256 over the asset
    fingerprint and `manifest`, or `None` when the directory cannot be listed."""
    entries = fingerprint(static_dir)
    if entries is None:
        return None
    body = json.dumps([entries, manifest], separators=(",", ":"))
    return _sha(body)[:DIGEST_LEN]


class UiVersion:
    """What `shell_feature` holds for the life of the process.

    The manifest cannot change without a restart, so `manifest_fn` runs once,
    on the first `value()` (by then every plugin has applied). The static half
    is recomputed on every call and never cached: a cache would need a way to
    know a file changed, which is the question being answered. Two requests
    racing on the first call may both run `manifest_fn`; it is pure, so they
    agree.
    """

    def __init__(self, static_dir, manifest_fn):
        self._static_dir = static_dir
        self._manifest_fn = manifest_fn
        self._manifest = None
        self._ready = False

    def value(self):
        if not self._ready:
            self._manifest = self._manifest_fn()
            self._ready = True
        return compute(self._static_dir, self._manifest)
