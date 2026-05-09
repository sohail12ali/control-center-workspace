---
ticket: "T02"
artifact: requirements
stage: CLARIFY
status: frozen
frozen: 2026-05-09
---

# Requirements: T02 — Make Noble Salah a Real Flutter Web Target

## Functional Requirements

### FR-01 Bootstrap — Web renders without blank page
`flutter run -d web-server` and `flutter build web` must produce a running SPA that reaches `runApp()` without throwing. All mobile-only calls in `main()` must be guarded with `if (!kIsWeb)` or replaced with web-safe stubs before `runApp()` is called. Single entry point `lib/main.dart` is kept — no separate `main_web.dart` (D7).

### FR-02 `dart:io` Platform references eliminated
Every direct call to `dart:io`'s `Platform.isAndroid`, `Platform.isIOS`, or any other `dart:io` Platform member must be replaced with `kIsWeb`-safe equivalents (`kIsWeb`, `defaultTargetPlatform`). Affected files at minimum: `notification_service.dart`, `onboarding_screen.dart`, `settings_screen.dart`.

### FR-03 Storage — drift/WASM with durable IndexedDB persistence (D1)
`AppDatabase` is migrated from raw `sqflite` to `drift`. Mobile uses `drift` with the native SQLite backend (`drift_sqflite` / `NativeDatabase`). Web uses `drift` with the WASM backend (`WasmDatabase` / IndexedDB). The Dart-level DAO API is identical on both platforms. Three tables are preserved: `prayer_tracking`, `tasbih_custom_phrases`, `tasbih_recitation_history`. A drift schema migration is provided so existing mobile users' data is preserved.

### FR-04 Prayer-times dashboard works on web
The prayer-times screen loads, calculates, and displays today's prayer times using saved or browser-provided geolocation. Pure-Dart `adhan_dart` calculation is used unchanged.

### FR-05 Prayer tracking persists across page refresh (D1)
A user who marks a prayer as complete, then refreshes the page, sees the same marked state. Data is stored in IndexedDB via drift/WASM.

### FR-06 Tasbih history persists across page refresh (D1)
Recitation history recorded in the Tasbih counter survives a page refresh. Data is stored in IndexedDB via drift/WASM.

### FR-07 Quran reader and audio player work on web
The Quran reader (asset-based) renders correctly. The Quran audio player streams from the CDN using `just_audio_web`. The CDN CORS policy allows the GitHub Pages origin and `localhost:*` (D2).

### FR-08 Dhikr / Adhkar works on web
The Adhkar screen renders. Text-to-speech (flutter_tts via Web Speech API) attempts playback; if the browser lacks an Arabic voice, the feature degrades silently (no crash) — existing `try/catch` guards are verified sufficient.

### FR-09 Qibla tab — static bearing card on web (D6)
On web the Qibla tab remains visible. The live compass needle is hidden. A static bearing card is shown displaying: the great-circle bearing in degrees, a fixed compass-rose SVG oriented to that bearing, and a label "Direction from your saved location". `QiblaService.compassStream()` returns `Stream.empty()` on web. No magnetometer access is attempted.

### FR-10 Athan notifications hidden on web (D5)
On web, the notification scheduling section in Settings is replaced by an informational banner: "Athan notifications are only available in the mobile app." `NotificationService.initialize()` is a no-op on web. `PrayerSchedulerService.initialize()` is not called on web. No `flutter_local_notifications` code path is reached on web.

### FR-11 Onboarding skipped on web; geolocation requested on demand (D8)
When `kIsWeb` is true, `app_shell.dart` bypasses the 4-page onboarding gate entirely. The user lands directly on the main shell. Geolocation permission is requested on demand at first feature touch (e.g. opening the prayer-times screen). Prayer calculation method defaults to a sensible preset; the user can change it in Settings.

### FR-12 Mobile-only UI sections hidden on web
The following UI sections are hidden (`kIsWeb` guard) and do not appear in the web build:
- Battery optimization prompt / card
- App update (Play Store) card
- Home-screen widget bridge (silently no-op)
- Onboarding notification permission page
- Onboarding battery optimization page

### FR-13 PWA manifest and service worker (D3)
The web build includes a valid `manifest.json` (name, short_name, theme_color, background_color, display: standalone, icons at 192 px and 512 px, `start_url` relative). A service worker caches the app shell for offline loading. The app is installable from supported browsers (Chrome, Edge).

### FR-14 GitHub Pages deployment compatibility (D2)
`flutter build web --base-href /noble-salah/` (or the actual GH Pages subpath) produces a build that loads correctly at that subpath. `start_url` in `manifest.json` is relative. No absolute-path assumptions in the Dart code.

### FR-15 No auth, no cloud sync (D4)
The web build is fully local-first. No authentication, no cloud sync, no telemetry added beyond what the existing mobile build already contains.

---

## Non-Functional Requirements

### NFR-01 Initial load time
Time-to-interactive on a desktop browser over a simulated Fast 3G connection (Chrome DevTools): ≤ 8 seconds on first load (no cache). Measured with Lighthouse or DevTools Network throttle.

### NFR-02 Service worker cache hit
On second load (service worker active, app shell cached): time-to-interactive ≤ 2 seconds over Fast 3G.

### NFR-03 No console errors on web
`flutter run -d web-server` produces zero uncaught JavaScript exceptions in the browser console for the core navigation flow (prayer times → Quran → Qibla → Dhikr → Tasbih → Settings).

