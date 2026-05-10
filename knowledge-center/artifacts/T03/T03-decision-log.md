---
ticket: "T03"
artifact: decision-log
---

# Decisions: T03

## D1 — Onboarding pre-seed via launchApp arguments
**Decision:** Add a debug-only escape hatch to the app that reads a `skipOnboarding` flag from `launchApp` arguments, setting the SharedPreferences key directly so Maestro flows land on the main shell without walking through onboarding.  
**Rationale:** Walking through onboarding in every test run is slow and ties all flows to onboarding UI stability. An arguments-based injection is faster, more isolated, and standard Maestro practice.  
**Impact:** Requires a small debug-only code path in `lib/main.dart` or a dedicated test bootstrap; must be guarded so it has zero effect in release builds.

## D2 — CI via local Android device + GitHub Actions (no Maestro Cloud)
**Decision:** Run Maestro flows against a local connected Android device (or emulator via `reactivecircus/android-emulator-runner`) in GitHub Actions using the `maestro test` CLI. No Maestro Cloud subscription.  
**Rationale:** Keeps costs at zero; the existing GitHub Actions setup is sufficient for a single-device smoke suite. Maestro Cloud can be added later if parallel multi-device coverage becomes a priority.  
**Impact:** CI job will need `maestro` CLI installed in the runner, an Android emulator or USB-connected device, and the APK built before the test step.

## D3 — Android only; iOS skipped this phase
**Decision:** Maestro flows and CI coverage target Android only. No iOS Simulator flows are written or run in T03.  
**Rationale:** Reduces scope and avoids the macOS runner cost. iOS coverage can be added as a follow-on ticket once the Android suite is stable.  
**Impact:** iOS-specific plugin behaviour (flutter_tts Web Speech, flutter_compass on Simulator) is untested until a future phase.

## Links
- [[T03-summary]] · [[T03-analysis]] · [[T03-requirements]] · [[T03-decision-log]] · [[T03-questions]] · [[T03-plan]] · [[T03-progress]] · [[T03-verification]]
