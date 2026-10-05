"""An answered question wakes the ticket's live chat once, and only once."""

from server import agent_manager, runs, tickets, trackers


def test_answered_question_wakes_the_live_chat_once(repo, monkeypatch):
    tickets.create(repo, "T-9", "Gate")
    rec = runs.create(repo, ticket="T-9", executor="chat", executor_id="chat-1",
                      state="running")
    assert rec["executor_id"] == "chat-1"
    sent = []

    monkeypatch.setattr(agent_manager, "get", lambda sid: object() if sid == "chat-1" else None)
    monkeypatch.setattr(agent_manager, "send",
                        lambda sid, text, mode="auto": sent.append((sid, text)) or {"result": "queued"})

    item = trackers.add(repo, "T-9", "questions", "Which lane?")
    assert sent == []
    trackers.update(repo, "T-9", "questions", item["id"], status="answered", answer="done")
    assert len(sent) == 1
    assert sent[0][0] == "chat-1"
    assert "Which lane?" in sent[0][1] and "done" in sent[0][1]
    again = trackers.update(repo, "T-9", "questions", item["id"], status="answered", answer="done")
    assert again["wake_delivery"] == "answered:done"
    assert len(sent) == 1


def test_no_live_chat_does_not_start_one(repo, monkeypatch):
    tickets.create(repo, "T-8", "Quiet")
    sent = []
    monkeypatch.setattr(agent_manager, "send",
                        lambda *a, **k: sent.append(a) or {"result": "queued"})
    item = trackers.add(repo, "T-8", "questions", "Still open?")
    saved = trackers.update(repo, "T-8", "questions", item["id"],
                            status="answered", answer="later")
    assert sent == []
    assert "wake_delivery" not in saved
