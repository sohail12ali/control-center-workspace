# Harness Standards — always-on core

Canonical source for the 6 gates and the cross-cutting voice. This file is small by design so it can be loaded into every session. Full norms — evidence, communication, scope, token discipline, test policy, orchestration — live in [SKILL.md](SKILL.md).

## The 6 stages (run in order as gates)

1. **GROUND** — Never assume. Survey current state (code, prior artifacts) before drafting anything. Do not speculate: verify in the repo or ask a specific question.
2. **CLARIFY** — Ask every open question before producing output. Ambiguous or missing scope, acceptance criteria, or context blocks progress until resolved or explicitly deferred.
3. **CANONICAL** — Every fact lives in exactly one file. Search before creating. Point to canonical if found; declare new location in one sentence before creating.
4. **TEMPLATE** — Every file type derives from a template in `knowledge-center/artifacts/_template/`. Stop if no template exists.
5. **SIMPLIFY** — Write the minimum that works. No speculative abstraction, no extra indirection.
6. **VERIFY** — Every claim of "done" is backed by cited evidence (build, test, file:line) and every produced artifact links UP to its sources and is linked FROM its dependents.

**Always (cross-cutting): BE HONEST** — Report outcomes faithfully. If tests fail, say so with the output; if a step was skipped or deferred, say that; if you are uncertain or assuming, label it. State done-and-verified plainly without hedging, and never claim work that did not happen or pass. Surface contradictions and bad news early.

**Default voice:** Be **concise**. Add detail only when misunderstanding would be costly, when editing stakeholder-facing artifacts, or when the user asks for depth.
