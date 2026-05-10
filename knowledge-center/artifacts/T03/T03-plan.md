---
ticket: "T03"
artifact: plan
stage: CANONICAL
status: draft
authored: 2026-05-09
---

# Plan: T03 — Setup Maestro-based testing

## Approach

Noble Salah has a mature unit-test suite but zero UI automation. T03 introduces Maestro as the black-box mobile testing layer: a `maestro/` directory at the Noble Salah project root, a debug-only onboarding bypass wired through `launchApp arguments`, five feature smoke flows (Dashboard, Quran, Tasbih, Qibla, Settings), and a GitHub Actions CI job that builds the debug APK, boots an Android emulator, and runs the full suite. The plan is structured as five sequenced slices: (1) repo scaffold and config, (2) debug bypass in `main.dart`, (3) helper flow and smoke flows, (4) CI workflow, (5) stability and verification. Each slice is independently shippable and gate-checked before the next begins. Slice 3 is the largest; flows are authored in dependency order (helper first, Dashboard second, remaining flows in parallel). Text-based `tapOn` selectors are the primary strategy given sparse semantic labels in the codebase. All validation warnings from the requirements review are incorporated as inline notes on their affected tasks.

---

## Slices

### Slice 1 — Repository scaffold and Maestro config

Establish the `maestro/` directory tree and `config.yaml`. No app code is touched in this slice.

---

#### [x] T03-01 — Create `maestro/` directory structure and `config.yaml` (1 h)

- [ ] Create `maestro/` at Noble Salah project root.
- [ ] Create `maestro/config.yaml` with `appId: co.humanity.noblesalah`.
- [ ] Create `maestro/flows/` directory (placeholder `.gitkeep` if needed).
- [ ] Create `maestro/flows/helpers/` directory.
- [ ] Add `maestro/` to `.gitignore` exclusions check — confirm no accidental ignore of YAML files.
- **Done-criteria:** `maestro/config.yaml` exists; `appId` value is exactly `co.humanity.noblesalah`; `maestro/flows/` and `maestro/flows/helpers/` directories are present and committed. AC-01 passes (`maestro test` reads config without error).
- **Effort:** 1 h
- **Basis:** Pure filesystem + YAML authoring; no app code.
- **Depends on:** —

---

### Slice 2 — Debug-only onboarding bypass

Instrument `lib/main.dart` with a `kDebugMode`-guarded `launchApp arguments` reader. This is the foundational unblock for all flows in Slice 3.

---

#### [x] T03-02 — Add `skipOnboarding` launchApp arguments reader in `main.dart` (2 h)

- [ ] Locate the `main()` entry point and the `onboardingComplete` resolution block (`lib/main.dart:327`).
- [ ] Import `package:flutter/foundation.dart` (already present; confirm `kDebugMode` is accessible).
- [ ] Wrap a `WidgetsFlutterBinding.ensureInitialized()` block: in `kDebugMode` only, read `dart:ui`'s `PlatformDispatcher.instance.initialLifecycleState` arguments string OR use `AppInstance` / `MethodChannel` to receive Maestro's `launchApp` arguments map. Preferred: use `FlutterError.onError` + `ServicesBinding.instance.defaultBinaryMessenger` pattern aligned with Maestro's documented `arguments` injection.
- [ ] When `skipOnboarding == 'true'` (or `true`), write `kOnboardingCompleteKey = true` to SharedPreferences before `runApp` resolves the onboarding flag.
- [ ] Guard the entire block with `assert(() { ... return true; }())` or `if (kDebugMode)` so the compiler tree-shakes it from release builds.
- [ ] Confirm `flutter build apk --release` does not include the bypass branch (manual APK smoke-test: fresh launch shows onboarding).
- **Done-criteria:** AC-03 passes — debug APK launched with `launchApp arguments: {skipOnboarding: true}` lands on Dashboard without onboarding. AC-04 passes — release APK fresh launch shows onboarding. NFR-02 satisfied.
- **Effort:** 2 h
- **Basis:** Single-file Dart change; pattern is well-documented in Maestro docs. Risk is in `arguments` delivery mechanism (see R-01).
- **Depends on:** T03-01

---

### Slice 3 — Maestro helper flow and feature smoke flows

