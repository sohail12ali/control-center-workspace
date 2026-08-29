"""Verbs — named deterministic jobs, declared in config, run without a model.

## Why

The expensive habit this exists to break is asking a language model to do
arithmetic. Checking whether a ticket's links resolve, computing which plan
tasks are unchecked, deriving a lane from git state, tallying a work log —
these have exactly one right answer and no judgement in them. Every one of them
run as a model turn is tokens spent on a calculation, and a calculation that
might come back subtly wrong.

A verb is that work, named once, so the board, the CLI, a scheduler, and an
agent all invoke the same implementation and get the same answer.

## What a verb is NOT

It is not a plugin. There is no lifecycle, no base class, no registration
protocol. A verb row names a `handler` as a dotted path into a module that
already exists, and the registry imports it. If implementing a verb means
writing a new subsystem, it should not be a verb.

## Gates belong to the verb, not the caller

A verb declares its own preconditions — `needs_ticket`, `needs_confirm`,
which board `kinds` and `lanes` it applies to. Every caller then enforces the
same rules for free, because the rules travel with the definition instead of
being reimplemented in the CLI, the board, and the scheduler separately. In
particular `needs_confirm` exists so that a verb which mutates git or the
filesystem cannot be triggered by a stray click or a hallucinated tool call.

## Failure timing

An unresolvable handler is an error at **registry load**, not at run time. A
verb that only fails when someone finally runs it — typically at the worst
moment — is a broken verb pretending to be a working one.
"""

import importlib
import inspect
import os

from . import boards as boards_mod
from . import tickets as tickets_mod
from . import tomlio

CONFIG_REL = os.path.join("console", "config", "verbs.toml")

_cache = {}


class VerbError(ValueError):
    """A verb could not be run: unknown id, failed gate, or bad arguments."""


class Verb:
    __slots__ = ("id", "label", "hint", "handler", "needs_ticket",
                 "needs_confirm", "kinds", "lanes", "enabled", "raw")

    def __init__(self, row):
        self.id = (row.get("id") or "").strip()
        if not self.id:
            raise VerbError("verbs.toml: a [[verb]] row needs an id")
        self.label = row.get("label", self.id)
        self.hint = row.get("hint", "")
        self.handler = (row.get("handler") or "").strip()
        if not self.handler:
            raise VerbError("verb %r has no handler" % self.id)
        self.needs_ticket = bool(row.get("needs_ticket", False))
        self.needs_confirm = bool(row.get("needs_confirm", False))
        self.kinds = [str(k) for k in row.get("kinds", [])]
        self.lanes = [str(l) for l in row.get("lanes", [])]
        self.enabled = bool(row.get("enabled", True))
        self.raw = row

    def describe(self):
        return {
            "id": self.id, "label": self.label, "hint": self.hint,
            "needs_ticket": self.needs_ticket, "needs_confirm": self.needs_confirm,
            "kinds": list(self.kinds), "lanes": list(self.lanes),
        }

    def resolve(self):
        """Import the handler. Raises VerbError with the id in the message —
        a bare ImportError three frames deep does not say which row is wrong."""
        module_path, _, attr = self.handler.rpartition(".")
        if not module_path or not attr:
            raise VerbError(
                "verb %r: handler %r is not a dotted path (module.function)"
                % (self.id, self.handler))
        try:
            module = importlib.import_module("." + module_path, __package__) \
                if not module_path.startswith("server.") \
                else importlib.import_module(module_path)
        except ImportError as exc:
            raise VerbError("verb %r: cannot import %r (%s)"
                            % (self.id, module_path, exc)) from None
        func = getattr(module, attr, None)
        if func is None or not callable(func):
            raise VerbError("verb %r: %r has no callable %r"
                            % (self.id, module_path, attr))
        return func


def load_config(repo_root, force=False):
    if not force and repo_root in _cache:
        return _cache[repo_root]
    path = os.path.join(repo_root, CONFIG_REL)
    data = tomlio.load(path) if os.path.isfile(path) else {"verb": []}
    _cache[repo_root] = data
    return data


