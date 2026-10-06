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

#: Claude Code only (T-024 FR-3): hands the server the main repo when a console
#: agent runs in a ticket worktree. Claude expands `${VAR:-}` to empty when the
#: variable is unset, which `paths.find_repo_root` ignores.
MCP_CLAUDE_ENV = {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"}

EDITORS = ("cursor", "claude", "vscode")

EDITOR_LABELS = {"cursor": "Cursor", "claude": "Claude", "vscode": "VS Code"}

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


def _editor_target(repo_root, editor):
    """`(path, servers_key)` for one editor's MCP file. Same paths
    `setup_editor` writes, so "already wired" and "write" cannot drift."""
    if editor == "cursor":
        return os.path.join(repo_root, ".cursor", "mcp.json"), "mcpServers"
    if editor == "claude":
        return os.path.join(repo_root, ".mcp.json"), "mcpServers"
    return os.path.join(repo_root, ".vscode", "mcp.json"), "servers"


def editor_status(repo_root):
    """Which editors already have the console MCP entry. No secrets: these
    files name a command, not a credential."""
    rows = []
    for editor in EDITORS:
        path, key = _editor_target(repo_root, editor)
        wired = False
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                data = {}
            servers = data.get(key) if isinstance(data, dict) else None
            wired = isinstance(servers, dict) and "console" in servers
        rows.append({
            "id": editor,
            "label": EDITOR_LABELS[editor],
            "wired": wired,
            "path": os.path.relpath(path, repo_root).replace(os.sep, "/"),
        })
    return rows


def setup_editor(repo_root, editor):
    """Write `editor`'s MCP config + the AGENTS.md snippet. Returns a dict
    describing what happened — safe to call repeatedly (FR-11 idempotency)."""
    if editor not in EDITORS:
        raise ValueError("unknown editor %r; choose one of %s" % (editor, EDITORS))

    entry_stdio = {"command": MCP_COMMAND, "args": MCP_ARGS}
    config_path, servers_key = _editor_target(repo_root, editor)
    if editor == "claude":
        # Claude Code expands ${CONSOLE_REPO_ROOT:-} so an agent running in a
        # ticket worktree still finds the main repo. The other editors do not.
        entry = dict(entry_stdio, env=dict(MCP_CLAUDE_ENV))
    elif editor == "vscode":
        # VS Code's entry additionally names its transport type.
        entry = dict(entry_stdio, type="stdio")
    else:
        entry = entry_stdio
    mcp_changed = _merge_mcp_json(config_path, servers_key, entry)

    agents_changed = _write_agents_snippet(repo_root)
    return {
        "editor": editor,
        "mcp_config": os.path.relpath(config_path, repo_root).replace(os.sep, "/"),
        "mcp_changed": mcp_changed,
        "agents_md": "AGENTS.md",
        "agents_changed": agents_changed,
    }
