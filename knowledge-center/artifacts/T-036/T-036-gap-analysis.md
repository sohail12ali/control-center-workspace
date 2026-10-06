---
ticket: "T-036"
artifact: gap-analysis
status: closed
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Gap Analysis: T-036

**Sources:** [[T-036-requirements-draft]] · [[T-036-context-snapshot]]

**Severity rule used in this pass (stated because it is a judgement):** 🔴 = changes scope, entity shape, an FR's behaviour or an NFR target and is **not** already settled by [[T-036-summary]] or [[T-036-decision-log]]. 🟡 = changes an acceptance criterion or the test plan. 🟢 = minor. The harness instruction for this ticket is to resolve every 🔴 with a reasonable default recorded in the decision log and to open a question only when the user must decide; Q1-Q5 (all low/medium, none blocking) were opened at draft time for the assumptions the decision log already marked "confirm at review".

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 2   | 2     |
| Business rules  | 1  | 2  | 0   | 3     |
| Edge cases      | 3  | 10 | 1   | 14    |
| NFRs            | 0  | 2  | 0   | 2     |
| Data / entities | 0  | 2  | 0   | 2     |
| Integrations    | 0  | 1  | 1   | 2     |
| UX / UI         | 0  | 2  | 1   | 3     |
| Compliance      | 0  | 1  | 1   | 2     |
| Cross-cutting   | 0  | 2  | 1   | 3     |
| **Total**       | **4** | **22** | **7** | **33** |

