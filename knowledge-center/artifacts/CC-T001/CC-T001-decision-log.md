---
ticket: "CC-T001"
artifact: decision-log
---

# Decisions: CC-T001

## one-backend-registry

**Decision:** Collapse `server/agents.py` onto `agent_backends.registry()` instead of
restoring the `[agents.backends]` block in `console.toml`.

**Rationale:** The block was not dead config, as the plan assumed. The `kanban agents *`
CLI path read it while the Agents tab read `agents.toml` — two registries for one concept,
free to disagree about command, model and permission mode with nothing to catch it.
Restoring it would have preserved the duplication that the defect was really about.

**Impact:** `agents launch` now goes through the same argv builders and command resolution
as the tab, gaining the Windows `.CMD` path handling it never had. `oneshot_args` added to
the claude row, which previously had no one-shot argv at all. `_from_legacy` kept and
tested, so an older checkout without `agents.toml` still works.

## cost-unknown-is-not-zero

**Decision:** Telemetry records `cost_usd: null` for a turn whose model has no published
rate, and every total containing one is reported as partial with a `*` and a count.

**Rationale:** Substituting `0.0` for an unknown rate makes an incomplete total look like a
cheap one. This data exists to decide which models and stages to keep spending on; a
silently-low number sends exactly those decisions the wrong way. A visibly partial number
is useful; a confidently wrong one is not.

**Impact:** `pricing.toml` ships with no rates at all — only a commented example — because
this template cannot verify prices on the user's behalf. Claude Code turns carry
`total_cost_usd` from the CLI and never consult the table.

## telemetry-per-turn-not-per-session

**Decision:** One record per turn, appended as JSONL, rather than one summary per session.

**Rationale:** A session can run for hours across several stages. A session-level total
cannot answer "which stage cost that", which is the only question the measurement exists to
answer. JSONL because this is written from a live session's reader thread mid-stream —
rewriting a whole document per turn would be both slow and a corruption risk.

**Impact:** Monthly files under `knowledge-center/telemetry/`. Records carry no prompt
text, tool arguments, or file content, so the log is safe to read and to commit.

## ticket-attribution-stays-optional

**Decision:** The Agents tab's ticket picker defaults to none, and no chat is forced to
name a ticket.

**Rationale:** An exploratory chat genuinely belongs to no ticket. Forcing a choice gets
one picked at random, and telemetry filed against the wrong ticket is far harder to notice
— and to undo — than telemetry filed against nothing.

**Impact:** Some turns will carry `ticket: ""` and appear under `(none)` in reports. That
is a true statement about the work, not a gap.

## accepted-gap-live-telemetry-unproven

**Decision:** Close CC-T001 with task 04's done-criterion "`telemetry --ticket CC-T001`
reports non-zero tokens" **unproven**, recorded rather than quietly ticked.

**Rationale:** Proving it end-to-end means starting a real agent run — a `claude`
subprocess doing real work against the user's account. That spends the user's money and
was not requested, so it is not mine to trigger for the sake of a green checkmark. The path
is proven at every seam below that: five tests drive a real `agent_session` object through
a `turn.end` event and assert the record lands on disk with the right attribution, and the
live server serves the composer that now sends the ticket id.

**Impact:** The first real chat started from the Agents tab satisfies the criterion with no
further code. Until then `telemetry` correctly reports "No telemetry recorded yet." The gap
is stated in [[CC-T001-verification]] § Gaps rather than closed over.

## Links
- [[CC-T001-summary]] · [[CC-T001-analysis]] · [[CC-T001-requirements]] · [[CC-T001-decision-log]] · [[CC-T001-plan]] · [[CC-T001-progress]] · [[CC-T001-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
