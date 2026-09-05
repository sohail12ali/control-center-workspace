---
tags: [active]
status: Open
ticket: "T-002"
---

# T-002: Desktop tray skeleton as the Agents control surface

**Status:** Open  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-05  
**Due:**  

## Overview

First tray code for the Delivery Console desktop shell. The tray is a remote
control of the **live Agents chat**, not a second product. This ticket wires
the native tray to five actions only: Show window, New chat, Mute replies
(`autoRead`), Interrupt current turn, and Quit.

The catalog already lives in `desktop/features.toml`. Every other row stays
`available = false` (grey with `reason_unavailable`, or hidden if Settings
later opts into hide-unavailable). Listen, clipboard, capture, watch, and
actuation are later phases on [[desktop-assistant]] — not this ticket.

Hotkeys share the same feature `id`s. Left-click default is Show window.
Quit must not stop a reused `kanban.py serve`. Do not add `shell` / `fs` to
`desktop/src-tauri/capabilities/loopback-chrome.json`.

## Current State

GROUND survey in [[T-002-analysis]]: no tray in the Tauri host; five actions
already exist in the Agents tab. Host now builds with a skeleton tray
(`desktop/src-tauri/src/tray.rs`). GUI smoke: tray icon present, close hides,
left-click restores, serve stays up. Menu actions still need a hand click —
see [[T-002-verification]].

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- Design: [[desktop-assistant]]
- Registry: `desktop/features.toml`
- Shell spike: [[T-001-summary]]
