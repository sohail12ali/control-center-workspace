"""`console setup cursor|claude|vscode` (T-017 FR-11, Phase 4 slice 4a).

Writes each editor's own documented MCP client config, pointed at this
console's stdio MCP server (`console/mcp_server.py` — the same command this
repo's own root `.mcp.json` already uses as the Claude Code config, which is
the model for the config shape here), plus an idempotent `AGENTS.md` snippet
warning against hand-editing ticket/tracker TOML.

Idempotent by construction: the MCP config write is a dict-merge keyed by
`"console"` under each format's own top-level servers key (so a second run
overwrites only that one entry, never a sibling server another tool already
registered), and the `AGENTS.md` snippet is replaced in place between two
HTML-comment markers rather than appended again.
"""

import json
import os

#: The stdio command every editor's config points at — matches the repo's
#: own root `.mcp.json` (Claude Code's project-scoped MCP config), which
#: predates this ticket and is the model FR-11 names.
MCP_COMMAND = "python"
MCP_ARGS = ["console/mcp_server.py"]

EDITORS = ("cursor", "claude", "vscode")

_AGENTS_START = "<!-- console:agents-snippet:start (T-017 FR-11) -->"
_AGENTS_END = "<!-- console:agents-snippet:end -->"

AGENTS_SNIPPET = """\
## Delivery Console tickets — do not hand-edit

`ticket.toml` and `{T}-{questions,bugs,todos,comments}.toml` under
`knowledge-center/artifacts/` are CLI-mutated only, via
`console/kanban.py` (equally reachable through the MCP tools this editor is
now wired to, or the console's HTTP API — one API, three surfaces). Hand-
editing these files bypasses validation, race-safety, and the audit log.

Use the verbs instead — `python console/kanban.py verb list` for the full,
current list. The ones most relevant day to day: `ticket create/list/show/
move/set`, `tracker add/list/update/blockers`, and the ready-claim-hooks
verbs `ready` (unblocked, unclaimed tickets), `claim` (take a ticket,
race-safe, audited), `comment` (attributed, timestamped, non-blocking).
"""


def _merge_mcp_json(path, servers_key, entry):
    """Read-modify-write `path`'s `servers_key` dict, setting only the
    `"console"` entry. Any other server already registered there, or any
    other top-level key in the file, is preserved untouched. Returns True if
    the file's content actually changed (used for reporting, not gating —
    the write itself is always safe to repeat)."""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError:
            data = {}
    else:
        data = {}
    servers = data.setdefault(servers_key, {})
    changed = servers.get("console") != entry
    servers["console"] = entry
    if changed:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    return changed


def _write_agents_snippet(repo_root):
    path = os.path.join(repo_root, "AGENTS.md")
    block = _AGENTS_START + "\n" + AGENTS_SNIPPET + _AGENTS_END + "\n"
    content = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    if _AGENTS_START in content and _AGENTS_END in content:
        pre, _, rest = content.partition(_AGENTS_START)
        _, _, post = rest.partition(_AGENTS_END)
        post = post.lstrip("\n")
        new_content = pre + block + (("\n" + post) if post else "")
    elif content:
        new_content = content.rstrip("\n") + "\n\n" + block
    else:
        new_content = "# AGENTS.md\n\n" + block
    changed = new_content != content
    if changed:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
    return changed


def setup_editor(repo_root, editor):
    """Write `editor`'s MCP config + the AGENTS.md snippet. Returns a dict
    describing what happened — safe to call repeatedly (FR-11 idempotency)."""
    if editor not in EDITORS:
        raise ValueError("unknown editor %r; choose one of %s" % (editor, EDITORS))

    entry_stdio = {"command": MCP_COMMAND, "args": MCP_ARGS}
    if editor == "cursor":
        # Cursor's project MCP config: .cursor/mcp.json, "mcpServers" key —
        # the same shape as Claude Code's own root .mcp.json.
        config_path = os.path.join(repo_root, ".cursor", "mcp.json")
        mcp_changed = _merge_mcp_json(config_path, "mcpServers", entry_stdio)
    elif editor == "claude":
        # Claude Code's project-scoped MCP config already lives at the repo
        # root as .mcp.json (predates this ticket) — merge into it rather
        # than writing a second, competing file.
        config_path = os.path.join(repo_root, ".mcp.json")
        mcp_changed = _merge_mcp_json(config_path, "mcpServers", entry_stdio)
    else:  # vscode
        # VS Code's MCP config: .vscode/mcp.json, "servers" key, each entry
        # additionally names its transport type.
        config_path = os.path.join(repo_root, ".vscode", "mcp.json")
        entry = dict(entry_stdio, type="stdio")
        mcp_changed = _merge_mcp_json(config_path, "servers", entry)

    agents_changed = _write_agents_snippet(repo_root)
    return {
        "editor": editor,
        "mcp_config": os.path.relpath(config_path, repo_root).replace(os.sep, "/"),
        "mcp_changed": mcp_changed,
        "agents_md": "AGENTS.md",
        "agents_changed": agents_changed,
    }
