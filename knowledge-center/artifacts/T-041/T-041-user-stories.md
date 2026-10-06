---
ticket: "T-041"
artifact: user-stories
created: "2026-10-06"
---

# User Stories: T-041

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-041 stories` · **Validated by:** `validate-artifacts T-041 links` · **Verified by:** `validate-artifacts T-041 links`

## Story Format

```
US-{n}: Nightly link checker: flag artifact-map and Links entries that moved

As a {role}
I want to {action}
So that {benefit}

Acceptance Criteria:
- [ ] Criterion 1

Business Rules:
- Rule 1

Edge Cases:
- Case 1

Related Components: {component list}
Related Tasks: {task list}
```

## Stories

Source: frozen [[T-041-requirements]]. Tasks are in [[T-041-plan]].

### US-1: Find broken signposts with one command

**As a** workspace maintainer
**I want to** run one command that reports every wikilink in a Links block that points at nothing, and every ticket artifact without a proper Links block
**So that** a moved or renamed file is found the same day, not when someone clicks a dead link

**Acceptance Criteria:**
- [ ] A dangling target in a Links block is an ERROR with file and line; the same target in prose is a WARN (AC-14, AC-15)
- [ ] Missing, duplicate, fused or non-last Links blocks are reported with the right code (AC-13)
- [ ] Links inside code fences and spans are ignored; `|alias`, `#heading` forms resolve (AC-3, AC-4, AC-5, AC-6)
- [ ] Only ticket artifacts get block rules; `_template/` and `_shared/` do not (AC-1, AC-2)

**Business Rules:**
- Wikilinks only; case-sensitive basename match; frozen files are not exempt (the fix is a Links-only edit)

**Edge Cases:**
- BOM, CRLF, lone CR; relocated vault; unclosed `[[`

**Related Components:** `console/server/link_check.py` (extractor, resolver, artifact rules)
**Related Tasks:** T-041-01, T-041-02

**Priority:** High
**Story Points:** 8

---

### US-2: Catch artifact-map drift against ticket state

**As a** workspace maintainer
**I want to** be told when `artifact-map.md` disagrees with `ticket.toml`
**So that** the fleet index can be trusted (T-019, T-036, T-037 read "Open" while in `verify`)

**Acceptance Criteria:**
- [ ] Row format, dangling row, unknown ticket, missing row, duplicate row (AC-9, AC-10, AC-11)
- [ ] Status, section and title drift per the stage table; Archived rows and unknown stages skipped (AC-12)

**Business Rules:**
- Owner and date are not compared; the `blocked` row shape is an unverified assumption

**Edge Cases:**
- Map file absent: one `map-missing` and nothing else

**Related Components:** `link_check.py` (map rules)
**Related Tasks:** T-041-03

**Priority:** High
**Story Points:** 5

---

### US-3: See sibling-link hygiene without drowning in it

**As a** workspace maintainer
**I want to** see one-way and incomplete sibling links, and misplaced or duplicate-named files, as warnings
**So that** every ticket stays a connected cluster, while the 1,344 existing one-way pairs do not hide real errors

**Acceptance Criteria:**
- [ ] One-way pair gives one WARN at the missing side; mutual, self and cross-ticket links give none (AC-16)
- [ ] An incomplete block gives one WARN listing the missing siblings (AC-17)
- [ ] Misplaced artifact and ambiguous basename (AC-18, AC-7)

**Business Rules:**
- WARN by default; ERROR through `--strict` or a later flip (Q1)

**Edge Cases:**
- Sibling with no Links block counts as linking nothing

**Related Components:** `link_check.py` (sibling rules)
**Related Tasks:** T-041-02

**Priority:** Medium
**Story Points:** 5

---

### US-4: Read the result and trust the exit code

**As a** maintainer, CI step or script
**I want to** get a short, ordered, ASCII report (or JSON) and an exit code that means pass, fail or could-not-run
**So that** I can act on errors at once and automate on the code

**Acceptance Criteria:**
- [ ] Exit 0 / 1 / 2 contract with `--strict` (AC-19); all 20 codes covered (AC-20)
- [ ] JSON and text shapes, cap of 20 warnings per code, `--all`, deterministic order (AC-21, AC-22, AC-29)
- [ ] On the real vault the first screen shows the errors with a fix hint (AC-34, manual)
- [ ] `vault links [--json] [--strict] [--all] [--ticket]` works through the CLI (AC-23)

**Business Rules:**
- Errors never capped; text is ASCII only

**Edge Cases:**
- Missing vault; unknown `--ticket`

**Related Components:** `link_check.py` (assembly, output), `console/kanban.py`
**Related Tasks:** T-041-04, T-041-06, T-041-07

**Priority:** High
**Story Points:** 5

---

### US-5: Let an agent or verifier call the check per ticket

