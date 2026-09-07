"""Adapters that give existing console functions the verb calling convention.

Every verb handler is called as `handler(repo_root, ticket=None, **args)`. The
underlying readers have their own natural signatures and should keep them, so
each adapter here is a one-line translation and nothing more.

**No handler takes `**kwargs`.** A catch-all would make `verbs.run` accept
`by=modle` in silence and return a default-grouped answer that looks correct;
declaring the real parameters lets the registry reject the typo by name before
the handler is ever called.

This file is deliberately dull. When an adapter starts wanting logic of its own,
that logic belongs in the module that owns the fact, not in the glue.
"""

from . import assistant as assistant_mod
from . import context as context_mod
from . import harness_lint
from . import kickoff as kickoff_mod
from . import model_catalog
from . import native_bridge
from . import telemetry as telemetry_mod
from . import tickets as tickets_mod
from . import todos_agg
from . import trackers as trackers_mod


def ticket_context(repo_root, ticket=None):
    """Everything about one ticket, in one call."""
    return context_mod.build(repo_root, ticket)


def ticket_blockers(repo_root, ticket=None):
    """Only the items that actually block, by each tracker's own rule."""
    found = trackers_mod.blockers(repo_root, ticket)
    return {"ticket": ticket, "blocked": bool(found), "blockers": found}


def ticket_artifacts(repo_root, ticket=None):
    return tickets_mod.list_artifacts(repo_root, ticket)


def plan_status(repo_root, ticket=None):
    """Task completion parsed from the plan artifact."""
    plan = context_mod.plan_tasks(repo_root, ticket)
    tasks = plan["tasks"]
    return {
        "ticket": ticket,
        "exists": plan["exists"],
        "parsed": plan["parsed"],
        "total": len(tasks),
        "done": sum(1 for t in tasks if t["done"]),
        "open": [t for t in tasks if not t["done"]],
    }


def harness_lint_verb(repo_root, ticket=None):
    findings, summary = harness_lint.lint(repo_root)
    return {"summary": summary, "findings": [f.as_dict() for f in findings]}


def telemetry_summary(repo_root, ticket=None, by="ticket"):
    return telemetry_mod.summarize(repo_root, group=by, ticket=ticket)


def skill_usage(repo_root, ticket=None):
    return telemetry_mod.skill_usage(repo_root)


def agent_models(repo_root, ticket=None, backend="", refresh=""):
    """Cached model catalogue per API provider; `refresh=1` re-fetches.

    Read-only by default so it is safe from the palette and from an agent's own
    tool list. A refresh reaches the provider's network, which is why it is an
    explicit argument rather than the default.
    """
    if not backend:
        return {"providers": model_catalog.summary(repo_root)}
    if str(refresh).lower() in ("1", "true", "yes", "on"):
        rows, error = model_catalog.fetch(repo_root, backend)
        return {"backend": backend, "models": rows, "count": len(rows),
                "error": error, "refreshed": True}
    # Same check `fetch` makes, so "this is a CLI" and "that row is disabled"
    # read identically whether you looked or re-fetched.
    resolved, why = model_catalog.resolve(repo_root, backend)
    if resolved is None:
        return {"backend": backend, "models": [], "count": 0,
                "refreshed": False, "error": why}
    hit = model_catalog.cached(repo_root, backend)
    if not hit:
        return {"backend": backend, "models": [], "count": 0, "refreshed": False,
                "error": "no cached catalogue — run with refresh=1 to fetch one"}
    return {"backend": backend, "models": hit["models"], "count": hit["count"],
            "fetched_at": hit["fetched_at"], "age_days": hit["age_days"],
            "refreshed": False, "error": ""}


def open_todos(repo_root, ticket=None):
    """Todos across every scope, or just this ticket's when one is given."""
    if ticket:
        return {"ticket": ticket,
                "items": trackers_mod.list_items(repo_root, ticket, "todos",
                                                 status="open")}
    return {"items": todos_agg.all_todos(repo_root, status="open")}


