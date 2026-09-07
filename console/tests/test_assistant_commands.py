"""T-004 C5/C7/C11: the fast-command table, the settings service, the CLI seam.

The matching half of dispatch is pure (`assistant_commands`), so most of this
file needs no repo, no server and no backend — which is the whole reason the
table returns a description instead of calling the machinery itself.

The rule these tests exist to defend is BR-1: `say` performs exactly one
fast-command match OR one `send`, never both, and never a second dispatch.
`TestBr1DispatchPurity` is the one to read first.
"""

import json
import os

import pytest

from server import assistant_commands as ac
from server import assistant_config


class TestNormalise:
    def test_strips_a_wake_word(self):
        assert ac.normalise("hey console, stop") == "stop"
        assert ac.normalise("Assistant: what's open") == "what's open"

    def test_strips_trailing_punctuation_and_folds_case(self):
        assert ac.normalise("What's Open?") == "what's open"

    def test_collapses_runs_of_whitespace(self):
        assert ac.normalise("  status   T-002  ") == "status t-002"

    def test_empty_input_is_empty_not_an_error(self):
        assert ac.normalise(None) == ""
        assert ac.normalise("   ") == ""


class TestCanonicalTicket:
    @pytest.mark.parametrize("raw,want", [
        ("t dash two", "T-002"),
        ("T-002", "T-002"),
        ("ticket 4", "T-004"),
        ("t 2", "T-002"),
        ("t-4", "T-004"),
        ("twenty", "T-020"),
        ("T-017", "T-017"),
    ])
    def test_spoken_and_written_forms_both_canonicalise(self, raw, want):
        assert ac.canonical_ticket(raw) == want

    @pytest.mark.parametrize("heard,want", [
        # The first of these is a REAL transcript: asked to say "status
        # ticket two", whisper base.en produced "Status ticket too". Without
        # homophone handling the command fell through to a model, which is
        # the wrong answer to a question the console can compute for free.
        ("too", "T-002"),
        ("to", "T-002"),
        ("won", "T-001"),
        ("for", "T-004"),
        ("fore", "T-004"),
        ("ate", "T-008"),
    ])
    def test_a_digit_a_speech_engine_misheard_still_resolves(self, heard, want):
        assert ac.canonical_ticket(heard) == want

    def test_a_real_word_beats_its_homophone(self):
        # "two" must not be reinterpreted by the "to" rule, which would be a
        # no-op here but would matter for any overlapping pair added later.
        assert ac.canonical_ticket("two") == "T-002"
        assert ac.canonical_ticket("four") == "T-004"

    def test_a_homophone_only_counts_inside_a_ticket_span(self):
        """The mapping is safe because of where it applies. A sentence that
        merely contains "to" is not a status request."""
        assert ac.match("what do I need to do") is None
        assert ac.match("status of the migration") is None

    def test_create_ticket_for_is_not_read_as_the_number_four(self):
        # "for" is a connector in this row and a homophone in the other. The
        # rows must not collide.
        cmd = ac.match("create ticket for the login bug")
        assert cmd.name == "create_ticket"
        assert cmd.args == {"title": "the login bug"}

    def test_a_span_with_no_number_is_none_not_a_guess(self):
        # The caller falls through to the model on None. Inventing an id here
        # would send "status of the migration" to a ticket that never existed.
        assert ac.canonical_ticket("the migration") is None
        assert ac.canonical_ticket("") is None
        assert ac.canonical_ticket(None) is None

    def test_prefix_and_width_are_configurable(self):
        assert ac.canonical_ticket("7", prefix="CC-T", width=3) == "CC-T007"


class TestWholeUtteranceOnly:
    """The safety property. A substring rule would make "stop the server"
    interrupt the turn instead of reaching the model."""

    @pytest.mark.parametrize("text", [
        "stop the server",
        "cancel my subscription please",
        "can you mute the alerts in prod",
        "i will remember the password myself",
        "what's open in the browser right now",
        "status of the migration",
    ])
    def test_a_command_word_inside_a_sentence_does_not_fire(self, text):
        cmd = ac.match(text)
        assert cmd is None or cmd.name == "send", (
            "%r matched %r — a mid-sentence command word must reach the model"
            % (text, cmd))

    @pytest.mark.parametrize("text,name", [
        ("stop", "interrupt"),
        ("cancel", "interrupt"),
        ("interrupt", "interrupt"),
        ("mute", "mute"),
        ("unmute", "unmute"),
        ("new chat", "new_chat"),
        ("start over", "new_chat"),
        ("reset", "new_chat"),
        ("what's open", "digest"),
        ("standup", "digest"),
        ("copy that", "copy_last"),
    ])
    def test_the_bare_utterance_does_fire(self, text, name):
        assert ac.match(text).name == name


