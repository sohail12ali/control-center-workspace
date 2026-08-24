# Claude Code Environment Setup

**Workspace:** `{WORKSPACE_ROOT}`  
**Status:** Ready for implementation

---

## Phase 1: Foundation (GROUND)

### Current State

| Component | Location | Purpose |
|-----------|----------|---------|
| **Workspace** | `{WORKSPACE_ROOT}` | Main directory |
| **Vault** | `{WORKSPACE_ROOT}\knowledge-center` | Artifacts & knowledge |
| **Config** | `{WORKSPACE_ROOT}\.claude` | Settings & skills |

### Goals

1. Define 6 agents following harness pattern (GROUND → VERIFY)
2. Register core Claude Code skills
3. Integrate Obsidian vault for artifacts
4. Set up memory and configuration management

---

## Phase 2: Structure (CLARIFY)

### Workflow Integration

**Claude Code ↔ Obsidian**
- Artifacts created in: `{WORKSPACE_ROOT}\knowledge-center\artifacts\{TICKET_ID}\`
- Index at: `{WORKSPACE_ROOT}\knowledge-center\artifact-map.md`

**Agents ↔ Skills**
- 6 agents orchestrate workflows
- Skills provide capabilities (canvas, review, simplify, etc.)
- Memory: `{WORKSPACE_ROOT}\.claude\projects\{PROJECT}\memory\`

---

## Phase 3: Configuration (CANONICAL)

### Agents (6 Core)

| Agent | Stage | Purpose |
|-------|-------|---------|
| **Harness** | All | Master orchestration |
| **Analyst** | GROUND, CLARIFY | Context & requirements |
| **Planner** | CANONICAL | Strategy & planning |
| **Builder** | TEMPLATE | Code generation |
| **Verifier** | VERIFY | Testing & validation |
| **Fixer** | Any | Issue resolution |

### Skills (Core)

canvas · simplify · review · security-review · update-config · keybindings-help · loop · schedule · claude-api

### Suggested Custom Skills (Optional)

Based on existing workflows, consider creating custom skills from these categories:

#### Analysis & Planning

- `/analyze` — Code structure, components, context analysis
- `/requirements` — Draft, enrich, freeze requirements
- `/plan-effort` — Generate effort forecast & task breakdown
- `/validate` — Challenge requirements, validate artifacts

#### Artifact Management

- `/prepare-work` — Create ticket structure, prepare artifact
- `/trace-context` — Load & trace requirements & dependencies
- `/progress-tracker` — Update status, track progress
- `/release-prep` — Prepare & stage releases, generate SQL

#### Workflow Operations

- `/kickoff` — Initialize new project/ticket
- `/compare` — Compare with existing implementations
- `/consolidate` — Consolidate artifacts & changes
- `/close-work` — Archive & close tickets

#### Query & Report

- `/questions` — Generate open questions template
- `/stories` — Extract & organize user stories
- `/graph` — Create workflow graphs & visualizations
- `/release-status` — Check release readiness



### Configuration

**`.claude/settings.json`**
```json
{
  "workspace": {
    "path": "{WORKSPACE_ROOT}"
  },
  "vault": {
    "path": "{WORKSPACE_ROOT}\\knowledge-center",
    "artifacts": "{WORKSPACE_ROOT}\\knowledge-center\\artifacts"
  },
  "skills": [
    "canvas", "simplify", "review", "security-review",
    "update-config", "keybindings-help", "loop", "schedule", "claude-api"
  ],
  "permissions": {
    "bash": ["git.*", "npm.*", "python.*"],
    "file_write": ["{WORKSPACE_ROOT}\\knowledge-center\\**", "{WORKSPACE_ROOT}\\.claude\\**"]
  }
}
```

**`.obsidian/settings.json`**
```json
{
  "vault_path": "{WORKSPACE_ROOT}\\knowledge-center",
  "plugins": {
    "graph": { "enabled": true },
    "backlinks": { "enabled": true }
  }
}
```

---

## Phase 4: Structure (TEMPLATE)

### Directory Layout

```
{WORKSPACE_ROOT}/
├── .claude/
│   ├── settings.json
│   ├── projects/{PROJECT}/memory/
│   └── skills/
├── .obsidian/
│   └── settings.json
├── knowledge-center/
│   ├── artifacts/{TICKET_ID}/
│   │   ├── summary.md               [Artifact overview]
│   │   ├── requirements.md          [Specs & requirements]
│   │   ├── plan.md                  [Implementation plan]
│   │   ├── progress.md              [Work log & updates]
│   │   ├── analysis.md              [Context & findings]
│   │   ├── decision-log.md          [Decisions made]
│   │   └── [other files as needed]
│   ├── artifact-map.md              [Index of all artifacts]
│   └── knowledge-center-index.md    [Vault navigation]
├── CLAUDE.md
└── README.md
```

### Artifact Structure

#### Artifact Directory
- **Location:** `{WORKSPACE_ROOT}\knowledge-center\artifacts\{TICKET_ID}\`
- **Naming:** Use ticket ID (e.g., TASK-001, PROJ-Q1-002, FEATURE-AUTH)
- **Per-Artifact:** One directory per work item

#### Standard Artifact Files

| File | Purpose | Used In Phase |
|------|---------|---------------|
| **summary.md** | Ticket overview, status, links | All |
| **requirements.md** | Specifications, acceptance criteria | CLARIFY, CANONICAL |
| **plan.md** | Implementation strategy, steps | CANONICAL, TEMPLATE |
| **progress.md** | Work log, updates, blockers | TEMPLATE, SIMPLIFY, VERIFY |
| **analysis.md** | Context findings, research | GROUND, CLARIFY |
| **decision-log.md** | Decisions, rationale, alternatives | CLARIFY, CANONICAL |

#### Optional Files (As Needed)
- `architecture.md` — System design, diagrams
- `risks.md` — Known risks, mitigation
- `notes.md` — Research, exploration notes
- `test-plan.md` — Testing strategy & results
- `verification.md` — QA findings, sign-off

### Artifact File Templates

#### summary.md
```markdown
# {TICKET_ID}: {Title}

