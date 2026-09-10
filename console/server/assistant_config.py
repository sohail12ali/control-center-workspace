"""T-004 C7 (service half): the Assistant's settings.

Two layers, deliberately:

    console/config/assistant.toml        committed defaults — what this
                                         workspace ships with.
    console/.cache/assistant/settings.json   this machine's choices, written
                                         by `POST /api/assistant/settings`.

## Why the runtime choice is not written back into the committed file

`plugins.toml`'s own header draws the line this follows: a committed config
file "is committed and applies to everyone who pulls the checkout," while a
per-user toggle is not. Picking a backend on this laptop is the second kind,
so persisting it into `console/config/assistant.toml` would put a personal
choice into everyone's diff and make `git status` dirty every time someone
changed their mind. Overrides live in the gitignored cache instead, and the
committed file keeps its job: stating the defaults.

The native shell (T-006) reads the merged view through
`GET /api/assistant/settings`, so it never needs to know there are two files.

## Why the backend default is empty

An id hardcoded here would be wrong on any machine that doesn't have that CLI
installed. Empty means "resolve it at use time" — first enabled+installed
backend in `LOCAL_FIRST` order — so the default is correct on a laptop with
only Ollama and on one with only Claude, without either being named here.
"""

import json
import os

from . import model_catalog
from . import tomlio

CONFIG_REL = os.path.join("console", "config", "assistant.toml")
OVERRIDE_REL = os.path.join("console", ".cache", "assistant", "settings.json")

#: Preference order when no backend has been chosen. Local first, per the
#: locked "local-first default" decision in the desktop-assistant design —
#: a private model before a hosted one, every time, unless asked otherwise.
#:
#: `openrouter` sits AHEAD of the CLIs, which it did not use to. That ordering
#: was the whole reason a laptop with no usable local model ended up holding
#: its conversations through the Claude Code CLI: a talk model answering
#: "what's open?" was paying for a coding agent's whole harness, measured at
#: 2-300 seconds a turn in `knowledge-center/telemetry/`.
LOCAL_FIRST = ("ollama", "lm-studio", "openrouter", "claude", "cursor-agent")

#: Preference order for the WORK role — code changes, builds, test runs.
#:
#: Local first here too, which it was not: `work_backend` had no chain at all.
#: It was a single id that had to be set by hand, and `delegate` refused
#: outright when it was empty, so in practice it was pinned to whichever CLI
#: someone had picked once. Same order as talking, for the same reason — a
#: model on this machine is free, private and offline — and the difference
#: between the two roles is not the order but the PREFLIGHT: see `work_ready`.
WORK_FIRST = ("ollama", "lm-studio", "openrouter", "claude", "cursor-agent")

#: Smallest context a model may have and still be sent real work.
#:
#: A work turn holds a file, an edit to it, a command's output and often a test
#: log. 16k is the point below which that stops fitting and the model starts
#: forgetting the beginning of its own task — which reads as a model that
#: cannot follow instructions rather than one that ran out of room.
#:
#: Only enforced when the server actually reports a context length. Silence
#: gets the benefit of the doubt, the same way tool support does.
WORK_MIN_CONTEXT = 16_384

