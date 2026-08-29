"""Telegram as a second client: answer approvals and drive agents from a phone.

`notify.py` is the outbound half — it tells you a run is blocked. This is the
inbound half, and without it the telling is not much use: a gated tool denies
after 300 seconds, so away from the desk the notification only converts "the
run died silently" into "the run died and you watched it".

## Polling, not a webhook

A webhook needs a public HTTPS URL pointing at this machine. This console binds
to loopback or a tailnet and **has no authentication of its own by design**, so
exposing it is the one thing the remote model forbids. Long-polling inverts the
direction: the console reaches out, Telegram never reaches in, and it works
behind NAT with nothing opened. It is also what the hermes adapter does.

## Authorization is the entire safety story

A bot token addresses a *public* endpoint. Anyone who finds the bot can message
it, and this console can approve `run_command` — so the allowlist is the only
thing between a stranger's message and a shell on this machine.

Therefore, deliberately copied from hermes' adapter:

  * the allowlist is **user ids**, not chat ids, and it is **fail-closed** —
    empty or unset means the bot answers nobody. Never allow-by-omission.
  * a channel post carries no `from_user`; it is authorized on `sender_chat` or
    refused, so the broadcast path cannot be used to inject commands.
  * `TELEGRAM_ALLOW_ALL_USERS` exists for development, is named so it cannot be
    set by accident, and is announced loudly at every start.

Both outcomes are audited. A rejected message matters more than an accepted
one: it is the only place a stranger probing the bot becomes visible.

## Restarting must not replay yesterday

Telegram redelivers every update that has not been acknowledged by advancing
the offset. Starting with no offset therefore replays whatever is queued —
which for this bot means re-running `/new` and starting agents nobody asked
for. `_drain()` skips the backlog once at startup.
"""

import json
import threading
import time

from . import agent_approvals, agent_backends, agent_manager, audit, notify

#: How long Telegram holds a `getUpdates` request open with nothing to say.
#: Long-polling: one request per 25 idle seconds rather than a request per
#: second, which is both cheaper and faster to react.
POLL_TIMEOUT = 25

#: After a network failure. Long enough not to hammer a dead link, short enough
#: that a laptop coming back from sleep reconnects while you are still looking.
BACKOFF = 5

#: Telegram's own per-message cap is 4096 characters.
MAX_REPLY = 3500


def config(repo_root):
    """Inbound settings, layered onto `notify`'s outbound ones."""
    from . import boards as boards_mod
    cfg = boards_mod.load_console_config(repo_root).get("notify", {}) or {}
    return {
        "inbound": bool(cfg.get("inbound", False)),
        "allowed_users_env": cfg.get("allowed_users_env") or "TELEGRAM_ALLOWED_USERS",
        "allow_all_env": cfg.get("allow_all_users_env") or "TELEGRAM_ALLOW_ALL_USERS",
        "poll_timeout": int(cfg.get("poll_timeout", POLL_TIMEOUT) or POLL_TIMEOUT),
    }


