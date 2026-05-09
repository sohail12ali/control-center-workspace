---
ticket: "T02"
artifact: plan
stage: CANONICAL
status: frozen
frozen: 2026-05-09
---

# Plan: T02 — Make Noble Salah a Real Flutter Web Target

## Total Effort

| Slice | Hours |
|-------|-------|
| S1 — Bootstrap unblock | 6 h |
| S2 — drift/WASM migration | 14 h |
| S3 — Plugin stubs & feature gating | 6 h |
| S4 — UI polish (PWA + web assets) | 5 h |
| S5 — Build & deploy (GH Pages + CI) | 5 h |
| S6 — Verification | 6 h |
| **Total** | **42 h** |

---

## Approach

The app breaks on web because `main()` calls mobile-only platform APIs before `runApp()`. The fix proceeds in dependency order: first unblock startup (S1), then migrate the storage layer to drift/WASM for durable IndexedDB persistence (S2), then stub every remaining mobile-only plugin and gate the corresponding UI sections (S3), then add PWA manifest, icons, and service worker (S4), then wire the GitHub Actions deploy pipeline (S5), then run the full verification matrix (S6). A single `main.dart` is kept throughout (D7); no separate entry-point is introduced. Mobile (Android/iOS) must remain regression-free after every slice.

---

## Slice S1 — Bootstrap Unblock

**Goal:** `flutter run -d web-server` reaches `runApp()` without throwing. Zero uncaught exceptions in the browser console on startup. Mobile build unaffected.

### [x] T02-01 — Enable Flutter web target (1 h)
- [ ] Run `flutter create --platforms web .` in project root to generate `web/` directory (`index.html`, `manifest.json` stub, `flutter_service_worker.js`, `favicon.png`).
- [ ] Verify `flutter run -d web-server` starts (blank page or crash is fine at this stage — just confirms the toolchain works).
- [ ] Commit the generated `web/` directory.
- **Done-criteria:** `web/index.html` exists and `flutter run -d web-server` starts without a Dart toolchain error.
- **Basis:** No web target currently exists (no `web/` directory found in source tree).
- **Depends on:** —

### [x] T02-02 — Guard `JustAudioBackground.init()` and `AudioSession` in `main.dart` (1 h)
- [ ] Add `import 'package:flutter/foundation.dart' show kIsWeb;` at top of `lib/main.dart`.
- [ ] Wrap `JustAudioBackground.init(...)` (line 166) with `if (!kIsWeb) { ... }` — move outside the existing try/catch since try/catch is insufficient on web dart2js.
- [ ] Wrap `AudioSession.instance` / `.configure(...)` (lines 178–179) with `if (!kIsWeb) { ... }`.
- [ ] Verify `flutter build apk --debug` still exits 0.
- **Done-criteria:** `JustAudioBackground.init()` and `AudioSession` code paths are skipped on web; no regression on APK build.
- **Basis:** analysis.md — "try/catch is insufficient on web dart2js runtime throws in a way that escapes the catch".
- **Depends on:** T02-01

### [x] T02-03 — Guard `HomeWidget`, `notificationService`, `prayerSchedulerService`, and `batteryOptimizationService` in `main.dart` (1 h)
- [ ] Wrap `HomeWidget.setAppGroupId(...)` (line 182) with `if (!kIsWeb)`.
- [ ] Wrap `notificationService.initialize(...)` (lines 239–240) with `if (!kIsWeb)`.
- [ ] Wrap `prayerSchedulerService.initialize()` (line 255) with `if (!kIsWeb)`.
- [ ] Wrap `batteryOptimizationService.checkStatus()` (line 257) with `if (!kIsWeb)`.
- [ ] Verify `flutter run -d web-server` no longer throws on these calls.
- **Done-criteria:** All four calls are skipped on web; APK build still exits 0.
- **Basis:** analysis.md call-site table, main.dart lines 182, 239–240, 255, 257.
- **Depends on:** T02-02

