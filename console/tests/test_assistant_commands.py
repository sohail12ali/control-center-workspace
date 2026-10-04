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


class TestTrayClickSetting:
    """T-009. One left-click on the tray icon has a meaning, and this is where
    it is chosen."""

    def test_the_default_is_the_state_aware_one(self, tmp_path):
        assert assistant_config.settings(str(tmp_path))["tray_click_action"] == "listen"

    @pytest.mark.parametrize("value", ["listen", "show", "hands_free"])
    def test_each_supported_action_round_trips(self, tmp_path, value):
        assistant_config.update(str(tmp_path), {"tray_click_action": value})
        assert assistant_config.settings(str(tmp_path))["tray_click_action"] == value

    def test_an_unknown_action_is_refused_and_names_the_valid_ones(self, tmp_path):
        # Stored, it would leave the icon doing nothing while the setting
        # looked as if it had been accepted.
        with pytest.raises(ValueError, match="listen, show, hands_free"):
            assistant_config.update(str(tmp_path), {"tray_click_action": "sing"})
        assert assistant_config.settings(str(tmp_path))["tray_click_action"] == "listen"

    def test_the_committed_file_ships_the_same_default(self, tmp_path):
        import server.tomlio as tomlio
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shipped = tomlio.load(os.path.join(
            root, "config", "assistant.toml"))["assistant"]
        assert shipped["tray_click_action"] == assistant_config.DEFAULTS["tray_click_action"]


class TestListeningSettings:
    """T-010. The two limits on a take, and which model transcribes it."""

    def test_the_cap_came_down_to_something_bearable(self, tmp_path):
        # It was 20s, and a detector that never saw silence cost that on
        # every take. The default is part of the fix, not decoration.
        s = assistant_config.settings(str(tmp_path))
        assert s["listen_max_seconds"] == 12
        assert s["listen_silence_ms"] == 700
        assert s["stt_model"] == "base.en"

    @pytest.mark.parametrize("key,value", [
        ("listen_max_seconds", 1), ("listen_max_seconds", 121),
        ("listen_silence_ms", 199), ("listen_silence_ms", 5001),
    ])
    def test_a_limit_outside_the_usable_range_is_refused(self, tmp_path, key, value):
        with pytest.raises(ValueError, match="between"):
            assistant_config.update(str(tmp_path), {key: value})

    def test_the_wake_pipeline_has_the_dials_the_shell_reads(self, tmp_path):
        # T-019. The shell's hands_free::fetch_policy asks for these by name
        # and falls back to its own cautious copies when they are missing —
        # so a rename here is a silent behaviour change there.
        s = assistant_config.settings(str(tmp_path))
        assert s["listen_first_pause_ms"] == 1500
        assert s["listen_preroll_ms"] == 1000
        assert s["wake_sensitivity"] == 0.5

    @pytest.mark.parametrize("key,value", [
        ("listen_first_pause_ms", 199), ("listen_first_pause_ms", 5001),
        ("listen_preroll_ms", -1), ("listen_preroll_ms", 3001),
        ("wake_sensitivity", -0.1), ("wake_sensitivity", 1.1),
    ])
    def test_a_wake_dial_outside_its_range_is_refused(self, tmp_path, key, value):
        with pytest.raises(ValueError, match="between"):
            assistant_config.update(str(tmp_path), {key: value})

    def test_a_sensitivity_posted_as_text_stays_a_number(self, tmp_path):
        # A slider posts "0.7". Stored as a string it would compare against
        # the range as a string, and the shell would read a float back as 0.
        assistant_config.update(str(tmp_path), {"wake_sensitivity": "0.7"})
        stored = assistant_config.settings(str(tmp_path))["wake_sensitivity"]
        assert isinstance(stored, float) and abs(stored - 0.7) < 1e-9

    def test_a_sensitivity_that_is_not_a_number_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="number"):
            assistant_config.update(str(tmp_path), {"wake_sensitivity": "loud"})

    @pytest.mark.parametrize("value", ["../../.env", "a/b", "..", "", "  "])
    def test_a_model_name_cannot_be_a_path(self, tmp_path, value):
        # It becomes `ggml-{name}.bin` in the shell, so this is the only place
        # that can stop it being a traversal.
        with pytest.raises(ValueError, match="model name"):
            assistant_config.update(str(tmp_path), {"stt_model": value})

    def test_a_model_name_round_trips(self, tmp_path):
        assistant_config.update(str(tmp_path), {"stt_model": "tiny.en"})
        assert assistant_config.settings(str(tmp_path))["stt_model"] == "tiny.en"

    def test_the_committed_file_ships_the_same_three(self, tmp_path):
        import server.tomlio as tomlio
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shipped = tomlio.load(os.path.join(
            root, "config", "assistant.toml"))["assistant"]
        for key in ("listen_max_seconds", "listen_silence_ms", "stt_model"):
            assert shipped[key] == assistant_config.DEFAULTS[key], key