def registry(repo_root, force=False):
    """id -> Verb for every enabled row, with every handler already resolved.

    Resolving here rather than at call time is the point: a typo in a handler
    path is a startup failure, listed with the verb id, instead of a surprise
    when someone finally runs it.
    """
    rows = load_config(repo_root, force=force).get("verb", [])
    out = {}
    for row in rows:
        verb = Verb(row)
        if not verb.enabled:
            continue
        verb.resolve()
        out[verb.id] = verb
    return out


def get(repo_root, verb_id):
    reg = registry(repo_root)
    if verb_id not in reg:
        raise VerbError("unknown verb %r; configured: %s"
                        % (verb_id, ", ".join(sorted(reg)) or "(none)"))
    return reg[verb_id]


def check_gates(repo_root, verb, ticket=None, confirm=False):
    """Raise VerbError if a declared precondition is not met.

    Separate from `run` so a UI can grey out a button — and say why — without
    having to attempt the call to find out.
    """
    if verb.needs_confirm and not confirm:
        raise VerbError(
            "verb %r requires explicit confirmation (it mutates state); "
            "pass confirm=true" % verb.id)

    if verb.needs_ticket and not ticket:
        raise VerbError("verb %r requires a ticket id" % verb.id)

    if not ticket:
        return

    record = tickets_mod.load(repo_root, ticket)
    if record is None:
        raise VerbError("no such ticket: %s" % ticket)

    kind = record.get("kind") or "tickets"
    if verb.kinds and kind not in verb.kinds:
        raise VerbError("verb %r does not apply to %s tickets (only: %s)"
                        % (verb.id, kind, ", ".join(verb.kinds)))
    stage = record.get("stage") or ""
    if verb.lanes and stage not in verb.lanes:
        raise VerbError("verb %r does not apply in lane %r (only: %s)"
                        % (verb.id, stage, ", ".join(verb.lanes)))


def run(repo_root, verb_id, *, ticket=None, confirm=False, args=None):
    """Check the gates, then call the handler.

    Handlers are called as `handler(repo_root, ticket=..., **args)`. Keeping
    the signature fixed is what lets a verb be dispatched from config without
    per-verb glue anywhere.
    """
    verb = get(repo_root, verb_id)
    check_gates(repo_root, verb, ticket=ticket, confirm=confirm)
    func = verb.resolve()
    call_args = dict(args or {})

    # Validate the call shape BEFORE calling, rather than catching TypeError
    # around the call. Wrapping the call would also swallow a TypeError raised
    # *inside* the handler and relabel a genuine crash as "bad arguments",
    # which sends the reader looking in entirely the wrong place.
    try:
        inspect.signature(func).bind(repo_root, ticket=ticket, **call_args)
    except TypeError as exc:
        raise VerbError("verb %r: handler does not accept those arguments (%s)"
                        % (verb_id, exc)) from None

    return func(repo_root, ticket=ticket, **call_args)


def list_verbs(repo_root, ticket=None):
    """Every enabled verb, each marked with whether it is runnable right now.

    `available` plus `reason` is what a board needs to render a disabled button
    with a tooltip, instead of offering one that fails on click.
    """
    out = []
    for verb in sorted(registry(repo_root).values(), key=lambda v: v.id):
        row = verb.describe()
        try:
            check_gates(repo_root, verb, ticket=ticket,
                        confirm=True)  # confirmation is a caller act, not a state
            row["available"] = True
            row["reason"] = ""
        except VerbError as exc:
            row["available"] = False
            row["reason"] = str(exc)
        out.append(row)
    return out


def format_list(rows):
    if not rows:
        return "No verbs configured."
    width = max(len(r["id"]) for r in rows)
    lines = []
    for row in rows:
        flags = []
        if row["needs_ticket"]:
            flags.append("ticket")
        if row["needs_confirm"]:
            flags.append("confirm")
        mark = " " if row.get("available", True) else "-"
        lines.append("%s %-*s  %s%s" % (
            mark, width, row["id"], row["label"],
            "  [" + ", ".join(flags) + "]" if flags else ""))
        if row.get("hint"):
            lines.append("  %s  %s" % (" " * width, row["hint"]))
        if not row.get("available", True) and row.get("reason"):
            lines.append("  %s  unavailable: %s" % (" " * width, row["reason"]))
    return "\n".join(lines)