### [x] T02-04 — Replace `dart:io Platform.*` calls with `kIsWeb`-safe equivalents (2 h)
- [ ] In `lib/domain/services/notification_service.dart`: remove `import 'dart:io'`; replace `Platform.isAndroid` (lines 93, 99, 116, 179, 186) and `Platform.isIOS` with `defaultTargetPlatform == TargetPlatform.android` / `defaultTargetPlatform == TargetPlatform.iOS` guarded by `!kIsWeb` where needed. Add `import 'package:flutter/foundation.dart'`.
- [ ] In `lib/features/onboarding/onboarding_screen.dart`: replace `Platform.isAndroid` (lines 946, 1034) with `!kIsWeb && defaultTargetPlatform == TargetPlatform.android`; remove `import 'dart:io'`.
- [ ] In `lib/features/settings/settings_screen.dart`: replace `Platform.isAndroid` / `_openPlayStore` call (line 1366) with `!kIsWeb && defaultTargetPlatform == TargetPlatform.android`; remove `import 'dart:io'`.
- [ ] Run `grep -rn "import 'dart:io'" lib/` and fix any remaining occurrences that are not inside a conditional import.
- [ ] Verify `flutter run -d web-server` starts without `UnsupportedError` from dart:io.
- **Done-criteria:** AC-07 grep passes (zero bare `Platform.*`); AC-08 files clean; APK exit 0.
- **Basis:** analysis.md "Critical Risk" section; requirements FR-02, AC-07, AC-08.
- **Depends on:** T02-03

### [x] T02-05 — Provide `WebNoOpCompassPlugin` stub and wire `QiblaService` (1 h)
- [ ] Add `class WebNoOpCompassPlugin implements CompassPlugin` in `qibla_service.dart` (or a new `lib/domain/services/web_stubs.dart`) — `get events => const Stream.empty()`.
- [ ] In `main.dart` where `FlutterCompassAdapter()` is constructed (line 209), replace with `kIsWeb ? WebNoOpCompassPlugin() : FlutterCompassAdapter()`.
- [ ] Verify `QiblaService` receives the no-op on web without crash.
- **Done-criteria:** `flutter run -d web-server` reaches `runApp()` without compass-related error; AC-16 (no magnetometer call in console) met.
- **Basis:** analysis.md line 61, main.dart line 209; requirements FR-09, AC-16.
- **Depends on:** T02-04

---

## Slice S2 — drift/WASM Migration

**Goal:** Replace raw `sqflite` with `drift`. Mobile uses `NativeDatabase`; web uses `WasmDatabase` backed by IndexedDB. Existing mobile data is preserved through a schema migration. All three tables (`prayer_tracking`, `tasbih_custom_phrases`, `tasbih_recitation_history`) are migrated.

### [x] T02-06 — Add drift dependencies to `pubspec.yaml` (1 h)
- [ ] Add to `dependencies`: `drift: ^2.x`, `sqlite3_flutter_libs: ^0.x` (mobile native SQLite), `drift_flutter: ^0.x` (provides both `NativeDatabase` and `WasmDatabase` factory).
- [ ] Add to `dev_dependencies`: `drift_dev: ^2.x`, `build_runner: ^2.x`.
- [ ] Remove `sqflite` from `dependencies` (keep `sqflite_common_ffi` in dev for existing migration test fixture).
- [ ] Run `flutter pub get` and confirm no version conflicts.
- **Done-criteria:** `flutter pub get` exits 0; `drift` and `drift_flutter` are in `.dart_tool/package_config.json`.
- **Basis:** decision-log D1; requirements FR-03, NFR-05.
- **Depends on:** T02-05

### [x] T02-07 — Define drift schema and generate DAO code (3 h)
- [ ] Create `lib/data/database/app_database.drift.dart` (or rewrite `app_database.dart`) declaring three drift `Table` classes mirroring the current sqflite schema: `PrayerTracking`, `TasbihCustomPhrases`, `TasbihRecitationHistory` — columns and types must be identical to the existing SQL DDL.
- [ ] Annotate with `@DriftDatabase(tables: [...])` and run `dart run build_runner build --delete-conflicting-outputs` to generate `app_database.g.dart`.
- [ ] Write DAOs (`PrayerTrackingDao`, `TasbihDao`) with typed query methods that match the current method signatures called by `PrayerTrackingService` and `TasbihRecitationRepository` (so callers require minimal changes).
- **Done-criteria:** `build_runner` exits 0; generated file exists; DAO methods match existing call sites by signature.
- **Basis:** analysis.md storage layer section; `app_database.dart` schema (version 2, 3 tables); requirements FR-03.
- **Depends on:** T02-06

