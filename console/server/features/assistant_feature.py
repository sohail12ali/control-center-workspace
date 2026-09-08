"""Assistant plugin: one reused "Assistant" chat, testable by typing.

T-004 makes the future voice assistant (T-006) testable today: the same
`say`/`session`/`new`/`stream`/`memory` routes a native bridge (T-005) or a
palette box (T-006) will post to, wired here to the ordinary chat machinery
`agents_feature.py` already exercises — one process, `agent_manager.create`,
a `Stream` of normalized events. Nothing about the transport is new; what's
new is that there is exactly ONE chat (the "Assistant" chat, pointed at by
`console/.cache/assistant/session.json`), reused across calls rather than one
per request, and a persona/context injection path threaded through C1.

## The dispatch table, and why it is only half here

`say` is "normalise -> one fast-command match -> its handler, OR one
`agent_manager.send` call, never both" (BR-1). The MATCHING half lives in
`assistant_commands` as pure functions, so the table can be tested without a
backend; the HANDLERS live below, because they need the machinery — verbs, the
session, the native bridge. `say` therefore has exactly one branch point: a
matched command runs its handler and returns, or the text is sent once. What a
handler returns is a spoken string, never another command, so nothing can
re-enter dispatch (the BR-1 regression test pins this).
"""

import calendar
import os
import time

from .. import (agent_backends, agent_manager, assistant,
                assistant_commands, assistant_config, assistant_reply, audit,
                native_bridge, prompt_build, verbs)
from .. import context as context_mod
from ..httpd import EventSource
from ..plugins.base import Plugin

#: The persona id every Assistant chat uses. One constant, not a parameter —
#: there is exactly one Assistant persona (`console/config/assistant.md`),
#: never a per-request choice.
PERSONA = "assistant"

#: T-004 C4's injected-context caps. Each is a belt-and-braces re-cap over a
#: source that (mostly) already caps itself — `context.tickets_digest` at
#: 1,200 and `assistant.memory`'s write-side cap at 1,500 — so the assembly
#: here can never silently exceed its own stated budget even if one of those
#: sources' caps ever drifts.
CONTEXT_DIGEST_CAP = 1_200
CONTEXT_MEMORY_CAP = 1_500
CONTEXT_CAPABILITIES_CAP = 500

#: Fallback only — the live value comes from `assistant_config.settings`,
#: which merges the committed defaults with this machine's choice.
DEFAULT_IDLE_MINUTES = assistant_config.DEFAULTS["session_idle_minutes"]

#: The stream route relays only these event types. Everything else a session
#: emits (usage, tool.*, queue.*, text.delta, ...) is filtered out — a voice
#: or typed UI only needs to know a turn started, something needs a human, a
#: reply arrived, or the turn ended.
#:
#: T-004 listed `attention` and `speaking.*` here, which NOTHING emitted: they
#: were placeholders for the reply watcher deferred to this ticket, so the
#: stream silently carried four event types rather than six. Fixed by naming
#: what a session actually publishes. `reply` is real — `assistant_reply`
#: publishes it, carrying the trimmed spoken form that appears nowhere else.
STREAM_EVENT_TYPES = frozenset({
    "turn.start", "turn.end",
    "text.done", "reply",
    "approval.request", "approval.decided",
    "notice", "error",
})


def _pick_backend(repo_root, requested=""):
    """Which backend a brand-new Assistant chat should use.

    Order and rationale live once, in `assistant_config.resolve_backend`:
    an explicit request, then the stored choice, then local-first. This stays
    as a one-line seam so the call sites below read the same as before.
    """
    return assistant_config.resolve_backend(
        repo_root, agent_backends.registry(repo_root), requested)


def _cap_section(text, cap, label):
    """Truncate `text` to `cap` chars with a stated marker — never silent
    (FR-4 AC2, matching `prompt_build.build`'s own truncation contract)."""
    if len(text) <= cap:
        return text
    return text[:cap].rstrip() + "\n…[%s cut to fit its %d-char cap]" % (label, cap)


def _vision_capable(repo_root, backend):
    """Does the Assistant's chosen backend have a vision-capable model
    configured? Reads the merged settings' `vision_models` list; empty is
    honestly "no" rather than a guess."""
    vision_models = set(assistant_config.settings(repo_root).get(
        "vision_models") or [])
    if not vision_models:
        return False
    backend_models = {m["id"] for m in backend.models}
    backend_models.add(backend.raw.get("default_model", ""))
    return bool(vision_models & backend_models)


