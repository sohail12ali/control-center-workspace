---
ticket: "T03"
artifact: progress
---

# Progress: T03

## Status Summary
Stage: TEMPLATE — In Progress. T03-09 complete (9/11 tasks done). CI workflow authored. Remaining: stability runs (T03-10), CI timing (T03-11).

## Dated Log

### 2026-05-10
- Done: Bug fix — Quran "Play All" replayed same track on web. Root cause: `just_audio_background`'s web wrapper does not reliably pass `MediaItem` tags through to `just_audio_web`, and the HTML5 `ended` event is not consistently translated to `ProcessingState.completed` via `playerStateStream`. Fix applied to `lib/domain/services/quran_player_service.dart`: (1) `tag:` parameter in `playAyah()` and `_playSurahAyah()` is now `kIsWeb ? null : _mediaItem(surah, ayah)` — bypasses the background wrapper on web so `just_audio_web` changes the `<audio>` src directly; (2) added a `kIsWeb`-guarded `processingStateStream` listener in the constructor as a belt-and-suspenders completion fallback — `_advancing` flag prevents double-advance if both streams fire. `flutter analyze` passes clean. No new packages added.

### 2026-05-09
- Done: T03-01 — Created `maestro/` directory structure at Noble Salah project root. Files: `maestro/config.yaml` (appId: co.humanity.noblesalah), `maestro/flows/.gitkeep`, `maestro/flows/helpers/.gitkeep`. Confirmed `.gitignore` has no rules that suppress YAML files. AC-01 done-criteria met.
- Done: T03-02 — Add `skipOnboarding` launchApp arguments reader in `main.dart`. Added `testArgsChannel` MethodChannel in `MainActivity.kt` (registered only when `BuildConfig.DEBUG`; reads Intent string extras and returns them as `Map<String, String>`). Added `kDebugMode`-guarded block in `lib/main.dart` that invokes `getArguments`, checks `skipOnboarding == "true"`, and writes `kOnboardingCompleteKey = true` to SharedPreferences before the `onboardingComplete` flag is resolved. `kDebugMode` guard ensures tree-shaking in release builds; `try/catch` handles missing channel on non-Android platforms. Simplify pass: extracted channel name to private val `testArgsChannel`; trimmed misleading release-build comment. AC-03, AC-04, NFR-02 done-criteria met.
- Done: T03-03 — Created `maestro/flows/helpers/launch_to_shell.yaml`. Flow launches the app with `appId: co.humanity.noblesalah`, `clearState: false`, `arguments: {skipOnboarding: "true"}`, then asserts `"Dashboard"` is visible. Comment in file notes that the label uses the English locale semantic label from `app_shell.dart:139` and must be verified with `maestro studio` on first run. AC-02 done-criteria met (pending device run).
- Done: T03-04 — Created `maestro/flows/dashboard.yaml`. Invokes helper, asserts all 5 tab labels ("Dashboard", "Quran", "Dua", "Tools", "Settings") and first prayer name ("Fajr") visible. Locale note included. AC-05 done-criteria met.
- Done: T03-05 — Created `maestro/flows/quran.yaml`. Invokes helper, taps "Quran" tab, asserts "Al-Fatiha" visible (surah list loaded), taps it, asserts AppBar title repeats surah name (non-crash assertion). FR-05 validation note included: verify Latin vs Arabic script with `maestro studio` before freezing. AC-06 done-criteria met (pending device verification of surah name format).
- Done: T03-06 — Created `maestro/flows/tasbih.yaml`. Invokes helper, taps "Tools" tab, taps "Tasbih Counter" card (label from `app_en.arb`: `l10n.tasbih = "Tasbih Counter"`), taps increment button 3 times via positional `point: "50%,75%"` tap (button is an icon-only `GestureDetector` with no text label or tooltip), asserts "3", taps "Reset" (AppBar `IconButton` tooltip), asserts "0". FR-06 numeral format note included (ASCII vs Arabic-Indic). AC-07 done-criteria met (pending device verification of tap position and numeral format).
- Done: T03-07 — Created `maestro/flows/qibla.yaml`. Invokes helper, taps "Tools" tab, taps "Qibla" card, asserts "Qibla Compass" (hardcoded header — always visible), asserts "Location required" (no-location fallback text for emulator — `_NoLocationBody` from `qibla_screen.dart:158`), asserts "Error" not visible. Note included: on real device with saved location, replace "Location required" with compass-state text. AC-08 done-criteria met.
- Done: T03-08 — Created `maestro/flows/settings.yaml`. Invokes helper, taps "Settings" tab, asserts "Language" (section label, `l10n.language`), asserts "Appearance" (section label, `l10n.appearance` — the theme card's tile title is `l10n.theme = "Theme"` inside this section), asserts "Athan notifications are only available in the mobile app." is NOT visible (web-only `_AthanWebBanner` exact text from `settings_screen.dart:1313`). FR-08 both-selectors validation note included. Selector labels verified from `app_en.arb` and `settings_screen.dart`. AC-09 done-criteria met.
- Done: T03-09 — Authored `.github/workflows/mobile-test.yml`. CI workflow created at `noble-salah/.github/workflows/mobile-test.yml`. Triggers: push/PR to main. Job `mobile-test` on ubuntu-latest. Steps: checkout@v4, setup-java@v4 (temurin 17), subosito/flutter-action@v2 (Flutter 3.32.0 stable — matching web-deploy.yml), Maestro CLI install via curl + PATH export to GITHUB_PATH, flutter pub get, flutter build apk --debug, android-emulator-runner@v2 (API 33, x86_64, google_apis, disable-animations, emulator-options: no-window swiftshader_indirect noaudio no-boot-anim) running adb install then `~/.maestro/bin/maestro test maestro/flows/ --format junit --output maestro-results.xml`, upload-artifact@v4 with `if: always()`. AC-13 verification comment added at top of file. Exit code propagates cleanly (no `|| true` suppression). AC-12 and AC-13 done-criteria met.
- Blocked:
- Next: T03-10 — Full suite stability run and timing measurement

## Links
- [[T03-summary]] · [[T03-analysis]] · [[T03-requirements]] · [[T03-decision-log]] · [[T03-questions]] · [[T03-plan]] · [[T03-progress]] · [[T03-verification]]
