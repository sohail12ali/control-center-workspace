---
id: handoff-2026-10-06-pending-work
date: 2026-10-06
owner: Sohail Ali
type: handoff
status: current
---

# Handoff, 2026-10-06 — what is built, what is pending, how to resume

Written so a **fresh chat on another machine** can continue without this session. Everything the next chat needs is in the repository: the per-machine memory directory and the `.claude/plans/` file of this session do not sync, so their key content is copied below.

Session summary: three bodies of work ran in parallel on branch `development`:

1. **Mic Drop adoption** (voice features ported into the Assistant): [[T-031-summary]] .. [[T-035-summary]], decided in [[INV-2026-10-05-micdrop-adoption-dossier]].
2. **UI sync and layout**: [[T-036-summary]] (app and browser in sync) and [[T-037-summary]] (resizable layout).
3. **MAPS "AI OS" UI ideas** from a YouTube video: [[T-038-summary]] .. [[T-041-summary]], decided in [[INV-2026-10-06-maps-os-ui-adoption-dossier]].

Honesty note: everything below marked "verified" was checked by tests or in the in-app browser on **one Windows machine**. Nothing was verified on real hardware (a human voice, a second microphone), inside the **desktop app window**, on Linux or macOS, or in CI.

---

## 1. Resume on a new machine

```bash
git pull origin development
PYTHONUTF8=1 python console/kanban.py serve --host 127.0.0.1 --port 8790   # console UI + API
PYTHONUTF8=1 python console/kanban.py context T-032                         # a ticket digest (use PYTHONUTF8=1 on Windows)
PYTHONUTF8=1 python -m pytest -o addopts="" -q                              # expect 1 known failure, see section 5
```

- Python 3.14 is what was used; the console is standard library only. Nothing to `pip install` for the console.
- **Rust shell** (`desktop/`): in PowerShell run `. ./desktop/msvc-env.ps1` first or cargo cannot compile. Judge cargo by its **output** (`test result:` lines), not the shell's exit code. Redirect **inside** `cmd` (`cmd /c "cargo ... > file 2>&1"`); never pipe cargo through PowerShell `Out-File` (see section 6).
- **Models are not in git** (`desktop/stt/`, `desktop/tts/` and `desktop/src-tauri/target` are ignored). On the new machine, download them with the new Settings model manager (T-031), or `desktop/get-whisper.ps1` / `desktop/get-piper.ps1` (Windows only; Linux and macOS engine install is manual, follow-up TD-1 in [[T-031-summary]]).
- **Quit the desktop app from its tray icon (right-click, Quit) before building.** Closing the window only hides it and the running exe locks `target/debug/delivery-console-desktop.exe`.
- Machine-local state that will be missing and is rebuilt on first use: `console/.cache/` (shared UI preferences in `prefs.json`, assistant `settings.json`, job records, `bridge.json`).
- The console on `:8790` serves `console/static` from disk with `Cache-Control: no-cache`, so UI edits show on reload; **Python changes need a server restart** (the new `/api/prefs` and `ui_version` only exist on a server started after T-036).

---

## 2. Ticket status (end of session)

Lane per `ticket.toml`. "Built" = code in the tree; "verified" = a test or browser observation is cited in that ticket's verification file.

| Ticket | Lane | Built | Verified | Not verified / pending |
|---|---|---|---|---|
| [[T-031-summary]] voice assets and devices | in-progress | 36 of 39 plan tasks plus the real-shell run | 68 of 73 acceptance criteria (62 PASS, 4 PASS-HL, 2 PASS-UI), 0 fail; Rust 310 tests, Python 2877 pass | HW-1..HW-8 need a human (preview audibility, two inputs, unplug, real voice on the level bar, tone); 9 UI items; CI, Linux, macOS; stale claim `builder`; todos TD-1..TD-11 |
| [[T-032-summary]] pause-tolerant endpointing, junk filter, wav-replay seam | open | nothing | analysis done; **requirements frozen** (FR-1..20, AC-1..15); decisions D-1..D-9; 14-task plan | its harness died while planning; summary text is stale ("GROUND not started") and `progress.md` is nearly empty; no build task started; plan critique not confirmed |
| [[T-033-summary]] turn loop, hold-to-talk, mute, summary, voice commands | open | nothing | | not started |
| [[T-034-summary]] voice onboarding, doctor, tray submenus | open | nothing | | not started; waits on T-031 and the onboarding wizard files landing |
| [[T-035-summary]] cloud STT, language, echo-cancelled barge-in | open | nothing | | not started; a spike |
| [[T-036-summary]] app and browser in sync | verify | all 23 tasks | 49 of 81 criteria PASS, 0 fail; **browser (in-app) confirmed**: version change reloads the page by itself, an unsent draft blocks the reload and shows the notice, layout stored on the server | 31 criteria not verified in a browser; **the desktop app window was never tested**; 1 PARTIAL (AC-62, caused by the unrelated `.ob-count` failure); stale claim `builder-t036` |
| [[T-037-summary]] resizable layout | verify | tasks 01..19, simplify, the lane aria fix and the F-8 dock fix | 31 of 65 criteria PASS (source/static), 0 fail; browser-observed: real drag, keyboard, persistence, 900/901 boundary, no overflow at 400 px, Vault handle, collapsible sections, docked ticket panel, Reset layout, the F-8 resize fix (via a dispatched `resize` event) | 34 criteria "not verified in a browser" (9 partially covered); task T-037-20 unticked; touch drag, print preview, real card drop, Vault viewer handle, the app window; Q1 open |
| [[T-038-summary]] brain views on the Vault | open (reset to GROUND) | nothing | | **re-scoped onto the Vault**; its old plan is superseded, do not build it |
| [[T-039-summary]] "Needs you" panel and panel freshness | open | nothing | | not started |
| [[T-040-summary]] routines board and Run now | open | nothing | | not started; same Overview files as T-039 |
| [[T-041-summary]] nightly link checker | open | nothing | | not started; backend only |