class TestRows:
    def test_status_resolves_a_spoken_ticket_id(self):
        cmd = ac.match("status t dash two")
        assert (cmd.name, cmd.args) == ("status", {"ticket": "T-002"})

    def test_status_honours_the_configured_prefix(self):
        cmd = ac.match("status ticket 7", ticket_prefix="CC-T")
        assert cmd.args == {"ticket": "CC-T007"}

    def test_use_backend_maps_a_spoken_name_to_an_id(self):
        assert ac.match("use cursor").args == {"backend": "cursor-agent"}
        assert ac.match("switch to lm studio").args == {"backend": "lm-studio"}

    def test_an_unknown_backend_name_reaches_the_model(self):
        # Better the model says "I don't know that backend" than we silently
        # map it to something plausible.
        assert ac.match("use banana") is None

    def test_create_ticket_keeps_the_title_in_its_original_case(self):
        cmd = ac.match("create a ticket for Fix the Tray Icon")
        assert cmd.name == "create_ticket"
        assert cmd.args == {"title": "Fix the Tray Icon"}

    def test_remember_keeps_the_fact_in_its_original_case(self):
        cmd = ac.match("remember that Sohail prefers terse replies")
        assert cmd.args == {"fact": "Sohail prefers terse replies"}

    def test_a_title_that_is_only_whitespace_falls_through(self):
        assert ac.match("create ticket for    ") is None

    def test_plain_text_is_not_a_command(self):
        assert ac.match("why is the tray icon grey?") is None


class TestRewrites:
    """Two rows have no local handler: they reshape the text and still perform
    exactly ONE send, so BR-1 holds."""

    def test_do_rewrite_is_a_send_carrying_the_do_skill(self):
        cmd = ac.match("fix the failing sidecar test")
        assert cmd.name == "send"
        assert cmd.args == {"skill": "do"}
        assert cmd.text == "fix the failing sidecar test"

    def test_screenshot_rewrite_names_the_target_and_the_question(self):
        cmd = ac.match("take a screenshot of Notepad and tell me the error")
        assert cmd.name == "send"
        assert "Notepad" in cmd.text, "the window title keeps its own case"
        assert "tell me the error" in cmd.text

    def test_bare_screenshot_gets_sensible_defaults(self):
        cmd = ac.match("screenshot")
        assert cmd.name == "send"
        assert "the whole screen" in cmd.text
        assert "describe what you see" in cmd.text

    def test_the_screenshot_rewrite_forbids_guessing(self):
        # If the shell is not running the model must say so, not invent a
        # plausible screen. The instruction carries that rule.
        cmd = ac.match("screenshot")
        assert "not running" in cmd.text and "instead of guessing" in cmd.text


class TestBr1DispatchPurity:
    """A handler returns a spoken STRING. If a handler could return another
    command, `say` could dispatch twice off one utterance — the thing BR-1
    forbids. These tests pin the shape that makes that impossible."""

    def test_a_command_is_never_returned_for_handler_output(self):
        for text in ("stop", "mute", "what's open", "copy that"):
            cmd = ac.match(text)
            assert isinstance(cmd, ac.Command)
            assert cmd.text is None, (
                "a handled command carries no send text, so `say` cannot "
                "both run a handler and send")

    def test_only_send_commands_carry_text(self):
        assert ac.match("do something").text is not None
        assert ac.match("screenshot").text is not None

    def test_fast_command_shaped_model_output_never_re_enters_dispatch(self):
        """`match` is only ever applied to the USER's utterance. Feeding it a
        reply that happens to read like a command is still just matching — it
        returns a description nobody executes, because `say` calls `match`
        once, before the send, and never on the reply."""
        reply = "stop"
        cmd = ac.match(reply)
        assert cmd.name == "interrupt"          # it would match, in isolation
        # ...which is exactly why the reply path must not call `match`. The
        # guard is structural: `assistant_feature.say` calls it once, on
        # `body["text"]`. This test documents the invariant that keeps the
        # single call site honest.
        source = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "server", "features", "assistant_feature.py"), encoding="utf-8").read()
        assert source.count("assistant_commands.match(") == 1


