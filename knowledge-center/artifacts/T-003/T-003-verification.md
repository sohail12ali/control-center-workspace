---
ticket: "T-003"
artifact: verification
---

# Verification: T-003

## Ground truth (before) — Phase 0 smoke 2026-09-06

Debug build `desktop/src-tauri/target/debug/delivery-console-desktop.exe` (built 2026-09-05), host pid 21556. Scripts: `ticket-scripts/probe-processes.ps1`, `ticket-scripts/list-console-windows.ps1`.

| # | Check | Observed |
|---|-------|----------|
| 1 | PE subsystem of the debug exe (`e_lfanew`+4+20+68) | **3 = CONSOLE** |
| 2 | Port 8790 before launch | closed |
| 3 | Launch → visible console-class windows | **1** × `CASCADIA_HOSTING_WINDOW_CLASS` (WindowsTerminal.exe pid 22348, OpenConsole pid 35540) titled with the exe path — the stray terminal, hosting the shell process itself |
| 4 | `GET /api/config` | 200, title "Noble Delivery Console"; serve pid 6092 with a *hidden* console (conhost 20856, `CREATE_NO_WINDOW`) |
| 5 | Claude chat via `POST /api/agents/chats` (`plan`, "say hi") | claude.exe 14492 + hook python children under serve; **no new visible console window** |
| 6 | Cursor chat (`ask`) | `cmd.exe → powershell.exe → node.exe` chain under serve; **no new visible console window** |
| 7 | Close the stray terminal | Killing its OpenConsole session detached the host without terminating it; a WM_CLOSE click-repro was not exercised (window already gone). User report stands on CTRL_CLOSE_EVENT semantics; verify by hand on the release build instead |
| 8 | Quit via tray | not exercised (no automated menu click — same limit as T-002) |
| 9 | `python -m pytest` | **758 passed** in 46.57 s |
| 10 | `cargo build` | pre-existing debug build used; release not yet built |

Conclusion: cause A (console-subsystem debug exe) is **confirmed live**. Cause B (agent spawns without `CREATE_NO_WINDOW`) **did not reproduce** — children inherit the server's hidden console — so the `procs.py` flags are defensive hygiene, not a fix for an observed defect. Counting `conhost.exe` is not a valid metric (hidden consoles have one too); count visible console-class windows.

## Acceptance Criteria