Older tickets still open: [[T-019-summary]] (hands-free, verify, two criteria wait for a human voice) and [[T-015-summary]] (verify, several manual checks), [[T-022-summary]], [[T-023-summary]] with [[T-025-summary]] .. [[T-028-summary]], and [[T-030-summary]]. T-020 and T-021 are lane `done`, but their onboarding-wizard files were still uncommitted in the working tree and are included in the commit that carries this note.

---

## 3. Decisions the user still owes (with the recommendation)

1. **T-037 Q1**: on wide screens should the docked ticket panel **replace** the old overlay, or be an **opt-in toggle**? Built as replace. A toggle costs about 1.5 h. Recommendation: keep replace unless it annoys in daily use.
2. **T-036**: (a) add a request timeout to preference saves (`C.post` has none; a hung save stalls later saves until the page closes; CR-38) — recommend yes, small; (b) AC-41 wording: frozen text says "no default-theme flash", the plan accepts a recorded flash on the static shell — decide with a real look; (c) Q1..Q5 are at recorded defaults (live pickup of theme and hidden tabs on, sidecar check built, 30 s idle window, delete the local copy after import, all 16 keys shared).
3. **T-031**: (a) raise the page's 4 s mic-test watch to 6 s (IC-1) — recommend yes; (b) AC-14 says the first retry delay is 0.5 s but the loop waits 1 s (IC-2) — amend the text or change the loop; (c) confirm D-18, the one-line `desktop/get-whisper.ps1:103` fix that the frozen text said would not change.
4. **T-038**: our area and layer mapping for the workspace graph (the analyst proposes, the user decides); whether the Vault joins the static export.
5. T-040: whether to unpark a harmless schedule so the routines board is not empty.

---

## 4. Pending work, in the suggested order

Run **at most two pipelines at once**. Three at once consumed about 78% of a 5-hour limit in roughly three hours.

1. **Resume T-032** (the largest voice win; build the wav-replay seam first). Its artifacts are the state: read `T-032-requirements.md`, `T-032-decision-log.md`, `T-032-plan.md` (14 tasks, 01..14), then confirm whether the plan was challenged before building. Resume by launching a harness for T-032 with the brief in section 7.
2. **T-039** then **T-040** (both edit the Overview files; do not run them together), and **T-041** (independent, backend only; can run beside either).
3. **T-038** brain views on the Vault: run the analyst first (requirements are an empty template). It edits `vault.js` and `styles.css`, so do not run it beside another ticket touching them.
4. **T-033**, **T-034** (after T-031 lands and the onboarding wizard files are settled), **T-035**.
5. **Finish and close what is built:** the human-only checks for T-031, T-036 and T-037 (all `needs_human`); release the stale claims with the `claim-release` verb; then `close-work` per ticket.
6. **Follow-ups logged but not ticketed:** TD-1 engine downloads for Linux and macOS; T-031 todos TD-2..TD-11 (engine robustness, hands-free goes deaf if a mic vanishes mid-session, threads per refresh); bug D-1 in `console/static/palette.js:103` (`app.drawer(...)` called as a function, logged on T-037); no request-body size cap in `console/server/httpd.py:190` (a 5 MB POST was refused with 400, the server stayed up; suggest a small ticket); the `test_stylesheet.py` failure `onboarding-wizard.js: .ob-count` (a missing CSS rule from the onboarding work, not fixed anywhere).
7. **Video material:** `scratch/` keeps only the notes (transcript, frames, scripts). The video, clip, PDF and its extracted page text are deliberately **not** in git (third-party material); re-extract from the source if needed.

---

## 5. Test baseline to compare against

- `PYTHONUTF8=1 python -m pytest -o addopts="" -q`: **1 failed, about 2877 passed, 1 skipped.** The one failure is `console/tests/test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`). Any other red test is new.
- Rust (`desktop/src-tauri`): `cargo test -- --test-threads=1` gave 310 passed at the last verification (the real-engine fixture test needs `desktop/stt/ggml-base.en.bin`; without it that test skips loudly). Two hardware-gated tests briefly open the default microphone (nothing is recorded).
- `desktop/tests`: 41 passed. `harness lint`: 39 skills, 7 agents, 0 errors, 20 warnings.

