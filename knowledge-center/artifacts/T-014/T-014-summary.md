---
tags: [active]
status: Done
ticket: "T-014"
---

# T-014: Model roles: a local model to talk, a capable one to work

**Status:** Done
**Stage:** VERIFY
**Owner:** Sohail Ali
**Created:** 2026-09-08
**Due:**

## Overview

The Assistant now has two model slots, because the two jobs want different
animals. A 9B on a local box answers "what's open?" in **1.4 seconds** and is a
poor engineer; a CLI agent is the other way round.

- **Talk** — conversation, status, ticket lookups, memory.
- **Work** — code changes, builds, test runs.

The talk model does not attempt the second kind: it calls `console_delegate`,
which starts a chat on the work backend and says where the task went. When that
turn ends a notice comes back into the Assistant chat with the gist, and the
transcript stays in the Agents tab. Delegating raises the approval card first —
a local model starting a second, often paid, agent is exactly what this console
asks about.

Two supporting pieces made that usable:

- **Providers can be re-pointed per machine.** The shipped LM Studio row says
  `127.0.0.1:1234`; yours is on the LAN. The address and the key's env-var name
  are overridable in the gitignored per-machine file — nothing else, because
  everything else about a row is a reviewed decision.
- **The picker knows what is loaded.** A local runtime keeps one model resident
  and swaps on demand, so choosing another is a ~20-second decision. Models
  show loaded / not loaded / unknown and whether the server claims tool
  training, and picking an unloaded one asks once.

## Current State

Shipped and verified: pytest 1173, lint clean, and the delegation loop driven
live — card raised, approved, "24" answered, notice returned.

Honestly incomplete: the LM Studio box dropped twice mid-session, so a *local*
model answering through the Assistant, and a local model choosing to delegate,
were not observed. The mechanism was proven with claude in both roles. See
[[T-014-verification]].

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
