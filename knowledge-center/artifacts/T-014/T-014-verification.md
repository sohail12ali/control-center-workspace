---
ticket: "T-014"
artifact: verification
---

# Verification: T-014

Verified 2026-09-08. **pytest 1173 passed** (1145 before), harness lint clean,
and the delegation loop driven end to end against a real claude chat.

## The loop, live

```
POST /api/verbs/delegate/run  {"task": "number of .rs files in desktop/src-tauri/src"}
  -> {"ok": true, "chat": "889dad33105d", "backend": "claude", "model": "claude-sonnet-5"}
  -> the delegated chat raises the approval card:  Bash  find … -name "*.rs" | wc -l
  -> approved
  -> it answers: 24
  -> a notice lands in the ASSISTANT chat:
     "Finished — …number of .rs files in desktop/src-tauri: 24
      (chat 889dad33105d — full transcript in the Agents tab)"
```

`ls desktop/src-tauri/src/*.rs | wc -l` is 24, so the answer is right as well
as delivered.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Two role slots, validated | PASS | `work_backend`/`work_model` round-trip; a work backend that is not enabled+installed is refused by the same rule the talk backend has always had |
| 2 | A shipped provider can be re-pointed per machine | PASS | `lm-studio` pointed at `192.168.1.14:1234` through `providers.json`; the committed row still reads `127.0.0.1:1234` and `git diff` on it shows only this ticket's hand-written comments |
| 3 | Only the address and the key NAME are overridable | PASS | `gated_tools`, `max_tool_rounds` and friends are refused — those are reviewed decisions, not machine facts. A pasted key is refused as it is everywhere else |
| 4 | Residency is reported, and "unknown" stays distinct | PASS | Live against your box: 12 models listed, `qwen/qwen3.8-27b` correctly marked loaded and the rest not. A provider that cannot answer returns `None`, unit-tested against a refused connection |
| 5 | The picker knows what each model can do | PASS | `tool_use`, `vision`, `params`, `context` come from the server's own `capabilities`. `meta/muse-glimmer` is marked as not tool-trained |
| 6 | The talk model can hand work over | PASS | The Assistant called `mcp__console__delegate` unprompted for a code task, and said "handing that to claude" |
| 7 | Delegating asks first | PASS | Every API-backed row gates `console_delegate`; the live delegated chat raised the card for its `Bash` call and waited |
| 8 | It never runs the task on the talk model | PASS | With no work backend it refuses and says so in those words |
| 9 | The result comes back | PASS | The notice above, in the Assistant's own stream — the same path that speaks replies aloud |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1173 passed
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

22 new tests: role validation, the three residency answers (ids / empty /
`None`), host recovery from a base URL, every `delegate` refusal, the hand-off
itself, and the two bugs below.

## Two bugs the live run found

**A delegation with no server behind it hung.** Run from a terminal
(`kanban verb run delegate`), the verb started a claude chat whose approval
hook had no port to call home to — so the first gated tool blocked invisibly
and the chat sat at `turn.start` indefinitely. It now refuses, naming the fix.
Found by watching a chat do nothing for three minutes.

**The result was never reported.** The first delegated chat answered "24"
correctly and the Assistant was never told, because the watcher waited for the
work chat to *die* — and a steerable backend keeps its process alive between
turns. It now reports when the **turn** ends. Both are pinned by tests.

## What your LM Studio box did and did not prove

Reached twice, and dropped twice mid-session (`WinError 10060`), so this splits
into what was actually observed and what was not:

**Observed:** all 12 models listed through the console; residency correct;
per-model `trained_for_tool_use`; the Assistant chat created on
`lm-studio` / `qwen/qwen3.5-9b`; and — when the box vanished — an honest notice
in the chat naming the address and the OS error rather than a hang.

**Not observed:** a local model answering a question through the Assistant, and
a local model deciding to delegate. The talk-model turn hit the timeout when
the box went away. The delegation loop above was proven with claude as the talk
model, so what is unproven is specifically *the local model's judgement*, not
the mechanism.

**Tool calling, per model** — one call each, measured earlier the same day
through the exact request shape the console sends. One successful call is not
a reliability claim over a long agent loop:

| Model | Called the tool | First call (includes the load) |
|---|---|---|
| `qwen/qwen3.5-9b` | yes | 8.5 s → **1.4 s warm** |
| `nvidia/nemotron-3-nano-4b` | yes | 5.9 s |
| `qwen/qwen3.8-27b` | yes | 17.6 s → 2.7 s warm |
| `qwen/qwen3.6-35b-a3b` | yes | 19.0 s |
| `google/gemma-4-26b-a4b` | yes | 25.1 s |
| `ornith-1.0-9b` | yes, on retry | a 400 while loading, then fine |
| `meta/muse-glimmer` | yes — **despite declaring `trained_for_tool_use: false`** | 19.6 s |

The remaining four (`gemma-4-12b-qat`, `gemma-4-26b-a4b-qat`,
`prism-ml/bonsai-27b`, `ornith-1.0-35b`) were **not** probed; they declare tool
training and nothing here has confirmed it.

## Notes

### The gate lands in different places for different talk models

An `openai_api` talk model (LM Studio, Ollama) hits the console's own
`gated_tools` card. A CLI talk model reaches the same verb over MCP as
`mcp__console__delegate`, where the CLI's own permission dialog answers — which
the console cannot answer for you. Seen live: the Assistant on claude reported
`permission_denied` and then said "waiting on your approval", which is correct
and worth knowing.

### Untested

`work_model` against a non-claude work backend; OpenRouter as either role; and
the Ollama residency adapter, which is written to the documented `/api/ps`
shape but was not exercised (that box is not the one on the LAN).

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