**Status:** [Open | In Progress | Blocked | Complete]
**Owner:** {Name}
**Created:** {DATE}
**Due:** {DATE}

## Overview
[Brief description of work]

## Key Links
- Requirements: [[requirements]]
- Plan: [[plan]]
- Progress: [[progress]]

## Current State
[Latest status update]
```

#### requirements.md
```markdown
# Requirements: {TICKET_ID}

## Functional Requirements
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

## Non-Functional Requirements
- [ ] Performance requirement
- [ ] Security requirement
- [ ] Scalability requirement

## Acceptance Criteria
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

## Out of Scope
- Not including X
- Not including Y

## Related: [[summary]]
```

#### plan.md
```markdown
# Implementation Plan: {TICKET_ID}

## Approach
[Strategy and rationale]

## Tasks
1. [ ] Task 1
   - Subtask 1a
   - Subtask 1b
2. [ ] Task 2
3. [ ] Task 3

## Dependencies
- Depends on: [[TASK-XXX]]
- Blocks: [[TASK-YYY]]

## Effort Estimate
- Total: {N} hours/days
- Breakdown: Task1 ({n}h), Task2 ({n}h)

## Timeline
- Start: {DATE}
- End: {DATE}

## Risks
- Risk 1: Mitigation
- Risk 2: Mitigation

## Related: [[summary]], [[requirements]]
```

#### progress.md
```markdown
# Progress Log: {TICKET_ID}

## {DATE} - Update Title
- Completed X
- Started Y
- Blocked by Z
- Next: A

## {DATE} - Update Title
- [progress entry]

## Key Milestones
- [X] Milestone 1 - {DATE}
- [ ] Milestone 2 - {DATE}
- [ ] Milestone 3 - {DATE}

## Blockers
- Blocker 1: Description, impact, ETA
- Blocker 2: Description, impact, ETA

## Related: [[summary]], [[plan]]
```

#### analysis.md
```markdown
# Analysis: {TICKET_ID}

## Context
[Background, why this work matters]

## Current State
[Existing situation, findings]

## Key Findings
- Finding 1: Significance
- Finding 2: Significance
- Finding 3: Significance

## Research
[References, sources, related work]

## Recommended Path Forward
[Direction based on analysis]

