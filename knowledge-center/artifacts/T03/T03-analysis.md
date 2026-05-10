---
ticket: "T03"
artifact: analysis
---

# Analysis: T03 — Setup Maestro-based testing

## Context

Noble Salah is a Flutter-based Islamic utility app (prayer times, Quran reader, Tasbih counter, Qibla compass, Dhikr, Dua, and Tools hub) published for Android and iOS, now also targeting Flutter web (T02, currently in VERIFY). The app reached v1.0.10+12 with a substantial unit/service test suite (30+ test files) but has zero end-to-end UI automation. Maestro is being added to close that gap — it provides black-box mobile UI testing via declarative YAML flows that run against the compiled app on real or emulated devices. The scope here is the Android and iOS native builds; web is out of scope for Maestro (Maestro targets mobile apps, not browsers). T02's web work has introduced kIsWeb guards and onboarding-skip logic that simplify Maestro's entry path on mobile.

## Current State

### Test infrastructure

- `test/` exists at `D:/Workspace/noble-wave/noble-salah/test/` with 30+ unit/service test files organised under `core/`, `data/`, `domain/`, and `features/` subdirectories. The single widget test at `test/widget_test.dart:11` is a placeholder stub that asserts `true`.
- `integration_test/` does **not exist** — confirmed absent from the project root. No Flutter integration test infrastructure has been established.
- `pubspec.yaml:58-60` lists only `flutter_test` and `flutter_lints` as dev dependencies. No `integration_test`, `patrol`, `flutter_driver`, or maestro-related packages are present.
- No `maestro/` directory or `.maestro/` config exists anywhere in the project — confirmed by filesystem search.

### Key screens and flows

Navigation is a flat 5-tab `NavigationBar` (mobile) / `NavigationRail` (tablet ≥ 840 dp), defined at `lib/navigation/app_shell.dart:69-75`. Tabs map to:

| Index | Screen class | File |
|-------|-------------|------|
| 0 | `DashboardScreen` | `lib/features/dashboard/dashboard_screen.dart` |
| 1 | `QuranScreen` | `lib/features/quran/quran_screen.dart` |
| 2 | `DuaScreen` | `lib/features/dua/dua_screen.dart` |
| 3 | `ToolsScreen` | `lib/features/tools/tools_screen.dart` |
| 4 | `SettingsScreen` | `lib/features/settings/settings_screen.dart` |

Secondary screens reached via push navigation (not tabs):

- `TasbihScreen` — reached from Dashboard card and Tools grid (`lib/features/tasbih/tasbih_screen.dart`)
- `QiblaScreen` — reached from Tools grid (`lib/features/qibla/qibla_screen.dart`)
- `DhikrScreen` — reached from Tools or Dua tab (`lib/features/dhikr/dhikr_screen.dart`)
- `OnboardingScreen` — shown on first launch only (`lib/features/onboarding/onboarding_screen.dart`); skipped when `kOnboardingCompleteKey` SharedPreferences flag is `true` (`lib/main.dart:327`)
- `MonthlyTableScreen`, `IslamicCalendarScreen`, `SalahGuideScreen`, `WuduScreen`, `RamadanCalendarScreen`, `QadaCounterScreen`, `AsmaUlHusnaScreen`, `AdhkarRoutineScreen` — all reachable from Tools grid (`lib/features/tools/tools_screen.dart`)
- `AlarmSettingsScreen`, `AboutScreen`, `PrivacyScreen` — reachable from Settings
- `CitySearchScreen` — reachable from Dashboard location widget and Settings

### Entry point and navigation structure

`lib/main.dart:178` is the entry point. `MyApp.build()` at line 499-501 routes to `OnboardingScreen` or `AppShell` based on the `onboardingComplete` boolean. `AppShell` is stateful and manages the selected tab index with `setState`; there is no named-route or go_router infrastructure — all secondary navigation uses `Navigator.push` with `MaterialPageRoute`.

### CI configuration

`.github/workflows/web-deploy.yml` is the only workflow. It runs `flutter test` (unit tests only) and then builds the WASM web bundle for GitHub Pages deployment. There is no mobile CI (no Android/iOS build, no test-on-device step, no Maestro cloud job).

## Key Findings

