---
tags: [active]
status: Open
ticket: "T02"
---

# T02: Make Noble Salah a real Flutter web target

**Status:** Open  
**Stage:** CLARIFY  
**Owner:** anjum@hu-manity.co  
**Created:** 2026-05-09  
**Due:**  

## Overview

Make Noble Salah's Flutter codebase run as a real web target. The app currently produces a blank page on `flutter run -d web-server` because `main()` calls mobile-only platform APIs before `runApp()`. Goal: full feature parity on web (where applicable) using `kIsWeb` guards, plugin stubs, and a DB abstraction layer.

## Current State

GROUND analysis complete. 8 open CLARIFY questions pending user input. Implementation blocked on answers to Q1 (persistence strategy) and Q5 (notifications on web). No code changes made yet.

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
