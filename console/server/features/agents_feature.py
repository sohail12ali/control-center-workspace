"""Agents plugin: live agent conversations.

The one plugin that starts real processes, so it is also the most obvious
candidate for `enabled = false` in plugins.toml on a shared or locked-down
checkout — turning it off there removes every route below rather than merely
hiding a button.
"""

import glob
import os

from .. import agent_approvals, agent_backends, agent_manager
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
        """Skills and personas read live off disk, so the composer offers this
        checkout's real roster rather than a list that rots."""
        skills = sorted(
            os.path.basename(os.path.dirname(p))
            for p in glob.glob(os.path.join(repo_root, ".claude", "skills", "*", "SKILL.md"))
        )
        personas = sorted(
            os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(repo_root, ".claude", "agents", "*.md"))
        )
        return {"skills": skills, "personas": personas}

    # -- chats -------------------------------------------------------------
    def chats(req):
        return {"chats": agent_manager.list_chats(repo_root)}

    def chat_new(req):
        b = req.body
        return agent_manager.create(
            repo_root,
            b.get("backend", ""),
            b.get("prompt", ""),
            mode=b.get("mode", ""),
            model=b.get("model", ""),
            skill=b.get("skill", "") or "",
            persona=b.get("persona", "") or "",
            title=b.get("title", "") or "",
            server_port=server_port,
        )

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
            timeout=sess.backend.approval_timeout)
        return {"decision": decision, "reason": reason}

    def chat_approve(req, sid):
        """Answer a pending approval from the browser."""
        key = (req.body.get("key") or "").strip()
        decision = (req.body.get("decision") or "").strip()
        if not key:
            raise ValueError("an approval key is required")
        p = agent_approvals.REGISTRY.decide(key, decision)
        sess = agent_manager.get(sid)
        if sess is not None:
            sess.stream.publish({"type": "approval.decided", "key": key,
                                 "tool": p.tool, "decision": p.decision,
                                 "by": p.by})
        return {"ok": True, "key": key, "decision": p.decision}

    ctx.get(r"^/api/agents/backends/?$", backends, "agents.backends")
    ctx.get(r"^/api/agents/catalog/?$", catalog, "agents.catalog")
    ctx.get(r"^/api/agents/chats/?$", chats, "agents.chats")
    ctx.get(r"^/api/agents/chats/([^/]+)/stream/?$", chat_stream, "agents.stream")
    ctx.get(r"^/api/agents/chats/([^/]+)/?$", chat_get, "agents.chat")

    ctx.post(r"^/api/agents/chats/?$", chat_new, "agents.new")
    ctx.post(r"^/api/agents/chats/([^/]+)/send/?$", chat_send, "agents.send")
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
