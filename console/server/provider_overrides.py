"""T-012: which model providers are on, and any you added yourself.

Two layers, the same split `assistant_config` already uses for the Assistant's
settings:

    console/config/agents.toml               committed — the rows this
                                             workspace ships with, and the
                                             ~200 lines of comments that
                                             explain them.
    console/.cache/agents/providers.json     this machine — what you switched
                                             on, and any endpoint you added.

## Why not just edit agents.toml

Two reasons, and the second is the load-bearing one.

Whether you happen to run Ollama is a fact about your laptop, not about the
template — the same argument that keeps a chosen backend out of the committed
file. And `agents.toml` is a *document*: it explains why the ollama row needs a
tool-capable model, what LM Studio means by "loaded", why a local context cap is
lower. `tomlio.dumps()` would round-trip that file into bare key-value pairs and
silently delete every word of it. The Settings panel's own comment already says
it refuses to write agents.toml for exactly this reason. So the override is a
separate, machine-local file, and the committed one is never touched.

## What a custom provider is, and is not

It is a `base_url` that speaks the OpenAI chat API, plus a label. It is NOT a
place to put an API key: `api_key_env` names the environment variable, the
value lives in the workspace `.env`, and `openai_client` reads it at use time.
Nothing here ever holds a secret, so this file staying gitignored is a second
line of defence rather than the only one.
"""

import json
import os
import re

#: Where this machine's choices live. Gitignored (`console/.cache/`).
OVERRIDE_REL = os.path.join("console", ".cache", "agents", "providers.json")

#: Ids are used as filenames (the model cache) and as URL path segments, and
#: they name a row in a config file. A slug keeps all three honest.
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")

#: An environment variable NAME. The check exists to catch someone pasting the
#: key itself into the field: a real key has characters this rejects, and the
#: refusal says what the field is for rather than storing a secret.
ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

#: What a custom row does not have to say. Everything here is either forced by
#: the transport or copied from the shipped local-provider rows, so a provider
#: you add behaves like `ollama` rather than like an unreviewed special case.
DEFAULTS_FOR_CUSTOM = {
    "transport": "openai_api",
    "enabled": True,
    "timeout": 300,
    "prompt_prefix_style": "none",
    # The same gate as the ollama and lm-studio rows: writes and shell ask a
    # human in the chat. A model you pointed at a URL five seconds ago gets no
    # more trust than the ones that shipped with the template.
    "gated_tools": ["write_file", "edit_file", "run_command",
                    "console_desktop_screenshot",
                    "console_desktop_clipboard_read",
                    "console_delegate"],
    "approval_timeout": 300,
    # A locally served model's context window is usually the constraint, and a
    # custom endpoint is more often local than not.
    "max_tool_rounds": 15,
    "max_history_messages": 40,
    "models": [],
    "modes": ["default"],
    "default_mode": "default",
    "mode_blurbs": {
        "default": "writes and shell ask you in the chat; reads and console "
                   "lookups do not",
    },
}

#: Fields a custom provider may set. Anything else is refused rather than
#: stored and ignored — a typo that persisted would look like it worked.
CUSTOM_FIELDS = ("id", "label", "base_url", "api_key_env", "models_url",
                 "notes", "start_hint")


def path(repo_root):
    return os.path.join(repo_root, OVERRIDE_REL)


def load(repo_root):
    """This machine's choices, or the empty set of them."""
    blank = {"enabled": {}, "custom": [], "where": {}}
    try:
        with open(path(repo_root), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        # A missing file is the ordinary case; a corrupt one must not take the
        # console down, and the committed rows are always a working set.
        return blank
    if not isinstance(data, dict):
        return blank
    enabled = data.get("enabled")
    custom = data.get("custom")
    where = data.get("where")
    return {
        "enabled": {str(k): bool(v) for k, v in (enabled or {}).items()},
        "custom": [c for c in (custom or []) if isinstance(c, dict)],
        "where": {str(k): dict(v) for k, v in (where or {}).items()
                  if isinstance(v, dict)},
    }


def save(repo_root, data):
    """Write atomically, so a crash mid-write cannot leave half a config."""
    target = path(repo_root)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, target)


