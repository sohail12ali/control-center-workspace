---
ticket: "T02"
artifact: analysis
stage: GROUND
---

# Analysis: T02 — Make Noble Salah a Real Flutter Web Target

## Context

Noble Salah is a Flutter prayer-time app (v1.0.10+12) currently targeting Android and iOS. The developer wants `flutter build web` to produce a fully working product, not a stub. A web-server build already starts but renders a blank page because `main()` throws before `runApp()` on unguarded mobile-only platform calls.

Source: `D:/Workspace/noble-wave/noble-salah/`

---

## Current State

- `flutter run -d web-server` starts; HTTP assets all return 200.
- Blank page at runtime — one or more of the calls below throws in a web `dart2js` context before `runApp()` is reached.
- `kIsWeb` guard exists in exactly 2 files (`tasbih_service.dart` import path, `battery_optimization_service.dart` adapter) — `main.dart` has none.
- The app uses a **NavigationRail breakpoint at 840 px** already in `app_shell.dart`, so some responsive-layout groundwork exists.

---

## Plugin / Dependency Web-Compatibility Audit

All dependencies from `pubspec.yaml` are classified below.

### Category A — Native web support (works on web with no changes)

| Package | Notes |
|---|---|
| `shared_preferences` | Uses `localStorage` on web; full support |
| `provider` | Pure Dart; full support |
| `intl` | Pure Dart; full support |
| `adhan_dart` | Pure Dart calculation; no platform channels |
| `timezone` | Pure Dart; full support |
| `url_launcher` | Web support via `window.open`; full support |
| `flutter_svg` | Full web canvas support |
| `flutter_localizations` | Flutter SDK; full support |
| `path` | Pure Dart; full support |

### Category B — Has web support / web-capable variant

| Package | Web story | Action needed |
|---|---|---|
| `geolocator` | Web support via Geolocation API; already published | Add web permission prompt wording; falls through to browser permission dialog |
| `just_audio` | `just_audio_web` is a peer dep that activates automatically on web; streams audio from URL (CDN) | Quran player should work; no bundled audio assets needed |
| `flutter_tts` | Has web support via Web Speech API (`speechSynthesis`) since v3.x | Works if Arabic voice available in browser; already has `try/catch` guard in both call sites |

### Category C — Mobile-only; needs `kIsWeb` stub / skip

| Package | Why it fails on web | Recommended approach |
|---|---|---|
| `sqflite` | Uses SQLite native library; **no web support**. `getDatabasesPath()` throws at runtime. | Replace with `sqflite_common_ffi_web` + `sembast_web` or use `drift` with `drift/wasm`. Alternatively stub the repository layer behind an interface and use an in-memory implementation on web for v1. |
| `just_audio_background` | Uses Android foreground service / iOS background mode; no web impl | Guard `JustAudioBackground.init()` with `if (!kIsWeb)` — already in a try/catch but the web dart2js runtime throws in a way that escapes the catch; needs explicit guard |
| `audio_session` | No web support; `AudioSession.instance` returns a channel error on web | Guard with `if (!kIsWeb)` |
| `home_widget` | iOS/Android home-screen widgets; no web concept | Guard with `if (!kIsWeb)` in `main.dart` and `WidgetBridgeService` |
| `flutter_local_notifications` | Uses native notification channels; web notifications API not supported by this package | Guard entire `NotificationService.initialize()` path; on web the service becomes a no-op |
| `flutter_compass` | Uses device magnetometer sensor; `FlutterCompass.events` returns null on web | `FlutterCompassAdapter.events` already handles null stream gracefully; but `FlutterCompassAdapter()` construction itself may fail — wrap in `kIsWeb` guard; on web return `Stream.empty()` |
| `in_app_update` | Google Play API; no web | `AppUpdateService` already swallows errors; guard at construction with `kIsWeb` so `PlayStoreUpdateChecker` is never called |

### Category D — Mobile-only; hide feature entirely on web

| Package / Feature | Reasoning |
|---|---|
| `home_widget` (HomeWidget.setAppGroupId, WidgetBridgeService.pushWidgetData) | Home-screen widgets are not a browser concept; hide silently |
| `flutter_local_notifications` / `PrayerSchedulerService` | Background push notifications require OS integration not available on web; show "notifications not available on web" UI badge; do not schedule |
| `in_app_update` | Play Store update flow meaningless on web; entire card hidden |
| Battery optimization prompt | Android-only; already has `defaultTargetPlatform != TargetPlatform.android` guard in adapter, but `AndroidBatteryOptimizationAdapter` may crash on web before that check |
| Onboarding notification + battery pages | Guard pages with `kIsWeb`; skip them on web |

---

## Call-Site Analysis in `main.dart`

The following calls in `main()` must be guarded or replaced:

