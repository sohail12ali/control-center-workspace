"""The tools an API-driven agent holds.

A CLI backend brings its own tools. An API backend has none, so this module is
where the console decides what an agent can do — which makes it both the most
useful and the most dangerous file in the repo.

## Two families

**Console verbs.** Every row in `verbs.toml` becomes a tool, with the schema
generated from its handler signature by the same code the MCP server uses. This
is the payoff of the verb registry: the agent reads a ticket with one `context`
call because that call is a tool it *holds*, not a convention it has to
remember and might not.

**Workspace tools.** `read_file`, `write_file`, `list_files`, `search_files`,
`run_command` — the irreducible minimum for an agent that edits code. Deliberately
few: every tool is surface area, and a model given fifteen overlapping tools
picks the wrong one.

## Confinement

Every path is resolved and checked against the workspace root before anything is
opened. `../` in a model-supplied path is not hypothetical — it is the single
most likely way this loop reaches a file it should not, whether through a
confused model or a prompt-injected instruction in a file it just read.

Confinement is not the whole safety story and is not meant to be: `run_command`
can do anything the shell can, which is why it is gated by default in
`agents.toml` and answered by a human on the "Permission needed" card. The rule
is that a tool is either confined, gated, or both — never neither.

## Results are strings

Every tool returns text, because that is what goes back into the conversation.
Errors return text too, describing what went wrong and what would work instead:
a model that can read the error can correct itself, while an exception just ends
the turn.
"""

import fnmatch
import io
import json
import os
import re
import subprocess

from . import mcp as mcp_mod
from . import verbs as verbs_mod

#: Never read, list, or search inside these, whatever the pattern says. They are
#: large, uninteresting, or contain credentials.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             ".pytest_cache", "dist", "build", ".cache"}

#: Refused outright by the file tools. Confinement stops path escapes; this
#: stops the boring case of an agent reading the key it is authenticating with.
SECRET_PATTERNS = ("*.env", ".env", ".env.*", "*.pem", "*.key", "id_rsa*",
                   "credentials.json", "*.pfx")

MAX_READ_BYTES = 200_000
MAX_SEARCH_HITS = 100
MAX_LIST_ENTRIES = 500
COMMAND_TIMEOUT = 120


class ToolError(Exception):
    """A tool refused or failed in a way the model should read and react to."""


# ------------------------------------------------------------ confinement ---

def _resolve(repo_root, path):
    """An absolute path inside the workspace, or ToolError.

    `os.path.realpath` on both sides so a symlink pointing outside cannot be
    used to step over the boundary — checking the unresolved string would pass
    a link whose target is anywhere at all.
    """
    if not path or not str(path).strip():
        raise ToolError("no path given")
    root = os.path.realpath(repo_root)
    candidate = os.path.realpath(
        path if os.path.isabs(path) else os.path.join(root, path))
    if candidate != root and not candidate.startswith(root + os.sep):
        raise ToolError(
            "%s is outside the workspace. Every path must stay under the "
            "workspace root; use a path relative to it." % path)
    return candidate


def _is_secret(path):
    name = os.path.basename(path)
    return any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_PATTERNS)


def _guard_secret(path):
    if _is_secret(path):
        raise ToolError(
            "%s looks like a credential file and is not readable through this "
            "tool." % os.path.basename(path))


def _rel(repo_root, path):
    return os.path.relpath(path, os.path.realpath(repo_root)).replace(os.sep, "/")


#: Hidden directories that ARE part of the project and must stay walkable —
#: the harness itself lives in one of them.
VISIBLE_DOT_DIRS = {".claude", ".cursor", ".github", ".githooks"}


def _skip_dir(name):
    if name in SKIP_DIRS:
        return True
    return name.startswith(".") and name not in VISIBLE_DOT_DIRS


def _walk(repo_root, base):
    for dirpath, dirnames, filenames in os.walk(base):
        # Pruned in place so os.walk does not descend into them at all.
        dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
        for filename in filenames:
            yield os.path.join(dirpath, filename)


# ---------------------------------------------------------- workspace tools --

