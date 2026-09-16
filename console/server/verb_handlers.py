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

from . import agent_backends
from . import agent_manager
from . import assistant as assistant_mod
from . import assistant_config
from . import assistant_reply
from . import audit
from . import context as context_mod
from . import harness_lint
from . import kickoff as kickoff_mod
from . import model_catalog
from . import native_bridge
from . import runs as runs_mod
from . import telemetry as telemetry_mod
from . import tickets as tickets_mod
from . import todos_agg
from . import trackers as trackers_mod
# Backend SPI (T-017 FR-5, decision-log a4). `ticket_move` (2b-4) is the one
# pre-existing mutating verb this phase rewires through it; `ready`/`claim`/
# `comment` get their own verb handlers in Phase 3, calling the same
# `backends_mod.default_backend()` singleton (`VaultBackend`, the only
# adapter — 2b-3).
from . import backends as backends_mod
from . import bus as bus_mod


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


def delegate(repo_root, ticket=None, task=""):
    """Hand a task to the work model (T-014).

    The Assistant's `backend`/`model` are the TALK pair — fast, local, good at
    conversation and ticket lookups. Code changes, builds and test runs want a
    different animal, and this is how the talk model asks for one: a new chat
    on `work_backend`, with the task as its opening message.

    Two things it refuses to do. It never runs the task on the talk model when
    no work backend is configured — a local 9B quietly attempting a refactor is
    the worst outcome available. And it never claims to have finished: it
    reports where the work went, and `assistant_reply.watch_delegate` posts the
    result back when there is one.
    """
    task = (task or "").strip()
    if not task:
        return {"ok": False, "error": "say what to delegate"}

    settings = assistant_config.settings(repo_root)
    # Resolved through the local-first work chain rather than read as a single
    # pinned id. It used to refuse outright when `work_backend` was empty,
    # which in practice meant it stayed pinned to whichever CLI someone chose
    # once — so a machine with two local runtimes installed sent every task to
    # a hosted coding agent. An explicit pin still wins; empty now means
    # "pick the best local one that is actually ready".
    skipped = []
    try:
        # `registry` reads the workspace's console config, so it can raise on
        # an incomplete checkout — which this verb must never do: every path
        # is documented to return a shape a model can read out, not an
        # exception. Building the registry only happened here once resolution
        # became a chain, so this guard is new with it.
        registry = agent_backends.registry(repo_root)
        backend_id = assistant_config.resolve_work_backend(
            repo_root, registry, report=skipped)
    except (ValueError, OSError) as exc:
        # Still never the talk model. A 4B chat model quietly attempting a
        # refactor is the worst outcome available, and it was the first thing
        # this verb was written to refuse.
        return {"ok": False, "error":
                "%s I have not run this on the talk model." % exc}
    try:
        backend = agent_backends.get(repo_root, backend_id)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    # A chat whose approval card can never be raised is a chat that hangs on
    # its first gated tool. That happens when this verb runs somewhere with no
    # server behind it — `kanban verb run delegate` from a terminal — because
    # the hook the CLI calls back into needs a port. Refusing beats starting an
    # agent that will sit at `turn.start` forever, which is what it did the
    # first time this was tested.
    port = agent_manager.server_port()
    if backend.gated_tools and backend.transport == "stream_json" and not port:
        return {"ok": False, "error":
                "delegation needs the console server running — the work "
                "agent's approval card has nowhere to appear from here. Start "
                "the console (kanban serve) and delegate from the Assistant."}

    pointer = assistant_mod.read_session(repo_root)
    title = "Delegated: " + (task[:60] + ("…" if len(task) > 60 else ""))
    try:
        snap = agent_manager.create(
            repo_root, backend_id, task, title=title,
            model=(settings.get("work_model") or ""),
            mode=(settings.get("mode") or ""),
            ticket=ticket or "",
            server_port=port)
    except (ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}

    if pointer and pointer.get("sid"):
        assistant_reply.watch_delegate(repo_root, snap["id"], pointer["sid"], task)

    answer = {"ok": True, "chat": snap["id"], "backend": backend_id,
              "model": snap.get("model") or "(backend default)",
              "status": "started — the result will be reported back here"}
    run = runs_mod.create(
        repo_root, ticket=ticket or "", role="work", executor="chat",
        executor_id=snap["id"], backend=backend_id, state="running")
    answer["run"] = run["id"]
    if skipped:
        # Which local runtime was passed over, and why. Without this, work
        # landing on a hosted agent when a local one was meant to take it is
        # invisible — the same silent-fallback problem the talk chain had.
        answer["passed_over"] = ["%s (%s)" % (b, why) for b, why in skipped]
    return answer


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


def launch_role(repo_root, ticket=None, role=""):
    """Start a harness persona as a console `cursor-agent` chat (T-016 FR-6).

    Missing binary fails named. Never falls through to `claude`.
    """
    role = (role or "").strip()
    if role not in runs_mod.ROLES or role in ("work", "assistant"):
        return {"ok": False, "error":
                "role must be one of analyst, planner, builder, verifier, "
                "fixer, harness, deployer"}
    try:
        backend = agent_backends.get(repo_root, "cursor-agent")
    except ValueError as exc:
        return {"ok": False, "error":
                "%s I have not fallen through to another backend." % exc}
    if not backend.installed:
        return {"ok": False, "error":
                "%s I have not fallen through to another backend."
                % backend.unavailable_reason}
    port = agent_manager.server_port()
    task = ("You are the %s for ticket %s. Follow that agent's protocol. "
            "Call console_context first." % (role, ticket))
    try:
        snap = agent_manager.create(
            repo_root, "cursor-agent", task,
            title="%s: %s" % (role, ticket),
            persona=role, ticket=ticket or "", server_port=port)
    except (ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}
    run = runs_mod.create(
        repo_root, ticket=ticket or "", role=role, executor="chat",
        executor_id=snap["id"], backend="cursor-agent", state="running")
    return {"ok": True, "run": run["id"], "chat": snap["id"],
            "backend": "cursor-agent", "role": role}


