---
tags: [active]
status: Open
ticket: "T-001"
---

# T-001: Native desktop shell spike wrapping the Delivery Console

**Status:** Open  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-05  
**Due:**  

## Overview

Phase 1 of the desktop-assistant roadmap in [[desktop-assistant]]. A native
window that starts `python console/kanban.py serve`, loads the loopback UI,
and shuts the sidecar down cleanly. Portable host; this machine smokes Windows.

The window is Tauri 2 (`desktop/src-tauri/`), not WinForms. See
[[T-001-decision-log]] `host-tauri-2` (supersedes `host-webview2-not-tauri`).

This ticket does not add screen capture, voice, multimodal `/send`, OS
control, or the system tray. Tray skeleton is [[T-002-summary]]. The stdlib
console still works in a browser without the shell.

## Current State

Tauri 2 host under `desktop/src-tauri/`. Caption buttons live in the Console
header. Run (from workspace root, after `desktop/msvc-env.ps1` if `vcruntime.h`
is missing): `cargo run --manifest-path desktop/src-tauri/Cargo.toml`

VERIFY evidence in [[T-001-verification]].

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
- Design: [[desktop-assistant]]
- Tray skeleton: [[T-002-summary]]
