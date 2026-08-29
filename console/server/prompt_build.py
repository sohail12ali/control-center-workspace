"""System prompt assembly for backends with no slash-command system.

A CLI backend is told `@builder /plan CC-T001` and resolves the persona and the
skill itself. An API model has no such machinery: if the skill's text is not in
the prompt, the skill does not exist. So "choose a skill" on this backend means
**inject its file**, which is why the roadmap's token work is a prerequisite for
its OpenRouter work rather than a parallel track — every skill is now paid for
in tokens on every turn that selects it.

## What goes in, in order

1. **The always-on core** — `harness-standards/core.md`. The gates and the
   honesty rule apply to every agent regardless of persona.
2. **The persona** — `.claude/agents/{name}.md`, frontmatter stripped. It is
   metadata for the CLI's own loader and means nothing to a model.
3. **The skill** — `.claude/skills/{id}/SKILL.md`, also stripped.
4. **Workspace orientation** — where it is, what the tools are for, and the one
   instruction that saves the most tokens: prefer `console_context` over
   reading a ticket's files.

## Budget

Capped, and **what was cut is stated in the prompt itself**. A silently
truncated skill is the worst failure available here: the agent believes it has
its instructions, follows the half it received, and nobody can tell from the
transcript that the other half was dropped.
"""

import os
import re

DEFAULT_BUDGET = 24_000  # characters, ~6k tokens

_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _strip_frontmatter(text):
    """Frontmatter is loader metadata, not instruction. Sending it spends
    tokens telling the model about a tools list it does not control."""
    return _FRONTMATTER_RE.sub("", text, count=1).strip()


def core_text(repo_root):
    return _strip_frontmatter(_read(os.path.join(
        repo_root, ".claude", "skills", "harness-standards", "core.md")))


def persona_text(repo_root, persona):
    if not persona:
        return ""
    return _strip_frontmatter(_read(os.path.join(
        repo_root, ".claude", "agents", "%s.md" % persona)))


def skill_text(repo_root, skill):
    if not skill:
        return ""
    return _strip_frontmatter(_read(os.path.join(
        repo_root, ".claude", "skills", skill, "SKILL.md")))


def orientation(repo_root, ticket=""):
    lines = [
        "# Workspace",
        "",
        "You are working in a Delivery Console workspace at `%s`."
        % repo_root.replace("\\", "/"),
        "",
        "Tools come in two families:",
        "",
        "- `console_*` tools answer questions about the board and its tickets. "
        "They are computed, exact, and cheap.",
        "- `read_file`, `write_file`, `edit_file`, `list_files`, "
        "`search_files`, `run_command` act on the workspace. Paths are "
        "relative to the workspace root and cannot leave it.",
        "",
        "**Call `console_context` before reading a ticket's files.** It returns "
        "the lane, blockers, unchecked plan tasks, open trackers and recent "
        "progress in one call, about sixteen times smaller than reading the "
        "artifacts. Only open an artifact the digest points you at, or one it "
        "says was truncated.",
        "",
        "Ticket and tracker state is TOML mutated only through the console. "
        "Never hand-edit `ticket.toml` or a `*-questions.toml` / `*-bugs.toml` "
        "/ `*-todos.toml` file.",
    ]
    if ticket:
        lines += ["", "The current ticket is **%s**." % ticket]
    return "\n".join(lines)


def build(repo_root, *, persona="", skill="", ticket="", budget=DEFAULT_BUDGET,
          extra=""):
    """Assemble the system prompt. Returns (text, report).

    `report` says what was included and what was cut, so the caller can show it
    and a transcript can be audited later.
    """
    sections = [
        ("orientation", orientation(repo_root, ticket)),
        ("harness core", core_text(repo_root)),
    ]
    if persona:
        body = persona_text(repo_root, persona)
        sections.append(("persona: %s" % persona, body or
                         "_(no agent file found for persona %r)_" % persona))
    if skill:
        body = skill_text(repo_root, skill)
        sections.append(("skill: %s" % skill, body or
                         "_(no SKILL.md found for skill %r)_" % skill))
    if extra:
        sections.append(("extra", extra))

    report = {"included": [], "truncated": [], "missing": [], "chars": 0}
    if persona and not persona_text(repo_root, persona):
        report["missing"].append("persona:%s" % persona)
    if skill and not skill_text(repo_root, skill):
        report["missing"].append("skill:%s" % skill)

    parts, used = [], 0
    for name, body in sections:
        if not body:
            continue
        block = body
        remaining = budget - used
        if remaining <= 0:
            report["truncated"].append(name)
            continue
        if len(block) > remaining:
            block = block[:remaining] + (
                "\n\n_[This section was cut here to fit the prompt budget. "
                "Read the file itself if you need the rest.]_")
            report["truncated"].append(name)
        parts.append(block)
        report["included"].append(name)
        used += len(block)

    if report["truncated"]:
        parts.append(
            "\n---\n\n_Prompt budget note: %s did not fit in full. Treat "
            "anything cut as unread, and open the file if you need it._"
            % ", ".join(report["truncated"]))

    text = "\n\n---\n\n".join(parts)
    report["chars"] = len(text)
    return text, report
