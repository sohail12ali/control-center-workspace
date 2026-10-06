"""Setup wizard — the choices a machine makes once, written where Settings
already edits them.

Distinct from `onboarding.py`, which only reports the checklist and never
writes. This module is the write path: workspace name, which providers are
on, editor MCP files, and the Assistant's Talk/Work pair. There is no second
copy of those settings. Reopening the wizard reads the same files.

Nothing here returns a secret. Key *names* and whether each is set travel
to the browser; the values stay in `.env`.
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone

from . import agent_backends, assistant_config, dotenv, model_catalog, procs
from . import boards as boards_mod
from . import provider_overrides, setup_editor
from .paths import resolve_rel

STEPS = ("workspace", "environment", "files", "models", "review")

WORKSPACE_REL = os.path.join("console", ".cache", "workspace.json")
STATE_REL = os.path.join("console", ".cache", "onboarding.json")
AUTHOR_REL = os.path.join("knowledge-center", "logs", "author.local")

#: The same stock titles the checklist treats as "not named yet".
_STOCK_TITLES = ("", "Delivery Console")

_MODEL_KEYS = ("backend", "model", "work_backend", "work_model")


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def display_title(repo_root):
    """This machine's console name, or "" when it has not chosen one.

    Stored beside the other per-machine overrides, not in console.toml.
    That file is mostly comments, and rewriting it would delete them.
    """
    data = _read_json(resolve_rel(repo_root, WORKSPACE_REL))
    return str(data.get("title") or "").strip()


def _committed_title(repo_root):
    general = boards_mod.load_console_config(repo_root).get("general", {}) or {}
    return str(general.get("title") or "").strip()


def effective_title(repo_root):
    """What the header should say: the override, else the committed name."""
    return display_title(repo_root) or _committed_title(repo_root)


def _git_user(repo_root):
    try:
        out = subprocess.run(
            ["git", "config", "user.name"], cwd=repo_root,
            capture_output=True, text=True, timeout=5, **procs.popen_kwargs(),
        )
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def author_slug(name):
    """Same shape log-work uses: lowercase, spaces to hyphens, [a-z0-9-] only."""
    text = name.strip().lower().replace("_", " ")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text[:32] or "author")


def read_author(repo_root):
    path = resolve_rel(repo_root, AUTHOR_REL)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.readlines()]
    except OSError:
        return {"name": "", "slug": ""}
    # Blank lines are not a name. The slug is the second non-empty line when
    # present, matching stop_hook's "line 2" on a file this module writes
    # with no blanks between them.
    filled = [ln for ln in lines if ln]
    return {
        "name": filled[0] if filled else "",
        "slug": filled[1] if len(filled) > 1 else "",
    }


def _key_status(repo_root):
    """``set`` or ``missing`` for each allowlisted name. Values are not read
    into the result — only whether a non-empty one exists in the process or
    in the file."""
    file_values = {}
    path = dotenv.path_for(repo_root)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                file_values = dotenv.parse(fh.read())
        except OSError:
            file_values = {}
    out = {}
    for name in sorted(dotenv.KEY_ALLOWLIST):
        in_env = bool(os.environ.get(name, "").strip())
        in_file = bool(str(file_values.get(name) or "").strip())
        out[name] = "set" if in_env or in_file else "missing"
    return out


def _registry(repo_root):
    try:
        return agent_backends.registry(repo_root)
    except Exception:  # noqa: BLE001 - a bad agents.toml must not blank the wizard
        return {}


def _providers(repo_root):
    """API providers, on or off, without probing them.

    `provider_list` asks each enabled local server whether it is up. The
    wizard paints on first launch, and a probe of a sleeping box is a
    multi-second stall for a question that is only "do you want this on?".
    """
    try:
        rows = agent_backends.load_config(repo_root).get("backend", []) or []
    except Exception:  # noqa: BLE001
        return []
    keys = _key_status(repo_root)
    out = []
    for row in rows:
        if row.get("transport") not in agent_backends.API_TRANSPORTS:
            continue
        try:
            backend = agent_backends.Backend(row)
        except ValueError:
            continue
        key_env = backend.api_key_env
        out.append({
            "id": backend.id,
            "label": backend.label,
            "enabled": bool(row.get("enabled", True)),
            "is_local": backend.is_local,
            "key_env": key_env,
            # Only names the wizard is allowed to write get a field. A custom
            # provider's variable is still set by editing .env.
            "needs_key": bool(key_env) and key_env in dotenv.KEY_ALLOWLIST,
            "has_key": keys.get(key_env) == "set" if key_env else False,
        })
    out.sort(key=lambda p: (not p["enabled"], not p["is_local"], p["label"].lower()))
    return out


def _clis(repo_root):
    """CLIs that are actually on PATH. Shown as already available — not a
    key field, and not something the wizard turns on."""
    out = []
    for backend in _registry(repo_root).values():
        if backend.is_api or backend.resolved_command is None:
            continue
        out.append({"id": backend.id, "label": backend.label})
    out.sort(key=lambda row: row["label"].lower())
    return out


def _model_id(entry):
    """A picker id. `Backend.models` is ``{id, label, hint}`` dicts; the
    catalogue cache is rows with an ``id``. The wizard posts the id string,
    so a dict must not reach the browser or the option renders as
    ``[object Object]``."""
    if isinstance(entry, dict):
        return str(entry.get("id") or "").strip()
    return str(entry or "").strip()


def _model_ids(cached_rows, shortlist):
    ids = []
    seen = set()
    for entry in list(cached_rows or []) + list(shortlist or []):
        mid = _model_id(entry)
        if mid and mid not in seen:
            seen.add(mid)
            ids.append(mid)
    return ids


def _model_choices(repo_root):
    """Backends the Talk/Work dropdowns may pin, with whatever model ids are
    already known. The catalogue is the cache on disk — this does not call
    a provider."""
    choices = []
    for bid, backend in sorted(_registry(repo_root).items()):
        if backend.is_api:
            hit = model_catalog.cached(repo_root, bid)
            rows = hit["models"] if hit else []
            choices.append({
                "id": bid, "label": backend.label, "kind": "api",
                "is_local": backend.is_local,
                "models": _model_ids(rows, backend.models),
            })
        elif backend.resolved_command is not None:
            choices.append({
                "id": bid, "label": backend.label, "kind": "cli",
                "is_local": False,
                "models": _model_ids([], backend.models),
            })
    return choices


def _usable_model_path(repo_root):
    """True when something can already answer: a CLI on PATH, or an enabled
    provider that is local or already has its key. Does not probe. A key
    that exists only in `.env` counts — the file is the setup, even when this
    process has not loaded it yet."""
    keys = _key_status(repo_root)
    for backend in _registry(repo_root).values():
        if not backend.is_api and backend.resolved_command is not None:
            return True
        if not backend.is_api:
            continue
        if backend.is_local:
            return True
        env = backend.api_key_env
        if env and (keys.get(env) == "set" or backend.has_key):
            return True
    return False


def _completed_at(repo_root):
    data = _read_json(resolve_rel(repo_root, STATE_REL))
    return str(data.get("completed_at") or "")


def should_open(repo_root):
    """Cover the board only when setup has never been finished AND the
    machine still has neither a name nor a way to run a model.

    Either half being done is enough to stay out of the way. A workspace
    that already has a title, a CLI, or a key is not a first run.
    """
    if _completed_at(repo_root):
        return False
    if read_author(repo_root)["name"]:
        return False
    if _usable_model_path(repo_root):
        return False
    return True


def _role_label(backend_id, model_id, choices):
    if not (backend_id or "").strip():
        return "Automatic (local first)"
    label = backend_id
    for choice in choices:
        if choice["id"] == backend_id:
            label = choice["label"]
            break
    if (model_id or "").strip():
        return "%s · %s" % (label, model_id)
    return "%s · backend default" % label


def _review(repo_root, providers, choices, keys, editors):
    author = read_author(repo_root)
    title = effective_title(repo_root) or "Delivery Console"
    cfg = assistant_config.settings(repo_root)
    enabled = [p["label"] for p in providers if p["enabled"]]
    key_bits = ["%s %s" % (name, state) for name, state in keys.items()]
    wired = [e["label"] for e in editors if e["wired"]]
    return [
        {"id": "name", "label": "Your name",
         "value": author["name"] or "Not set",
         "where": "Settings, Workspace identity"},
        {"id": "title", "label": "Console name",
         "value": title, "where": "Settings, Workspace identity"},
        {"id": "providers", "label": "Providers",
         "value": ", ".join(enabled) or "None switched on",
         "where": "Settings, Model providers"},
        {"id": "keys", "label": "Keys",
         "value": ", ".join(key_bits) or "None",
         "where": "Settings, Model providers"},
        {"id": "editors", "label": "Editor files",
         "value": ", ".join(wired) or "None",
         "where": "the editor's own MCP config"},
        {"id": "talk", "label": "Talk",
         "value": _role_label(cfg.get("backend", ""), cfg.get("model", ""), choices),
         "where": "Settings, Assistant"},
        {"id": "work", "label": "Work",
         "value": _role_label(cfg.get("work_backend", ""), cfg.get("work_model", ""), choices),
         "where": "Settings, Assistant"},
    ]


def snapshot(repo_root):
    """The wizard's current answers. Safe to send to a browser."""
    author = read_author(repo_root)
    providers = _providers(repo_root)
    choices = _model_choices(repo_root)
    keys = _key_status(repo_root)
    editors = setup_editor.editor_status(repo_root)
    cfg = assistant_config.settings(repo_root)
    return {
        "steps": list(STEPS),
        "completed_at": _completed_at(repo_root),
        "should_open": should_open(repo_root),
        "workspace": {
            "name": author["name"],
            "slug": author["slug"],
            "title": effective_title(repo_root),
            "committed_title": _committed_title(repo_root),
            "git_name": _git_user(repo_root),
        },
        "providers": providers,
        "clis": _clis(repo_root),
        "keys": keys,
        "editors": editors,
        "models": {
            "backend": cfg.get("backend", "") or "",
            "model": cfg.get("model", "") or "",
            "work_backend": cfg.get("work_backend", "") or "",
            "work_model": cfg.get("work_model", "") or "",
            "choices": choices,
        },
        "review": _review(repo_root, providers, choices, keys, editors),
    }