def allowed_users(repo_root):
    """The allowlist, as a set of id strings. Empty means nobody."""
    import os
    raw = os.environ.get(config(repo_root)["allowed_users_env"], "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def allow_all(repo_root):
    import os
    value = os.environ.get(config(repo_root)["allow_all_env"], "")
    return value.strip().lower() in ("1", "true", "yes", "on")


def authorize(repo_root, user_id):
    """Fail-closed. Returns (ok, why).

    An empty allowlist denies a perfectly real user id on purpose. The
    alternative — treating "no list" as "everyone" — is how a bot token pasted
    into a config becomes a remote shell, and it is the bug hermes had to fix
    (their issue #24457) rather than a hypothetical.
    """
    if not user_id:
        return False, "no user id on the update"
    if allow_all(repo_root):
        return True, "allow-all is on"
    ids = allowed_users(repo_root)
    if not ids:
        return False, "the allowlist is empty, so nobody is authorized"
    if "*" in ids or str(user_id) in ids:
        return True, ""
    return False, "user is not on the allowlist"


def _actor(user_id, name=""):
    """The audit shape for someone arriving over Telegram rather than HTTP."""
    return {"addr": "telegram:%s" % user_id, "agent": name or "telegram"}


def identity(update):
    """Who sent this, for authorization. Returns (user_id, display_name).

    A channel post has no `from_user` at all, so it is authorized on the
    sending chat instead — otherwise the broadcast path would be an unchecked
    way in.
    """
    node = (update.get("message") or update.get("edited_message")
            or update.get("channel_post") or update.get("callback_query") or {})
    user = node.get("from") or {}
    uid = str(user.get("id") or "").strip()
    name = (user.get("username") or user.get("first_name") or "").strip()
    if not uid:
        sender = node.get("sender_chat") or {}
        uid = str(sender.get("id") or "").strip()
        name = (sender.get("title") or "").strip()
    return uid, name


class Poller:
    """One long-poll loop for the life of the server process."""

    def __init__(self, repo_root, server_port=0):
        self.repo_root = repo_root
        self.server_port = server_port
        self._stop = threading.Event()
        self._thread = None
        self._offset = None
        #: Telegram chat id -> console chat id. Which agent a bare message
        #: goes to, so you do not have to name it every time.
        #:
        #: No card bookkeeping alongside it: a `callback_query` carries the
        #: message it came from, so editing the card after a decision needs
        #: nothing remembered from when it was sent.
        self._bound = {}

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        """Ask the loop to finish. Does not interrupt a poll already in flight.

        A `getUpdates` call parks for up to 25 seconds, and there is no way to
        cancel it from here — so the flag is seen when that call returns, which
        can be well after this is called. The thread is a daemon precisely so
        that gap cannot hold up shutdown: the process exits, the socket goes
        with it, and the update is simply redelivered on the next start.
        """
        self._stop.set()

    # -- the loop ----------------------------------------------------------
    def _loop(self):
        cfg = notify.config(self.repo_root)
        self._drain(cfg)
        while not self._stop.is_set():
            result, detail = notify.api_call(cfg, "getUpdates", {
                "offset": self._offset,
                "timeout": config(self.repo_root)["poll_timeout"],
                # Only what this bot acts on. Anything else is bandwidth and
                # another shape to defend against.
                "allowed_updates": json.dumps(["message", "callback_query"]),
            }, opener=_long_poll_opener(cfg))
            if detail:
                # `detail`, not `result`: an idle long-poll succeeds and
                # returns an EMPTY list, which is not a failure. Never raise
                # out of this thread either — it holds the only inbound path,
                # and a crash here would take Telegram control away silently
                # while the console carried on serving.
                if not self._stop.wait(BACKOFF):
                    continue
                break
            for update in result:
                self._offset = int(update.get("update_id", 0)) + 1
                try:
                    self._handle(cfg, update)
                except Exception as exc:  # noqa: BLE001
                    # One malformed update must not stop the loop.
                    audit.record(self.repo_root, "telegram.rejected",
                                 actor=_actor("?"), target="handler",
                                 outcome="error: %s" % type(exc).__name__)

    def _drain(self, cfg):
        """Acknowledge whatever is queued without acting on it.

        Telegram holds undelivered updates for 24h. Without this, restarting
        the console re-runs every command sent while it was down — including
        `/new`, which starts agents.
        """
        result, _detail = notify.api_call(cfg, "getUpdates",
                                          {"offset": -1, "timeout": 0})
        for update in result or []:
            self._offset = int(update.get("update_id", 0)) + 1

    # -- routing -----------------------------------------------------------
    def _handle(self, cfg, update):
        user_id, name = identity(update)
        ok, why = authorize(self.repo_root, user_id)
        if not ok:
            # The single most important line in this module. A stranger
            # probing the bot appears nowhere else.
            audit.record(self.repo_root, "telegram.rejected",
                         actor=_actor(user_id or "unknown", name),
                         target="inbound", outcome=why)
            return

        if update.get("callback_query"):
            self._on_callback(cfg, update["callback_query"], user_id, name)
        elif update.get("message"):
            self._on_message(cfg, update["message"], user_id, name)

    def _on_callback(self, cfg, query, user_id, name):
        """A tapped approval button."""
        decision, key = notify.parse_callback(query.get("data"))
        if decision is None:
            notify.answer_callback(cfg, query.get("id"), "Unrecognised button.")
            return

        wire = {"allow": "allow", "session": "allow-session", "deny": "deny"}[decision]
        who = "telegram:%s" % (name or user_id)
        try:
            agent_approvals.REGISTRY.decide(key, wire, by=who)
            said = {"allow": "Allowed", "session": "Allowed for this chat",
                    "deny": "Denied"}[decision]
        except ValueError as exc:
            # Already answered, or timed out and gone. Say which, rather than
            # leaving a spinner on a button that will never do anything.
            said = str(exc)

        audit.record(self.repo_root, "approval.decide",
                     actor=_actor(user_id, name), target=key,
                     detail={"decision": wire, "via": "telegram"},
                     outcome=said)
        notify.answer_callback(cfg, query.get("id"), said)

        # Replace the card so its buttons stop looking live. A used button that
        # still invites a tap gets tapped, and the second tap always fails.
        message = query.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id and message.get("message_id"):
            original = message.get("text") or ""
            notify.edit_message(cfg, chat_id, message["message_id"],
                                "%s\n\n— %s by %s" % (original, said, who))

    def _on_message(self, cfg, message, user_id, name):
        text = (message.get("text") or "").strip()
        chat_id = (message.get("chat") or {}).get("id")
        if not text or chat_id is None:
            return

        reply = self._dispatch(text, chat_id, user_id, name)
        audit.record(self.repo_root, "telegram.command",
                     actor=_actor(user_id, name),
                     target=text.split()[0][:40],
                     outcome="ok" if reply else "no reply")
        if reply:
            notify.send(self.repo_root, "approval", reply[:MAX_REPLY],
                        chat_id=str(chat_id))

    # -- commands ----------------------------------------------------------
    def _dispatch(self, text, chat_id, user_id, name):
        if not text.startswith("/"):
            return self._say(text, chat_id)
        word, _, rest = text.partition(" ")
        handler = {
            "/chats": self._cmd_chats, "/use": self._cmd_use,
            "/new": self._cmd_new, "/stop": self._cmd_stop,
            "/interrupt": self._cmd_interrupt, "/status": self._cmd_status,
            "/help": self._cmd_help, "/start": self._cmd_help,
        }.get(word.split("@")[0].lower())   # "/chats@mybot" in a group
        if handler is None:
            return "Unknown command. /help lists them."
        return handler(rest.strip(), chat_id)

    def _cmd_help(self, _rest, _chat_id):
        return ("/chats — list chats\n"
                "/use <n> — send my messages to that chat\n"
                "/new <backend> [model] <prompt> — start one\n"
                "/interrupt · /stop — on the bound chat\n"
                "/status — what is available\n"
                "Anything else is sent to the bound chat.")

    def _live(self):
        return [c for c in agent_manager.list_chats(self.repo_root) if c.get("alive")]

    def _cmd_chats(self, _rest, chat_id):
        rows = self._live()
        if not rows:
            return "No live chats. /new starts one."
        bound = self._bound.get(chat_id)
        out = []
        for i, c in enumerate(rows, 1):
            mark = " ←" if c["id"] == bound else ""
            out.append("%d. %s — %s%s%s" % (
                i, c.get("title") or "(untitled)", c.get("agent") or "?",
                " · working" if c.get("busy") else "", mark))
        return "\n".join(out)

    def _cmd_use(self, rest, chat_id):
        rows = self._live()
        try:
            pick = rows[int(rest.strip()) - 1]
        except (ValueError, IndexError):
            return "Give the number from /chats."
        self._bound[chat_id] = pick["id"]
        return "Bound to: %s" % (pick.get("title") or pick["id"])

    def _cmd_new(self, rest, chat_id):
        """`/new <backend> [model] <prompt>`.

        The backend must be named: guessing which agent to spend money with is
        exactly the decision a person should be making deliberately.
        """
        parts = rest.split(None, 1)
        if len(parts) < 2:
            usable = [b.id for b in agent_backends.registry(self.repo_root).values()
                      if b.installed]
            return "Usage: /new <backend> <prompt>\nAvailable: %s" % (
                ", ".join(usable) or "none")
        backend_id, prompt = parts[0], parts[1]
        try:
            snap = agent_manager.create(
                self.repo_root, backend_id, prompt,
                title=prompt[:80], server_port=self.server_port)
        except Exception as exc:  # noqa: BLE001
            return "Could not start: %s" % exc
        self._bound[chat_id] = snap["id"]
        return "Started %s on %s. Bound to it." % (snap["id"], backend_id)

    def _bound_session(self, chat_id):
        sid = self._bound.get(chat_id)
        if not sid:
            return None, "Nothing bound. /chats then /use <n>."
        return sid, ""

    def _say(self, text, chat_id):
        sid, err = self._bound_session(chat_id)
        if err:
            return err
        try:
            result = agent_manager.send(sid, text, "auto")
        except Exception as exc:  # noqa: BLE001
            return "Could not send: %s" % exc
        return "Queued." if result.get("result") == "queued" else "Sent."

    def _cmd_interrupt(self, _rest, chat_id):
        sid, err = self._bound_session(chat_id)
        if err:
            return err
        try:
            agent_manager.interrupt(sid)
        except Exception as exc:  # noqa: BLE001
            return "Could not interrupt: %s" % exc
        return "Interrupting after the current step."

    def _cmd_stop(self, _rest, chat_id):
        sid, err = self._bound_session(chat_id)
        if err:
            return err
        try:
            agent_manager.stop(sid)
        except Exception as exc:  # noqa: BLE001
            return "Could not stop: %s" % exc
        self._bound.pop(chat_id, None)
        return "Session ended."

    def _cmd_status(self, _rest, chat_id):
        reg = agent_backends.registry(self.repo_root, force=True)
        ready = [b.id for b in reg.values() if b.installed]
        lines = ["Backends: %s" % (", ".join(ready) or "none available")]
        sid = self._bound.get(chat_id)
        lines.append("Bound: %s" % (sid or "nothing"))
        lines.append("Live chats: %d" % len(self._live()))
        return "\n".join(lines)


def _long_poll_opener(cfg):
    """`getUpdates` holds the connection open for `timeout` seconds, so the
    socket timeout has to outlast it — otherwise every idle poll ends as a
    client-side timeout and the loop spins on its own backoff."""
    import urllib.request

    def opener(request, timeout=None):
        return urllib.request.urlopen(
            request, timeout=(cfg["timeout"] + POLL_TIMEOUT + 5))
    return opener


#: The running poller, if any. One per process, like the scheduler's ticker.
POLLER = None


def start(repo_root, server_port=0):
    """Start inbound handling, or say why there is none. Returns the poller."""
    global POLLER
    cfg = config(repo_root)
    if not cfg["inbound"]:
        return None
    state = notify.status(repo_root)
    if not state["ready"]:
        print("  telegram inbound: OFF — %s" % state["reason"])
        return None
    if allow_all(repo_root):
        print("  telegram inbound: ON, ALLOWING EVERY USER (%s is set)."
              % cfg["allow_all_env"])
        print("                    Anyone who finds this bot can drive it.")
    else:
        count = len(allowed_users(repo_root))
        if not count:
            print("  telegram inbound: ON but %s is empty, so nobody is "
                  "authorized." % cfg["allowed_users_env"])
        else:
            print("  telegram inbound: ON — %d allowed user(s)" % count)
    POLLER = Poller(repo_root, server_port=server_port).start()
    return POLLER
