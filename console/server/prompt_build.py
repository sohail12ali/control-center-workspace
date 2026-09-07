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

#: T-004's persona cap (BR-7): ≤4,000 chars, truncated+stated when over, never
#: silent. Small enough that a run-away persona file cannot itself blow the
#: session-argv budget C1 threads it through (`--append-system-prompt`, or a
#: first-turn wire prefix).
PERSONA_CAP = 4_000

_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)

#: Console-owned personas (T-004's `persona-console-owned-second-root`
#: decision) live directly under `console/config/` — `assistant.md` is the
#: first tenant. Tried FIRST, so a persona id with a console-owned file here
#: resolves to it; `.claude/agents/%s.md` stays the fallback for every
#: existing agent persona, unchanged.
PERSONA_ROOT_REL = os.path.join("console", "config")


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
    """The persona's text, tried console-owned root first, capped at
    `PERSONA_CAP` chars (BR-7).

    `console/config/{persona}.md` — the second root T-004 adds, so the
    Assistant's persona (`console/config/assistant.md`) is console-owned
    rather than a synthetic 8th `.claude/agents/` file (BR-3) — wins if it
    exists; `.claude/agents/{persona}.md` is the fallback every pre-existing
    agent persona still resolves through, unchanged.

    The cap is enforced here, in the one place every caller (`build()` for
    `openai_api`, and a CLI backend's `system_append` composition) reads
    persona text from, so a run-away persona file can never silently blow a
    session's argv or prompt budget: it is cut, the cut is stated in the text
    itself, and the cut is audited — never a silent truncation.
    """
    if not persona:
        return ""
    console_owned = os.path.join(repo_root, PERSONA_ROOT_REL, "%s.md" % persona)
    if os.path.isfile(console_owned):
        text = _strip_frontmatter(_read(console_owned))
    else:
        text = _strip_frontmatter(_read(os.path.join(
            repo_root, ".claude", "agents", "%s.md" % persona)))
    if len(text) > PERSONA_CAP:
        text = text[:PERSONA_CAP] + (
            "\n\n_[Persona text cut here — over the %d-char cap. Read the "
            "file itself if you need the rest.]_" % PERSONA_CAP)
        try:
            from . import audit
            audit.record(repo_root, "assistant.persona_truncated",
                         target="persona:%s" % persona,
                         detail={"cap": PERSONA_CAP})
        except Exception:  # noqa: BLE001
            # The audit trail losing an entry must never be why a persona
            # fails to load.
            pass
    return text


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
