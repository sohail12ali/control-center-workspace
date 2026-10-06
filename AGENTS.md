# AGENTS.md

<!-- console:agents-snippet:start (T-017 FR-11) -->
## Delivery Console tickets — do not hand-edit

`ticket.toml` and `{T}-{questions,bugs,todos,comments}.toml` under
`knowledge-center/artifacts/` are CLI-mutated only, via
`console/kanban.py` (equally reachable through the MCP tools this editor is
now wired to, or the console's HTTP API — one API, three surfaces). Hand-
editing these files bypasses validation, race-safety, and the audit log.

Use the verbs instead — `python console/kanban.py verb list` for the full,
current list. The ones most relevant day to day: `ticket create/list/show/
move/set`, `tracker add/list/update/blockers`, and the ready-claim-hooks
verbs `ready` (unblocked, unclaimed tickets), `claim` (take a ticket,
race-safe, audited), `comment` (attributed, timestamped, non-blocking).
<!-- console:agents-snippet:end -->