def run_list(repo_root, ticket=None, state=""):
    """List Run records, optionally filtered by ticket or state."""
    rows = runs_mod.list_runs(repo_root, ticket=ticket, state=state)
    return {"runs": rows, "count": len(rows)}


def run_show(repo_root, ticket=None, run_id=""):
    """One Run by id."""
    rec = runs_mod.get(repo_root, run_id)
    if rec is None:
        return {"ok": False, "error": "no run %s" % run_id}
    return rec


def ticket_move(repo_root, ticket=None, stage=""):
    """Move a ticket to a board lane, through the Backend SPI (T-017 FR-5,
    2b-4) rather than calling `tickets.move` directly — invalid lanes still
    fail there, `VaultBackend.move` is a thin passthrough. Publishes to the
    MCP change-notification bus (T-017 FR-3/1e-4) so a session subscribed to
    `ticket://{ticket}` learns of the move — the one existing mutating verb
    this phase wires in; the new `ready`/`claim`/`comment` verbs land in
    Phase 3 and will publish the same way."""
    result = backends_mod.default_backend().move(repo_root, ticket, stage)
    bus_mod.default().publish("ticket://%s" % ticket)
    return result


def ticket_ready(repo_root, ticket=None, kind=None, stage=None, owner=None):
    """Unblocked, unclaimed tickets (T-017 FR-7, decision-log a6). `ticket`
    is accepted-but-unused: `ready` is a workspace-wide query, not scoped to
    one ticket, but every verb handler shares the `(repo_root, ticket=None,
    **args)` signature `verbs.run` dispatches against. Reuses the Backend
    SPI's `ready` (2b-2), which itself reuses `trackers.blockers` (a6) — no
    second blocking-logic engine. An empty result is a plain empty list, not
    an error (Edge Case §8)."""
    items = backends_mod.default_backend().ready(repo_root, kind=kind,
                                                  stage=stage, owner=owner)
    return {"count": len(items), "tickets": items}


def ticket_claim(repo_root, ticket=None, agent=""):
    """Claim a ticket for an agent identity (T-017 FR-8). Delegates to the
    Backend SPI's `claim`, which is `tickets.set_claim` underneath —
    race-safe (3a-5) via one lock-guarded read-modify-write, so two
    concurrent claims by different identities cannot both succeed. A
    conflicting claim is reported back by name, not silently overwritten
    (Edge Case §8); re-claiming with the same identity is a no-op success
    that refreshes `claimed_at` (3a-6). Audited either way (NFR-5) and
    published to the MCP change-notification bus on success, same pattern as
    `ticket_move`."""
    agent = (agent or "").strip()
    if not agent:
        return {"ok": False, "error": "claim needs an agent identity — pass agent=<id>"}
    try:
        result = backends_mod.default_backend().claim(repo_root, ticket, agent)
    except tickets_mod.ClaimConflictError as exc:
        audit.record(repo_root, "ticket.claim", target=ticket,
                     detail={"agent": agent}, outcome="error: %s" % exc)
        return {"ok": False, "error": str(exc)}
    audit.record(repo_root, "ticket.claim", target=ticket, detail={"agent": agent})
    bus_mod.default().publish("ticket://%s" % ticket)
    return {"ok": True, "ticket": result}


def ticket_comment(repo_root, ticket=None, text="", author=""):
    """Append an attributed, timestamped, non-blocking comment (T-017 FR-9)
    via the Backend SPI's `comment` → the `comments` tracker kind
    (decision-log a2, `trackers.add` already stamps `author`/`posted_on`).
    Audited (NFR-5) and published to the MCP change-notification bus, same
    pattern as `ticket_move`/`ticket_claim`."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "comment needs text"}
    extra = {"author": author} if author else {}
    item = backends_mod.default_backend().comment(repo_root, ticket, text, **extra)
    audit.record(repo_root, "ticket.comment", target=ticket,
                 detail={"author": item.get("author", "")})
    bus_mod.default().publish("ticket://%s" % ticket)
    return item


def ticket_set(repo_root, ticket=None, field="", value=""):
    """Set one editable ticket.toml field. Writer is `tickets.set_field`."""
    return tickets_mod.set_field(repo_root, ticket, field, value)


def tracker_add(repo_root, ticket=None, kind="", text="", type="", priority=""):
    """Add a questions/bugs/todos item. Extra fields stay optional so the
    schema MCP derives from this signature stays small."""
    extra = {}
    if type:
        extra["type"] = type
    if priority:
        extra["priority"] = priority
    return trackers_mod.add(repo_root, ticket, kind, text, **extra)


def tracker_update(repo_root, ticket=None, kind="", item_id="", status="",
                   answer="", priority="", type=""):
    """Patch a tracker item. Empty strings are omitted so a call that only
    sets status does not blank the answer."""
    fields = {}
    if status:
        fields["status"] = status
    if answer:
        fields["answer"] = answer
    if priority:
        fields["priority"] = priority
    if type:
        fields["type"] = type
    return trackers_mod.update(repo_root, ticket, kind, item_id, **fields)


def desktop_clipboard_write(repo_root, ticket=None, text=""):
    """Put text on the clipboard (T-005). Ungated, audited.

    The asymmetry with the read above is the point: writing replaces something
    the user can see and can undo by copying again; reading can hand a secret
    to a hosted model.
    """
    return native_bridge.clipboard_write(repo_root, text)