**State after pass 4 (final): 0 🔴 open.** The 4 🔴 raised in pass 1 (G3, G6, G7, G8) were closed in iteration 1 by defaults D-13, D-15, D-16; none needed the user. G31-G33 were found in pass 2 and closed in iteration 2. Accepted (not closed by a requirement change): G1, G10, G11, G12, G13, G19, G25, G26, G28, G29. Interaction conflict: 1 (§9 row "tab script load order"), closed by D-11. Findings: [[T-036-critique-report]] CR-1..CR-25.

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-05 | — | Initial pass from `challenge-requirements` (gaps + red-team + interactions), pass 1 | analyst |
| 2026-10-05 | G3, G4 | Closed: FR-6 `rejected` bucket and toasts, FR-4 response shape, BR-16, AC-75, AC-76; D-16 (iteration 1) | analyst |
| 2026-10-05 | G5 | Closed: FR-2, BR-15, AC-12; D-20 (iteration 1) | analyst |
| 2026-10-05 | G6 | Closed: FR-2 version rules, BR-5, AC-68; D-13 (iteration 1) | analyst |
| 2026-10-05 | G7, G8 | Closed: FR-5 write-failure and keepalive rules, AC-71, AC-72, AC-74; D-15 (iteration 1); the 64 KiB figure is recalled, not re-verified here, covered by a [BROWSER] check | analyst |
| 2026-10-05 | G9, G33 | Closed: FR-6 `!==` and absent `prefs_rev` ignored, AC-53 (iterations 1, 2) | analyst |
| 2026-10-05 | G14, G22 | Closed: FR-6, AC-77; D-18 (iteration 1) | analyst |
| 2026-10-05 | G15 | Closed: AC-18 pass condition; A-6 stays labelled unverified (iteration 1) | analyst |
| 2026-10-05 | G16 | Closed: FR-1 text, AC-67; D-13 (iteration 1) | analyst |
| 2026-10-05 | G17 | Closed by `requirements enrich`: NFR-4..NFR-6 proposed numbers marked ⚠ [unrealistic?], AC-65, AC-66 | analyst |
| 2026-10-05 | G18 | Closed: FR-5 hydration bound, NFR-6, AC-73; D-17 (iteration 1) | analyst |
| 2026-10-05 | G20, G27 | Closed: AC-32; D-19 (iteration 1) | analyst |
| 2026-10-05 | G21 | Closed: AC-1 and AC-58 pin the old keys and `is_up` | analyst |
| 2026-10-05 | G23, G24 | Closed: FR-2 notice definition, AC-10, AC-69; FR-6 toast copy, AC-76 (iterations 1, 2) | analyst |
| 2026-10-05 | G2, G30 | Closed: draft §3 Out of scope; NFR-9 and the wizard-comment SHOULD (iteration 1) | analyst |
| 2026-10-05 | G31, G32 | Closed: FR-4/FR-6, AC-25, AC-46, AC-79, AC-80; D-21 (iteration 2) | analyst |
| 2026-10-05 | G1, G10, G11, G12, G13, G19, G25, G26, G28, G29 | Accepted with rationale (Q5/Q4 open and non-blocking where noted): A-5, edge-case list, BR-4, NFR-7, draft §13; G28 rollback note goes in `T-036-release.md` | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟢 | Devices that reach the console over a network (phone, laptop via tailnet, `httpd.py:203-240`) will share pixel `layout`, `chatListHidden` and `voice` with the desktop. | Accepted risk A-5 / BR-11; Q5 asks whether any key should stay per-device (default none). |
| G2 | 🟢 | The HUD overlay (`hud.html:141`) is a second long-lived page with no heartbeat; nothing says it stays stale. | Already Out of scope in the draft §3; keep the sentence so it is not assumed covered. |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G3 | 🔴 | FR-6 import returns only `imported` and `skipped`; a legacy key with an invalid name, an over-cap value (32 KB / 128 keys / 256 KB file) or unparsable JSON has no defined outcome, and "delete local keys after the server acknowledges" would lose it silently. | **Closed, iteration 1.** Add a third bucket `rejected:[{key,reason}]` to the import response; the client toasts rejected keys with the reason, then deletes them (they cannot live on the server); a local value that does not parse is treated as absent (as `C.prefs.get` does today, `core.js:449-450`) and deleted without a toast. Decision D-16. |
| G4 | 🟡 | When the import window is closed (after Reset) the client deletes its old keys without importing and without telling anyone: values vanish silently. | One info toast: "Old settings in this browser were discarded because preferences were reset." Decision D-16. |
| G5 | 🟡 | "Reload now" while the page holds typed text: the draft does not say whether an explicit click overrides the busy rules. | An explicit click is consent and reloads at once; the notice text says what typed text will be lost only when the page is busy. Decision D-20 (accepted behaviour). |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G6 | 🔴 | BR-5 says a missing `ui_version` never triggers a reload, but FR-5's recovery path (new JS served by a server not yet restarted → local mode → server restarts with the new routes → page should move to server mode) needs a page whose boot response had no `ui_version` to reload once a later response has one. As written the page stays in local mode until someone relaunches it. | **Closed, iteration 1.** Rule: boot version absent + later version present = "changed" (reload when idle); version present → absent (downgrade) is ignored. Stable afterwards, so no loop. Decision D-13. |
| G7 | 🔴 | FR-5 says a failed write "stays in memory for that page lifetime" but not whether it is retried, and FR-6 blocks `refresh()` while deltas are pending, so one failed flush can freeze live pickup forever; a 400 (validation) retried forever is worse. | **Closed, iteration 1.** Retry pending deltas on the next `set`, on the connection coming back (`C.onConnection`) and on each heartbeat that succeeds; a 400 drops the batch once with a toast; the client mirrors the key regex and the 32 KB cap and keeps an invalid or oversized value in memory only (not queued), toasting once per key per session. Server validation stays authoritative and all-or-nothing. Decision D-15. |
| G8 | 🔴 | `keepalive` fetch bodies share a 64 KiB budget in the Fetch standard (recalled, not re-verified in this session: web fetches of the spec did not return the step); the store allows 32 KB × 128 keys, so a pending delta can exceed it and the flush on page hide would fail as a network error. | **Closed, iteration 1.** Send the keepalive flush only when the serialised body is ≤ 60,000 bytes; otherwise send one request per key; a key whose value alone exceeds that goes without `keepalive` (best effort, may be lost on teardown). Realistic prefs are well under 2 KB. Decision D-15; [BROWSER] check. |
| G9 | 🟡 | `rev` is an integer reset to 0 if the file is deleted; a client comparing `>` would never refresh. | Clients compare `rev` for inequality only (FR-6 text); AC checks the comparison form. |
| G10 | 🟡 | Object-valued keys (`panelOpen`, `voice`, `modelByBackend`, `layout`) are last-writer-wins as a whole: two clients toggling different panels within one heartbeat lose one change. | Accepted: mitigated by `refresh()` within 15 s; recorded in the edge-case list. |
| G11 | 🟡 | Server unreachable at boot (local mode), the user changes a pref, the server returns during the same page lifetime: the page switches to server mode and the locally written value is imported as "skipped" if the server already had that key. | Accepted: the skipped toast names the key and value, so nothing is lost silently (AC-50). |
| G12 | 🟡 | The store's lock is a `threading.Lock`, process-local; two servers on one checkout (different ports) could interleave read-modify-write and collide on `rev`. | Accepted and documented: one server per checkout is the supported setup (the sidecar attaches to one port, `sidecar.py:273-292`); each write is atomic so the file never corrupts. |
| G13 | 🟡 | A non-heartbeat request in flight (POST via `C.post`, not counted by `C.inflightCount`, `core.js:140`) when the reload fires is aborted by navigation; the server still completes it but the page loses the result. | Accepted: the idle window makes this rare, the server finishes the write, the page re-reads state on boot; not added to the busy list. |
| G14 | 🟡 | Live pickup of `hiddenTabs` may hide the tab currently shown. | The active tab's content stays until the person navigates; `rebuildNav` only rebuilds the nav buttons (`app.js:74-106`). Added to edge cases. |
| G15 | 🟡 | A Tauri-hidden window may have throttled or frozen timers; the 15 s heartbeat may not run for days. | The `visibilitychange` check on show covers it (AC-9, AC-18 [BROWSER]); labelled unverified (A-6). |
| G16 | 🟡 | The stamp must never make `/api/config` fail (it is the sidecar readiness probe, `sidecar.py:23`): a file removed between listing and `stat` (editor save-rename) or a missing static dir. | A vanished file is skipped; if the static directory cannot be listed, `ui_version` is omitted from the response (clients treat a missing field as unknown). Decision D-13 addendum; new AC. |
| G31 | 🟡 | Two tabs of the same browser (or a retry) can import the same values at the same moment; a key already equal on the server is neither "imported" nor "skipped" as defined. | An equal value is reported in `imported` and does not increment `rev` (FR-6, AC-46, AC-80). Decision D-21. |
| G32 | 🟡 | "The client takes its own `rev` from each POST response" hides another client's intervening change (the response's `rev` already includes it). | `POST /api/prefs` returns `{rev, prev}`; adopt `rev` only when `prev` equals the last known rev, else wait for the heartbeat mismatch and `refresh()` (FR-4, FR-6, AC-25, AC-79). Decision D-21. |
| G33 | 🟢 | Behaviour when `prefs_rev` is absent from `/api/config` (plugin disabled, older server) is unstated. | Ignored; no comparison, no refresh (FR-6, AC-53). Decision D-21. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G17 | 🟡 | NFR-4, NFR-5, NFR-6 carry `〈TBD〉` targets; "per-request cost of the stamp" cannot be asserted in CI (wall-time is flaky). | Enrich: propose numbers marked `⚠ [unrealistic?]`; make the stamp's cost testable deterministically (stat-only, AC-6) and record the measured 0.144 ms rather than assert it (same approach as T-031 NFR-7). |
| G18 | 🟡 | Boot waits on hydration with no bound; `REQUEST_TIMEOUT_MS` is 15 s (`core.js:50`), so a hung `/api/prefs` would hold the first render for 15 s. | Hydration has its own bound (proposed 3 s ⚠); on timeout boot proceeds as for "server unreachable" and the late result is applied through the live-pickup path. Decision D-17. |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G19 | 🟡 | `import_closed` never reopens (only deleting the file does); a legitimately new browser profile that still holds old values after a Reset loses them. | Intended by BR-4; stated in the entity lifecycle and in the Settings hint; no reopen control (not requested). |
| G20 | 🟡 | `audit.ACTIONS` (`audit.py:44`) feeds the `kanban.py audit --action` choices (`kanban.py:977`) and the Work-tab filter (`work_feature.py:48`); `record()` does not validate, so an unregistered action is recorded but unfilterable. `audit.py` has another ticket's uncommitted hunk. | New requirement: `prefs.reset` and `prefs.import` are in `audit.ACTIONS` (AC-32 extended); add after the foreign hunk settles (NFR-9). Decision D-19. |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G21 | 🟢 | `/api/config` is also the sidecar probe; `is_up` ignores the payload (`sidecar.py:110-117`), so added fields cannot break it. | Recorded; AC-1 pins the old keys, AC-58 pins `is_up` unchanged. |
| G22 | 🟡 | Live pickup calls `rebuildNav`, and `buildNav` adds a fresh `keydown` listener to the same `#tabs` element on every call (`app.js:94-105`; `C.clear` returns the same node, `core.js:193`), so repeated rebuilds make one arrow key move several tabs (read from code, not reproduced). Today only Settings toggles trigger it. | `rebuildNav` is called from pickup only when `hiddenTabs` actually changed; the listener is bound once. Decision D-18; [BROWSER] AC. |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G23 | 🟡 | "Persistent notice" is not a toast: toasts are armed to disappear (`core.js:508-522`), and no requirement says where the notice lives or that it must not cover the drawer's close button. | Notice is a non-modal element visible on every tab, `role="status"`, not a toast; exact placement is the builder's, checked in a browser; any new hyphenated class must exist in `styles.css` (NFR-3). |
| G24 | 🟡 | Copy for the three toasts (skipped, rejected, closed) is unspecified. | Fixed sentences in FR-6: name each key, give the value (skipped) or the reason (rejected); closed has the one sentence in G4. |
| G25 | 🟢 | `ConsoleDesktopTray.emitSession` runs on session events (`agents.js:1534-1543`), so a `voice.autoRead` change picked up from another client does not refresh the tray's mute indicator. | Accepted with A-5 (shared `voice`); not in scope to push tray state. |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G26 | 🟡 | `onboardingDraft` holds the person's name and console title (`onboarding-wizard.js:41,235`); it will sit in `console/.cache/prefs.json` (gitignored) and `GET /api/prefs` is unauthenticated like every other GET, including on a non-loopback bind (`httpd.py:203-240`). | Accepted: same exposure as the existing routes; BR-10 forbids secrets; the 16 keys hold none ([[T-036-analysis]] §3). |
| G27 | 🟢 | Audit detail must carry key names only. | Added to AC-32 (precedent: the onboarding actions' comment in `audit.py`). |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G28 | 🟡 | Rollback: deleting each browser's local copy after import means an old UI after rollback shows defaults; deleting `prefs.json` resets every client. | Q4 asks; default stays "delete"; rollback note goes in the release artifact. |
| G29 | 🟢 | No switch turns auto-reload off (a developer editing static files is reloaded when idle). Not requested. | Deferred; the notice and `enabled=false` for `prefs` are the only switches. Not added. |
| G30 | 🟡 | `onboarding-wizard.js:4` (a stale comment) sits in a file that is still untracked and edited by another pipeline; `app.js`, `settings.js`, `index.html`, `shell_feature.py`, `audit.py`, `styles.css` carry foreign hunks. | NFR-9 (surgical, re-read before edit, no reformat); the wizard comment fix is a SHOULD done only after that file lands. |

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements-draft]] · [[T-036-context-snapshot]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]]
- [[T-036-critique-report]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-release]]