def read_file(repo_root, path="", start_line=None, end_line=None):
    full = _resolve(repo_root, path)
    _guard_secret(full)
    if not os.path.isfile(full):
        raise ToolError("%s does not exist or is not a file" % path)
    if os.path.getsize(full) > MAX_READ_BYTES:
        raise ToolError(
            "%s is %d bytes, over the %d-byte read limit. Use search_files to "
            "find the part you need, then read a line range."
            % (path, os.path.getsize(full), MAX_READ_BYTES))
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    first = max(1, int(start_line or 1))
    last = min(len(lines), int(end_line or len(lines)))
    numbered = ["%6d\t%s" % (i, lines[i - 1]) for i in range(first, last + 1)]
    header = "%s (lines %d-%d of %d)" % (path, first, last, len(lines))
    return header + "\n" + "\n".join(numbered)


def write_file(repo_root, path="", content=""):
    full = _resolve(repo_root, path)
    _guard_secret(full)
    existed = os.path.isfile(full)
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content or "")
    return "%s %s (%d bytes)" % ("Overwrote" if existed else "Created",
                                 path, len(content or ""))


def edit_file(repo_root, path="", find="", replace=""):
    """Replace one exact occurrence.

    One, not all: a `replace_all` that silently hits three places is how an
    edit goes wrong in a way nobody notices until later. If the text appears
    more than once the tool refuses and says so, and the model supplies more
    surrounding context.
    """
    full = _resolve(repo_root, path)
    _guard_secret(full)
    if not os.path.isfile(full):
        raise ToolError("%s does not exist" % path)
    if not find:
        raise ToolError("`find` is empty — use write_file to replace a whole file")
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    count = text.count(find)
    if count == 0:
        raise ToolError("that text does not appear in %s (check whitespace and "
                        "indentation — the match is exact)" % path)
    if count > 1:
        raise ToolError("that text appears %d times in %s; include enough "
                        "surrounding context to make it unique" % (count, path))
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace(find, replace or "", 1))
    return "Edited %s" % path


def list_files(repo_root, path="", pattern="*"):
    base = _resolve(repo_root, path or ".")
    if not os.path.isdir(base):
        raise ToolError("%s is not a directory" % (path or "."))
    hits = []
    for full in _walk(repo_root, base):
        rel = _rel(repo_root, full)
        if fnmatch.fnmatch(os.path.basename(full), pattern or "*"):
            hits.append(rel)
        if len(hits) >= MAX_LIST_ENTRIES:
            hits.append("... more than %d entries; narrow the pattern"
                        % MAX_LIST_ENTRIES)
            break
    return "\n".join(sorted(hits)) if hits else "No files matched."


def search_files(repo_root, query="", path="", glob="*"):
    if not query:
        raise ToolError("no query given")
    base = _resolve(repo_root, path or ".")
    try:
        matcher = re.compile(query)
    except re.error as exc:
        raise ToolError("that is not a valid regular expression (%s)" % exc)

    hits = []
    for full in _walk(repo_root, base):
        if not fnmatch.fnmatch(os.path.basename(full), glob or "*"):
            continue
        if _is_secret(full):
            continue
        try:
            with io.open(full, "r", encoding="utf-8", errors="replace") as fh:
                for number, line in enumerate(fh, 1):
                    if matcher.search(line):
                        hits.append("%s:%d: %s" % (_rel(repo_root, full),
                                                   number, line.rstrip()[:300]))
                        if len(hits) >= MAX_SEARCH_HITS:
                            break
        except OSError:
            continue
        if len(hits) >= MAX_SEARCH_HITS:
            hits.append("... stopped at %d matches; narrow the query"
                        % MAX_SEARCH_HITS)
            break
    return "\n".join(hits) if hits else "No matches."


