---
ticket: "T05"
artifact: analysis
---

# Analysis: T05

## Context

Noble Salah is a Flutter app at `D:\Workspace\noble-wave\noble-salah\`. The Salah Guide is an existing feature under `lib/features/guides/salah_guide_screen.dart` (single file, 1809 lines). The app uses the Provider pattern for state management. Gender, audio playback (via `just_audio`), and Quran data are all already wired as app-level services in `main.dart`.

## Current State

**Salah Guide screen** (`lib/features/guides/salah_guide_screen.dart`):
- Single `StatefulWidget` (`SalahGuideScreen`, line 868) with horizontal chip selector and animated switcher.
- Data model is fully in-file (private enums and classes, lines 10–98).
- Covers 8 prayer types: Fajr, Dhuhr, Asr, Maghrib, Isha, Witr, Eid, Janazah — all flat in one `_kSalahTypes` list (line 784). No Daily / Occasional distinction exists.
- Each prayer has `_Section` → `_Step` objects with recitation, response, options, variants, and `_GenderVariant` text fields (lines 52–98). Steps expand via `ExpansionTile`.
- Gender awareness exists at text level only: `_GenderVariantRow` (line 1595) reads `GenderService.isMale` via `context.watch` and highlights the relevant text variant. No image support exists.
- No audio playback is implemented anywhere in the Salah Guide screen.
- `_SalahInfo.components` (line 88) already encodes Sunnah + Fard counts per prayer, rendered as a `_PrayerStructureCard` timeline (line 1143). This partially addresses the Rakat breakdown requirement.

**Gender service** (`lib/domain/services/gender_service.dart`):
- `GenderService extends ChangeNotifier`, persisted via `SharedPreferences` key `noble_salah.gender` (line 19).
- Exposes `isMale` / `isFemale` booleans and `AppGender` enum (lines 9–13).
- Already registered as `ChangeNotifierProvider` in `main.dart` line 463.

**Audio** (`lib/domain/services/quran_player_service.dart`):
- `QuranPlayerService` wraps `just_audio` (line 2). Streams audio from everyayah.com CDN per surah/ayah.
- Registered as `ChangeNotifierProvider` in `main.dart` line 484.
- API: `playAyah(surah, ayah)`, `playSurah(...)`, `pause()`, `stop()`, `resume()`.
- Current audio is Quran recitation only (CDN URL per ayah). There are no local step-audio files in the project.

**App assets** (`assets/` in project):
- `assets/images/` contains only `mosque.svg` — no step posture images are bundled in the app.
- `assets/audio/athan/` has 3 athan mp3 files only.
- Step images currently exist only in the knowledge-center repo at `knowledge-center/assets/images/`.

**Step images in knowledge-center** (`knowledge-center/assets/images/`):
- Male: `male_step_1.png` through `male_step_9.png` (9 images; steps 10 and 11 missing)
- Female: `female_step_2.png` through `female_step_9.png` (8 images; step 1 missing — note filename `female_step_ 1.png` has a leading space which is a bug; steps 10 and 11 missing)
- `male_step_7.jpg` is JPEG while all others are PNG — inconsistency.
- `female_step_3.png` is also missing.
- Steps 10 (second Tasleem) and 11 (Du'a-e-Qunut) have no images for either gender.

**Routing**:
- `SalahGuideScreen` is launched via `MaterialPageRoute` from both `DashboardScreen` (line 1189) and `ToolsScreen` (line 148). No named routes. No navigation changes needed for the redesign.

**Occasional prayer gaps in current screen**:
- Jumu'ah, Tasbeeh, and Istikhara are entirely absent from the current `_kSalahTypes` list (line 784). The ticket brief lists these as required Occasional Prayers.

**No separation of Daily vs Occasional prayers exists** — all 8 prayer types appear as flat chips.

## Key Findings

- **Architecture is monolithic** (`salah_guide_screen.dart`, 1809 lines): all data, models, and UI are file-private. Significance: adding sections/images/audio without structural changes will make the file unmanageable; a data/UI split or extraction to sub-widgets is warranted.
- **No step images are in the app bundle**: All step images live only in `knowledge-center/assets/images/` and must be copied into `assets/images/steps/` (or similar) and declared in `pubspec.yaml`. Significance: asset pipeline work is a prerequisite for any image feature.
- **Image set is incomplete**: Female step 1 is absent (filename has a leading space), female step 3 is absent, and both male and female steps 10–11 are absent. `male_step_7.jpg` is JPEG vs PNG for the rest. Significance: placeholder handling is mandatory, not optional.
- **Audio source is Quran CDN (per ayah)**: No local step-level audio exists. The brief says "sourced from Quran audio already in the app" — this likely means playing the relevant Quran recitation (e.g. Al-Fatiha = Surah 1) via `QuranPlayerService` rather than bespoke step audio. Significance: scoping needs to be clarified with the owner — does "audio" mean per-step recitation audio mapped to Quran surah/ayah, or something else?
- **GenderService is provider-injected and reactive**: `context.watch<GenderService>()` already works inside `_StepCard._buildExpandedContent` (line 1559). Image switching by gender can follow the same pattern.
- **Occasional prayers partially exist**: Witr, Eid, Janazah are in the current screen. Jumu'ah, Tasbeeh, and Istikhara are entirely absent — content authoring required.
- **`_PrayerStructureCard` already shows Sunnah+Fard counts** for the 5 daily prayers (line 1143). The "Rakat breakdown" requirement is partially fulfilled; the redesign should preserve or evolve this.
- **Both entry points use `MaterialPageRoute`**: no deep-linking or route-name changes are required.

## Research

- `just_audio` (v0.10.5) supports `AudioSource.uri` for CDN URLs and asset sources for bundled files — both patterns are usable for step audio.
- `just_audio_background` is already configured for lock-screen media controls; any new audio player can reuse this infrastructure.
- Asset declaration in `pubspec.yaml` (line 140): a new directory entry (e.g. `assets/images/steps/`) needs to be added when step images are copied in.
- `female_step_ 1.png` has a leading space in its filename — this will cause asset load failures if used as-is. The file should be renamed to `female_step_1.png`.

## Recommended Path

Keep the existing `salah_guide_screen.dart` as the entry point but restructure it in two passes. Pass 1 (data layer): extract the `_SalahInfo` / `_Step` model to a separate `salah_guide_data.dart` file, add a `category` field (`daily` / `occasional`) to `_SalahInfo`, add `imageAssetPath` to `_Step`, and author the three missing Occasional Prayers (Jumu'ah, Tasbeeh, Istikhara). Pass 2 (UI layer): redesign the chip selector into a two-section list or tabbed view (Daily / Occasional), wire `_StepCard` to display the gender-appropriate image using `context.watch<GenderService>()`, and add a play/stop audio button per step that invokes `QuranPlayerService.playAyah(surah, ayah)` for recitation steps that map to Quran verses. Images must be copied from `knowledge-center/assets/images/` into `assets/images/steps/` and declared in `pubspec.yaml` before the UI work begins. Placeholders (e.g. a grey silhouette container) should be used for the 5 missing images (female steps 1, 3, male/female steps 10–11). The `female_step_ 1.png` filename space bug must be fixed on copy.

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