### [x] T02-08 — Implement platform-conditional database factory (2 h)
- [ ] In `lib/data/database/app_database.dart` (now a drift `GeneratedDatabase` subclass), add a static factory:
  ```dart
  static AppDatabase open() {
    if (kIsWeb) {
      return AppDatabase(connectOnWeb());  // WasmDatabase via drift_flutter
    }
    return AppDatabase(NativeDatabase.createInBackground(File(path)));
  }
  ```
- [ ] Implement `connectOnWeb()` using `drift_flutter`'s `WasmDatabase.open()` with `dbName: 'noble_salah'` targeting IndexedDB.
- [ ] Update `main.dart` to call `AppDatabase.open()` instead of `AppDatabase.instance`; remove the singleton pattern.
- [ ] Ensure mobile path still compiles and links `sqlite3_flutter_libs`.
- **Done-criteria:** `flutter run -d web-server` opens IndexedDB without error; `flutter build apk --debug` exits 0.
- **Basis:** decision-log D1; requirements FR-03, FR-05, FR-06, AC-06.
- **Depends on:** T02-07

### [x] T02-09 — Update repositories and services to use drift DAOs (2 h)
- [ ] Update `TasbihRecitationRepository` to use `TasbihDao` (drift-generated) instead of raw `Database.rawQuery`/`insert`.
- [ ] Update `PrayerTrackingService` to use `PrayerTrackingDao`.
- [ ] Update `QadaService` and `StreakService` if they access `AppDatabase` directly.
- [ ] Remove all `sqflite` imports from repository/service files.
- **Done-criteria:** All repository unit tests pass (`flutter test`); no sqflite imports remain outside `dev_dependencies`.
- **Basis:** analysis.md — repositories using AppDatabase; requirements FR-03.
- **Depends on:** T02-08

### [x] T02-10 — Schema migration: sqflite v2 → drift (2 h)
- [ ] Implement drift `MigrationStrategy.onUpgrade` to handle existing sqflite databases on mobile: on first open with drift, detect old sqflite DB file and copy its rows into the drift/NativeDatabase tables, then delete the old file.
- [ ] Alternatively: use drift's `from` parameter to attach the existing `noble_salah.db` SQLite file directly (drift can open any SQLite file natively).
- [ ] Write a migration integration test in `test/data/database/app_database_migration_test.dart`: start with a pre-seeded sqflite fixture, run drift migration, assert all rows present in drift DAO queries.
- **Done-criteria:** NFR-05 — migration test passes with zero data loss on a fixture DB seeded with v2 schema rows.
- **Basis:** decision-log D1 "schema migration story still needed"; NFR-05; existing `test/data/database/app_database_migration_test.dart`.
- **Depends on:** T02-09

### [ ] T02-11 — Verify IndexedDB persistence on web (2 h)
- [ ] Run `flutter run -d web-server`.
- [ ] Mark a prayer as complete → confirm IndexedDB entry in DevTools → Application → Storage.
- [ ] Refresh the page → confirm prayer remains marked (AC-04).
- [ ] Increment Tasbih 33 times → navigate away → return → confirm count preserved (AC-05).
- [ ] Run `flutter build web --wasm` and measure gzip transfer size (NFR-06 ≤ 8 MB).
- **Done-criteria:** AC-04, AC-05, AC-06 pass manually; build size recorded and within budget.
- **Basis:** requirements FR-05, FR-06, AC-04, AC-05, AC-06, NFR-06.
- **Depends on:** T02-10

---

## Slice S3 — Plugin Stubs & Feature Gating

**Goal:** All remaining mobile-only UI sections hidden on web. No plugin that lacks a web implementation is ever invoked on web. Settings and Qibla screens branch correctly on `kIsWeb`.

