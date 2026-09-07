"""First-run onboarding — "am I set up, and what do I do next?"

One step list, three consumers: the `onboard` CLI verb prints it,
`GET /api/onboarding` serves it, and the Overview card renders it. A step
described in more than one of those would drift, so it is described here and
nowhere else.

## What this asks that a working console does not

The console starts fine on an empty workspace — it just has nothing to show.
The question a person actually has on their first day is not "does it run" but
"how do I get from an empty vault to a ticket with agreed requirements", and
the answer is a sequence nothing else states end to end: name the workspace,
pick your boards, get a CLI on PATH, open a ticket, then drive that ticket
through the pre-freeze requirements pipeline.

That last step is the point of the whole list. Everything above it is setup;
requirements are the actual work, and the skills that do it (`draft-requirements`
→ `analyze-context` → `identify-gaps` → `enrich-requirements` →
`iterate-requirements` → `challenge-requirements` → `freeze-requirements`)
are a chain nobody remembers the order of.

## What may act, and what may only ask

Nothing here writes. Every step reports state and offers the command or the
tab that changes it. That is deliberate: the things left to do are decisions
(what is this project called, which boards do you want, what are the
requirements) and a setup wizard that guesses at those produces a workspace
someone then has to un-guess.

## Statuses

    ok    done, nothing to do
    todo  not done, and it is the normal next thing to do
    warn  works, but something is worth knowing
    fail  the console cannot function until this is fixed

Only `cli` can be `fail`-adjacent in practice, and even that is a `warn`:
a console with no agent CLI is still a perfectly good board.
"""

import os
import re
import subprocess

from . import agent_backends
from . import boards as boards_mod
from . import procs
from . import tickets as tickets_mod

#: The pre-freeze requirements chain, in the order the skills run. Named here
#: because the order is the part people forget.
REQUIREMENTS_CHAIN = [
    "draft-requirements", "analyze-context", "identify-gaps",
    "enrich-requirements", "iterate-requirements", "challenge-requirements",
    "freeze-requirements",
]

_DEFAULT_TITLES = ("", "Delivery Console")


def _step(sid, title, status, detail, **extra):
    out = {"id": sid, "title": title, "status": status, "detail": detail}
    out.update(extra)
    return out


