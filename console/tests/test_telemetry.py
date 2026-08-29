"""Token and cost records.

The rule this file exists to defend: **an unknown cost is never zero.** Every
other behaviour here is bookkeeping; that one decides whether the totals can be
trusted to make a decision with.
"""

import json
import os

import pytest

from server import agent_backends, agent_session, telemetry

PRICING = """\
[[model]]
id = "priced-model"
input_per_mtok = 10.0
output_per_mtok = 50.0
verified = "2026-08-29"
"""


@pytest.fixture(autouse=True)
def _clear_pricing():
    telemetry._pricing_cache.clear()
    yield
    telemetry._pricing_cache.clear()


@pytest.fixture
def priced(repo):
    with open(os.path.join(repo, "console", "config", "pricing.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(PRICING)
    return repo


class TestPricing:
    def test_exact_match(self, priced):
        cost, source = telemetry.price(priced, "priced-model", 1_000_000, 1_000_000)
        assert (cost, source) == (60.0, "table")

    def test_longest_prefix_covers_a_dated_release(self, priced):
        # A pinned id and its dated form must price the same without a row each.
        cost, source = telemetry.price(priced, "priced-model-20260114", 1_000_000, 0)
        assert (cost, source) == (10.0, "table")

    def test_unknown_model_is_unknown_not_free(self, priced):
        assert telemetry.price(priced, "mystery-model", 999, 999) == (None, "unknown")

    def test_empty_model_is_unknown(self, priced):
        assert telemetry.price(priced, "", 10, 10) == (None, "unknown")

    def test_no_pricing_file_is_not_an_error(self, repo):
        assert telemetry.price(repo, "anything", 10, 10) == (None, "unknown")

    def test_partial_tokens_scale_linearly(self, priced):
        cost, _ = telemetry.price(priced, "priced-model", 500_000, 0)
        assert cost == 5.0


class TestRecording:
    def test_writes_one_line_per_turn(self, repo):
        telemetry.record_turn(repo, session="s1", model="m", input_tokens=10,
                              output_tokens=5)
        telemetry.record_turn(repo, session="s1", model="m", input_tokens=20,
                              output_tokens=7)
        assert len(telemetry.read_records(repo)) == 2

    def test_record_carries_every_declared_field(self, repo):
        telemetry.record_turn(repo, session="s1", backend="b", model="m",
                              mode="plan", ticket="CC-T001", skill="plan",
                              persona="planner", input_tokens=1, output_tokens=2)
        rec = telemetry.read_records(repo)[0]
        assert set(rec) == set(telemetry.FIELDS)

    def test_backend_reported_cost_wins_over_the_table(self, priced):
        telemetry.record_turn(priced, model="priced-model", input_tokens=1_000_000,
                              output_tokens=0, cost_usd=0.42)
        rec = telemetry.read_records(priced)[0]
        assert (rec["cost_usd"], rec["cost_source"]) == (0.42, "backend")

    def test_table_fills_in_when_the_backend_reports_nothing(self, priced):
        telemetry.record_turn(priced, model="priced-model",
                              input_tokens=1_000_000, output_tokens=0)
        rec = telemetry.read_records(priced)[0]
        assert (rec["cost_usd"], rec["cost_source"]) == (10.0, "table")

    def test_unknown_model_records_null_cost(self, repo):
        telemetry.record_turn(repo, model="mystery", input_tokens=100,
                              output_tokens=100)
        rec = telemetry.read_records(repo)[0]
        assert rec["cost_usd"] is None and rec["cost_source"] == "unknown"

    def test_records_hold_no_prompt_or_tool_content(self, repo):
        telemetry.record_turn(repo, session="s1", model="m", input_tokens=1,
                              output_tokens=1)
        blob = json.dumps(telemetry.read_records(repo)[0])
        for leaky in ("prompt", "text", "result", "content", "args"):
            assert leaky not in blob

    def test_an_unwritable_directory_returns_none_instead_of_raising(self, repo, monkeypatch):
        # Called from a live session's reader thread: losing a measurement is
        # acceptable, killing the chat is not.
        monkeypatch.setattr(telemetry.os, "makedirs",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
        assert telemetry.record_turn(repo, model="m") is None

    def test_a_corrupt_line_does_not_hide_the_rest(self, repo):
        telemetry.record_turn(repo, session="good", model="m", input_tokens=1)
        folder = telemetry.telemetry_dir(repo)
        path = os.path.join(folder, sorted(os.listdir(folder))[0])
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("{ this is not json\n")
        assert [r["session"] for r in telemetry.read_records(repo)] == ["good"]


class TestSummarize:
    @pytest.fixture
    def data(self, priced):
        telemetry.record_turn(priced, ticket="CC-T001", skill="plan",
                              model="priced-model", input_tokens=1_000_000,
                              output_tokens=0)
        telemetry.record_turn(priced, ticket="CC-T001", skill="verify",
                              model="priced-model", input_tokens=1_000_000,
                              output_tokens=0)
        telemetry.record_turn(priced, ticket="CC-T002", skill="plan",
                              model="mystery-model", input_tokens=500, output_tokens=500)
        return priced

    def test_groups_by_ticket(self, data):
        rows = {r["key"]: r for r in telemetry.summarize(data, group="ticket")["rows"]}
        assert rows["CC-T001"]["turns"] == 2
        assert rows["CC-T001"]["cost_usd"] == 20.0

    def test_groups_by_skill(self, data):
        rows = {r["key"]: r for r in telemetry.summarize(data, group="skill")["rows"]}
        assert rows["plan"]["turns"] == 2
        assert rows["verify"]["turns"] == 1

    def test_ticket_filter(self, data):
        summary = telemetry.summarize(data, group="skill", ticket="CC-T002")
        assert [r["key"] for r in summary["rows"]] == ["plan"]

    def test_unpriced_turns_are_counted_not_zeroed(self, data):
        rows = {r["key"]: r for r in telemetry.summarize(data, group="ticket")["rows"]}
        t2 = rows["CC-T002"]
        assert t2["unpriced_turns"] == 1
        assert t2["cost_complete"] is False
        assert t2["tokens"] == 1000        # tokens are still counted

    def test_totals_flag_themselves_as_partial(self, data):
        totals = telemetry.summarize(data, group="ticket")["totals"]
        assert totals["cost_complete"] is False
        assert totals["unpriced_turns"] == 1
        assert totals["cost_usd"] == 20.0  # the priced turns only

    def test_a_fully_priced_selection_is_complete(self, data):
        totals = telemetry.summarize(data, group="skill", ticket="CC-T001")["totals"]
        assert totals["cost_complete"] is True

    def test_report_marks_partial_totals_visibly(self, data):
        text = telemetry.format_summary(telemetry.summarize(data, group="ticket"))
        assert "*" in text and "partial" in text

    def test_unknown_group_is_refused(self, data):
        with pytest.raises(ValueError):
            telemetry.summarize(data, group="phase-of-the-moon")

    def test_empty_log_summarizes_to_nothing(self, repo):
        summary = telemetry.summarize(repo)
        assert summary["rows"] == [] and summary["totals"]["turns"] == 0


class TestSkillUsage:
    def test_partitions_fired_and_never_fired(self, repo):
        telemetry.record_turn(repo, skill="plan", input_tokens=10, output_tokens=5)
        telemetry.record_turn(repo, skill="plan", input_tokens=10, output_tokens=5)
        report = telemetry.skill_usage(repo, all_skills=["plan", "verify", "fix"])
        assert report["fired"] == [{"skill": "plan", "turns": 2, "tokens": 30}]
        assert report["never_fired"] == ["fix", "verify"]

    def test_turns_with_no_skill_are_not_counted_as_one(self, repo):
        telemetry.record_turn(repo, skill="", input_tokens=10)
        report = telemetry.skill_usage(repo, all_skills=["plan"])
        assert report["fired"] == []
        assert report["never_fired"] == ["plan"]

    def test_a_recorded_skill_no_longer_on_disk_is_surfaced(self, repo):
        telemetry.record_turn(repo, skill="deleted-skill", input_tokens=1)
        report = telemetry.skill_usage(repo, all_skills=["plan"])
        assert report["unknown_skills"] == ["deleted-skill"]

    def test_report_states_it_is_evidence_not_a_verdict(self, repo):
        text = telemetry.format_skill_usage(
            telemetry.skill_usage(repo, all_skills=["plan"]))
        assert "not a verdict" in text


class TestSessionIntegration:
    """The wiring, not the module: a turn ending must actually leave a record."""

    def _session(self, repo, **kw):
        backend = agent_backends.get(repo, "alpha")
        return agent_session.build("sid123", backend, repo, model="priced-model",
                                   **kw)

    def test_turn_end_writes_a_record(self, priced):
        sess = self._session(priced, ticket="CC-T001", skill="plan",
                             persona="planner")
        sess._observe({"type": "turn.end", "cost_usd": 0.25,
                       "input_tokens": 120, "output_tokens": 40,
                       "duration_ms": 900, "num_turns": 1})
        rec = telemetry.read_records(priced)[0]
        assert rec["ticket"] == "CC-T001"
        assert rec["skill"] == "plan"
        assert rec["persona"] == "planner"
        assert (rec["input_tokens"], rec["output_tokens"]) == (120, 40)
        assert rec["cost_usd"] == 0.25

    def test_mid_turn_usage_events_are_not_double_counted(self, priced):
        # A backend may report usage incrementally AND in its result event.
        sess = self._session(priced, ticket="CC-T001")
        sess._observe({"type": "usage", "input_tokens": 100, "output_tokens": 30})
        sess._observe({"type": "usage", "input_tokens": 120, "output_tokens": 40})
        sess._observe({"type": "turn.end", "input_tokens": 120,
                       "output_tokens": 40, "num_turns": 1})
        rec = telemetry.read_records(priced)[0]
        assert (rec["input_tokens"], rec["output_tokens"]) == (120, 40)

    def test_each_turn_is_its_own_record(self, priced):
        sess = self._session(priced, ticket="CC-T001")
        for _ in range(3):
            sess._observe({"type": "turn.end", "input_tokens": 10,
                           "output_tokens": 5, "num_turns": 1})
        records = telemetry.read_records(priced)
        assert len(records) == 3
        assert sess.tokens_in == 30      # session total still accumulates

    def test_a_chat_with_no_ticket_records_an_empty_one(self, priced):
        # Attributing an exploratory chat to a ticket would corrupt its cost.
        sess = self._session(priced)
        sess._observe({"type": "turn.end", "input_tokens": 10, "num_turns": 1})
        assert telemetry.read_records(priced)[0]["ticket"] == ""

    def test_telemetry_failure_does_not_break_the_turn(self, priced, monkeypatch):
        monkeypatch.setattr(telemetry, "record_turn",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        sess = self._session(priced, ticket="CC-T001")
        sess._observe({"type": "turn.end", "input_tokens": 10,
                       "output_tokens": 5, "num_turns": 1})
        assert sess.tokens_in == 10      # the session carried on regardless
