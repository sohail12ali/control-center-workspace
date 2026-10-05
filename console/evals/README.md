# Prompt evals

Replay grades committed transcripts against the rules the prompts already state.
It does not prove live agent behaviour. One live pass is not reliability.

## Format

One file, `scenarios/{id}.toml`, plus `fixtures/{id}.pass.jsonl` and
`{id}.fail.jsonl`. Parsed with the console's TOML subset.

- Double every backslash in a regex (`kanban\\.py`, not `kanban\.py`).
- No trailing `# comment` on a value. A value that still starts with a quote
  character is rejected, and the error names the file and the key.
- `prompt` and every `quote` are a single line. A quote over a newline is rejected.
- `[scenario] mode` is `plan`.
- A scenario needs a positive check: `call` with `min` at least 1 (the default),
  `first_call`, or `text` with `present` true (the default). `order` and `end`
  do not count, so a scenario made of only those two is rejected.

## Check kinds

`call`, `first_call`, `order`, `text`, `end`.

The canonical call string is `Tool argtext`:

- Bash uses `command`.
- Edit, Write, MultiEdit, and NotebookEdit use `file_path` or `notebook_path`,
  with backslashes rewritten to slashes.
- Skill is `skill` plus a space plus `args` when args is non-empty.
- Every other tool is compact sorted JSON (`ensure_ascii` false).
- ExitPlanMode is not a call. Its plan text is part of the `all` and `any` text scopes.

`final` text is the last non-empty assistant text block, otherwise the raw
`result.result`, otherwise empty.

`text` scope `all` is every assistant text block plus ExitPlanMode plan text.
`any` is that plus every canonical call string. `present = false` requires the
regex to be absent.

`end` looks at `is_error`, never `subtype`. No `turn.end` is `no_result` and
matches neither `completed` nor `error`.

## Taxonomy

One primary class, in this order: grading, infra, product, model.

Reason codes: `bad_scenario`, `bad_fixture`, `check_error`, `golden_failed`,
`must_fail_passed`, `spawn_error`, `no_result`, `timeout`, `api_error`, `auth`,
`rate_limit`, `overloaded`, `budget_cap`, `empty_turn`, `cli_error`,
`rule_moved`, `subject_missing`, `behaviour`, `max_turns`, `tool_cap`.

## What a run proves

`evals replay` proves the graders and the fixtures, not live agent behaviour.
The footer says so. Usage on a replay row is `n/a (replay)`, and the run is
complete because that is not an unknown cost.

A number is known only when the raw `result` carries it. A missing token or
cost is UNKNOWN, never zero. A reported zero stays zero with `cost_source`
`backend`. Missing cost with known tokens uses `telemetry.price` (`table`) or
stays unknown.

`evals replay --changed` maps edits under `.claude/agents`, `.claude/skills`,
`CLAUDE.md`, `.claude/settings.json`, and `console/evals/` onto scenario
subjects. Any change that edits a gated file runs it in its verify step.
`--changed` is the one replay path that runs git.

## Normalizer

Graders read calls, assistant text, and `turn.end`. They do not read
`tool.result`. Duplicate `tool.start` events for one id collapse to the first.
Empty `text.done` events are dropped. Usage is read from the raw `result`,
because the normalizer reports 0 when the usage key was absent.

## GRADER_VERSION

`GRADER_VERSION` in `grade.py` is an integer. Bump it when grader semantics
change (what a check matches, or how a transcript is viewed). A wording change
in this file does not bump it.

## Adding a scenario

1. Re-read the prompt file and copy a single-line substring into `[[source]] quote`.
2. Add the checks. The must-fail fixture must fail every id in `fail_checks`
   and pass the others.
3. Re-pin the quote in the same change that edits the cited rule.
4. `python console/kanban.py evals replay`.

Promoting a live transcript into a fixture is manual. Scrub paths, keys, and
account names first. The fixture scan rejects `C:\Users\`, `/Users/`, `/home/`,
`sk-` or `ghp_` plus 16 word characters, `OPENROUTER`, and `Bearer `.

Live mode is `evals live --scenario ID --confirm`. It is refused when `CI` is
set. It is not an MCP verb. There is no live verb.

## Deferred

Claim before work, and stop on a claim conflict. No prompt states either rule,
so neither has a scenario. The natural moment to add one is when a role or
skill adopts the rule (T-020 item 5).

## Rollback

Remove the `evals-replay` verb row, the `evals` block in `kanban.py`, and this
directory. `evals.live` audit rows are written, but `evals.live` is not in
`audit.ACTIONS`, so `kanban.py audit --action evals.live` is not a filter.
The unfiltered audit listing still shows the row.