def _capabilities_line(repo_root, backend):
    """One line: is this backend local or cloud, does it have a
    vision-capable model, and is the native bridge (C10, T-005) up."""
    locality = "local" if backend.is_local else "cloud"
    vision = "yes" if _vision_capable(repo_root, backend) else "no"
    bridge_ok, bridge_reason = native_bridge.available(repo_root)
    bridge = "available" if bridge_ok else "unavailable (%s)" % bridge_reason
    line = ("Capabilities: backend=%s (%s), vision=%s, native bridge=%s"
           % (backend.id, locality, vision, bridge))
    return _cap_section(line, CONTEXT_CAPABILITIES_CAP, "capabilities")


def _compose_extra(repo_root, backend):
    """FR-4: tickets digest (≤1,200) + memory (≤1,500) + a capabilities line,
    each individually capped with a stated marker, well inside
    `prompt_build.DEFAULT_BUDGET` (24k) in total — composition only, no new
    truncation MECHANISM (that's `prompt_build.build`'s, reused)."""
    digest = _cap_section(context_mod.tickets_digest(repo_root)["text"],
                          CONTEXT_DIGEST_CAP, "tickets digest")
    memory = assistant.read_memory(repo_root)
    sections = ["## Open tickets\n" + digest]
    if memory:
        sections.append("## Remembered\n" +
                        _cap_section(memory, CONTEXT_MEMORY_CAP, "memory"))
    sections.append("## Capabilities\n" + _capabilities_line(repo_root, backend))
    if assistant_config.settings(repo_root).get("speak"):
        # Only when it is actually true. A model told "this will be read aloud"
        # while nothing speaks would write for an audience that does not exist,
        # and the person reading on screen would get the abbreviated version.
        sections.append(
            "## This reply will be read aloud\n"
            "A synthesiser will speak your answer, so write it to be HEARD: no "
            "markdown, no bullet lists, no code fences, no URLs. Two or three "
            "sentences. Say ticket ids the way a person says them (\"T two\", "
            "not \"T dash zero zero two\"). If the full answer needs a list or "
            "code, say the short version out loud and add that the detail is "
            "on screen.")
    return "\n\n".join(sections)


def _session_kwargs(repo_root, backend):
    """Route the Assistant's persona AND injected context to whichever kwarg
    this backend actually reads (FR-3's per-backend injection, FR-4's
    assembly).

    An `openai_api` backend takes `persona=` (read via `prompt_build.build`,
    already wired — C1) and `extra=` separately. Every other transport's own
    `--agent`/persona flag expects an id under `.claude/agents/`, which the
    console-owned persona deliberately is NOT (BR-3) — so for those, BOTH the
    persona text and the injected context go via the one channel C1 gives a
    CLI backend: `system_append` (claude's own flag, or a first-turn
    wire-prefix for a backend with none, e.g. cursor-agent).
    """
    extra = _compose_extra(repo_root, backend)
    if backend.is_api:
        return {"persona": PERSONA, "extra": extra}
    persona_text = prompt_build.persona_text(repo_root, PERSONA)
    combined = "\n\n".join(t for t in (persona_text, extra) if t)
    return {"system_append": combined}


def _minutes_since(iso_ts):
    """Minutes between `iso_ts` (session.json's stamp format) and now, or
    None if it can't be parsed — treated as "not stale" by the caller rather
    than as an error."""
    if not iso_ts:
        return None
    try:
        then = time.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return (calendar.timegm(time.gmtime()) - calendar.timegm(then)) / 60.0


