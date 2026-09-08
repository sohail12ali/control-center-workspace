---
ticket: "T-014"
artifact: decision-log
---

# Decisions: T-014

## talk-and-work-rather-than-one-model
**Decision:** Two slots. `backend`/`model` keep their meaning as the talk pair;
`work_backend`/`work_model` are new.
**Rationale:** Keeping the existing keys means every setting, and the `use
ollama` fast command, keep working. And the two jobs genuinely differ: 1.4 s of
local conversation against a CLI agent that can actually edit code.
**Impact:** No migration, and one new pair to validate.

## delegation-is-a-verb
**Decision:** `console_delegate` is a verb row, not bespoke code.
**Rationale:** The verb registry turns one config row into an Assistant tool,
an MCP tool and a CLI command with no glue — and it puts the human gate where
this console already keeps it, in `agents.toml`'s `gated_tools`.
**Impact:** The Assistant gained an ability for ~40 lines of handler.

## delegating-asks-first
**Decision:** `console_delegate` is gated on every API-backed row.
**Rationale:** A local model starting a second, often paid, agent with file
access is exactly the shape of thing this console asks about — the same
argument as `run_command`.
**Impact:** One card per delegation. Removable by editing the row, and the
README says so.

## it-never-falls-back-to-the-talk-model
**Decision:** With no work backend, `delegate` refuses in those words.
**Rationale:** A local 9B quietly attempting a refactor is the worst outcome
available here, and it would look like success until you read the diff.
**Impact:** An explicit refusal, tested.

## report-on-the-turn-ending
**Decision:** The watcher reports when the delegated TURN ends, not when the
chat dies.
**Rationale:** Found live — the delegated chat answered "24" correctly and the
Assistant was never told, because a steerable backend keeps its process alive
between turns.
**Impact:** The notice arrives when the work is done rather than never.

## only-where-it-is-is-overridable
**Decision:** A per-machine override may change `base_url` and `api_key_env`
and nothing else.
**Rationale:** Where a server lives and what its key is called are facts about
a machine. A row's gates and context caps are reviewed decisions, and letting a
local file quietly widen a tool gate would be a bad trade.
**Impact:** `validate_where` refuses everything else by name.

## unknown-is-not-not-loaded
**Decision:** Residency returns `None` when a provider cannot say, and the UI
shows "unknown".
**Rationale:** Your box went unreachable twice during this ticket. Rendering
that as "not loaded" invites someone to pick a model and wait for a load that
never starts.
**Impact:** Three states everywhere instead of two.

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