Author all YAML flows. The helper flow is authored first; all feature flows depend on it. Flows for Quran (FR-05) and Tasbih (FR-06) carry validation-review annotations.

---

#### [x] T03-03 — Helper flow: `launch_to_shell.yaml` (1 h)

- [ ] Author `maestro/flows/helpers/launch_to_shell.yaml`.
- [ ] `launchApp` with `appId: co.humanity.noblesalah`, `clearState: false`, `arguments: {skipOnboarding: true}`.
- [ ] `assertVisible` Dashboard tab label (use text `"Dashboard"` — English locale, localized string via semantics label from `app_shell.dart:139`).
- [ ] Add comment in file: "Dashboard tab label uses English locale semantic label. Verify actual rendered text with `maestro studio` before finalizing."
- **Done-criteria:** AC-02 passes — `maestro test maestro/flows/helpers/launch_to_shell.yaml` on a connected device passes. Dashboard tab is visible post-launch.
- **Effort:** 1 h
- **Basis:** Single flow file; no app code.
- **Depends on:** T03-02

#### [x] T03-04 — Dashboard smoke flow (1 h)

- [ ] Author `maestro/flows/dashboard.yaml`.
- [ ] First step: `runFlow: helpers/launch_to_shell.yaml`.
- [ ] `assertVisible` each of the 5 tab labels: `"Dashboard"`, `"Quran"`, `"Dua"`, `"Tools"`, `"Settings"`.
- [ ] `assertVisible` at least one of: `"Fajr"`, `"Dhuhr"`, `"Asr"`, `"Maghrib"`, `"Isha"` (use `anyOf` pattern or assert first visible prayer name).
- **Done-criteria:** AC-05 passes — all 5 tabs visible, at least one prayer name visible.
- **Effort:** 1 h
- **Basis:** Straightforward text assertions; prayer names are rendered in English.
- **Depends on:** T03-03

#### [x] T03-05 — Quran smoke flow (1.5 h)

> **FR-05 validation note:** The `assertVisible: "Al-Fatiha"` selector assumes the surah list renders the English Latin transliteration. Before writing the final flow, verify with `maestro studio` or `adb shell` screenshot that the first surah name visible on-screen is `"Al-Fatiha"` and not the Arabic `"الفاتحة"` or an alternative transliteration. If the app renders Arabic script, switch the assertion to an Arabic character range check or a different visible English label.

- [ ] Author `maestro/flows/quran.yaml`.
- [ ] First step: `runFlow: helpers/launch_to_shell.yaml`.
- [ ] `tapOn: "Quran"` to navigate to Quran tab.
- [ ] Add comment: "Surah name text format must be confirmed before finalizing — see FR-05 validation note above. Default assertion uses `Al-Fatiha` (English Latin). Verify on device with maestro studio."
- [ ] `assertVisible: "Al-Fatiha"` (or confirmed first surah label — adjust after verification step).
- [ ] `tapOn: "Al-Fatiha"` (or first surah entry) to open ayah view.
- [ ] `assertVisible` at least one Arabic character string or bismillah text; alternatively assert the surah detail screen AppBar title is visible (non-crash assertion).
- **Done-criteria:** AC-06 passes — Quran tab opens, surah list visible, first surah tappable and ayah view loads without crash. Surah name text format verified before flow is frozen.
- **Effort:** 1.5 h
- **Basis:** Extra 0.5 h for the surah name format verification step.
- **Depends on:** T03-03

#### [x] T03-06 — Tasbih smoke flow (1.5 h)

> **FR-06 validation note:** The counter increment assertion (`count == 3` after 3 taps) must account for counter display format. Confirm whether the Tasbih screen renders the count as ASCII numerals (`3`) or Arabic-Indic numerals (`٣`) before writing the `assertVisible` assertion. Use `maestro studio` or a screenshot on device. Update the `assertVisible` value accordingly.

