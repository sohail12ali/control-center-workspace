"""When a person answers a question, queue that answer into the live chat.

One delivery per status-and-answer pair. A ticket with no live chat Run, or
whose chat is not in this process, stays answered and is left for the desk.
This never starts a new agent.
"""


def _token(item):
    return "%s:%s" % (item.get("status") or "", (item.get("answer") or "").strip())


def should_wake(before_status, item):
    status = item.get("status") or ""
    if status not in ("answered", "resolved"):
        return False
    if status == before_status and item.get("wake_delivery") == _token(item):
        return False
    if before_status in ("answered", "resolved") and item.get("wake_delivery") == _token(item):
        return False
    if item.get("wake_delivery") == _token(item):
        return False
    return True


def mark(item):
    item["wake_delivery"] = _token(item)


def deliver(repo_root, ticket_id, item):
    """Queue one message on the ticket's newest live chat. True when queued."""
    from . import agent_manager
    from . import runs as runs_mod
    live = [r for r in runs_mod.list_runs(repo_root, ticket=ticket_id)
            if r.get("executor") == "chat" and r.get("state") in runs_mod.ACTIVE
            and r.get("executor_id")]
    if not live:
        return False
    live.sort(key=lambda r: r.get("created") or "")
    chat = live[-1]["executor_id"]
    if agent_manager.get(chat) is None:
        return False
    text = "Question %s was answered.\n\nQ: %s\n\nA: %s" % (
        item.get("id") or "", item.get("text") or "",
        (item.get("answer") or "").strip() or "(no answer text)")
    agent_manager.send(chat, text)
    return True
