# /do — dispatch reference

Detailed rules for [SKILL.md](SKILL.md). Loaded on demand (one level deep). The SKILL.md flow holds the compact decision tables; this file holds the full enumerations Claude reads only when a lane, gate, or loop decision is non-trivial.

## Contents
- Principles — safe progress + caveman output
- Lane tie-breakers
- Lane D — fan-out + adversarial verify
- Step 2b — SKILL MATCH scoring + multi-skill
- Step 2c — AGENT MATCH + spawn procedure
- ACT vs ASK boundary (full enumeration)
- Agentic loop driver, loop bounds + budget heuristic

---

## Principles — safe progress + caveman output

**Safe progress:** Every increment moves toward DONE without collateral damage. Before editing: read surrounding code, match local conventions, minimize diff scope. Prefer extend-over-replace. After editing: run the narrowest check that proves the change (build, test, lint on touched files). If a fix requires touching unrelated surfaces, split — ship the safe increment, ASK or defer the risky one.

**Caveman output:** load `.claude/skills/caveman/SKILL.md` when applying. Drop articles/filler/hedging in user-facing `/do` prose. Keep technical terms, paths, error strings, code exact. Pattern: `[thing] [action] [reason]. [next].` Resume full sentences per caveman Auto-Clarity (security, irreversible, ASK-GATE).

---

## Lane tie-breakers

First match wins on the Step 2 table. When two lanes plausibly fit:

- ticket id present → **A deliver**
- "just tell me / find / trace" → **D investigate**
- explicit `/name` in the text → **B skill** (skip 2b — honor the named skill)
- repo path outside this workspace root, or explicit build/test/publish verb naming a sub-project → **E cross-repo**
- feature-shaped with no other signal → **A deliver** (default)

Low-confidence or genuinely ambiguous classification → treat as a blocking unknown (ASK per Step 1). Do **not** guess a lane.

---

## Lane D — fan-out + adversarial verify

For non-trivial investigations only. Skip for simple one-answer lookups — a single targeted read is enough.

1. **Fan-out** — run 2–3 parallel read angles (e.g. grep + artifact read + `validate-artifacts trace`).
2. **Challenge** — for each finding, actively seek contradicting evidence ("can I find a counter-example or a more recent state that disproves this?"). Drop findings that don't survive; flag contested ones.
3. **Synthesize** — one answer built only from surviving findings, with `file:line` citations.

---

## Step 2b — SKILL MATCH scoring + multi-skill

Runs when lane = B, or to confirm fuzzy A/C/E. Source of truth: **live skill catalog** — never invent skill ids.

1. **Extract intent** — action verb(s) + object (e.g. "estimate effort", "map dependencies", "check artifact links").
2. **Score by `description`** (purpose + trigger), not name alone. Prefer the skill naming the exact artifact/phase.
3. **Disambiguate by specificity** — e.g. `estimate(mode=forecast)` (mid-build, task-level) over `estimate(mode=upfront)` (upfront, order-of-magnitude); `validate-artifacts links` over the default structure scope when only link integrity is in question. Redirect in description → lane E.
4. **Single vs multi-skill:**
   - **One skill** — default when one description clearly covers the whole request.
   - **Multi-skill** — when any of:
     - **Independent subtasks** — e.g. `analyze-components` + `plan risk` for a scope-impact question (parallel load if no dependency).
     - **Explicit pipeline handoff** — e.g. `requirements freeze` → `requirements stories`.
     - **Complementary surfaces** — different layers/artifacts, no overlap (e.g. `verify cases` + `validate-artifacts links` for coverage plus traceability).
   - Order: dependencies first; parent reconciles outputs. Cap ~3 unless pipeline specifies more. Do **not** stack skills that solve the same slice — pick the most specific one.
5. **Confidence gate** — top not a clear win → ASK with the 2 closest skills as closed choices.

Record chosen skill(s), runner-up, reason → `🧭 DISPATCH`.

