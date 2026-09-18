"""The one-call context digest.

This replaces an agent reading eight artifacts per turn, so the properties that
matter are: it agrees with the board rather than deriving state its own way,
and where it cannot fit everything it says so instead of quietly dropping the
newest blocker.
"""

import os

import pytest

from server import context, telemetry, tickets, trackers

PLAN = """\
---
ticket: "CC-T001"
---

# Plan: CC-T001

### [x] CC-T001-01 — Done thing (2 h)
- [x] a subtask

### [ ] CC-T001-02 — Open thing (3 h)
- [ ] another

### [ ] CC-T001-03 — Also open
"""

PROGRESS = """\
# Progress: CC-T001

## Dated Log

### 2026-08-27
- Done: the first thing

### 2026-08-28
- Done: the second thing

### 2026-08-29
- Done: the third thing
"""


def _artifact(repo, name, text):
    folder = tickets.dir_for(repo, "CC-T001")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "CC-T001-%s.md" % name), "w",
              encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture
def ticket(repo):
    tickets.create(repo, "CC-T001", "A ticket", owner="Sam")
    _artifact(repo, "plan", PLAN)
    _artifact(repo, "progress", PROGRESS)
    return repo


class TestPlanParsing:
    def test_counts_done_and_open(self, ticket):
        digest = context.build(ticket, "CC-T001")
        assert (digest["plan"]["total"], digest["plan"]["done"]) == (3, 1)
        assert [t["id"] for t in digest["plan"]["open"]] == \
            ["CC-T001-02", "CC-T001-03"]

    def test_effort_suffix_is_stripped_from_the_title(self, ticket):
        open_tasks = context.build(ticket, "CC-T001")["plan"]["open"]
        assert open_tasks[0]["title"] == "Open thing"

    def test_a_plan_with_no_task_headings_reports_unparsed(self, ticket):
        # "0 open tasks" and "I could not read the plan" are different facts,
        # and an agent told the first about the second acts confidently wrong.
        _artifact(ticket, "plan", "# Plan\n\nProse only, no task headings.\n")
        plan = context.build(ticket, "CC-T001")["plan"]
        assert plan["exists"] is True and plan["parsed"] is False

    def test_a_missing_plan_is_reported_as_missing(self, repo):
        tickets.create(repo, "CC-T002", "No plan")
        plan = context.build(repo, "CC-T002")["plan"]
        assert plan["exists"] is False and plan["total"] == 0

    def test_open_task_list_is_capped_and_says_so(self, ticket):
        lines = ["# Plan\n"] + [
            "### [ ] T-%02d — Task %d\n" % (i, i)
            for i in range(context.MAX_OPEN_TASKS + 5)]
        _artifact(ticket, "plan", "\n".join(lines))
        plan = context.build(ticket, "CC-T001")["plan"]
        assert len(plan["open"]) == context.MAX_OPEN_TASKS
        assert plan["omitted"] == 5
        assert "5 more open task" in context.format_markdown(
            context.build(ticket, "CC-T001"))


class TestProgress:
    def test_newest_entries_first(self, ticket):
        dates = [e["date"] for e in context.build(ticket, "CC-T001")["progress"]]
        assert dates == ["2026-08-29", "2026-08-28", "2026-08-27"]

    def test_long_entries_are_marked_truncated(self, ticket):
        _artifact(ticket, "progress",
                  "### 2026-08-29\n" + ("x" * (context.MAX_PROGRESS_CHARS + 50)))
        entry = context.build(ticket, "CC-T001")["progress"][0]
        assert entry["truncated"] is True
        assert "truncated" in context.format_markdown(
            context.build(ticket, "CC-T001"))

    def test_missing_progress_is_an_empty_list(self, repo):
        tickets.create(repo, "CC-T002", "Bare")
        assert context.build(repo, "CC-T002")["progress"] == []


class TestAgreementWithTheBoard:
    """The digest must not become a second source of truth."""

    def test_lane_matches_the_board_including_its_label(self, ticket):
        tickets.move(ticket, "CC-T001", "blocked")
        t = context.build(ticket, "CC-T001")["ticket"]
        assert (t["stage"], t["stage_label"]) == ("blocked", "Blocked")

    def test_terminal_lane_is_flagged(self, ticket):
        tickets.move(ticket, "CC-T001", "done")
        assert context.build(ticket, "CC-T001")["ticket"]["terminal"] is True

    def test_blockers_match_the_tracker_rules(self, ticket):
        trackers.add(ticket, "CC-T001", "bugs", "data loss", severity="critical")
        digest = context.build(ticket, "CC-T001")
        assert list(digest["blockers"]) == ["bugs"]
        assert "## BLOCKED" in context.format_markdown(digest)

        trackers.update(ticket, "CC-T001", "bugs", "D-1", status="verified")
        assert context.build(ticket, "CC-T001")["blockers"] == {}

    def test_only_open_tracker_items_are_counted(self, ticket):
        trackers.add(ticket, "CC-T001", "todos", "one")
        trackers.add(ticket, "CC-T001", "todos", "two")
        trackers.update(ticket, "CC-T001", "todos", "TD-1", status="done")
        assert context.build(ticket, "CC-T001")["trackers"]["todos"]["open"] == 1

    def test_tracker_list_is_capped_and_says_so(self, ticket):
        for i in range(context.MAX_TRACKER_ITEMS + 3):
            trackers.add(ticket, "CC-T001", "todos", "item %d" % i)
        section = context.build(ticket, "CC-T001")["trackers"]["todos"]
        assert len(section["items"]) == context.MAX_TRACKER_ITEMS
        assert section["omitted"] == 3
        assert "3 more not shown" in context.format_markdown(
            context.build(ticket, "CC-T001"))

    def test_spend_comes_from_telemetry(self, ticket):
        telemetry.record_turn(ticket, ticket="CC-T001", input_tokens=100,
                              output_tokens=50)
        spend = context.build(ticket, "CC-T001")["spend"]
        assert spend["turns"] == 1 and spend["tokens"] == 150

    def test_unknown_ticket_raises(self, repo):
        with pytest.raises(FileNotFoundError):
            context.build(repo, "CC-T999")


class TestMarkdown:
    def test_states_no_blockers_rather_than_omitting_the_section(self, ticket):
        # Absence of a "blocked" heading could mean either "not blocked" or
        # "the digest forgot to check", so it says which.
        assert "**No blockers.**" in context.format_markdown(
            context.build(ticket, "CC-T001"))

    def test_carries_the_facts_a_turn_starts_from(self, ticket):
        text = context.format_markdown(context.build(ticket, "CC-T001"))
        for expected in ("CC-T001", "A ticket", "Sam", "1/3 tasks done",
                         "CC-T001-02", "## Artifacts"):
            assert expected in text

    def test_stays_small_enough_to_paste_into_a_prompt(self, ticket):
        # The whole point is replacing ~27 KB of artifacts with a digest.
        assert len(context.format_markdown(context.build(ticket, "CC-T001"))) < 2048