## Related: [[summary]], [[requirements]]
```

### Artifact Hierarchy & Breakdown

Organize work into nested levels for clarity and deliverability:

```
TICKET-001 (Main artifact)
│
├── SLICE-001 (Vertical slice: complete feature end-to-end)
│   │   [Includes: Entities → DB → API → UI]
│   │
│   ├── PHASE-ENTITIES (Data model work)
│   │   ├── TASK-ENTITY-001 (Define User entity)
│   │   ├── TASK-ENTITY-002 (Define Post entity)
│   │   └── TASK-ENTITY-003 (Define relationships)
│   │
│   ├── PHASE-DB (Database work)
│   │   ├── TASK-DB-001 (Create User table)
│   │   ├── TASK-DB-002 (Create Post table)
│   │   └── TASK-DB-003 (Create indexes)
│   │
│   ├── PHASE-API (Backend work)
│   │   ├── TASK-API-001 (User endpoints)
│   │   ├── TASK-API-002 (Post endpoints)
│   │   └── TASK-API-003 (Authentication)
│   │
│   └── PHASE-UI (Frontend work)
│       ├── TASK-UI-001 (User dashboard)
│       ├── TASK-UI-002 (Post list)
│       └── TASK-UI-003 (Post creation)
│
└── SLICE-002 (Vertical slice: another complete feature)
    ├── PHASE-ENTITIES
    ├── PHASE-DB
    ├── PHASE-API
    └── PHASE-UI
```

#### Breakdown Strategy

**Ticket Level**
- Location: `{WORKSPACE_ROOT}\knowledge-center\artifacts\TICKET-001\`
- Content: Overall project summary, strategy, all slices
- File: `summary.md`, `plan.md`, `requirements.md`

**Slice Level**
- Location: `{WORKSPACE_ROOT}\knowledge-center\artifacts\TICKET-001\SLICE-001\`
- Content: Vertical slice overview (entities → db → api → ui)
- File: `slice-summary.md` (links to all phases below)
- Each slice delivers complete end-to-end value

**Phase Level**
- Location: `{WORKSPACE_ROOT}\knowledge-center\artifacts\TICKET-001\SLICE-001\PHASE-DB\`
- Content: One layer (Entities, DB, API, or UI) for one slice
- File: `phase-summary.md`, `tasks.md`, `progress.md`
- Owned by single person/team

**Task Level**
- Location: File in phase directory or inline in `tasks.md`
- Content: Atomic unit of work (1-4 hours)
- Format: Checkbox in `tasks.md` with description and status

#### Artifact Map Structure

Link hierarchy in `artifact-map.md`:

```markdown
# Artifact Map

## TICKET-001: Complete User Feature

### SLICE-001: User Authentication

- [[TICKET-001/SLICE-001/PHASE-ENTITIES]] — User entity & permissions
- [[TICKET-001/SLICE-001/PHASE-DB]] — User tables & indexes
- [[TICKET-001/SLICE-001/PHASE-API]] — Auth endpoints & validation
- [[TICKET-001/SLICE-001/PHASE-UI]] — Login & registration flows

### SLICE-002: User Profile

- [[TICKET-001/SLICE-002/PHASE-ENTITIES]] — Profile entity
- [[TICKET-001/SLICE-002/PHASE-DB]] — Profile tables
- [[TICKET-001/SLICE-002/PHASE-API]] — Profile endpoints
- [[TICKET-001/SLICE-002/PHASE-UI]] — Profile pages
```

#### Naming Convention for Breakdown

| Level | Naming | Example |
|-------|--------|---------|
| **Ticket** | `TICKET-###` or `FEATURE-NAME` | `TICKET-001`, `FEATURE-AUTH` |
| **Slice** | `SLICE-###` (under ticket) | `SLICE-001`, `SLICE-AUTH-BASIC` |
| **Phase** | `PHASE-LAYER` | `PHASE-ENTITIES`, `PHASE-DB`, `PHASE-API`, `PHASE-UI` |
| **Task** | `TASK-LAYER-###` | `TASK-ENTITIES-001`, `TASK-API-002` |

### Artifact Lifecycle

**GROUND → CLARIFY**
- Create artifact directory
- Write summary.md (overview)
- Write analysis.md (context)
- Link in artifact-map.md

**CLARIFY → CANONICAL**
- Complete requirements.md
- Write decision-log.md
- Gather feedback
- Update summary.md status

**CANONICAL → TEMPLATE**
- Create plan.md
- Decompose into tasks
- Estimate effort
- Define blockers & risks

**TEMPLATE → SIMPLIFY → VERIFY**
- Update progress.md continuously
- Log milestones
- Track blockers
- Document verification results

**VERIFY → Close**
- Final summary.md update
- Mark status as Complete
- Archive if appropriate
- Update artifact-map.md

### Artifact Naming Conventions