### [x] T02-12 — Gate `WidgetBridgeService` and `home_widget` on web (1 h)
- [ ] In `lib/domain/services/widget_bridge_service.dart`: guard all `HomeWidget.*` calls with `if (!kIsWeb)`. `pushWidgetData()` becomes a no-op on web.
- [ ] In `lib/navigation/app_shell.dart`: guard `widgetBridgeService.pushWidgetData()` call in `initState` and `didChangeAppLifecycleState` with `if (!kIsWeb)` — or rely on the service-level guard.
- [ ] Verify no `home_widget` method channel calls appear in web browser console.
- **Done-criteria:** `flutter run -d web-server` → zero `MissingPluginException` for home_widget; AC-02 (zero uncaught exceptions).
- **Basis:** analysis.md Category C/D; requirements FR-12.
- **Depends on:** T02-05

### [x] T02-13 — Gate notification UI and service on web; add informational banner (2 h)
- [ ] In `lib/features/settings/settings_screen.dart`: wrap the athan notification scheduling section (including `_AthanNavigationCard`, `_TestNotificationCard`, `_TestAlarmCard`) with `if (!kIsWeb)`. Add an `_AthanWebBanner` widget shown only on web: `"Athan notifications are only available in the mobile app."` styled as an info card.
- [ ] In `lib/features/onboarding/onboarding_screen.dart`: skip the notification permission page entirely when `kIsWeb` (page index 1 in the PageView). The onboarding gate will be removed entirely in T02-15, but this guard is a safety net.
- [ ] Verify `NotificationService.initialize()` is never called on web (it is already guarded in T02-03 — add a unit test mock asserting `initialize()` is not invoked when `kIsWeb` is simulated).
- **Done-criteria:** AC-17, AC-18, AC-19 pass; no `flutter_local_notifications` method channel calls in web console.
- **Basis:** decision-log D5; requirements FR-10, AC-17, AC-18, AC-19.
- **Depends on:** T02-12

### [x] T02-14 — Gate battery optimization and Play Store update UI on web (1 h)
- [ ] In `lib/features/settings/settings_screen.dart`: wrap `_BatteryOptimizationBanner` render with `if (!kIsWeb)`. Wrap `_CheckForUpdateCard` section with `if (!kIsWeb)`.
- [ ] Verify no `AndroidBatteryOptimizationAdapter` method channel is invoked on web (the adapter already checks `defaultTargetPlatform != TargetPlatform.android`, which is sufficient on web, but the UI card must also be hidden).
- **Done-criteria:** AC-22 (no battery optimization card on web) and AC-23 (no Play Store update card) pass.
- **Basis:** requirements FR-12, AC-22, AC-23; analysis.md Category D.
- **Depends on:** T02-13

### [x] T02-15 — Skip onboarding on web; add demand-based geolocation (1 h)
- [ ] In `lib/main.dart`: after reading `onboardingComplete`, override to `true` when `kIsWeb` — web users always land on the main shell.
- [ ] In `lib/features/dashboard/dashboard_screen.dart` (or the prayer-times screen): if `locationService.getLastKnown() == null` and `kIsWeb`, show a one-time geolocation permission prompt (browser Geolocation API via `geolocator`).
- [ ] Guard onboarding battery and notification pages with `if (!kIsWeb)` as a belt-and-suspenders measure.
- **Done-criteria:** AC-20 (web goes directly to main shell) and AC-21 (notification/battery onboarding pages never shown on web) pass.
- **Basis:** decision-log D8; requirements FR-11, AC-20, AC-21.
- **Depends on:** T02-14

### [x] T02-16 — Qibla screen static bearing card on web (1 h)
- [ ] In `lib/features/qibla/qibla_screen.dart`: add `kIsWeb` branch in `_QiblaScreenState.build()`. When `kIsWeb`, instead of `_CompassBody`, render `_StaticBearingCard` — a widget showing: numeric bearing in degrees (from `computeQiblaBearing()` using saved location), a compass-rose SVG rotated to that bearing, and label "Direction from your saved location".
- [ ] When no location is saved on web, show `_NoLocationBody` (already exists).
- [ ] Write a widget test asserting `_CompassBody` is not in the tree when `kIsWeb` branch is taken (AC-15).
- **Done-criteria:** AC-14 (static bearing card visible on web), AC-15 (live needle absent — widget test), AC-16 (no FlutterCompass calls) pass.
- **Basis:** decision-log D6; requirements FR-09, AC-14, AC-15, AC-16.
- **Depends on:** T02-05

