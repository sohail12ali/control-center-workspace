---
ticket: "T-011"
artifact: decision-log
---

# Decisions: T-011

## resume-in-place-not-as-a-copy
**Decision:** A resumed chat keeps its session id, its transcript file and its
working directory. Nothing is copied and no new chat appears in the list.
**Rationale:** It is the same conversation. A "resume" that produced a second
chat with the old text pasted above it would be a different feature wearing
this one's name.
**Impact:** `Stream` takes a `start_seq` so numbering continues in one file.

## refuse-rather-than-quietly-start-fresh
**Decision:** No session id in the transcript, or a backend that cannot
resume, raises.
**Rationale:** In a chat window, a resume that silently started a new session
looks exactly like one that worked. The user finds out several turns later,
when the model has forgotten everything.
**Impact:** Two explicit refusals with messages naming the cause.

## capability-is-read-off-the-config-row
**Decision:** `Backend.can_resume` looks for `{resume_id}` in the templates.
**Rationale:** The flags are a claim about a CLI, and `agents.toml` is where
this project keeps such claims — its own comments already say qwen's are
unverified. Hardcoding ids here would put the same knowledge in two places.
**Impact:** A backend gains resume by gaining a config row, not a code change.

## the-transcript-is-the-source-for-history
**Decision:** `transcript()` reads the file whenever there is one, and uses
the live session only for its snapshot.
**Rationale:** Found by opening a resumed chat: the in-memory ring holds only
what the current process published, which after a resume is two events.
**Impact:** One branch reordered; the whole conversation comes back.

## the-assistant-resumes-before-it-recreates
**Decision:** `_ensure_session` tries `resume` on a dead pointer first, and
logs which path it took.
**Rationale:** The Assistant's value is continuity. Silently starting over is
the failure mode that made this ticket worth doing.
**Impact:** A failed resume falls back to today's behaviour and says why,
rather than implying a continuity that is not there.

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
