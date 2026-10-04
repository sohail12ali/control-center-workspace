"""Composer catalog.

The catalog is what the Agents tab offers, and it had two implementations —
this module's and the HTTP feature's own globs — which could show different
rosters. These tests pin the single one, and the rule that a closed ticket is
not offered as somewhere to start new work.
"""

import os

from server import agents, tickets


def test_reads_skills_and_personas_off_disk(repo):
    skills = os.path.join(repo, ".claude", "skills")
    for name in ("alpha", "beta"):
        os.makedirs(os.path.join(skills, name))
        open(os.path.join(skills, name, "SKILL.md"), "w").close()
    agent_dir = os.path.join(repo, ".claude", "agents")
    os.makedirs(agent_dir)
    open(os.path.join(agent_dir, "builder.md"), "w").close()

    cat = agents.list_catalog(repo)
    assert cat["skills"] == ["alpha", "beta"]
    assert cat["personas"] == ["builder"]


def test_a_directory_without_skill_md_is_not_a_skill(repo):
    os.makedirs(os.path.join(repo, ".claude", "skills", "bundle"))
    assert agents.list_catalog(repo)["skills"] == []


def test_offers_open_tickets(repo):
    tickets.create(repo, "CC-T001", "First")
    tickets.create(repo, "CC-T002", "Second")
    tickets.move(repo, "CC-T002", "in-progress")
    ids = [t["id"] for t in agents.list_catalog(repo)["tickets"]]
    assert ids == ["CC-T001", "CC-T002"]


def test_terminal_lane_tickets_are_not_offered(repo):
    # You do not start new work on a closed ticket, and offering one invites
    # a chat's cost being filed against work that already shipped.
    tickets.create(repo, "CC-T001", "Done thing")
    tickets.move(repo, "CC-T001", "done")
    assert agents.list_catalog(repo)["tickets"] == []


def test_ticket_rows_carry_what_the_picker_renders(repo):
    tickets.create(repo, "CC-T001", "First")
    row = agents.list_catalog(repo)["tickets"][0]
    assert row == {"id": "CC-T001", "title": "First", "stage": "open"}


def test_empty_workspace_returns_empty_lists_not_an_error(repo):
    cat = agents.list_catalog(repo)
    assert cat == {"skills": [], "personas": [], "tickets": []}
