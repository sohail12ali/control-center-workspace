---
ticket: "T02"
artifact: decision-log
---

# Decisions: T02

## D1 — Persistence: drift/WASM (durable IndexedDB)
**Decision:** Migrate `AppDatabase` from raw `sqflite` to `drift` with the `drift_wasm` web backend. Mobile keeps `drift_sqflite` (or `drift_native`). Same schema, same Dart-level API, different driver per platform.
**Rationale:** Prayer tracking, streak, and tasbih history must survive page refresh — losing this data on web would make the web app feel broken vs the mobile experience. drift gives one type-safe DAO across all platforms with minimal divergence.
**Impact:** +2–3 days. Affects `lib/data/database/app_database.dart` and every repository that touches it (`tasbih_recitation_repository`, `prayer_tracking_service`, `qada_service`, `streak_service`). Schema migration story still needed for existing mobile users.
**Resolves:** Q1
**Date:** 2026-05-09

## D2 — Hosting: GitHub Pages primary, keep options open
**Decision:** Build artefacts and PWA manifest configured to work on GitHub Pages first (subpath `--base-href` aware), but no hosting-specific features that would lock it to GH Pages. Quran audio CDN CORS must allow the GH Pages origin and `localhost` for dev.
**Rationale:** GH Pages is free, version-controlled, and good enough for v1. Keeping it portable means Firebase/custom domain remain possible without rewrite.
**Impact:** Adds a `--base-href` build step. PWA `start_url` must be relative. CDN CORS update is an external (non-code) task.
**Resolves:** Q2
**Date:** 2026-05-09

## D3 — Ship as PWA
**Decision:** v1 ships as an installable Progressive Web App with manifest, icons, and a service worker for offline shell caching (CodeBase + Quran assets cache-on-demand).
**Rationale:** PWA gives the closest thing to a native app feel on web (installable, offline shell, splash screen) at low cost — Flutter generates most of it.
**Impact:** Custom `flutter_service_worker.js` config; PWA install prompt logic in shell.
**Resolves:** Q3
**Date:** 2026-05-09

## D4 — Stay fully local on web (no auth, no cloud sync)
**Decision:** Web version remains 100% local-first, same as mobile. No accounts, no cloud sync, no telemetry beyond what the mobile build already does.
**Rationale:** Keeping parity with mobile's local-first model. Adding auth/sync is a separate, larger initiative — out of scope for T02.
**Impact:** No backend changes. Drift/WASM stores everything in the user's browser IndexedDB. Multi-device sync remains a future ticket.
**Resolves:** Q4
**Date:** 2026-05-09

## D5 — Hide athan notifications on web (no Web Push in v1)
**Decision:** On web, the notification scheduling section is hidden and replaced with an informational banner: "Athan notifications are only available in the mobile app." Web Push is explicitly out of scope.
**Rationale:** `flutter_local_notifications` has no web implementation; Web Push requires a backend (push server, VAPID keys, subscription store) which contradicts D4 (stay local). Cleanly hiding is the only option that fits.
**Impact:** Settings UI gates the section behind `!kIsWeb`. `NotificationService` becomes a no-op stub on web. Onboarding's Notifications page removed on web (see D8).
**Resolves:** Q5
**Date:** 2026-05-09

## D6 — Hide compass-dependent UI on web; keep static Qibla bearing
**Decision:** On web, the live Qibla compass needle is hidden. The Qibla tab is kept and shows a static bearing card (calculated great-circle direction in degrees + a fixed compass rose SVG oriented to that bearing). Anything that strictly requires magnetometer is hidden.
**Rationale:** Most of the Qibla feature's value (knowing the direction) survives without a live needle; only the live-rotation UX is lost. Hiding the whole tab would over-cut.
**Impact:** `qibla_screen.dart` branches on `kIsWeb`; `QiblaService.compassStream()` returns `Stream.empty()` on web; static bearing widget added.
**Resolves:** Q6
**Date:** 2026-05-09