#: Every key the Assistant reads, with the value used when neither the
#: committed file nor the override supplies one. This dict IS the schema:
#: a key absent from here is rejected by `update`, so a typo in a POST body
#: fails loudly instead of being stored and silently ignored forever.
DEFAULTS = {
    "backend": "",              # "" = resolve local-first at use time
    "model": "",                # "" = the backend's own default
    "mode": "default",          # not "plan" — gated writes must be reachable
    "vision_models": [],        # globs/ids that can see a screenshot (T-007)
    "session_idle_minutes": 240,
    "speak": True,              # T-006 honours this; stored here from T-004
    "reply_chars": 400,         # spoken-form cap
    "ticket_prefix": "T-",

    # -- two models, two jobs (T-014) ----------------------------------------
    # `backend`/`model` above are the TALK pair: conversation, status, ticket
    # lookups, memory. On a local server that is a 1.4-second answer.
    #
    # These are where real work goes — code changes, builds, test runs. The
    # talk model hands a task over with `console_delegate`; the work model is
    # what picks it up. Empty means there is nowhere to delegate to, and the
    # tool says so rather than quietly running the task on the talk model.
    "work_backend": "",
    "work_model": "",

    # Which backends may be chosen, in order, when a role's backend is not
    # pinned. Comma-separated ids; empty means the built-in order
    # (`LOCAL_FIRST` / `WORK_FIRST`, both local-first).
    #
    # This is how you say "never a CLI" without a second setting to mean it:
    # `backend_chain = "ollama,lm-studio"` and nothing else is reachable, so a
    # role with no local model available FAILS and says what it tried, rather
    # than quietly falling through to a coding CLI. Which of those two you
    # want is a real preference and not something a default can settle — the
    # default keeps working, this makes it strict.
    "backend_chain": "",

    # -- how a reply sounds (T-013) -------------------------------------------
    # Which neural voice reads replies, by name, matching a file in
    # desktop/tts (`en_US-amy-medium`). Blank means "whichever is installed";
    # with no piper at all the OS synthesiser speaks instead and says so.
    "speak_voice": "",
    # Speaking speed as a percentage of the voice's natural pace. A percentage
    # rather than piper's own `length_scale`, which runs the other way and
    # would put "0.8 is faster" in a settings panel.
    "speak_rate_percent": 100,

    # -- the tray (T-009) ----------------------------------------------------
    # What ONE left-click on the tray icon does. "listen" is state-aware: talk
    # when idle, send the take you are in the middle of, stop a reply being
    # read aloud, and show the window when only a human can help (a permission
    # card, or a turn already in flight). "show" restores the plain
    # open-the-window behaviour for anyone who expects a tray click to do that,
    # and "hands_free" makes the icon an arm/disarm switch.
    "tray_click_action": "listen",

    # -- listening and transcription (T-010) ---------------------------------
    # A take ends when you stop talking; these bound the two ways that can go
    # wrong. `listen_max_seconds` is the backstop for a detector that never
    # sees silence — it was 20s and cost that on every take in a noisy room
    # before the detector learned to calibrate. `listen_silence_ms` is how
    # long a pause has to be before it counts as "finished", so someone who
    # thinks mid-sentence is not cut off.
    "listen_max_seconds": 12,
    "listen_silence_ms": 700,
    # Which whisper.cpp model to load, by name. `base.en` is accurate enough
    # for ticket ids; `tiny.en` is several times faster and noticeably worse
    # at exactly those. Named rather than inferred, so dropping a second model
    # into desktop/stt does not silently change what transcribes your voice.
    "stt_model": "base.en",

    # -- hands-free (T-008) --------------------------------------------------
    # An always-on microphone is a different proposition from push-to-talk, so
    # every one of these defaults to the cautious answer.
    #
    # `hands_free_require_wake` is the important one. With it on, audio is
    # transcribed LOCALLY and the transcript is thrown away unless it is
    # addressed to the assistant — so leaving the mic on does not mean sending
    # the room to a model. Turning it off means every utterance becomes a turn.
    "hands_free_require_wake": True,
    "hands_free_wake_word": "console",
    # Whether to keep listening while a reply is being read aloud. Off by
    # default because on speakers the assistant hears itself and answers its
    # own voice. On headphones there is no echo, and turning this on is what
    # makes barge-in work by voice rather than by hotkey.
    "hands_free_listen_while_speaking": False,
    # A cap, so an always-on mic left running by accident stops on its own.
    "hands_free_max_minutes": 30,
}

#: The three things a tray click can mean. Validated rather than free text:
#: an unrecognised value would leave the icon doing nothing, with the setting
#: looking as if it had been accepted.
TRAY_CLICK_ACTIONS = ("listen", "show", "hands_free")

#: Keys a POST may change. `vision_models` is excluded on purpose: it is a
#: capability statement about models, which belongs in the committed file
#: where it can be reviewed, not in a per-machine override.
WRITABLE = frozenset({
    "backend", "model", "mode", "session_idle_minutes", "speak",
    "reply_chars", "ticket_prefix", "tray_click_action",
    "listen_max_seconds", "listen_silence_ms", "stt_model",
    "speak_voice", "speak_rate_percent",
    "work_backend", "work_model", "backend_chain",
    "hands_free_require_wake", "hands_free_wake_word",
    "hands_free_listen_while_speaking", "hands_free_max_minutes",
})


def _committed(repo_root):
    path = os.path.join(repo_root, CONFIG_REL)
    if not os.path.isfile(path):
        return {}
    try:
        return tomlio.load(path).get("assistant", {}) or {}
    except (OSError, ValueError):
        # A malformed committed file must not take the Assistant down; the
        # defaults below are always a working configuration.
        return {}