---

## Slice S4 — UI Polish (PWA + Web Assets)

**Goal:** The web build is an installable PWA with correct manifest, icons, and a service worker that caches the app shell.

### [x] T02-17 — Configure PWA manifest and icons (2 h)
- [ ] Edit `web/manifest.json` (generated by T02-01): set `name: "Noble Salah"`, `short_name: "Noble Salah"`, `theme_color: "#1A3D2B"`, `background_color: "#FFFFFF"`, `display: "standalone"`, `start_url: "./"` (relative).
- [ ] Add 192 px and 512 px PNG icons to `web/icons/` (source: `assets/brand/icon.png` — resize/export). Reference them in `manifest.json` `icons` array.
- [ ] Run `dart run flutter_launcher_icons` if the `pubspec.yaml` `flutter_launcher_icons.web` section already covers this; otherwise generate manually.
- [ ] Verify Chrome DevTools → Application → Manifest shows no errors.
- **Done-criteria:** Manifest valid in DevTools; `start_url` is relative; 192 and 512 px icons present and reachable.
- **Basis:** requirements FR-13, AC-24, AC-25; decision-log D3.
- **Depends on:** T02-01

### [ ] T02-18 — Implement custom service worker for app shell caching (2 h) [RE-OPENED 2026-05-09]
- **Context:** Flutter's generated `flutter_service_worker.js` is a deprecated self-unregistering stub (calls `self.registration.unregister()` on activate, caches nothing). Must be replaced with a real caching service worker. See decision-log Amendment 2026-05-09.
- [ ] Create `web/service_worker.js` using the Cache API. On `install`, pre-cache the app shell asset list: `flutter_bootstrap.js`, `flutter.js`, `main.dart.js`, `manifest.json`, `favicon.png`, `icons/Icon-192.png`, `icons/Icon-512.png`. On `fetch`, serve cache-first for same-origin requests; network-first (pass-through) for CDN audio URLs.
- [ ] In `web/index.html`, register `service_worker.js` via a `<script>` block (standard `navigator.serviceWorker.register('./service_worker.js')`) — do NOT use the deprecated `serviceWorkerSettings` approach in `flutter_bootstrap.js` (it loads the self-unregistering stub).
- [ ] Remove or neutralise the `serviceWorkerSettings` block in `flutter_bootstrap.js` / `index.html` so Flutter does not re-register the deprecated stub over the custom SW.
- [ ] Test offline load in Chrome DevTools: disable network → reload → app shell loads from cache within 2 s (AC-26).
- [ ] Confirm in DevTools → Application → Service Workers that `service_worker.js` shows as active (not the old `flutter_service_worker.js`).
- **Done-criteria:** AC-26 (offline shell load ≤ 2 s) passes; custom `service_worker.js` active in DevTools; NFR-02 (second load TTI ≤ 2 s over Fast 3G) measured and recorded in verification.md.
- **Basis:** requirements FR-13, NFR-01, NFR-02, AC-26; decision-log D3, Amendment 2026-05-09.
- **Depends on:** T02-17

### [x] T02-19 — Configure `base-href` and validate asset paths (1 h)
- [ ] Confirm `flutter build web --base-href /noble-salah/` builds without error and `index.html` references assets at `/noble-salah/`.
- [ ] Confirm no Dart code contains absolute-path string literals for assets.
- [ ] Verify `start_url: "./"` in manifest is relative (already set in T02-17).
- **Done-criteria:** AC-27 (`flutter build web --base-href /noble-salah/` exits 0, asset paths correct).
- **Basis:** requirements FR-14, AC-27; decision-log D2.
- **Depends on:** T02-18

---

## Slice S5 — Build & Deploy

**Goal:** GitHub Actions pipeline builds and deploys to GitHub Pages. CORS for Quran CDN is documented and actioned. Smoke deployment confirms AC-28.