def apply(ctx):
    repo_root = ctx.repo_root
    # Needed to reinstall the approval hook when a chat is resumed: the gate
    # is a settings file pointing at this port, and a resumed session without
    # it would run ungated.
    # `getattr`, because a context without config is a real case (the tests
    # build a minimal one) and it means the same thing as no port: skip the
    # gate installation rather than half-install it, exactly as `create` does.
    _general = (getattr(ctx, "config", None) or {}).get("general") or {}
    server_port = int(_general.get("port", 0) or 0)

    def _current():
        """(live session or None, the pointer or None)."""
        pointer = assistant.read_session(repo_root)
        if not pointer:
            return None, None
        return agent_manager.get(pointer["sid"]), pointer

    def _ensure_session(backend_hint=""):
        """The one reused Assistant chat: alive and fresh -> reuse it; dead,
        idle-timed-out, or never started -> start a new one (FR-2)."""
        sess, pointer = _current()
        if sess is not None and sess.alive:
            idle = _minutes_since(pointer.get("updated_at"))
            window = assistant_config.settings(repo_root).get(
                "session_idle_minutes", DEFAULT_IDLE_MINUTES)
            if idle is None or idle < window:
                # Idempotent: a second `say` must not start a second watcher,
                # or every reply would be spoken twice.
                assistant_reply.watch(repo_root, sess.id)
                return sess
        # A dead pointer is not necessarily a dead conversation. The CLI
        # still remembers this chat by its own session id, so try to pick it
        # up before starting over — a restart of the console (or the shell)
        # otherwise silently costs the Assistant everything it knew.
        if pointer and sess is None:
            try:
                snap = agent_manager.resume(repo_root, pointer["sid"],
                                            server_port=server_port)
                assistant.write_session(repo_root, sid=snap["id"],
                                        backend=snap.get("agent", ""),
                                        model=snap.get("model", ""))
                assistant_reply.watch(repo_root, snap["id"])
                print("assistant: resumed chat %s" % snap["id"])
                return agent_manager.require(snap["id"])
            except (FileNotFoundError, ValueError, OSError) as e:
                # Every one of these is ordinary: no transcript, a backend
                # that cannot resume, a CLI that has forgotten the id. Say
                # which, then start fresh — the one thing not to do is imply
                # continuity that is not there.
                print("assistant: starting a new chat (%s)" % e)

        backend_id = _pick_backend(repo_root, backend_hint)
        backend = agent_backends.get(repo_root, backend_id)
        # Mode and model come from the Assistant's own settings. Without
        # them the chat inherited the BACKEND's defaults, and for claude that
        # is `plan` — the one mode `assistant.toml` explicitly rejects, since
        # the Assistant is asked to create tickets and write to memory and
        # plan mode refuses every write. The model was dropped the same way,
        # which is what made "use ollama" unable to work at all: an
        # OpenAI-compatible endpoint needs to be told which model.
        settings = assistant_config.settings(repo_root)
        snap = agent_manager.create(
            repo_root, backend_id, "Hello.", title="Assistant",
            mode=settings.get("mode", ""), model=settings.get("model", ""),
            **_session_kwargs(repo_root, backend))
        assistant.write_session(repo_root, sid=snap["id"], backend=backend_id,
                                model=snap.get("model", ""))
        # Speaks finished replies and records the last one, which is what
        # `copy that` reads (T-006 / FR-8, deferred out of T-004).
        assistant_reply.watch(repo_root, snap["id"])
        return agent_manager.require(snap["id"])

    # -- fast-command handlers ----------------------------------------------
    # Each returns the SPOKEN string for that command and nothing else. None
    # of them may return another command, which is what keeps BR-1's "one
    # match, one action" true by construction rather than by discipline.

    def _start_new_chat(backend_hint=""):
        """End the current Assistant chat and start a fresh one.

        ONE implementation, called by both the `new chat` command and the
        `/api/assistant/new` route. They had drifted: the route called
        `_ensure_session` without clearing the pointer first, so it returned
        the EXISTING chat and "new chat" did nothing — which also meant a
        changed backend or model never took effect, since those are read when
        a chat is created.
        """
        pointer = assistant.read_session(repo_root)
        if pointer:
            sess = agent_manager.get(pointer["sid"])
            if sess is not None and sess.alive:
                agent_manager.stop(pointer["sid"])
        assistant.clear_session(repo_root)
        return _ensure_session(backend_hint=backend_hint)

    def _h_new_chat():
        sess = _start_new_chat()
        return "New chat on %s." % sess.agent

    def _h_interrupt():
        sess, _pointer = _current()
        if sess is None or not sess.alive:
            return "Nothing is running."
        agent_manager.interrupt(sess.id)
        return "Interrupting."

    def _h_set_speak(speak):
        assistant_config.update(repo_root, {"speak": speak})
        return "Unmuted." if speak else "Muted."

    def _h_use_backend(backend):
        installed = [bid for bid, b in
                     agent_backends.registry(repo_root).items() if b.installed]
        assistant_config.update(repo_root, {"backend": backend},
                                installed_backends=installed)
        # Deliberately does NOT restart the live chat: switching backend
        # mid-conversation would silently drop its context. It takes effect on
        # the next new chat, and the spoken reply says exactly that.
        return "Next chat uses %s." % backend

    def _h_status(ticket):
        data = verbs.run(repo_root, "context", ticket=ticket)
        info = data["ticket"]
        blockers = data.get("blockers") or []
        plan = data.get("plan") or {}
        parts = ["%s is in %s" % (
            info["id"], info.get("stage_label") or info.get("stage") or "no lane")]
        if plan.get("exists"):
            # `context`'s plan["open"] is a CAPPED LIST of open tasks, not a
            # count — total minus done is the real number.
            total = plan.get("total", 0)
            parts.append("%d of %d tasks open"
                         % (total - plan.get("done", 0), total))
        parts.append("%d blocker%s" % (
            len(blockers), "" if len(blockers) == 1 else "s"))
        return ", ".join(parts) + "."

    def _h_digest():
        return verbs.run(repo_root, "tickets-digest")["text"]

    def _h_create_ticket(title):
        result = verbs.run(repo_root, "kickoff", confirm=True,
                           args={"title": title})
        return "Created %s: %s." % (result["id"], result["title"])

    def _h_copy_last():
        text = assistant.read_last_reply(repo_root)
        if not text:
            return "There is no last reply to copy yet."
        ok, reason = native_bridge.available(repo_root)
        if not ok:
            # The honest answer until T-005 writes the bridge pointer file.
            return "I cannot reach the clipboard: %s." % reason
        wrote = native_bridge.clipboard_write(repo_root, text)
        if not wrote.get("ok"):
            return ("I could not write the clipboard: %s."
                    % wrote.get("reason", "unknown"))
        return "Copied."

    def _h_remember(fact):
        result = verbs.run(repo_root, "remember", confirm=True,
                           args={"fact": fact})
        if not result.get("ok"):
            return result.get("reason", "I did not store that.")
        return "Noted."

    HANDLERS = {
        "new_chat": _h_new_chat,
        "interrupt": _h_interrupt,
        "mute": lambda: _h_set_speak(False),
        "unmute": lambda: _h_set_speak(True),
        "use_backend": _h_use_backend,
        "status": _h_status,
        "digest": _h_digest,
        "create_ticket": _h_create_ticket,
        "copy_last": _h_copy_last,
        "remember": _h_remember,
    }

    # -- say -----------------------------------------------------------------
    def say(req):
        body = req.body or {}
        text = (body.get("text") or "").strip()
        source = body.get("source") or "chat"
        if not text:
            return {"result": "error",
                    "reason": "an empty message cannot be sent"}

        cfg = assistant_config.settings(repo_root)
        command = assistant_commands.match(
            text, ticket_prefix=cfg.get("ticket_prefix", "T-"))

        # The one branch point (BR-1): a local command, or a single send.
        if command is not None and command.name != "send":
            try:
                spoken = HANDLERS[command.name](**command.args)
            except Exception as exc:  # noqa: BLE001
                audit.record(repo_root, "assistant.say",
                             actor=audit.actor_of(req), target=source,
                             outcome="error: %s" % exc)
                return {"result": "error", "command": command.name,
                        "reason": str(exc)}
            audit.record(repo_root, "assistant.say", actor=audit.actor_of(req),
                         target=source, detail={"command": command.name},
                         outcome="handled")
            return {"result": "handled", "command": command.name,
                    "spoken": spoken}

        send_text = command.text if command is not None else text
        try:
            sess = _ensure_session()
            result = sess.send(send_text)
            assistant.write_session(repo_root, sid=sess.id, backend=sess.agent,
                                    model=sess.model)
        except Exception as exc:  # noqa: BLE001
            # BR-1's "no second orchestrator" cuts both ways: a backend
            # failure is reported, not raised into a 500 - the caller (a
            # native bridge, a CLI, the palette) always gets a shape it can
            # show, never an unhandled exception.
            audit.record(repo_root, "assistant.say", actor=audit.actor_of(req),
                         target=source, outcome="error: %s" % exc)
            return {"result": "error", "reason": str(exc)}
        audit.record(repo_root, "assistant.say", actor=audit.actor_of(req),
                     target=source, detail={"result": result})
        return {"result": result, "id": sess.id}

    # -- session / new ---------------------------------------------------------
    def session(req):
        sess, pointer = _current()
        if sess is None:
            return {"active": False, "pointer": pointer}
        snap = sess.snapshot()
        snap["active"] = True
        return snap

    def new(req):
        body = req.body or {}
        sess = _start_new_chat(backend_hint=(body.get("backend") or "").strip())
        return sess.snapshot()

    # -- stream ----------------------------------------------------------------
    def stream(req):
        _sess, pointer = _current()
        if not pointer:
            raise FileNotFoundError("no Assistant chat has started yet")
        try:
            from_seq = int(req.query.get("from", 0))
        except ValueError:
            from_seq = 0
        gen = agent_manager.subscribe(repo_root, pointer["sid"], from_seq,
                                      types=STREAM_EVENT_TYPES)
        return EventSource(gen, closer=getattr(gen, "close", None))

    # -- memory ----------------------------------------------------------------
    def memory_get(req):
        return {"memory": assistant.read_memory(repo_root)}

    def memory_post(req):
        fact = (req.body or {}).get("fact", "")
        result = assistant.remember(repo_root, fact)
        audit.record(repo_root, "assistant.remember", actor=audit.actor_of(req),
                     target="memory", detail=result,
                     outcome="ok" if result.get("ok") else "declined")
        return result

    # -- settings (C7 service half; the Settings-tab control is T-006) -------
    def settings_get(req):
        return {"settings": assistant_config.settings(repo_root),
                "writable": sorted(assistant_config.WRITABLE),
                "installed": sorted(
                    bid for bid, b in agent_backends.registry(repo_root).items()
                    if b.installed)}

    def settings_post(req):
        installed = [bid for bid, b in
                     agent_backends.registry(repo_root).items() if b.installed]
        merged = assistant_config.update(repo_root, req.body or {},
                                         installed_backends=installed)
        audit.record(repo_root, "assistant.settings",
                     actor=audit.actor_of(req), target="settings",
                     detail=dict(req.body or {}))
        return {"settings": merged}

    ctx.get(r"^/api/assistant/session/?$", session, "assistant.session")
    ctx.post(r"^/api/assistant/new/?$", new, "assistant.new")
    ctx.post(r"^/api/assistant/say/?$", say, "assistant.say")
    ctx.get(r"^/api/assistant/stream/?$", stream, "assistant.stream")
    ctx.get(r"^/api/assistant/memory/?$", memory_get, "assistant.memory_get")
    ctx.post(r"^/api/assistant/memory/?$", memory_post, "assistant.memory_post")
    ctx.get(r"^/api/assistant/settings/?$", settings_get, "assistant.settings_get")
    ctx.post(r"^/api/assistant/settings/?$", settings_post, "assistant.settings_post")