class TestSettings:
    def test_defaults_apply_with_no_files_at_all(self, tmp_path):
        s = assistant_config.settings(str(tmp_path))
        assert s["mode"] == "default", "plan mode would refuse every write"
        assert s["backend"] == "", "resolved at use time, never hardcoded"
        assert s["ticket_prefix"] == "T-"

    def test_the_committed_file_overrides_a_default(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "assistant.toml").write_text(
            '[assistant]\nreply_chars = 120\n', encoding="utf-8")
        assert assistant_config.settings(str(tmp_path))["reply_chars"] == 120

    def test_this_machine_overrides_the_committed_file(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "assistant.toml").write_text(
            '[assistant]\nreply_chars = 120\n', encoding="utf-8")
        assistant_config.update(str(tmp_path), {"reply_chars": 999})
        assert assistant_config.settings(str(tmp_path))["reply_chars"] == 999

    def test_a_write_never_touches_the_committed_file(self, tmp_path):
        """Picking a backend on one laptop must not appear in everyone's diff."""
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        committed = cfg / "assistant.toml"
        committed.write_text('[assistant]\nbackend = ""\n', encoding="utf-8")
        before = committed.read_text(encoding="utf-8")
        assistant_config.update(str(tmp_path), {"backend": "claude"},
                                installed_backends=["claude"])
        assert committed.read_text(encoding="utf-8") == before
        override = tmp_path / "console" / ".cache" / "assistant" / "settings.json"
        assert json.loads(override.read_text(encoding="utf-8")) == {"backend": "claude"}

    def test_an_uninstalled_backend_is_refused_and_nothing_is_written(self, tmp_path):
        with pytest.raises(ValueError, match="not enabled and installed"):
            assistant_config.update(str(tmp_path), {"backend": "ollama"},
                                    installed_backends=["claude"])
        override = tmp_path / "console" / ".cache" / "assistant" / "settings.json"
        assert not override.exists()

    def test_a_key_that_is_not_writable_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="not a writable setting"):
            assistant_config.update(str(tmp_path), {"vision_models": ["x"]})

    def test_an_unknown_key_is_refused_rather_than_silently_stored(self, tmp_path):
        # A typo that got stored would look like it worked forever.
        with pytest.raises(ValueError, match="not a writable setting"):
            assistant_config.update(str(tmp_path), {"bakcend": "claude"})

    def test_a_half_wrong_patch_stores_nothing(self, tmp_path):
        with pytest.raises(ValueError):
            assistant_config.update(str(tmp_path),
                                    {"reply_chars": 50, "nope": 1})
        assert assistant_config.settings(str(tmp_path))["reply_chars"] == 400

    @pytest.mark.parametrize("value,want", [
        (True, True), ("true", True), ("on", True),
        (False, False), ("false", False), ("off", False),
    ])
    def test_booleans_coerce_from_the_strings_a_form_sends(self, tmp_path, value, want):
        assistant_config.update(str(tmp_path), {"speak": value})
        assert assistant_config.settings(str(tmp_path))["speak"] is want

    def test_a_nonsense_boolean_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="must be true or false"):
            assistant_config.update(str(tmp_path), {"speak": "maybe"})

    @pytest.mark.parametrize("key", ["session_idle_minutes", "reply_chars"])
    def test_a_non_positive_number_is_refused(self, tmp_path, key):
        with pytest.raises(ValueError, match="at least 1"):
            assistant_config.update(str(tmp_path), {key: 0})

    def test_a_malformed_committed_file_falls_back_to_defaults(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "assistant.toml").write_text("[assistant\nbroken", encoding="utf-8")
        # A bad config must not take the Assistant down.
        assert assistant_config.settings(str(tmp_path))["mode"] == "default"

    def test_a_corrupt_override_file_falls_back_too(self, tmp_path):
        d = tmp_path / "console" / ".cache" / "assistant"
        d.mkdir(parents=True)
        (d / "settings.json").write_text("{not json", encoding="utf-8")
        assert assistant_config.settings(str(tmp_path))["reply_chars"] == 400


class _FakeBackend:
    def __init__(self, installed):
        self.installed = installed


class TestBackendResolution:
    def test_an_explicit_request_wins(self, tmp_path):
        reg = {"claude": _FakeBackend(True), "ollama": _FakeBackend(True)}
        assert assistant_config.resolve_backend(
            str(tmp_path), reg, "claude") == "claude"

    def test_the_stored_choice_is_used_when_nothing_is_requested(self, tmp_path):
        reg = {"claude": _FakeBackend(True), "ollama": _FakeBackend(True)}
        assistant_config.update(str(tmp_path), {"backend": "claude"},
                                installed_backends=["claude", "ollama"])
        assert assistant_config.resolve_backend(str(tmp_path), reg) == "claude"

    def test_local_first_when_nothing_is_stored(self, tmp_path):
        reg = {"claude": _FakeBackend(True), "ollama": _FakeBackend(True)}
        assert assistant_config.resolve_backend(str(tmp_path), reg) == "ollama"

    def test_an_uninstalled_stored_choice_is_skipped(self, tmp_path):
        """The stored backend may have been uninstalled since; falling back
        beats failing on a machine that has a perfectly good alternative."""
        reg = {"claude": _FakeBackend(True), "ollama": _FakeBackend(False)}
        assistant_config.update(str(tmp_path), {"backend": "ollama"})
        assert assistant_config.resolve_backend(str(tmp_path), reg) == "claude"

    def test_nothing_installed_says_so_plainly(self, tmp_path):
        reg = {"claude": _FakeBackend(False)}
        with pytest.raises(ValueError, match="no enabled\\+installed backend"):
            assistant_config.resolve_backend(str(tmp_path), reg)
