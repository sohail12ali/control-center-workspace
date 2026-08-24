# Delivery Console feature comparison — CCW vs ShopLC (lc-wms-cursor-config)

**Date:** 2026-08-24 · **Scope:** `control-center-workspace/console/` (~12.7k lines) vs `lc-wms-cursor-config/.kanban/` (~39.4k lines).
The ShopLC console is the company-specific fork this template was genericized from; by design it carries integrations and volume features the template deliberately leaves out. Rows marked **NEW** landed in CCW on 2026-08-24 (ported from ShopLC per T-request: question interface, voice, models, themes).

## Feature matrix

| Feature | CCW (this workspace) | ShopLC | Why the difference |
|---|---|---|---|
| Tickets / Investigations boards | ✅ | ✅ | Core in both |
| Migrations / Releases boards | Config present, `enabled = false` | ✅ fully built, with editors | ShopLC has real release/migration workflows; template ships the schema off-by-default so a fork flips a flag |
| Projects tab (git across repos) | ❌ | ✅ (1,047-line tab) | Multi-repo git fleet view is company workflow; template keeps repo routing in `project-layout` skill instead |
| Files tab (release packages) | ❌ | ✅ | Package validation is ShopLC's release process |
| Overview / Analytics / Work / Todos / Vault / About / Settings | ✅ | ✅ | Parity |
| Plugin architecture (`plugins.toml` removes routes + tab) | ✅ | Feature-gated tabs (similar effect, different seam) | CCW rebuilt this cleaner during genericization |
| Onboarding report (`kanban.py onboard`) | ✅ read-only 6-step | ✅ `onboard` + `doctor --fix` (self-fixing) + `people.toml` roster | ShopLC manages a team roster; template stays personal |
| **Agent chats (live stream-json, steer/queue, interrupt)** | ✅ | ✅ | Parity |
| **Approval gate (PreToolUse hook → "Permission needed" card)** | ✅ **NEW** — `gated_tools` in agents.toml; Allow once / Allow for chat / Deny; fail-closed timeout; acceptEdits auto-allows edits | ✅ (the original) | Ported. CCW adds the acceptEdits carve-out so mode blurbs stay truthful |
| AskUserQuestion widget | ❌ (renders as tool card) | ❌ (same) | Neither special-cases it; the approval card + steer composer is the human-in-the-loop surface in both |
| **Voice announcements ("The agent is done." / "Permission needed for X")** | ✅ **NEW** — announce pref on by default, per-chat toggle | ✅ (the original) | Ported; both suppress the done-line when read-aloud already spoke the reply |
| Read-aloud + dictation | ✅ (already had) | ✅ | Parity; ShopLC adds auto-send-after-dictation and a voice test button |
| **Model picker** | ✅ **NEW** — 11-entry Claude shortlist (aliases + pinned incl. `claude-fable-5`, `claude-opus-5`) with labels/hints + custom-id box | ✅ `models.toml` per backend (8 claude + 12 cursor entries) + custom-id box | Ported; CCW keeps it in `agents.toml` (labels/hints sub-tables) since tomlio has no inline tables |
| **Themes** | ✅ **NEW** — 5 (System/Light/Dark/VS Dark/VS Light), 4-colour sampled swatches (2×2) | ✅ 6 — same five plus a **custom-theme builder** (7 seed colours → ~47 derived tokens, WCAG audit, corner/typeface axes) | Swatches + VS themes ported. The custom builder (~300 lines of colour math) not ported — say the word and it can be |
| Worktree isolation (`kanban/<ticket>` branch per run) | ❌ (explicitly warned against concurrent runs) | ✅ per-repo worktrees + preview + CLI management | Big, git-topology-aware feature; template records it as a known gap |
| Terminal launches (hand a run to a real console) | ❌ | ✅ | Depends on ShopLC's runner stack |
| Recipes (20 named skill+persona+mode bundles, lane `▸ advance` buttons) | ❌ | ✅ | Encodes ShopLC's specific delivery playbook; CCW's equivalent is `/do` + skills |
| Mechanical verbs (11 no-LLM jobs from a card) | ❌ | ✅ | Company workflow automation |
| Schedules (serve-is-the-clock cron) | ❌ | ✅ | Template defers recurring work to `/loop` in the harness |
| Git reconciliation (`shipped`, `sync-stages`, branch chips) | ❌ | ✅ | Assumes a production-branch model; template keeps git conventions in `project-layout` |
| Projexa (ticket system) integration | ❌ by design | ✅ (OAuth, sync, time entries, dupes) | The definition of company-specific; the template's zero-dependency rule excludes it |
| Trackers | 3 (questions/bugs/todos; gaps/critique reserved) | 5 (+ gaps, critique as TOML) | CCW keeps challenge outputs as markdown until wired |
| Work log | ✅ markdown daily files + `log-work` skill | ✅ TOML log + `day-evidence` (git-observed day length, human-accepted) | ShopLC's evidence flow is a nice honesty feature; CCW's summary mode covers the timesheet need |
| Chat sharing (local vs committed transcripts) | ❌ (local only, gitignored) | ✅ move-to-vault read-only replay | Worth porting later if transcripts need review |
| SSE resume with `seq` / static export | ✅ | ✅ | Parity (both re-read on `stream.reset`) |
| Custom one-shot backends from Settings (no code, no restart) | ❌ (config edit works) | ✅ UI-managed | Convenience layer |
| Test harness | ❌ (no JS/py test suite yet) | ✅ (`test_kanban.py` 3k+ lines; CSS-coverage JS test that fails on unstyled classes) | The most-worth-copying gap on CCW's side |

## Reading of the split

- **ShopLC is a company product**: Projexa, release packages, recipes, schedules, git reconciliation, and a people roster encode how that team ships. Porting those wholesale would violate this template's genericization rules (zero-dependency, config-driven, off-by-default).
- **CCW is the clean core**: same board/tracker/chat spine, rebuilt with the plugin seam and CLI-only TOML discipline, now at feature parity on the human-in-the-loop layer (approval gate, voice, models, themes).
- **Best next ports if wanted**: custom-theme builder (self-contained), chat sharing to the vault, worktree isolation (largest payoff — removes the "one run per repo" restriction), and above all a test suite in ShopLC's style.

## Links

- [[control-center-presentation]] (HTML, same folder) · `console/README.md` · `.claude/skills/console/SKILL.md`
