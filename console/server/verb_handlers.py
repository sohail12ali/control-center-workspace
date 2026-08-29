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

from . import context as context_mod
from . import harness_lint
from . import model_catalog
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
