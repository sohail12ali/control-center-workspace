"""What models a provider actually offers, fetched and cached on disk.

## Why this exists

`agents.toml` carries a `models` shortlist per backend, and the composer keeps
a paste box beside it, so any id is reachable. That is fine for claude, which
has eight ids worth naming. It is useless for OpenRouter, which serves hundreds
and changes them weekly, and it is actively wrong for Ollama, whose model list
is a fact about YOUR machine that no committed file could know.

So the catalogue is fetched from the provider and cached, while the shortlist
stays hand-curated. The composer offers both: cache first, shortlist second,
paste box last.

## Why the cache is gitignored and not config

A fetched catalogue is a fact about one account at one moment. Committing
OpenRouter's several hundred rows into a template other people clone would make
every clone carry a stale snapshot of somebody else's account — the same
reasoning that keeps the audit log out of git.

It also means this module never writes `agents.toml`. That file is
hand-maintained and mostly comments, and `tomlio.dumps()` does not preserve
comments — a single "save" would silently delete the documentation that makes
the file usable.

## Never raises

`fetch` returns `(rows, error)`. A provider being down, rate-limiting, or
answering with something unexpected must not break the page that asked — the
same contract `notify.discover_chat_ids` works to, for the same reason.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import agent_backends
from . import tomlio

CACHE_REL = os.path.join("console", ".cache", "models")

#: Providers can be enormous — OpenRouter is in the hundreds. The cap is high
#: enough to hold a full catalogue and low enough that a misbehaving endpoint
#: cannot write an unbounded file.
MAX_MODELS = 2000

FETCH_TIMEOUT = 20


def cache_dir(repo_root):
    return os.path.join(repo_root, CACHE_REL)


def cache_path(repo_root, backend_id):
    # The id is used as a filename, and ids come from config. Anything that
    # could climb out of the cache directory is refused rather than sanitised:
    # a backend id with a slash in it is a config mistake, not a filename.
    if not backend_id or "/" in backend_id or "\\" in backend_id or os.pardir in backend_id:
        raise ValueError("bad backend id for a cache path: %r" % backend_id)
    return os.path.join(cache_dir(repo_root), backend_id + ".toml")


# ------------------------------------------------------------------ parse --
def _price(pricing, key):
    """Provider prices are per token, as strings. Ours are per million tokens,
    as floats — the unit `telemetry` already works in.

    Returns None for anything unparseable, which travels all the way to the UI
    as "unpriced". A model whose price we could not read must never render as
    free; that is the same rule the spend panel already enforces.
    """
    raw = (pricing or {}).get(key)
    if raw in (None, ""):
        return None
    try:
        # Rounded because the multiply is what introduces the error, not the
        # source: OpenRouter's "0.0000008" per token becomes
        # 0.7999999999999999 per million, which then gets written to the cache
        # and read back looking like a suspiciously precise price.
        return round(float(raw) * 1_000_000, 6)
    except (TypeError, ValueError):
        return None


def parse(payload):
    """Rows from an OpenAI-compatible `/models` body.

    Handles the shape every provider here serves — `{"data": [...]}` — and
    tolerates the extra fields each one adds. OpenRouter carries `pricing` and
    `context_length`; Ollama carries neither and that is not an error, it is a
    local model with no price.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        # Some local servers answer a bare list.
        data = payload if isinstance(payload, list) else []

    rows = []
    for item in data[:MAX_MODELS]:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        if not mid:
            continue
        row = {"id": mid, "label": str(item.get("name") or mid).strip()}

        context = item.get("context_length") or item.get("context_window")
        top = item.get("top_provider")
        if not context and isinstance(top, dict):
            context = top.get("context_length")
        try:
            if context:
                row["context"] = int(context)
        except (TypeError, ValueError):
            pass

        pricing = item.get("pricing")
        if isinstance(pricing, dict):
            inp = _price(pricing, "prompt")
            out = _price(pricing, "completion")
            if inp is not None:
                row["input_per_mtok"] = inp
            if out is not None:
                row["output_per_mtok"] = out

        rows.append(row)

    rows.sort(key=lambda r: r["id"])
    return rows


# ------------------------------------------------------------------ fetch --
def resolve(repo_root, backend_id):
    """The backend, or (None, why-not). Shared by the fetch and the cached
    read so both give the SAME reason for the same problem.

    They did not, briefly: the cached read skipped this and answered "no cached
    catalogue — run refresh" for a CLI backend and for a disabled row alike.
    Refreshing helps with neither, so both readings sent people to do something
    that could not work.
    """
    try:
        backend = agent_backends.get(repo_root, backend_id)
    except ValueError as exc:
        return None, str(exc)
    if not backend.is_api:
        return None, ("%s is a CLI, not an API provider — it has no model "
                      "endpoint to ask. Its shortlist lives in agents.toml."
                      % backend.label)
    return backend, ""


