---
ticket: "T02"
artifact: verification
---

# Verification: T02

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-01 | `flutter run -d web-server` reaches `runApp()` without throwing; non-blank in Chrome within 15 s | PENDING-USER-VERIFICATION | Build succeeded; needs user to open Chrome and confirm visual render. Repro: `cd D:/Workspace/noble-wave/noble-salah && flutter run -d web-server --web-port 8080`, then open `http://localhost:8080`. |
| AC-02 | Zero uncaught exceptions in browser console on core nav (PT/Quran/Qibla/Dhikr/Tasbih/Settings) | PENDING-USER-VERIFICATION | All known throw-points guarded with `kIsWeb`; remaining must be confirmed via DevTools Console. |
| AC-03 | `flutter build apk --debug` exits 0 with no new errors | **PASS** | `√ Built build\app\outputs\flutter-apk\app-debug.apk` — Gradle 80.3 s, exit 0. Mobile regression-free. |
| AC-04 | Prayer-tracking record persists across browser refresh (drift/WASM/IndexedDB) | PENDING-USER-VERIFICATION | drift `WasmDatabase` factory wired in `app_database.dart`; needs manual mark-prayer + refresh in browser. |
| AC-05 | Tasbih history (count) survives page refresh | PENDING-USER-VERIFICATION | Same drift IndexedDB path as AC-04. |
| AC-06 | DevTools → IndexedDB shows `noble_salah` database entry | PENDING-USER-VERIFICATION | Manual DevTools inspection needed. |
| AC-07 | `grep -rn "Platform\." lib/` returns zero bare calls (only `TargetPlatform`/`defaultTargetPlatform`/`MethodChannel`) | **PASS** | `grep -rn "Platform\." lib/ --include="*.dart" \| grep -v "TargetPlatform\|defaultTargetPlatform\|MethodChannel\|DeviceOrientation"` → zero output. |
| AC-08 | `notification_service.dart`, `onboarding_screen.dart`, `settings_screen.dart` clean of bare `dart:io Platform.*` | **PASS** | `grep -rn "import 'dart:io'" lib/` returns zero — no `dart:io` imports anywhere in `lib/`. |
| AC-09 | Prayer times display within 3 s on web | PENDING-USER-VERIFICATION | Browser timing measurement required. |
| AC-10 | Quran reader opens Surah Al-Fatiha on web | PENDING-USER-VERIFICATION | Manual browser check. |
| AC-11 | Quran audio plays ≥ 5 s from CDN without CORS error | PENDING-USER-VERIFICATION + EXTERNAL | Blocked on T02-21 (CDN CORS allowlist for GH Pages origin). Repro: with CDN CORS set, click play on a verse; audio should advance ≥ 5 s. |
| AC-12 | Adhkar screen renders all categories; TTS button does not crash | PENDING-USER-VERIFICATION | `flutter_tts` has Web Speech API support; visual confirm needed. |
| AC-13 | Tasbih counter increments and resets | PENDING-USER-VERIFICATION | Visual confirm. Persistence covered by AC-05. |
| AC-14 | Qibla tab shows static bearing card + compass-rose SVG on web | PENDING-USER-VERIFICATION | `_WebStaticBearingBody` widget in `qibla_screen.dart` rendered behind `kIsWeb`; visual confirm needed. |
| AC-15 | Live needle absent on web | **PASS** | `QiblaScreen` accepts `isWebOverride` param (`@visibleForTesting`). Widget test `qibla_screen_web_guard_test.dart` passes `isWebOverride: true`, asserts `find.byType(CircularProgressIndicator)` finds nothing (no `_CompassBody`) and `find.textContaining('Live compass requires the mobile app')` finds one widget. 3/3 widget tests pass (677 pass / 5 fail suite). |
| AC-16 | No FlutterCompass method-channel calls in browser console | **PASS (code-level)** | `WebNoOpCompassPlugin()` injected in `main.dart` line 209 when `kIsWeb`; never instantiates `FlutterCompassAdapter`. |
| AC-17 | Athan notification scheduling section hidden in Settings on web | **PASS (code-level)** | `settings_screen.dart` wraps athan section in `if (!kIsWeb)`. Visual confirm needed. |
| AC-18 | Info banner "Athan notifications are only available in the mobile app" visible | **PASS (code-level)** | `_AthanWebBanner` widget rendered when `kIsWeb`; visual confirm needed. |
| AC-19 | `NotificationService.initialize()` never invoked on web | **PASS** | `main.dart` wraps call via `initNotificationServiceIfNative(svc, isWeb: kIsWeb)`. Unit test `notification_service_web_guard_test.dart` mocks `NotificationsPlugin`, calls with `isWeb: true`, asserts `initializeCallCount == 0`. Test passes (674 pass / 5 fail suite). |
| AC-20 | Web first load goes directly to main shell (no onboarding) | **PASS (code-level)** | `main.dart` overrides `onboardingComplete = true` when `kIsWeb`. |
| AC-21 | Onboarding notification/battery pages never shown on web | **PASS (code-level)** | Belt-and-suspenders guards in `onboarding_screen.dart` plus the AC-20 short-circuit. |
| AC-22 | No battery optimization card on web in Settings | **PASS (code-level)** | `_BatteryOptimizationBanner` wrapped in `if (!kIsWeb)`. |
| AC-23 | No Play Store update card on web in Settings | **PASS (code-level)** | `_CheckForUpdateCard` wrapped in `if (!kIsWeb)`. |
| AC-24 | PWA install prompt appears in Chrome | PENDING-USER-VERIFICATION | Manifest valid; needs user to visit deployed URL and observe install icon. |
| AC-25 | Lighthouse PWA score ≥ 90 | PENDING-USER-VERIFICATION | Run Lighthouse against deployed URL after T02-22 (smoke deploy). |
| AC-26 | Service worker offline shell loads in ≤ 2 s | **NOT-YET-IMPLEMENTED** | `flutter_service_worker.js` is Flutter's deprecated self-unregistering stub (815 bytes, calls `self.registration.unregister()` on activate, caches nothing). `flutter_bootstrap.js` explicitly labels it deprecated. T02-18 was incorrectly marked `[x]` — flipped back to `[ ]` in plan.md. Real app-shell caching service worker (e.g. Workbox or custom Cache API) is builder scope; routed to planner via evolve. AC-26 cannot pass until T02-18 is re-implemented. |
| AC-27 | `flutter build web --base-href /noble-salah/` exits 0 | **PASS** | `√ Built build\web` — 76.2 s, exit 0. Run via PowerShell to avoid MSYS path mangling. |
| AC-28 | No 404s for JS/CSS/icon assets on deployed URL | PENDING-USER-VERIFICATION + EXTERNAL | Blocked on T02-22 (GitHub Pages deployment). |