| Pattern | Example | Use Case |
|---------|---------|----------|
| **TASK-###** | TASK-001, TASK-042 | Individual tasks |
| **PROJ-XXX** | PROJ-Q1, PROJ-2024 | Projects |
| **FEATURE-NAME** | FEATURE-AUTH, FEATURE-UI-V2 | Features |
| **BUG-### or BUG-NAME** | BUG-001, BUG-LOGIN-CRASH | Bug fixes |
| **EPIC-NAME** | EPIC-PLATFORM, EPIC-INFRASTRUCTURE | Large initiatives |

### Best Practices

✅ **DO**
- One artifact per work item
- Link related artifacts using [[wikilinks]]
- Update progress.md regularly
- Keep summary.md status current
- Add decision-log.md for significant decisions
- Use templates for consistency
- Tag artifacts in summary.md (`#active`, `#completed`, `#blocked`)

❌ **DON'T**
- Store artifacts outside designated folder
- Mix multiple work items in one artifact
- Leave progress.md stale
- Skip linking to artifact-map.md
- Use vague or duplicate ticket IDs
- Store large binaries (use links instead)

### Artifact Queries in Obsidian

Use tags to query artifacts in Obsidian:

```
#active — Active/in-progress artifacts
#blocked — Artifacts with blockers
#completed — Finished artifacts
#urgent — High-priority work
#waiting — Waiting on external dependencies
```

Add tags to summary.md frontmatter:
```yaml
---
tags: [active, urgent]
status: In Progress
---
```

---

## Phase 5: Review (SIMPLIFY)

- [ ] Paths are absolute and use backslashes
- [ ] `.claude/settings.json` valid JSON
- [ ] `.obsidian/settings.json` valid JSON
- [ ] Vault exists at `{WORKSPACE_ROOT}\knowledge-center\`
- [ ] Artifacts directory exists
- [ ] Memory directory ready
- [ ] Config files in place

---

## Phase 6: Verification (VERIFY)

### Test Checklist

```
1. Config loads without errors
   ✓ .claude/settings.json valid
   ✓ .obsidian/settings.json valid

2. Vault integration
   ✓ Obsidian opens vault at {WORKSPACE_ROOT}\knowledge-center\
   ✓ Artifact directory exists

3. Skills test
   ✓ /canvas works
   ✓ /simplify functions

4. End-to-end workflow
   ✓ Create artifact in {WORKSPACE_ROOT}\knowledge-center\artifacts\DEMO\
   ✓ Link in artifact-map.md
   ✓ Verify in Obsidian graph

5. Memory system
   ✓ Memory path accessible: {WORKSPACE_ROOT}\.claude\projects\{PROJECT}\memory\
```

---

## Implementation Checklist

- [ ] Create directories (vault, artifacts, memory)
- [ ] Create `.claude/settings.json` with absolute paths
- [ ] Create `.obsidian/settings.json`
- [ ] Create `{WORKSPACE_ROOT}\knowledge-center\artifact-map.md`
- [ ] Create `{WORKSPACE_ROOT}\knowledge-center\knowledge-center-index.md`
- [ ] Test all 6 agents load correctly
- [ ] Test core skills execute
- [ ] Verify Obsidian vault opens
- [ ] Run end-to-end workflow (GROUND → VERIFY)

---

## Path Reference

```
Workspace:           {WORKSPACE_ROOT}
Vault:               {WORKSPACE_ROOT}\knowledge-center
Artifacts:           {WORKSPACE_ROOT}\knowledge-center\artifacts
Memory:              {WORKSPACE_ROOT}\.claude\projects\{PROJECT}\memory
Claude Config:       {WORKSPACE_ROOT}\.claude\settings.json
Obsidian Config:     {WORKSPACE_ROOT}\.obsidian\settings.json
Artifact Map:        {WORKSPACE_ROOT}\knowledge-center\artifact-map.md
```

---

## Quick Start Workflow

1. **GROUND:** Analyze state → save to `artifacts\{ID}\analysis.md`
2. **CLARIFY:** Document decisions → update `artifacts\{ID}\summary.md`
3. **CANONICAL:** Create plan → save to `artifacts\{ID}\plan.md`
4. **TEMPLATE:** Generate scaffold → use `/canvas` if needed
5. **SIMPLIFY:** Use `/simplify` skill → refine code
6. **VERIFY:** Test & validate → document in `artifacts\{ID}\verification.md`
7. **Link:** Add to `artifact-map.md`

---

## Document Info

- **Type:** Claude Code Environment Setup Guide
- **Purpose:** Reusable template for establishing Claude Code environments
- **Placeholder:** Replace `{WORKSPACE_ROOT}` with your workspace path
- **Setup Time:** ~15 minutes