def apply(rows, overrides):
    """Merge the committed rows with this machine's choices.

    Pure, and separate from the file, because this is the part with rules in
    it: which `enabled` wins, and what a half-specified custom row becomes.
    """
    enabled = (overrides or {}).get("enabled") or {}
    where = (overrides or {}).get("where") or {}
    out = []
    for row in rows or []:
        row = dict(row)
        rid = row.get("id")
        if rid in enabled:
            row["enabled"] = enabled[rid]
        # Where this machine actually reaches it. The shipped `lm-studio` row
        # says 127.0.0.1:1234 because that is where LM Studio runs by default;
        # yours may be a box on the LAN with its own key. Overriding the
        # address here keeps agents.toml — and its comments — the same file on
        # every machine.
        for field, value in (where.get(rid) or {}).items():
            if value:
                row[field] = value
        if (where.get(rid) or {}).get("api_key_env"):
            row["auth"] = "key"
        out.append(row)
    known = {r.get("id") for r in out}
    for custom in (overrides or {}).get("custom") or []:
        rid = custom.get("id")
        # A custom row can never shadow a committed one. If the ids collide the
        # committed row wins, because it is the one with the comments and the
        # review; `validate` refuses the collision at write time, and this is
        # the belt to that braces.
        if not rid or rid in known:
            continue
        row = dict(DEFAULTS_FOR_CUSTOM)
        row.update({k: v for k, v in custom.items() if k in CUSTOM_FIELDS and v not in (None, "")})
        row["auth"] = "key" if row.get("api_key_env") else "none"
        row["custom"] = True
        if rid in enabled:
            row["enabled"] = enabled[rid]
        out.append(row)
        known.add(rid)
    return out


def rows_for(repo_root, committed_rows):
    """The committed rows with this machine's overrides applied."""
    return apply(committed_rows, load(repo_root))


def validate(provider, committed_ids=()):
    """Check one custom provider, returning the cleaned row.

    Raises ValueError with a sentence a person can act on — the same contract
    `assistant_config.update` keeps, so the UI can show the refusal rather than
    re-implementing the rules and drifting from them.
    """
    if not isinstance(provider, dict):
        raise ValueError("a provider needs at least an id and a base_url")

    unknown = sorted(set(provider) - set(CUSTOM_FIELDS))
    if unknown:
        raise ValueError("not a provider field: %s" % ", ".join(unknown))

    pid = str(provider.get("id") or "").strip().lower()
    if not ID_RE.match(pid):
        raise ValueError(
            "id must be 2-32 characters of lowercase letters, digits, - or _ "
            "(it names a row and a cache file)")
    if pid in set(committed_ids):
        raise ValueError(
            "%r is already a provider in console/config/agents.toml — switch "
            "that one on instead of shadowing it" % pid)

    base_url = str(provider.get("base_url") or "").strip().rstrip("/")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ValueError("base_url must start with http:// or https://")

    key_env = str(provider.get("api_key_env") or "").strip()
    if key_env and not ENV_RE.match(key_env):
        # The likely mistake, said plainly: this field is the NAME of an
        # environment variable, not the key. Storing a pasted key here would
        # put a secret in a file this project has never put secrets in.
        raise ValueError(
            "api_key_env is the NAME of an environment variable (like "
            "TOGETHER_API_KEY), not the key itself — put the value in the "
            "workspace .env")

    clean = {"id": pid, "base_url": base_url,
             "label": str(provider.get("label") or "").strip() or pid}
    if key_env:
        clean["api_key_env"] = key_env
    for field in ("models_url", "notes", "start_hint"):
        value = str(provider.get(field) or "").strip()
        if value:
            clean[field] = value
    return clean


