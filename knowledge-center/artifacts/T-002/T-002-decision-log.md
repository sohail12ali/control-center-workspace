---
ticket: "T-002"
artifact: decision-log
---

# Decisions: T-002

## skeleton-five-actions
**Decision:** First tray code drop wires only Show window (`show_window`), New chat (`new_chat`), Mute replies (`mute_replies`), Interrupt (`interrupt`), and Quit (`quit`), plus the header line `session_backend`. Every other `desktop/features.toml` row stays `available = false`.
**Rationale:** Locked in [[desktop-assistant]]. The tray is a remote control of the live Agents chat. Listen, clipboard, capture, watch, and actuation wait for their phases. Do not ship a second product in the menu.
**Impact:** Requirements freeze and the first Tauri tray-icon implementation must not add listen/clipboard/capture rows as working actions. Disabled-with-reason is allowed.

## hide-to-tray-not-destroy
**Decision:** Window close (HTML caption X and OS close) hides to the tray and does not stop the sidecar. **Quit** is the T-001 close: stop an owned `kanban.py serve`, leave a reused serve running.
**Rationale:** [[desktop-assistant]] `[projection].close_window_default = hide_to_tray`. T-001 FR 4 still applies to Quit, not to hide.
**Impact:** `desktop-chrome.js` must not call `win.close()` as destroy-only; host must intercept close. Tests/smoke must distinguish hide vs quit.

## skeleton-menu-omits-unavailable
**Decision:** T-002 tray menu is header + Show / New chat / Mute / Interrupt / Quit only. Later-phase `available = false` rows are omitted from the menu, not shown grey.
**Rationale:** Projecting the whole catalog on day one is clutter. Wiki disabled-with-reason applies when a phase lands and the row is in the projection.
**Impact:** Do not implement listen/clipboard/capture menu entries this ticket.

## events-not-capability-widen
**Decision:** Tray and (future) hotkeys are native. They emit events into the webview. Do not add `shell` / `fs` to `loopback-chrome.json`. Do not add a TOML parser crate this ticket; skeleton ids are hardcoded to match `desktop/features.toml`.
**Rationale:** [[desktop-assistant]] Native vs webview. SIMPLIFY: six ids, not a registry engine.
**Impact:** Drift risk if catalog ids change; comment both sides.

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- Design: [[desktop-assistant]]
- Registry: `desktop/features.toml`