def tickets_digest(repo_root, ticket=None):
    """A capped "what's open" summary across every ticket (T-004 FR-6)."""
    return context_mod.tickets_digest(repo_root)


def remember(repo_root, ticket=None, fact=""):
    """Append a fact to the Assistant's memory (T-004 FR-6/FR-9). The
    secret-shaped-fact guard lives in `assistant.remember` itself, so every
    caller — this verb, the fast-command row, the `memory` HTTP route —
    shares one guarantee."""
    return assistant_mod.remember(repo_root, fact)


def kickoff(repo_root, ticket=None, title="", kind="tickets", owner="",
           prefix=kickoff_mod.DEFAULT_PREFIX):
    """Create a new ticket (T-004 FR-6): the same 3 artifacts the `kickoff`
    skill produces by hand, never a thin `tickets.create` wrapper (BR-5)."""
    return kickoff_mod.create_ticket(repo_root, title, kind=kind, owner=owner,
                                     prefix=prefix)


# -- desktop (T-005) --------------------------------------------------------
# These reach the native shell over the loopback bridge. Every one degrades to
# `{"ok": False, "reason": "shell not running"}` in a plain browser session
# rather than raising, so a model gets an answer it can read out instead of a
# turn that dies.


def desktop_windows(repo_root, ticket=None):
    """Open windows the shell can capture (T-005). Titles and geometry only."""
    return native_bridge.list_windows(repo_root)


def desktop_monitors(repo_root, ticket=None):
    """Monitors the shell can capture (T-005)."""
    return native_bridge.list_monitors(repo_root)


def desktop_screenshot(repo_root, ticket=None, target="screen", window_title="",
                       monitor_id=None, x=None, y=None, width=None, height=None,
                       max_side=None):
    """Capture the screen, a monitor, a window by title, or a region (T-005).

    Gated in `agents.toml` for every hosted backend: the pixels of whatever is
    on screen are the single most sensitive thing this console can send, and
    the human answering the card is the only one who knows what is on it.
    """
    region = None
    if target == "region":
        region = {"x": x or 0, "y": y or 0, "width": width or 0,
                  "height": height or 0}
    return native_bridge.capture(repo_root, target=target,
                                 window_title=window_title,
                                 monitor_id=monitor_id, region=region,
                                 max_side=max_side)


def desktop_ocr(repo_root, ticket=None, capture_id=""):
    """Read the text in a capture already taken (T-005).

    Ungated, unlike the screenshot that produced the capture: the decision
    about whether those pixels could be looked at was made when the capture
    was approved. Asking twice for the same screen would train people to
    click allow without reading.
    """
    if not (capture_id or "").strip():
        return {"ok": False, "reason": "which capture? pass the capture_id "
                                       "returned by desktop-screenshot"}
    return native_bridge.ocr(repo_root, capture_id)


def desktop_clipboard_peek(repo_root, ticket=None):
    """How much text is on the clipboard, and a short preview (T-005).

    Ungated on purpose, and it exists precisely so the gate on the READ can be
    specific: a card that says "will read 1,204 characters" is a decision, a
    card that says "read the clipboard?" is a reflex.
    """
    return native_bridge.clipboard_peek(repo_root)


def desktop_clipboard_read(repo_root, ticket=None):
    """Read the clipboard (T-005). Gated on every backend, local included.

    The clipboard is where a password manager leaves things. Unlike a
    screenshot, the user cannot see what is in it before answering, which is
    why `desktop_clipboard_peek` exists and why this never gets an
    allow-for-this-chat.
    """
    return native_bridge.clipboard_read(repo_root)


def desktop_clipboard_write(repo_root, ticket=None, text=""):
    """Put text on the clipboard (T-005). Ungated, audited.

    The asymmetry with the read above is the point: writing replaces something
    the user can see and can undo by copying again; reading can hand a secret
    to a hosted model.
    """
    return native_bridge.clipboard_write(repo_root, text)
