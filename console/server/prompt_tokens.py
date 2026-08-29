"""Inline `/skill`, `@agent` and `#file` references, resolved per backend.

## The problem this solves

Skill and persona used to be two dropdowns on the New-chat form, and nothing
else. Once a chat was running there was no way to invoke a skill at all:
`agent_manager.send()` passed the text through `compose_prompt(skill="",
persona="")`, which returns it untouched.

So the composer gets the three triggers every other agent surface has. The
picker is a UI affordance; THIS module is the wire format, and it lives on the
server so the tab and the CLI can never disagree about what `/plan` means.

## A token only transforms if it names something real

`#1234` in "see issue #1234" is not a file. `/` in "and/or" is not a skill.
Rather than inventing an escaping rule nobody will remember, a token is
rewritten **only when it resolves** — a skill that exists, a persona that
exists, a path that is really in the workspace. Everything else stays exactly
as typed, which means prose is safe by default and a typo degrades to plain
text instead of to a broken reference.

## Why the rendering differs per backend

    slash    claude parses `/skill` and `@agent` itself, so they are left
             alone. `#path` becomes `@path`, which is claude's own convention
             for naming a file.
    inline   cursor-agent has no slash-command system, so a reference has to
             become a sentence naming the file on disk.
    none     an API model has neither. It DOES have `read_file`, so a
             reference names the path and lets the agent read it.

## Files are named, never inlined

`#path` does not paste the file into the prompt. The prompt budget is 24k
characters and one file can exceed it on its own; `prompt_build` exists because
a silently truncated instruction is the worst failure available here. Naming
the path costs a dozen tokens and the agent reads what it actually needs.
"""

import fnmatch
import glob
import os
import re

from . import agent_tools

#: Trigger → what it refers to. Deliberately three separate characters rather
#: than one overloaded picker: they resolve against three different rosters,
#: and a single list mixing skills, agents and files is one nobody can scan.
TRIGGERS = {"/": "skill", "@": "persona", "#": "path"}

#: A trigger only fires at a token boundary — start of input, or after
#: whitespace. Without that, `and/or` is a skill and `a@b.com` is a persona.
#: The name must START with an alphanumeric, which is what keeps a markdown
#: heading (`# Heading`, `## Notes`) and a bare `/` out of it.
TOKEN_RE = re.compile(r"(?:(?<=\s)|\A)([/@#])([A-Za-z0-9][A-Za-z0-9._\-/\\]*)")

#: Guard against a pathological paste. A message naming forty files is not a
#: message, and resolving each one stats the disk.
MAX_TOKENS = 40


class Token:
    __slots__ = ("kind", "name", "start", "end", "resolved")

    def __init__(self, kind, name, start, end):
        self.kind = kind
        self.name = name
        self.start = start
        self.end = end
        self.resolved = False

    @property
    def raw(self):
        return {"skill": "/", "persona": "@", "path": "#"}[self.kind] + self.name

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<Token %s:%s resolved=%s>" % (self.kind, self.name, self.resolved)


def scan(text):
    """Every syntactic token in `text`, in order. No disk access."""
    out = []
    for match in TOKEN_RE.finditer(text or ""):
        if len(out) >= MAX_TOKENS:
            break
        out.append(Token(TRIGGERS[match.group(1)], match.group(2),
                         match.start(), match.end()))
    return out


# ----------------------------------------------------------------- roster --
def _skills(repo_root):
    return {os.path.basename(os.path.dirname(p)) for p in
            glob.glob(os.path.join(repo_root, ".claude", "skills", "*", "SKILL.md"))}


def _personas(repo_root):
    return {os.path.splitext(os.path.basename(p))[0] for p in
            glob.glob(os.path.join(repo_root, ".claude", "agents", "*.md"))}


def is_secret(rel):
    """Paths the workspace tools refuse to read.

    Offering one in the picker would be a menu item that cannot work — and the
    one most worth not offering is `.env`, which holds every key the console
    authenticates with. The pattern list is `agent_tools`' own, so the picker
    and the tools can never disagree about what is off limits.
    """
    base = os.path.basename(rel)
    return any(fnmatch.fnmatch(base, pattern)
               for pattern in agent_tools.SECRET_PATTERNS)


def _path_exists(repo_root, name):
    """Is `name` a real file or directory inside the workspace?

    Resolved and confined, because this is a model- or user-supplied path and
    `../` is the obvious way one reaches somewhere it should not.
    """
    candidate = os.path.normpath(os.path.join(repo_root, name))
    root = os.path.abspath(repo_root)
    if not os.path.abspath(candidate).startswith(root + os.sep):
        return False
    if is_secret(name):
        return False
    return os.path.exists(candidate)


