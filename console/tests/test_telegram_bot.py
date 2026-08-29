"""Inbound Telegram — the half that can start work rather than describe it.

No network anywhere: a fake opener returns whatever Telegram payload the test
wants, the same fixture style `test_notify_audit.py` uses.

The authorization tests carry more weight than the rest of this file. Inbound
Telegram can approve `run_command`, so the allowlist is the only thing between
a stranger's message and a shell on this machine. A regression there is not a
broken feature; it is a remote shell.
"""

import json
import os

import pytest

from server import agent_approvals, audit, notify, telegram_bot

CONSOLE = """\
[notify]
enabled   = true
channel   = "telegram"
events    = ["approval", "turn_end", "job_error"]
inbound   = true
timeout   = 2

[audit]
enabled = true
dir     = "console/.cache/audit"
"""


class Fake:
    """Scripted Telegram. Records the params of every call it is handed."""

    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append({
            "url": request.full_url.rsplit("/", 1)[-1],
            "params": dict(pair.split("=", 1) for pair in
                           request.data.decode().split("&") if "=" in pair),
        })
        body = self.payloads.pop(0) if self.payloads else {"ok": True, "result": []}

        class Resp:
            def read(inner):
                return json.dumps(body).encode()

            def __enter__(inner):
                return inner

            def __exit__(inner, *a):
                return False
        return Resp()


@pytest.fixture
def ws(repo, monkeypatch):
    with open(os.path.join(repo, "console", "config", "console.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(CONSOLE)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "8774432343:secret-part-here")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1340545818")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USERS", raising=False)
    monkeypatch.delenv("TELEGRAM_ALLOW_ALL_USERS", raising=False)
    return repo


def message(text, user_id="1340545818", update_id=10):
    return {"update_id": update_id,
            "message": {"message_id": 5, "text": text,
                        "chat": {"id": 1340545818, "type": "private"},
                        "from": {"id": int(user_id), "username": "sohail"}}}


class TestAuthorization:
    """Fail-closed, on user id, always."""

    def test_an_empty_allowlist_denies_a_real_user(self, ws):
        # The load-bearing test in this file. "No list" must never mean
        # "everyone" — that is how a pasted bot token becomes a remote shell.
        ok, why = telegram_bot.authorize(ws, "1340545818")
        assert ok is False
        assert "allowlist is empty" in why

    def test_a_listed_user_is_allowed(self, ws, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "999, 1340545818 ,111")
        assert telegram_bot.authorize(ws, "1340545818")[0] is True

    def test_an_unlisted_user_is_denied(self, ws, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "999")
        ok, why = telegram_bot.authorize(ws, "1340545818")
        assert ok is False and "not on the allowlist" in why

    def test_allow_all_is_explicit_and_separate(self, ws, monkeypatch):
        # Only ever true because someone set a variable named ALLOW_ALL_USERS.
        monkeypatch.setenv("TELEGRAM_ALLOW_ALL_USERS", "true")
        assert telegram_bot.authorize(ws, "77")[0] is True

    def test_a_missing_user_id_is_denied(self, ws, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "*")
        assert telegram_bot.authorize(ws, "")[0] is False

    def test_a_channel_post_is_authorized_on_its_sender_chat(self, ws):
        # Channel posts carry no `from`, so without this the broadcast path
        # would be an unchecked way in.
        uid, name = telegram_bot.identity({
            "channel_post": {"text": "hi", "sender_chat":
                             {"id": -100123, "title": "Some Channel"}}})
        assert uid == "-100123" and name == "Some Channel"
        assert telegram_bot.authorize(ws, uid)[0] is False

    def test_a_rejected_message_is_audited(self, ws):
        # A stranger probing the bot appears nowhere else in the system, so
        # this record is the only evidence it happened.
        poller = telegram_bot.Poller(ws)
        poller._handle(notify.config(ws), message("/status", user_id="4242"))

        rows = audit.read(ws, action="telegram.rejected")
        assert len(rows) == 1, rows
        assert rows[0]["actor"]["addr"] == "telegram:4242"
        assert "allowlist is empty" in rows[0]["outcome"]

    def test_an_unauthorized_message_never_reaches_a_command(self, ws):
        # Belt and braces on the same boundary: prove the refusal happens
        # before dispatch, not merely that it is logged afterwards.
        poller = telegram_bot.Poller(ws)
        called = []
        poller._dispatch = lambda *a, **k: called.append(a)
        poller._handle(notify.config(ws), message("/new claude go", user_id="4242"))
        assert called == []


class TestCallbacks:
    def test_the_three_buttons_map_onto_the_three_decisions(self):
        # They must stay exactly the set `REGISTRY.decide` accepts, or a tap
        # would raise instead of answering.
        wire = {"allow": "allow", "session": "allow-session", "deny": "deny"}
        for _label, data in [b for row in notify.approval_buttons("k" * 12)
                             for b in row]:
            decision, key = notify.parse_callback(data)
            assert decision in wire and key == "k" * 12

    def test_callback_data_fits_telegram_s_limit(self):
        # Past 64 bytes Telegram rejects the whole keyboard, so the message
        # arrives with no buttons at all and the run dies on its timeout.
        for _label, data in [b for row in notify.approval_buttons("f" * 12)
                             for b in row]:
            assert len(data.encode("utf-8")) <= notify.CALLBACK_MAX

    def test_junk_callback_data_is_ignored(self):
        assert notify.parse_callback("hello") == (None, "")
        assert notify.parse_callback("ap:sudo:key") == (None, "")
        assert notify.parse_callback("") == (None, "")

    def test_a_stale_key_is_reported_not_raised(self, ws, monkeypatch):
        """A button tapped after the approval timed out must explain itself.

        The alternative is a spinner that never stops: `decide` raises for a
        key that is no longer pending, and an unhandled raise here would skip
        `answerCallbackQuery` entirely.
        """
        monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "1340545818")
        fake = Fake({"ok": True, "result": True},      # answerCallbackQuery
                    {"ok": True, "result": {}})        # editMessageText
        monkeypatch.setattr(notify.urllib.request, "urlopen", fake)

        poller = telegram_bot.Poller(ws)
        poller._on_callback(notify.config(ws), {
            "id": "cb1", "data": "ap:allow:deadbeefcafe",
            "message": {"message_id": 5, "chat": {"id": 1}, "text": "x"},
        }, "1340545818", "sohail")

        answered = [c for c in fake.calls if c["url"] == "answerCallbackQuery"]
        assert len(answered) == 1, fake.calls
        assert "no+longer+pending" in answered[0]["params"]["text"]

    def test_a_live_key_is_decided_and_attributed(self, ws, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "1340545818")
        fake = Fake({"ok": True, "result": True}, {"ok": True, "result": {}})
        monkeypatch.setattr(notify.urllib.request, "urlopen", fake)

        # Park a real question the way `request()` does, without its blocking.
        pending = agent_approvals.Pending("live00000key", "chat1", "write_file",
                                          {}, "tu1")
        agent_approvals.REGISTRY._pending["live00000key"] = pending
        try:
            telegram_bot.Poller(ws)._on_callback(notify.config(ws), {
                "id": "cb2", "data": "ap:session:live00000key",
                "message": {"message_id": 5, "chat": {"id": 1}, "text": "x"},
            }, "1340545818", "sohail")
        finally:
            agent_approvals.REGISTRY._pending.pop("live00000key", None)
            agent_approvals.REGISTRY._session_allow.pop("chat1", None)

        assert pending.decision == "allow"
        # Who answered, and from where — the browser card shows this.
        assert pending.by == "telegram:sohail"
        assert pending.event.is_set()
        # The card is edited so its buttons stop inviting a second tap.
        assert [c for c in fake.calls if c["url"] == "editMessageText"]


