"""Agents plugin: live agent conversations.

The one plugin that starts real processes, so it is also the most obvious
candidate for `enabled = false` in plugins.toml on a shared or locked-down
checkout — turning it off there removes every route below rather than merely
hiding a button.
"""

from .. import agent_approvals, agent_backends, agent_manager, audit
from .. import provider_overrides
from .. import agents as agents_mod
from .. import model_catalog, prompt_tokens
from ..httpd import EventSource
from ..plugins.base import Plugin

# File-edit tools that a session in acceptEdits mode auto-allows, so the
# mode's blurb ("file writes apply without asking") stays truthful even with
# the approval gate installed.
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def apply(ctx):
    repo_root = ctx.repo_root
    # The server's bound port — httpd writes the actual binding back into the
    # config before plugins load, so a --port override reaches the hook too.
    server_port = int((ctx.config.get("general") or {}).get("port", 8790) or 8790)

    ctx.provide("agents", agent_manager)
    ctx.register_tab(
        "agents", label="Agents", short="Run", icon="cpu", group="main",
        needs_live=True, badge=True,
    )

    # -- discovery ---------------------------------------------------------
    def backends(req):
        reg = agent_backends.registry(repo_root, force=True)
        return {"backends": [b.describe() for b in reg.values()]}

    def catalog(req):
        # One implementation, shared with the `agents catalog` CLI verb. This
        # route used to repeat the globs, so the tab and the CLI could disagree
        # about what the roster even was.
        return agents_mod.list_catalog(repo_root)

    def files(req):
        """Workspace paths for the composer's `#` picker.

        Confined and filtered by `prompt_tokens`, which uses `agent_tools`' own
        skip list and secret patterns — so the picker can never offer a path
        the agent's tools would then refuse to read. `.env` is the one that
        matters: it holds every key this console authenticates with.
        """
        query = (req.query.get("q") or "").strip()
        try:
            limit = max(1, min(int(req.query.get("limit", 25)),
                               prompt_tokens.MAX_FILE_RESULTS))
        except (TypeError, ValueError):
            limit = 25
        return {"query": query,
                "files": prompt_tokens.search_files(repo_root, query, limit)}

    # -- providers (T-012) ---------------------------------------------------
    def providers(req):
        """Every API-capable provider, INCLUDING the switched-off ones.

        Deliberately not `registry()`, which only yields what is enabled: a
        panel that lists only the providers you already turned on cannot be
        the place you turn one on.
        """
        return {"providers": agent_backends.provider_list(repo_root)}

    def providers_post(req):
        """Switch providers on and off, and add or remove your own.

        Audited for the reason `models.refresh` is: this decides which model
        can be handed this workspace's tools.
        """
        committed = [r.get("id") for r in agent_backends.committed_rows(repo_root)]
        stored = provider_overrides.update(repo_root, req.body or {},
                                           committed_ids=committed)
        # A newly enabled provider has to be usable on the NEXT request, not
        # after a restart — `load_config` memoises, and the reachability probe
        # caches its answer for a provider that was not running a moment ago.
        agent_backends.forget_config()
        audit.record(repo_root, "providers.change", actor=audit.actor_of(req),
                     target=",".join(sorted((req.body or {}).get("enabled", {})))
                            or str((req.body or {}).get("remove")
                                   or ((req.body or {}).get("custom") or {}).get("id", "")),
                     detail={"keys": sorted(req.body or {})})
        return {"stored": stored,
                "providers": agent_backends.provider_list(repo_root)}

    def providers_probe(req):
        """Does this endpoint answer, and what does it serve?

        Exists so **Test** works before saving. Adding a provider and finding
        out on the first turn is the version of this that wastes an afternoon
        on a typo in a port number.
        """
        base_url = str((req.body or {}).get("base_url") or "").strip().rstrip("/")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        models_url = base_url + "/models"
        ok, reason = agent_backends.probe(models_url)
        out = {"ok": bool(ok), "reason": reason, "url": models_url}
        if ok:
            names = model_catalog.peek(models_url,
                                       (req.body or {}).get("api_key_env", ""))
            out["models"] = names[:20]
            out["count"] = len(names)
        return out

    def models(req):
        """The CACHED catalogue. Deliberately offline: this is a GET, and a GET
        that reaches a paid third-party API is one a browser will repeat on
        back-navigation and a prefetcher will make unprompted."""
        backend = (req.query.get("backend") or "").strip()
        if not backend:
            return {"providers": model_catalog.summary(repo_root)}
        resolved, why = model_catalog.resolve(repo_root, backend)
        if resolved is None:
            return {"backend": backend, "models": [], "count": 0, "error": why}
        hit = model_catalog.cached(repo_root, backend)
        if not hit:
            return {"backend": backend, "models": [], "count": 0,
                    "error": "no cached catalogue yet"}
        return {"backend": backend, "models": hit["models"],
                "count": hit["count"], "fetched_at": hit["fetched_at"],
                "age_days": hit["age_days"], "error": ""}

    def models_refresh(req):
        """Re-fetch from the provider. A POST because it leaves this machine.

        Audited for the same reason `verb.run` is: it is an outbound call made
        with the workspace's credentials, and "who asked this console to talk
        to OpenRouter" is a question worth being able to answer.
        """
        backend = (req.body.get("backend") or "").strip()
        if not backend:
            raise ValueError("a backend id is required")
        rows, error = model_catalog.fetch(repo_root, backend)
        audit.record(repo_root, "models.refresh", actor=audit.actor_of(req),
                     target=backend, detail={"count": len(rows)},
                     outcome="ok" if not error else "error: %s" % error)
        return {"backend": backend, "models": rows, "count": len(rows),
                "error": error}

    # -- chats -------------------------------------------------------------
    def chats(req):
        return {"chats": agent_manager.list_chats(repo_root)}

    def chat_new(req):
        b = req.body
        snap = agent_manager.create(
            repo_root,
            b.get("backend", ""),
            b.get("prompt", ""),
            mode=b.get("mode", ""),
            model=b.get("model", ""),
            skill=b.get("skill", "") or "",
            persona=b.get("persona", "") or "",
            title=b.get("title", "") or "",
            ticket=b.get("ticket", "") or "",
            server_port=server_port,
        )
        # Starting an agent is the single most consequential thing this API
        # does, so it is the one line the trail must never be missing.
        audit.record(repo_root, "chat.start", actor=audit.actor_of(req),
                     target=snap.get("id", ""),
                     detail={"backend": snap.get("agent", ""),
                             "model": snap.get("model", ""),
                             "ticket": snap.get("ticket", ""),
                             "skill": snap.get("skill", ""),
                             "persona": snap.get("persona", "")})
        return snap

    def chat_resume(req, sid):
        """Pick a past chat back up, in place.

        Audited like a start, because that is what it is from the machine's
        point of view: a CLI process spawned with this repo's files in reach.
        """
        snap = agent_manager.resume(repo_root, sid, server_port=server_port)
        audit.record(repo_root, "chat.resume", actor=audit.actor_of(req),
                     target=sid,
                     detail={"backend": snap.get("agent", ""),
                             "model": snap.get("model", "")})
        return snap

    def chat_get(req, sid):
        return agent_manager.transcript(repo_root, sid)

    def chat_stream(req, sid):
        """SSE. `from` resumes after a reconnect so the client receives
        exactly what it missed, once."""
        try:
            from_seq = int(req.query.get("from", 0))
        except ValueError:
            from_seq = 0
        gen = agent_manager.subscribe(repo_root, sid, from_seq)
        return EventSource(gen, closer=getattr(gen, "close", None))

    def chat_send(req, sid):
        return agent_manager.send(sid, req.body.get("text", ""), req.body.get("mode", "auto"))

    def chat_interrupt(req, sid):
        return agent_manager.interrupt(sid)

    def chat_stop(req, sid):
        audit.record(repo_root, "chat.stop", actor=audit.actor_of(req), target=sid)
        return agent_manager.stop(sid)

    def chat_delete(req, sid):
        return agent_manager.delete(repo_root, sid)

    def chat_rename(req, sid):
        return agent_manager.rename(sid, req.body.get("title", ""))

    def chat_unqueue(req, sid, item_id):
        return agent_manager.unqueue(sid, item_id)

    # -- approval gate -------------------------------------------------------
    def hook_pretooluse(req):
        """Called by hooks/pretooluse.py, and by nothing else. Blocks this
        request thread until a human answers or the registry times out — that
        is the point: the hook process and the agent's tool call are blocked
        too, and ThreadingHTTPServer gives each request its own thread, so one
        parked question does not stall the console."""
        body = req.body
        chat = (body.get("chat") or "").strip()
        tool = (body.get("tool_name") or "").strip()
        if not chat or not tool:
            return {"decision": "deny",
                    "reason": "the console received a malformed approval request."}
        sess = agent_manager.get(chat)
        if sess is None or not sess.alive:
            return {"decision": "deny",
                    "reason": "the console has no live session for this chat."}
        # Mode semantics stay truthful: acceptEdits auto-allows file edits;
        # everything else on the gated list asks a human.
        if (body.get("permission_mode") or sess.mode) == "acceptEdits" and tool in EDIT_TOOLS:
            return {"decision": "allow",
                    "reason": "acceptEdits mode auto-allows file edits"}
        decision, reason = agent_approvals.REGISTRY.request(
            chat, tool, body.get("tool_input") or {},
            body.get("tool_use_id") or "", sess.stream.publish,
            timeout=sess.backend.approval_timeout, repo_root=repo_root,
            title=sess.title)
        return {"decision": decision, "reason": reason}

    def chat_approve(req, sid):
        """Answer a pending approval from the browser."""
        key = (req.body.get("key") or "").strip()
        decision = (req.body.get("decision") or "").strip()
        if not key:
            raise ValueError("an approval key is required")
        p = agent_approvals.REGISTRY.decide(key, decision)
        audit.record(repo_root, "approval.decide", actor=audit.actor_of(req),
                     target=p.tool, detail={"chat": sid, "decision": p.decision})
        sess = agent_manager.get(sid)
        if sess is not None:
            sess.stream.publish({"type": "approval.decided", "key": key,
                                 "tool": p.tool, "decision": p.decision,
                                 "by": p.by})
        return {"ok": True, "key": key, "decision": p.decision}

    ctx.get(r"^/api/agents/backends/?$", backends, "agents.backends")
    ctx.get(r"^/api/agents/catalog/?$", catalog, "agents.catalog")
    ctx.get(r"^/api/agents/files/?$", files, "agents.files")
    ctx.get(r"^/api/agents/providers/?$", providers, "agents.providers")
    ctx.post(r"^/api/agents/providers/?$", providers_post, "agents.providers_post")
    ctx.post(r"^/api/agents/providers/probe/?$", providers_probe, "agents.providers_probe")
    ctx.get(r"^/api/agents/models/?$", models, "agents.models")
    ctx.post(r"^/api/agents/models/refresh/?$", models_refresh, "agents.models_refresh")
    ctx.get(r"^/api/agents/chats/?$", chats, "agents.chats")
    ctx.get(r"^/api/agents/chats/([^/]+)/stream/?$", chat_stream, "agents.stream")
    ctx.get(r"^/api/agents/chats/([^/]+)/?$", chat_get, "agents.chat")

    ctx.post(r"^/api/agents/chats/?$", chat_new, "agents.new")
    ctx.post(r"^/api/agents/chats/([^/]+)/send/?$", chat_send, "agents.send")
    ctx.post(r"^/api/agents/chats/([^/]+)/resume/?$", chat_resume, "agents.resume")
    ctx.post(r"^/api/agents/chats/([^/]+)/interrupt/?$", chat_interrupt, "agents.interrupt")
    ctx.post(r"^/api/agents/chats/([^/]+)/stop/?$", chat_stop, "agents.stop")
    ctx.post(r"^/api/agents/chats/([^/]+)/delete/?$", chat_delete, "agents.delete")
    ctx.post(r"^/api/agents/chats/([^/]+)/rename/?$", chat_rename, "agents.rename")
    ctx.post(r"^/api/agents/chats/([^/]+)/queue/([^/]+)/remove/?$", chat_unqueue, "agents.unqueue")
    ctx.post(r"^/api/agents/hooks/pretooluse/?$", hook_pretooluse, "agents.hook_pretooluse")
    ctx.post(r"^/api/agents/chats/([^/]+)/approve/?$", chat_approve, "agents.approve")


PLUGIN = Plugin(
    id="agents",
    apply=apply,
    summary="Live agent conversations over configurable CLI backends.",
)
