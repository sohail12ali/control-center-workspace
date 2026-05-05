# Agents (Cursor)

Structured ticket work uses the same harness as Claude Code.

1. Read **`CURSOR.md`** for full layout, pipeline stages, and conventions.
2. Follow **`.cursor/rules/control-center-harness.mdc`** (always-on).
3. **Skills:** **`.claude/skills/<skill-name>/SKILL.md`**
4. **Routing / roles:** **`.claude/agents/*.md`** (same definitions for Claude Code and Cursor).

Delegate multi-stage tickets per **`.claude/agents/harness.md`**; in Cursor use the **Task** tool where harness describes delegating to another agent.
