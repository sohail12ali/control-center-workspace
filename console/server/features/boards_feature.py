"""Boards plugin: the ticket/investigation boards and the ticket detail view.

Publishes the `boards`, `tickets` and `trackers` providers that most other
plugins read, so nothing else needs to import those modules directly.
"""

from .. import boards as boards_mod
from .. import render, tickets as tickets_mod, trackers as trackers_mod
from ..plugins.base import Plugin

# Nav metadata per board kind. `short` is what the nav shows on a narrow
# viewport; `icon` names an entry in the frontend's icon set.
_BOARD_NAV = {
    "tickets": {"icon": "columns", "short": "Tix"},
    "investigations": {"icon": "scope", "short": "Invs"},
    "migrations": {"icon": "arrowRight", "short": "Migs"},
    "releases": {"icon": "package", "short": "Rel"},
}


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.provide("boards", boards_mod)
    ctx.provide("tickets", tickets_mod)
    ctx.provide("trackers", trackers_mod)
    ctx.provide("render", render)

    for kind in boards_mod.enabled_boards(repo_root):
        nav = _BOARD_NAV.get(kind, {"icon": "columns", "short": kind[:4].title()})
        ctx.register_tab(
            "board:" + kind,
            label=boards_mod.board_label(kind, repo_root),
            short=nav["short"],
            icon=nav["icon"],
            group="boards",
            badge=True,
            kind=kind,
        )

    def boards_index(req):
        return render.boards_index(repo_root)

    def board_view(req, kind):
        return render.board_view(kind, repo_root)

    def ticket_view(req, ticket_id):
        view = render.ticket_view(ticket_id, repo_root)
        if view is None:
            raise FileNotFoundError(f"ticket not found: {ticket_id}")
        return view

    def tracker_list(req, ticket_id, kind):
        return trackers_mod.list_items(repo_root, ticket_id, kind)

    def tracker_add(req, ticket_id, kind):
        body = dict(req.body)
        text = body.pop("text", "")
        return trackers_mod.add(repo_root, ticket_id, kind, text, **body)

    def tracker_update(req, ticket_id, kind, item_id):
        return trackers_mod.update(repo_root, ticket_id, kind, item_id, **req.body)

    def ticket_move(req, ticket_id):
        return tickets_mod.move(repo_root, ticket_id, req.body.get("stage", ""))

    def ticket_patch(req, ticket_id):
        return tickets_mod.patch(repo_root, ticket_id, req.body)

    def board_priorities(req):
        return {"priorities": list(tickets_mod.PRIORITIES), "default": tickets_mod.DEFAULT_PRIORITY,
                "editable": list(tickets_mod.EDITABLE)}

    ctx.get(r"^/api/boards/?$", boards_index, "boards.index")
    ctx.get(r"^/api/board/([^/]+)/?$", board_view, "boards.view")
    ctx.get(r"^/api/ticket/([^/]+)/?$", ticket_view, "boards.ticket")
    ctx.get(r"^/api/ticket/([^/]+)/trackers/([^/]+)/?$", tracker_list, "trackers.list")
    ctx.post(r"^/api/ticket/([^/]+)/trackers/([^/]+)/?$", tracker_add, "trackers.add")
    ctx.post(r"^/api/ticket/([^/]+)/trackers/([^/]+)/([^/]+)/?$", tracker_update, "trackers.update")
    ctx.post(r"^/api/ticket/([^/]+)/move/?$", ticket_move, "boards.move")
    ctx.post(r"^/api/ticket/([^/]+)/patch/?$", ticket_patch, "boards.patch")
    ctx.get(r"^/api/board-meta/?$", board_priorities, "boards.meta")


PLUGIN = Plugin(
    id="boards",
    apply=apply,
    summary="Ticket/investigation boards, ticket detail, tracker CRUD.",
)
