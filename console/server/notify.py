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

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

from . import boards as boards_mod

DEFAULT_TIMEOUT = 8
TELEGRAM_API = "https://api.telegram.org"

#: Event kinds a channel may be asked to deliver. `approval` is the one that
#: matters; the rest are opt-in because a phone that buzzes for everything gets
#: muted, and then it buzzes for nothing.
KINDS = ("approval", "turn_end", "job_error")


def config(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("notify", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "channel": cfg.get("channel", "telegram"),
        "token_env": cfg.get("token_env") or "TELEGRAM_BOT_TOKEN",
        "chat_id_env": cfg.get("chat_id_env") or "TELEGRAM_CHAT_ID",
        "events": [e for e in cfg.get("events", ["approval"]) if e in KINDS],
        "timeout": int(cfg.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT),
    }


def status(repo_root):
    """What a person needs to diagnose 'why didn't my phone buzz?'.

    Deliberately reports whether each secret is *present*, never its value.
    """
    cfg = config(repo_root)
    token = os.environ.get(cfg["token_env"], "").strip()
    chat_id = os.environ.get(cfg["chat_id_env"], "").strip()
    ready = bool(cfg["enabled"] and token and chat_id)
    reason = ""
    if not cfg["enabled"]:
        reason = "notifications are disabled in console.toml"
    elif not token:
        reason = "%s is not set" % cfg["token_env"]
    elif not chat_id:
        reason = "%s is not set" % cfg["chat_id_env"]
    return {"enabled": cfg["enabled"], "channel": cfg["channel"],
            "events": cfg["events"], "ready": ready, "reason": reason,
            "token_present": bool(token), "chat_id_present": bool(chat_id)}


def _post_telegram(cfg, text, opener=None):
    """Send one message. Returns (ok, detail). Never raises."""
    token = os.environ.get(cfg["token_env"], "").strip()
    chat_id = os.environ.get(cfg["chat_id_env"], "").strip()
    if not token or not chat_id:
        return False, "credentials not set"

    url = "%s/bot%s/sendMessage" % (TELEGRAM_API, token)
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text[:4000],          # Telegram's own limit is 4096
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=cfg["timeout"]) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
            return bool(payload.get("ok")), ""
    except urllib.error.HTTPError as exc:
        # The status, never the URL: the URL contains the bot token.
        return False, "telegram returned HTTP %s" % exc.code
    except Exception as exc:  # noqa: BLE001
        return False, "%s" % type(exc).__name__


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


def send(repo_root, kind, text, *, opener=None, block=False):
    """Deliver `text` if this kind is enabled. Returns a small result dict.

    Fires on a daemon thread by default so a slow or hanging provider cannot
    add latency to an agent turn. `block=True` is for tests and for the CLI,
    where there is no turn to protect and the caller wants the answer.
    """
    cfg = config(repo_root)
    if not cfg["enabled"]:
        return {"sent": False, "reason": "disabled"}
    if kind not in cfg["events"]:
        return {"sent": False, "reason": "%s not in the enabled events" % kind}
    channel = CHANNELS.get(cfg["channel"])
    if channel is None:
        return {"sent": False, "reason": "unknown channel %r" % cfg["channel"]}

    if block:
        ok, detail = channel(cfg, text, opener=opener)
        return {"sent": ok, "reason": detail}

    threading.Thread(target=channel, args=(cfg, text),
                     kwargs={"opener": opener}, daemon=True).start()
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
