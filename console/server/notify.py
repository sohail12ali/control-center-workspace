"""Push a message to a phone. Currently Telegram; the seam is one function.

## Why this exists at all

A gated tool call parks and denies after 300 seconds of silence. Sitting in
front of the board that is a feature. Away from it, it means **every remote run
stalls at its first write and then fails**, and nothing tells you it happened.
So a notification channel is not a nicety bolted onto remote running — it is
the thing that makes remote running work at all.

## Fail soft, always

A notification that cannot be delivered must never block, delay, or fail the run
it is describing. Every send is best-effort with a short timeout, on the
caller's thread only long enough to fire and forget. If Telegram is down, the
approval still appears in the browser and still denies on the same timeout as
before — you are simply not told about it, which is exactly as bad as not having
this module, and no worse.

## Credentials

`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` come from the workspace's `.env`
(gitignored, loaded at startup) or from the shell, and are read per send. Never
stored on an object, never written to an event, a transcript, an audit record or
a log line — the same discipline as the OpenRouter key. A token in a URL is
still a token, so the failure path deliberately reports the status code and not
the URL it called.
"""

import datetime
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

from . import boards as boards_mod
from . import tomlio

DEFAULT_TIMEOUT = 8
TELEGRAM_API = "https://api.telegram.org"

#: Event kinds a channel may be asked to deliver. `approval` is the one that
#: matters; the rest are opt-in because a phone that buzzes for everything gets
#: muted, and then it buzzes for nothing.
KINDS = ("approval", "turn_end", "job_error")


#: Where the browser's preferences live. A generated, machine-local file, kept
#: apart from `console.toml` for the same reason `agents.toml` is never
#: rewritten: that file is mostly comments, and `tomlio.dumps` drops them.
PREFS_REL = os.path.join("console", "config", "notify-local.toml")

#: The ONLY keys the browser may write, and both can only ever make the bot
#: quieter. Nothing that could widen who reaches this machine is settable from
#: a page that has no authentication of its own — see `apply_prefs`.
WRITABLE = ("events", "quiet_from", "quiet_to")


def prefs_path(repo_root):
    return os.path.join(repo_root, PREFS_REL)


def load_prefs(repo_root):
    path = prefs_path(repo_root)
    if not os.path.isfile(path):
        return {}
    try:
        return tomlio.load(path).get("notify", {}) or {}
    except Exception:  # noqa: BLE001
        # A hand-mangled overlay must not take the console down; the committed
        # config is the source of truth and still works on its own.
        return {}


def apply_prefs(repo_root, incoming):
    """Persist the browser's choices. Returns the stored dict.

    **Narrowing only.** `events` is intersected with what `console.toml`
    already allows, so the page can switch a notification off but never on for
    a kind the checkout has not opted into — and can never touch `inbound`,
    the allowlist, or a credential.

    That asymmetry is the point. This console has no authentication, and since
    inbound landed a Telegram tap can approve `run_command`. Anything that
    widens who can reach this machine stays in the terminal, where there is at
    least a shell someone had to already have.
    """
    committed = boards_mod.load_console_config(repo_root).get("notify", {}) or {}
    allowed = [e for e in committed.get("events", ["approval"]) if e in KINDS]

    stored = load_prefs(repo_root)
    if "events" in incoming:
        asked = [e for e in (incoming.get("events") or []) if e in KINDS]
        stored["events"] = [e for e in asked if e in allowed]
    for key in ("quiet_from", "quiet_to"):
        if key in incoming:
            stored[key] = _clock(incoming.get(key))
    stored = {k: v for k, v in stored.items() if k in WRITABLE}
    tomlio.atomic_write(prefs_path(repo_root), {"notify": stored})
    return stored


def _clock(value):
    """`"23:30"` → `"23:30"`, anything else → `""` (meaning: no quiet hours)."""
    text = str(value or "").strip()
    if not text:
        return ""
    parts = text.split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return ""
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return ""
    return "%02d:%02d" % (hour, minute)


def in_quiet_hours(cfg, now=None):
    """True when the clock is inside the configured quiet window.

    Handles a window that wraps midnight (22:00 → 07:00), which is the usual
    shape — a naive `start <= now <= end` is false for every minute of it.
    """
    start, end = cfg.get("quiet_from") or "", cfg.get("quiet_to") or ""
    if not start or not end or start == end:
        return False
    stamp = (now or datetime.datetime.now()).strftime("%H:%M")
    if start < end:
        return start <= stamp < end
    return stamp >= start or stamp < end