## Non-Functional Requirements

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| NFR-01 | Initial load TTI ≤ 8 s on Fast 3G | PENDING-USER-VERIFICATION | Lighthouse measurement after deploy. |
| NFR-02 | Service-worker second load TTI ≤ 2 s on Fast 3G | **NOT-YET-IMPLEMENTED** | Depends on AC-26. T02-18 re-opened in plan.md (service worker caches nothing — deprecated self-unregistering stub). Cannot measure until real caching SW is built. |
| NFR-03 | Zero console errors on core navigation | PENDING-USER-VERIFICATION | DevTools Console inspection. |
| NFR-04 | Mobile build (Android) regression-free | **PASS** | `flutter build apk --debug` exit 0; AC-03 evidence. |
| NFR-05 | Drift migration preserves existing sqflite data | **PARTIAL PASS** | `test/data/database/app_database_migration_test.dart` updated to use drift in-memory. Real-world migration from existing user devices needs field test. |
| NFR-06 | WASM/JS bundle ≤ 8 MB gzipped | **PASS** | JS build: `main.dart.js` gzipped = 1.38 MB. WASM build (`flutter build web --wasm --base-href '/noble-salah/'`, run 2026-05-09 via PowerShell): `main.dart.mjs` 205.8 KB + `main.dart.wasm` 1,323.1 KB + `flutter.js` 3.6 KB + `flutter_bootstrap.js` 3.8 KB + `sqlite3.wasm` 327.4 KB = **1.86 MB gzipped** initial load (1.93 MB including `drift_worker.js`). Well under 8 MB budget. Note: `geolocator_web` bumped from 2.2.1 → 4.1.3 (via `geolocator ^14.0.0`) to fix `dart:html` WASM compile error. |
| NFR-07 | Browser support (Chrome ≥ 110, Edge ≥ 110, Firefox ≥ 115, Safari ≥ 15) | PENDING-USER-VERIFICATION | Cross-browser smoke required after deploy. |

## Test Results

- **Full `flutter test`**: 671 pass / 6 fail.
- **6 failures**:
  - 4 in `test/features/islamic_calendar/islamic_calendar_screen_test.dart` (renders / today highlight / next-month chevron / event dot) — **pre-existing**, unrelated to T02 (no DB or platform code touched in this feature).
  - 1 in `test/domain/services/athan_preferences_service_test.dart` (`alarmClockMode defaults to false`) — **pre-existing**.
  - 1 in `test/domain/services/tasbih_service_phrase_test.dart` (`T2.5 — 33-target: history has 1 entry after 99 taps`) — **consistently failing** (Expected 1, Actual 3 — reproducible on re-run 2026-05-09). Not a timing flake; logic error in auto-complete session counting. Blocker for fixer.
- **Test fixes applied during VERIFY (3 files)**: `streak_service_test.dart`, `tasbih_service_phrase_test.dart`, `widget_bridge_service_test.dart` — migrated from sqflite `injectDatabase()` to drift `injectExecutor(NativeDatabase.memory())`.

## Code-Level Pass Summary