class _LocalRequest:
    """A request that never came over HTTP.

    `audit.actor_of` reads `client_addr`/`user_agent` off whatever it is
    given and is documented as best-effort, so a local caller supplies the
    same two fields with honest values rather than pretending to be a browser.
    """

    def __init__(self, body=None, query=None):
        self.body = body or {}
        self.query = query or {}
        self.client_addr = "cli"
        self.user_agent = "kanban"


class _CaptureCtx:
    """Collects the plugin's route handlers instead of serving them.

    Deliberately implements only `get`/`post` — the two things `apply` above
    actually calls. Stubbing the rest of the plugin-ctx surface "just in
    case" would both be dead code and quietly defeat the shipped-registry
    test that asserts this file never mentions tab registration.
    """

    def __init__(self, repo_root):
        self.repo_root = repo_root
        self.routes = {}

    def get(self, pattern, fn, name):
        self.routes[name] = fn

    def post(self, pattern, fn, name):
        self.routes[name] = fn


def handlers(repo_root):
    """This plugin's handlers, bound to `repo_root`, with no HTTP server.

    The CLI (`kanban assistant say ...`) must run the SAME `say` the route
    runs — a second implementation of the dispatch would be a second place
    for BR-1 to be violated. Applying the plugin against a capture-only ctx
    yields one implementation with two callers. It also means the CLI gains
    nothing the HTTP surface lacks: no CSRF bypass, because CSRF is enforced
    by `httpd` on the way in, not by these functions.
    """
    ctx = _CaptureCtx(repo_root)
    apply(ctx)
    return ctx.routes


def call(repo_root, name, body=None, query=None):
    """Invoke one handler by its registered name, locally."""
    route = handlers(repo_root).get(name)
    if route is None:
        raise KeyError("no assistant route named %r" % name)
    return route(_LocalRequest(body, query))

PLUGIN = Plugin(
    id="assistant",
    apply=apply,
    summary="One reused Assistant chat, typed-first: say/session/new/stream/memory/settings.",
)