### [x] T02-20 — GitHub Actions web build workflow (2 h)
- [ ] Create `.github/workflows/web-deploy.yml`: trigger on push to `main`; steps: checkout, `flutter pub get`, `flutter test`, `flutter build web --wasm --base-href /noble-salah/`, deploy `build/web/` to `gh-pages` branch using `actions/deploy-pages` or `peaceiris/actions-gh-pages`.
- [ ] Pin Flutter SDK to `stable` channel (≥ 3.22) in the workflow to ensure WASM support (R8 mitigation).
- [ ] Add `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers for WASM SharedArrayBuffer support — configure via GitHub Pages `_headers` file or a custom header step (R10 mitigation).
- **Done-criteria:** Workflow runs on push and produces a successful deploy; Flutter SDK version ≥ 3.22 is pinned.
- **Basis:** requirements FR-14, AC-27, AC-28; risk R8, R10.
- **Depends on:** T02-19

### [ ] T02-21 — Quran audio CDN CORS configuration (1 h, non-code action)
- [ ] Document the required CORS allow-list for the Quran audio CDN: `Access-Control-Allow-Origin: https://<owner>.github.io` and `http://localhost:*`.
- [ ] File or action the CORS update with whoever controls the CDN. If self-hosted (e.g. an S3 bucket or Cloudflare), apply the config directly.
- [ ] Verify with `curl -H "Origin: https://<owner>.github.io" -I <cdn-audio-url>` that the response includes the correct `Access-Control-Allow-Origin` header.
- **Done-criteria:** CDN responds with correct CORS header for the GH Pages origin; AC-11 can now pass end-to-end.
- **Basis:** decision-log D2 "CDN CORS update is an external (non-code) task"; requirements FR-07, AC-11; risk R5.
- **Depends on:** T02-20

### [ ] T02-22 — Smoke deploy and 404 check (2 h)
- [ ] After first successful GitHub Actions deploy, open the GH Pages URL in Chrome, Edge, Firefox, and Safari.
- [ ] Confirm no 404s for JS, CSS, icon assets (AC-28).
- [ ] Confirm PWA install prompt appears in Chrome (AC-24).
- [ ] Record Lighthouse PWA score (target ≥ 90, AC-25) and initial load TTI on Fast 3G (NFR-01 ≤ 8 s).
- **Done-criteria:** AC-24, AC-25, AC-28 pass; NFR-01 TTI recorded.
- **Basis:** requirements FR-13, FR-14, AC-24, AC-25, AC-28, NFR-01.
- **Depends on:** T02-21

---

## Slice S6 — Verification

**Goal:** Full browser testing matrix, regression check on Android. All 28 ACs verified with evidence.

### [ ] T02-23 — Core navigation and feature smoke test (web) (2 h)
- [ ] In Chrome: navigate Prayer Times → Quran → Qibla → Dhikr → Tasbih → Settings. Zero uncaught exceptions in console (AC-02).
- [ ] Verify prayer times display within 3 s (AC-09).
- [ ] Verify Quran reader opens Surah Al-Fatiha (AC-10).
- [ ] Verify Quran audio plays ≥ 5 s from CDN without error (AC-11) — requires T02-21 CORS complete.
- [ ] Verify Adhkar screen renders all categories; TTS button does not crash (AC-12).
- [ ] Verify Tasbih counter increments and resets (AC-13).
- **Done-criteria:** AC-02, AC-09, AC-10, AC-11, AC-12, AC-13 pass in Chrome; evidence logged in T02-verification.md.
- **Basis:** requirements AC-02, AC-09–AC-13.
- **Depends on:** T02-22

### [ ] T02-24 — Platform guard and persistence verification (1 h)
- [ ] Run `grep -rn "Platform\." lib/` — assert zero bare calls (AC-07).
- [ ] Manually verify `notification_service.dart`, `onboarding_screen.dart`, `settings_screen.dart` have no bare `dart:io` Platform calls (AC-08).
- [ ] Verify AC-04 (prayer tracking persists on refresh) and AC-05 (tasbih history persists) in Chrome.
- [ ] Open DevTools → IndexedDB → confirm `noble_salah` database entry exists (AC-06).
- **Done-criteria:** AC-04, AC-05, AC-06, AC-07, AC-08 pass; evidence in verification.md.
- **Basis:** requirements FR-02, FR-05, FR-06, AC-04–AC-08.
- **Depends on:** T02-23