def compose(repo_root, text, style, skill="", persona=""):
    """Turn typed text into the form this backend understands.

    Returns `(wire, report)`. `report` names what resolved and what did not, so
    the caller can say "3 references" or explain that `/plna` was a typo rather
    than silently sending it as prose.

    With no `repo_root` there is no roster to resolve against, so tokens are
    left exactly as typed and only the explicit dropdown selections apply —
    which is the behaviour this function had before tokens existed.
    """
    text = (text or "").strip()
    if not repo_root:
        return _prefix_explicit(text, style, skill, persona), _empty_report()
    tokens = scan(text)

    skills, personas = _skills(repo_root), _personas(repo_root)
    for token in tokens:
        if token.kind == "skill":
            token.resolved = token.name in skills
        elif token.kind == "persona":
            token.resolved = token.name in personas
        else:
            token.resolved = _path_exists(repo_root, token.name)

    found = [t for t in tokens if t.resolved]
    report = {
        "skills": [t.name for t in found if t.kind == "skill"],
        "personas": [t.name for t in found if t.kind == "persona"],
        "paths": [t.name for t in found if t.kind == "path"],
        "unresolved": [t.raw for t in tokens if not t.resolved],
    }

    if style == "slash":
        wire = _render_slash(text, found)
    else:
        wire = _render_named(repo_root, text, found)

    # An explicit selection that the text ALREADY names must not be prefixed
    # onto it a second time. For a slash backend `_prefix_explicit` prepends
    # the very same token, so choosing `plan` and typing `/plan` travelled as
    # "/plan /plan do the thing" — the skill named twice, once by each route.
    # Deduped here rather than in the caller because both routes converge on
    # this function, and only this function knows what resolved.
    if skill and skill in report["skills"]:
        skill = ""
    if persona and persona in report["personas"]:
        persona = ""

    # What remains is a statement about the whole chat that the message did not
    # already make; a token is a reference inside one message.
    return _prefix_explicit(wire, style, skill, persona), report


def _empty_report():
    return {"skills": [], "personas": [], "paths": [], "unresolved": []}


def _replace(text, tokens, render):
    """Rewrite tokens right-to-left so earlier offsets stay valid."""
    out = text
    for token in sorted(tokens, key=lambda t: t.start, reverse=True):
        out = out[:token.start] + render(token) + out[token.end:]
    return out


def _render_slash(text, found):
    """claude resolves `/skill` and `@agent` itself; only `#path` needs a
    rewrite, to the `@path` form claude uses for a file."""
    paths = [t for t in found if t.kind == "path"]
    return _replace(text, paths, lambda t: "@" + t.name)


def _render_named(repo_root, text, found):
    """For a backend with no command syntax: the token becomes a plain name,
    and a short preamble says where each referenced thing lives.

    The preamble is separate from the message rather than woven into it so the
    user's own wording survives — an agent reading a mangled sentence answers
    the mangled version.
    """
    body = _replace(text, found, lambda t: t.name)

    lines = []
    for token in found:
        if token.kind == "skill":
            lines.append("Follow the instructions in .claude/skills/%s/SKILL.md."
                         % token.name)
        elif token.kind == "persona":
            lines.append("Act as the %s role in .claude/agents/%s.md."
                         % (token.name, token.name))
    paths = [t.name for t in found if t.kind == "path"]
    if paths:
        # Named, not inlined — see the module docstring.
        lines.append("Referenced in this message (read them if relevant): %s."
                     % ", ".join(paths))
    if not lines:
        return body
    return "\n\n".join(lines + [body])


def _prefix_explicit(text, style, skill, persona):
    """The New-chat dropdowns, applied the way they always were."""
    if style == "none" or (not skill and not persona):
        return text
    if style == "inline":
        bits = []
        if skill:
            bits.append("Follow the instructions in .claude/skills/%s/SKILL.md." % skill)
        if persona:
            bits.append("Act as the %s role in .claude/agents/%s.md." % (persona, persona))
        bits.append(text)
        return "\n\n".join(b for b in bits if b)
    parts = []
    if persona:
        parts.append("@" + persona)
    if skill:
        parts.append("/" + skill)
    prefix = " ".join(parts)
    return (prefix + " " + text).strip() if prefix else text


# ------------------------------------------------------------ file search --
#: A picker is scanned, not read. Past a few dozen rows nobody looks, and the
#: walk costs more than the answer is worth.
MAX_FILE_RESULTS = 50


def search_files(repo_root, query, limit=MAX_FILE_RESULTS):
    """Workspace paths matching `query`, for the `#` picker.

    Skips the same directories the workspace tools skip and refuses the same
    secret patterns, so the picker can never offer a path `read_file` would
    then decline. Directories are included: `#console/server/` is a perfectly
    good thing to point an agent at.
    """
    query = (query or "").strip().replace("\\", "/").lower()
    root = os.path.abspath(repo_root)
    hits = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not agent_tools._skip_dir(d))
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""

        for name in dirnames:
            rel = (rel_dir + "/" + name if rel_dir else name)
            if not query or query in rel.lower():
                hits.append({"path": rel + "/", "kind": "dir"})

        for name in sorted(filenames):
            rel = (rel_dir + "/" + name if rel_dir else name)
            if is_secret(rel):
                continue
            if not query or query in rel.lower():
                hits.append({"path": rel, "kind": "file"})

        if len(hits) > limit * 6:
            break  # enough to rank well without walking a whole monorepo

    # A path whose FILENAME matches beats one that merely sits in a matching
    # directory: typing "agents" should surface agents.js, not forty files
    # under an `agents/` folder.
    def rank(hit):
        base = os.path.basename(hit["path"].rstrip("/")).lower()
        return (0 if query and base.startswith(query) else
                1 if query and query in base else 2,
                len(hit["path"]), hit["path"])

    hits.sort(key=rank)
    return hits[:limit]