- [ ] Author `maestro/flows/tasbih.yaml`.
- [ ] First step: `runFlow: helpers/launch_to_shell.yaml`.
- [ ] `tapOn: "Tools"` to navigate to Tools tab.
- [ ] `tapOn: "Tasbih"` to enter the Tasbih screen.
- [ ] Add comment: "Counter display format (ASCII `3` vs Arabic-Indic `٣`) must be confirmed on device before finalizing assertVisible value — see FR-06 validation note."
- [ ] Tap counter button 3 times (use `tapOn` by tooltip text or visible counter widget; tooltip is `"Increment"` or button content).
- [ ] `assertVisible` count value `"3"` (or `"٣"` — resolve per validation note).
- [ ] `tapOn: "Reset"` (tooltip-labelled button per `tasbih_screen.dart:224`).
- [ ] `assertVisible` count value `"0"` (or `"٠"` — resolve per validation note).
- **Done-criteria:** AC-07 passes — counter increments by 3 then resets to 0. Display format confirmed before assertion is frozen.
- **Effort:** 1.5 h
- **Basis:** Extra 0.5 h for numeral format verification step.
- **Depends on:** T03-03

#### [x] T03-07 — Qibla smoke flow (1 h)

- [ ] Author `maestro/flows/qibla.yaml`.
- [ ] First step: `runFlow: helpers/launch_to_shell.yaml`.
- [ ] `tapOn: "Tools"` to navigate to Tools tab.
- [ ] `tapOn: "Qibla"` to enter Qibla screen.
- [ ] `assertVisible` either a compass widget OR the no-location fallback message rendered by `_NoLocationBody`. On emulator (no GPS fix), the fallback branch is expected.
- [ ] `assertNotVisible` any error dialog or crash overlay.
- **Done-criteria:** AC-08 passes — Qibla screen reachable, no crash on emulator, either compass or no-location message visible.
- **Effort:** 1 h
- **Basis:** Straightforward; fallback branch is well-identified in analysis.
- **Depends on:** T03-03

#### [x] T03-08 — Settings smoke flow (1 h)

> **FR-08 validation note:** The flow must assert BOTH the language selector AND the theme selector are visible — not just one. Requirements originally stated "language selector or theme selector"; the validation review tightened this to both. Assert both elements are visible on the Settings screen before the flow exits.

- [ ] Author `maestro/flows/settings.yaml`.
- [ ] First step: `runFlow: helpers/launch_to_shell.yaml`.
- [ ] `tapOn: "Settings"` to navigate to Settings tab.
- [ ] `assertVisible` language selector (confirm rendered label text with `maestro studio` — likely `"Language"` or locale-specific heading).
- [ ] `assertVisible` theme selector (confirm rendered label text — likely `"Theme"` or `"Appearance"`).
- [ ] `assertNotVisible` the web-only Athan notification banner text (per FR-08 and T02 context).
- [ ] Add comment: "Both language selector AND theme selector must be asserted visible per FR-08 validation review."
- **Done-criteria:** AC-09 passes — Settings screen opens, language selector visible, theme selector visible, web-only notification banner not present.
- **Effort:** 1 h
- **Basis:** Simple navigation + assertions; settings screen has identifiable text headings.
- **Depends on:** T03-03

---

### Slice 4 — GitHub Actions CI workflow

Wire the full flow suite into CI. Depends on Slice 3 being complete so the workflow runs a real flow directory.

---

#### [x] T03-09 — Author `.github/workflows/mobile-test.yml` (2 h)

- [ ] Create `.github/workflows/mobile-test.yml`.
- [ ] Trigger: `push` to `main`; `pull_request` targeting `main`.
- [ ] Job `mobile-test` with `runs-on: ubuntu-latest`.
- [ ] Step: checkout repo.
- [ ] Step: set up Java (required by Android SDK / emulator runner).
- [ ] Step: set up Flutter (`subosito/flutter-action` or equivalent, matching project Flutter version).
- [ ] Step: install Maestro CLI (`curl -Ls "https://get.maestro.mobile.dev" | bash` or pinned version).
- [ ] Step: build debug APK (`flutter build apk --debug`).
- [ ] Step: start Android emulator via `reactivecircus/android-emulator-runner` (API 33, x86_64, `target: google_apis` for Play Services if needed).
- [ ] Step: install APK on emulator (`adb install build/app/outputs/flutter-apk/app-debug.apk`).
- [ ] Step: `maestro test maestro/flows/` — exits non-zero on any failure.
- [ ] Confirm job fails when a deliberate bad assertion is injected (AC-13 verification).
- **Done-criteria:** AC-12 passes — workflow file exists, job green on `main`. AC-13 passes — deliberate failure causes non-zero exit. CI job wall-clock ≤ 15 min target set (NFR-04 / AC-14).
- **Effort:** 2 h
- **Basis:** Similar to existing `web-deploy.yml` structure; emulator runner is a well-known action. Risk in emulator boot time (see R-02).
- **Depends on:** T03-08 (all flows complete)