#: Fields a committed row can be re-pointed at, per machine. Deliberately
#: only the two that are facts about THIS machine — where the server is, and
#: what its key is called. Everything else about a row (its gates, its context
#: caps, its transport) is a reviewed decision that belongs in the committed
#: file.
WHERE_FIELDS = ("base_url", "api_key_env")


def validate_where(patch):
    """Check a re-pointing patch, returning the cleaned fields."""
    if not isinstance(patch, dict) or not patch:
        raise ValueError("nothing to change")
    unknown = sorted(set(patch) - set(WHERE_FIELDS))
    if unknown:
        raise ValueError("cannot override %s on a shipped provider — only %s"
                         % (", ".join(unknown), " and ".join(WHERE_FIELDS)))
    clean = {}
    if "base_url" in patch:
        url = str(patch["base_url"] or "").strip().rstrip("/")
        # Empty is not invalid — it is the undo. Clearing the field is how a
        # provider goes back to where the committed row says it lives, and a
        # refusal here would leave no way back except editing the file.
        if url and not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        clean["base_url"] = url
    if "api_key_env" in patch:
        name = str(patch["api_key_env"] or "").strip()
        if name and not ENV_RE.match(name):
            raise ValueError(
                "api_key_env is the NAME of an environment variable (like "
                "LMSTUDIO_API_KEY), not the key itself — put the value in the "
                "workspace .env")
        clean["api_key_env"] = name
    return clean


def update(repo_root, patch, committed_ids=()):
    """Apply a patch and persist it. Returns the stored overrides.

    Accepts, in one call:
        {"enabled": {"ollama": true}}   switch committed or custom rows on/off
        {"custom": {...}}               add or replace one custom provider
        {"remove": "id"}                drop a custom provider

    Nothing is written unless every part validates, so a half-wrong request
    leaves the stored config exactly as it was.
    """
    if not isinstance(patch, dict) or not patch:
        raise ValueError("nothing to change")
    unknown = sorted(set(patch) - {"enabled", "custom", "remove", "where"})
    if unknown:
        raise ValueError("not a provider setting: %s" % ", ".join(unknown))

    data = load(repo_root)
    known_custom = {c.get("id") for c in data["custom"]}

    if "custom" in patch:
        # A custom row's own id is not a collision with itself: replacing one
        # is how you edit it.
        clean = validate(patch["custom"], committed_ids=committed_ids)
        data["custom"] = [c for c in data["custom"] if c.get("id") != clean["id"]]
        data["custom"].append(clean)
        known_custom.add(clean["id"])

    if "remove" in patch:
        rid = str(patch["remove"] or "").strip()
        if rid not in known_custom:
            raise ValueError(
                "%r is not one of your providers — only ones you added here "
                "can be removed" % rid)
        data["custom"] = [c for c in data["custom"] if c.get("id") != rid]
        data["enabled"].pop(rid, None)

    if "where" in patch:
        pointing = patch["where"]
        if not isinstance(pointing, dict) or not pointing:
            raise ValueError("where must name at least one provider")
        allowed = set(committed_ids) | {c.get("id") for c in data["custom"]}
        stored_where = data.setdefault("where", {})
        for pid, fields in pointing.items():
            if pid not in allowed:
                raise ValueError("unknown provider %r" % pid)
            clean = validate_where(fields)
            if clean.get("base_url") or clean.get("api_key_env"):
                stored_where.setdefault(str(pid), {}).update(clean)
            else:
                # An empty patch is how you put a provider back where the
                # committed row says it lives.
                stored_where.pop(str(pid), None)

    if "enabled" in patch:
        flags = patch["enabled"]
        if not isinstance(flags, dict) or not flags:
            raise ValueError("enabled must name at least one provider")
        allowed = set(committed_ids) | {c.get("id") for c in data["custom"]}
        for pid, on in flags.items():
            if pid not in allowed:
                raise ValueError("unknown provider %r" % pid)
            data["enabled"][str(pid)] = bool(on)

    save(repo_root, data)
    return data
