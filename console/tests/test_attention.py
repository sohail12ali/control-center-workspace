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


# --- T-039: Needs you / Needs repair split ---------------------------------

import contextlib
import hashlib
import os


@contextlib.contextmanager
def _approval(key="k1", chat="chat-9", tool="run_command"):
    pending = agent_approvals.Pending(key, chat, tool, {}, "tu")
    pending.event = threading.Event()
    with agent_approvals.REGISTRY._lock:
        agent_approvals.REGISTRY._pending[key] = pending
    try:
        yield
    finally:
        with agent_approvals.REGISTRY._lock:
            agent_approvals.REGISTRY._pending.pop(key, None)


def _owned(repo, tid, title="Work"):
    return tickets.create(repo, tid, title, owner="Sam")


def _age(repo, tid, day="2000-01-01"):
    config = overview.boards_mod.load_console_config(repo)
    ticket = tickets.load(repo, tid)
    ticket["updated"] = day
    tickets._save(repo, config, tid, ticket)


def test_payload_has_both_lists_and_exact_counts(repo):
    _owned(repo, "T-1")
    trackers.add(repo, "T-1", "questions", "Which cutoff?")
    with _approval():
        attn = overview.needs_attention(repo)
    assert attn["counts"]["needs_you"] == len(attn["needs_you"]) == 2
    assert attn["counts"]["needs_repair"] == len(attn["needs_repair"]) == 0
    for entry in attn["needs_you"]:
        for key in ("id", "title", "kind", "stage", "type", "href"):
            assert key in entry
    question = [e for e in attn["needs_you"] if e["type"] == "question"][0]
    assert question["ref"] == "Q1" and question["priority"] == "medium"
    assert [e for e in attn["needs_you"] if e["type"] == "approval"][0]["href"] == "agents"


def test_open_answered_and_resolved_questions_land_apart(repo):
    _owned(repo, "T-1")
    trackers.add(repo, "T-1", "questions", "open one")
    trackers.add(repo, "T-1", "questions", "answered one")
    trackers.add(repo, "T-1", "questions", "resolved one")
    trackers.add(repo, "T-1", "questions", "closed one")
    trackers.update(repo, "T-1", "questions", "Q2", status="answered")
    trackers.update(repo, "T-1", "questions", "Q3", status="resolved")
    trackers.update(repo, "T-1", "questions", "Q4", status="closed")
    attn = overview.needs_attention(repo)
    assert [e["title"] for e in attn["needs_you"]] == ["open one"]
    assert [(e["title"], e["type"]) for e in attn["needs_repair"]] == [("answered one", "answered")]
    assert [e["title"] for e in attn["questions"]] == ["open one"]
    assert [e["title"] for e in attn["answered"]] == ["answered one"]
    assert attn["counts"]["answered"] == 1


def test_repair_kinds_and_what_is_left_out(repo):
    _owned(repo, "T-1")                              # blocked (critical open question)
    trackers.add(repo, "T-1", "questions", "stop", priority="critical")
    _owned(repo, "T-2")                              # stale
    _age(repo, "T-2")
    tickets.create(repo, "T-3", "Nobody")            # unowned
    _owned(repo, "T-4")                              # finished: never attention
    tickets.move(repo, "T-4", "done")
    _age(repo, "T-4")
    tickets.set_field(repo, "T-3", "owner", "")
    for state in ("failed", "timed_out", "scheduled_retry", "done"):
        runs.create(repo, ticket="T-1", executor="chat", executor_id="c", state=state)
    attn = overview.needs_attention(repo)
    types = sorted(e["type"] for e in attn["needs_repair"])
    assert types == ["blocked", "run", "run", "run", "stale", "unowned"]
    ids = {(e["type"], e["id"]) for e in attn["needs_repair"] if e["type"] != "run"}
    assert ids == {("blocked", "T-1"), ("stale", "T-2"), ("unowned", "T-3")}
    assert "T-4" not in {e["id"] for e in attn["needs_repair"]}
    assert sorted(e["stage"] for e in attn["needs_repair"] if e["type"] == "run") == [
        "failed", "scheduled_retry", "timed_out"]
    assert attn["counts"]["needs_repair"] == 6


def test_pending_approval_is_needs_you_only(repo):
    with _approval():
        attn = overview.needs_attention(repo)
    assert [e["type"] for e in attn["needs_you"]] == ["approval"]
    assert attn["needs_repair"] == []


def test_review_escalation_adds_no_entry_of_its_own(repo):
    _owned(repo, "T-1")
    ticket = tickets.load(repo, "T-1")
    ticket["review_escalated"] = True
    tickets._save(repo, overview.boards_mod.load_console_config(repo), "T-1", ticket)
    attn = overview.needs_attention(repo)
    assert attn["needs_you"] == [] and attn["needs_repair"] == []


