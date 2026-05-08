---
name: release-android
description: Build a signed Android release for the Noble Salah Flutter app — AAB for Play Store, APK for sideload, or both. Bumps version, runs `flutter build`, verifies the merged manifest, and optionally installs the APK on an attached device. Use when the user asks for a "release build", "Play Store build", "AAB", "release APK", or wants to deploy a release to a connected device.
---

# When to use

- "Create a release AAB / APK / both"
- "Build a Play Store upload"
- "Bump the version and rebuild"
- "Deploy a release on the connected device"

# Inputs

| arg | required | default | meaning |
|---|---|---|---|
| `type` | no | `aab` | `aab` (Play Store), `apk` (sideload), or `both` |
| `version` | no | current `pubspec.yaml` versionName | new versionName, e.g. `1.0.9` |
| `code` | no | current versionCode | new versionCode (must increase per Play Store upload) |
| `clean` | no | false | `flutter clean && pub get` before building |
| `install` | no | false | also install the APK on an attached device |
| `device` | no | first attached | adb device id |

# Project paths

The Flutter app lives **outside this workspace** at:

```
D:\Workspace\noble-wave\noble-salah\
```

The build script lives at:

```
D:\Workspace\noble-wave\noble-salah\scripts\release.sh   # bash
D:\Workspace\noble-wave\noble-salah\scripts\release.ps1  # PowerShell wrapper
```

Output artifacts:

```
build/app/outputs/bundle/release/app-release.aab   # Play Store
build/app/outputs/flutter-apk/app-release.apk      # sideload
```

# Steps

1. **Pre-flight**
   - Confirm `D:\Workspace\noble-wave\noble-salah\android\key.properties` exists. The release signing config needs it; the script aborts if missing.
   - If the user named a `version` and/or `code`, pass them through — the script edits `pubspec.yaml` in-place.
   - Play Store requires monotonically increasing `versionCode`. If the user re-runs the same code, surface that.

2. **Build**
   - Invoke the script in the Flutter project root. Prefer the bash entry point; on bare PowerShell use the `.ps1` wrapper.
   - Bash:
     ```
     cd /d/Workspace/noble-wave/noble-salah
     bash scripts/release.sh --type {type} [--version X] [--code Y] [--clean] [--install]
     ```
   - PowerShell:
     ```
     cd D:\Workspace\noble-wave\noble-salah
     .\scripts\release.ps1 -Type {type} [-Version X] [-Code Y] [-Clean] [-Install]
     ```
   - Builds run for ~3–8 min; run with `run_in_background: true` and stream progress with `Monitor` watching `Running Gradle|Built|FAILURE|FAILED|error:` lines.

3. **Cosmetic exit-1 to ignore**
   - Flutter's wrapper exits 1 with `Release app bundle failed to strip debug symbols from native libraries`. The AAB is still produced. The script tolerates this and re-validates the output file exists.

4. **Verify**
   - The script prints `versionCode` / `versionName` from the merged manifest after build. Confirm they match what the user requested.
   - List output paths and sizes.

5. **Install on device (if asked)**
   - The script auto-picks the first attached device or honours `--device <id>`.
   - If a debug build is already installed on the device, `adb install -r` will fail with `INSTALL_FAILED_UPDATE_INCOMPATIBLE` (signature mismatch). Tell the user; the script prints the uninstall hint.

6. **Post-build for Play Store**
   - Recommend the user upload the AAB to **Play Console → Testing → Internal testing → Create new release** before promoting to Production. Internal testing exposes AAB-specific issues (split-language, R8 stripping, etc.) without burning a versionCode reviewable round.

# Known AAB-only failure modes

| Symptom | Cause | Fix already in repo |
|---|---|---|
| Stuck on splash on Play-installed build | Language splits enabled — device only gets matching locale | `bundle.language.enableSplit = false` in `android/app/build.gradle.kts` |
| `PlatformException(invalid_icon, ic_notification not found)` | Resource shrinker stripped reflectively-loaded drawable | `android/app/src/main/res/raw/keep.xml` keeps `@drawable/ic_notification` |
| Background isolate crash on first prayer notification | R8 stripped `audio_service` / `just_audio_background` entry points | Keep rules in `android/app/proguard-rules.pro` |

If a new AAB-only failure appears, add the corresponding keep rule (or split-disable) and bump versionCode before re-uploading.

# Output

A short report:

- AAB and/or APK paths with sizes
- `versionCode` / `versionName` confirmed from the merged manifest
- Device-install result (if `install` was set)
- Next-step nudge (upload to Internal testing, etc.)

# Anti-patterns

- Do not run `flutter run --release` to "build a release". It builds an APK *and* installs it; for Play Store you need the AAB. Use the script with `--type aab` or `--type both`.
- Do not amend `versionCode` to an already-uploaded value. Play Console rejects it.
- Do not commit `key.properties` or the keystore. They live in the Flutter project but are gitignored.