def _save_author(repo_root, name, slug):
    path = resolve_rel(repo_root, AUTHOR_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("%s\n%s\n" % (name, slug))


def _apply_workspace(repo_root, body):
    name = str(body.get("name") or "").strip()
    title = str(body.get("title") or "").strip()
    if not name:
        raise ValueError("your name is required")
    if "\n" in name or "\r" in name or len(name) > 80:
        raise ValueError("name must be a single line")
    if "\n" in title or "\r" in title or len(title) > 80:
        raise ValueError("console name must be a single line")
    slug = str(body.get("slug") or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", slug or ""):
        slug = author_slug(name)
    _save_author(repo_root, name, slug)
    path = resolve_rel(repo_root, WORKSPACE_REL)
    if title and title not in _STOCK_TITLES:
        _write_json(path, {"title": title})
    elif os.path.isfile(path):
        # Clearing the field, or typing the stock name, drops the override
        # so the committed title shows again.
        try:
            os.remove(path)
        except OSError:
            _write_json(path, {})


def _apply_environment(repo_root, body):
    keys = body.get("keys") or {}
    if keys and not isinstance(keys, dict):
        raise ValueError("keys must be an object of variable names")
    # Validate before either write, so a rejected key does not leave the
    # provider toggles half-applied.
    to_write = {}
    for name, value in (keys or {}).items():
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise ValueError("%s must be a string" % name)
        if not value.strip():
            continue
        if "\n" in value or "\r" in value or "\x00" in value:
            raise ValueError("%s must be a single line" % name)
        to_write[str(name)] = value
    if to_write:
        unknown = sorted(set(to_write) - dotenv.KEY_ALLOWLIST)
        if unknown:
            raise ValueError(
                "not an environment key this setup can write: %s" % ", ".join(unknown))

    enabled = body.get("enabled")
    if "enabled" in body and enabled is not None and not isinstance(enabled, dict):
        raise ValueError("enabled must be an object")
    if isinstance(enabled, dict) and enabled:
        committed = [r.get("id") for r in agent_backends.committed_rows(repo_root)]
        provider_overrides.update(repo_root, {"enabled": enabled}, committed_ids=committed)
        agent_backends.forget_config()
    if to_write:
        dotenv.set_keys(repo_root, to_write)


def _apply_files(repo_root, body):
    editors = body.get("editors") if "editors" in body else []
    if not isinstance(editors, list):
        raise ValueError("editors must be a list")
    for editor in editors:
        setup_editor.setup_editor(repo_root, str(editor))


def _apply_models(repo_root, body):
    patch = {}
    for key in _MODEL_KEYS:
        patch[key] = "" if body.get(key) is None else str(body.get(key))
    # Automatic means both halves empty. A model id with no backend would
    # pin a model onto whichever backend resolves later — not what the
    # "Automatic" choice says.
    if not patch["backend"].strip():
        patch["model"] = ""
    if not patch["work_backend"].strip():
        patch["work_model"] = ""
    reg = _registry(repo_root)
    # CLIs must be on PATH. API providers may be pinned before their server
    # is up — onboarding is often the moment you turn one on.
    installed = []
    for bid, backend in reg.items():
        if backend.is_api or backend.resolved_command is not None:
            installed.append(bid)
    assistant_config.update(repo_root, patch, installed_backends=installed)


def apply(repo_root, body):
    """Apply one step and return a fresh snapshot. ``review`` is not a write."""
    if not isinstance(body, dict):
        raise ValueError("setup body must be an object")
    step = str(body.get("step") or "").strip()
    if step == "workspace":
        _apply_workspace(repo_root, body)
    elif step == "environment":
        _apply_environment(repo_root, body)
    elif step == "files":
        _apply_files(repo_root, body)
    elif step == "models":
        _apply_models(repo_root, body)
    elif step == "review":
        pass
    else:
        raise ValueError("unknown setup step %r" % step)
    return snapshot(repo_root)


def complete(repo_root):
    """Remember that the wizard was finished, so the next launch does not
    cover the board."""
    path = resolve_rel(repo_root, STATE_REL)
    data = _read_json(path)
    data["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_json(path, data)
    return snapshot(repo_root)


def public_detail(body):
    """A copy of a POST body safe to put in the audit log. Key names only."""
    if not isinstance(body, dict):
        return {}
    detail = {}
    for key, value in body.items():
        if key == "keys" and isinstance(value, dict):
            detail["keys"] = sorted(
                name for name, raw in value.items()
                if isinstance(raw, str) and raw.strip()
            )
        else:
            detail[key] = value
    return detail
