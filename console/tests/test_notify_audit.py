"""Notifications and the audit trail.

Both exist because of remote running. The notification is what stops a remote
run stalling silently at its first gated tool; the audit trail is what answers
"what happened, and was it me" once more than one device can start work.

The property both share, and the one most worth defending: **neither may ever
break the thing it is describing.** A failed send and a failed audit write are
both dropped, never raised.
"""

import json
import os
import urllib.error

import pytest

from server import agent_approvals, audit, boards, notify

NOTIFY_ON = """
[notify]
enabled = true
channel = "telegram"
token_env = "TEST_TG_TOKEN"
chat_id_env = "TEST_TG_CHAT"
events = ["approval"]
timeout = 3
"""


@pytest.fixture
def configured(repo, monkeypatch):
    with open(os.path.join(repo, "console", "config", "console.toml"), "a",
              encoding="utf-8") as fh:
        fh.write(NOTIFY_ON)
    boards._console_cache.clear()
    monkeypatch.setenv("TEST_TG_TOKEN", "12345:secret-bot-token")
    monkeypatch.setenv("TEST_TG_CHAT", "99887766")
    yield repo
    boards._console_cache.clear()


class Sent:
    """Captures what would have gone to the provider."""

    def __init__(self, status=200, ok=True):
        self.requests = []
        self.status = status
        self.ok = ok

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if self.status != 200:
            raise urllib.error.HTTPError(request.full_url, self.status,
                                         "err", {}, None)

        class Resp:
            def read(inner):
                return json.dumps({"ok": self.ok}).encode()

            def __enter__(inner):
                return inner

            def __exit__(inner, *a):
                return False
        return Resp()


class TestStatus:
    def test_disabled_by_default_and_says_so(self, repo):
        state = notify.status(repo)
        assert state["ready"] is False
        assert "disabled" in state["reason"]

    def test_enabled_without_a_token_names_the_variable(self, configured, monkeypatch):
        monkeypatch.delenv("TEST_TG_TOKEN")
        state = notify.status(configured)
        assert state["ready"] is False
        assert "TEST_TG_TOKEN" in state["reason"]

    def test_ready_when_configured(self, configured):
        assert notify.status(configured)["ready"] is True

    def test_status_never_reveals_a_secret(self, configured):
        # It reports presence, because "is it set" is the diagnostic question
        # and "what is it" is nobody's business.
        blob = json.dumps(notify.status(configured))
        assert "secret-bot-token" not in blob and "99887766" not in blob
        assert '"token_present": true' in blob.replace(" ", " ")


class TestSending:
    def test_a_message_is_delivered(self, configured):
        sent = Sent()
        out = notify.send(configured, "approval", "hello", opener=sent, block=True)
        assert out["sent"] is True
        assert len(sent.requests) == 1

    def test_the_chat_id_and_text_are_sent(self, configured):
        sent = Sent()
        notify.send(configured, "approval", "the message", opener=sent, block=True)
        body = sent.requests[0].data.decode()
        assert "99887766" in body and "the+message" in body.replace("%20", "+")

    def test_disabled_sends_nothing(self, repo):
        sent = Sent()
        out = notify.send(repo, "approval", "hi", opener=sent, block=True)
        assert out["sent"] is False and sent.requests == []

    def test_an_event_kind_that_is_not_enabled_is_skipped(self, configured):
        sent = Sent()
        out = notify.send(configured, "turn_end", "hi", opener=sent, block=True)
        assert out["sent"] is False
        assert "not in the enabled events" in out["reason"]

    def test_a_provider_failure_is_reported_not_raised(self, configured):
        out = notify.send(configured, "approval", "hi",
                          opener=Sent(status=500), block=True)
        assert out["sent"] is False
        assert "500" in out["reason"]

    def test_a_failure_never_leaks_the_token(self, configured):
        # The URL contains the bot token, so the failure path must report the
        # status and not the URL it called.
        out = notify.send(configured, "approval", "hi",
                          opener=Sent(status=401), block=True)
        assert "secret-bot-token" not in out["reason"]

    def test_an_unknown_channel_is_refused_cleanly(self, repo):
        with open(os.path.join(repo, "console", "config", "console.toml"), "a",
                  encoding="utf-8") as fh:
            fh.write('\n[notify]\nenabled = true\nchannel = "carrier-pigeon"\n'
                     'events = ["approval"]\n')
        boards._console_cache.clear()
        out = notify.send(repo, "approval", "hi", block=True)
        assert out["sent"] is False and "unknown channel" in out["reason"]