class TestHandsFreeSettings:
    """T-008. These four decide how an always-on microphone behaves, so the
    thing worth testing is that the shipped answer is the cautious one and
    that a setting which would weaken it has to be asked for explicitly."""

    def test_the_defaults_are_the_cautious_ones(self, tmp_path):
        s = assistant_config.settings(str(tmp_path))
        assert s["hands_free_require_wake"] is True, (
            "unaddressed speech must not be sent by default")
        assert s["hands_free_listen_while_speaking"] is False, (
            "on speakers the assistant would answer its own voice")
        assert s["hands_free_max_minutes"] >= 1, "it must stop on its own"
        assert len(s["hands_free_wake_word"]) >= 2

    def test_turning_the_wake_word_off_round_trips(self, tmp_path):
        # It is a legitimate choice with headphones on — it just has to be
        # a choice, made here, rather than the default.
        assistant_config.update(str(tmp_path), {"hands_free_require_wake": "off"})
        assert assistant_config.settings(
            str(tmp_path))["hands_free_require_wake"] is False

    def test_a_too_short_wake_word_is_refused(self, tmp_path):
        # A one-letter wake word matches almost anything, which is the same as
        # having none while looking like it has one.
        with pytest.raises(ValueError, match="two characters"):
            assistant_config.update(str(tmp_path), {"hands_free_wake_word": "c"})

    def test_a_wake_word_is_stored_trimmed(self, tmp_path):
        assistant_config.update(str(tmp_path), {"hands_free_wake_word": "  jarvis "})
        assert assistant_config.settings(
            str(tmp_path))["hands_free_wake_word"] == "jarvis"

    def test_the_time_cap_cannot_be_switched_off_with_a_zero(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assistant_config.update(str(tmp_path), {"hands_free_max_minutes": 0})

    def test_the_committed_file_ships_the_same_answers(self, tmp_path):
        """`assistant.toml` documents these; if it drifted from DEFAULTS the
        documentation would describe a configuration nobody runs."""
        import server.tomlio as tomlio
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shipped = tomlio.load(os.path.join(
            root, "config", "assistant.toml"))["assistant"]
        for key in ("hands_free_require_wake", "hands_free_wake_word",
                    "hands_free_listen_while_speaking", "hands_free_max_minutes"):
            assert shipped[key] == assistant_config.DEFAULTS[key], key

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
    """Enough of `agent_backends.Backend` for resolution to run.

    `auth` matters as much as `installed` now: it is what decides whether a
    row is asked the two preflight questions (is a model loaded, does it do
    tools). `"key"` is the default here so the existing cases keep testing
    what they were written to test — plain ordering — and the preflight cases
    below opt in with `auth="none"`.
    """

    def __init__(self, installed, auth="key", label="", bid=""):
        self.installed = installed
        self.auth = auth
        self.id = bid
        self.label = label or bid or "a backend"

    @property
    def unavailable_reason(self):
        return "" if self.installed else "%s is not available" % self.label


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
        reg = {"claude": _FakeBackend(False, bid="claude")}
        with pytest.raises(ValueError, match="no backend can hold a conversation"):
            assistant_config.resolve_backend(str(tmp_path), reg)

    def test_the_failure_names_every_candidate_and_why(self, tmp_path):
        """"Nothing works" is not a diagnosis. The message has to carry the
        reason each one was passed over, or the next step is reading source."""
        reg = {"claude": _FakeBackend(False, bid="claude", label="Claude Code"),
               "ollama": _FakeBackend(False, bid="ollama", label="Ollama")}
        with pytest.raises(ValueError) as caught:
            assistant_config.resolve_backend(str(tmp_path), reg)
        message = str(caught.value)
        assert "Claude Code is not available" in message
        assert "Ollama is not available" in message

    def test_openrouter_is_preferred_over_a_cli(self, tmp_path):
        """The default-order fix. A conversation should not go through a
        coding CLI when a hosted API row is available: measured at 2-300s a
        turn on `claude` versus about a second on a small hosted model."""
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "openrouter": _FakeBackend(True, bid="openrouter")}
        assert assistant_config.resolve_backend(str(tmp_path), reg) == "openrouter"

    def test_a_skipped_candidate_reports_why(self, tmp_path):
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "ollama": _FakeBackend(False, bid="ollama", label="Ollama")}
        skipped = []
        chosen = assistant_config.resolve_backend(str(tmp_path), reg,
                                                  report=skipped)
        assert chosen == "claude"
        assert skipped == [("ollama", "Ollama is not available")]

    def test_a_backend_not_in_the_registry_is_not_chosen(self, tmp_path):
        """A stored choice can name a backend that has since been deleted from
        agents.toml. That must fall through, not raise a KeyError."""
        reg = {"claude": _FakeBackend(True, bid="claude")}
        assistant_config.update(str(tmp_path), {"backend": "gone"})
        assert assistant_config.resolve_backend(str(tmp_path), reg) == "claude"


