"""Todos plugin: cross-vault todo aggregation, plus create/move/delete.

A todo can belong to a ticket or to nothing at all, and can be moved between
those at any time — so this owns write routes rather than leaving every
mutation to the ticket-scoped tracker endpoints, which have no way to express
"and now it belongs somewhere else".
"""

from .. import todos_agg
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.register_tab("todos", label="Todos", short="Todo", icon="list", group="main", badge=True)

    def listing(req):
        return todos_agg.all_todos(
            repo_root, status=req.query.get("status"), owner=req.query.get("owner")
        )

    def scopes(req):
        return {"scopes": todos_agg.scopes(repo_root)}

    def create(req):
        body = dict(req.body)
        text = body.pop("text", "")
        scope = body.pop("scope", todos_agg.GENERAL) or todos_agg.GENERAL
        return todos_agg.create(repo_root, text, scope=scope, **body)

    def move(req, scope, item_id):
        target = req.body.get("to", "")
        if not target:
            raise ValueError("a move needs a target scope")
        return todos_agg.move(repo_root, scope, item_id, target)

    def remove(req, scope, item_id):
        return todos_agg.delete(repo_root, scope, item_id)

    ctx.get(r"^/api/todos/?$", listing, "todos.list")
    ctx.get(r"^/api/todos/scopes/?$", scopes, "todos.scopes")
    ctx.post(r"^/api/todos/?$", create, "todos.create")
    ctx.post(r"^/api/todos/([^/]+)/([^/]+)/move/?$", move, "todos.move")
    ctx.post(r"^/api/todos/([^/]+)/([^/]+)/delete/?$", remove, "todos.delete")


PLUGIN = Plugin(
    id="todos",
    apply=apply,
    requires=("boards",),
    summary="Every todo across every ticket, plus unscoped ones.",
)
