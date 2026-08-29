"""The scheduler.

Cron parsers are where scheduling bugs live, so the field grammar is pinned
exhaustively. The two behavioural rules that matter more than the parsing: an
unsupported expression is rejected rather than quietly treated as `*`, and a
console that was off does not catch up when it comes back.
"""

import os
from datetime import datetime

import pytest

from server import jobs, schedules, tickets, verbs

VERBS = """\
[[verb]]
id = "report"
label = "A report"
handler = "verb_handlers.open_todos"

[[verb]]
id = "guarded"
label = "Mutates"
handler = "verb_handlers.open_todos"
needs_confirm = true
"""


def _write_schedules(repo, text):
    with open(os.path.join(repo, "console", "config", "schedules.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(text)
    schedules._cache.clear()
    return repo


@pytest.fixture
def wired(repo):
    with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(VERBS)
    verbs._cache.clear()
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()
    schedules._cache.clear()


def one(expr, **kw):
    row = ['[[schedule]]', 'id = "s1"', 'label = "One"',
           'expr = "%s"' % expr, 'verb = "report"']
    for key, value in kw.items():
        row.append("%s = %s" % (key, "true" if value is True else
                                "false" if value is False else '"%s"' % value))
    return "\n".join(row) + "\n"


class TestFieldGrammar:
    @pytest.mark.parametrize("expr,when,expected", [
        ("* * * * *",   datetime(2026, 8, 29, 13, 7),  True),
        ("0 9 * * *",   datetime(2026, 8, 29, 9, 0),   True),
        ("0 9 * * *",   datetime(2026, 8, 29, 9, 1),   False),
        ("30 * * * *",  datetime(2026, 8, 29, 13, 30), True),
        ("*/15 * * * *", datetime(2026, 8, 29, 13, 30), True),
        ("*/15 * * * *", datetime(2026, 8, 29, 13, 31), False),
        ("0 9-17 * * *", datetime(2026, 8, 29, 14, 0), True),
        ("0 9-17 * * *", datetime(2026, 8, 29, 18, 0), False),
        ("0 0 1 * *",   datetime(2026, 9, 1, 0, 0),    True),
        ("0 0 1 * *",   datetime(2026, 9, 2, 0, 0),    False),
        ("0 0 * 12 *",  datetime(2026, 12, 5, 0, 0),   True),
        ("0 0 * 12 *",  datetime(2026, 11, 5, 0, 0),   False),
        ("0 9 * * 1,3,5", datetime(2026, 8, 31, 9, 0), True),   # Monday
        ("0 9 * * 1,3,5", datetime(2026, 9, 1, 9, 0),  False),  # Tuesday
    ])
    def test_matching(self, wired, expr, when, expected):
        _write_schedules(wired, one(expr))
        assert schedules.registry(wired)["s1"].matches(when) is expected

    def test_weekday_zero_is_sunday(self, wired):
        _write_schedules(wired, one("0 9 * * 0"))
        schedule = schedules.registry(wired)["s1"]
        assert schedule.matches(datetime(2026, 8, 30, 9, 0)) is True   # Sunday
        assert schedule.matches(datetime(2026, 8, 31, 9, 0)) is False  # Monday

    def test_weekday_seven_is_also_sunday(self, wired):
        # Half the world writes it that way; rejecting it would be pedantry.
        _write_schedules(wired, one("0 9 * * 7"))
        assert schedules.registry(wired)["s1"].matches(
            datetime(2026, 8, 30, 9, 0)) is True

    def test_day_and_weekday_together_mean_and(self, wired):
        # Real cron ORs them. This ANDs, which is what someone who has not
        # memorised the POSIX rule expects — and it is documented as such.
        _write_schedules(wired, one("0 9 1 * 1"))
        schedule = schedules.registry(wired)["s1"]
        assert schedule.matches(datetime(2026, 6, 1, 9, 0)) is True    # Mon 1st
        assert schedule.matches(datetime(2026, 6, 8, 9, 0)) is False   # Mon 8th
        assert schedule.matches(datetime(2026, 7, 1, 9, 0)) is False   # Wed 1st


class TestRejection:
    @pytest.mark.parametrize("expr", [
        "@daily", "0 9 * *", "0 9 * * * *", "0 9 L * *", "0 9 * * MON",
        "0 99 * * *", "60 * * * *", "0 9 * 13 *", "*/0 * * * *", "5-2 * * * *",
    ])
    def test_unsupported_or_invalid_expressions_are_refused(self, wired, expr):
        # Never silently treated as `*` — a schedule that fires every minute
        # because its expression was not understood is the worst outcome here.
        _write_schedules(wired, one(expr))
        with pytest.raises(schedules.ScheduleError):
            schedules.registry(wired, force=True)

    def test_the_error_names_the_schedule(self, wired):
        _write_schedules(wired, one("@daily"))
        with pytest.raises(schedules.ScheduleError) as exc:
            schedules.registry(wired, force=True)
        assert "s1" in str(exc.value)

    def test_a_row_without_a_verb_is_refused(self, wired):
        _write_schedules(wired, '[[schedule]]\nid = "s1"\nexpr = "* * * * *"\n')
        with pytest.raises(schedules.ScheduleError):
            schedules.registry(wired, force=True)

    def test_a_parked_row_is_still_parsed(self, wired):
        # Finding out a parked schedule never parsed, at the moment someone
        # re-enables it, is finding out too late.
        _write_schedules(wired, one("@daily", enabled=False))
        with pytest.raises(schedules.ScheduleError):
            schedules.registry(wired, force=True)

    def test_missing_config_is_an_empty_registry(self, repo):
        schedules._cache.clear()
        assert schedules.registry(repo) == {}


class TestNextRun:
    def test_finds_the_next_firing(self, wired):
        _write_schedules(wired, one("0 9 * * *"))
        nxt = schedules.registry(wired)["s1"].next_after(
            datetime(2026, 8, 29, 10, 0))
        assert nxt == datetime(2026, 8, 30, 9, 0)

    def test_it_is_strictly_after_the_given_moment(self, wired):
        _write_schedules(wired, one("0 9 * * *"))
        nxt = schedules.registry(wired)["s1"].next_after(
            datetime(2026, 8, 29, 9, 0))
        assert nxt == datetime(2026, 8, 30, 9, 0)

    def test_an_unreachable_schedule_returns_none(self, wired):
        # 30 February.
        _write_schedules(wired, one("0 0 30 2 *"))
        assert schedules.registry(wired)["s1"].next_after(
            datetime(2026, 1, 1)) is None

    def test_describe_carries_the_next_run(self, wired):
        _write_schedules(wired, one("0 9 * * *"))
        row = schedules.registry(wired)["s1"].describe(datetime(2026, 8, 29, 10, 0))
        assert row["next_run"] == "2026-08-30 09:00"

    def test_a_parked_schedule_reports_no_next_run(self, wired):
        _write_schedules(wired, one("0 9 * * *", enabled=False))
        assert schedules.registry(wired)["s1"].describe()["next_run"] == ""


class TestTicker:
    @pytest.fixture
    def queue(self, wired):
        q = jobs.JobQueue(wired, max_concurrent=1).start()
        yield q
        q.stop()

    def test_the_first_tick_fires_nothing(self, wired, queue):
        # Catching up after a gap would run every schedule dozens of times at
        # once, and these submit real work.
        _write_schedules(wired, one("* * * * *"))
        ticker = schedules.Ticker(wired, queue)
        assert ticker.tick(datetime(2026, 8, 29, 12, 0)) == []

    def test_a_later_minute_fires(self, wired, queue):
        _write_schedules(wired, one("* * * * *"))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        submitted = ticker.tick(datetime(2026, 8, 29, 12, 1))
        assert len(submitted) == 1
        assert submitted[0]["verb"] == "report"

    def test_the_same_minute_cannot_fire_twice(self, wired, queue):
        # Timers drift and a wake-up can land twice inside one minute.
        _write_schedules(wired, one("* * * * *"))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        assert len(ticker.tick(datetime(2026, 8, 29, 12, 1))) == 1
        assert ticker.tick(datetime(2026, 8, 29, 12, 1)) == []

    def test_a_gap_does_not_replay_the_missed_minutes(self, wired, queue):
        _write_schedules(wired, one("* * * * *"))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        submitted = ticker.tick(datetime(2026, 8, 30, 12, 0))   # a day later
        assert len(submitted) == 1      # one firing, not 1440

    def test_a_parked_schedule_does_not_fire(self, wired, queue):
        _write_schedules(wired, one("* * * * *", enabled=False))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        assert ticker.tick(datetime(2026, 8, 29, 12, 1)) == []

    def test_the_job_records_which_schedule_fired_it(self, wired, queue):
        _write_schedules(wired, one("* * * * *"))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        job = ticker.tick(datetime(2026, 8, 29, 12, 1))[0]
        assert job["submitted_by"] == "schedule:s1"

    def test_a_gated_verb_needs_confirm_declared_in_the_file(self, wired, queue):
        # A scheduled job runs with nobody watching, so the grant has to be
        # deliberate and committed.
        _write_schedules(wired, one("* * * * *").replace(
            'verb = "report"', 'verb = "guarded"'))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        assert ticker.tick(datetime(2026, 8, 29, 12, 1)) == []
        assert ticker.skipped == 1

    def test_confirm_true_lets_it_through(self, wired, queue):
        _write_schedules(wired, one("* * * * *", confirm=True).replace(
            'verb = "report"', 'verb = "guarded"'))
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        assert len(ticker.tick(datetime(2026, 8, 29, 12, 1))) == 1

    def test_one_broken_schedule_does_not_stop_the_others(self, wired, queue):
        _write_schedules(wired,
                         one("* * * * *") +
                         '\n[[schedule]]\nid = "s2"\nexpr = "* * * * *"\n'
                         'verb = "no-such-verb"\n')
        ticker = schedules.Ticker(wired, queue)
        ticker.tick(datetime(2026, 8, 29, 12, 0))
        submitted = ticker.tick(datetime(2026, 8, 29, 12, 1))
        assert [j["verb"] for j in submitted] == ["report"]
        assert ticker.skipped == 1


class TestShippedConfig:
    def test_the_template_schedules_parse_and_are_parked(self):
        from server.paths import find_repo_root
        root = find_repo_root()
        schedules._cache.clear()
        registry = schedules.registry(root, force=True)
        assert registry, "the template ships example schedules"
        assert all(not s.enabled for s in registry.values()), \
            "a template must not start firing jobs nobody chose"