### [ ] T02-25 — Feature gating verification (1 h)
- [ ] Web: confirm Qibla tab shows static bearing card + compass-rose SVG (AC-14); confirm no live needle (AC-15); confirm no FlutterCompass calls in console (AC-16).
- [ ] Web: confirm athan notification scheduling section is hidden (AC-17); info banner "Athan notifications are only available in the mobile app" is visible (AC-18).
- [ ] Web: confirm no battery optimization card (AC-22) and no Play Store update card (AC-23) in Settings.
- [ ] Web: confirm first load goes directly to main shell (AC-20); onboarding notification/battery pages never shown (AC-21).
- **Done-criteria:** AC-14–AC-18, AC-20–AC-23 pass; evidence in verification.md.
- **Basis:** requirements FR-09–FR-12, D5, D6, D8.
- **Depends on:** T02-24

### [ ] T02-26 — Cross-browser and mobile regression (2 h)
- [ ] Repeat AC-02, AC-09, AC-10, AC-12, AC-13 in Edge ≥ 110 and Firefox ≥ 115 (NFR-07).
- [ ] Test AC-01 (`flutter run -d web-server` non-blank in Chrome within 15 s) — confirm on development machine.
- [ ] Run `flutter build apk --debug` — assert exit 0, zero new errors or warnings (AC-03, NFR-04).
- [ ] Run drift migration integration test — assert no data loss (NFR-05).
- [ ] Record WASM build size (NFR-06 ≤ 8 MB gzip).
- **Done-criteria:** AC-01, AC-03, NFR-04, NFR-05, NFR-06, NFR-07 pass; all evidence logged.
- **Basis:** requirements AC-01, AC-03, NFR-04–NFR-07.
- **Depends on:** T02-25

---

## Effort Summary

| Task | Hours | AC Coverage |
|------|-------|-------------|
| T02-01 — Enable Flutter web target | 1 h | AC-01 (partial) |
| T02-02 — Guard JustAudioBackground / AudioSession | 1 h | AC-01, AC-02 |
| T02-03 — Guard HomeWidget / notifications / scheduler / battery | 1 h | AC-01, AC-02 |
| T02-04 — Replace dart:io Platform.* calls | 2 h | AC-07, AC-08 |
| T02-05 — WebNoOpCompassPlugin stub | 1 h | AC-16 |
| T02-06 — Add drift dependencies | 1 h | FR-03 (setup) |
| T02-07 — Define drift schema and generate DAOs | 3 h | FR-03 |
| T02-08 — Platform-conditional database factory | 2 h | AC-04, AC-05, AC-06 |
| T02-09 — Update repositories to drift DAOs | 2 h | FR-03, FR-05, FR-06 |
| T02-10 — Schema migration sqflite v2 → drift | 2 h | NFR-05 |
| T02-11 — Verify IndexedDB persistence | 2 h | AC-04, AC-05, AC-06 |
| T02-12 — Gate WidgetBridgeService / home_widget | 1 h | AC-02 |
| T02-13 — Gate notification UI + info banner | 2 h | AC-17, AC-18, AC-19 |
| T02-14 — Gate battery opt + Play Store UI | 1 h | AC-22, AC-23 |
| T02-15 — Skip onboarding on web | 1 h | AC-20, AC-21 |
| T02-16 — Qibla static bearing card | 1 h | AC-14, AC-15, AC-16 |
| T02-17 — PWA manifest and icons | 2 h | AC-24, AC-25 |
| T02-18 — Service worker for app shell caching | 2 h | AC-26, NFR-01, NFR-02 |
| T02-19 — base-href and asset paths | 1 h | AC-27 |
| T02-20 — GitHub Actions web build workflow | 2 h | AC-27, AC-28 |
| T02-21 — CDN CORS configuration | 1 h | AC-11 |
| T02-22 — Smoke deploy and 404 check | 2 h | AC-24, AC-25, AC-28 |
| T02-23 — Core navigation smoke test | 2 h | AC-02, AC-09–AC-13 |
| T02-24 — Platform guard + persistence verification | 1 h | AC-04–AC-08 |
| T02-25 — Feature gating verification | 1 h | AC-14–AC-18, AC-20–AC-23 |
| T02-26 — Cross-browser + mobile regression | 2 h | AC-01, AC-03, NFR-04–NFR-07 |
| **Total** | **42 h** | All 28 ACs covered |

