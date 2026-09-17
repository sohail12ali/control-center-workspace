---
ticket: "T-016"
artifact: user-stories
created: "2026-09-11"
---

# User Stories: T-016

**Created by:** `requirements T-016 stories` · **Frozen source:** [[T-016-requirements]]

## Stories

### US-1: Assistant is the shell home

**As a** person in the desktop shell
**I want to** land on the Assistant (talk, live runs, ticket strip)
**So that** I do not hunt through a kanban app to talk to the workspace

**Acceptance Criteria:**
- [ ] With `html.in-shell`, the Assistant tab is first and is the default view (FR-1)
- [ ] Without that class, Overview remains first and nav is unchanged (FR-1, BR-4)
- [ ] Tray `say` still uses the same Assistant session (FR-1)

**Business Rules:** BR-2, BR-4
**Edge Cases:** Browser `kanban.py serve` must not invert nav
**Related Components:** Assistant tab, in-shell nav
**Related Tasks:** 3-1-1, 3-1-2
**Priority:** High
**Story Points:** 5

---

### US-2: Watch work as Runs

**As a** person (or the talk model)
**I want** every piece of work to have a Run id I can watch
**So that** delegate and harness launch are not “some chat on the Agents tab”

**Acceptance Criteria:**
- [ ] `console_delegate` creates/points at a Run (FR-2)
- [ ] Assistant can name id and state without switching tabs (FR-2)
- [ ] Record survives console restart (FR-2)
- [ ] Agents tab lists that same id (FR-4)

**Business Rules:** BR-5
**Edge Cases:** interrupted vs done (`jobs.py` distinction, applied to Runs)
**Related Components:** Run store, delegate wrap, inspector
**Related Tasks:** 2-1-1, 2-1-2, 4-1-2
**Priority:** High
**Story Points:** 8

---

### US-3: Ticket action starts a Run

**As a** person on the board
**I want** the ticket’s primary agent action to ask the Assistant or create a Run
**So that** I am not dumped into the Agents composer

**Acceptance Criteria:**
- [ ] `startAgentFor` is not compose+`go("agents")` as the only path (FR-3)
- [ ] Action is ticket-scoped (FR-3)

**Business Rules:** BR-2
**Related Components:** Board JS
**Related Tasks:** 4-1-1
**Priority:** High
**Story Points:** 3

---

### US-4: Agents can move tickets through verbs

**As an** MCP or `openai_api` agent
**I want** ticket move/set and tracker add/update as tools
**So that** I do not shell `kanban.py` or edit TOML

**Acceptance Criteria:**
- [ ] MCP `tools/list` includes the four `console_*` verbs (FR-5)
- [ ] Invalid lane fails like `tickets.move` (FR-5)
- [ ] Pytest covers handlers (FR-5)

**Business Rules:** BR-1, BR-6
**Related Components:** Mutation verbs
**Related Tasks:** 1-1-1, 1-1-2
**Priority:** High
**Story Points:** 5

---

### US-5: Launch a harness role

**As a** person talking to the Assistant
**I want to** start analyst (etc.) on a ticket as a named Run
**So that** I can watch it; the work is a `cursor-agent` chat with that persona

**Acceptance Criteria:**
- [ ] Backend `cursor-agent` + persona; Run executor is chat id (FR-6)
- [ ] Missing binary fails named; no `claude` fallback (FR-6)
- [ ] Still seven `.claude/agents/` files (FR-6)

**Business Rules:** BR-3, BR-5
**Related Components:** Harness launch, Run store
**Related Tasks:** 2-1-3
**Priority:** High
**Story Points:** 5

---

### US-6: Wiki matches the product

**As a** future ticket
**I want** [[desktop-assistant]] to describe the Assistant, not the Agents tab, as the tray’s target
**So that** we do not re-litigate T-004

**Acceptance Criteria:**
- [ ] No “live Agents session” tray lock (FR-7)
- [ ] Wikilinks T-016 decisions (FR-7)

**Business Rules:** BR-2
**Related Components:** Wiki
**Related Tasks:** 5-1-1
**Priority:** Medium
**Story Points:** 2

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Assistant is the shell home | Pending | High | 5 | 3-1-1, 3-1-2 |
| US-2 | Watch work as Runs | Pending | High | 8 | 2-1-1, 2-1-2, 4-1-2 |
| US-3 | Ticket action starts a Run | Pending | High | 3 | 4-1-1 |
| US-4 | Agents can move tickets through verbs | Pending | High | 5 | 1-1-1, 1-1-2 |
| US-5 | Launch a harness role | Pending | High | 5 | 2-1-3 |
| US-6 | Wiki matches the product | Pending | Medium | 2 | 5-1-1 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | Assistant tab, in-shell nav | 3-1-1, 3-1-2 |
| US-2 | Run store, delegate wrap, inspector | 2-1-1, 2-1-2, 4-1-2 |
| US-3 | Board JS | 4-1-1 |
| US-4 | Mutation verbs | 1-1-1, 1-1-2 |
| US-5 | Harness launch, Run store | 2-1-3 |
| US-6 | Wiki | 5-1-1 |

## Links
- [[T-016-summary]] · [[T-016-requirements]] · [[T-016-user-stories]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
