"""What a gated tool call would actually do, shown before it does it.

## The problem this fixes

The approval card used to render the tool's arguments as JSON. For a file write
that means a wall of escaped text with `\\n` between every line, and for an edit
it means two opaque strings. Nobody reads that. They click Allow because the
alternative is reading four hundred characters of escaped JSON to find out
whether one line changed — and a gate that is always approved without reading is
not a gate, it is a speed bump with a log.

So the console computes a **diff** and sends it with the request. Reviewing "3
lines changed in `console/server/verbs.py`" is a thing a person will actually
do.

## Server-side on purpose

Computing this in the browser would need a new endpoint to fetch the current
file, an authorisation question about what that endpoint may read, and a second
implementation for anyone who is not the browser. The server already has the
repo root and the tool input, and both backends — the CLI hook path and the
in-process API loop — go through one registry, so one implementation covers
both.

## Truthful about what it does not know

A preview is a prediction. `write_file` is exact. `edit_file` is exact if its
target text is found, and says so when it is not. `run_command` cannot be
previewed at all beyond showing the command, and this module does not pretend
otherwise — it returns a `command` preview and leaves the judgement to the
person, which is the honest division of labour.
"""

import difflib
import os

MAX_DIFF_LINES = 400
MAX_LINE_CHARS = 400
MAX_CONTENT_BYTES = 400_000

#: tool name -> how to read its arguments. Covers both naming conventions: the
#: Claude Code tools that arrive through the hook, and this console's own tools
#: that the API loop calls.
WRITE_TOOLS = {
    "Write": ("file_path", "content"),
    "write_file": ("path", "content"),
}
EDIT_TOOLS = {
    "Edit": ("file_path", "old_string", "new_string"),
    "edit_file": ("path", "find", "replace"),
}
COMMAND_TOOLS = {
    "Bash": "command",
    "run_command": "command",
}


def _read(repo_root, path):
    """Current contents of a file, or None if it does not exist / cannot be read."""
    if not path:
        return None
    full = path if os.path.isabs(path) else os.path.join(repo_root, path)
    try:
        if not os.path.isfile(full):
            return None
        if os.path.getsize(full) > MAX_CONTENT_BYTES:
            return None
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _rel(repo_root, path):
    """A workspace-relative path for display.

    `os.path.relpath` resolves a RELATIVE input against the process working
    directory, not against `repo_root` — so a tool argument that was already
    relative came back as `../../../..` walking out of wherever the server
    happened to be started. That went unnoticed on Windows only because the
    workspace and the cwd were often on different drives, which raises and hit
    the fallback below; on Linux there is no drive to differ and the wrong
    answer was returned instead.

    A tool path is relative to the workspace by contract, so an already
    relative one is simply normalised.
    """
    if not os.path.isabs(path):
        return path.replace(os.sep, "/")
    try:
        rel = os.path.relpath(path, repo_root)
    except ValueError:
        # Different drives on Windows: not inside the workspace at all.
        return path
    # Outside the workspace: show it as given rather than as a walk upwards.
    if rel.startswith(os.pardir + os.sep) or rel == os.pardir:
        return path.replace(os.sep, "/")
    return rel.replace(os.sep, "/")


def _diff(before, after, path):
    """A unified diff as structured lines the UI can colour.

    Returned as data rather than a formatted string so the browser controls
    presentation — and so the counts are computed once, here, instead of by
    counting `+` prefixes in the client and getting the `+++` header wrong.
    """
    before_lines = (before or "").splitlines()
    after_lines = (after or "").splitlines()
    rows, added, removed = [], 0, 0

    for line in difflib.unified_diff(before_lines, after_lines, lineterm="", n=3):
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            rows.append({"kind": "hunk", "text": line})
            continue
        kind = "context"
        if line.startswith("+"):
            kind, added = "add", added + 1
        elif line.startswith("-"):
            kind, removed = "remove", removed + 1
        text = line[1:] if line[:1] in "+- " else line
        rows.append({"kind": kind, "text": text[:MAX_LINE_CHARS]})

    truncated = len(rows) > MAX_DIFF_LINES
    return {
        "kind": "diff",
        "path": path,
        "lines": rows[:MAX_DIFF_LINES],
        "added": added,
        "removed": removed,
        "truncated": truncated,
        "omitted": max(0, len(rows) - MAX_DIFF_LINES),
    }


def build(repo_root, tool, tool_input):
    """A preview for one gated call, or None when there is nothing useful to show.

    None is a real answer: for a tool this module does not understand, the card
    falls back to the arguments, which is no worse than before and honest about
    knowing nothing extra.
    """
    tool_input = tool_input or {}

    if tool in COMMAND_TOOLS:
        command = str(tool_input.get(COMMAND_TOOLS[tool]) or "").strip()
        if not command:
            return None
        return {"kind": "command", "command": command,
                "cwd": str(tool_input.get("cwd") or "") or "."}

    if tool in WRITE_TOOLS:
        path_key, content_key = WRITE_TOOLS[tool]
        path = str(tool_input.get(path_key) or "")
        if not path:
            return None
        after = tool_input.get(content_key)
        if not isinstance(after, str):
            return None
        before = _read(repo_root, path)
        preview = _diff(before, after, _rel(repo_root, path))
        preview["creating"] = before is None
        return preview

    if tool in EDIT_TOOLS:
        path_key, find_key, replace_key = EDIT_TOOLS[tool]
        path = str(tool_input.get(path_key) or "")
        find = tool_input.get(find_key)
        replace = tool_input.get(replace_key)
        if not path or not isinstance(find, str):
            return None
        before = _read(repo_root, path)
        if before is None:
            return {"kind": "note", "path": _rel(repo_root, path),
                    "text": "This edit targets a file that does not exist or "
                            "cannot be read, so no preview is possible."}
        count = before.count(find)
        if count == 0:
            # Worth surfacing before approval: the call is going to fail, and
            # approving it wastes a round trip.
            return {"kind": "note", "path": _rel(repo_root, path),
                    "text": "The text this edit looks for does not appear in "
                            "the file. The call will fail."}
        after = before.replace(find, replace if isinstance(replace, str) else "", 1)
        preview = _diff(before, after, _rel(repo_root, path))
        preview["creating"] = False
        if count > 1:
            preview["warning"] = (
                "That text appears %d times; only the first would be replaced."
                % count)
        return preview

    return None
