---
ticket: "CC-T002"
artifact: decision-log
---

# Decisions: CC-T002

## verbs-are-config-not-plugins

**Decision:** A verb is a config row naming a dotted path into a module that already exists.
No base class, no lifecycle, no registration protocol.

**Rationale:** The fork's verb system is the idea worth porting; a plugin framework is not.
The test of whether something belongs here is that adding it takes a row and a one-line
adapter. If implementing a verb means writing a subsystem, it is not a verb.

**Impact:** `verb_handlers.py` is deliberately dull and should stay that way. When an adapter
starts wanting logic of its own, that logic belongs in the module that owns the fact.

## handlers-resolve-at-load

**Decision:** Every handler path is imported when the registry is built, not when the verb is
first run.

**Rationale:** A verb that only fails when someone finally runs it — typically at the worst
moment, possibly unattended — is a broken verb pretending to be a working one. A typo should
be a startup error naming the row.

**Impact:** A bad row breaks `verb list` for everyone immediately, which is the intent.

## no-kwargs-on-handlers

**Decision:** No verb handler takes `**kwargs`.

**Rationale:** A catch-all makes `by=modle` succeed silently and return a default-grouped
answer that looks correct. Declaring real parameters lets `inspect.signature().bind()` reject
the typo by name before the handler is called. Found by a test that asserted the wrong thing
for the right reason.

**Impact:** Adding a handler parameter is now a deliberate act, and every caller — CLI, queue,
MCP — gets the same validation.

## digest-composes-existing-readers

**Decision:** `context` assembles its answer from `tickets`, `trackers`, `telemetry` and
`boards`. It does not read the filesystem for facts those modules already own.

**Rationale:** A digest that derives lane or blocker state by its own route is a second source
of truth. It will eventually disagree with the board, and the disagreement will surface as an
agent acting on a state the board does not show.

**Impact:** Two narrow parsers remain — plan task headings and dated progress entries — because
nothing else reads those. Both report what they could not parse rather than guessing, and
tests assert agreement with the board for everything else.

## unparseable-is-not-empty

**Decision:** A plan with no recognisable task headings reports `parsed: false`, distinct from
a plan with zero open tasks.

**Rationale:** "No open tasks" and "I could not read the plan" lead to opposite actions. An
agent told the first about the second closes a ticket with work outstanding, confidently.

**Impact:** The markdown says so in words, and points the reader at the artifact.

## truncation-is-always-stated

**Decision:** Every capped section reports how many items it dropped.

**Rationale:** A digest that silently omits the newest blocker is worse than one that is
honestly incomplete, because the reader cannot tell the difference. Silence has to mean
completeness or it means nothing.

## gates-checked-at-submission

**Decision:** `JobQueue.submit` runs the verb's gates before recording the job.

**Rationale:** The caller is still there to be told. Accepting a job that will fail its own
gate, queueing it, and failing it later with nobody watching converts an immediate clear
error into a delayed obscure one.

**Impact:** A queue drained after a state change can still fail at run time — that is correct,
because the state changed after the promise was made.

## interrupted-is-its-own-state

**Decision:** A job left `running` by a dead process becomes `interrupted`, not `error` and
not `done`.

**Rationale:** `done` is a lie. `error` is a guess that asserts the work failed, when the
truth is that nobody knows how far it got — and a job that half-applied a change and lost its
process is exactly the situation a person must look at. The state name should summon that
attention rather than filing it under a heading that invites ignoring it.

## monotonic-sequence-for-job-order

**Decision:** Jobs carry a `seq` counter; listings sort by it, not by `submitted`.

**Rationale:** `submitted` is ISO to the second and this queue routinely accepts several jobs
per second, leaving their relative order undefined — visible as a job list that reshuffles
between polls. The counter is floored from existing records so it survives a restart.

## mcp-generates-tools-from-the-registry

**Decision:** The MCP server has no tool table. `tools/list` walks the verb registry and
derives each schema from the handler's signature.

**Rationale:** A hand-written tool list beside the thing it describes goes stale, and the
client trusts the schema. Generation makes "add a verb" and "add a tool" the same act.

**Impact:** A test adds a verb at runtime and asserts the tool appears, so the property is
enforced rather than merely intended.

## tool-errors-are-results-not-protocol-errors

**Decision:** A failed gate or a missing ticket comes back as `isError: true` with the reason
in the content, not as a JSON-RPC error code.

**Rationale:** The model should see what went wrong and be able to correct itself — supply the
ticket, pass confirm. A protocol error is handled by the client, never reaches the model, and
turns a recoverable mistake into a dead end.

## mcp-declares-only-what-it-implements

**Decision:** `initialize` advertises `tools` and nothing else.

**Rationale:** Declaring resources or prompts would have clients calling methods that do not
exist. Failing at runtime is a worse way to say "not implemented" than not claiming it.

## Links
- [[CC-T002-summary]] · [[CC-T002-analysis]] · [[CC-T002-requirements]] · [[CC-T002-decision-log]] · [[CC-T002-plan]] · [[CC-T002-progress]] · [[CC-T002-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