### NFR-04 Mobile build regression-free
`flutter build apk --debug` continues to succeed with zero new errors or warnings introduced by this ticket's changes. Existing Android behaviour is unchanged.

### NFR-05 Drift schema migration correctness
After upgrading from sqflite to drift on mobile, an existing database (schema version N) is migrated to the drift schema without data loss. Migration is covered by at least one integration test.

### NFR-06 WASM build size
`flutter build web --wasm` total transfer size (gzipped) for the initial load must not exceed 8 MB (excluding audio assets streamed from CDN on demand).

### NFR-07 Browser support
The web target must function correctly in: Chrome ≥ 110, Edge ≥ 110, Firefox ≥ 115, Safari ≥ 16.4. WASM is supported across all four; IndexedDB is supported across all four.

---

## Acceptance Criteria

### Bootstrap
- [ ] AC-01: `flutter run -d web-server` starts and the app shell renders (non-blank) in Chrome within 15 seconds on a development machine.
- [ ] AC-02: Browser console shows zero uncaught exceptions during the startup sequence and during navigation through all main tabs.
- [ ] AC-03: `flutter build apk --debug` exits with code 0 and zero new errors after all T02 changes are applied.

### Storage / Persistence (D1)
- [ ] AC-04: User marks Fajr prayer as complete on web, refreshes the page — Fajr remains marked.
- [ ] AC-05: User increments the Tasbih counter 33 times and navigates away, then returns — count and history are preserved.
- [ ] AC-06: IndexedDB entry is visible in browser DevTools → Application → Storage → IndexedDB after first prayer-time page load.

### Platform guards / dart:io (FR-02)
- [ ] AC-07: `grep -rn "Platform\." lib/` returns zero occurrences that are not behind a `!kIsWeb` guard or wrapped in `defaultTargetPlatform` check (automated grep in CI).
- [ ] AC-08: `notification_service.dart`, `onboarding_screen.dart`, `settings_screen.dart` contain no bare `dart:io` Platform calls.

### Feature parity
- [ ] AC-09: Prayer-times dashboard displays today's 5 prayer times on web within 3 seconds of the page becoming interactive.
- [ ] AC-10: Quran reader opens Surah Al-Fatiha on web without error.
- [ ] AC-11: Quran audio player plays at least 5 seconds of audio from the CDN without buffering error in the browser console.
- [ ] AC-12: Adhkar screen renders all categories without error; TTS play button does not crash (graceful no-op if no Arabic voice).
- [ ] AC-13: Tasbih counter increments and resets correctly on web.

### Qibla (D6)
- [ ] AC-14: On web, the Qibla tab is visible and shows a static bearing card with a numeric degree value and a compass-rose SVG.
- [ ] AC-15: The live compass needle widget is not rendered on web (`kIsWeb` branch confirmed by widget test).
- [ ] AC-16: No `FlutterCompass` or magnetometer API call appears in the browser console network or JS error log.

### Notifications (D5)
- [ ] AC-17: On web, the Settings screen does not show the athan notification scheduling section.
- [ ] AC-18: On web, an informational banner reading "Athan notifications are only available in the mobile app" is visible in the Settings area where notification scheduling would otherwise appear.
- [ ] AC-19: `NotificationService.initialize()` is never called on web (verified by unit test mock).

### Onboarding (D8)
- [ ] AC-20: On web, navigating to the app for the first time goes directly to the main shell, not the onboarding flow.
- [ ] AC-21: The onboarding notification permission page and battery optimization page are never shown on web.

### Hidden mobile-only UI (FR-12)
- [ ] AC-22: Battery optimization card does not appear anywhere in the web build's Settings screen.
- [ ] AC-23: Play Store update card does not appear in the web build.

### PWA (D3)
- [ ] AC-24: Chrome's address bar shows the install (PWA) prompt when visiting the deployed GitHub Pages URL.
- [ ] AC-25: Lighthouse PWA audit score ≥ 90 on the production build.
- [ ] AC-26: App loads from service worker cache (offline mode) and shows the shell within 2 seconds when network is disabled in DevTools.

### GitHub Pages deployment (D2)
- [ ] AC-27: `flutter build web --base-href /noble-salah/` completes without error and the built `index.html` references assets at the correct subpath.
- [ ] AC-28: The deployed build loads without 404s for JS, CSS, or icon assets.

---

## Out of Scope

- **Web Push / athan notifications on web** — explicitly excluded (D5). Future ticket.
- **Multi-device / cloud sync** — explicitly excluded (D4). Future ticket.
- **Live Qibla compass needle on web** — magnetometer not available in browsers (D6). Future ticket if Web Bluetooth or similar becomes viable.
- **iOS Safari PWA install flow** — behaviour is Safari-specific and not a v1 requirement; documented as known limitation.
- **Separate `main_web.dart` entry point** — single `main.dart` with `kIsWeb` guards only (D7).
- **App update / Play Store flow on web** — hidden entirely (FR-12).
- **Home-screen widget on web** — no browser equivalent; silently no-op (FR-12).
- **Auth, accounts, or cloud backend of any kind** (D4).
- **In-app purchase or subscription on web** — not present in the app today; remains out of scope.

---

## Open Questions

None. All 8 CLARIFY questions resolved as D1–D8 (see [[T02-decision-log]]).

---

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
