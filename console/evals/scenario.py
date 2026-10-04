"""Scenario TOML: load, validate, provenance, and selection.

Parsed with server.tomlio only. A value that still starts with a quote
character is the symptom of a trailing comment or a single-quoted literal,
and is rejected with the file and key named.
"""

import hashlib
import os
import re

from server import tomlio

from evals.grade import (
    BAD_FIXTURE,
    BAD_SCENARIO,
    CHECK_ERROR,
    KINDS,
    RULE_MOVED,
    SUBJECT_MISSING,
    GradingError,
    Problem,
)

_ID_RE = re.compile(r"^[a-z0-9-]+$")
_SCENARIO_KEYS = {
    "id", "title", "persona", "skill", "ticket", "prompt", "subjects",
    "mode", "max_tool_calls", "fail_checks",
}
_SOURCE_KEYS = {"file", "quote"}
_CHECK_KEYS = {
    "id", "kind", "why", "match", "min", "max", "first", "before",
    "scope", "present", "disposition",
}
_CORE_FILES = ("CLAUDE.md", ".claude/settings.json")


def _sha(path):
    with open(path, "rb") as fh:
        data = fh.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _reject_quoted(value, file, key):
    if isinstance(value, str) and value[:1] in ("'", '"'):
        raise GradingError(
            BAD_SCENARIO,
            "value starts with a quote character (trailing comment or single quotes?)",
            file=file, key=key)
    if isinstance(value, str) and key.endswith("quote") and "\n" in value:
        raise GradingError(BAD_SCENARIO, "quote contains a newline", file=file, key=key)


def _walk(value, file, key):
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, file, (key + "." + k) if key else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk(v, file, "%s[%d]" % (key, i))
    else:
        _reject_quoted(value, file, key)


def _unknown(keys, allowed, file, table):
    extra = [k for k in keys if k not in allowed]
    if extra:
        raise GradingError(BAD_SCENARIO, "unknown key %s" % ", ".join(sorted(extra)),
                           file=file, key=table + "." + extra[0])


def _fixtures_dir_for(path, fixtures_dir):
    if fixtures_dir:
        return fixtures_dir
    return os.path.join(os.path.dirname(os.path.dirname(path)), "fixtures")


class Scenario:
    def __init__(self, data, path, sha, fixtures_dir):
        self.data = data
        self.path = path
        self.sha256 = sha
        self.fixtures_dir = fixtures_dir
        s = data.get("scenario") or {}
        self.id = s.get("id") or ""
        self.title = s.get("title") or self.id
        self.persona = s.get("persona") or ""
        self.skill = s.get("skill") or ""
        self.ticket = s.get("ticket") or ""
        self.prompt = s.get("prompt") or ""
        self.subjects = list(s.get("subjects") or [])
        self.mode = s.get("mode") or ""
        self.max_tool_calls = int(s.get("max_tool_calls") or 25)
        self.fail_checks = list(s.get("fail_checks") or [])
        self.sources = list(data.get("source") or [])
        self.checks = list(data.get("check") or [])

    def fixture_path(self, which):
        return os.path.join(self.fixtures_dir, "%s.%s.jsonl" % (self.id, which))


