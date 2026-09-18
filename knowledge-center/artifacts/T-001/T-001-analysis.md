---
ticket: "T-001"
artifact: analysis
---

# Analysis: T-001

GROUND notes. Full survey of Tauri sidecar details is still due; product
shape is already recorded in [[desktop-assistant]].

## Context

T-001 is phase 1 of the desktop assistant: wrap the existing loopback web
UI in a native window. It is not a new agent runtime.

## Current State

Verified in-repo 2026-09-05:

- `console/` is stdlib-only Python, bind `127.0.0.1:8790`, vanilla JS UI.
- Agents backends already exist in `console/config/agents.toml` (`claude`,
  `cursor-agent`, `openrouter`, `ollama`, `lm-studio`). This ticket does
  not change them.
- Live `/send` is text-only (`console/static/agents.js`,
  `console/server/agent_session.py`, `console/server/agent_api_session.py`).
- No `desktop/` directory yet (stale at GROUND). `desktop/` now holds `sidecar.py` and the Tauri 2 host.

## Key Findings
- Finding: A browser cannot host OS capture or a private mic. Significance: the shell is a new process, not a `console/` plugin that draws pixels itself.
- Finding: Tauri 2 sidecar + WebView2 is the recommended host. Significance: `desktop/` is the implementation tree; `console/` stays drop-in.

## Research

See [[desktop-assistant]] (ranked shell / STT / OS stack, retrieved 2026-09-05). This ticket only consumes the **shell spike** slice.

## Recommended Path

Scaffold `desktop/` as Tauri 2, spawn `kanban.py serve`, load the loopback
URL, prove shutdown. Do not extend `/send` here.

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
- Design: [[desktop-assistant]]
