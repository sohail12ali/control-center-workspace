"""T-004 C5: the Assistant's fast-command table.

`say` is "normalise -> one fast-command match -> its handler, OR one
`agent_manager.send`, never both" (BR-1). This module owns the FIRST half of
that sentence and nothing else: it turns a line of text into either a
`Command` describing what to do, or `None` meaning "just send it".

## Why the matching is pure

Every handler needs the console's machinery — verbs, the session, the native
bridge. If the table *called* that machinery, testing "does `status T-002`
avoid a model call" would need a live backend. So `match()` returns a
description and `assistant_feature.say` executes it. One match, one action,
and the whole table is unit-testable with no process, no server, no chat.

## Why whole-utterance matching only

A voice transcript is a whole sentence, so a substring rule is actively
dangerous: "stop the server" must reach the model, not silently interrupt the
turn. Every pattern here is anchored at both ends. The cost is that a command
buried mid-sentence isn't recognised — the right trade, because the failure
mode is "it answered you" rather than "it did something you didn't ask for".

## Rewrites are still one `send`

Two rows (`do|fix|build|run …`, `screenshot …`) don't have a local handler:
they reshape the text and hand it to the model. Those return
`Command("send", ..., text=<rewritten>)`, so the caller still performs
exactly one `send` — BR-1 holds. The model may then call a tool, which is its
turn, not a second dispatch of ours.
"""

import re
from collections import namedtuple

#: `name`  what the caller should do (see `assistant_feature`'s HANDLERS).
#: `args`  keyword arguments for that handler.
#: `text`  for `name == "send"`, the text to send INSTEAD of the original;
#:         None everywhere else.
Command = namedtuple("Command", "name args text")

#: Spoken small numbers, because a transcript says "t dash two", not "T-2".
#: Stops at twenty deliberately: ticket ids past that are read as digits by
#: every STT engine worth using, and a bigger table would be guessing.
_WORD_DIGITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

#: Homophones a speech engine actually produces where a digit was spoken.
#:
#: Not speculation. Asked to transcribe "status ticket two", whisper base.en
#: returned **"Status ticket too"** — so the literal spellings above matched
#: nothing, and a command the console can answer for free fell through to a
#: model instead. Every entry here was either observed or is the same class of
#: mistake.
#:
#: Safe because of WHERE it applies: only inside `canonical_ticket`, on a span
#: an anchored row has already identified as a ticket id. "status to" means
#: nothing else, and an id that resolves to a ticket which does not exist gets
#: a plain "no ticket.toml for T-002". Mapping homophones in general text
#: would be a different and much worse idea.
_DIGIT_HOMOPHONES = {
    "won": 1,
    "to": 2, "too": 2,
    "for": 4, "fore": 4,
    "ate": 8,
    "oh": 0,
}

#: Words that only ever join a command to its argument. If one of these is
#: all that survived as a captured "title", the user did not actually name
#: anything, so the row falls through instead of inventing a name.
_CONNECTORS = frozenset({"for", "to", "about", "that", "the", "a", "an"})

#: Wake words stripped from the front before matching, so "hey console, stop"
#: is the same utterance as "stop".
_WAKE = re.compile(
    r"^(?:hey\s+|ok\s+|okay\s+)?(?:console|assistant|computer)\s*[,:]?\s+",
    re.I)

#: Spoken backend names -> `agents.toml` ids. Only the ids this workspace
#: actually ships; an unknown name falls through to the model, which can say
#: so, rather than being silently mapped to something plausible.
_BACKEND_ALIASES = {
    "claude": "claude", "claude code": "claude",
    "cursor": "cursor-agent", "cursor agent": "cursor-agent",
    "ollama": "ollama",
    "lm studio": "lm-studio", "lmstudio": "lm-studio", "lm-studio": "lm-studio",
    "openrouter": "openrouter", "open router": "openrouter",
    "qwen": "qwen", "qwen code": "qwen",
}


def normalise(text):
    """Lower-case, wake-word-stripped, punctuation-trimmed, single-spaced.

    Only ever used for MATCHING. Anything captured for a handler (a ticket
    title, a fact to remember) is taken from the ORIGINAL text, because
    case and punctuation are meaningful there.
    """
    s = (text or "").strip()
    s = _WAKE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" \t\r\n.!?").lower()