class TestMisconfiguration:
    def test_a_chat_id_equal_to_the_bot_id_is_caught_offline(self, ws, monkeypatch):
        # The real failure on this machine: TELEGRAM_CHAT_ID was set to the
        # number in front of the colon in the token, so every send was the bot
        # messaging itself and Telegram answered a bare 403.
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "8774432343")
        why = notify.misconfigured(ws)
        assert "bot's own id" in why
        assert notify.status(ws)["ready"] is False

    def test_a_correct_pair_is_not_flagged(self, ws):
        assert notify.misconfigured(ws) == ""
        assert notify.status(ws)["ready"] is True


class TestMessages:
    def test_an_unpriced_run_never_reports_zero_dollars(self):
        # $0.00 reads as free. Unknown cost is omitted instead.
        text = notify.turn_end_message("t", "ollama", "qwen3", 2, 0.0)
        assert "$" not in text

    def test_a_priced_run_reports_what_it_cost(self):
        assert "$0.1823" in notify.turn_end_message("t", "or", "m", 9, 0.1823)

    def test_a_failed_run_says_so(self):
        assert notify.turn_end_message("t", "a", "m", 1, 0, error=True).startswith(
            "Run failed")


class TestReplayOnRestart:
    def test_the_backlog_is_skipped_not_executed(self, ws):
        """Telegram redelivers unacknowledged updates for 24 hours.

        Without draining, restarting the console re-runs whatever was sent
        while it was down — including `/new`, which starts agents nobody is
        waiting for.
        """
        fake = Fake({"ok": True, "result": [
            {"update_id": 41, "message": {"message_id": 1, "text": "/new x go",
                                          "chat": {"id": 1},
                                          "from": {"id": 1340545818}}}]})
        poller = telegram_bot.Poller(ws)
        monkey_cfg = dict(notify.config(ws))
        original = notify.api_call

        def spy(cfg, method, params, opener=None):
            return original(cfg, method, params, opener=fake)
        notify.api_call = spy
        try:
            poller._drain(monkey_cfg)
        finally:
            notify.api_call = original
        # Acknowledged past the backlog, and nothing was handled.
        assert poller._offset == 42
        assert poller._bound == {}

    def test_the_loop_drains_before_it_starts_listening(self, ws):
        """The drain must be WIRED, not merely correct.

        Testing `_drain` alone passes happily while the call is missing from
        `_loop` — which is the only place it matters.
        """
        poller = telegram_bot.Poller(ws)
        drained = []
        poller._drain = lambda cfg: drained.append(cfg)
        poller._stop.set()          # so the poll loop itself never runs
        poller._loop()
        assert drained, "_loop must drain the backlog before its first poll"
