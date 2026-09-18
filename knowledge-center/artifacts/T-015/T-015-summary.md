---
tags: [active]
status: Verify
ticket: "T-015"
---

# T-015: Make the Assistant fast, the tray honest, and the popup dismissible

**Status:** Verify  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-10  
**Due:**  

## Overview

Three usability defects across the desktop shell, taken as one ticket because they share a
cause: surfaces that claim more than they deliver, and I/O on paths that must not block.

1. **The Assistant is slow** — not because the fast path is missing, but because it is unused.
   The `openai_api` transport already runs a streaming, tool-holding, approval-gated loop the
   console owns ([[T-012-summary]], [[T-014-summary]]); the machine's stored setting points at
   the Claude Code CLI instead.
2. **The tray declares 16 available features and offers 8**, and freezes on a click because the
   click handler does blocking HTTP on the UI thread against an endpoint that probes the network.
3. **The voice overlay cannot be dismissed** and has states it never leaves.

Decisions taken up front (asked and answered before planning): OpenRouter becomes the default
talk backend with a health-checked local fallback chain; the tray menu is generated from
`desktop/features.toml` rather than hand-written; the overlay is fixed against sticking first,
then made interactive. [[T-002-summary]] (tray skeleton, still in Verify) is closed inside this
ticket, since Thread 2 supersedes its scope.

## Current State

Evidence gathered at GROUND, all citable:

- `console/.cache/assistant/settings.json` → `backend: "claude"`, `work_backend: "claude"`.
- `knowledge-center/telemetry/2026-09.jsonl` → `claude` turns at 2.4s / 4.4s / 6.6s and
  92s / 125s / 307s. API-backed turns all report `duration_ms: 0`, so the fast path is
  unmeasurable.
- `console/.cache/agent-chats/*.events.jsonl` → the three local failures that caused the
  fallback to `claude`: `qwen3:8b` needs 5.5 GiB with 4.7 available; `deepseek-coder`
  "does not support tools"; LM Studio at `192.168.1.14:1234` times out (WinError 10060).
- `console/config/agents.toml` → `openrouter` is already `enabled = true`; it needs a key
  and a model, not code.
- `desktop/features.toml` → 25 rows, 16 `available = true`;
  `desktop/src-tauri/src/tray.rs` hand-writes 8 menu items.
- `desktop/src-tauri/src/click.rs:128` → `setting_for` calls `console_settings::string_or`,
  which bypasses the module's own cache and blocks the tray's UI thread.
- `console/server/features/assistant_feature.py` `settings_get` → evaluates
  `Backend.installed` for every row, which probes at `PROBE_TIMEOUT = 1.5s` each.
- `console/server/agent_manager.py:63` `create()` always sends its opening message;
  `assistant_feature.py:239` passes `"Hello."` — a whole wasted turn per new chat.
- `desktop/src-tauri/src/tray_paint.rs:138` → `Event::ApprovalResolved` maps to `{}`, so the
  overlay never hides when a card resolves.

Baseline before any change: **1175 python tests pass** (`pytest -o addopts=""`, 94.6s).
The Rust crate needs `. ./desktop/msvc-env.ps1` sourced before `cargo` will compile at all —
without it, `cc-rs` fails on a missing `excpt.h`.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