| Line | Call | Fix |
|---|---|---|
| 166 | `JustAudioBackground.init(...)` | Wrap with `if (!kIsWeb)` (already in try/catch but try/catch is insufficient on web) |
| 178–179 | `AudioSession.instance` / `.configure(...)` | Wrap with `if (!kIsWeb)` |
| 182 | `HomeWidget.setAppGroupId(...)` | Wrap with `if (!kIsWeb)` |
| 209 | `FlutterCompassAdapter()` → passed to `QiblaService` | On web substitute `_WebCompassPlugin()` that emits `Stream.empty()` |
| 212–215 | `AppDatabase.instance` / `tasbihRecitationRepository` / `tasbihService.init()` | Replace `AppDatabase` with interface; provide `WebNoOpDatabase` on web, or use `sembast_web` |
| 233–234 | `AndroidBatteryOptimizationAdapter()` | On web substitute `_WebNoOpBatteryPlugin()` (returns null) — already has partial guard in adapter |
| 239–240 | `notificationService.initialize(...)` | Wrap with `if (!kIsWeb)` (no-op on web) |
| 255 | `prayerSchedulerService.initialize()` | Wrap with `if (!kIsWeb)` |
| 258 | `batteryOptimizationService.checkStatus()` | Wrap with `if (!kIsWeb)` |

---

## Storage Layer (`AppDatabase`) — Web Story

`AppDatabase` is a thin hand-rolled sqflite wrapper. Schema has 3 tables:
- `prayer_tracking` — used by `PrayerTrackingService`
- `tasbih_custom_phrases` — used by `TasbihService`
- `tasbih_recitation_history` — used by `TasbihService`

**Options:**
1. **Stub (v1 web)** — Introduce `AbstractDatabase` interface; on web provide an in-memory implementation. Prayer tracking and tasbih history won't persist across page refresh, but all UI flows will work.
2. **Drift/WASM (full persistence)** — Migrate `AppDatabase` to `drift` with `WasmDatabase` backend. Adds significant migration complexity.
3. **sembast_web** — Key-value store that works on web via IndexedDB. Requires rewriting queries.

Recommended for v1: Option 1 (in-memory stub) to unblock web rendering; option 2 can be a v2 task.

---

## Feature Map: Web vs Mobile

| Feature | On Web | Notes |
|---|---|---|
| Prayer times (dashboard) | Yes | Pure Dart calculation; fully web-capable |
| Hijri calendar | Yes | Pure Dart |
| Qibla compass | Partial | Bearing computation works; magnetometer unavailable in browser — show static bearing with geolocation |
| Quran reader | Yes | Asset-based; fully works |
| Quran audio player | Yes | just_audio + CDN streaming; works on web |
| Dhikr / Adhkar | Yes | Content-only; flutter_tts has Web Speech API support |
| Tasbih counter | Yes (no history persistence in v1) | If using in-memory DB stub |
| Prayer tracking | Yes (no persistence across refresh in v1) | Same DB stub caveat |
| Athan notifications | No — hide on web | flutter_local_notifications has no web impl |
| Home-screen widgets | No — skip silently | Not a browser concept |
| Battery optimization prompt | No — hide on web | Android-only |
| App update (Play Store) | No — hide on web | Android-only |
| Onboarding notification / battery pages | Skip on web | Guard with kIsWeb |

---

## `Platform.isAndroid` Usage — Critical Risk

`notification_service.dart` and `onboarding_screen.dart` both call `Platform.isAndroid` directly. On Flutter Web, `dart:io`'s `Platform` class throws `UnsupportedError`. These must be replaced with:
```dart
import 'package:flutter/foundation.dart';
defaultTargetPlatform == TargetPlatform.android
// OR
!kIsWeb && Platform.isAndroid
```

Files affected:
- `lib/domain/services/notification_service.dart` (lines 93, 99, 116, 179, 186)
- `lib/features/onboarding/onboarding_screen.dart` (lines 946, 1034)
- `lib/features/settings/settings_screen.dart` (line 1366 — `_openPlayStore`)

---

## Recommended Path

**Phase 1 — Unblock web (make it render)**
1. Add `import 'package:flutter/foundation.dart' show kIsWeb;` to `main.dart`.
2. Guard all 8 mobile-only calls in `main()` with `if (!kIsWeb)`.
3. Replace all `Platform.isAndroid` / `Platform.isIOS` with `kIsWeb`-safe equivalents across 3 files.
4. Introduce `AbstractDatabase` / `WebNoOpDatabase` so `AppDatabase.instance` is never called on web.
5. Supply `_WebNoOpBatteryPlugin` and a web-compatible `CompassPlugin` stub.

**Phase 2 — Web-quality features**
6. Qibla screen: show static bearing card when magnetometer unavailable (already handles null stream; just needs UI copy).
7. Settings: hide battery optimization, app update, athan scheduling sections on web.
8. Onboarding: skip battery optimization and notification permission pages on web.
9. Notifications: add "notifications unavailable on web" informational card in settings.

**Phase 3 — Persistence (optional v1 or v2)**
10. Migrate `AppDatabase` to drift/WASM for full IndexedDB persistence on web.

---

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
