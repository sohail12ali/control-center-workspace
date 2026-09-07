---
ticket: "T-011"
artifact: plan
---

# Plan: T-011

## Approach

Everything needed is already written down; what is missing is the way back in.
Recover the identity from the transcript, teach the backend how to hand a
session id back, rebuild the session in place, then expose it.

## Tasks

### [x] T-011-01 — Recover the identity (1 h)
- [x] `_meta_from_transcript` also returns cwd, the CLI session id, and the
      highest seq
- [x] `agent_events.last_seq`, and `Stream(start_seq=...)`
- **Done-criteria:** a dead chat's transcript yields everything needed to
  start the same conversation again
- **Depends on:** —

### [x] T-011-02 — Teach the backends (1 h)
- [x] `session_argv(resume_id=...)` selecting `resume_session_args`
- [x] `Backend.can_resume`, reported on the snapshot
- [x] claude's `resume_session_args` in `agents.toml`
- **Depends on:** T-011-01

### [x] T-011-03 — Resume in place (2 h)
- [x] `agent_manager.resume`, same id, same file, continued numbering
- [x] Two refusals; a `session.resumed` event marking the seam
- [x] `transcript()` reads the file so history survives
- **Depends on:** T-011-02

### [x] T-011-04 — Surfaces (1 h)
- [x] `POST /api/agents/chats/{id}/resume`, audited as `chat.resume`
- [x] `resumable` on the listing; the chip and the Resume button
- **Depends on:** T-011-03

### [x] T-011-05 — The Assistant (1 h)
- [x] `_ensure_session` resumes its pointer's chat before creating one
- **Depends on:** T-011-03

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-011-01 — Recover the identity | 1 h | reading what is already written |
| T-011-02 — Teach the backends | 1 h | mirrors `turn_argv` |
| T-011-03 — Resume in place | 2 h | the new path |
| T-011-04 — Surfaces | 1 h | one route, one button |
| T-011-05 — The Assistant | 1 h | one branch in `_ensure_session` |
| **Total** | **6 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1, 2 | T-011-03 |
| 3 | T-011-03 |
| 4 | T-011-03 |
| 5 | T-011-04 |
| 6 | T-011-05 |
| 7 | T-011-01, T-011-03 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| A resume that quietly starts a new chat | Med | High | Refuse loudly; prove memory with a word only the old process knew | Builder |
| Duplicate sequence numbers in one file | High | Med | `start_seq` from the transcript, with a test | Builder |
| History lost on reopen | Med | High | `transcript()` reads the file; found live, fixed, and pinned by a test | Builder |
| A CLI that has forgotten the id | Med | Low | The CLI refuses, the error surfaces, a new chat is one click away | Builder |

## Dependencies
- Blocks: —
- Blocked by: —

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