## D7 — Single `main.dart` with `kIsWeb` guards
**Decision:** Keep one entry-point `lib/main.dart`. Branch on `kIsWeb` (and `defaultTargetPlatform` where finer granularity is needed) for platform-specific init. No separate `main_web.dart`.
**Rationale:** Lower divergence, less code duplication, easier to keep platforms in sync. The init code that differs is small enough to inline-guard.
**Impact:** Refactor `main()` to wrap each platform-only call in `kIsWeb`-aware blocks. Affected services keep one Dart file but gain platform-aware factories.
**Resolves:** Q7
**Date:** 2026-05-09

## D8 — Skip onboarding on web; ask permissions on demand
**Decision:** On web, the 4-page onboarding flow is skipped on first load. Permissions (Geolocation primarily) are requested on demand when the user first interacts with a feature that needs them. Prayer calculation method defaults to a sensible value with an inline edit affordance in Settings.
**Rationale:** Web users expect SPA-style "land and use," not a mobile onboarding wizard. Permission-on-demand is the web norm. Two of four onboarding pages don't apply on web anyway (D5 covers Notifications, Battery is mobile-only).
**Impact:** `app_shell.dart` skips the onboarding gate when `kIsWeb`. Geolocation prompt is moved to first feature touch (e.g. opening prayer-times screen). Calculation-method default lives in `prayer_settings_service` defaults.
**Resolves:** Q8
**Date:** 2026-05-09

## D8.1 — Default to timezone-derived location on web (refines D8)
**Decision:** On web first launch, when `LocationService.getLastKnown()` returns null, the app calls `fetchTimezoneLocation()` synchronously in `main()` before `runApp()`. The browser geolocation permission prompt is no longer the first-touch UX — it remains available through Settings → "Use my location".
**Rationale:** Asking for browser geolocation on first paint is a heavy permission ask that most users decline. Timezone-derived location (UTC-offset → representative city, ±500 km accuracy) lets the app render prayer times immediately with zero friction. The user can refine to GPS later when they explicitly want to.
**Impact:** 5-line addition to `lib/main.dart` after LocationService construction. The existing `LocationService.fetchTimezoneLocation()` and `LocationSource.timezone` were already in the codebase — no new APIs needed.
**Resolves:** Refines D8 (which originally said "permission-on-demand at first feature touch"). Now first feature touch shows a useful (if approximate) result; permission becomes opt-in later.
**Date:** 2026-05-09

## Amendment 2026-05-09 — T02-18 re-opened: service worker never implemented

**Trigger:** Fixer BLOCK-1 discovery during VERIFY pass.

**Before:** T02-18 marked `[x]` in plan.md. Done-criteria stated: "AC-26 (offline shell load ≤ 2 s) passes; service worker shown as active in DevTools; NFR-02 measured." Builder registered `flutter_service_worker.js` in `index.html` and considered the task complete.

**After:** T02-18 flipped back to `[ ]`. Evidence: `build/web/flutter_service_worker.js` is 815 bytes — Flutter's deprecated self-unregistering stub. On `activate` it calls `self.registration.unregister()` and reloads clients; it caches nothing. `flutter_bootstrap.js` explicitly comments: *"Flutter's service worker is deprecated and will be removed in a future Flutter release."* No custom service worker file exists anywhere in `web/`. AC-26 and NFR-02 cannot pass.

**Required action (builder scope):** Write `web/service_worker.js` — a custom Cache API service worker that:
1. On `install`: pre-caches app shell assets (`flutter.js`, `main.dart.js`, `flutter_bootstrap.js`, `manifest.json`, `favicon.png`, `icons/*`, `assets/`).
2. On `fetch`: serves cached assets cache-first; falls through to network for CDN audio URLs.
3. Register it in `web/index.html` replacing the deprecated `serviceWorkerSettings` approach in `flutter_bootstrap.js`.

Alternatively: add `workbox-cli` or `workbox-webpack-plugin` and generate the precache manifest from the build output.

**Cascades:** AC-26 and NFR-02 in verification.md set to NOT-YET-IMPLEMENTED. T02-11 done-criteria note updated (build size must be re-measured after real SW added). D3 remains valid — decision to ship as PWA stands; only the implementation task was mis-marked done.

**Date:** 2026-05-09

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
