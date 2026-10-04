"""Needs attention is one payload for the page and the badge."""

import threading

from server import agent_approvals, overview, runs, tickets, trackers


def test_questions_approvals_and_failed_runs(repo):
    tickets.create(repo, "T-1", "Open work")
    trackers.add(repo, "T-1", "questions", "What is the cutoff?")
    runs.create(repo, ticket="T-1", executor="chat", executor_id="c", state="failed")
    runs.create(repo, ticket="T-1", executor="chat", executor_id="c", state="done")

    pending = agent_approvals.Pending("k1", "chat-9", "run_command", {}, "tu")
    pending.event = threading.Event()
    with agent_approvals.REGISTRY._lock:
        agent_approvals.REGISTRY._pending["k1"] = pending
    try:
        attn = overview.needs_attention(repo)
    finally:
        with agent_approvals.REGISTRY._lock:
            agent_approvals.REGISTRY._pending.pop("k1", None)

    assert attn["counts"]["questions"] == 1
    assert attn["questions"][0]["title"] == "What is the cutoff?"
    assert attn["counts"]["runs"] == 1
    assert attn["runs"][0]["stage"] == "failed"
    assert attn["counts"]["approvals"] == 1
    assert attn["approvals"][0]["href"] == "agents"
    assert attn["approvals"][0]["title"] == "run_command"