def canonical_ticket(raw, prefix="T-", width=3):
    """`t dash two` / `t 2` / `T4` / `ticket 4` / `T-004` -> `T-004`.

    Returns None when `raw` holds no number, so a caller can fall through
    instead of inventing an id.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    s = re.sub(r"\b(?:ticket|dash|number)\b", " ", s)
    s = s.replace("-", " ")
    for word, digit in _WORD_DIGITS.items():
        s = re.sub(r"\b%s\b" % word, str(digit), s)
    # After the real words, so "two" is never beaten to it by "to".
    for word, digit in _DIGIT_HOMOPHONES.items():
        s = re.sub(r"\b%s\b" % word, str(digit), s)
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    return "%s%0*d" % (prefix, width, int(digits))


# -- the table ---------------------------------------------------------------
# Anchored at both ends, checked in order. The first match wins; a row that
# captures free text keeps its capture group loose on purpose, because the
# handler validates (an unparseable ticket id falls through to the model).

_ROWS = (
    ("new_chat", re.compile(r"^(?:new chat|start over|reset)$")),
    ("interrupt", re.compile(r"^(?:stop|cancel|interrupt)$")),
    ("mute", re.compile(r"^(?:mute|be quiet|quiet)$")),
    ("unmute", re.compile(r"^unmute$")),
    ("use_backend", re.compile(r"^(?:use|switch to) (?P<backend>.+)$")),
    # The ticket span is captured LOOSELY on purpose: a transcript can say
    # "t dash two", "ticket 4", "T-002" or "t two", and enumerating those
    # shapes in the regex means a shape nobody thought of silently reaches
    # the model instead. `canonical_ticket` is the validator — it returns None
    # when the span holds no number, and the caller falls through. So
    # "status of the migration" asks the model, while "status t dash two"
    # resolves to T-002, without either being special-cased here.
    ("status", re.compile(
        r"^(?:what(?:'|’)?s the )?status (?:of |for )?(?P<ticket>[a-z][a-z0-9\s-]*)$")),
    ("digest", re.compile(
        r"^(?:what(?:'|’)?s open|open tickets|standup|what am i working on)$")),
    ("create_ticket", re.compile(
        r"^(?:create|open|make) (?:a )?ticket (?:for |to |about )?(?P<title>.+)$")),
    ("copy_last", re.compile(
        r"^(?:copy that|copy the (?:last )?reply"
        r"|put (?:that|the last reply) (?:on|in)(?: the)? clipboard)$")),
    ("remember", re.compile(r"^remember (?:that )?(?P<fact>.+)$")),
    ("rewrite_do", re.compile(r"^(?P<verb>do|fix|build|run) (?P<rest>.+)$")),
    ("rewrite_capture", re.compile(
        r"^(?:take (?:a )?)?screenshot(?: of (?P<what>.+?))?"
        r"(?: and (?P<ask>.+))?$")),
)


def _original_tail(text, normalised_match, group):
    """Recover a captured span from the ORIGINAL text.

    `normalise` case-folds and strips punctuation, so a title or fact taken
    from the normalised string would come back lower-cased and stripped of a
    trailing question mark. The captured group's END offset is stable enough
    to slice the original by length from the right, which preserves the
    user's own capitalisation.
    """
    captured = normalised_match.group(group)
    if not captured:
        return captured
    tail = (text or "").strip()
    tail = _WAKE.sub("", tail)
    tail = tail.strip(" \t\r\n.!?")
    # The capture always runs to the end of the utterance for the rows that
    # use this helper (title / fact / rest), so the last N characters of the
    # original are that same span with its original case.
    return tail[-len(captured):] if len(captured) <= len(tail) else captured


def _original_case(text, span):
    """Recover `span` (taken from the normalised string) in its original case.

    Used for a capture that is NOT at the end of the utterance, where
    `_original_tail`'s length trick cannot apply — a window title in
    "screenshot of Notepad and tell me…". Falls back to the normalised span
    when it cannot be found, which only costs capitalisation.
    """
    if not span:
        return span
    idx = (text or "").lower().find(span.lower())
    return text[idx:idx + len(span)] if idx != -1 else span


def match(text, *, ticket_prefix="T-"):
    """A `Command`, or None meaning "send the original text unchanged"."""
    s = normalise(text)
    if not s:
        return None

    for name, pattern in _ROWS:
        m = pattern.match(s)
        if not m:
            continue

        if name == "use_backend":
            backend = _BACKEND_ALIASES.get(m.group("backend").strip())
            if not backend:
                return None          # unknown name -> let the model answer
            return Command("use_backend", {"backend": backend}, None)

        if name == "status":
            ticket = canonical_ticket(m.group("ticket"), prefix=ticket_prefix)
            if not ticket:
                return None
            return Command("status", {"ticket": ticket}, None)

        if name == "create_ticket":
            title = _original_tail(text, m, "title").strip()
            # "create ticket for" with nothing after it leaves the connector
            # itself as the title, because `normalise` already stripped the
            # trailing space the pattern would have consumed. A ticket called
            # "for" is worse than falling through and being asked what to
            # call it.
            if not title or title.lower() in _CONNECTORS:
                return None
            return Command("create_ticket", {"title": title}, None)

        if name == "remember":
            fact = _original_tail(text, m, "fact").strip()
            if not fact:
                return None
            return Command("remember", {"fact": fact}, None)

        if name == "rewrite_do":
            rest = _original_tail(text, m, "rest").strip()
            return Command("send", {"skill": "do"},
                           "%s %s" % (m.group("verb"), rest))

        if name == "rewrite_capture":
            what = _original_case(text, (m.group("what") or "").strip()) \
                or "the whole screen"
            ask = _original_case(text, (m.group("ask") or "").strip()) \
                or "describe what you see"
            return Command("send", {}, (
                "Take a screenshot of %s, then %s. Use the desktop screenshot "
                "tool; if it reports that the desktop shell is not running, "
                "say so plainly instead of guessing at what is on screen."
                % (what, ask)))

        return Command(name, {}, None)

    return None
