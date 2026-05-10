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

VERIFY in progress — 22/26 plan tasks complete. T02-18 re-implemented: custom Cache API service worker in `web/service_worker.js`, registered in `index.html`. AC-03/NFR-04 PASS (BuildConfig fix). AC-26/NFR-02 now PENDING-USER-VERIFICATION (SW built, needs Chrome DevTools confirmation). Test suite: 677 pass / 5 fail (all pre-existing). Next: browser smoke test, CDN CORS, GH Pages deploy.

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