class TestWorkGoesLocalFirstToo:
    """`work_backend` had no chain: it was one id set by hand, and `delegate`
    refused outright when empty. In practice that pinned work to whichever CLI
    was chosen once — so a machine with two local runtimes installed sent every
    task to a hosted coding agent."""

    def _local(self, resident, caps, monkeypatch):
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: resident)
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities",
                            lambda *a, **kw: caps)

    def test_a_local_runtime_is_preferred_over_a_cli(self, tmp_path, monkeypatch):
        self._local({"qwen3:8b"}, {"qwen3:8b": {"tool_use": True,
                                                "context": 32768}}, monkeypatch)
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "ollama": _FakeBackend(True, auth="none", bid="ollama")}
        assert assistant_config.resolve_work_backend(
            str(tmp_path), reg) == "ollama"

    def test_a_pinned_work_backend_still_wins(self, tmp_path, monkeypatch):
        """An explicit choice is an explicit choice."""
        self._local({"qwen3:8b"}, {}, monkeypatch)
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "ollama": _FakeBackend(True, auth="none", bid="ollama")}
        assistant_config.update(str(tmp_path), {"work_backend": "claude"})
        assert assistant_config.resolve_work_backend(
            str(tmp_path), reg) == "claude"

    def test_a_model_that_cannot_call_tools_is_not_sent_work(self, tmp_path,
                                                             monkeypatch):
        """It can still talk. It cannot change a line of code."""
        self._local({"deepseek-coder"},
                    {"deepseek-coder": {"tool_use": False, "context": 32768}},
                    monkeypatch)
        backend = _FakeBackend(True, auth="none", bid="ollama", label="Ollama")
        ok, why = assistant_config.work_ready(str(tmp_path), backend)
        assert not ok and "tool calling" in why

    def test_a_model_with_no_room_to_work_is_not_sent_work(self, tmp_path,
                                                           monkeypatch):
        """A work turn carries a file, an edit, a command's output and often a
        test log. Below ~16k that stops fitting, and a model that has forgotten
        the start of its own task reads as one that will not follow
        instructions."""
        self._local({"tiny-2k"}, {"tiny-2k": {"tool_use": True,
                                              "context": 4096}}, monkeypatch)
        backend = _FakeBackend(True, auth="none", bid="lm-studio",
                               label="LM Studio")
        ok, why = assistant_config.work_ready(str(tmp_path), backend)
        assert not ok
        assert "16k of context" in why
        # And it is explicitly still fine for the other role.
        assert "fine for talking" in why
        talk_ok, _ = assistant_config.talk_ready(str(tmp_path), backend)
        assert talk_ok

    def test_one_capable_resident_model_is_enough(self, tmp_path, monkeypatch):
        """LM Studio can hold several; the question is whether ANY of them can
        do the job, not whether all of them can."""
        self._local({"tiny-2k", "qwen3-4b"},
                    {"tiny-2k": {"tool_use": True, "context": 4096},
                     "qwen3-4b": {"tool_use": True, "context": 262144}},
                    monkeypatch)
        backend = _FakeBackend(True, auth="none", bid="lm-studio")
        assert assistant_config.work_ready(str(tmp_path), backend) == (True, "")

    def test_a_runtime_that_describes_nothing_gets_the_benefit(self, tmp_path,
                                                               monkeypatch):
        """Ollama reports no capabilities at all. Refusing on silence would
        rule it out permanently, which is not the intent."""
        self._local({"qwen3:8b"}, {}, monkeypatch)
        backend = _FakeBackend(True, auth="none", bid="ollama")
        assert assistant_config.work_ready(str(tmp_path), backend) == (True, "")

    def test_a_broken_row_is_skipped_rather_than_fatal(self, tmp_path,
                                                       monkeypatch):
        """One malformed backend must not stop the chain reaching the next."""
        class Exploding:
            id = "boom"
            label = "Boom"
            auth = ""

            @property
            def installed(self):
                raise ValueError("no session_args")

        reg = {"boom": Exploding(), "claude": _FakeBackend(True, bid="claude")}
        # Named in the chain, or it would never be asked about — which is
        # itself the behaviour: the chain only consults ids it is given.
        assistant_config.update(str(tmp_path), {"backend_chain": "boom,claude"})
        skipped = []
        assert assistant_config.resolve_work_backend(
            str(tmp_path), reg, report=skipped) == "claude"
        assert skipped and "no session_args" in skipped[0][1]


