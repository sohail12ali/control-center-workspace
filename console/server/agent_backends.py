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
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import boards as boards_mod
from . import prompt_tokens
from . import tomlio

CONFIG_REL = os.path.join("console", "config", "agents.toml")

#: The transports a backend row may declare.
#:
#: `openai_api` is the odd one out and deliberately so: the other three spawn
#: somebody else's agent and inherit its tools and permission model, while this
#: one has no process at all — the console runs the loop, holding its own verbs
#: as tools and its own approval gate. See `agent_api_session`.
TRANSPORTS = ("stream_json", "resume", "oneshot", "openai_api")

#: Transports with no executable. Asking PATH about these reports every one as
#: missing, so availability is answered by `auth` below instead.
API_TRANSPORTS = ("openai_api",)

#: How an API backend proves it is usable. This exists because "is it usable"
#: has three genuinely different answers and one of them was previously
#: unreachable:
#:
#:   key     a credential must be present in the environment (OpenRouter,
#:           OpenAI, Groq). Availability is "the variable is set" — cheap,
#:           local, and no network call.
#:   none    no credential at all (Ollama, LM Studio, llama.cpp). The only
#:           honest question is whether the server is RUNNING, which needs a
#:           probe. Under the old model these were permanently unavailable:
#:           `installed` asked whether a key was set, and there is no key.
#:   probe   a credential is optional but the endpoint must answer (a shared
#:           vLLM box behind a gateway).
AUTH_MODES = ("key", "none", "probe")

#: How long a reachability probe is trusted. `/api/agents/backends` is polled
#: by the open tab, and a blocking socket call per provider per poll would
#: stall it. Short enough that starting `ollama serve` shows up while you are
#: still looking at the screen.
PROBE_TTL = 10.0
PROBE_TIMEOUT = 1.5

#: Budgets for the loop the console owns (`openai_api` only). They live here,
#: with the rest of a backend's configuration, rather than as constants in
#: `agent_api_session` — because they are not one policy for every provider.
#:
#: A flat pair of numbers was wrong in both directions at once: 120 messages
#: overflows a 4k local model long before the count is reached, and 25 rounds
#: is timid for a 200k hosted one. A row that says nothing still gets these,
#: so nothing changes for a backend nobody has tuned.
DEFAULT_TOOL_ROUNDS = 25
DEFAULT_HISTORY_MESSAGES = 120

_cache = {}
_probe_cache = {}
_probe_lock = threading.Lock()


def _probe(url, timeout=PROBE_TIMEOUT, opener=None):
    """Is something answering at `url`? Returns (ok, reason).

    Never raises. A provider that is down must make its own card say so, not
    take the page down with it — the same contract `notify` works to.

    The reason is the entire value here. "Not available" sends someone reading
    source; "connection refused — the server is not running" does not.
    """
    now = time.time()
    with _probe_lock:
        hit = _probe_cache.get(url)
        if hit and now - hit[0] < PROBE_TTL:
            return hit[1], hit[2]

    ok, reason = False, ""
    try:
        request = urllib.request.Request(url, method="GET")
        with (opener or urllib.request.urlopen)(request, timeout=timeout):
            ok = True
    except urllib.error.HTTPError:
        # Any HTTP status at all means a server answered, which is the whole
        # question. 401/404 is a live endpoint with an opinion, not a dead one.
        ok = True
    except urllib.error.URLError as exc:
        ok = False
        reason = _url_error_reason(exc, url)
    except Exception as exc:  # noqa: BLE001
        ok = False
        reason = "%s while reaching %s" % (type(exc).__name__, url)

    with _probe_lock:
        _probe_cache[url] = (now, ok, reason)
    return ok, reason