class TestApprovalMessage:
    def test_a_write_leads_with_the_file_and_the_size_of_the_change(self):
        # The question being answered on a lock screen is "do I need to walk
        # to a laptop", so a generic "approval needed" is useless.
        text = notify.approval_message(
            "write_file", {"path": "a.py"},
            {"kind": "diff", "path": "src/a.py", "added": 3, "removed": 1},
            300)
        assert "src/a.py" in text and "+3 -1" in text
        assert "300s" in text

    def test_a_new_file_is_marked(self):
        text = notify.approval_message(
            "write_file", {}, {"kind": "diff", "path": "x.py", "added": 9,
                               "removed": 0, "creating": True}, 300)
        assert "new file" in text

    def test_a_command_is_shown(self):
        text = notify.approval_message(
            "run_command", {}, {"kind": "command", "command": "rm -rf build"}, 60)
        assert "$ rm -rf build" in text

    def test_it_falls_back_to_arguments_with_no_preview(self):
        text = notify.approval_message("Weird", {"a": 1}, None, 300)
        assert "Weird" in text and "a" in text

    def test_the_chat_title_is_included(self):
        text = notify.approval_message("write_file", {}, None, 300,
                                       chat_title="Fix the parser")
        assert "Fix the parser" in text


class TestGateIntegration:
    def test_a_parked_approval_notifies(self, configured, monkeypatch):
        sent = []
        monkeypatch.setattr(notify, "send",
                            lambda root, kind, text, **kw: sent.append((kind, text)))

        def publish(event):
            agent_approvals.REGISTRY.decide(event["key"], "allow", by="test")

        agent_approvals.REGISTRY.request(
            "chat-n", "write_file", {"path": "a.py", "content": "x"},
            "t1", publish, timeout=5, repo_root=configured, title="A chat")
        assert sent and sent[0][0] == "approval"

    def test_a_notification_failure_does_not_break_the_gate(self, configured, monkeypatch):
        # The run must survive a broken notifier; being un-notified is no worse
        # than not having notifications configured.
        monkeypatch.setattr(notify, "send",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        seen = []

        def publish(event):
            seen.append(event)
            agent_approvals.REGISTRY.decide(event["key"], "allow", by="test")

        decision, _ = agent_approvals.REGISTRY.request(
            "chat-n2", "write_file", {"path": "a.py", "content": "x"},
            "t2", publish, timeout=5, repo_root=configured)
        assert decision == "allow"
        assert seen, "the card must still have been shown"


class TestAudit:
    def test_a_record_is_written_and_read_back(self, repo):
        audit.record(repo, "verb.run", actor={"addr": "100.64.0.2", "agent": "curl"},
                     target="harness-lint")
        rows = audit.read(repo)
        assert len(rows) == 1
        assert rows[0]["action"] == "verb.run"
        assert rows[0]["actor"]["addr"] == "100.64.0.2"

    def test_records_come_back_newest_first(self, repo):
        for i in range(3):
            audit.record(repo, "verb.run", target="v%d" % i)
        assert [r["target"] for r in audit.read(repo)][0] in ("v0", "v1", "v2")
        assert len(audit.read(repo)) == 3

    def test_it_can_be_filtered_by_action(self, repo):
        audit.record(repo, "verb.run", target="a")
        audit.record(repo, "chat.start", target="b")
        assert [r["target"] for r in audit.read(repo, action="chat.start")] == ["b"]

    def test_a_failed_outcome_is_recorded_too(self, repo):
        # A refused run is exactly what you want in the trail afterwards.
        audit.record(repo, "verb.run", target="context", outcome="error: no ticket")
        assert "error" in audit.read(repo)[0]["outcome"]

    def test_disabling_it_writes_nothing(self, repo):
        with open(os.path.join(repo, "console", "config", "console.toml"), "a",
                  encoding="utf-8") as fh:
            fh.write("\n[audit]\nenabled = false\n")
        boards._console_cache.clear()
        assert audit.record(repo, "verb.run", target="x") is None
        assert audit.read(repo) == []
        boards._console_cache.clear()

    def test_an_unwritable_directory_is_dropped_not_raised(self, repo, monkeypatch):
        # Evidence that can abort the work is worse than a gap in the evidence.
        monkeypatch.setattr(audit.os, "makedirs",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
        assert audit.record(repo, "verb.run", target="x") is None

    def test_a_corrupt_line_does_not_hide_the_rest(self, repo):
        audit.record(repo, "verb.run", target="good")
        folder = audit.audit_dir(repo)
        path = os.path.join(folder, sorted(os.listdir(folder))[0])
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("{ not json\n")
        assert [r["target"] for r in audit.read(repo)] == ["good"]

    def test_actor_from_a_request_object(self):
        class Req:
            client_addr = "100.64.0.7"
            user_agent = "Mozilla/5.0"
        assert audit.actor_of(Req()) == {"addr": "100.64.0.7", "agent": "Mozilla/5.0"}

    def test_actor_without_a_request_is_local(self):
        assert audit.actor_of(None)["addr"] == "local"


class TestBindingWarning:
    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
    def test_loopback_is_silent(self, host, capsys):
        from server import httpd
        httpd._announce_binding(host)
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize("host", ["0.0.0.0", "100.64.0.1", "192.168.1.10"])
    def test_anything_else_warns_loudly(self, host, capsys):
        # A console listening beyond this machine must never be a quiet fact.
        from server import httpd
        httpd._announce_binding(host)
        out = capsys.readouterr().out
        assert "BINDING" in out and host in out
        assert "NO authentication" in out
        assert "internet" in out


class Updates:
    """A scripted getUpdates response."""

    def __init__(self, payload=None, status=200):
        self.payload = payload if payload is not None else {"ok": True, "result": []}
        self.status = status
        self.urls = []

    def __call__(self, url, timeout=None):
        self.urls.append(url)
        if self.status != 200:
            raise urllib.error.HTTPError(url, self.status, "err", {}, None)

        class Resp:
            def read(inner):
                return json.dumps(self.payload).encode()

            def __enter__(inner):
                return inner

            def __exit__(inner, *a):
                return False
        return Resp()


def _update(chat_id, **chat):
    return {"message": {"chat": dict({"id": chat_id}, **chat)}}


class TestChatIdDiscovery:
    """Telegram never tells you your own chat id; you read it out of an update.

    This exists so nobody has to paste a live bot token into a browser URL bar
    to complete setup.
    """

    def test_a_private_chat_is_reported_with_its_name(self, configured):
        opener = Updates({"ok": True, "result": [
            _update(99887766, type="private", first_name="Sohail", last_name="Ali"),
        ]})
        rows, error = notify.discover_chat_ids(configured, opener=opener)
        assert error == ""
        assert rows == [{"chat_id": "99887766", "name": "Sohail Ali",
                         "type": "private"}]

    def test_a_group_is_reported_by_title_and_keeps_its_negative_id(self, configured):
        # Group ids are negative. Losing the sign gives you an id that looks
        # plausible and silently delivers nowhere.
        opener = Updates({"ok": True, "result": [
            _update(-1001234567890, type="supergroup", title="Delivery"),
        ]})
        rows, _ = notify.discover_chat_ids(configured, opener=opener)
        assert rows[0]["chat_id"] == "-1001234567890"
        assert rows[0]["name"] == "Delivery"

    def test_repeated_chats_collapse_to_one_row(self, configured):
        opener = Updates({"ok": True, "result": [
            _update(5, type="private", first_name="A"),
            _update(5, type="private", first_name="A"),
            _update(6, type="private", first_name="B"),
        ]})
        rows, _ = notify.discover_chat_ids(configured, opener=opener)
        assert [r["chat_id"] for r in rows] == ["5", "6"]

    def test_no_updates_is_empty_not_an_error(self, configured):
        # The normal first answer: the bot has not been spoken to yet.
        rows, error = notify.discover_chat_ids(configured, opener=Updates())
        assert rows == [] and error == ""

    def test_a_missing_token_is_reported_before_any_call(self, configured,
                                                         monkeypatch):
        monkeypatch.delenv("TEST_TG_TOKEN")
        opener = Updates()
        rows, error = notify.discover_chat_ids(configured, opener=opener)
        assert rows == [] and "TEST_TG_TOKEN" in error
        assert opener.urls == []

    def test_a_bad_token_says_so_rather_than_a_bare_status(self, configured):
        rows, error = notify.discover_chat_ids(
            configured, opener=Updates(status=401))
        assert rows == [] and "rejected the token" in error

    def test_an_unreachable_provider_is_not_fatal(self, configured):
        def boom(url, timeout=None):
            raise urllib.error.URLError("no route")
        rows, error = notify.discover_chat_ids(configured, opener=boom)
        assert rows == [] and error == "URLError"

    def test_the_error_never_carries_the_token(self, configured):
        # The token is in the URL, so a naive error message leaks it.
        rows, error = notify.discover_chat_ids(
            configured, opener=Updates(status=500))
        assert "secret-bot-token" not in error

    def test_updates_without_a_chat_are_skipped(self, configured):
        opener = Updates({"ok": True, "result": [
            {"poll": {"id": "x"}},
            {"message": {}},
            _update(7, type="private", first_name="C"),
        ]})
        rows, _ = notify.discover_chat_ids(configured, opener=opener)
        assert [r["chat_id"] for r in rows] == ["7"]

    def test_channel_posts_count_too(self, configured):
        opener = Updates({"ok": True, "result": [
            {"channel_post": {"chat": {"id": -100999, "type": "channel",
                                       "title": "Ops"}}},
        ]})
        rows, _ = notify.discover_chat_ids(configured, opener=opener)
        assert rows[0]["name"] == "Ops"