- **No Maestro baseline exists.** No `maestro/` directory, no `.maestro` config, no `mobile.dev` CLI references anywhere in the codebase. The first task is pure greenfield setup.

- **Onboarding is the critical flow gate.** Every Maestro test session will face `OnboardingScreen` unless the SharedPreferences key `noble_salah.onboarding_complete` is pre-seeded. Maestro's `copyTextFrom` / `inputText` alone cannot write SharedPreferences; a dedicated `launchApp` `arguments` map or a pre-seed helper script will be needed. Alternatively, the onboarding flow itself should be the first Maestro flow tested (walk through all 4-6 pages to completion).

- **Permission dialogs are unavoidable on first run.** Onboarding requests location (`geolocator`, `lib/features/onboarding/onboarding_screen.dart:78`) and notifications (`flutter_local_notifications`, `lib/features/onboarding/onboarding_screen.dart:~120`). On Android, Maestro can handle system permission dialogs with `tapOn: "Allow"` or `tapOn: "While using the app"`. On iOS, Maestro uses `runFlow` + `allowPermissions` or `tapOn` matching the system alert button text. Both platforms require explicit handling in the onboarding flow YAML.

- **Semantic labels are sparse.** Only 8 `Semantics(` call sites exist across the entire `lib/` tree. Labels found:
  - Navigation bar destinations use `Semantics(label: d.label, ...)` via the localized `localizations.dashboard`, `localizations.quran`, etc. (`lib/navigation/app_shell.dart:139,208`) — these are the most reliable Maestro tap targets.
  - `lib/features/islamic_calendar/islamic_calendar_screen.dart:185,217` — previous/next month buttons carry `semanticLabel`.
  - `lib/features/settings/settings_screen.dart:918,926` — gender radio tiles have `Semantics(label: ...)`.
  - `lib/features/settings/settings_screen.dart:1444` — update-check progress indicator has `Semantics(label: ...)`.
  - `lib/features/guides/salah_guide_screen.dart:1223` — one labelled widget.
  - `lib/features/onboarding/onboarding_screen.dart:1348` — one labelled widget.
  - Most screens have **no widget keys or semantic labels**. Maestro will need to rely on visible text (`tapOn: "Tasbih"`, `tapOn: "Quran"`) or position-based selectors.

- **Widget keys are minimal.** The only `ValueKey` constants usable as stable Maestro identifiers are:
  - `ValueKey('method_dropdown')` at `lib/features/onboarding/onboarding_screen.dart:1243` (calculation method dropdown)
  - `ValueKey('madhab_dropdown')` at `lib/features/onboarding/onboarding_screen.dart:1264` (school dropdown)
  - `ValueKey(_selectedIndex)` at `lib/navigation/app_shell.dart:191` — dynamically changes with tab selection, not useful as a stable test key.
  - Tasbih `History` and `Reset` buttons are tooltip-labelled (`lib/features/tasbih/tasbih_screen.dart:215,224`) — Maestro can target them via `tapOn: "History"` and `tapOn: "Reset"`.

- **Plugins that need handling in Maestro:**
  - `geolocator 14.0.0` — requests location permission at runtime. Maestro must intercept the OS dialog or pre-grant via emulator/simulator config.
  - `flutter_local_notifications ^17.2.0` + `just_audio_background` — notification permission prompt on Android 13+ / iOS. Same interception needed.
  - `flutter_compass ^0.8.0` — reads device sensor; on emulator the compass will return 0 or null. The Qibla screen already has a `_NoLocationBody` branch for no-location state and a `_WebStaticBearingBody` for web; on emulator without GPS fix the `_NoLocationBody` branch will render — tests should assert that state rather than compass values.
  - `in_app_update ^4.2.3` — requires Google Play; will be a no-op on emulator, safe to ignore.
  - `home_widget ^0.9.1` — iOS App Groups interaction; irrelevant to Maestro UI flows.
  - `flutter_tts ^4.2.5` — used in `DhikrScreen`; may produce error-state UI if TTS engine absent on emulator. Tests should handle or skip TTS-dependent assertions.
  - `just_audio ^0.10.5` — Quran audio player; audio playback on CI emulators may be silent but the UI controls should still render.

- **No maestro CLI or mobile.dev account** has been configured. The project has no `maestroConfig.yaml`, no `MAESTRO_CLOUD_API_KEY` secret, and no CI step for Maestro.