def _overrides(repo_root):
    path = os.path.join(repo_root, OVERRIDE_REL)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def settings(repo_root):
    """The merged view: defaults <- committed file <- this machine."""
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in _committed(repo_root).items() if k in DEFAULTS})
    merged.update({k: v for k, v in _overrides(repo_root).items() if k in DEFAULTS})
    return merged


def talk_ready(repo_root, backend):
    """Can this backend actually hold a conversation? Returns (ok, reason).

    `installed` is not enough, and assuming it was is what made the local path
    look broken. For an API row `installed` means only "something answered at
    that address", and all three of these got past it before failing mid-turn,
    with the failure showing up as a dead assistant rather than as a bad pick:

      * `qwen3:8b` selected on a box with 4.7 GiB free — "model requires more
        system memory (5.5 GiB) than is available"
      * `deepseek-coder` selected and then "does not support tools", so every
        verb the Assistant has was unreachable
      * a reachable LM Studio with nothing loaded, where picking a model means
        waiting out a load

    So a local runtime is asked the two questions that decide it: is a model
    resident, and does it claim tool training. Both come from the server's own
    answer via `model_catalog`, and a provider that reports neither is given
    the benefit of the doubt — `capabilities` is documented as a hint, and
    `muse-glimmer` calls tools correctly while declaring it cannot.

    Only a keyless API row is asked — `auth = "none"` is exactly the class of
    "a model runtime you run yourself", and it is the right test rather than
    `is_local`: an LM Studio reached over the LAN is still a box that swaps
    models one at a time, and `is_local` calls it hosted because the host is
    not 127.0.0.1. A CLI has tools by construction, and a keyed provider has
    no residency to report, so both skip these two requests entirely.
    """
    if not backend.installed:
        return False, backend.unavailable_reason
    if backend.auth != "none":
        return True, ""

    resident = model_catalog.loaded(repo_root, backend.id)
    if resident is not None and not resident:
        return False, ("%s is running but has no model loaded — load one, or "
                       "pull one with `ollama pull`" % backend.label)

    caps = model_catalog.capabilities(repo_root, backend.id)
    if caps and resident:
        # Only judge what is ACTUALLY loaded: a catalogue full of tool-capable
        # models is no help when the resident one is not among them.
        tool_capable = [m for m in resident
                        if caps.get(m, {}).get("tool_use", True)]
        if not tool_capable:
            return False, ("%s has %s loaded, which does not support tool "
                           "calling — the Assistant's verbs would all fail"
                           % (backend.label, ", ".join(sorted(resident))))
    return True, ""