---

## Acceptance Criterion Coverage

| AC | Covered by |
|----|-----------|
| AC-01 | T02-02, T02-26 |
| AC-02 | T02-02, T02-03, T02-12, T02-23 |
| AC-03 | T02-04, T02-26 |
| AC-04 | T02-08, T02-11, T02-24 |
| AC-05 | T02-08, T02-11, T02-24 |
| AC-06 | T02-08, T02-11, T02-24 |
| AC-07 | T02-04, T02-24 |
| AC-08 | T02-04, T02-24 |
| AC-09 | T02-23 |
| AC-10 | T02-23 |
| AC-11 | T02-21, T02-23 |
| AC-12 | T02-23 |
| AC-13 | T02-23 |
| AC-14 | T02-16, T02-25 |
| AC-15 | T02-16, T02-25 |
| AC-16 | T02-05, T02-16, T02-25 |
| AC-17 | T02-13, T02-25 |
| AC-18 | T02-13, T02-25 |
| AC-19 | T02-13, T02-25 |
| AC-20 | T02-15, T02-25 |
| AC-21 | T02-13, T02-15, T02-25 |
| AC-22 | T02-14, T02-25 |
| AC-23 | T02-14, T02-25 |
| AC-24 | T02-17, T02-22 |
| AC-25 | T02-17, T02-22 |
| AC-26 | T02-18 |
| AC-27 | T02-19, T02-20 |
| AC-28 | T02-20, T02-22 |

---

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| R1 — `dart:io Platform.*` throws `UnsupportedError` before `runApp()` (root cause of blank page) | High | High | T02-04 replaces all bare Platform.* calls; AC-07 grep enforced in CI | Builder |
| R2 — `try/catch` around `JustAudioBackground.init()` does not catch on web dart2js | High | High | T02-02 wraps with explicit `if (!kIsWeb)` guard before try/catch | Builder |
| R3 — drift/WASM migration corrupts existing mobile SQLite data | Med | High | T02-10 migration integration test with pre-seeded fixture; NFR-05 gates CI | Builder |
| R4 — sqlite3.wasm + Flutter WASM exceeds 8 MB gzip NFR-06 budget | Med | High | T02-11 measures size early; mitigate with deferred WASM loading or lazy sqlite3.wasm if over budget | Builder |
| R5 — Quran audio CDN CORS not allowlisted before verification (external dependency) | Med | High | T02-21 documents and actions CORS update before S6; CDN verified with curl; if unresolved, AC-11 flagged as external blocker | anjum |
| R6 — `AndroidBatteryOptimizationAdapter()` construction crashes on web before platform check | High | Med | T02-03 wraps `batteryOptimizationService.checkStatus()` with `if (!kIsWeb)`; adapter's internal `defaultTargetPlatform` check is a second defence | Builder |
| R7 — `FlutterCompassAdapter()` construction throws on web (not just `.events`) | Med | Med | T02-05 replaces construction with `WebNoOpCompassPlugin()` on web — adapter never instantiated on web | Builder |
| R8 — GitHub Actions runner has Flutter SDK < 3.22 (no WASM support) | Low | High | T02-20 pins Flutter SDK channel to `stable` with explicit version ≥ 3.22 | Builder |
| R9 — Mobile regression from drift migration wipes existing user data | Low | High | T02-10 drift migration preserves existing SQLite file; integration test asserts row-level data preserved | Builder |
| R10 — Firefox/Safari WASM requires COOP/COEP headers; GH Pages doesn't set them by default | Med | Med | T02-20 adds `_headers` file or header-injection step in deploy workflow; Flutter 3.22+ sets them in `flutter run` automatically | Builder |

---

## Dependencies

- **Blocks:** T03 (future: Web Push athan notifications) — depends on this ticket completing S5 deploy.
- **Blocked by:** Quran audio CDN CORS allowlist (external, non-code — T02-21). If CORS remains unresolved, AC-11 cannot pass but all other ACs can.

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