def validate(data, path, fixtures_dir=None):
    """Raise GradingError (class grading) or return a Scenario."""
    file = os.path.basename(path)
    if not isinstance(data, dict) or "scenario" not in data:
        raise GradingError(BAD_SCENARIO, "missing [scenario]", file=file, key="scenario")
    _walk(data, file, "")
    s = data["scenario"]
    if not isinstance(s, dict):
        raise GradingError(BAD_SCENARIO, "[scenario] is not a table", file=file, key="scenario")
    _unknown(s.keys(), _SCENARIO_KEYS, file, "scenario")
    for src in data.get("source") or []:
        _unknown(src.keys(), _SOURCE_KEYS, file, "source")
    seen = set()
    for check in data.get("check") or []:
        _unknown(check.keys(), _CHECK_KEYS, file, "check")
        kind = check.get("kind")
        if kind not in KINDS:
            raise GradingError(BAD_SCENARIO, "unknown check kind %r" % kind,
                               file=file, key="check.kind")
        cid = check.get("id") or ""
        if not cid or cid in seen:
            raise GradingError(BAD_SCENARIO, "duplicate or empty check id %r" % cid,
                               file=file, key="check.id")
        seen.add(cid)
        for rex_key in ("match", "first", "before"):
            if check.get(rex_key):
                try:
                    re.compile(check[rex_key])
                except re.error as exc:
                    raise GradingError(BAD_SCENARIO, "invalid regex: %s" % exc,
                                       file=file, key="check." + rex_key)
    sid = s.get("id") or ""
    if not _ID_RE.match(sid) or os.path.splitext(file)[0] != sid:
        raise GradingError(BAD_SCENARIO, "id must match the filename and ^[a-z0-9-]+$",
                           file=file, key="scenario.id")
    prompt = s.get("prompt") or ""
    if "\n" in prompt or len(prompt) > 800:
        raise GradingError(BAD_SCENARIO, "prompt must be one line of at most 800 characters",
                           file=file, key="scenario.prompt")
    if s.get("mode") != "plan":
        raise GradingError(BAD_SCENARIO, "mode must be plan", file=file, key="scenario.mode")
    known = {c.get("id") for c in data.get("check") or []}
    for fid in s.get("fail_checks") or []:
        if fid not in known:
            raise GradingError(BAD_SCENARIO, "fail_checks names unknown id %r" % fid,
                               file=file, key="scenario.fail_checks")
    fdir = _fixtures_dir_for(path, fixtures_dir)
    for which in ("pass", "fail"):
        fixture = os.path.join(fdir, "%s.%s.jsonl" % (sid, which))
        if not os.path.isfile(fixture):
            raise GradingError(BAD_FIXTURE, "missing fixture %s" % os.path.basename(fixture),
                               file=file, key="fixture")
    scenario = Scenario(data, path, _sha(path), fdir)
    assert_not_vacuous(scenario)
    return scenario


def assert_not_vacuous(scenario):
    """A positive check is a call with room to match, a first_call, or a
    text check that expects a match. order and end do not count."""
    for check in scenario.checks:
        kind = check.get("kind")
        if kind == "first_call":
            return scenario
        if kind == "text" and check.get("present", True) is not False:
            return scenario
        if kind == "call" and check.get("max", None) != 0 and check.get("min", 1) >= 1:
            return scenario
    raise GradingError(BAD_SCENARIO, "vacuous: no positive check",
                       file=os.path.basename(scenario.path), key="check")


def load_file(path, fixtures_dir=None):
    try:
        data = tomlio.load(path)
    except tomlio.TomlError as exc:
        raise GradingError(BAD_SCENARIO, str(exc),
                           file=os.path.basename(path), key="scenario")
    return validate(data, path, fixtures_dir)


def load_dir(scenarios_dir, fixtures_dir=None):
    if not os.path.isdir(scenarios_dir):
        return []
    out = []
    for name in sorted(os.listdir(scenarios_dir)):
        if name.endswith(".toml"):
            out.append(load_file(os.path.join(scenarios_dir, name), fixtures_dir))
    return out


def _subject_path(repo_root, subject):
    if subject == "core":
        return os.path.join(repo_root, "CLAUDE.md")
    if subject.startswith("agent:"):
        return os.path.join(repo_root, ".claude", "agents", subject.split(":", 1)[1] + ".md")
    if subject.startswith("skill:"):
        return os.path.join(repo_root, ".claude", "skills", subject.split(":", 1)[1], "SKILL.md")
    return ""


def preflight(repo_root, scenario):
    """Provenance and subject files. Product problems, no grading exception."""
    problems = []
    for src in scenario.sources:
        rel = src.get("file") or ""
        quote = src.get("quote") or ""
        path = os.path.join(repo_root, *rel.split("/")) if rel else ""
        if not path or not os.path.isfile(path):
            problems.append(Problem("product", RULE_MOVED,
                                    "missing source file %s" % rel, rel))
            continue
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
        if quote not in body:
            problems.append(Problem("product", RULE_MOVED,
                                    "quote missing from %s" % rel, quote))
    for subject in scenario.subjects:
        path = _subject_path(repo_root, subject)
        if not path or not os.path.isfile(path):
            problems.append(Problem("product", SUBJECT_MISSING, subject, subject))
    return problems


def map_changed(paths):
    """(subjects, every_scenario, gated_paths) from repo-relative paths.

    A path that does not name an agent, a skill, core, or console/evals is
    not gated. `--changed` with only those is "nothing to gate".
    """
    subjects = set()
    every = False
    gated = []
    for raw in paths:
        p = (raw or "").replace("\\", "/")
        if p.startswith("./"):
            p = p[2:]
        hit = False
        if p.startswith("console/evals/"):
            every = True
            hit = True
        m = re.match(r"\.claude/agents/([^/]+)\.md$", p)
        if m:
            subjects.add("agent:" + m.group(1))
            hit = True
        m = re.match(r"\.claude/skills/([^/]+)(/|$)", p)
        if m:
            if m.group(1) == "harness-standards":
                subjects.add("core")
            else:
                subjects.add("skill:" + m.group(1))
            hit = True
        if p in _CORE_FILES:
            subjects.add("core")
            hit = True
        if hit:
            gated.append(p)
    return subjects, every, gated