**As a** verifier agent (or any MCP or HTTP caller)
**I want to** call a `link-check` verb, optionally scoped to one ticket
**So that** I get findings and an `ok` flag without shelling out

**Acceptance Criteria:**
- [ ] Verb registered, not confirm-gated, returns `ok`, `summary`, `findings`, never raises on findings; `strict` flips `ok`; `ticket` scopes (AC-24)
- [ ] Present in the MCP tool list and the agent tool list (AC-25)

**Business Rules:**
- No UI, route or static file added (NFR-8)

**Edge Cases:**
- `strict` arrives as a string

**Related Components:** `verbs.toml`, `verb_handlers.py`
**Related Tasks:** T-041-06

**Priority:** Medium
**Story Points:** 3

---

### US-6: Have a nightly routine ready, parked

**As a** console operator
**I want to** a `link-check-nightly` row in `schedules.toml`, parked
**So that** I can turn it on after the repair pass without writing config

**Acceptance Criteria:**
- [ ] Row parses, verb exists, `enabled = false`, shipped-config test passes (AC-26)
- [ ] One tick on a throwaway console gives a `done` job with `result.ok` (AC-35, manual)

**Business Rules:**
- Not in CI; unparking waits for the repairs (T-041-R1, R2, R3)

**Edge Cases:**
- Console not running at 02:30: no run

**Related Components:** `schedules.toml`
**Related Tasks:** T-041-06, T-041-07, follow-ups R1 to R3

**Priority:** Medium
**Story Points:** 2

---

### US-7: Know the checker is safe, fast and portable

**As a** maintainer on Windows or Linux
**I want to** a checker that is read-only, stdlib-only, deterministic and quick
**So that** it can run unattended on any machine without surprise

**Acceptance Criteria:**
- [ ] Stdlib-only imports; no write calls; tree unchanged by a run (AC-27, AC-28)
- [ ] Same output twice; 2,000 files under 10 s; real repo under 5 s (AC-29, AC-30)
- [ ] CRLF/LF/lone CR/BOM equivalent; symlink and junction not followed; invalid UTF-8 survives (AC-31, AC-32, AC-33)

**Business Rules:**
- Reads only under the vault root; never opens a path built from a link target

**Edge Cases:**
- OS cannot create a symlink: test skipped with a reason

**Related Components:** `link_check.py`, `console/tests/test_link_check.py`
**Related Tasks:** T-041-05

**Priority:** High
**Story Points:** 3

---

### US-8: Find the rule documented

**As a** new contributor
**I want to** README and console SKILL to describe the command, severities and exit codes, and how it differs from `validate-artifacts`
**So that** I know what is automatic and what stays manual

**Acceptance Criteria:**
- [ ] README, console SKILL and the split sentence read correctly; no change under `console/static/` or `export.py` (AC-36, manual)

**Business Rules:**
- `validate-artifacts` text is left as is (FR-14)

**Edge Cases:**
- None

**Related Components:** `console/README.md`, `.claude/skills/console/SKILL.md`
**Related Tasks:** T-041-07

**Priority:** Low
**Story Points:** 1

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Find broken signposts | Pending | High | 8 | T-041-01, 02 |
| US-2 | Catch map drift | Pending | High | 5 | T-041-03 |
| US-3 | Sibling hygiene | Pending | Medium | 5 | T-041-02 |
| US-4 | Report and exit code | Pending | High | 5 | T-041-04, 06, 07 |
| US-5 | Per-ticket verb | Pending | Medium | 3 | T-041-06 |
| US-6 | Parked nightly | Pending | Medium | 2 | T-041-06, 07, R1-R3 |
| US-7 | Safe, fast, portable | Pending | High | 3 | T-041-05 |
| US-8 | Documented | Pending | Low | 1 | T-041-07 |

## Traceability Matrix

| Story | Components | Tasks | FR / NFR |
|-------|-----------|-------|----------|
| US-1 | extractor, resolver, artifact rules | T-041-01, 02 | FR-1, 2, 3, 6, 7 |
| US-2 | map rules | T-041-03 | FR-4, 5 |
| US-3 | sibling rules | T-041-02 | FR-8, 13 |
| US-4 | assembly, output, CLI | T-041-04, 06, 07 | FR-9, 10, 11 |
| US-5 | verb | T-041-06 | FR-12 |
| US-6 | schedule | T-041-06, 07 | FR-15 |
| US-7 | whole module | T-041-05 | NFR-1 to NFR-10 |
| US-8 | docs | T-041-07 | FR-14, NFR-8 |

All 36 acceptance criteria appear under at least one story: AC-1..6 (US-1), 7 (US-3), 9..12 (US-2), 13..15 (US-1), 16..18 (US-3), 19..23 (US-4), 24..25 (US-5), 26 (US-6), 27..33 (US-7), 34 (US-4), 35 (US-6), 36 (US-8). AC-8 (drift guard) is covered by US-1's resolution rule via task 01.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