11 ACs pass at code/build level (AC-03, 07, 08, 16–23, 27; NFR-04, NFR-06 pass; NFR-05 partial). AC-26 BLOCKED (service worker caches nothing — T02-18 done-criteria unmet). NFR-02 BLOCKED (same root cause). 14 ACs require live browser verification (AC-01, 02, 04–06, 09–15, 24, 25, 28 plus NFR-01, NFR-03, NFR-07). 2 ACs additionally blocked on external work (AC-11 CDN CORS, AC-28 GitHub Pages deploy). 1 test blocker: tasbih_service_phrase_test T2.5 consistently failing.

## Pending User Verification — Reproduction Steps

1. **Local web smoke test** (covers AC-01, AC-02, AC-04, AC-05, AC-06, AC-09, AC-10, AC-12, AC-13, AC-14, AC-15, AC-17, AC-18, AC-22, AC-23, AC-26, NFR-03):
   ```powershell
   cd D:/Workspace/noble-wave/noble-salah
   flutter run -d web-server --web-port 8080
   ```
   Open `http://localhost:8080` in Chrome. Open DevTools → Console (zero red errors expected). Navigate Prayer Times → Quran → Qibla → Dhikr → Tasbih → Settings. Mark a prayer → refresh → confirm persisted. Open DevTools → Application → IndexedDB → confirm `noble_salah` entry.

2. **CDN CORS allowlist** (AC-11, T02-21): coordinate with whoever controls the Quran audio CDN to add `https://<owner>.github.io` and `http://localhost:*` to `Access-Control-Allow-Origin`. Verify with `curl -H "Origin: https://<owner>.github.io" -I <cdn-audio-url>`.

3. **GitHub Pages deploy & cross-browser** (AC-24, AC-25, AC-28, NFR-01, NFR-02, NFR-07): merge to `main` to trigger `.github/workflows/web-deploy.yml`. After successful deploy, open the GH Pages URL in Chrome, Edge, Firefox, Safari. Run Lighthouse → record PWA score. Throttle to Fast 3G → measure first and second load TTI.

## Edge Cases Probed

- `dart:io` removed from all `lib/` files (zero imports).
- All bare `Platform.*` calls replaced with `defaultTargetPlatform`-based checks.
- `try/catch` around `JustAudioBackground.init()` replaced with `if (!kIsWeb)` guard (per analysis: dart2js runtime errors escape try/catch).
- `AndroidBatteryOptimizationAdapter()` construction guarded at the call site (R6 mitigation).
- `FlutterCompassAdapter()` construction replaced with `WebNoOpCompassPlugin()` on web (R7 mitigation).
- Drift in-memory test executor pattern adopted across 6 test files (3 originally migrated by builder + 3 fixed during VERIFY).

## Notes

- Working tree under `D:/Workspace/noble-wave/noble-salah` is on branch `develop` with 30 modified/untracked files (21 modified lib/test files + 9 untracked web assets incl. `.github/`). Changes are uncommitted.
- **SERVICE WORKER — T02-18 re-opened (fixer decision 2026-05-09):** `build/web/flutter_service_worker.js` (815 bytes) is Flutter's deprecated self-unregistering stub — activates, calls `self.registration.unregister()`, caches nothing, then reloads clients. `flutter_bootstrap.js` explicitly comments it as deprecated. T02-18 was incorrectly marked `[x]`; fixer flipped it back to `[ ]` in plan.md. Implementing a real app-shell caching service worker (Workbox or custom Cache API) is **builder scope** — routed to planner via evolve. AC-26 and NFR-02 status set to NOT-YET-IMPLEMENTED.
- **TASBIH TEST BLOCKER (reconcile finding 2026-05-09):** `tasbih_service_phrase_test.dart T2.5` consistently fails with Expected: 1 / Actual: 3 on re-run — not a timing flake. Logic error in auto-complete session save counting. **Routed to fixer.**
- **flutter_tts WASM lint warnings (BLOCK-6, resolved 2026-05-09):** `flutter build web --wasm` emits `invalid_runtime_check_with_js_interop_types` lint warnings from `flutter_tts-4.2.5`. Verified on Flutter 3.41.7 / Dart 3.11.5 stable: WASM build **succeeds** (exit 0) with these warnings present — they are non-fatal under the current SDK. Downgraded from BLOCK to documented warning. No code change required. Monitor CI; if a future Flutter/Dart upgrade promotes these to errors, fix by pinning a newer `flutter_tts` version that uses `package:web` interop.
- **geolocator dart:html WASM error (BLOCK-5/BLOCK-6, resolved 2026-05-09):** `geolocator_web-2.2.1` used `dart:html` which is unavailable under dart2wasm, causing a hard compile error. Fixed by bumping `geolocator` constraint from `^9.0.0` to `^14.0.0` in `pubspec.yaml`, resolving `geolocator_web` to 4.1.3 (which uses `package:web`). `desiredAccuracy` param in `getCurrentPosition` calls is now deprecated in v14 but still accepted — no call-site changes required. WASM build now succeeds.
- Bash-on-Windows mangles `--base-href /noble-salah/` to `C:/Program Files/Git/noble-salah/`. Always run `flutter build web` via PowerShell.
- The local `flutter build web` (non-`--wasm`) completed successfully: exit 0, `build/web/` produced, `<base href="/noble-salah/">` present in built `index.html`.

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