def _url_error_reason(exc, url):
    """Separate "nothing is listening there" from "that host does not exist".

    They need different fixes — start the server, versus correct the base_url —
    and one message for both sends half the readers the wrong way.

    Classified by EXCEPTION TYPE, not by errno or by matching English in the
    message. Both alternatives were tried and both are wrong here: errno for
    "connection refused" is 61/111/10061 depending on platform, and on Windows
    a closed loopback port does not raise ConnectionRefusedError at all — it
    raises TimeoutError with errno None. Verified against 127.0.0.1:11434 with
    Ollama installed but not serving.

    Which is why a timeout to a LOOPBACK address is reported as "not running"
    rather than "slow": a local port that is genuinely listening answers in
    microseconds, so a 1.5s silence from localhost is a dead server every time.
    A remote host is a different matter and keeps the honest "did not answer".
    """
    inner = getattr(exc, "reason", exc)
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc or url
    is_loopback = (parts.hostname or "") in ("localhost", "127.0.0.1", "::1")

    if isinstance(inner, socket.gaierror):
        return "the host %s does not resolve — check base_url" % host
    if isinstance(inner, ConnectionRefusedError):
        return "nothing is listening on %s — is the server running?" % host
    if isinstance(inner, (socket.timeout, TimeoutError)):
        if is_loopback:
            return "nothing is listening on %s — is the server running?" % host
        return "%s did not answer within %gs" % (host, PROBE_TIMEOUT)
    return "could not reach %s (%s)" % (host, inner)