def fetch(repo_root, backend_id, opener=None):
    """Ask the provider for its catalogue and cache it. Returns (rows, error).

    Never raises: every failure becomes an error string the caller can show.
    """
    backend, why = resolve(repo_root, backend_id)
    if backend is None:
        return [], why

    url = backend.models_url
    if not url:
        return [], "%s declares no base_url" % backend.label

    headers = {"Accept": "application/json"}
    if backend.api_key_env:
        key = os.environ.get(backend.api_key_env, "").strip()
        if not key:
            return [], ("%s is not set, so %s cannot be asked for its models."
                        % (backend.api_key_env, backend.label))
        headers["Authorization"] = "Bearer " + key
    headers.update(dict(backend.raw.get("extra_headers", {}) or {}))

    try:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with (opener or urllib.request.urlopen)(request, timeout=FETCH_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as exc:
        # The status is the actionable part. The URL is not echoed: for a
        # provider whose key travels in a header that is harmless, but the
        # habit is what keeps a token out of a log the day one travels in a
        # query string.
        if exc.code in (401, 403):
            return [], ("%s rejected the credentials (HTTP %s)."
                        % (backend.label, exc.code))
        return [], "%s returned HTTP %s" % (backend.label, exc.code)
    except urllib.error.URLError as exc:
        return [], agent_backends._url_error_reason(exc, url)
    except ValueError:
        return [], "%s answered with something that is not JSON" % backend.label
    except Exception as exc:  # noqa: BLE001
        return [], "%s while asking %s" % (type(exc).__name__, backend.label)

    rows = parse(payload)
    if not rows:
        return [], ("%s answered, but listed no models. For a local server "
                    "that usually means nothing is pulled or loaded yet."
                    % backend.label)

    error = _write_cache(repo_root, backend_id, rows)
    return rows, error


def peek(models_url, api_key_env="", opener=None):
    """Model ids served at `models_url`, for a URL that is not a backend yet.

    Used by the provider **Test** button, so what you see before saving is what
    the console would see after. Never raises and never caches: nothing has an
    id to cache under until it has been added.
    """
    headers = {"Accept": "application/json"}
    key_env = (api_key_env or "").strip()
    if key_env:
        key = os.environ.get(key_env, "").strip()
        if key:
            headers["Authorization"] = "Bearer " + key
    try:
        request = urllib.request.Request(models_url, headers=headers, method="GET")
        with (opener or urllib.request.urlopen)(request, timeout=FETCH_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    except Exception:  # noqa: BLE001
        # The caller already has the probe's reason, which is the useful one.
        return []
    return [row["id"] for row in parse(payload) if row.get("id")]


def _write_cache(repo_root, backend_id, rows):
    """Persist the catalogue. A failure to cache is reported, not raised — the
    rows were fetched successfully and are still usable this session."""
    try:
        os.makedirs(cache_dir(repo_root), exist_ok=True)
        tomlio.atomic_write(cache_path(repo_root, backend_id), {
            "backend": backend_id,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(rows),
            "model": rows,
        })
    except Exception as exc:  # noqa: BLE001
        return "fetched %d models but could not cache them (%s)" % (
            len(rows), type(exc).__name__)
    return ""


# ------------------------------------------------------------------ read ---
def cached(repo_root, backend_id):
    """The stored catalogue, or None. `age_days` is what the UI shows.

    A stale cache is returned WITH its age rather than withheld. Hiding it
    would leave the picker empty and the user with no way to tell whether that
    means "never fetched" or "too old to trust".
    """
    try:
        path = cache_path(repo_root, backend_id)
    except ValueError:
        return None
    if not os.path.isfile(path):
        return None
    try:
        data = tomlio.load(path)
    except Exception:  # noqa: BLE001
        return None  # a corrupt cache is a missing cache, not a crash

    rows = [r for r in data.get("model", []) if isinstance(r, dict) and r.get("id")]
    fetched_at = data.get("fetched_at", "")
    return {
        "backend": backend_id,
        "fetched_at": fetched_at,
        "count": len(rows),
        "models": rows,
        "age_days": _age_days(path),
    }


def _age_days(path):
    try:
        return round((time.time() - os.path.getmtime(path)) / 86400.0, 1)
    except OSError:
        return None


def summary(repo_root):
    """One row per API backend: is it cached, how many, how old.

    Drives the Settings panel and `kanban agents models` with no argument.
    """
    out = []
    for bid, backend in sorted(agent_backends.registry(repo_root).items()):
        if not backend.is_api:
            continue
        hit = cached(repo_root, bid)
        out.append({
            "id": bid,
            "label": backend.label,
            "available": backend.installed,
            "reason": backend.unavailable_reason,
            "is_local": backend.is_local,
            "cached": bool(hit),
            "count": hit["count"] if hit else 0,
            "fetched_at": hit["fetched_at"] if hit else "",
            "age_days": hit["age_days"] if hit else None,
        })
    return out


def format_list(rows, limit=40):
    """Table for the CLI. Truncated, with the count said out loud — a provider
    with 400 models should not flood a terminal, and silently showing 40 of
    them would misrepresent what was fetched."""
    if not rows:
        return "No models."
    lines = ["%-52s %-10s %10s %10s" % ("ID", "CONTEXT", "IN $/Mtok", "OUT $/Mtok")]
    for row in rows[:limit]:
        ctx = row.get("context")
        lines.append("%-52s %-10s %10s %10s" % (
            row["id"][:52],
            "{:,}".format(ctx) if ctx else "-",
            ("%.2f" % row["input_per_mtok"]) if row.get("input_per_mtok") is not None else "-",
            ("%.2f" % row["output_per_mtok"]) if row.get("output_per_mtok") is not None else "-",
        ))
    if len(rows) > limit:
        lines.append("... and %d more (%d total)" % (len(rows) - limit, len(rows)))
    return "\n".join(lines)
