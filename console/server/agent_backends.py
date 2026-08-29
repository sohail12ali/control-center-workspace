"""Backend registry: which CLIs this console can talk to, and how.

The point of this module is that adding a CLI is **config, not code**. A
backend is a table in `console/config/agents.toml`, and it declares its own
capabilities, its own permission-mode ladder, and templates for the argv in
each transport. Nothing here names a specific product, and the two bundled
entries (claude, cursor-agent) are ordinary rows with no privileges — delete
them and the tab offers whatever is left.

## Transports, and why a backend must declare which it has

    stream_json   ONE process for the whole conversation, stdin held open as a
                  JSON-lines channel. Messages can arrive mid-turn, so
                  steering and a true interrupt are possible.
    resume        ONE process PER TURN, continued with a resume flag. It can
                  stream output perfectly well, but there is no open channel
                  to write to, so a message can only be QUEUED for the next
                  turn.
    oneshot       one process, one prompt, no continuation. Watch it and stop
                  it; that's all.

That difference is a CLI capability, not a preference, so the UI reads
`steerable` off the backend and hides the steer control on a transport that
cannot do it — rather than offering a button that silently does something else.

## Permission modes

Each backend lists its own ladder with a blurb per rung, because the words
mean different things per CLI ("plan" is read-only in both, but claude's
"default" gates via a hook while cursor-agent's prompts in-process). Full
bypass modes are deliberately NOT shipped in the default config: turning the
gate off is a decision for a terminal you're sitting in front of, not a button
on a web page. A fork that wants one adds it to its own config and owns that.
"""

import os
import shutil

from . import boards as boards_mod
from . import tomlio

CONFIG_REL = os.path.join("console", "config", "agents.toml")

#: The transports a backend row may declare.
#:
#: `openai_api` is the odd one out and deliberately so: the other three spawn
#: somebody else's agent and inherit its tools and permission model, while this
#: one has no process at all — the console runs the loop, holding its own verbs
#: as tools and its own approval gate. See `agent_api_session`.
TRANSPORTS = ("stream_json", "resume", "oneshot", "openai_api")

#: Transports with no executable. `installed` means "has a key" for these, and
#: asking PATH about them would report every one as missing.
API_TRANSPORTS = ("openai_api",)

_cache = {}


def load_config(repo_root, force=False):
    """Backend definitions. Falls back to console.toml's `[agents.backends]`
    so an older config keeps working, but agents.toml is the real home."""
    if not force and repo_root in _cache:
        return _cache[repo_root]
    path = os.path.join(repo_root, CONFIG_REL)
    if os.path.isfile(path):
        data = tomlio.load(path)
    else:
        legacy = boards_mod.load_console_config(repo_root).get("agents", {})
        data = {"backend": _from_legacy(legacy.get("backends", {}))}
    _cache[repo_root] = data
    return data


def _from_legacy(mapping):
    out = []
    for bid, cfg in (mapping or {}).items():
        out.append({
            "id": bid,
            "label": cfg.get("label", bid),
            "command": cfg.get("command", bid),
            "transport": "oneshot",
            "oneshot_args": cfg.get("args", []),
        })
    return out


def _expand(template, values):
    """Substitute {placeholders}, dropping any arg whose placeholder resolved
    to empty — that's how an optional flag disappears rather than being passed
    as an empty string the CLI then rejects."""
    out = []
    for item in template:
        if not isinstance(item, str):
            continue
        # A bare optional token like "{model}" vanishes entirely when unset.
        if item.startswith("{") and item.endswith("}") and item.count("{") == 1:
            key = item[1:-1]
            val = values.get(key, "")
            if val == "" or val is None:
                out.append(None)
                continue
            out.append(str(val))
            continue
        rendered = item
        for key, val in values.items():
            rendered = rendered.replace("{" + key + "}", "" if val is None else str(val))
        out.append(rendered)
    # Drop a flag whose value slot collapsed: ["--model", None] -> [].
    cleaned = []
    skip_next = False
    for i, item in enumerate(out):
        if skip_next:
            skip_next = False
            continue
        if item is None:
            # Remove the preceding flag we already emitted, if any.
            if cleaned and cleaned[-1].startswith("-"):
                cleaned.pop()
            continue
        cleaned.append(item)
    return cleaned


