---
tags: [completed]
status: Complete
ticket: "T-001"
closed_date: "2026-09-06"
---

# T-001: Native desktop shell spike wrapping the Delivery Console

**Status:** Complete  
**Stage:** Closed  
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

## Close note (2026-09-06)

All 8 acceptance criteria PASS ([[T-001-verification]]). The one open note (debug-build stray console window, subsystem `3`) is now tracked and fixed under [[T-003-verification]] FR-1. Closed by `@verifier` during the T-003 VERIFY pass, per `T-003-task-breakdown.md` task 5a-1.

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
- Design: [[desktop-assistant]]
- Tray skeleton: [[T-002-summary]]