class TestTheChainCanBeMadeStrict:
    """`backend_chain` is how "never a CLI" is said without a second setting
    to mean it: name the backends you accept, and a role with none of them
    available FAILS and reports what it tried."""

    def test_a_named_chain_excludes_everything_else(self, tmp_path, monkeypatch):
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: set())
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities",
                            lambda *a, **kw: {})
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "ollama": _FakeBackend(True, auth="none", bid="ollama",
                                      label="Ollama")}
        assistant_config.update(str(tmp_path), {"backend_chain": "ollama"})
        # Ollama is up but empty, and claude is deliberately unreachable.
        for resolve in (assistant_config.resolve_backend,
                        assistant_config.resolve_work_backend):
            with pytest.raises(ValueError) as caught:
                resolve(str(tmp_path), reg)
            assert "no model loaded" in str(caught.value)

    def test_a_named_chain_is_honoured_in_its_own_order(self, tmp_path):
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "cursor-agent": _FakeBackend(True, bid="cursor-agent")}
        assistant_config.update(str(tmp_path),
                                {"backend_chain": "cursor-agent,claude"})
        assert assistant_config.resolve_backend(
            str(tmp_path), reg) == "cursor-agent"

    def test_an_empty_chain_falls_back_to_the_builtin_order(self, tmp_path):
        reg = {"claude": _FakeBackend(True, bid="claude"),
               "openrouter": _FakeBackend(True, bid="openrouter")}
        assistant_config.update(str(tmp_path), {"backend_chain": "   "})
        assert assistant_config.resolve_backend(
            str(tmp_path), reg) == "openrouter"