class Backend:
    """One launchable CLI, described entirely by config."""

    __slots__ = ("id", "label", "command", "transport", "modes", "default_mode",
                 "mode_flag", "mode_blurbs", "models", "gated_tools",
                 "approval_timeout", "supports", "raw")

    def __init__(self, row):
        self.id = row.get("id") or ""
        if not self.id:
            raise ValueError("agents.toml: a [[backend]] row needs an id")
        self.label = row.get("label", self.id)
        self.command = row.get("command", self.id)
        self.transport = row.get("transport", "oneshot")
        if self.transport not in TRANSPORTS:
            raise ValueError(
                "backend %r: unknown transport %r (%s)"
                % (self.id, self.transport, "|".join(TRANSPORTS))
            )
        self.modes = list(row.get("modes", []))
        self.default_mode = row.get("default_mode", self.modes[0] if self.modes else "")
        self.mode_flag = row.get("mode_flag", "")
        self.mode_blurbs = dict(row.get("mode_blurbs", {}) or {})
        # Model picker entries: `models` is a plain id list; optional
        # `[backend.model_labels]` / `[backend.model_hints]` tables dress the
        # ids up for the UI (tomlio has no inline tables). An id with no label
        # labels itself. Empty list = the picker offers only "(backend
        # default)" and a custom-id box.
        _labels = dict(row.get("model_labels", {}) or {})
        _hints = dict(row.get("model_hints", {}) or {})
        self.models = [
            {"id": str(m).strip(), "label": _labels.get(m, str(m).strip()),
             "hint": _hints.get(m, "")}
            for m in row.get("models", []) if str(m).strip()
        ]
        # Tools the PreToolUse approval hook gates behind a human in the chat.
        # Empty = no gate, no settings file, the CLI runs exactly as before.
        # Only meaningful on a stream_json backend that honours --settings.
        self.gated_tools = [str(t).strip() for t in row.get("gated_tools", [])
                            if str(t).strip()]
        self.approval_timeout = int(row.get("approval_timeout", 300) or 300)
        self.raw = row

    # -- capability flags the UI reads instead of hardcoding CLI names -------
    @property
    def is_api(self):
        return self.transport in API_TRANSPORTS

    @property
    def steerable(self):
        # An API turn is a sequence of HTTP requests with no open channel to
        # write down, so a message can only be queued for the next turn.
        return self.transport == "stream_json"

    @property
    def resumable(self):
        return self.transport in ("stream_json", "resume", "openai_api")

    @property
    def streaming(self):
        return self.transport in ("stream_json", "resume", "openai_api")

    @property
    def api_key_env(self):
        return self.raw.get("api_key_env") or "OPENROUTER_API_KEY"

    @property
    def installed(self):
        """Whether this backend can actually be used right now.

        For an API backend that is "a key is set", not "a command is on PATH".
        Asking PATH about a backend with no executable reports it as missing
        and the UI greys out something that would have worked.
        """
        if self.is_api:
            return bool(os.environ.get(self.api_key_env, "").strip())
        return self.resolved_command is not None

    @property
    def unavailable_reason(self):
        if self.installed:
            return ""
        if self.is_api:
            return ("%s is not set in this environment. Export it in the shell "
                    "that starts the console." % self.api_key_env)
        return "%s is not on PATH (command: %s)" % (self.label, self.command)

    @property
    def resolved_command(self):
        """The command's full path, or None.

        Spawning must use this rather than the bare name. On Windows a CLI is
        often a `.CMD`/`.BAT` shim (cursor-agent is), and `CreateProcess` —
        which is what Popen uses without a shell — does NOT consult PATHEXT the
        way a shell does. So `Popen(["cursor-agent", ...])` raises
        FileNotFoundError for a CLI that is plainly installed and that
        `shutil.which` finds. Resolving here keeps argv free of shell quoting
        while still pointing at a real file.
        """
        if os.path.isabs(self.command) or os.sep in self.command or "/" in self.command:
            # An explicit path (e.g. "./scripts/my-runner.sh") is used as given.
            return self.command if os.path.exists(self.command) else shutil.which(self.command)
        return shutil.which(self.command)

    def _exe(self):
        found = self.resolved_command
        if not found:
            raise FileNotFoundError(
                "%s is not on PATH (command: %s)" % (self.label, self.command))
        return found

    def describe(self):
        return {
            "id": self.id, "label": self.label, "command": self.command,
            "transport": self.transport,
            "steerable": self.steerable, "resumable": self.resumable,
            "streaming": self.streaming, "installed": self.installed,
            "modes": [{"id": m, "blurb": self.mode_blurbs.get(m, "")} for m in self.modes],
            "default_mode": self.default_mode,
            "models": self.models,
            # An API session gates in-process, so the hook-only restriction
            # that applies to a CLI backend does not apply to it.
            "approval_gate": bool(self.gated_tools) and (
                self.transport == "stream_json" or self.is_api),
            "prompt_prefix_style": self.raw.get("prompt_prefix_style", "slash"),
            "is_api": self.is_api,
            "unavailable_reason": self.unavailable_reason,
        }

    # -- argv builders -------------------------------------------------------
    def session_argv(self, *, mode="", model="", persona="", settings_path="", add_dirs=()):
        """The argv for a long-lived streaming session (`stream_json`)."""
        tmpl = self.raw.get("session_args")
        if not tmpl:
            raise ValueError("backend %r has no session_args" % self.id)
        argv = [self._exe()] + _expand(tmpl, {
            "mode": mode or self.default_mode,
            "model": model,
            "persona": persona,
            "settings": settings_path,
        })
        for d in add_dirs or ():
            for part in _expand(self.raw.get("add_dir_args", []), {"dir": d}):
                argv.append(part)
        return argv

    def turn_argv(self, prompt, *, mode="", model="", resume_id=""):
        """The argv for one turn of a `resume` backend, or a `oneshot` run."""
        key = "resume_args" if (resume_id and self.raw.get("resume_args")) else None
        if key is None:
            key = "turn_args" if self.raw.get("turn_args") else "oneshot_args"
        tmpl = self.raw.get(key)
        if not tmpl:
            raise ValueError("backend %r has no %s" % (self.id, key))
        return [self._exe()] + _expand(tmpl, {
            "prompt": prompt,
            "mode": mode or self.default_mode,
            "model": model,
            "resume_id": resume_id,
        })

    def compose_prompt(self, text, skill="", persona=""):
        """How this backend wants a skill/persona referenced.

        `slash`  -> "@persona /skill text"   (a CLI with slash commands)
        `inline` -> a sentence naming the skill file, for a CLI that has no
                    slash-command system — worst case it just reads the file,
                    which is literally what a skill is.
        `none`   -> the text, untouched.
        """
        style = self.raw.get("prompt_prefix_style", "slash")
        text = (text or "").strip()
        if style == "none" or (not skill and not persona):
            return text
        if style == "inline":
            bits = []
            if skill:
                bits.append(
                    "Follow the instructions in .claude/skills/%s/SKILL.md." % skill)
            if persona:
                bits.append("Act as the %s role in .claude/agents/%s.md." % (persona, persona))
            bits.append(text)
            return "\n\n".join(b for b in bits if b)
        parts = []
        if persona:
            parts.append("@" + persona)
        if skill:
            parts.append("/" + skill)
        prefix = " ".join(parts)
        return (prefix + " " + text).strip() if prefix else text


def registry(repo_root, force=False):
    """id -> Backend for every configured row."""
    rows = load_config(repo_root, force=force).get("backend", [])
    out = {}
    for row in rows:
        if not row.get("enabled", True):
            continue
        b = Backend(row)
        out[b.id] = b
    return out


def get(repo_root, backend_id):
    reg = registry(repo_root)
    if backend_id not in reg:
        raise ValueError("unknown backend %r; configured: %s"
                         % (backend_id, ", ".join(sorted(reg)) or "(none)"))
    return reg[backend_id]