def config(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("notify", {}) or {}
    local = load_prefs(repo_root)
    events = [e for e in cfg.get("events", ["approval"]) if e in KINDS]
    if "events" in local:
        # Intersected, not replaced: the overlay narrows what the committed
        # config permits and can never extend it.
        events = [e for e in events if e in (local.get("events") or [])]
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "channel": cfg.get("channel", "telegram"),
        "token_env": cfg.get("token_env") or "TELEGRAM_BOT_TOKEN",
        "chat_id_env": cfg.get("chat_id_env") or "TELEGRAM_CHAT_ID",
        "events": events,
        "quiet_from": _clock(local.get("quiet_from")),
        "quiet_to": _clock(local.get("quiet_to")),
        "timeout": int(cfg.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT),
    }


def status(repo_root):
    """What a person needs to diagnose 'why didn't my phone buzz?'.

    Deliberately reports whether each secret is *present*, never its value.
    """
    cfg = config(repo_root)
    token = os.environ.get(cfg["token_env"], "").strip()
    chat_id = os.environ.get(cfg["chat_id_env"], "").strip()
    reason = ""
    if not cfg["enabled"]:
        reason = "notifications are disabled in console.toml"
    elif not token:
        reason = "%s is not set" % cfg["token_env"]
    elif not chat_id:
        reason = "%s is not set" % cfg["chat_id_env"]
    else:
        # Set is not the same as workable. This one case can be proven wrong
        # without a network call, and it used to report ready: true while every
        # send failed with a 403 that named no cause.
        reason = misconfigured(repo_root)
    ready = bool(cfg["enabled"] and token and chat_id and not reason)
    return {"enabled": cfg["enabled"], "channel": cfg["channel"],
            "events": cfg["events"], "ready": ready, "reason": reason,
            "token_present": bool(token), "chat_id_present": bool(chat_id)}


def bot_id(token):
    """The bot's own numeric id — the public half of its token.

    A Telegram token is `<bot_id>:<secret>`. The id before the colon is not a
    credential: it is in every message the bot sends. Splitting it out lets us
    catch a misconfiguration offline (see `misconfigured`).
    """
    return (token or "").split(":", 1)[0].strip()


def misconfigured(repo_root):
    """A configuration error that no network call is needed to see.

    `status()` reports whether the two variables are SET, which is not the same
    as whether they can work — and the gap is not theoretical. Setting
    `TELEGRAM_CHAT_ID` to the id in front of the colon in the bot token is an
    easy mistake (both are long numbers printed near each other by BotFather),
    and it is always wrong: it asks the bot to message itself, which Telegram
    answers with a bare 403 that names no cause.

    Returns a sentence, or "" when nothing is provably wrong.
    """
    cfg = config(repo_root)
    token = os.environ.get(cfg["token_env"], "").strip()
    chat_id = os.environ.get(cfg["chat_id_env"], "").strip()
    if not token or not chat_id:
        return ""
    if chat_id == bot_id(token):
        # For a one-to-one chat the chat id IS the user id, so if the workspace
        # already names the person, the right value is sitting right there and
        # the message should say so rather than send them looking.
        own = os.environ.get("TELEGRAM_USER_ID", "").strip()
        fix = ("Set it to %s (your TELEGRAM_USER_ID)." % own if own
               else "Set it to YOUR chat id — `kanban notify chat-id` prints it.")
        return ("%s is set to the bot's own id, so every send is a bot "
                "messaging itself and Telegram answers 403. %s"
                % (cfg["chat_id_env"], fix))
    return ""


def api_call(cfg, method, params, opener=None):
    """One Bot API call. Returns `(result, detail)`. Never raises.

    **`detail` is the success signal, not `result`.** Telegram's `ok` field
    says whether the call worked; `result` is merely its payload, and different
    methods return an object, a bare `true`, or nothing at all. Treating a
    missing `result` as failure marks successful calls as failed — which is
    exactly what `sendMessage` did here until a test caught it.

    Every Telegram call in this console goes through this one function so the
    rules about credentials hold in one place: the token is read per call, and
    a failure reports the status code and never the URL — the URL contains the
    token, so logging it would leak the credential into whatever read the log.
    """
    token = os.environ.get(cfg["token_env"], "").strip()
    if not token:
        return None, "%s is not set" % cfg["token_env"]

    url = "%s/bot%s/%s" % (TELEGRAM_API, token, method)
    body = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=cfg["timeout"]) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
        if not payload.get("ok"):
            return None, str(payload.get("description") or "telegram reported not-ok")
        return payload.get("result"), ""
    except urllib.error.HTTPError as exc:
        # The status, never the URL: the URL contains the bot token.
        return None, "telegram returned HTTP %s" % exc.code
    except Exception as exc:  # noqa: BLE001
        return None, "%s" % type(exc).__name__