def work_ready(repo_root, backend):
    """Can this backend be trusted with real WORK? Returns (ok, reason).

    Everything `talk_ready` asks, plus the two things that only matter once a
    model is editing files and running commands:

    **Tools are not optional.** A model that cannot call one can still hold a
    conversation; it cannot change a line of code. For talking, a server that
    reports nothing about tool support gets the benefit of the doubt — here it
    still does, because Ollama reports no capabilities at all and refusing on
    silence would rule it out permanently. What changes is that a model
    explicitly declaring no tool support is refused for work even where
    talking would have tolerated it.

    **Room to work.** `WORK_MIN_CONTEXT`. A work turn carries a file, an edit,
    a command's output and often a test log; below about 16k that stops
    fitting, and a model that has forgotten the start of its own task looks
    like one that will not follow instructions.

    Neither check applies to a CLI or a keyed provider — a coding CLI has
    tools by construction, and a hosted provider reports no residency.
    """
    ok, why = talk_ready(repo_root, backend)
    if not ok:
        return False, why
    if backend.auth != "none":
        return True, ""

    resident = model_catalog.loaded(repo_root, backend.id)
    caps = model_catalog.capabilities(repo_root, backend.id)
    if not resident or not caps:
        # Nothing reported. `talk_ready` already established the server is up
        # and has something loaded; anything more specific would be a guess.
        return True, ""

    for model in sorted(resident):
        fact = caps.get(model)
        if fact is None:
            return True, ""  # loaded but undescribed — give it the benefit
        if not fact.get("tool_use", True):
            continue
        context = fact.get("context")
        if isinstance(context, int) and context < WORK_MIN_CONTEXT:
            continue
        return True, ""

    return False, (
        "%s has %s loaded, which is not up to being sent work — it needs tool "
        "calling and at least %dk of context. It is fine for talking."
        % (backend.label, ", ".join(sorted(resident)),
           WORK_MIN_CONTEXT // 1024))


def _chain(repo_root, default_order):
    """The ordered candidate list for a role.

    `backend_chain` in settings overrides the built-in order when set, which
    is how "never a CLI" is expressed: name only the backends you will accept
    and the rest are unreachable, so a role with nothing available fails and
    says what it tried instead of falling through to something you did not
    want. Unknown ids are kept rather than dropped — they simply never match a
    registry entry, and `resolve` reports them as such.
    """
    raw = (settings(repo_root).get("backend_chain") or "").strip()
    if not raw:
        return list(default_order)
    named = [part.strip() for part in raw.split(",") if part.strip()]
    return named or list(default_order)


def resolve_work_backend(repo_root, registry, requested="", report=None):
    """Which backend a delegated task should run on.

    Same shape as `resolve_backend` and deliberately so, because `work_backend`
    used to have no chain at all: it was one id that had to be set by hand, and
    `delegate` refused outright when it was empty. In practice that pinned it
    to whichever CLI was chosen once — which is how a machine with two local
    runtimes installed sent every task to a hosted coding agent.

    The order is local-first (`WORK_FIRST`), and the bar is `work_ready`.
    """
    rejected = report if report is not None else []
    stored = settings(repo_root).get("work_backend", "")

    def ready(bid):
        backend = registry.get(bid)
        if backend is None:
            rejected.append((bid, "not a backend in console/config/agents.toml"))
            return False
        try:
            ok, why = work_ready(repo_root, backend)
        except Exception as exc:  # noqa: BLE001
            # A malformed row, or a provider that raised while being asked
            # about itself. Skip it and say so — one bad backend must not stop
            # the chain reaching the next, which is what happened when this
            # was first written: an agents.toml row missing `session_args`
            # aborted resolution instead of being passed over.
            rejected.append((bid, "%s: %s" % (type(exc).__name__, exc)))
            return False
        if not ok:
            rejected.append((bid, why))
        return ok

    for candidate in (requested, stored):
        if candidate and ready(candidate):
            return candidate
    seen = set()
    for candidate in _chain(repo_root, WORK_FIRST):
        if candidate in seen:
            continue
        seen.add(candidate)
        if ready(candidate):
            return candidate
    raise ValueError(
        "no backend is ready to be sent work. Tried: %s. Load a tool-capable "
        "model in a local runtime, or pin one in Settings > Assistant (Work)."
        % ("; ".join("%s (%s)" % (b, why) for b, why in rejected) or "nothing"))


def resolve_backend(repo_root, registry, requested="", report=None):
    """Which backend a brand-new Assistant chat should use.

    Order: an explicit request, then the stored choice, then the first backend
    in `LOCAL_FIRST` that is ready to talk, then anything else that is.
    Raises only when nothing at all is usable, which is a real setup problem
    and worth saying out loud.

    Two things this deliberately does NOT do any more:

    **It does not ask every backend whether it is installed.** It used to
    build that list up front, which meant a stored choice of `claude` — one
    `shutil.which` away — still paid a 1.5s network probe for every API row,
    including a LAN box that was switched off. That is the ~3s stall the tray
    was measured hanging on, because `GET /api/assistant/settings` came
    through here. Candidates are now asked one at a time, in order, and the
    common case answers before any socket is opened.

    **It does not treat "reachable" as "usable".** See `talk_ready`.

    `report` is an optional list; every rejected candidate appends
    `(id, reason)` to it. The caller surfaces those, because "why am I on this
    backend" is the question a silent fallback makes unanswerable.
    """
    rejected = report if report is not None else []

    def ready(bid):
        backend = registry.get(bid)
        if backend is None:
            return False
        try:
            ok, why = talk_ready(repo_root, backend)
        except Exception as exc:  # noqa: BLE001
            # Skipped, not fatal — see `resolve_work_backend.ready`.
            rejected.append((bid, "%s: %s" % (type(exc).__name__, exc)))
            return False
        if not ok:
            rejected.append((bid, why))
        return ok

    for candidate in (requested, settings(repo_root).get("backend", "")):
        if candidate and ready(candidate):
            return candidate
    seen = set()
    # `backend_chain` when set, else the built-in order plus anything else the
    # registry has. The trailing sweep is deliberate for TALKING: a machine
    # with only some third CLI configured should still be able to hold a
    # conversation. It is skipped once a chain is named, because naming one is
    # how you say "these and nothing else".
    named = _chain(repo_root, LOCAL_FIRST)
    order = named if (settings(repo_root).get("backend_chain") or "").strip() \
        else named + sorted(registry)
    for candidate in order:
        if candidate in seen:
            continue
        seen.add(candidate)
        if ready(candidate):
            return candidate
    raise ValueError(
        "no backend can hold a conversation right now. Tried: %s. Set one up "
        "in console/config/agents.toml, or fix one of these."
        % ("; ".join("%s (%s)" % (b, why) for b, why in rejected) or "nothing"))


def _coerce(key, value):
    """Match the default's type, or raise ValueError naming the key."""
    want = type(DEFAULTS[key])
    if want is bool:
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("true", "1", "yes", "on"):
            return True
        if str(value).lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError("%s must be true or false" % key)
    if want is int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError("%s must be a whole number" % key) from None
    return str(value)


def update(repo_root, patch, installed_backends=()):
    """Validate and persist a settings patch. Returns the merged view.

    Nothing is written unless every key in `patch` is valid, so a request
    that is half-wrong leaves the stored settings exactly as they were —
    a partially-applied settings write is worse than a rejected one.
    """
    if not isinstance(patch, dict) or not patch:
        raise ValueError("no settings given")

    unknown = sorted(set(patch) - WRITABLE)
    if unknown:
        raise ValueError("not a writable setting: %s" % ", ".join(unknown))

    clean = {}
    for key, value in patch.items():
        clean[key] = _coerce(key, value)

    for key in ("backend", "work_backend"):
        chosen = clean.get(key)
        if chosen and installed_backends and chosen not in installed_backends:
            raise ValueError(
                "%s %r is not enabled and installed — available: %s"
                % (key, chosen, ", ".join(sorted(installed_backends)) or "none"))

    if "session_idle_minutes" in clean and clean["session_idle_minutes"] < 1:
        raise ValueError("session_idle_minutes must be at least 1")
    if "reply_chars" in clean and clean["reply_chars"] < 1:
        raise ValueError("reply_chars must be at least 1")
    if "tray_click_action" in clean and clean["tray_click_action"] not in TRAY_CLICK_ACTIONS:
        raise ValueError("tray_click_action must be one of: %s"
                         % ", ".join(TRAY_CLICK_ACTIONS))
    if "listen_max_seconds" in clean and not 2 <= clean["listen_max_seconds"] <= 120:
        raise ValueError("listen_max_seconds must be between 2 and 120")
    if "listen_silence_ms" in clean and not 200 <= clean["listen_silence_ms"] <= 5000:
        # Below 200ms a normal pause between words ends the take; above five
        # seconds you are waiting for the backstop instead of the detector.
        raise ValueError("listen_silence_ms must be between 200 and 5000")
    if "speak_rate_percent" in clean and not 50 <= clean["speak_rate_percent"] <= 200:
        # Outside this the voice is either unintelligible or comic, and both
        # read as "broken" rather than "you set it that way".
        raise ValueError("speak_rate_percent must be between 50 and 200")
    if "speak_voice" in clean:
        name = clean["speak_voice"].strip()
        if name and ("/" in name or "\\" in name or ".." in name):
            # It becomes a filename in desktop/tts.
            raise ValueError("speak_voice must be a voice name like en_US-amy-medium")
        clean["speak_voice"] = name
    if "stt_model" in clean:
        name = clean["stt_model"].strip().lstrip("-")
        if not name or "/" in name or "\\" in name or ".." in name:
            # It becomes a filename (`ggml-{name}.bin`), so it must not be a
            # path — this is the only place that can stop it being one.
            raise ValueError("stt_model must be a model name like base.en")
        clean["stt_model"] = name
    if "hands_free_max_minutes" in clean and clean["hands_free_max_minutes"] < 1:
        raise ValueError("hands_free_max_minutes must be at least 1")
    if "hands_free_wake_word" in clean:
        word = clean["hands_free_wake_word"].strip()
        # A blank or one-letter wake word would match almost anything, which
        # defeats the point of requiring one.
        if len(word) < 2:
            raise ValueError("hands_free_wake_word needs at least two characters")
        clean["hands_free_wake_word"] = word

    path = os.path.join(repo_root, OVERRIDE_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stored = _overrides(repo_root)
    stored.update(clean)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(stored, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)
    return settings(repo_root)
