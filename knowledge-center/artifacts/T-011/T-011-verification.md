---
ticket: "T-011"
artifact: verification
---

# Verification: T-011

Verified 2026-09-07. **pytest 1100 passed** (1088 before this ticket's tests),
harness lint clean, and the one check that no test can stand in for: a resumed
model was asked what it had been told before the console was restarted, and it
knew.

## The proof

```
1.  POST /api/agents/chats          "Remember this word: pomegranate."   -> "OK"
2.  transcript records the CLI's own id                b36c0d9b-f19b-405d-…
3.  console stopped                                    (the chat is now dead)
4.  console restarted; the chat lists as               resumable: true
5.  POST /api/agents/chats/{id}/resume                 alive: true
6.  send "What word did I ask you to remember?"        -> "Pomegranate."
```

Step 6 is the whole ticket. Everything else could have been faked by a chat
that merely looked continuous.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | A dead chat comes back live | PASS | The sequence above; `alive: true` on the same id, with no new chat in the list |
| 2 | The model remembers | PASS | "Pomegranate." — after a full console restart |
| 3 | The whole history comes back | PASS | 25 events and both replies (`OK`, `Pomegranate.`) on reopen, with `snapshot.alive` true |
| 4 | Refused when it cannot work | PASS | No session id in the transcript → "nothing to resume"; a backend without resume flags → "cannot resume a past chat"; unit-tested both ways |
| 5 | The listing says which | PASS | `resumable: true` on chats with an id and a capable backend, `false` on one without an id. The rail chip reads `resumable` instead of `past` |
| 6 | The Assistant continues itself | PASS | Live: `session.resumed` at seq 231 in the Assistant's own transcript, directly after turns from before the restart, then its next answer — instead of the fresh chat it used to start |
| 7 | Numbering continues, the seam is recorded | PASS | The resumed chat's events continue at 12, 13, 20 after the dead session's 8; `session.resumed` carries the CLI id it handed back |
| 8 | Resuming is audited | PASS | `chat.resume` recorded with actor and backend, alongside `chat.start` |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1100 passed
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

New tests cover what the transcript gives back (id, cwd, last seq; the last id
winning), both refusals, the listing flag, argv selection with and without a
resume template, that the shipped claude row can still resume, continued
sequence numbering, and the history bug below.

## A bug found by opening one

The first resumed chat opened with two events and no history. `transcript()`
preferred the live session's in-memory ring, which after a resume holds only
what the new process has published — the conversation was on disk the whole
time. It now reads the file whenever there is one and uses the session only
for its snapshot, with a test that fails if that ordering is reversed.

It is worth noting how this was found: the API said `alive: true`, the tests
were green, and the feature was wrong. Opening the thing is what caught it.

## Notes

### What cannot be resumed, and says so

- A chat whose transcript has no CLI session id — nothing to hand back.
- A backend whose `agents.toml` row declares no resume flags. `qwen`'s row
  already documents that its flags are unverified, and it is honestly listed
  as not resumable rather than being guessed at.
- `openai_api` sessions have no external process to resume; their history is
  the console's own and was never lost.

### Untested here

`cursor-agent` resume (it has `resume_args` for turns, and this ticket did not
exercise it live), and the case where the CLI itself has forgotten the session
id — the refusal comes from the CLI, and the error surfaces, but no run here
proved it.

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
