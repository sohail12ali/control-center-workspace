"""Static checks over the harness itself — `.claude/skills/` and `.claude/agents/`.

The harness is prompt-facing config with no compiler behind it: a skill whose
`name` drifts from its directory, an `implements:` pointing at a file someone
renamed, or a skill nothing references at all are all silent failures that only
show up as an agent behaving oddly mid-ticket. This module is the missing
compile step.

## What is and is not an error

ERROR is reserved for things that are unambiguously broken — a missing
frontmatter field, a name that disagrees with its own directory, a path
reference that resolves to nothing. Those fail CI.

WARN covers judgement: an orphan skill (referenced by no agent, no other skill,
and not by CLAUDE.md) is *evidence* that a skill may be dead, not proof — a
skill can be legitimately user-invoked only. Warnings never fail CI, because a
lint that cries wolf gets disabled, and then the errors go unseen too.

Reference checking is deliberately narrow. It follows only EXPLICIT paths —
`.claude/skills/<id>/...`, `.claude/agents/<name>.md` — never a bare word in
backticks. Guessing at prose would produce false positives on every ordinary
noun, and a linter that is wrong about a third of its findings is worse than
no linter.
"""

import os
import re

ERROR = "error"
WARN = "warn"

SKILLS_REL = os.path.join(".claude", "skills")
AGENTS_REL = os.path.join(".claude", "agents")

# `.claude/skills/<id>/<path>` and `.claude/agents/<name>.md`, in any of the
# quoting styles the docs use (backticks, parentheses, bare). The second group
# spans slashes on purpose: `template/scripts/New-FromTemplate.ps1` is one
# reference, and stopping at the first slash would report the *directory*
# `scripts` as a missing file.
_SKILL_PATH_RE = re.compile(r"\.claude/skills/([A-Za-z0-9_-]+)/([A-Za-z0-9_.\-/]*)")
_AGENT_PATH_RE = re.compile(r"\.claude/agents/([A-Za-z0-9_-]+)\.md")