class TestTalkReadyPreflight:
    """Reachable is not usable.

    Every case here is a real failure from `console/.cache/agent-chats/`: a
    server answering with nothing loaded, and a resident model that cannot
    call a tool. Both got past the old `installed` check and then failed
    mid-turn, which reads as a broken assistant rather than a bad pick.
    """

    def test_a_keyed_provider_is_not_interrogated(self, tmp_path, monkeypatch):
        """No residency to report and tools by construction — so no requests.
        This is also what keeps OpenRouter off the two extra round trips."""
        def boom(*a, **kw):
            raise AssertionError("a keyed provider must not be probed")
        monkeypatch.setattr(assistant_config.model_catalog, "loaded", boom)
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities", boom)
        ok, why = assistant_config.talk_ready(
            str(tmp_path), _FakeBackend(True, auth="key", bid="openrouter"))
        assert (ok, why) == (True, "")

    def test_a_running_server_with_nothing_loaded_is_skipped(self, tmp_path,
                                                             monkeypatch):
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: set())
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities",
                            lambda *a, **kw: {})
        ok, why = assistant_config.talk_ready(
            str(tmp_path),
            _FakeBackend(True, auth="none", bid="lm-studio", label="LM Studio"))
        assert not ok
        assert "no model loaded" in why

    def test_a_resident_model_without_tools_is_skipped(self, tmp_path,
                                                       monkeypatch):
        """`deepseek-coder` — reachable, loaded, and "does not support tools",
        which makes every verb the Assistant has unreachable."""
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: {"deepseek-coder"})
        monkeypatch.setattr(
            assistant_config.model_catalog, "capabilities",
            lambda *a, **kw: {"deepseek-coder": {"tool_use": False}})
        ok, why = assistant_config.talk_ready(
            str(tmp_path),
            _FakeBackend(True, auth="none", bid="ollama", label="Ollama"))
        assert not ok
        assert "tool calling" in why

    def test_a_resident_tool_capable_model_is_ready(self, tmp_path, monkeypatch):
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: {"qwen3:4b"})
        monkeypatch.setattr(
            assistant_config.model_catalog, "capabilities",
            lambda *a, **kw: {"qwen3:4b": {"tool_use": True}})
        ok, why = assistant_config.talk_ready(
            str(tmp_path), _FakeBackend(True, auth="none", bid="ollama"))
        assert (ok, why) == (True, "")

    def test_a_server_that_reports_nothing_gets_the_benefit_of_the_doubt(
            self, tmp_path, monkeypatch):
        """`None` is "cannot say", not "nothing loaded" — and the tool flag is
        documented as a hint. Refusing on silence would rule out every
        runtime that does not publish a residency endpoint."""
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: None)
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities",
                            lambda *a, **kw: {})
        ok, why = assistant_config.talk_ready(
            str(tmp_path), _FakeBackend(True, auth="none", bid="ollama"))
        assert (ok, why) == (True, "")

    def test_the_chain_falls_past_a_dead_local_to_a_hosted_one(self, tmp_path,
                                                               monkeypatch):
        """The whole point, end to end: Ollama running but empty, LM Studio
        unreachable, and the answer is OpenRouter rather than a silent CLI."""
        monkeypatch.setattr(assistant_config.model_catalog, "loaded",
                            lambda *a, **kw: set())
        monkeypatch.setattr(assistant_config.model_catalog, "capabilities",
                            lambda *a, **kw: {})
        reg = {
            "ollama": _FakeBackend(True, auth="none", bid="ollama",
                                   label="Ollama"),
            "lm-studio": _FakeBackend(False, auth="none", bid="lm-studio",
                                      label="LM Studio"),
            "openrouter": _FakeBackend(True, auth="key", bid="openrouter"),
            "claude": _FakeBackend(True, bid="claude"),
        }
        skipped = []
        assert assistant_config.resolve_backend(
            str(tmp_path), reg, report=skipped) == "openrouter"
        assert [b for b, _why in skipped] == ["ollama", "lm-studio"]