---

## 6. Rules and lessons that cost time this session (carry them over)

- **Agents:** the `harness` agent has **no Bash**. It must delegate every shell command to a builder, verifier or fixer launched with the Agent tool. One run stopped for lacking a shell and wasted a run; say so explicitly in its brief. A harness that dies leaves artifacts but no report: re-launch a fresh one that rebuilds state from the ticket folder.
- **Never trust a subagent's "done"** (memory `subagent-status-not-evidence`): check the tree and re-run the tests yourself. Several results here are builder-reported only and the ticket verification files say which.
- **Leaked child hangs the pipe:** a test that panics after the speech engine starts orphans `whisper-server.exe`; it inherits the stdout pipe of `cmd /c cargo | Out-File` and the wrapper never exits. Check `whisper-server.exe` parents before and after every cargo run, redirect inside `cmd`, stop only verified orphans (never the app's own engine, whose parent is `delivery-console-desktop.exe`). Never `grep -r` into `desktop/src-tauri/target`.
- **Do not touch the user's running app or its debug port 9333**: an earlier UI run navigated the app's HUD webview to a throwaway page. Test in your own browser on a random port.
- **Shared tree etiquette:** several tickets edit the same files (`settings.js`, `styles.css`, `app.js`, `core.js`). Re-read a file right before each edit, keep edits surgical, preserve CRLF or LF as found (one builder flipped `piper.rs` to LF), and never anchor an Edit on the bare text `## Links` (it fused paragraphs in two progress files).
- **Usage:** the 5-hour limit is the constraint (plan Team; extra usage is enabled and has $3.16 spent, so exhausting the limit may bill). The pattern used: a recurring check that holds all pipelines at 90%.
- **Browser testing caveats:** the in-app browser's viewport emulation does **not** fire `resize` or media-query change events, so dispatch `window resize` by script after each size change; a fresh navigation after a server restart needs the server up first; the pane may report a 0 by 0 viewport until `resize_window` is called.
- **"Reset all preferences"** (Settings, Stored preferences) now clears the **shared server-side** preferences used by the desktop app and every browser. Do not click it to test; use a throwaway console on another port.
- **Skipped on purpose:** real card drops on the board (they would move a real ticket), "Reset all preferences", anything that writes the user's real `console/.cache/assistant/settings.json`.

---

## 7. Agent brief template that worked (condense and reuse)

Start a pipeline with the `harness` agent (named, for example `harness-t0NN`) and include:

- Ticket id and title, the files to read first (`knowledge-center/artifacts/T-0NN/T-0NN-summary.md` plus the relevant dossier), and the scope.
- "You have no Bash; delegate every shell command to specialists; stop only for a genuine CLARIFY question."
- Hard constraints: no commit or push; never revert, stash, checkout, reformat or `git add` other tickets' hunks; re-Read before each Edit; preserve line endings; no new dependency without `tech-select(confirm-existing)`; ES5 IIFE style for `console/static/*.js` (no `=>`, no statement-leading `let/const`, tests enforce it); CSS classes used from JS must exist in `styles.css`; never append at the end of `styles.css`; cargo hygiene and orphan checks (section 6); never use port 9333.
- "Report exact test counts, say what is verified versus not verified (hardware, human, browser, app window, CI), do not claim browser behaviour you did not observe; stop after `close-check`; do not run `close-work`."
- "If I message you to hold, finish only the task in flight, write progress.md and stop."

Roles and order are in `CLAUDE.md`: analyst (GROUND and CLARIFY), planner (CANONICAL), builder (TEMPLATE and SIMPLIFY), verifier (VERIFY), fixer (any), deployer (after close-work, ASK-gated).

---

## 8. Ready-to-paste first message for the new chat

> Read `knowledge-center/wiki/handoff-2026-10-06-pending-work.md` first, then the two dossiers it links (`INV-2026-10-05-micdrop-adoption` and `INV-2026-10-06-maps-os-ui-adoption`). I want to make a new plan for the pending work in its section 4. Check the repo state first (`git status`, `git log -5`, the console `ticket list`), summarise what changed since the note, then ask me the open decisions in its section 3 before launching any agents. Run at most two pipelines at once and hold at 90% of the 5-hour usage limit.

## Links
- Dossiers: [[INV-2026-10-05-micdrop-adoption-dossier]] · [[INV-2026-10-06-maps-os-ui-adoption-dossier]]
- Tickets: [[T-031-summary]] · [[T-032-summary]] · [[T-033-summary]] · [[T-034-summary]] · [[T-035-summary]] · [[T-036-summary]] · [[T-037-summary]] · [[T-038-summary]] · [[T-039-summary]] · [[T-040-summary]] · [[T-041-summary]]
- Older: [[T-015-summary]] · [[T-019-summary]] · [[T-022-summary]] · [[T-023-summary]] · [[T-025-summary]] · [[T-026-summary]] · [[T-027-summary]] · [[T-028-summary]] · [[T-030-summary]]
