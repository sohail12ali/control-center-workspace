---
tags: [active]
status: Open
ticket: "T02"
---

# T02: Make Noble Salah a real Flutter web target

**Status:** In Progress  
**Stage:** VERIFY  
**Owner:** anjum@hu-manity.co  
**Created:** 2026-05-09  
**Due:**  

## Overview

Make Noble Salah's Flutter codebase run as a real web target. The app currently produces a blank page on `flutter run -d web-server` because `main()` calls mobile-only platform APIs before `runApp()`. Goal: full feature parity on web (where applicable) using `kIsWeb` guards, plugin stubs, and a DB abstraction layer.

## Current State

VERIFY in progress — all 6 fixer blocks resolved. 21/26 plan tasks complete (T02-18 re-opened, routed to planner). AC-15, AC-19 PASS with tests; NFR-06 PASS with WASM measurement (1.86 MB gzipped). WASM build: exit 0 after geolocator bump to ^14.0.0. flutter_tts warnings: non-fatal, documented. AC-26/NFR-02 NOT-YET-IMPLEMENTED (T02-18 builder scope). Test suite: 677 pass / 5 fail (all pre-existing). Next: user browser smoke test, CDN CORS, GH Pages deploy.

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