---

## Step 2c — AGENT MATCH + spawn procedure

After the lane is set, decide the **executor**: inline, or one/more agents spawned via the **Agent** tool. Source of truth is the **live agent catalog** (`available agent types` injected this session) — never invent an agent type.

1. **Inline vs delegate** — execute inline for short, single-surface work that fits the main context. **Delegate to a subagent** when the work is (a) a whole role-phase, (b) read-heavy enough to flood context (broad searches → `Explore`), (c) independently parallelizable, or (d) better isolated (worktree edits that would conflict).
2. **Pick the agent by role**, most-specific first — use the Step 2c table in [SKILL.md](SKILL.md). Prefer a named role agent (`analyst`/`planner`/`builder`/`verifier`/`fixer`/`deployer`) over `general-purpose`; use `Explore` for read-only sweeps and `Plan` for architecture/plan questions. `deployer` is never auto-triggered by a clean verify — it only runs on an explicit deploy/publish request, still gated by ASK.
3. **Lane A defers to kickoff** — `/kickoff {ID} full` already orchestrates analyst→planner→builder→verifier with fixer handoffs. Do **not** hand-spawn those roles in parallel to it; let kickoff own the chain.
4. **Parallel fan-out** — independent subtasks (read angles, layer-by-layer analysis, parallel skill surfaces) → spawn **multiple Agent calls in one message**. Same turn can combine multi-skill load + multi-agent spawn when subtasks don't depend on each other. Cap at loop bounds (handoff/spawn depth ≤2); parent aggregates before next PLAN.
5. **Spawn threshold (heavy build)** — large multi-file, multi-layer builds → parallel child `builder`s by layer/slice; below that, one agent or inline.
6. **Continuity** — to add work to an agent already running this session, use **SendMessage** with its id/name (context preserved) instead of spawning a fresh one.
7. **Confidence gate** — if no agent is a clear win, **ASK rather than guess** (offer the 2 closest as closed choices) per Step 1.

Record chosen agent(s), parallel-vs-serial, and reason → surfaced in `🌿 SPAWN` at REPORT.

---

## ACT vs ASK boundary (full enumeration)

**✅ ACT freely (no prompt):** investigate · grep · trace · read-only artifact/vault reads · draft / plan / breakdown · write/edit in-repo source (diffs) · build / compile · analyzers · vault/artifact writes · artifact-map updates.

**🛑 ASK first (stop, batch up front, never auto-approve):**
- **Deploy / publish** — any publish skill, writes under a release/staging output path.
- **External system writes** — any non-read operation against a system outside this repo (database, SaaS API, ticket tracker, cloud resource). Classify by the operation's intent, not by tool name: pure lookups/reads are ACT; anything that creates, updates, deletes, or triggers a side effect elsewhere is ASK.
- **Git** — push, branch create, commit, PR open/merge; any destructive git.
- **Secrets** — never read or echo credentials, tokens, connection strings, or `.env`-style files.
- **External / networked MCP mutations** — WebFetch/WebSearch feeding a write, third-party API writes, scheduling/remote-trigger tools.
- **Scale** — >10 files or a risky refactor (harness-standards §9 equivalent).
- **Wrong tree** — edits outside the intended project root, or into a sub-project's tree when the request was scoped to this workspace's own artifacts (and vice versa).

