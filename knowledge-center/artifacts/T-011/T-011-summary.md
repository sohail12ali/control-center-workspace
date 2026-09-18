---
tags: [active]
status: Done
ticket: "T-011"
---

# T-011: Session resume: pick a chat back up after a restart

**Status:** Done
**Stage:** VERIFY
**Owner:** Sohail Ali
**Created:** 2026-09-07
**Due:**

## Overview

Chats used to die with the console. `agent_session`'s own docstring said so —
"nothing re-attaches after a restart" — and the Agents tab listed every past
chat as replay-only. Meanwhile the CLI's session id, which exists precisely so
a conversation can be continued, was already being captured on every event and
written into every transcript. Nothing read it back out.

Now a past chat has a **Resume** button. It starts the CLI with `--resume`,
against the same chat id and the same transcript file, so the history stays
where it was and the model still remembers. The Assistant does the same for
its own chat: a restart of the console or the shell continues the conversation
instead of quietly starting a new one and losing everything it knew.

Two refusals matter as much as the feature: a chat with no session id in its
transcript, and a backend whose config row does not say how to resume, are
both refused out loud. A resume that silently started a fresh chat would look
identical — until several turns later, when the model turned out to remember
nothing.

## Current State

Shipped and verified end to end: a chat was told a word, the console was
stopped, restarted, the chat resumed, and asked what the word was. It said
**"Pomegranate."**

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
