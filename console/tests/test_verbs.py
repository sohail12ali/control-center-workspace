"""Verb registry.

Two properties carry the design: a bad handler path fails at **load**, not at
run time, and a verb's gates travel with its definition so every caller enforces
them identically without reimplementing any of them.
"""

import os

import pytest

from server import tickets, verbs

VERBS = """\
[[verb]]
id = "plain"
label = "Plain"
handler = "verb_handlers.open_todos"

[[verb]]
id = "needs-ticket"
label = "Needs a ticket"
handler = "verb_handlers.ticket_blockers"
needs_ticket = true

[[verb]]
id = "dangerous"
label = "Mutates things"
handler = "verb_handlers.ticket_artifacts"
needs_ticket = true
needs_confirm = true

[[verb]]
id = "build-lane-only"
label = "Only in progress"
handler = "verb_handlers.ticket_artifacts"
needs_ticket = true
lanes = ["in-progress"]

[[verb]]
id = "tickets-only"
label = "Only ticket boards"
handler = "verb_handlers.ticket_artifacts"
needs_ticket = true
kinds = ["tickets"]

[[verb]]
id = "switched-off"
label = "Disabled"
handler = "verb_handlers.ticket_artifacts"
enabled = false
"""


def _write_verbs(repo, text=VERBS):
    path = os.path.join(repo, "console", "config", "verbs.toml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    verbs._cache.clear()
    return repo


@pytest.fixture
def wired(repo):
    _write_verbs(repo)
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()


class TestRegistry:
    def test_lists_enabled_rows(self, wired):
        assert set(verbs.registry(wired)) == {
            "plain", "needs-ticket", "dangerous", "build-lane-only", "tickets-only"}

    def test_disabled_row_is_absent(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.get(wired, "switched-off")

    def test_unknown_verb_error_names_what_exists(self, wired):
        with pytest.raises(verbs.VerbError) as exc:
            verbs.get(wired, "ghost")
        assert "plain" in str(exc.value)

    def test_missing_config_is_an_empty_registry_not_a_crash(self, repo):
        verbs._cache.clear()
        assert verbs.registry(repo) == {}

    def test_row_without_an_id_is_refused(self, repo):
        _write_verbs(repo, '[[verb]]\nlabel = "x"\nhandler = "verb_handlers.open_todos"\n')
        with pytest.raises(verbs.VerbError):
            verbs.registry(repo, force=True)

    def test_row_without_a_handler_is_refused(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "x"\nlabel = "x"\n')
        with pytest.raises(verbs.VerbError):
            verbs.registry(repo, force=True)


class TestHandlerResolution:
    """A verb that only breaks when someone runs it is a broken verb pretending
    to work, so every one of these must fail at registry load."""

    def test_missing_module_fails_at_load(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "x"\nlabel = "x"\n'
                           'handler = "no_such_module.thing"\n')
        with pytest.raises(verbs.VerbError) as exc:
            verbs.registry(repo, force=True)
        assert "x" in str(exc.value)

    def test_missing_function_fails_at_load(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "x"\nlabel = "x"\n'
                           'handler = "verb_handlers.no_such_function"\n')
        with pytest.raises(verbs.VerbError):
            verbs.registry(repo, force=True)

    def test_handler_that_is_not_a_dotted_path_fails_at_load(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "x"\nlabel = "x"\nhandler = "bare"\n')
        with pytest.raises(verbs.VerbError):
            verbs.registry(repo, force=True)

    def test_a_non_callable_attribute_fails_at_load(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "x"\nlabel = "x"\n'
                           'handler = "verb_handlers.context_mod"\n')
        with pytest.raises(verbs.VerbError):
            verbs.registry(repo, force=True)


class TestGates:
    def test_needs_ticket_refuses_without_one(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "needs-ticket")

    def test_needs_confirm_refuses_without_confirmation(self, wired):
        # The whole point: a stray click or a hallucinated tool call must not
        # be able to trigger a mutating verb.
        with pytest.raises(verbs.VerbError) as exc:
            verbs.run(wired, "dangerous", ticket="CC-T001")
        assert "confirm" in str(exc.value)

    def test_needs_confirm_runs_when_confirmed(self, wired):
        assert verbs.run(wired, "dangerous", ticket="CC-T001", confirm=True)

    def test_unknown_ticket_is_refused(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "needs-ticket", ticket="CC-T999")

    def test_lane_restriction_is_enforced(self, wired):
        with pytest.raises(verbs.VerbError) as exc:
            verbs.run(wired, "build-lane-only", ticket="CC-T001")
        assert "lane" in str(exc.value)

        tickets.move(wired, "CC-T001", "in-progress")
        assert verbs.run(wired, "build-lane-only", ticket="CC-T001") is not None

    def test_kind_restriction_allows_a_matching_board(self, wired):
        assert verbs.run(wired, "tickets-only", ticket="CC-T001") is not None

    def test_a_verb_with_no_ticket_requirement_runs_bare(self, wired):
        assert verbs.run(wired, "plain") is not None


class TestListing:
    def test_reports_availability_and_why_not(self, wired):
        rows = {r["id"]: r for r in verbs.list_verbs(wired, ticket="CC-T001")}
        assert rows["tickets-only"]["available"] is True
        assert rows["build-lane-only"]["available"] is False
        assert "lane" in rows["build-lane-only"]["reason"]

    def test_confirmation_is_not_treated_as_unavailability(self, wired):
        # A board should render the button and ask on click, not grey it out —
        # confirmation is an act the caller performs, not a state of the world.
        rows = {r["id"]: r for r in verbs.list_verbs(wired, ticket="CC-T001")}
        assert rows["dangerous"]["available"] is True
        assert rows["dangerous"]["needs_confirm"] is True

    def test_listing_without_a_ticket_does_not_crash_on_ticket_verbs(self, wired):
        rows = {r["id"]: r for r in verbs.list_verbs(wired)}
        assert rows["needs-ticket"]["available"] is False


class TestDispatch:
    def test_extra_args_reach_the_handler(self, repo):
        _write_verbs(repo, '[[verb]]\nid = "tele"\nlabel = "t"\n'
                           'handler = "verb_handlers.telemetry_summary"\n')
        out = verbs.run(repo, "tele", args={"by": "model"})
        assert out["group"] == "model"

    def test_an_argument_typo_is_refused_by_name(self, wired):
        # No handler takes **kwargs, so `by=modle` cannot be silently ignored
        # and answered with a default-grouped result that looks right.
        with pytest.raises(verbs.VerbError) as exc:
            verbs.run(wired, "plain", args={"nonsense": 1})
        assert "plain" in str(exc.value)

    def test_a_crash_inside_a_handler_is_not_relabelled_as_bad_arguments(self, repo):
        # Regression: wrapping the call in `except TypeError` turned any
        # TypeError raised *inside* a handler into "bad arguments", pointing
        # the reader at the call site instead of the actual fault.
        _write_verbs(repo, '[[verb]]\nid = "boom"\nlabel = "b"\n'
                           'handler = "verb_handlers.ticket_artifacts"\n')
        with pytest.raises(TypeError):
            verbs.run(repo, "boom", ticket=None)


T004_VERBS = """\
[[verb]]
id = "kickoff"
label = "Create ticket"
handler = "verb_handlers.kickoff"
needs_confirm = true

[[verb]]
id = "tickets-digest"
label = "Tickets digest"
handler = "verb_handlers.tickets_digest"

[[verb]]
id = "remember"
label = "Remember a fact"
handler = "verb_handlers.remember"
needs_confirm = true
"""


@pytest.fixture
def t004_wired(repo):
    _write_verbs(repo, T004_VERBS)
    yield repo
    verbs._cache.clear()


class TestT004Verbs:
    """C6: the `kickoff`/`tickets-digest`/`remember` rows, called the way any
    other verb is — `verbs.run`, gates included."""

    def test_kickoff_needs_confirm(self, t004_wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(t004_wired, "kickoff", args={"title": "New thing"})

    def test_kickoff_confirmed_creates_a_ticket(self, t004_wired, monkeypatch):
        from server import kickoff as kickoff_mod
        # PowerShell-unavailable is still a real, honest run of the gated
        # handler: the ticket.toml step (before rendering) must have happened.
        monkeypatch.setattr(kickoff_mod, "_powershell_exe", lambda: None)
        with pytest.raises(kickoff_mod.PowerShellUnavailable):
            verbs.run(t004_wired, "kickoff", confirm=True,
                     args={"title": "New thing"})
        assert tickets.load(t004_wired, "T-001") is not None

    def test_tickets_digest_runs_without_confirm(self, t004_wired):
        out = verbs.run(t004_wired, "tickets-digest")
        assert "text" in out and "count" in out

    def test_remember_needs_confirm(self, t004_wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(t004_wired, "remember", args={"fact": "the sky is blue"})

    def test_remember_confirmed_appends(self, t004_wired):
        from server import assistant
        out = verbs.run(t004_wired, "remember", confirm=True,
                        args={"fact": "the sky is blue"})
        assert out["ok"] is True
        assert "the sky is blue" in assistant.read_memory(t004_wired)

    def test_remember_confirmed_still_declines_a_secret(self, t004_wired):
        out = verbs.run(t004_wired, "remember", confirm=True,
                        args={"fact": "sk-abcdefghijklmnopqrstuvwxyz0123456789"})
        assert out["ok"] is False


class TestShippedRegistry:
    """The config this template actually ships must load and be runnable."""

    def test_every_shipped_verb_resolves(self):
        from server.paths import find_repo_root
        root = find_repo_root()
        verbs._cache.clear()
        reg = verbs.registry(root, force=True)
        assert "context" in reg and "blockers" in reg
        for verb in reg.values():
            assert callable(verb.resolve())