# Prose puts a reference at the end of a sentence or clause often enough that
# not trimming this produces a phantom finding for a path that is really there.
_TRAILING_PUNCT = ".,;:)"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class Finding:
    __slots__ = ("level", "code", "path", "message")

    def __init__(self, level, code, path, message):
        self.level = level
        self.code = code
        self.path = path
        self.message = message

    def as_dict(self):
        return {"level": self.level, "code": self.code,
                "path": self.path, "message": self.message}

    def __str__(self):
        return "%-5s %-22s %s\n      %s" % (
            self.level.upper(), self.code, self.path, self.message)


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _frontmatter(text):
    """The frontmatter block as a flat dict, or None if there is none.

    A hand-rolled scanner rather than YAML: the console runtime is stdlib-only,
    and harness frontmatter is flat `key: value` by convention. A nested or
    multi-line value is reported as unparsed rather than silently mangled.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    out = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in (" ", "\t") or ":" not in line:
            continue  # nested/continuation line — not part of the flat subset
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def _rel(repo_root, path):
    return os.path.relpath(path, repo_root).replace(os.sep, "/")


def _skill_dirs(repo_root):
    base = os.path.join(repo_root, SKILLS_REL)
    if not os.path.isdir(base):
        return []
    bundles = _reference_bundles(repo_root)
    out = []
    for name in sorted(os.listdir(base)):
        if name.startswith("_") or name.startswith("."):
            continue
        if name in bundles:
            continue  # shared reference material, not an invocable skill
        if os.path.isdir(os.path.join(base, name)):
            out.append(name)
    return out


def _reference_bundles(repo_root):
    """Directories under skills/ that hold shared reference material rather
    than an invocable skill — no SKILL.md, but real .md content that other
    skills link to (`challenge-standards/rules.md` is the bundled example).

    They are not skills and must not be counted as such: CLAUDE.md's roster
    count is the number of things a model can invoke, and inflating it by
    directories nothing can load would make the doc wrong.
    """
    base = os.path.join(repo_root, SKILLS_REL)
    if not os.path.isdir(base):
        return set()
    out = set()
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if not os.path.isdir(path) or name.startswith("."):
            continue
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            continue
        if any(f.endswith(".md") for f in os.listdir(path)):
            out.add(name)
    return out


def _agent_files(repo_root):
    base = os.path.join(repo_root, AGENTS_REL)
    if not os.path.isdir(base):
        return []
    return sorted(f for f in os.listdir(base) if f.endswith(".md"))


def _check_frontmatter(repo_root, path, expected_name, kind, findings):
    """Shared skill/agent frontmatter rules. Returns the parsed dict or None."""
    rel = _rel(repo_root, path)
    data = _frontmatter(_read(path))
    if data is None:
        findings.append(Finding(ERROR, "missing-frontmatter", rel,
                                "no --- frontmatter block at the top of the file"))
        return None
    name = data.get("name", "")
    if not name:
        findings.append(Finding(ERROR, "missing-name", rel,
                                "frontmatter has no `name:`"))
    elif name != expected_name:
        findings.append(Finding(
            ERROR, "name-mismatch", rel,
            "frontmatter name is %r but the %s is %r — invocation uses the "
            "%s, so they must agree" % (name, kind, expected_name, kind)))
    if not data.get("description"):
        findings.append(Finding(
            ERROR, "missing-description", rel,
            "frontmatter has no `description:` — this is the text the model "
            "matches against when choosing whether to load it"))
    return data


def _check_references(repo_root, path, skills, agents, findings):
    """Explicit `.claude/...` paths must resolve."""
    rel = _rel(repo_root, path)
    text = _read(path)

    for skill_id, subpath in set(_SKILL_PATH_RE.findall(text)):
        subpath = subpath.rstrip(_TRAILING_PUNCT).rstrip("/")
        if skill_id not in skills and skill_id not in _reference_bundles(repo_root):
            findings.append(Finding(
                ERROR, "dead-skill-path", rel,
                "references .claude/skills/%s/ which does not exist" % skill_id))
            continue
        if not subpath:
            continue  # a bare directory reference; existence checked above
        target = os.path.join(repo_root, SKILLS_REL, skill_id, *subpath.split("/"))
        if not os.path.exists(target):
            findings.append(Finding(
                ERROR, "dead-skill-file", rel,
                "references .claude/skills/%s/%s which does not exist"
                % (skill_id, subpath)))

    for agent_name in set(_AGENT_PATH_RE.findall(text)):
        if agent_name not in agents:
            findings.append(Finding(
                ERROR, "dead-agent-path", rel,
                "references .claude/agents/%s.md which does not exist" % agent_name))


def _referenced_ids(repo_root, skills):
    """Every skill id mentioned anywhere outside its own directory.

    A mention has to look like an *invocation or link*, not just the word:
    `/id`, `` `id` ``, `[[id]]`, or an explicit `.claude/skills/id/` path.

    Matching the bare word instead — the obvious first cut — clears every
    skill immediately, because ids like `plan`, `verify`, `fix` and `estimate`
    are ordinary English that appears in every document in the harness. A
    check that can never fire is worse than no check: it reports "0 orphans"
    and reads as evidence.
    """
    seen = set()
    haystacks = []

    for name in ("CLAUDE.md", "README.md", "CURSOR.md"):
        path = os.path.join(repo_root, name)
        if os.path.isfile(path):
            haystacks.append((None, path))
    for filename in _agent_files(repo_root):
        haystacks.append((None, os.path.join(repo_root, AGENTS_REL, filename)))
    for skill_id in skills:
        skill_dir = os.path.join(repo_root, SKILLS_REL, skill_id)
        for root, _dirs, files in os.walk(skill_dir):
            for filename in files:
                if filename.endswith(".md") or filename.endswith(".json"):
                    haystacks.append((skill_id, os.path.join(root, filename)))

    patterns = {}
    for sid in skills:
        esc = re.escape(sid)
        patterns[sid] = re.compile(
            r"/%s(?![A-Za-z0-9_-])"          # /skill-id  — slash invocation
            r"|`%s`"                          # `skill-id` — cited in prose
            r"|\[\[%s\]\]"                    # [[skill-id]] — wikilink
            r"|\.claude/skills/%s/" % (esc, esc, esc, esc))

    for owner, path in haystacks:
        text = _read(path)
        for skill_id, pattern in patterns.items():
            if skill_id == owner or skill_id in seen:
                continue
            if pattern.search(text):
                seen.add(skill_id)
    return seen


def lint(repo_root):
    """Run every check. Returns (findings, summary-dict)."""
    findings = []
    skills = _skill_dirs(repo_root)
    agent_files = _agent_files(repo_root)
    agents = [f[:-3] for f in agent_files]

    bundles = _reference_bundles(repo_root)
    for skill_id in skills:
        path = os.path.join(repo_root, SKILLS_REL, skill_id, "SKILL.md")
        if not os.path.isfile(path):
            findings.append(Finding(
                ERROR, "empty-skill-dir",
                "%s/%s" % (SKILLS_REL.replace(os.sep, "/"), skill_id),
                "directory has neither a SKILL.md nor any .md content — "
                "nothing can load it and nothing can link to it"))
            continue
        _check_frontmatter(repo_root, path, skill_id, "directory name", findings)
        for root, _dirs, files in os.walk(os.path.join(repo_root, SKILLS_REL, skill_id)):
            for filename in files:
                if filename.endswith(".md"):
                    _check_references(repo_root, os.path.join(root, filename),
                                      skills, agents, findings)

    for filename in agent_files:
        path = os.path.join(repo_root, AGENTS_REL, filename)
        data = _check_frontmatter(repo_root, path, filename[:-3], "filename", findings)
        _check_references(repo_root, path, skills, agents, findings)
        if data and "tools" not in data:
            findings.append(Finding(
                WARN, "no-tools-declared", _rel(repo_root, path),
                "no `tools:` line — the agent inherits every tool, which is "
                "rarely what a scoped role wants"))

    referenced = _referenced_ids(repo_root, skills)
    for skill_id in skills:
        if skill_id not in referenced:
            findings.append(Finding(
                WARN, "orphan-skill",
                "%s/%s" % (SKILLS_REL.replace(os.sep, "/"), skill_id),
                "no agent, skill, or root doc mentions it — may be dead, or "
                "may be user-invoked only"))

    findings.extend(_check_declared_counts(repo_root, skills, agents))

    summary = {
        "skills": len(skills),
        "agents": len(agents),
        "errors": sum(1 for f in findings if f.level == ERROR),
        "warnings": sum(1 for f in findings if f.level == WARN),
    }
    return findings, summary


_COUNT_RE = re.compile(r"(\d+)\s+(skills|agents)\b")


def _check_declared_counts(repo_root, skills, agents):
    """CLAUDE.md states its own roster sizes ("7 agents · 39 skills"). Those
    numbers are read by a model as fact, so drift is worth flagging — as a
    warning, since prose may legitimately count something else."""
    path = os.path.join(repo_root, "CLAUDE.md")
    if not os.path.isfile(path):
        return []
    actual = {"skills": len(skills), "agents": len(agents)}
    out = []
    for count, noun in set(_COUNT_RE.findall(_read(path))):
        if int(count) != actual[noun]:
            out.append(Finding(
                WARN, "stale-count", "CLAUDE.md",
                "says %s %s, but %d exist on disk" % (count, noun, actual[noun])))
    return out


def format_report(findings, summary):
    lines = []
    for level in (ERROR, WARN):
        for finding in findings:
            if finding.level == level:
                lines.append(str(finding))
    lines.append("")
    # ASCII only: this line lands in CI logs and Windows consoles, where a
    # middot or em dash comes out as a replacement character.
    lines.append("%d skills, %d agents | %d error(s), %d warning(s)"
                 % (summary["skills"], summary["agents"],
                    summary["errors"], summary["warnings"]))
    return "\n".join(lines)
