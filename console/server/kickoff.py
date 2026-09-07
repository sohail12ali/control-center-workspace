"""The `kickoff` verb — the `kickoff` skill's 3 steps, callable without a
model turn (decision-log `kickoff-as-verb-not-agent-turn`).

Mirrors the skill exactly, never a thin `tickets.create` wrapper (BR-5):

    1. `tickets.create` — ticket.toml + tracker TOMLs, console-synced.
    2. Every `_template/*.md` rendered to `{id}-{name}.md` via the existing
       `New-FromTemplate.ps1` (never a Python port — CANONICAL: one
       implementation of template substitution, not two).
    3. One row appended to `knowledge-center/artifact-map.md`, directly under
       the `## Active` heading.

PowerShell 5.1 only, per this workspace's environment. A checkout with no
PowerShell on PATH (routine on macOS/Linux, rare on Windows) fails honestly
with `PowerShellUnavailable` — a distinct type the fast-command layer (C5)
catches to compose a chat fallback instead of surfacing a raw error.
"""

import os
import re
import shutil
import subprocess
from datetime import date

from . import procs
from . import tickets as tickets_mod
from .paths import find_repo_root

TEMPLATE_DIR_REL = os.path.join("knowledge-center", "artifacts", "_template")
ARTIFACT_MAP_REL = os.path.join("knowledge-center", "artifact-map.md")
RENDER_SCRIPT_REL = os.path.join(
    ".claude", "skills", "template", "scripts", "New-FromTemplate.ps1")

#: This workspace's own id scheme (`T-001`, `T-002`, ...). A fork with a
#: different prefix passes its own via `create_ticket(..., prefix=...)`.
DEFAULT_PREFIX = "T-"
ID_WIDTH = 3

RENDER_TIMEOUT = 30


class PowerShellUnavailable(RuntimeError):
    """PowerShell is not on PATH. Distinct from a generic `RuntimeError` so a
    caller (the fast-command table's "create ticket for X" row) can catch
    exactly this and compose an honest chat fallback, rather than treating
    every kickoff failure the same way."""


def next_ticket_id(repo_root, prefix=DEFAULT_PREFIX):
    """The next unused `{prefix}{NNN}` id, scanning existing ticket dirs
    under `knowledge-center/artifacts/`. Zero dirs matching the prefix ->
    `{prefix}001`."""
    data_root = os.path.join(repo_root, "knowledge-center", "artifacts")
    highest = 0
    if os.path.isdir(data_root):
        pattern = re.compile(r"^%s(\d+)$" % re.escape(prefix))
        for name in os.listdir(data_root):
            m = pattern.match(name)
            if m:
                highest = max(highest, int(m.group(1)))
    return "%s%0*d" % (prefix, ID_WIDTH, highest + 1)


def _powershell_exe():
    return shutil.which("powershell") or shutil.which("powershell.exe")


def _render_templates(repo_root, ticket_id, title, *, runner=None):
    """Render every `_template/*.md` into the ticket's own directory.

    `runner` (defaults to `subprocess.run`) is the one seam a test replaces —
    matching the fake-opener idiom used elsewhere in this ticket, rather than
    mocking `subprocess` globally.
    """
    # Only when we are the ones about to invoke PowerShell. An injected
    # `runner` IS the stand-in for it, so demanding the real executable first
    # made the seam useless anywhere PowerShell does not exist — which is
    # every Linux and macOS CI runner, and how this was found.
    if runner is None:
        exe = _powershell_exe()
        if not exe:
            raise PowerShellUnavailable(
                "PowerShell is not on PATH — cannot render templates for %s. "
                "Run the `kickoff` skill by hand, or install PowerShell 5.1+ "
                "(Windows PowerShell; this workspace does not use pwsh)."
                % ticket_id)
    else:
        exe = _powershell_exe() or "powershell"
    template_dir = os.path.join(repo_root, TEMPLATE_DIR_REL)
    script = os.path.join(repo_root, RENDER_SCRIPT_REL)
    target_dir = tickets_mod.dir_for(repo_root, ticket_id)
    run = runner or subprocess.run

    rendered = []
    for name in sorted(os.listdir(template_dir)):
        if not name.endswith(".md"):
            continue
        artifact = name[:-len(".md")]
        template_path = os.path.join(template_dir, name)
        out_path = os.path.join(target_dir, "%s-%s.md" % (ticket_id, artifact))
        result = run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", script, "-TemplatePath", template_path,
             "-OutputPath", out_path, "-Ticket", ticket_id, "-Title", title],
            capture_output=True, text=True, timeout=RENDER_TIMEOUT,
            **procs.popen_kwargs())
        if result.returncode != 0:
            raise RuntimeError(
                "rendering %s for %s failed: %s" % (
                    name, ticket_id,
                    (result.stderr or result.stdout or "").strip()))
        rendered.append(out_path)
    return rendered


def _insert_under_active(text, row):
    """Insert `row` directly under the `## Active` heading — heading-relative,
    never "after the last ticket-shaped row" (the bug this guards against:
    a map whose `## Completed` section is non-empty and whose `## Active`
    section is EMPTY must still land the new row under `## Active`, not at
    the end of the file where the last row happened to be)."""
    lines = text.splitlines()
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "## Active":
            heading_idx = i
            break
    if heading_idx is None:
        raise ValueError("artifact-map.md has no '## Active' heading")

    next_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            next_idx = i
            break

    span = lines[heading_idx + 1:next_idx]
    rows = [line for line in span if line.strip().startswith("-")]
    rows.append(row)
    new_span = [""] + rows + [""]
    lines[heading_idx + 1:next_idx] = new_span

    out = "\n".join(lines)
    if text.endswith("\n"):
        out += "\n"
    return out


def _append_artifact_map_row(repo_root, ticket_id, title, owner):
    path = os.path.join(repo_root, ARTIFACT_MAP_REL)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    row = "- [[%s-summary]] — %s — Open — %s — %s" % (
        ticket_id, title, owner or "(unassigned)", date.today().isoformat())
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_insert_under_active(text, row))
    return row


def create_ticket(repo_root, title, *, kind="tickets", owner="",
                  prefix=DEFAULT_PREFIX, runner=None):
    """The verb's real work — the kickoff skill's 3 steps, in order.

    A partial failure (templates rendered, artifact-map row not yet
    appended) leaves the ticket.toml already created — the same state a
    human running the skill by hand would be in if a step failed midway;
    this does not attempt a rollback the skill itself doesn't have either.
    """
    repo_root = repo_root or find_repo_root()
    title = (title or "").strip()
    if not title:
        raise ValueError("kickoff needs a title")

    ticket_id = next_ticket_id(repo_root, prefix=prefix)
    ticket = tickets_mod.create(repo_root, ticket_id, title, kind=kind, owner=owner)
    rendered = _render_templates(repo_root, ticket_id, title, runner=runner)
    row = _append_artifact_map_row(repo_root, ticket_id, title, owner)
    return {"id": ticket_id, "title": title, "rendered": rendered,
           "artifact_map_row": row, "ticket": ticket}