def test_legacy_keys_keep_their_shape(repo):
    _owned(repo, "T-1")
    trackers.add(repo, "T-1", "questions", "stop", priority="critical")
    attn = overview.needs_attention(repo)
    for key in ("blocked", "stale", "unowned", "questions", "approvals", "runs"):
        assert isinstance(attn[key], list)
    for key in ("blocked", "stale", "unowned", "questions", "approvals", "runs"):
        assert key in attn["counts"]
    assert attn["blocked"][0]["id"] == "T-1"          # assistant.js reads attention.blocked
    assert attn["blocked"][0]["blocking"] == 1


def test_needs_you_is_capped_at_50_with_the_exact_count(repo):
    _owned(repo, "T-1")
    for n in range(60):
        trackers.add(repo, "T-1", "questions", "q%d" % n)
    attn = overview.needs_attention(repo)
    assert len(attn["needs_you"]) == 50
    assert attn["counts"]["needs_you"] == 60


def test_needs_you_order_is_approval_then_critical_then_normal(repo):
    _owned(repo, "T-1")
    trackers.add(repo, "T-1", "questions", "normal one")
    trackers.add(repo, "T-1", "questions", "critical one", priority="critical")
    with _approval():
        attn = overview.needs_attention(repo)
    assert [e["title"] for e in attn["needs_you"]] == ["run_command", "critical one", "normal one"]


def test_repair_groups_keep_cap_8_with_exact_counts(repo):
    for n in range(10):
        tickets.create(repo, "T-%d" % (n + 1), "Orphan %d" % n)
    attn = overview.needs_attention(repo)
    assert len(attn["unowned"]) == 8 and attn["counts"]["unowned"] == 10
    assert len([e for e in attn["needs_repair"] if e["type"] == "unowned"]) == 8
    assert attn["counts"]["needs_repair"] == 10


def test_repair_count_is_the_sum_of_group_counts(repo):
    tickets.create(repo, "T-1", "Idle and ownerless")   # unowned and stale: counted in both
    _age(repo, "T-1")
    attn = overview.needs_attention(repo)
    assert attn["counts"]["stale"] == 1 and attn["counts"]["unowned"] == 1
    assert attn["counts"]["needs_repair"] == 2
    assert len(attn["needs_repair"]) == 2


def test_question_ref_is_the_tracker_item_id(repo):
    _owned(repo, "T-1")
    for text in ("a", "b", "c"):
        trackers.add(repo, "T-1", "questions", text)
    attn = overview.needs_attention(repo)
    assert sorted(e["ref"] for e in attn["needs_you"]) == ["Q1", "Q2", "Q3"]


def _tree_hash(root):
    digest = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as fh:
                digest[path] = hashlib.sha256(fh.read()).hexdigest()
    return digest


def test_needs_attention_writes_nothing_and_leaves_approvals_pending(repo):
    _owned(repo, "T-1")
    trackers.add(repo, "T-1", "questions", "stop", priority="critical")
    runs.create(repo, ticket="T-1", executor="chat", executor_id="c", state="failed")
    roots = [os.path.join(repo, "knowledge-center", "artifacts"),
             os.path.join(repo, "console", ".cache", "runs")]
    with _approval():
        before = [_tree_hash(r) for r in roots]
        first = overview.needs_attention(repo)
        second = overview.needs_attention(repo)
        assert [_tree_hash(r) for r in roots] == before
        assert agent_approvals.REGISTRY.pending_all()
    assert first == second
    assert any(before)


def test_full_overview_generated_at_uses_the_injected_now(repo):
    from datetime import datetime, timezone
    at = datetime(2026, 10, 6, 9, 5, 7, tzinfo=timezone.utc)
    assert overview.full_overview(repo, now=at)["generated_at"] == "2026-10-06T09:05:07Z"


def test_full_overview_generated_at_matches_the_pattern_without_now(repo):
    import re
    stamp = overview.full_overview(repo)["generated_at"]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", stamp)


def test_static_export_carries_generated_at(repo, tmp_path):
    import json
    from server import export
    import shutil
    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copy(os.path.join(here, "..", "config", "plugins.toml"),
                os.path.join(repo, "console", "config", "plugins.toml"))
    out = str(tmp_path / "site")
    export.export_static(repo, out)
    with open(os.path.join(out, "data", "overview.json"), encoding="utf-8") as fh:
        stamp = json.load(fh)["generated_at"]
    assert stamp.endswith("Z")
    with open(os.path.join(out, "data.js"), encoding="utf-8") as fh:
        assert '"generated_at": "%s"' % stamp in fh.read()


def test_overview_source_calls_no_mutator():
    path = os.path.join(os.path.dirname(overview.__file__), "overview.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    for needle in (".decide(", "trackers_mod.add", "trackers_mod.update", "trackers_mod.remove",
                   "tickets_mod.move", "tickets_mod.set_", "tickets_mod.patch",
                   "tickets_mod.create", "open(", ".write("):
        assert needle not in source, needle