---

### Slice 5 — Stability, timing, and verification pass

Run the full suite 3 consecutive times locally to satisfy NFR-03 / AC-10. Measure wall-clock time for NFR-01 / AC-11.

---

#### [ ] T03-10 — Full suite stability run and timing measurement (1.5 h)

> **NFR-03 / AC-10 annotation:** This task must pass on **3 consecutive local runs** without modification to any flow file. A single pass is insufficient. Record each run result in `T03-progress.md`. If any run fails, diagnose the selector and fix before restarting the 3-run sequence.

- [ ] Run `maestro test maestro/flows/` on a connected Android device — run 1. Record pass/fail and wall-clock time.
- [ ] Run `maestro test maestro/flows/` — run 2. Record result.
- [ ] Run `maestro test maestro/flows/` — run 3. Record result.
- [ ] Confirm all 3 runs pass with zero failures (AC-10).
- [ ] Confirm total suite wall-clock ≤ 5 minutes across all 3 runs (AC-11 / NFR-01).
- [ ] If any run fails due to flaky selector: fix selector → reset counter → re-run 3 times from scratch.
- [ ] Log all 3 run timestamps and durations in `T03-progress.md`.
- **Done-criteria:** AC-10 passes — 3 consecutive zero-failure local runs confirmed and logged. AC-11 passes — suite ≤ 5 min. NFR-03 satisfied.
- **Effort:** 1.5 h
- **Basis:** Test execution + diagnosis buffer for flaky selectors.
- **Depends on:** T03-09

#### [ ] T03-11 — CI timing confirmation and AC-14 verification (0.5 h)

- [ ] Observe CI job wall-clock time on a `main` branch push (use GitHub Actions run log).
- [ ] Confirm total `mobile-test` job time ≤ 15 minutes (AC-14 / NFR-04).
- [ ] If job exceeds 15 min: investigate emulator boot time, consider caching AVD snapshot or switching to API 30 for faster boot.
- [ ] Record CI timing in `T03-progress.md`.
- **Done-criteria:** AC-14 passes — CI job wall-clock ≤ 15 minutes confirmed on at least one successful run.
- **Effort:** 0.5 h
- **Basis:** Observation-only; no code changes expected unless timing is over budget.
- **Depends on:** T03-09

---

## Effort

| Task | Title | Estimate | Basis |
|------|-------|----------|-------|
| T03-01 | Create `maestro/` directory structure and `config.yaml` | 1.0 h | Filesystem + YAML only |
| T03-02 | Add `skipOnboarding` launchApp arguments reader in `main.dart` | 2.0 h | Single-file Dart; arguments injection mechanism needs care |
| T03-03 | Helper flow: `launch_to_shell.yaml` | 1.0 h | Single YAML flow |
| T03-04 | Dashboard smoke flow | 1.0 h | Text assertions, 5 tabs + prayer names |
| T03-05 | Quran smoke flow | 1.5 h | +0.5 h for surah name format verification |
| T03-06 | Tasbih smoke flow | 1.5 h | +0.5 h for numeral display format verification |
| T03-07 | Qibla smoke flow | 1.0 h | Fallback branch identified; straightforward |
| T03-08 | Settings smoke flow | 1.0 h | Navigation + 2 visible-element assertions + 1 not-visible |
| T03-09 | Author `.github/workflows/mobile-test.yml` | 2.0 h | CI YAML + emulator runner config |
| T03-10 | Full suite stability run and timing measurement | 1.5 h | 3-run sequence + selector fix buffer |
| T03-11 | CI timing confirmation and AC-14 verification | 0.5 h | Observation; no code changes expected |
| **Total** | | **14.0 h** | |

---

## Acceptance Criterion Coverage

