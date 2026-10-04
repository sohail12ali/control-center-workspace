---
ticket: "T-002"
artifact: user-stories
created: "2026-09-05"
---

# User Stories: T-002

**Created by:** `requirements T-002 stories`

## Stories

### US-1: Show from the tray

**As a** desktop user
**I want to** left-click the tray or pick Show window
**So that** the existing Console window comes back without starting a second session

**Acceptance Criteria:**
- [ ] Hide then Show restores the same window
- [ ] Left-click does not send, listen, or approve tools

**Business Rules:** BR-1
**Related Tasks:** T-002-01, T-002-02
**Priority:** High

### US-2: Drive the live Agents chat from the tray

**As a** desktop user
**I want to** New chat, Mute replies, and Interrupt from the tray
**So that** I control the current Agents session without a second product

**Acceptance Criteria:**
- [ ] New chat opens the existing form, no `/send`
- [ ] Mute toggles `autoRead` and can stop speaking
- [ ] Interrupt uses existing HTTP when a chat is busy; toast when not

**Business Rules:** BR-1, BR-3
**Related Tasks:** T-002-03
**Priority:** High

### US-3: Quit without killing a reused server

**As a** desktop user
**I want to** close to the tray and Quit separately
**So that** an already-running `kanban.py serve` survives, and an owned one stops on Quit

**Acceptance Criteria:**
- [ ] Close leaves serve up
- [ ] Quit owned stops serve
- [ ] Quit reused leaves serve up

**Business Rules:** BR-4
**Related Tasks:** T-002-02
**Priority:** High

### US-4: Honest catalog

**As a** maintainer
**I want to** `features.toml` to show which tray rows actually work
**So that** later phases can flip `available` without a parallel menu list

**Acceptance Criteria:**
- [ ] Six skeleton rows `available = true`; all others false

**Business Rules:** BR-2
**Related Tasks:** T-002-04
**Priority:** Medium

## Story Status Summary

| Story ID | Title | Status | Priority | Related Tasks |
|----------|-------|--------|----------|---------------|
| US-1 | Show from the tray | Pending | High | T-002-01, T-002-02 |
| US-2 | Drive live Agents chat | Pending | High | T-002-03 |
| US-3 | Quit vs hide | Pending | High | T-002-02 |
| US-4 | Honest catalog | Pending | Medium | T-002-04 |

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-user-stories]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