- **Quran screen uses `GlobalKey` per ayah** (`lib/features/quran/quran_screen.dart:574`). These are runtime-allocated, not useful for Maestro. Surah names rendered as text are the practical targets.

- **T02 web guard** (`lib/main.dart:327`) skips onboarding on web. On mobile Maestro targets the native build, so onboarding will fire. This is a T02 change that clarifies the mobile path — the onboarding skip is deliberately web-only.

## Research

Maestro (mobile.dev / maestro.mobile.dev) is a mobile UI testing framework using declarative YAML flow files. Key concepts relevant to Noble Salah:

- **`launchApp`** — starts the app under test; accepts `appId` (bundle ID / package name), `clearState: true` to wipe SharedPreferences/DB between runs, and `arguments` for passing test flags. Using `clearState: true` ensures onboarding is shown fresh each run.
- **`tapOn`** — taps a visible element by text, `id` (accessibility label), or `point`. For Noble Salah's sparse semantic tree, text-based `tapOn` ("Quran", "Tools", "Tasbih") is the primary selector.
- **`assertVisible` / `assertNotVisible`** — verifies UI state without tapping. Used to confirm screen transitions and that specific prayer names or Quran surah titles appear.
- **`inputText`** — types into focused text fields. Used for city search (`CitySearchScreen`).
- **`runFlow`** — calls a sub-flow YAML, enabling reusable setup flows (e.g., a `flows/helpers/complete_onboarding.yaml` sub-flow invoked by every test flow).
- **`allowPermissions`** — iOS-specific command that pre-approves location/notification permissions before the app prompts. On Android, `tapOn: "While using the app"` handles the OS dialog inline.
- **Maestro Studio** — desktop GUI to record flows interactively; useful for initial flow authoring against a live emulator.
- **`maestro test`** — runs a flow or directory of flows locally against a connected device or emulator.
- **`maestro cloud`** — uploads flows to Maestro Cloud (SaaS) for parallel device-farm execution and CI integration via GitHub Actions (`mobile-dev-inc/maestro-cloud-action`).
- **Flow structure convention:** flows live in a `maestro/` directory at project root with subdirectories by feature (e.g., `maestro/flows/onboarding.yaml`, `maestro/flows/dashboard.yaml`). A `maestro/config.yaml` (or `.maestro.yaml`) can set global `appId` and environment variables.

## Recommended Path

Begin with a `maestro/` directory at the Noble Salah project root containing a `config.yaml` that sets the Android `appId` (`co.humanity.noblesalah`) and iOS bundle ID. The first flow to build is `flows/helpers/complete_onboarding.yaml` — a reusable sub-flow that launches the app with `clearState: false` (or pre-seeds the SharedPreferences flag via `launchApp arguments`) to land directly on the main shell; alternatively, walk through all onboarding pages in sequence, using `tapOn: "Allow"` / `allowPermissions` for location and notification dialogs, selecting a default city via the city search field, and tapping "Let's Go" on the final settings page. With onboarding solved, build core smoke flows in priority order: (1) Dashboard — assert prayer names are visible; (2) Quran — navigate to tab, assert surah list loads, tap first surah, assert ayah text visible; (3) Tasbih — tap counter button 3 times, assert count increments, tap Reset; (4) Qibla — assert either compass or no-location message appears (no GPS on emulator); (5) Settings — change language or theme, assert the setting persists on re-launch. Handle the Qibla compass by asserting the fallback `_NoLocationBody` text rather than compass values on emulator. For CI, start with local `maestro test` on an Android emulator in GitHub Actions (`reactivecircus/android-emulator-runner`) before committing to Maestro Cloud costs — the existing web-deploy workflow can be extended with a parallel `test-mobile` job. Add `MAESTRO_CLOUD_API_KEY` as a GitHub secret when cloud execution is desired. Instrument the top-priority screens (Dashboard, Tasbih, Qibla, Settings header) with `Semantics` labels or `Key` values as a parallel task to make flows more robust against text changes.

## Links
- [[T03-summary]] · [[T03-analysis]] · [[T03-requirements]] · [[T03-decision-log]] · [[T03-questions]] · [[T03-plan]] · [[T03-progress]] · [[T03-verification]]
