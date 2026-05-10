---
ticket: "T03"
artifact: requirements
stage: CLARIFY
status: frozen
frozen: 2026-05-09
---

# Requirements: T03 — Setup Maestro-based testing

## Functional Requirements

### FR-01 Maestro directory structure
A `maestro/` directory is created at the Noble Salah project root containing:
- `config.yaml` — sets `appId: co.humanity.noblesalah` (Android package name)
- `flows/helpers/` — reusable sub-flows (onboarding bypass, etc.)
- `flows/` — one YAML file per feature smoke flow

### FR-02 Debug-only onboarding bypass via launchApp arguments
The app reads a `skipOnboarding` key from Maestro's `launchApp` arguments map. When present and `true`, `main.dart` writes the `kOnboardingCompleteKey` SharedPreferences flag and skips to `AppShell` without rendering `OnboardingScreen`. This code path is active in debug builds only (`assert` or `kDebugMode` guard); it has zero effect in release builds.

### FR-03 Reusable helper flow — app launch to main shell
`maestro/flows/helpers/launch_to_shell.yaml` launches the app with `skipOnboarding: true` via `launchApp arguments`, then asserts the Dashboard tab is visible. Every feature flow uses this helper via `runFlow` as its first step.

### FR-04 Dashboard smoke flow
`maestro/flows/dashboard.yaml` verifies that:
- All 5 navigation tabs are visible ("Dashboard", "Quran", "Dua", "Tools", "Settings")
- At least one of the 5 canonical prayer names is visible on screen ("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha")

### FR-05 Quran smoke flow
`maestro/flows/quran.yaml` verifies that:
- Tapping the "Quran" tab opens the Quran screen
- The surah list is visible (assert "Al-Fatiha" or equivalent first surah name is present)
- Tapping the first surah opens the ayah view without a crash (assert at least one Arabic character string or bismillah text is visible)

### FR-06 Tasbih smoke flow
`maestro/flows/tasbih.yaml` verifies that:
- The Tasbih screen is reachable (via Tools tab → Tasbih entry)
- Tapping the counter button 3 times increments the displayed count by 3
- Tapping "Reset" resets the count to 0

### FR-07 Qibla smoke flow
`maestro/flows/qibla.yaml` verifies that:
- The Qibla screen is reachable via the Tools tab
- On an emulator (no GPS fix), either a compass widget or a no-location fallback message is visible (no crash, no blank screen)

### FR-08 Settings smoke flow
`maestro/flows/settings.yaml` verifies that:
- The Settings screen opens from the Settings tab
- The language selector or theme selector is visible
- The notification banner "Athan notifications are only available in the mobile app" is **not** present (mobile build — the banner is web-only per T02)

### FR-09 GitHub Actions CI job — mobile-test
A new workflow file `.github/workflows/mobile-test.yml` (or an added job in the existing workflow) that:
- Installs the Maestro CLI
- Starts an Android emulator via `reactivecircus/android-emulator-runner`
- Builds a debug APK with `flutter build apk --debug`
- Installs the APK on the emulator
- Runs `maestro test maestro/flows/` and exits non-zero on any flow failure
- Runs on push to `main` and on pull requests targeting `main`

### FR-10 All flows pass on a local connected Android device
`maestro test maestro/flows/` completes with zero failures when run against a physical Android device connected via ADB, using the debug APK.

---

## Non-Functional Requirements

### NFR-01 Flow suite wall-clock time
The full `maestro/flows/` suite (all 5 feature flows + helper) completes in ≤ 5 minutes on a mid-range Android emulator (API 33, x86_64).

### NFR-02 Debug bypass leaves no trace in release build
`flutter build apk --release` must produce a binary where the `skipOnboarding` argument branch is fully dead (no SharedPreferences write on a clean launch). Verified by: running the release APK fresh and confirming onboarding is shown.

### NFR-03 Flow stability — no flaky selectors
Each flow must pass on 3 consecutive local runs without modification. Text-based `tapOn` selectors use the English locale string; flows are not expected to be locale-agnostic in this phase.

### NFR-04 CI job duration
The `mobile-test` GitHub Actions job (emulator boot + APK install + suite run) completes in ≤ 15 minutes total.

### NFR-05 No new Dart dependencies
Maestro is a CLI tool external to Flutter. No new packages are added to `pubspec.yaml` beyond what is already present. The `kDebugMode` guard for FR-02 uses the existing Flutter foundation import.

---

## Acceptance Criteria

### Setup
- [ ] AC-01: `maestro/config.yaml` exists with `appId: co.humanity.noblesalah`.
- [ ] AC-02: `maestro test maestro/flows/helpers/launch_to_shell.yaml` passes on a connected Android device.

### Debug bypass (FR-02)
- [ ] AC-03: Launching the debug APK with `launchApp arguments: {skipOnboarding: true}` lands on the Dashboard tab without showing any onboarding screen.
- [ ] AC-04: Launching the release APK fresh (no prior SharedPreferences) shows the onboarding screen — the bypass is inactive.

### Feature flows
- [ ] AC-05: `maestro test maestro/flows/dashboard.yaml` passes — prayer name visible, all 5 tabs visible.
- [ ] AC-06: `maestro test maestro/flows/quran.yaml` passes — surah list visible, first surah opens without crash.
- [ ] AC-07: `maestro test maestro/flows/tasbih.yaml` passes — counter increments by 3, Reset returns to 0.
- [ ] AC-08: `maestro test maestro/flows/qibla.yaml` passes — Qibla screen visible, no crash on emulator.
- [ ] AC-09: `maestro test maestro/flows/settings.yaml` passes — Settings screen visible, no web-only notification banner.

### Full suite
- [ ] AC-10: `maestro test maestro/flows/` runs all flows with zero failures on a local Android device.
- [ ] AC-11: Full suite completes in ≤ 5 minutes (NFR-01).

### CI
- [ ] AC-12: `.github/workflows/mobile-test.yml` exists and the job passes on the `main` branch.
- [ ] AC-13: A deliberate flow failure (e.g. assert wrong text) causes the CI job to exit non-zero.
- [ ] AC-14: CI job wall-clock time ≤ 15 minutes (NFR-04).

---

## Out of Scope

- **iOS Simulator flows** — Android only in this phase (D3). iOS deferred to a future ticket.
- **Maestro Cloud** — no `maestro cloud` upload, no `MAESTRO_CLOUD_API_KEY` secret (D2). Local only.
- **Full onboarding walkthrough flow** — replaced by the `launchApp arguments` bypass (D1). Onboarding UI testing is out of scope.
- **Locale / RTL testing** — flows use English locale strings only; Arabic / RTL assertions are a future concern.
- **Audio playback assertion** — `just_audio` may be silent on emulators; audio UI controls are tested but sound output is not.
- **TTS assertion in Dhikr** — `flutter_tts` behaviour on emulators is untested; Dhikr screen render is in-scope only if easily reachable via text tap.
- **In-app update / Play Store flows** — `in_app_update` is a no-op on emulator; not tested.
- **Performance profiling** — Maestro flows verify functional correctness, not frame rates or memory.
- **Drift/IndexedDB persistence round-trips** — storage integration tests are a separate concern (see T02 NFR-05).

---

## Open Questions

None. All questions resolved (see [[T03-questions]], [[T03-decision-log]]).

---

## Links
- [[T03-summary]] · [[T03-analysis]] · [[T03-requirements]] · [[T03-decision-log]] · [[T03-questions]] · [[T03-plan]] · [[T03-progress]] · [[T03-verification]]