**⛔ Inherited hard stops (link, don't restate):** unresolved **open**/**blocker** items in `{ID}-questions.toml` or a failed harness gate → stop at the affected gate. Canonical: `.claude/skills/kickoff/SKILL.md` + `harness.md`.

**Conflict-split:** a request that both reads and demands a gated action ("fix and push") splits — ACT the fix, ASK before push. Never bundle work past a gate.

**How it asks:** batch all blocking unknowns once at Step 1 via `clarify`. Non-blocking gaps → proceed with a ≤3-line stated-assumptions block. An ASK trigger reached mid-run emits an `ASK-GATE:` block: what's done · the exact gated action · the decision needed · 2 options — answerable in one message.

---

## Agentic loop driver, loop bounds + budget heuristic

`/do` runs Step 3 as an **iterate-until-done loop**, not a single dispatch. The cycle:

```
DEFINE  → one-line success criterion (the observable check that ends the loop); >~3 steps → seed a task list
PLAN    → choose the next smallest increment (or the next agent to spawn / message)
ACT     → invoke the skill / spawn|continue the agent(s) / call the tool
OBSERVE → capture a micro-feedback line: ✓ {tool} → {what changed} | ✗ {tool} → {error}
EVALUATE→ run the termination table below; if none fire, re-PLAN with the new state
```

- **Define DONE first.** The success criterion is set before the first PLAN; if it isn't measurable, that's a blocking unknown → ASK (Step 1), don't loop blindly. A task list (`TaskCreate`) is the loop's persisted state — it survives context compaction and is what a `🔁 RESUME?` reattaches to.
- **One increment per turn**, then re-evaluate — never batch past a gate or assume the goal is done after a single action when work remains.
- **Verify before Done.** The `Goal achieved` row requires the criterion's *actual check to have passed this run* (re-build, re-run tests/ACs, re-read the artifact, `verifier` for code) — not an inference from the last action. An unrun or failed check is **not** Done: loop again, or `ASK-GATE` if not autonomously fixable.
- **Retry-with-memory (N=3).** A failed increment is never re-fired unchanged. On `✗`, note the failing tactic and root cause (in-conversation, or in `{ID}-questions.toml` as a `blocker` if the ticket will be resumed later); re-attempt with a **different tactic** up to **3 varied attempts**; before re-planning any increment, check for a prior noted failure on the same goal-step and adopt its learning rather than repeating a known-bad approach. 3rd failure → `escalated` + `ASK-GATE: stuck`.
- **Delegated loops nest**: lane A's `/kickoff` and a spawned agent each run their own inner loop; `/do`'s outer loop tracks only handoff/spawn depth and overall termination.
- **Recurring/watch tasks** (poll a build, retry until green, run every N min) are driven by the **`/loop`** skill — the canonical recurring driver. Use `/loop {interval} /do {task}` for a **fixed cadence**, or invoke `/loop` with **no interval** to let the model **self-pace** (it schedules its own next wake). Reach for a one-off scheduled wakeup only for a single deferred re-entry that isn't a real loop. Schedule the next wake and exit cleanly; do **not** sleep-spin inside one turn. Each wake is one self-contained `/do` increment that re-checks the success criterion and terminates when met.

After every tool call or file write, capture the micro-feedback line and evaluate termination before the next action. The micro-feedback line feeds the next PLAN step; it is not emitted to the user unless execution fails.

| Condition | Termination |
|---|---|
| Goal achieved **and success criterion re-verified this run** (build green, ACs pass, artifact re-read, answer cited) | **Done** → Step 4 |
| Increment failed **3 varied attempts** (or same tool+args fired twice, no change) | **Stuck** → emit `ASK-GATE: stuck` — the 3 tactics tried, what didn't change |
| Context window >80% estimated consumed | **Checkpoint** → note current state as `blocker: context-budget` (in `{ID}-questions.toml` if ticketed), emit `ASK-GATE: budget — N steps remain unfinished`, then Step 4 with partial log |
| Hard-stop hit (open blocker, failed gate) | **Abort** → persist progress, list deferred actions, Step 4 |
| Handoff depth > 2 | **Escalate** → surface to user, do not recurse further |

**Budget heuristic:** treat context as near-limit when a sub-task chain has already consumed 3+ full skill loads or equivalent. Exact tracking is not possible — use depth + output volume as the proxy. Err on the side of checkpointing early for lane A; lane D/B investigations are short enough to skip the check.

Loop bounds: handoff depth ≤2, ~5-min timebox per increment, verifier→builder one re-run then escalate.
