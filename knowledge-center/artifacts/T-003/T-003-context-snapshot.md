---
ticket: "T-003"
artifact: context-snapshot
status: draft
created: "2026-09-06"
last_updated: "2026-09-06"
scope: codebase + history
---

# Context Snapshot: T-003

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-003 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Remove the stray console window the shell shows today, define a per-OS launch path, add a file logger + single-instance guard, stand up a 3-OS CI build, and close out T-001/T-002 — per the user-approved programme plan `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md § T-003 — Shell hygiene`.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Sidecar process lifecycle (spawn/probe/stop `kanban.py serve`) | `desktop/sidecar.py` | Python subprocess mgmt, Rust `sidecar::ensure`/`stop` | `spawn_serve` (`sidecar.py:114-145`) already sets `CREATE_NO_WINDOW\|CREATE_NEW_PROCESS_GROUP\|CREATE_BREAKAWAY_FROM_JOB` on Windows and `start_new_session` on POSIX — the pattern `procs.py` should mirror for the other six spawn sites | `desktop/sidecar.py:114-184` |
| Windows job-object lifetime binding | `desktop/src-tauri/src/job.rs` (referenced from `main.rs:108-116`) | Rust, `#[cfg(windows)]` | Existing pattern for platform-gated Rust code T-003's own `--console`/`AllocConsole` code should follow | `desktop/src-tauri/src/main.rs:1,108-116` |
| Tray menu skeleton + swallowed-error sites | `desktop/src-tauri/src/tray.rs` | Rust, Tauri tray | The exact `let _ =` call sites the logger's `log::warn!` calls attach to | `tray.rs:32-34,45,55,162-163` |
| CI Python-only pipeline | `.github/workflows/verify.yml` | GitHub Actions, 3 jobs (`tests`, `harness`, `cli`), all `ubuntu-latest` | Structure (matrix job, `actions/checkout` + `actions/setup-python`) to extend with a new `desktop` job rather than rewriting the file | `.github/workflows/verify.yml` |

### Existing patterns to reuse
- OS branching in Python via `os.name == "nt"` — `desktop/sidecar.py:131,152`.
- `#[cfg(windows)]` / `#[cfg(target_os = "macos")]` gating already used in `main.rs` (job-object setup, macOS titlebar) and should be the template for `--console`/`AllocConsole` gating — `desktop/src-tauri/src/main.rs:6-7,22-29,75-84`.
- Platform-strategy table's trait+registry pattern (Capture/Ocr/Tts/etc.) is **out of scope for T-003's features** but its cfg/registry *shape* — one OS-aware file (`procs.py`) that is a no-op on POSIX — is exactly what T-003 must produce, per programme plan § "Platform strategy" intro paragraph.

### Naming and architectural conventions in play
- Ticket artifact filenames `{T}-{artifact}.md`, flat, ending in `## Links` — `CLAUDE.md § Layout`.
- One fact, one file — decisions go to `T-003-decision-log.md` only, docs stay in `desktop/README.md` per programme plan § "Docs" table.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-001 | Native Tauri shell wrapping the console server | All ACs PASS, not closed | One line about the debug-subsystem defect must be added when closing (programme plan line 137) |
| T-002 | Tray remote (Show / New chat / Mute / Interrupt / Quit) | 9 PASS, 4 PENDING, 1 PARTIAL — native menu clicks aren't automatable | Needs one manual click-through recorded before `close-work` (programme plan line 137) |

### Relevant commits / PRs
- `8cb29e4` "Add a native Tauri shell and tray remote for the Delivery Console" (git log, most recent on `development`) — the T-001/T-002 shell this ticket hardens.

### Known incidents / regressions in this area
- Stray console window at shell launch, reported by the user this session; root-caused as cause A (debug-only `windows_subsystem`) via Phase 0 smoke, `T-003-verification.md § Ground truth (before)` rows 1, 3, 7.

## 4. External Systems in the Loop

- GitHub Actions (`.github/workflows/verify.yml`) — CI runner matrix extension.
- MSVC/xwin toolchain (`desktop/msvc-env.ps1`) — required to build/test the Rust host locally.

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- `tauri-plugin-single-instance` is a net-new dependency, unverified on the xwin/MSVC toolchain this machine uses — could fail to link; the plan itself calls this a descope-not-block condition.
- `desktop/sidecar.py:153` cannot import from the new `console/server/procs.py` (file must stay importable standalone) — needs its own inline flag constant, an intentional duplication.
- CI `desktop` job cannot be proven green until pushed; push is ASK-gated per harness rules, so the AC must separate "defined correctly" from "green on all 3 runners."

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. Convert to open questions via `clarify` if any would change the draft.

- `whisper-server`/mic-capture/OCR rows of the platform-strategy table are **not** confirmed or re-verified here — they belong to T-004–T-007 and are out of scope; listed only for the trait/registry pattern reference.
- `pytest.ini` has no `live` marker registered yet — not needed for T-003 (only relevant from T-005 onward per programme plan verification section); noted so a future ticket doesn't assume it already exists.

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-06 | Read | `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md` | Frozen programme intent for T-003 |
| 2026-09-06 | Read | `knowledge-center/artifacts/T-003/T-003-verification.md` | Phase 0 smoke ground truth |
| 2026-09-06 | Read | `desktop/src-tauri/src/main.rs` | Confirm cause A (debug-only windows_subsystem), cfg-gating patterns |
| 2026-09-06 | Read | `desktop/README.md` | Confirm `cargo run` = debug build guidance |
| 2026-09-06 | Read | `desktop/sidecar.py` | Confirm existing OS-aware spawn/kill pattern |
| 2026-09-06 | Read | `desktop/src-tauri/src/tray.rs` | Confirm swallowed `let _ =` sites for logger |
| 2026-09-06 | Read | `desktop/src-tauri/Cargo.toml`, `Cargo.lock` (grep `single-instance`, `name = "log"`) | Confirm `log` present, `single-instance` absent |
| 2026-09-06 | Read | `desktop/src-tauri/tauri.conf.json` | Confirm `identifier` for macOS bundle |
| 2026-09-06 | Read | `.github/workflows/verify.yml` | Confirm CI is Python/Ubuntu-only today |
| 2026-09-06 | Read | `pytest.ini` | Confirm test discovery roots, no `live` marker |
| 2026-09-06 | Read | `console/server/agent_session.py:360-419,495-519`, `agents.py:200-224`, `agent_tools.py:240-254`, `onboarding.py:60-79`, `worktrees.py:48-67` | Confirm the six `procs.py` call sites |
| 2026-09-06 | Bash `git log --oneline -5` | repo | Confirm T-001/T-002 landed in `8cb29e4` |
| 2026-09-06 | WebFetch | `raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md` | Confirm GH-hosted ubuntu runner preinstalls Rust 1.98.0/Cargo 1.98.0 (closes CR-4/G5 — enrich pass) |

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements-draft]] · [[T-003-context-snapshot]] · [[T-003-gap-analysis]] · [[T-003-iteration-log]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