# ---------------------------------------------------------------- identity --
def _git_user(repo_root):
    try:
        out = subprocess.run(["git", "config", "user.name"], cwd=repo_root,
                             capture_output=True, text=True, timeout=5,
                             **procs.popen_kwargs())
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _identity_step(repo_root):
    """Who the work logs will be attributed to. `log-work` resolves this
    itself, but a person setting up wants to know it resolved to the right
    name before a month of entries land under the wrong one."""
    author_local = os.path.join(repo_root, "knowledge-center", "logs", "author.local")
    if os.path.isfile(author_local):
        try:
            with open(author_local, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            if lines:
                return _step("identity", "Identity", "ok",
                             "work logs are attributed to “%s”" % lines[0],
                             extra={"author": lines[0]})
        except OSError:
            pass
    name = _git_user(repo_root)
    if name:
        return _step("identity", "Identity", "todo",
                     "git says “%s” — that name is used on first log entry" % name,
                     hint="/log-work Internal ~0.5h set up the workspace",
                     extra={"author": name})
    return _step("identity", "Identity", "warn",
                 "git has no user.name, so work logs have nobody to attribute to",
                 hint="git config user.name \"Your Name\"")


# ----------------------------------------------------------------- project --
def _project_step(repo_root):
    general = boards_mod.load_console_config(repo_root).get("general", {})
    title = (general.get("title") or "").strip()
    if title and title not in _DEFAULT_TITLES:
        return _step("project", "Project name", "ok",
                     "this workspace is “%s”" % title, extra={"title": title})
    return _step(
        "project", "Project name", "todo",
        "still the stock name, so every board and tab header says “Delivery Console”",
        hint="set general.title (and subtitle) in console/config/console.toml",
        file="console/config/console.toml",
    )


# ------------------------------------------------------------------ boards --
def _boards_step(repo_root):
    kinds = boards_mod.enabled_boards(repo_root)
    if not kinds:
        return _step("boards", "Boards", "warn",
                     "no board kinds are enabled, so there is nothing to track work on",
                     hint="set general.enabled_boards in console/config/console.toml")
    parts = []
    for kind in kinds:
        lanes = boards_mod.lanes_for(kind, repo_root)
        parts.append("%s (%d lanes)" % (kind, len(lanes)))
    return _step("boards", "Boards", "ok", " · ".join(parts),
                 jump={"tab": "board:" + kinds[0]},
                 extra={"kinds": kinds})


# --------------------------------------------------------------------- CLI --
def _cli_step(repo_root):
    try:
        reg = agent_backends.registry(repo_root, force=True)
    except Exception as exc:  # noqa: BLE001 - a bad config must not break the list
        return _step("cli", "Agent CLI", "warn",
                     "agents.toml could not be read — %s" % exc,
                     file="console/config/agents.toml")
    installed = [b for b in reg.values() if b.installed]
    if installed:
        return _step("cli", "Agent CLI", "ok",
                     "%s on PATH" % ", ".join(b.label for b in installed),
                     jump={"tab": "agents"},
                     extra={"installed": [b.id for b in installed]})
    return _step(
        "cli", "Agent CLI", "warn",
        "none of the configured CLIs are on PATH — the board still works, the Agents tab won't",
        hint="install one, or add a [[backend]] row to console/config/agents.toml",
        file="console/config/agents.toml",
    )


# ------------------------------------------------------------- first ticket --
def _ticket_step(repo_root, all_tickets):
    if all_tickets:
        return _step("ticket", "First ticket", "ok",
                     "%d ticket(s) in the vault" % len(all_tickets),
                     jump={"tab": "board:tickets"},
                     extra={"count": len(all_tickets)})
    return _step(
        "ticket", "First ticket", "todo",
        "nothing to work on yet — a ticket is the folder every artifact hangs off",
        hint="/kickoff T001   (scaffolds artifacts + ticket.toml together)",
        skill="kickoff",
    )


# ------------------------------------------------------------- requirements --
_FROZEN_RE = re.compile(r"^\s*(?:freeze_status|status)\s*:\s*frozen\s*$", re.MULTILINE)

#: List markers: "1.", "2)", "-", "*", each optionally followed by a
#: checkbox. Matched and STRIPPED rather than tested in one pattern with a
#: trailing `\S` — an optional group backtracks, so "- [ ] " (an empty
#: checklist entry) matched by skipping the checkbox and treating "[" as its
#: content. Stripping the marker and asking whether anything is left has no
#: such ambiguity.
_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s*(?:\[[ xX]\]\s*)?")

#: `kickoff` writes a Links block into every artifact, so it is scaffold, not
#: content — counting it would make a freshly-scaffolded file look drafted.
_LINKS_RE = re.compile(r"^\s*#{1,6}\s+Links\s*$", re.MULTILINE | re.IGNORECASE)

#: Two items, not one: a single line is often a leftover example or a note to
#: self, and calling that "drafted" would tell someone their requirements are
#: further along than they are.
_DRAFTED_MIN_ITEMS = 2


def _requirements_state(repo_root, ticket_id):
    """`missing` | `stub` | `drafted` | `frozen` for one ticket.

    "stub" matters: `kickoff` scaffolds requirements.md from the template, so
    the file existing proves nothing. A template still full of empty numbered
    bullets is not a requirement — reporting it as done would make this whole
    step lie on every freshly-created ticket.
    """
    folder = tickets_mod.dir_for(repo_root, ticket_id)
    path = os.path.join(folder, "%s-requirements.md" % ticket_id)
    if not os.path.isfile(path):
        return "missing", path
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return "missing", path
    if _FROZEN_RE.search(text):
        return "frozen", path
    body = re.sub(r"^---.*?---", "", text, count=1, flags=re.DOTALL)
    cut = _LINKS_RE.search(body)
    if cut:
        body = body[: cut.start()]
    items = 0
    for line in body.splitlines():
        m = _MARKER_RE.match(line)
        if m and line[m.end():].strip():
            items += 1
    return ("drafted" if items >= _DRAFTED_MIN_ITEMS else "stub"), path


def _requirements_step(repo_root, all_tickets):
    if not all_tickets:
        return _step(
            "requirements", "Product requirements", "todo",
            "create a ticket first — requirements are written per ticket",
            chain=REQUIREMENTS_CHAIN,
        )

    buckets = {"missing": [], "stub": [], "drafted": [], "frozen": []}
    for t in all_tickets:
        state, _path = _requirements_state(repo_root, t["id"])
        buckets[state].append(t["id"])

    unfrozen = buckets["missing"] + buckets["stub"] + buckets["drafted"]
    if not unfrozen:
        return _step("requirements", "Product requirements", "ok",
                     "every ticket has frozen requirements",
                     chain=REQUIREMENTS_CHAIN, buckets=buckets)

    # Point at one concrete ticket. A list of eight ids is a report; one id
    # with the next command is something a person can act on now.
    nxt = (buckets["drafted"] or buckets["stub"] or buckets["missing"])[0]
    started = bool(buckets["drafted"])
    return _step(
        "requirements", "Product requirements",
        "todo",
        "%d of %d ticket(s) have frozen requirements" % (len(buckets["frozen"]), len(all_tickets)),
        hint=("/iterate-requirements %s   then /challenge-requirements, /freeze-requirements" % nxt)
             if started else ("/draft-requirements %s" % nxt),
        next_ticket=nxt,
        chain=REQUIREMENTS_CHAIN,
        buckets=buckets,
    )


# -------------------------------------------------------------------- suite --
def steps(repo_root):
    """The step list, in the order a person meets them."""
    all_tickets = [t for t in tickets_mod.list_tickets(repo_root) if t.get("kind") == "tickets"]
    return [
        _identity_step(repo_root),
        _project_step(repo_root),
        _boards_step(repo_root),
        _cli_step(repo_root),
        _ticket_step(repo_root, all_tickets),
        _requirements_step(repo_root, all_tickets),
    ]


def report(repo_root):
    rows = steps(repo_root)
    done = sum(1 for s in rows if s["status"] == "ok")
    todo = [s for s in rows if s["status"] == "todo"]
    return {
        "steps": rows,
        "done": done,
        "total": len(rows),
        "complete": done == len(rows),
        # The one thing to do next, so a caller doesn't have to re-derive it.
        "next": todo[0]["id"] if todo else None,
        "chain": REQUIREMENTS_CHAIN,
    }