| AC | Description (abbreviated) | Covered by |
|----|---------------------------|-----------|
| AC-01 | `maestro/config.yaml` exists with correct `appId` | T03-01 |
| AC-02 | `launch_to_shell.yaml` passes on connected device | T03-03 |
| AC-03 | Debug APK + `skipOnboarding: true` lands on Dashboard | T03-02 |
| AC-04 | Release APK fresh launch shows onboarding (bypass inactive) | T03-02 |
| AC-05 | `dashboard.yaml` passes — 5 tabs + prayer name visible | T03-04 |
| AC-06 | `quran.yaml` passes — surah list visible, first surah opens | T03-05 |
| AC-07 | `tasbih.yaml` passes — counter +3, Reset → 0 | T03-06 |
| AC-08 | `qibla.yaml` passes — Qibla screen visible, no crash | T03-07 |
| AC-09 | `settings.yaml` passes — Settings visible, no web banner | T03-08 |
| AC-10 | Full suite zero failures on local device (3 consecutive runs) | T03-10 |
| AC-11 | Full suite ≤ 5 min wall-clock | T03-10 |
| AC-12 | `mobile-test.yml` exists and job passes on `main` | T03-09 |
| AC-13 | Deliberate flow failure causes CI non-zero exit | T03-09 |
| AC-14 | CI job wall-clock ≤ 15 minutes | T03-11 |

All 14 acceptance criteria are covered. Coverage ratio: 14/14.

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|-----------|--------|------------|-------|
| R-01 | `launchApp arguments` injection mechanism differs from Maestro docs or requires a platform channel on current Flutter version | Med | High | Prototype T03-02 first on a local device before committing CI. Fallback: pre-seed via ADB `am instrument` or a debug-only `MethodChannel`. Decision documented in `T03-decision-log.md`. | Builder |
| R-02 | Android emulator cold boot in GitHub Actions exceeds 15-min CI budget | Med | High | Use `reactivecircus/android-emulator-runner` with AVD caching and `disable-animations: true`. Consider API 30 (faster boot) if API 33 is too slow. Monitor on first CI push and adjust. | Builder |
| R-03 | Surah name rendered as Arabic script rather than Latin, breaking `assertVisible: "Al-Fatiha"` (FR-05 warning) | Med | Med | Explicitly verify with `maestro studio` screenshot before freezing T03-05. If Arabic-only, use a different English-visible label or bismillah text assertion. | Builder |
| R-04 | Tasbih counter displayed as Arabic-Indic numerals, breaking ASCII numeral assertion (FR-06 warning) | Med | Med | Verify numeral format on device before freezing T03-06. Update `assertVisible` to `"٣"` / `"٠"` if needed. | Builder |
| R-05 | Flaky selectors causing intermittent failures on 3-run stability check (NFR-03) | Med | Med | Use `assertVisible` with `timeout` parameter rather than bare assertions. Fall back to position-based tap if text changes between app states. Add `wait` steps after navigation. | Builder |
| R-06 | Release APK still includes `skipOnboarding` branch due to insufficient dead-code elimination | Low | High | Confirm with `grep` on decompiled APK or by running the release build fresh. Use `assert(() {...}())` idiom which is guaranteed eliminated in release. | Builder |

No high-likelihood × high-impact risks remain without mitigation. All high-impact risks have documented fallback strategies.

---

## Dependencies

### Blocks
- T04 (if any): CI green on `main` is a prerequisite for any future release automation ticket that depends on a stable Android CI pipeline.

### Blocked by
- Noble Salah project must be buildable as a debug APK locally (`flutter build apk --debug` must pass) — assumed satisfied given existing unit test CI.
- An Android device or emulator must be available for local validation of T03-10.
- T02 must be in a state where `main.dart` onboarding logic is stable (T02 is in VERIFY; the onboarding skip on web does not conflict with the mobile bypass in T03-02).

### External
- Maestro CLI installable from `get.maestro.mobile.dev` — public endpoint, no account required for local use (D2).
- `reactivecircus/android-emulator-runner` GitHub Action — public, no secrets required.

---

## Links
- [[T03-summary]] · [[T03-analysis]] · [[T03-requirements]] · [[T03-decision-log]] · [[T03-questions]] · [[T03-plan]] · [[T03-progress]] · [[T03-verification]]