Verified fresh by `@verifier` 2026-09-06, re-running the automated suite and re-doing the live smoke against the release exe (not just trusting the builder's numbers). Release exe: `desktop/src-tauri/target/release/delivery-console-desktop.exe` (rebuilt during this pass by `cargo test`; `test_pe_subsystem.py` re-confirms subsystem 2).

| # | Criterion (FR) | Status | Evidence |
|---|-----------------|--------|----------|
| FR-1 | Unconditional GUI subsystem, zero visible console at launch (debug + release) | PASS | `test_pe_subsystem.py` (1 passed) reads subsystem `2` off the built exe. Live smoke via `cmd //c start` (same mechanism the ticket specifies): `list-console-windows.ps1` → zero visible console-class windows; `probe-processes.ps1` → `conhost in host tree: 0`, `api/config ok`. |
| FR-2 | `--console`/`DESKTOP_CONSOLE=1` escape hatch | PASS (Windows smoke) / PENDING (cross-OS compile-clean) | Live smoke: `cmd //c start ... --console` → `list-console-windows.ps1` shows `ConsoleWindowClass \| pid=22948`, confirming a real visible console appears only when requested. `main.rs:69-88` `#[cfg(windows)]`-gates `maybe_attach_console`; the non-Windows branch is a documented no-op stub — compiles by inspection, but "compiles clean on ubuntu-latest/macos-latest CI" is PENDING an ASK-gated push (no Linux/macOS hardware here). |
| FR-3 | Host file logger: rotation + UTC unit tests; lifecycle lines in `host.log` | PASS | `cargo test --manifest-path desktop/src-tauri/Cargo.toml` (after `. .\desktop\msvc-env.ps1`): 3/3 (`utc_formatting_matches_known_instants`, `rotates_past_the_limit_with_no_data_loss`, `a_second_rotation_replaces_the_previous_dot_one`). Live: `console/.cache/desktop/host.log` contains real `startup`/`ensure`/`job`/`window`/`tray`/`close`/`single-instance` lines from every launch this session, correct ISO-UTC timestamps. The specific `tray.rs` `warn_on_err` sites (show_main/eval_tray/request_quit/desktop-session listener) are code-reviewed only — reachable solely via tray-menu clicks, which this pass's UIA attempt (§ below) could not drive; **code verified, not live-exercised**. |
| FR-4 | Single-instance guard: second launch = one tray icon; descope-safe | PASS | Live smoke: launched release exe via `cmd //c start` (pid 5128), then a second `Start-Process` while the first ran — `Get-Process delivery-console-desktop` showed exactly one process throughout; `host.log` logged `single-instance: second launch detected, focusing the existing window` at the matching timestamp. Repeated later in the session (second occurrence at 06:50:38 after a close-to-tray). Quit-race (callback firing mid-shutdown) **not deliberately forced** this pass either — no crash observed across ~6 launch/quit/kill cycles, but that specific race remains code-verified/not adversarially exercised, same caveat the builder recorded. |
| FR-5 | Defensive no-window hygiene, 6 Python spawn sites, wording states hygiene not fix | PASS | `console/tests/test_procs.py` — 16/16 passed. Confirmed by direct read of all 6 call sites: `agent_session.py:376` (`creationflags=procs.no_window_flags(...)`), `agent_session.py:514` (`**procs.popen_kwargs()`), `agents.py:218`, `agent_tools.py:252` (kept `shell=True`+`stdin=DEVNULL`), `onboarding.py:73`, `worktrees.py:61` — all import `from . import procs` and apply it. `procs.py` docstring + `T-003-decision-log.md` § "Cause B scope" both state hygiene-not-fix; no "fixed" claim found anywhere in code/docs. |
| FR-6 | `sidecar.py` log capture + standalone import safety | PASS | `desktop/tests/test_sidecar.py` — 14/14 passed. Direct read: `sidecar.py:31` keeps its own inline `CREATE_NO_WINDOW = 0x08000000` (no `from procs import` / `import procs` anywhere in the file — grep-confirmed); `_serve_log_handle` redirects stdout/stderr to `console/.cache/desktop/serve.log` (append), falls back to `DEVNULL` only if the dir can't be created. Live: `serve.log` present and non-empty after every launch this session. |
| FR-7 | Per-OS launch path | PARTIAL | Windows: `launch.ps1`/`install-shortcut.ps1` code-reviewed; the real Start-Menu/Desktop/Startup install is correctly **not run** by anyone (writes outside the repo, ASK-gated) — left for the user. macOS/Linux: `desktop/tests/test_install_launcher.py` — 4/4 passed (build-only, explicitly no hardware smoke claimed, matches scope). `.claude/launch.json` reviewed, valid JSON, both entries resolve. |
| FR-8 | Cross-platform CI: 3-OS `desktop` job, correct matrix/steps, apt scope, no Rust pin | PASS (defined) / PENDING (proven green) | `yaml.safe_load('.github/workflows/verify.yml')` this pass: matrix = `['windows-latest','ubuntu-latest','macos-latest']`; steps = install deps → (Linux-only) apt prereqs → `cargo build --release` → `cargo test` → `pytest desktop/tests`; existing jobs `tests`/`harness`/`cli` untouched (4 job names total, none overlapping). "Green on all 3 runners" stays PENDING — no push performed this pass (ASK-gated), never claimed as PASS. |
| FR-9 | Close T-001 | PASS | See § T-001/T-002 closure below — `close-work T-001` run this pass; lane `done`, artifact-map row moved to Completed. |
| FR-10 | Close T-002 | PENDING | Not closed this pass by design — see § T-001/T-002 closure below. Dated "Manual smoke" section added to `T-002-verification.md`; PENDING rows correctly labeled `PENDING — user click-through`, not silently dropped or faked. |

## Fresh Test Evidence (this verifier pass, 2026-09-06)

| Command | Result |
|---------|--------|
| `python -m pytest` (repo root, junit-xml) | **783 passed, 0 failed, 0 errors** in 53.46s (`--junit-xml` counted; `-q` run separately hit one intermittent Windows `os.replace` sharing-violation flake in `console/tests/test_trackers.py::test_status_filter` on one run, same root cause as the pre-existing `test_tomlio.py` flake noted by the builder — **not confined to that one test as literally stated**; confirmed pre-existing and unrelated to T-003's diff since `tomlio.py`/`trackers.py` are untouched by this session's changes; a deterministic rerun (`-p no:randomly`) and a `--junit-xml` run both came back 783/783 clean) |
| `cargo test --manifest-path desktop/src-tauri/Cargo.toml` (after `. .\desktop\msvc-env.ps1`) | **3 passed; 0 failed** (logger rotation ×2 + UTC formatting) |
| `python -m pytest console/tests/test_procs.py desktop/tests/test_sidecar.py desktop/tests/test_install_launcher.py desktop/tests/test_pe_subsystem.py -v` | **35 passed** |
| Release exe exists | `desktop/src-tauri/target/release/delivery-console-desktop.exe` (rebuilt by `cargo test` this pass; 10.7 MB) |
| Live smoke: default launch (`cmd //c start`) | zero visible console windows (`list-console-windows.ps1`); `conhost in host tree: 0`; `api/config ok` |
| Live smoke: `--console` launch (`cmd //c start ... --console`) | 1 visible `ConsoleWindowClass` window |
| Live smoke: close-to-tray | `CloseMainWindow()` → process alive, window hidden (title reverts to internal id), `api/config` still 200 |
| Live smoke: second launch | exactly one host process throughout; `host.log` single-instance line present at the matching timestamp; window re-shown (title back to "Delivery Console") |
| Live smoke: force-kill | `Stop-Process -Force` on host → owned `serve` pid (job-object member) disappears within 2s; `api/config` connection refused; no LISTENING socket left on 8790 |
| UIA tray-menu drive attempt | **Attempted, failed to locate a drivable element** — see § UIA attempt below |

## Edge Cases Probed
- Windows-only code paths (`AttachConsole`/`AllocConsole`, job object) are `#[cfg(windows)]`-scoped — confirmed by direct read of `main.rs`; cross-OS compile-clean is a CI claim, not locally provable (no Linux/macOS hardware).
- `procs.py` no-op on POSIX — confirmed by reading `no_window_flags`/`popen_kwargs` (both branch on `os.name == "nt"`); not re-run on a POSIX machine this pass (Windows-only environment), same limitation as the builder's own pass.
- Single-instance race during quit — not deliberately forced; no crash across ~6 launch/quit/kill cycles this session.
- `host.log` rotation mid-write — unit-tested (`cargo test`), not reproduced with a real 1 MiB file this pass (impractical to force live).
- `sidecar.py` standalone-import safety — grep-confirmed no `procs` import; `test_sidecar.py` passes run in isolation.
- Force-kill cascade — exercised live this pass (see Fresh Test Evidence), confirms job-object teardown still works after the `simplify` pass touched `main.rs`.

## UIA attempt (T-002, tray-menu automation)

One bounded UIA drive attempted against the just-verified release exe (assemblies `UIAutomationClient`/`UIAutomationTypes` load fine on this machine). Searched the full UI Automation tree (`TreeScope.Descendants` from the desktop root) for an element named "Delivery Console" other than the main window/title bar, both before and after trying to invoke a "Show hidden icons" chevron (not found — this machine's taskbar exposes no such element via UIA either). Result: only the main Tauri window and its title bar matched; **no tray-icon-sized UIA element was found at all**, so no right-click/context-menu drive was possible. This is a stronger negative than T-002's own prior finding (which at least found *a* notify-icon element via UIA and failed only at the right-click/menu step) — confirms the same class of limitation from a different angle. Full script: `uia-tray-attempt.ps1` (scratchpad, not committed — reusable if a future pass wants to retry with a different approach, e.g. `IUIAutomation` COM directly or a taskbar-specific accessibility bridge).

## T-001/T-002 closure (this pass)

- **T-001**: all 8 ACs already PASS ([[T-001-verification]]). Added a line noting the debug-subsystem stray-console defect is now tracked/fixed under T-003 ([[T-001-verification]] § Notes). Ran `close-work T-001` — lane `done`, artifact-map row moved to Completed (confirmed below).
- **T-002**: 9 PASS / 4 PENDING / 1 PARTIAL, native tray-menu clicks are not automatable (confirmed again this pass, see § UIA attempt). Per the ticket's explicit instruction, **`close-work T-002` was NOT run**. Added a dated "Manual smoke" checklist header to [[T-002-verification]] for the user to click through by hand against the release exe; the 4 PENDING rows are labeled `PENDING — user click-through`, not marked PASS and not silently dropped. T-002 stays in the `verify` lane.

## Notes
- Reconcile (this pass): `T-003` ticket lane was still `open` in `ticket.toml`/`artifact-map.md` despite build being complete and this VERIFY pass underway — moved to `verify` via `python console/kanban.py ticket move T-003 verify` (TOML mutated only through the CLI, per project rule) and `artifact-map.md`'s row + `T-003-summary.md`'s Status/Stage/Current-State synced to match (plain markdown, hand-edited — not a TOML tracker). Logged as an auto-fix, not a semantic change.
- `validate-artifacts` (links) found one dangling wikilink: `T-003-task-breakdown.md`'s `## Links` block referenced `[[T-003-effort-forecast]]`, a file that was never produced (no scope drift triggered `estimate(mode=forecast)` — the ticket stayed under its estimate). Removed the dangling reference; no other broken links found across T-001/T-002/T-003's full wikilink sets (grep-verified).
- No TOML file was hand-edited. Nothing was committed or pushed this pass.

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]

