---
ticket: "T-003"
artifact: gap-analysis
status: open
created: "2026-09-06"
last_updated: "2026-09-06"
---

# Gap Analysis: T-003

**Sources:** [[T-003-requirements-draft]] · [[T-003-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 0   | 0     |
| Business rules  | 0  | 1  | 0   | 1     |
| Edge cases      | 0  | 1  | 0   | 1     |
| NFRs            | 0  | 0  | 1   | 1     |
| Data / entities | 0  | 0  | 0   | 0     |
| Integrations    | 0  | 1  | 0   | 1     |
| UX / UI         | 0  | 0  | 0   | 0     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 0  | 1   | 1     |
| **Total**       | **0** | **3** | **2** | **5** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-06 | — | Initial pass from `challenge-requirements` (gaps) | — |
| 2026-09-06 | G1-G5 | Closed via `requirements T-003 iterate` (see [[T-003-iteration-log]] iteration 1) | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | Single stakeholder (Sohail Ali), sign-off already recorded via the approved programme plan — no gap |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | `serve.log` (FR-6) has no stated rotation/retention policy — will grow unbounded across long-running sessions, unlike `host.log`'s explicit 1 MiB rotation (FR-3) | Add BR stating `serve.log` rotation is explicitly out of scope for T-003 (unbounded growth is an accepted, documented limitation, not silently unaddressed) — follow-up tracked as a todo, not new T-003 scope |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟡 | Second-launch race: `tauri-plugin-single-instance`'s callback (`tray::show_main`) could fire while the first instance is mid-`quitting` (`main.rs:135-145` `CloseRequested`/`Destroyed` handlers) — draft § 8 names this as an edge case but FR-4 has no AC covering it | Add an explicit AC to FR-4 (or a dedicated test note) — this is a builder/verifier-stage test to design, not a scope change; flagged now so it isn't dropped |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G3 | 🟢 | The template's Performance / Scalability / Availability / Usability NFR categories have no row (explicit N/A or otherwise) in § 5 | Add explicit N/A rows with one-line rationale each (single-user desktop app, no scale/latency targets apply to shell hygiene) so the freeze checklist's "every NFR" reads as deliberately-scoped, not silently skipped |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | `host.log`, `serve.log`, `.claude/launch.json` all have a canonical path + lifecycle note — no gap |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G5 | 🟡 | FR-8's CI flow (§ 4) never states how the Rust toolchain gets onto the 3 runners — relies on an unstated assumption that `windows-latest`/`ubuntu-latest`/`macos-latest` ship a compatible preinstalled Rust (GitHub's `runner-images` do preinstall a recent stable Rust, but no version is pinned against `rust-version = "1.77"` in `Cargo.toml`) | State explicitly in FR-8 that the job relies on the runner's preinstalled Rust (no pin) for this ticket, matching "keep it minimal" scope — pinning is a future hardening item, not required now since preinstalled stable Rust already exceeds `1.77` |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | No end-user UI surface changes in this ticket (shell startup behavior only) — no gap |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | No regulated/user data touched — no gap |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G4 | 🟢 | FR-7's installer scripts (`install-shortcut.ps1`, `install-launcher.sh`) don't state idempotent re-run behavior (shortcut/`.desktop` file already exists) | Add one line to FR-7: re-running overwrites the existing shortcut/`.desktop` file rather than erroring or duplicating — low risk, cheap to state now so the builder doesn't have to guess |

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements-draft]] · [[T-003-context-snapshot]] · [[T-003-gap-analysis]] · [[T-003-iteration-log]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