def _covers(scenario, subjects, every):
    if every:
        return True
    return bool(set(scenario.subjects) & set(subjects))


def select(scenarios, *, ids=None, agent="", skill="", all_=False, changed=None):
    """Pick scenarios.

    `changed` is None, or a dict with paths (list), subjects (set), every (bool).
    Returns (chosen, meta) where meta has exit, message, uncovered.
    """
    ids = [i for i in (ids or []) if i]
    meta = {"exit": 0, "message": "", "uncovered": []}
    if changed is not None:
        paths = list(changed.get("paths") or [])
        subjects = set(changed.get("subjects") or [])
        every = bool(changed.get("every"))
        if not paths:
            meta["message"] = "nothing to gate"
            return [], meta
        chosen = [s for s in scenarios if _covers(s, subjects, every)]
        covered = set()
        if every:
            covered = set(subjects)
        else:
            for s in scenarios:
                covered |= set(s.subjects)
        missing = sorted(subjects - covered)
        if missing:
            meta["uncovered"] = missing
        if not chosen:
            meta["exit"] = 2
            named = ", ".join(missing) if missing else "(none)"
            meta["message"] = "UNCOVERED %s" % named
        return chosen, meta
    if all_ and not ids and not agent and not skill:
        return list(scenarios), meta
    chosen = list(scenarios)
    if ids:
        known = {s.id: s for s in scenarios}
        missing = [i for i in ids if i not in known]
        if missing:
            meta["exit"] = 2
            meta["message"] = "unknown scenario %s" % ", ".join(missing)
            return [], meta
        chosen = [known[i] for i in ids]
    if agent:
        chosen = [s for s in chosen if "agent:" + agent in s.subjects]
    if skill:
        chosen = [s for s in chosen if "skill:" + skill in s.subjects]
    if (ids or agent or skill) and not chosen:
        meta["exit"] = 2
        meta["message"] = "selector matched nothing"
    return chosen, meta


def changed_paths(repo_root, base="HEAD", git=None):
    """Union of `git diff --name-only` and `git status --porcelain`.

    `git` is an injectable callable taking an argv list (without the git
    binary) and returning stdout. Renames keep the new path.
    """
    from server import procs

    def run(argv):
        if git is not None:
            return git(argv)
        import subprocess
        proc = subprocess.run(
            ["git", *argv], cwd=repo_root, capture_output=True, text=True,
            **procs.popen_kwargs())
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "git failed").strip()
            raise RuntimeError(err)
        return proc.stdout

    try:
        diff = run(["diff", "--name-only", base or "HEAD"])
        status = run(["status", "--porcelain", "--untracked-files=all"])
    except RuntimeError:
        raise
    paths = []
    for line in (diff or "").splitlines():
        if line.strip():
            paths.append(line.strip())
    for line in (status or "").splitlines():
        if len(line) < 4:
            continue
        body = line[3:].strip().strip('"')
        if " -> " in body:
            body = body.split(" -> ", 1)[1].strip().strip('"')
        if body:
            paths.append(body)
    return paths


def coverage(repo_root, scenarios):
    agents_dir = os.path.join(repo_root, ".claude", "agents")
    skills_dir = os.path.join(repo_root, ".claude", "skills")
    agents = []
    if os.path.isdir(agents_dir):
        agents = sorted(os.path.splitext(n)[0] for n in os.listdir(agents_dir)
                        if n.endswith(".md"))
    skills = []
    if os.path.isdir(skills_dir):
        for name in sorted(os.listdir(skills_dir)):
            if os.path.isfile(os.path.join(skills_dir, name, "SKILL.md")):
                skills.append(name)
    covered_agents = set()
    covered_skills = set()
    for scenario in scenarios:
        for subject in scenario.subjects:
            if subject.startswith("agent:"):
                covered_agents.add(subject.split(":", 1)[1])
            elif subject.startswith("skill:"):
                covered_skills.add(subject.split(":", 1)[1])
    return {
        "agents": agents,
        "agents_covered": [a for a in agents if a in covered_agents],
        "skills": skills,
        "skills_covered": [s for s in skills if s in covered_skills],
        "uncovered": [s for s in skills if s not in covered_skills],
    }


# Imported for the regex-error path's reason constant; kept referenced so a
# grader-version reader can see check failures stay grading.
_ = CHECK_ERROR