def run_command(repo_root, command="", cwd=""):
    """Run a shell command in the workspace.

    Gated by default in `agents.toml`, because confinement cannot help here —
    a shell can do anything the user can. The gate, not this function, is what
    makes it safe, and the gate is a human reading the command.
    """
    if not (command or "").strip():
        raise ToolError("no command given")
    workdir = _resolve(repo_root, cwd or ".")
    try:
        proc = subprocess.run(command, shell=True, cwd=workdir,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=COMMAND_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ToolError("command exceeded %ds and was killed" % COMMAND_TIMEOUT)
    output = (proc.stdout or "").strip()
    if len(output) > MAX_READ_BYTES:
        output = output[:MAX_READ_BYTES] + "\n... output truncated"
    return "exit %d\n%s" % (proc.returncode, output or "(no output)")


#: name -> (function, description, JSON schema). Kept as data so the tool list
#: and the dispatcher cannot disagree about what exists.
WORKSPACE_TOOLS = {
    "read_file": (read_file, "Read a text file from the workspace, with line numbers.", {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "start_line": {"type": "integer", "description": "First line (1-based)."},
            "end_line": {"type": "integer", "description": "Last line, inclusive."},
        },
        "required": ["path"],
    }),
    "write_file": (write_file, "Create a file or replace its entire contents.", {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string", "description": "The complete new contents."},
        },
        "required": ["path", "content"],
    }),
    "edit_file": (edit_file, "Replace one exact, unique occurrence of some text in a file.", {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "find": {"type": "string",
                     "description": "Exact text to replace. Must appear exactly once."},
            "replace": {"type": "string", "description": "Replacement text."},
        },
        "required": ["path", "find", "replace"],
    }),
    "list_files": (list_files, "List files under a directory, optionally filtered by a glob.", {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory. Defaults to the root."},
            "pattern": {"type": "string", "description": "Filename glob, e.g. *.py"},
        },
        "required": [],
    }),
    "search_files": (search_files, "Search file contents with a regular expression.", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Regular expression."},
            "path": {"type": "string", "description": "Directory to search under."},
            "glob": {"type": "string", "description": "Filename glob to limit the search."},
        },
        "required": ["query"],
    }),
    "run_command": (run_command, "Run a shell command in the workspace and return its output.", {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "cwd": {"type": "string", "description": "Directory to run in."},
        },
        "required": ["command"],
    }),
}

#: Tool names that map to a verb are prefixed, so a verb called `read_file`
#: could never shadow the file tool — and so a reader of a transcript can tell
#: at a glance which calls touched the board.
VERB_PREFIX = "console_"


def verb_tool_name(verb_id):
    return VERB_PREFIX + verb_id.replace("-", "_")


def _verb_id_from_tool(repo_root, name):
    if not name.startswith(VERB_PREFIX):
        return None
    stem = name[len(VERB_PREFIX):]
    for verb_id in verbs_mod.registry(repo_root):
        if verb_tool_name(verb_id) == name or verb_id == stem:
            return verb_id
    return None


def tool_definitions(repo_root, include_workspace=True):
    """OpenAI-shaped tool definitions: workspace tools plus every console verb.

    Verb schemas come from `mcp._schema_for`, the same generator the MCP server
    uses, so an agent on this backend and an agent on Claude Code see identical
    descriptions of the same verb.
    """
    out = []
    if include_workspace:
        for name, (_func, description, schema) in WORKSPACE_TOOLS.items():
            out.append({"type": "function", "function": {
                "name": name, "description": description, "parameters": schema}})

    for verb in sorted(verbs_mod.registry(repo_root).values(), key=lambda v: v.id):
        description = verb.label
        if verb.hint:
            description += " — " + verb.hint
        out.append({"type": "function", "function": {
            "name": verb_tool_name(verb.id),
            "description": description,
            "parameters": mcp_mod._schema_for(verb),
        }})
    return out


def dispatch(repo_root, name, arguments):
    """Run one tool call. Always returns a string — never raises to the loop.

    A tool that raises ends the turn; a tool that returns its error lets the
    model read what went wrong and try something that works.
    """
    arguments = dict(arguments or {})
    try:
        verb_id = _verb_id_from_tool(repo_root, name)
        if verb_id is not None:
            ticket = arguments.pop("ticket", None) or None
            confirm = bool(arguments.pop("confirm", False))
            result = verbs_mod.run(repo_root, verb_id, ticket=ticket,
                                   confirm=confirm, args=arguments)
            return json.dumps(result, indent=2, default=str)

        entry = WORKSPACE_TOOLS.get(name)
        if entry is None:
            return ("No tool named %r. Available: %s"
                    % (name, ", ".join(sorted(WORKSPACE_TOOLS))))
        return entry[0](repo_root, **arguments)
    except ToolError as exc:
        return "Error: %s" % exc
    except verbs_mod.VerbError as exc:
        return "Error: %s" % exc
    except TypeError as exc:
        return "Error: wrong arguments for %s (%s)" % (name, exc)
    except Exception as exc:  # noqa: BLE001
        return "Error: %s: %s" % (type(exc).__name__, exc)
