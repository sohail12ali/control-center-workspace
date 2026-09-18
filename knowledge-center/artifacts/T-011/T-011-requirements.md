---
ticket: "T-011"
artifact: requirements
---

# Requirements: T-011

## Functional Requirements
1. A chat from a previous run can be resumed, keeping its id, its transcript
   and the model's context.
2. The Agents tab says which past chats can be resumed and offers the button
   only for those.
3. The Assistant continues its own chat across a restart, rather than starting
   a new one.
4. A resume that cannot work is refused with the reason.
5. The transcript records where one process handed over to the next.

## Non-Functional Requirements
1. Whether a backend can resume is read off its config row, never hardcoded.
2. A resumed chat's events continue the existing numbering.
3. Resuming is audited exactly like starting a chat — it spawns the same
   process with the same reach.

## Acceptance Criteria
- [x] 1. `POST /api/agents/chats/{id}/resume` brings a dead chat back live.
- [x] 2. A resumed model demonstrably remembers the earlier conversation.
- [x] 3. Opening a resumed chat shows its whole history, not only the part
      after the resume.
- [x] 4. Refused, with a message, when there is no session id in the
      transcript or the backend cannot resume.
- [x] 5. `resumable` appears on the listing; the UI shows Resume only then.
- [x] 6. The Assistant resumes its pointer's chat, and falls back to a new
      chat while saying why.
- [x] 7. Sequence numbers continue; `session.resumed` is in the transcript.

## Out of Scope
- Resuming a chat whose CLI has forgotten the id (nothing can fix that from
  here; the refusal is the answer).
- `openai_api` sessions, which have no external process to resume — their
  history is already the console's own.

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