def forget_probes():
    """Drop every cached probe. For tests, and for a config reload."""
    with _probe_lock:
        _probe_cache.clear()


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
                 "approval_timeout", "supports", "auth", "raw")

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
        # How this backend proves it is usable. Only meaningful for a transport
        # with no executable; a CLI's answer is always "is it on PATH".
        self.auth = row.get("auth") or ("key" if self.transport in API_TRANSPORTS else "")
        if self.transport in API_TRANSPORTS:
            if self.auth not in AUTH_MODES:
                raise ValueError(
                    "backend %r: unknown auth %r (%s)"
                    % (self.id, self.auth, "|".join(AUTH_MODES)))
            # Caught at load, next to the ticket that names the row, rather
            # than as a mystery 401 on the first turn. The old code defaulted a
            # missing api_key_env to OPENROUTER_API_KEY, so a misconfigured
            # OpenAI row silently authenticated with the wrong provider's key.
            if self.auth == "key" and not row.get("api_key_env"):
                raise ValueError(
                    "backend %r: auth = \"key\" needs api_key_env (or set "
                    "auth = \"none\" for a local server that takes no key)"
                    % self.id)
            if not row.get("base_url"):
                raise ValueError("backend %r: transport %r needs a base_url"
                                 % (self.id, self.transport))
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
        # Refused at load, beside the row that is wrong, rather than as a loop
        # that ends instantly or never — both of which look like a hang.
        for field in ("max_tool_rounds", "max_history_messages"):
            if row.get(field) is not None and int(row[field]) < 1:
                raise ValueError("backend %r: %s must be at least 1"
                                 % (self.id, field))
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
        """The env var holding this provider's key, or "" for a keyless one.

        No default. A fallback of "OPENROUTER_API_KEY" meant every row that
        forgot the field quietly authenticated against OpenRouter's key —
        wrong provider, confusing 401, and a key sent somewhere it was not
        meant to go. `__init__` now refuses such a row instead.
        """
        return self.raw.get("api_key_env") or ""

    @property
    def base_url(self):
        return (self.raw.get("base_url") or "").rstrip("/")

    @property
    def models_url(self):
        """Where to ask for this provider's model list.

        Defaults to the OpenAI-compatible `/models`, which every provider in
        this file serves. Overridable because a provider that speaks the chat
        shape does not always serve the catalogue at the same place.
        """
        explicit = (self.raw.get("models_url") or "").strip()
        return explicit or (self.base_url + "/models" if self.base_url else "")

    @property
    def is_local(self):
        """A provider running on this machine. Not cosmetic: local means free,
        private, and offline-capable — the three things a person actually
        wants to know before picking one."""
        if not self.is_api:
            return False
        host = urllib.parse.urlsplit(self.base_url).hostname or ""
        return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")

    @property
    def has_key(self):
        return bool(self.api_key_env and os.environ.get(self.api_key_env, "").strip())

    @property
    def max_tool_rounds(self):
        """Tool-call rounds allowed in one turn before the loop stops itself.

        A loop that can call tools can call them forever, and every round costs
        money. This is the cap; hitting it ends the turn with a notice saying so,
        because "stopped early" and "finished" look identical in a transcript.
        """
        return int(self.raw.get("max_tool_rounds") or DEFAULT_TOOL_ROUNDS)

    @property
    def max_history_messages(self):
        """Conversation messages kept before the oldest are dropped.

        A blunt guard against outgrowing the model's context. Real compaction is
        a later problem; dropping the oldest is at least predictable, and the
        system message is never among them.
        """
        return int(self.raw.get("max_history_messages") or DEFAULT_HISTORY_MESSAGES)

    @property
    def installed(self):
        """Whether this backend can actually be used right now.

        Three different questions behind one name, because the answer depends
        on what the backend IS:

          a CLI          is the command on PATH
          auth = "key"   is the credential in the environment
          auth = "none"  is the server answering  (the probe)
          auth = "probe" is the server answering, key optional

        Asking any one of those about the wrong kind of backend greys out
        something that would have worked. That is exactly what happened to
        keyless local providers before: they were asked for a key they do not
        have, so they were never available.
        """
        if not self.is_api:
            return self.resolved_command is not None
        if self.auth == "key":
            return self.has_key
        ok, _reason = _probe(self.models_url or self.base_url)
        return ok

    @property
    def unavailable_reason(self):
        if self.installed:
            return ""
        if not self.is_api:
            return "%s is not on PATH (command: %s)" % (self.label, self.command)
        if self.auth == "key":
            return ("%s is not set in this environment. Put it in the "
                    "workspace's .env or export it in the shell that starts "
                    "the console." % self.api_key_env)
        _ok, reason = _probe(self.models_url or self.base_url)
        hint = self.raw.get("start_hint") or ""
        return (reason + (" " + hint if hint else "")) or (
            "%s is not answering." % (self.base_url or self.label))

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
            # The names themselves, so the composer can say WHICH tools will
            # stop and ask. Tool names are not secrets; the arguments they are
            # called with never travel with them.
            "gated_tools": list(self.gated_tools),
            "prompt_prefix_style": self.raw.get("prompt_prefix_style", "slash"),
            "is_api": self.is_api,
            "unavailable_reason": self.unavailable_reason,
            # Setup facts, for the composer's grouping and the Settings panel.
            # `key_env` is a variable NAME; the value is never sent anywhere.
            "auth": self.auth,
            "is_local": self.is_local,
            "base_url": self.base_url,
            "key_env": self.api_key_env,
            "has_key": self.has_key,
            "notes": self.raw.get("notes", "") or "",
            # The EFFECTIVE budgets, never the raw config: the UI shows what
            # the loop will actually enforce, so a row that sets nothing reads
            # the same as one that sets the default explicitly. Meaningless for
            # a CLI backend, whose loop belongs to someone else.
            "budgets": {"tool_rounds": self.max_tool_rounds,
                        "history_messages": self.max_history_messages}
                       if self.is_api else None,
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

    @property
    def prompt_prefix_style(self):
        return self.raw.get("prompt_prefix_style", "slash")

    def compose_prompt(self, text, skill="", persona="", repo_root=None):
        """How this backend wants a skill/persona/file referenced.

        `slash`  -> "@persona /skill text"   (a CLI with slash commands)
        `inline` -> a sentence naming the skill file, for a CLI that has no
                    slash-command system — worst case it just reads the file,
                    which is literally what a skill is.
        `none`   -> the text, plus any references named.

        Passing `repo_root` additionally resolves inline `/skill`, `@agent` and
        `#file` tokens typed in the message itself — see `prompt_tokens`. It is
        optional only so a caller with no workspace in hand still works; every
        real call site has one.
        """
        return prompt_tokens.compose(
            repo_root, text, self.prompt_prefix_style,
            skill=skill, persona=persona)[0]


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
    if backend_id in reg:
        return reg[backend_id]
    # "Unknown" and "switched off" need different fixes — add a row, versus
    # flip one field — and one message for both sent people looking for a
    # typo in a row that was sitting right there with `enabled = false`.
    known = {row.get("id") for row in load_config(repo_root).get("backend", [])}
    if backend_id in known:
        raise ValueError(
            "backend %r is configured but disabled. Set enabled = true on its "
            "[[backend]] row in %s." % (backend_id, CONFIG_REL))
    raise ValueError("unknown backend %r; enabled: %s"
                     % (backend_id, ", ".join(sorted(reg)) or "(none)"))
