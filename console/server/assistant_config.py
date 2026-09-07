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

from . import tomlio

CONFIG_REL = os.path.join("console", "config", "assistant.toml")
OVERRIDE_REL = os.path.join("console", ".cache", "assistant", "settings.json")

#: Preference order when no backend has been chosen. Local first, per the
#: locked "local-first default" decision in the desktop-assistant design —
#: a private model before a hosted one, every time, unless asked otherwise.
LOCAL_FIRST = ("ollama", "lm-studio", "claude", "openrouter", "cursor-agent")

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


def resolve_backend(repo_root, registry, requested=""):
    """Which backend a brand-new Assistant chat should use.

    Order: an explicit request, then the stored choice, then the first
    enabled+installed backend in `LOCAL_FIRST`, then whatever else is
    installed. Raises only when nothing at all is usable, which is a real
    setup problem and worth saying out loud.
    """
    installed = [bid for bid, b in registry.items() if b.installed]
    for candidate in (requested, settings(repo_root).get("backend", "")):
        if candidate and candidate in installed:
            return candidate
    for candidate in LOCAL_FIRST:
        if candidate in installed:
            return candidate
    if installed:
        return installed[0]
    raise ValueError("no enabled+installed backend is configured — set one up "
                     "in console/config/agents.toml first")


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

    backend = clean.get("backend")
    if backend and installed_backends and backend not in installed_backends:
        raise ValueError(
            "backend %r is not enabled and installed — available: %s"
            % (backend, ", ".join(sorted(installed_backends)) or "none"))

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