def _post_telegram(cfg, text, opener=None, buttons=None, chat_id=None):
    """Send one message. Returns (ok, detail). Never raises.

    `buttons` is a list of rows, each a list of `(label, callback_data)`. They
    are what turns a notification into an answer: without them the message says
    a run is blocked and leaves you to find a browser, which on a phone means
    the run dies on its timeout anyway.
    """
    target = (chat_id or os.environ.get(cfg["chat_id_env"], "")).strip()
    if not target:
        return False, "credentials not set"

    params = {
        "chat_id": target,
        "text": text[:4000],          # Telegram's own limit is 4096
        "disable_web_page_preview": "true",
    }
    if buttons:
        params["reply_markup"] = json.dumps({"inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in buttons]})
    _result, detail = api_call(cfg, "sendMessage", params, opener=opener)
    return (not detail), detail


def edit_message(cfg, chat_id, message_id, text, opener=None):
    """Replace a sent message's text and drop its buttons.

    Called once a decision is made. A button that has already been used but
    still looks live invites a second tap, and the second tap hits an approval
    that is no longer pending — so the honest thing is to remove the buttons
    and say what happened.
    """
    return api_call(cfg, "editMessageText", {
        "chat_id": chat_id, "message_id": message_id,
        "text": text[:4000], "disable_web_page_preview": "true",
    }, opener=opener)


def answer_callback(cfg, callback_id, text="", opener=None):
    """Stop the spinner on a tapped button.

    Telegram shows a loading state on an inline button until this is called.
    Skipping it leaves the button spinning for ~15s even when the action
    already succeeded, which reads as a hang.
    """
    return api_call(cfg, "answerCallbackQuery", {
        "callback_query_id": callback_id, "text": text[:200],
    }, opener=opener)


CHANNELS = {"telegram": _post_telegram}


def discover_chat_ids(repo_root, opener=None):
    """Ask Telegram which chats have spoken to this bot. Returns (rows, error).

    Telegram never tells you your own chat id; you have to read it out of an
    update. The documented way is to paste `getUpdates` into a browser with the
    token in the URL — which writes a live credential into browser history, an
    address bar, and any screenshot of either. This does the same call from the
    process that already holds the token, and prints only the ids.

    An empty list is the normal first answer and is not an error: the bot has
    to be spoken to before it has anything to report.
    """
    cfg = config(repo_root)
    token = os.environ.get(cfg["token_env"], "").strip()
    if not token:
        return [], "%s is not set" % cfg["token_env"]

    url = "%s/bot%s/getUpdates" % (TELEGRAM_API, token)
    try:
        with (opener or urllib.request.urlopen)(url, timeout=cfg["timeout"]) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 404):
            return [], "Telegram rejected the token (HTTP %s)" % exc.code
        return [], "telegram returned HTTP %s" % exc.code
    except Exception as exc:  # noqa: BLE001
        return [], "%s" % type(exc).__name__

    if not payload.get("ok"):
        return [], "telegram reported not-ok"

    seen, rows = set(), []
    for update in payload.get("result") or []:
        message = (update.get("message") or update.get("channel_post")
                   or update.get("edited_message") or {})
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or chat_id in seen:
            continue
        seen.add(chat_id)
        name = chat.get("title") or " ".join(
            p for p in (chat.get("first_name"), chat.get("last_name")) if p)
        rows.append({"chat_id": str(chat_id),
                     "name": name or chat.get("username") or "",
                     "type": chat.get("type") or ""})
    return rows, ""


def send(repo_root, kind, text, *, opener=None, block=False, buttons=None,
         chat_id=None):
    """Deliver `text` if this kind is enabled. Returns a small result dict.

    Fires on a daemon thread by default so a slow or hanging provider cannot
    add latency to an agent turn. `block=True` is for tests and for the CLI,
    where there is no turn to protect and the caller wants the answer.

    `buttons` reaches the channel unchanged; a channel that has no concept of
    them ignores the argument rather than failing, which is what keeps
    `CHANNELS` a seam other services can be added to.
    """
    cfg = config(repo_root)
    if not cfg["enabled"]:
        return {"sent": False, "reason": "disabled"}
    if kind not in cfg["events"]:
        return {"sent": False, "reason": "%s not in the enabled events" % kind}
    # Quiet hours never apply to an approval, and this is deliberate rather
    # than an oversight worth "fixing" later. A parked approval denies after
    # its timeout, so silencing one does not postpone a buzz — it kills the
    # run. The two events quiet hours exist for are the ones that are merely
    # informative: a finished run and a failed job both keep until morning.
    if kind != "approval" and in_quiet_hours(cfg):
        return {"sent": False, "reason": "quiet hours"}
    channel = CHANNELS.get(cfg["channel"])
    if channel is None:
        return {"sent": False, "reason": "unknown channel %r" % cfg["channel"]}

    kw = {"opener": opener, "buttons": buttons, "chat_id": chat_id}
    if block:
        ok, detail = channel(cfg, text, **kw)
        return {"sent": ok, "reason": detail}

    threading.Thread(target=channel, args=(cfg, text), kwargs=kw,
                     daemon=True).start()
    return {"sent": True, "reason": "dispatched"}


# ------------------------------------------------------------- messages -----

def _shorten(value, limit=180):
    text = str(value or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def approval_message(tool, tool_input, preview, timeout, chat_title=""):
    """A message you can act on from a lock screen.

    The point is deciding whether to walk to a laptop, so it leads with the
    single most decision-relevant fact: which file, how much changed, or what
    command. A generic "approval needed" tells you nothing you did not already
    know from the fact that your phone buzzed.
    """
    lines = ["Permission needed: %s" % tool]
    if chat_title:
        lines.append(_shorten(chat_title, 90))

    if preview and preview.get("kind") == "diff":
        lines.append("%s  +%d -%d%s" % (
            preview.get("path", "?"), preview.get("added", 0),
            preview.get("removed", 0),
            "  (new file)" if preview.get("creating") else ""))
    elif preview and preview.get("kind") == "command":
        lines.append("$ %s" % _shorten(preview.get("command"), 300))
    elif preview and preview.get("kind") == "note":
        lines.append(_shorten(preview.get("text")))
    else:
        lines.append(_shorten(json.dumps(tool_input or {}, default=str), 300))

    lines.append("Denies in %ds if nobody answers." % int(timeout or 0))
    return "\n".join(lines)


#: Prefix for approval callbacks. Telegram caps `callback_data` at 64 BYTES and
#: silently rejects the whole keyboard past it, so the budget is worth stating:
#: "ap:" + at most "session" + ":" + a 12-hex key = 23 bytes. The key comes from
#: `uuid4().hex[:12]`, so this cannot drift without that changing too.
CALLBACK_PREFIX = "ap:"
CALLBACK_MAX = 64


def approval_buttons(key, session_offer=True):
    """Allow once / allow for this chat / deny, as one row plus one.

    The three map exactly onto what `agent_approvals.REGISTRY.decide` already
    accepts, so answering from a phone runs the same code as answering from the
    browser — no second decision path to keep in step.
    """
    row = [("✅ Allow once", CALLBACK_PREFIX + "allow:" + key)]
    if session_offer:
        row.append(("✅ Allow for this chat", CALLBACK_PREFIX + "session:" + key))
    return [row, [("❌ Deny", CALLBACK_PREFIX + "deny:" + key)]]


def parse_callback(data):
    """`ap:allow:<key>` → `("allow", "<key>")`, or `(None, "")`."""
    text = str(data or "")
    if not text.startswith(CALLBACK_PREFIX):
        return None, ""
    parts = text[len(CALLBACK_PREFIX):].split(":", 1)
    if len(parts) != 2 or parts[0] not in ("allow", "session", "deny"):
        return None, ""
    return parts[0], parts[1]


def turn_end_message(title, agent, model, turns, cost_usd, error=False):
    """"Your run finished" — the other reason to look at a phone.

    Cost is omitted rather than shown as $0.00 when nothing reported one: a
    zero that means "unknown" is the single misreading the cost rules in this
    console exist to prevent.
    """
    head = "Run failed" if error else "Run finished"
    lines = ["%s: %s" % (head, _shorten(title or "(untitled)", 90))]
    facts = [f for f in (agent, model, "%d turn%s" % (turns, "" if turns == 1 else "s")
                         if turns else "") if f]
    if cost_usd:
        facts.append("$%.4f" % cost_usd)
    if facts:
        lines.append(" · ".join(facts))
    return "\n".join(lines)


def job_error_message(verb, ticket, error):
    """A scheduled job died. Nobody is watching a 3am job by definition."""
    lines = ["Job failed: %s" % (verb or "?")]
    if ticket:
        lines.append("ticket %s" % ticket)
    lines.append(_shorten(error, 300))
    return "\n".join(lines)
