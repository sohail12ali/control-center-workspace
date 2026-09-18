---
tags: [active]
status: Done
ticket: "T-009"
---

# T-009: Tray click-to-talk, armed icon, Assistant settings panel

**Status:** Done  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-07  
**Due:**  

## Overview

Click the tray icon to talk. One click means whatever the icon is showing you:
talk when idle, send the take you are in the middle of when it is listening,
stop a reply that is being read aloud, and open the window when only a human
can help. `Tray icon click` in Settings → Assistant changes that to plain
"show the window", or to arming hands-free.

Two things came with it:

- **The icon now actually follows the state.** It did not before — repainting
  was reachable only from the console's event stream, so the microphone could
  open with the tray still showing idle. One painter (`tray_paint`) now serves
  every source of events.
- **A new `armed` icon** for hands-free: the mic is open and gated by a wake
  word. Held steady rather than following each take, which would flicker.

And the Assistant's settings — backend, model, mode, speech, session window,
ticket prefix, tray click, and the four hands-free keys — are on the Settings
tab instead of in a text editor, with `vision_models` shown read-only because
it is a committed statement about models rather than a per-machine choice.

## Current State

Shipped and verified: pytest 1076, cargo test 110, harness lint clean, and a
live run driving the real tray menu with one confirmed click per mode while
reading what the shell painted.

Still on a human: one physical left-click on the icon (every live check went
through the menu's Talk row, which is the same entry point), and the Linux
path, which nothing here can run.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
