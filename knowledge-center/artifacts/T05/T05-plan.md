---
ticket: "T05"
artifact: plan
status: ready
amended: 2026-05-18 (v3)
---

# Plan: T05 — Improve Salah Guide

## Approach

The redesign is executed in four vertically-sequenced slices that match the dependency graph: assets must land before UI can reference them; the data model must be stable before the UI consumes it; the two screen layers (list → detail → step) are built bottom-up so each can be independently tested.

This ordering follows the analysis finding that the existing `salah_guide_screen.dart` is a monolithic 1809-line file with all data, models, and UI co-located (Analysis: "Architecture is monolithic"). D03 (flat 11-step sequence) and D07 (per-prayer step inclusion) drive the data model design — a single canonical step enum with a per-prayer inclusion bitmask is the cleanest encoding. D02 (Navigator.push detail view) and D08 (active-gender-only rendering) directly shape the UI layer structure. D01 (QuranPlayerService CDN audio) and D06 (placeholder fallback) are integrated in the detail view slice without requiring new infrastructure.

**Amendment 2026-05-18 (D09):** The navigation hierarchy is now three levels: `SalahGuideScreen` → `RakatSelectionScreen` → `StepDetailScreen`. The former `PrayerDetailScreen` (which showed a flat step list) is replaced by two screens: `RakatSelectionScreen` (shows the prayer's rakat group cards with counts) and `StepDetailScreen` (shows the 11-step posture walkthrough). Slice C tasks are revised accordingly.

The approach is additive-then-replace: new files (`salah_guide_data.dart`, `rakat_selection_screen.dart`, `step_detail_screen.dart`) are built first, then `salah_guide_screen.dart` is stripped of its data and sub-widgets and replaced with the two-section list shell. This avoids a single high-risk "big bang" rewrite commit.

---

## Slices

### Slice A — Asset Pipeline

**Goal:** All step images are in the Flutter asset bundle and declared in `pubspec.yaml`; the builder can reference them by a deterministic naming scheme.

**Covers:** FR-08, NFR-02, AC-11, AC-12

**Work:**
- Copy `male_step_1.png` through `male_step_9.png` from `knowledge-center/assets/images/` to `noble-salah/assets/images/steps/`.
- Copy `male_step_7.jpg` → convert/rename to `male_step_7.png` (consistent extension per FR-08).
- Copy female step images, renaming `female_step_ 1.png` → `female_step_1.png` (space bug fix per FR-08).
- Note: `female_step_3.png`, `male_step_10.png`, `male_step_11.png`, `female_step_10.png`, `female_step_11.png` do not exist — no copy needed; placeholder logic in Slice C will handle them.
- Add `- assets/images/steps/` entry to `pubspec.yaml` flutter assets section.
- Run `flutter pub get` and verify no asset errors.

**Done-signal:** `flutter build apk --debug` exits 0; `assets/images/steps/` contains 16 files (9 male + 7 female — with step 7 as .png, step 1 female without space).

---

### Slice B — Data Model + Static Data

**Goal:** A standalone `salah_guide_data.dart` file contains all prayer types, step definitions, per-prayer inclusion maps, step-to-Quran mappings, and rakat structure summaries. No UI code. All 11 prayers are covered.

**Covers:** FR-05, FR-10, FR-11, FR-12, AC-04, AC-05, AC-14, AC-15 (partial)

**Work:**
- Define public types: `SalahCategory` (daily/occasional), `PrayerType` (enum of 11 prayers), `StepId` (enum of 11 steps), `StepData`, `GenderVariant`, `PrayerStep`, `PrayerInfo`, `PrayerComponent`.
- Add `imageAssetPath(StepId, bool isMale) → String?` helper — returns null for missing images (steps 10, 11 both genders; female steps 1, 3).
- Add `quranMapping(StepId) → QuranRef?` — returns `(surah, ayah)` for steps 3 and 11; null otherwise.
- Populate static data for all 11 prayers: Fajr, Dhuhr, Asr, Maghrib, Isha, Witr (daily); Jumu'ah, Janazah, Tasbeeh, Istikhara, Eid, Tarawih, Tahajjud, Duha (occasional).
  - Migrate existing Eid and Janazah step content from the current `salah_guide_screen.dart`.
  - Author new content for Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, Duha (recitations, transliterations, gender-variant text).
- Apply the FR-05 inclusion table as a `Set<StepId>` per prayer.
- Preserve `_PrayerComponent` / rakat structure data for the 5 daily prayers + Witr.
- Unit test: verify Fajr includes exactly the FR-05 steps; verify Janazah excludes Ruku/Sujud; verify step 11 maps to `(2, 201)`.

**Done-signal:** `salah_guide_data.dart` exists, compiles with no warnings, is ≤ 600 lines (if it exceeds 600 lines due to content volume, a `salah_guide_content.dart` companion holds the raw Arabic/transliteration strings and this file imports them — see Risk R-02). Unit tests pass.

---

### Slice C — Screen Layer (List → RakatSelection → StepDetail) *(amended v2)*

**Goal:** Three-level navigation hierarchy is fully functional: prayer list → rakat group selection → step walkthrough. Gender-aware images, audio buttons on steps 3 and 11, and rakat group cards on all prayers.

**Covers:** FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-09, FR-10, FR-13, NFR-01, NFR-03, NFR-04, NFR-05, NFR-06, AC-01 through AC-10, AC-13, AC-15, AC-16, AC-17, AC-18

**Work:**

**3a — `SalahGuideScreen` (list, two-section)**
- Replace the existing chip selector with a `ListView` containing two labelled `Section` groups.
- Daily section: Fajr, Dhuhr, Asr, Maghrib, Isha; Witr rendered as an indented sub-item beneath Isha.
- Occasional section: 8 prayers from FR-03 in stated order.
- Each row is a tappable `ListTile` / card that calls `Navigator.push(MaterialPageRoute(builder: (_) => RakatSelectionScreen(prayer: p)))`.
- Strip all data, model classes, and sub-widgets from `salah_guide_screen.dart`; import from `salah_guide_data.dart`.
- File must be ≤ 600 lines after strip.

**3b — `RakatSelectionScreen`** *(replaces former PrayerDetailScreen — amended v2)*
- New file `rakat_selection_screen.dart` (pushed screen, receives `PrayerInfo`).
- Shows prayer name, Arabic, description header.
- Renders a list of tappable rakat group cards derived from `prayer.components`. Each card shows "{count} {label}" (e.g. "2 Sunnat", "2 Fard").
- On card tap: `Navigator.push(MaterialPageRoute(builder: (_) => StepDetailScreen(prayer: prayer, rakatGroup: component)))`.
- For prayers with no `components` (empty list), render a single "Begin" card that navigates directly to `StepDetailScreen`.

**3c — `StepDetailScreen` + `StepCard` widget** *(formerly PrayerDetailScreen step list — amended v2)*
- New file `step_detail_screen.dart` (pushed screen, receives `PrayerInfo` and optional rakat group context).
- Shows prayer name and rakat group label in the app bar (e.g. "Fajr — 2 Sunnat").
- Renders a `ListView` of `StepCard` widgets for the prayer's applicable steps.
- `StepCard` reads `context.watch<GenderService>().isMale` to select image path and text variant.
- Displays `Image.asset(path)` when image exists; displays placeholder (`Container` with grey background + `Icons.person_outline` centred, same fixed dimensions) when `imageAssetPath` returns null.
- Displays play/stop `IconButton` when `quranMapping(stepId)` is non-null; hidden otherwise.
- Audio button calls `context.read<QuranPlayerService>().playAyah(surah, ayah)` (toggle built into service per D01).
- Audio state indicator: watches `context.watch<QuranPlayerService>()` to show play vs stop icon.

**Done-signal:** App hot-restarts cleanly; all 18 ACs are manually exercisable; `salah_guide_screen.dart` is ≤ 600 lines; no widget-test failures.

---

### Slice D — Tests

**Goal:** Automated safety net covering the data model and screen render paths.

**Covers:** AC-04, AC-05, AC-08, AC-09, AC-15 (indirect)

**Work:**
- Unit test `salah_guide_data.dart`: step inclusion correctness for Fajr (steps per table), Janazah (no Ruku/Sujud), Witr (includes step 11), Dhuhr (no step 11).
- Unit test `quranMapping`: step 3 → `(1, 1)`, step 11 → `(2, 201)`, step 1 → null.
- Unit test `imageAssetPath`: step 10 male → null (triggers placeholder), step 1 male → `'assets/images/steps/male_step_1.png'`.
- Widget test `SalahGuideScreen`: renders two section headers without throwing; all 14 prayer names are present in the widget tree.
- Widget test `RakatSelectionScreen` (Fajr): renders without throwing; rakat group cards present ("2 Sunnat", "2 Fard"). *(amended v2)*
- Widget test `StepDetailScreen` (Fajr): renders without throwing; step cards present; no audio button on Niyyah card; audio button present on Qiyam card. *(amended v2)*
- Widget test `StepCard` gender switch: pumping `GenderService` with `isMale = false` causes the widget to show female image path.

**Done-signal:** `flutter test` exits 0; all described test cases exist and pass.

---

## Tasks

### Slice A — Asset Pipeline

#### [x] T05-A01 — Copy and rename step images into app bundle (1.5 h)
- Copy `male_step_1.png` through `male_step_9.png` from `D:\Workspace\control-center-workspace\knowledge-center\assets\images\` to `D:\Workspace\noble-wave\noble-salah\assets\images\steps\`.
- Convert `male_step_7.jpg` → `male_step_7.png` (lossless PNG export; verify visually against JPEG original; note dimensions in progress.md).
- Copy female step images; rename `female_step_ 1.png` → `female_step_1.png` (remove leading space).
- Do NOT copy `female_step_3.png` (does not exist); placeholders for steps 3, 10, 11 handled in Slice C.
- Record actual pixel dimensions of all images in progress.md; flag to owner if any image exceeds 600×800 px.
- **Done-criteria:** `assets/images/steps/` contains exactly 16 files: `male_step_1.png` … `male_step_9.png` (all `.png`), `female_step_1.png` … `female_step_9.png` excluding step 3 (`female_step_3.png` absent — 7 female files). File `female_step_ 1.png` (with space) does not exist in the destination.
- **Basis:** FR-08, AC-11, AC-12; direct file-copy work. ~30 min copy + ~30 min conversion verification + ~30 min dimension checks.
- **Depends on:** —

#### [x] T05-A02 — Declare `assets/images/steps/` in `pubspec.yaml` (0.5 h)
- Add `- assets/images/steps/` under the `flutter: assets:` block in `pubspec.yaml`.
- Run `flutter pub get`; confirm exit 0 with no asset warnings.
- Run `flutter build apk --debug`; confirm exit 0.
- **Done-criteria:** `pubspec.yaml` contains the `assets/images/steps/` entry; `flutter build apk --debug` exits 0 with no asset-loading errors.
- **Basis:** FR-08, AC-11; single-line pubspec edit + build verification.
- **Depends on:** T05-A01

---

### Slice B — Data Model + Static Data

#### [x] T05-B01 — Define public data model types (1.5 h)
- Create `lib/features/guides/salah_guide_data.dart`.
- Define: `SalahCategory` enum (`daily`, `occasional`), `PrayerType` enum (14 entries: fajr, dhuhr, asr, maghrib, isha, witr, jumuah, janazah, tasbeeh, istikhara, eid, tarawih, tahajjud, duha — 6 daily + 8 occasional), `StepId` enum (11 entries: niyyah, takbirAlIhram, qiyam, ruku, itidal, firstSujud, jalsa, secondSujud, tashahhud, secondTasleem, duaEQunut).
- Define: `QuranRef` (surah, ayah fields), `GenderVariant` (maleDescription, femaleDescription), `PrayerStep` (stepId, title, action, recitation?, genderVariant?), `PrayerComponent` (type, rakats), `PrayerInfo` (type, category, title, arabic, description, steps, components).
- Add `String? imageAssetPath(StepId stepId, bool isMale)` top-level function implementing the full null-return matrix (steps 10, 11 both genders → null; female step 1 → null; female step 3 → null; all others → `assets/images/steps/{gender}_step_{n}.png`).
- Add `QuranRef? quranMapping(StepId stepId)` returning `QuranRef(1, 1)` for qiyam, `QuranRef(2, 201)` for duaEQunut, null for all others.
- **Done-criteria:** File compiles (`dart analyze` 0 errors); `imageAssetPath(StepId.duaEQunut, true)` returns null; `quranMapping(StepId.qiyam)` returns surah 1; `imageAssetPath(StepId.ruku, true)` returns `'assets/images/steps/male_step_4.png'`.
- **Basis:** FR-05, FR-07, FR-09, FR-12, D03, D07; type definition work. 1.5 h.
- **Depends on:** —

#### [x] T05-B02 — Populate daily prayer step data (Fajr, Dhuhr, Asr, Maghrib, Isha, Witr) (2 h)
- In `salah_guide_data.dart` (or companion `salah_guide_content.dart` if file approaches 600 lines), define `PrayerInfo` constants for the 6 daily prayers.
- Apply FR-05 inclusion table: each prayer's `steps` list contains only the `StepId`s marked `yes` for that prayer.
- Migrate existing step text (recitations, gender variants) from `salah_guide_screen.dart` private constants for Fajr, Dhuhr, Asr, Maghrib, Isha, Witr.
- Include `PrayerComponent` lists (Sunnah + Fard counts) for all 5 daily prayers and Witr.
- Flag each step's `genderVariant` where applicable using existing `_GenderVariant` data from the old file.
- **Done-criteria:** All 6 prayers compile with correct step counts matching FR-05 table (e.g., Fajr has step 11 / Du'a-e-Qunut; Dhuhr/Asr/Maghrib/Isha do not; Witr has step 11); rakat component data present for all 6.
- **Basis:** FR-02, FR-05, FR-10, FR-12; data migration + authoring. 2 h.
- **Depends on:** T05-B01

#### [x] T05-B03 — Migrate existing Occasional Prayer data (Janazah, Eid) (1 h)
- Define `PrayerInfo` constants for Janazah and Eid by migrating from `_kJanazahSections` / `_kEidSections` in the existing `salah_guide_screen.dart`.
- Apply FR-05 inclusion table: Janazah excludes Ruku (step 4), I'tidal (step 5), First Sujud (step 6), Jalsa (step 7), Second Sujud (step 8), Du'a-e-Qunut (step 11).
- Customise step 9 (Tashahhud) and step 10 (Tasleem) labels for Janazah to reflect salam-sequence wording.
- **Done-criteria:** Janazah `PrayerInfo.steps` does not contain `StepId.ruku`, `StepId.firstSujud`, `StepId.jalsa`, or `StepId.secondSujud`; Eid `PrayerInfo.steps` matches FR-05 (all standard steps except step 11).
- **Basis:** FR-05, FR-11, AC-05, D07; data migration. 1 h.
- **Depends on:** T05-B01

#### [x] T05-B05 — Populate step `description` field for all 2/3/4-rakat sequences *(added v3)* (2 h)
- For every step in the 2-rakat, 3-rakat, and 4-rakat canonical templates (FR-14), populate the `description` field with the plain-English instruction text provided by the owner.
- Source: owner-provided 17-step sequence (2-rakat template, 2026-05-18). 3-rakat and 4-rakat templates follow the rakat progression rules from FR-14.
- `description` must be a single concatenated plain-text string: physical action + recitation text. No markdown, no HTML (D11).
- Ensure no step in any prayer sequence has an empty or null `description` (AC-20).
- Carry description text through to the per-prayer `PrayerStep` instances in `salah_guide_content.dart` and `salah_guide_content_occasional.dart`.
- **Done-criteria:** Every `PrayerStep` instance across all prayer data files has a non-empty `description` string. `dart analyze` exits 0. AC-19 (2-rakat = 17 steps), AC-20 (all descriptions non-empty), and AC-21 (3-rakat Maghrib correct count) are satisfiable by the data.
- **Basis:** FR-07 (amended v3), FR-14, FR-15, AC-19, AC-20, AC-21, D10, D11; data enrichment task. 2 h.
- **Depends on:** T05-B01, T05-B02, T05-B03, T05-B04

#### [x] T05-B04 — Author new Occasional Prayer content (Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, Duha) (3 h)
- Author `PrayerInfo` constants for all 6 prayers. Each prayer requires: Arabic title, description, step list (per FR-05 inclusion table — all 6 have full step sequences except step 11), recitation text for each step (Arabic + transliteration + translation), gender-variant posture descriptions.
- Recitations use standard general-practice Islamic sources; mark each authored block with `// TODO: owner-review` inline comment.
- **Done-criteria:** All 6 prayers compile; each has at least steps 1–10 with non-empty recitation/action text; `// TODO: owner-review` comment is present on each authored prayer block; AC-14 is satisfiable (prayers are navigable).
- **Basis:** FR-03, FR-11, AC-14, Risk R-02; new content authoring. 3 h (most effort-intensive data task).
- **Depends on:** T05-B01

---

### Slice C — Screen Layer

#### [x] T05-C01 — Build `SalahGuideScreen` two-section list (2 h) *(tap target updated to RakatSelectionScreen — amended v2)*
- Replace the chip selector and `AnimatedSwitcher` in `salah_guide_screen.dart` with a `ListView` containing two `_SectionHeader` widgets and prayer `ListTile` cards.
- Daily section: Fajr, Dhuhr, Asr, Maghrib, Isha as full-height cards; Witr as an indented sub-card beneath Isha.
- Occasional section: 8 prayers from FR-03 in listed order.
- Each card tap: `Navigator.push(context, MaterialPageRoute(builder: (_) => RakatSelectionScreen(prayer: info)))`. *(was PrayerDetailScreen)*
- Import all prayer data from `salah_guide_data.dart`; explicitly delete all private class definitions from `salah_guide_screen.dart` after confirming they are fully replaced by imports.
- **Done-criteria:** `salah_guide_screen.dart` is ≤ 600 lines; both section headers are visible on initial load; all 14 prayer entries are present; tapping any entry pushes `RakatSelectionScreen`; back navigation returns to list without crash.
- **Basis:** FR-01, FR-02, FR-03, FR-04, NFR-05, AC-01, AC-02, AC-03; UI rebuild. 2 h.
- **Depends on:** T05-B01, T05-B02, T05-B03, T05-B04

#### [x] T05-C02 — Build `RakatSelectionScreen` *(was PrayerDetailScreen — needs revision per D09 — amended v2)* (1.5 h)
- Create `lib/features/guides/rakat_selection_screen.dart` (replaces `prayer_detail_screen.dart`).
- Accept `PrayerInfo prayer` as constructor parameter; add `assert(prayer != null)` guard (Risk R-07 mitigation).
- Header: prayer title (large), Arabic name, description text.
- Rakat group cards: iterate `prayer.components`; for each component render a tappable card displaying "{component.rakats} {component.typeLabel}" (e.g. "2 Sunnat", "2 Fard").
- On card tap: `Navigator.push(context, MaterialPageRoute(builder: (_) => StepDetailScreen(prayer: prayer, rakatGroup: component)))`.
- If `prayer.components.isEmpty`: render a single "Begin" card that navigates to `StepDetailScreen(prayer: prayer, rakatGroup: null)`.
- **Done-criteria:** RakatSelectionScreen renders for Fajr (shows "2 Sunnat" and "2 Fard" cards, each tappable), Janazah (shows at least one card), and any occasional prayer without throwing. Tapping a card pushes StepDetailScreen. Back navigation from RakatSelectionScreen returns to SalahGuideScreen without crash. AC-13, AC-17 satisfied.
- **Basis:** FR-04, FR-10, FR-13, AC-03, AC-13, AC-17, AC-18, D02, D09; new screen. 1.5 h.
- **Depends on:** T05-B02, T05-B03, T05-B04, T05-C01

#### [x] T05-C03 — Build `StepDetailScreen` + `StepCard` widget *(was step list inside PrayerDetailScreen — amended v2)* (2.5 h)
- Create `lib/features/guides/step_detail_screen.dart`.
- Accept `PrayerInfo prayer` and optional `PrayerComponent? rakatGroup` as constructor parameters.
- App bar title: "{prayer.title} — {rakatGroup?.typeLabel ?? prayer.title}" (e.g. "Fajr — 2 Sunnat").
- Render a `ListView` of `StepCard(step: s, prayer: prayer)` for each step in `prayer.steps`.
- Create `lib/features/guides/step_card.dart` (or co-locate if ≤ 600 lines combined).
- `context.watch<GenderService>().isMale` → select image path via `imageAssetPath(step.stepId, isMale)`.
- If path non-null: `Image.asset(path, width: kStepImageWidth, height: kStepImageHeight, fit: BoxFit.cover)`.
- If path null: `Container(width: kStepImageWidth, height: kStepImageHeight, color: Colors.grey.shade300, child: Center(child: Icon(Icons.person_outline)))` (NFR-06).
- Audio button: `quranMapping(step.stepId)` non-null → show `IconButton`; null → `SizedBox.shrink()`.
- Audio `IconButton`: uses `Selector<QuranPlayerService, bool>` scoped to `isPlaying && currentSurah == ref.surah && currentAyah == ref.ayah` (Risk R-05 mitigation); shows `Icons.stop` when playing this step, `Icons.play_arrow` otherwise.
- Tap: `context.read<QuranPlayerService>().playAyah(ref.surah, ref.ayah)`.
- Gender-variant text: render only the active gender's `genderVariant` text.
- Display `step.description` text below the posture image (or placeholder) for every step (FR-15, AC-20).
- Step list is generated per rakat-count template from `PrayerInfo.rakatCount` (FR-14): use the 2/3/4-rakat canonical sequences from FR-14 rather than the raw flat `prayer.steps` list.
- **Done-criteria:** With `isMale = true`, step 1 shows male image; step 10 shows placeholder; step 3 shows audio button; step 1 shows no audio button. With `isMale = false`, step 1 shows placeholder (female_step_1 missing), step 2 shows female image. `Selector` wraps the audio icon (not the whole card). Back navigation from StepDetailScreen returns to RakatSelectionScreen. AC-18 satisfied. Step description visible below each image (AC-20). A 2-rakat entry point shows exactly 17 steps (AC-19). A 3-rakat Maghrib entry point shows correct step count per template (AC-21).
- Run `flutter run --profile`; navigate to a prayer → rakat group → step screen; log first-frame build time in progress.md as evidence for AC-16.
- **Basis:** FR-05, FR-06, FR-07 (amended v3), FR-09, FR-14, FR-15, NFR-04, NFR-06, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-16, AC-18, AC-19, AC-20, AC-21, D01, D06, D08, D09, D10, D11; new screen + widget. 2.5 h.
- **Depends on:** T05-A01, T05-A02, T05-B01, T05-B05, T05-C02

#### [x] T05-C04 — Wire three-screen navigation end-to-end and smoke test (1 h) *(added v2)*
- Verify the full navigation chain compiles and runs: SalahGuideScreen → RakatSelectionScreen → StepDetailScreen → back → back.
- Ensure `Navigator.push` calls in C01 and C02 reference the correct screen constructors.
- Manual smoke test: tap Fajr → verify "2 Sunnat" and "2 Fard" cards appear → tap "2 Fard" → verify step list appears with Fajr steps → back twice → back at list.
- Manual smoke test: tap Janazah → verify rakat/begin card(s) appear → tap → verify Janazah steps (no Ruku/Sujud) appear.
- **Done-criteria:** Full three-screen navigation chain works without crash for at least Fajr and Janazah. AC-03, AC-17, AC-18 all manually verified and noted in progress.md.
- **Basis:** FR-04, FR-13, AC-03, AC-17, AC-18, D09; integration wiring. 1 h.
- **Depends on:** T05-C01, T05-C02, T05-C03

---

### Slice D — Tests

#### [x] T05-D01 — Unit tests: data model correctness (1.5 h)
- Create `test/features/guides/salah_guide_data_test.dart`.
- Test `stepInclusion`: Fajr includes exactly {niyyah, takbirAlIhram, qiyam, ruku, itidal, firstSujud, jalsa, secondSujud, tashahhud, secondTasleem, duaEQunut} (all 11); Dhuhr includes all except duaEQunut (10 steps); Janazah includes {niyyah, takbirAlIhram, tashahhud, secondTasleem} (4 steps — steps 3–8 and 11 excluded); Witr includes all 11.
- Test `quranMapping`: step qiyam → surah 1 ayah 1; step duaEQunut → surah 2 ayah 201; step niyyah → null.
- Test `imageAssetPath`: `(StepId.ruku, true)` → `'assets/images/steps/male_step_4.png'`; `(StepId.duaEQunut, true)` → null; `(StepId.niyyah, false)` → null (female step 1 missing); `(StepId.niyyah, true)` → `'assets/images/steps/male_step_1.png'` (male step 1 EXISTS — confirms only female is missing, not male); `(StepId.ruku, false)` → `'assets/images/steps/female_step_4.png'`.
- **Done-criteria:** `flutter test test/features/guides/salah_guide_data_test.dart` exits 0; all assertions pass; no skipped tests.
- **Basis:** AC-04, AC-05, AC-09; pure unit tests. 1.5 h.
- **Depends on:** T05-B01, T05-B02, T05-B03, T05-B04

#### [x] T05-D02 — Widget tests: screen render and gender switching (2 h) *(screen names updated — amended v2)*
- Create `test/features/guides/salah_guide_screen_test.dart`, `test/features/guides/rakat_selection_screen_test.dart`, and `test/features/guides/step_detail_screen_test.dart`.
- `SalahGuideScreen` test: pump with mock providers; verify "Daily Prayers" and "Occasional Prayers" headers present; verify all 14 prayer names in widget tree; verify Witr appears after Isha in render order.
- `RakatSelectionScreen` (Fajr) test: verify "2 Sunnat" and "2 Fard" cards present and tappable. *(amended v2 — was PrayerDetailScreen rakat card test)*
- `StepDetailScreen` (Fajr) test: verify step card for "Niyyah" has no audio `IconButton`; verify step card for "Qiyam" / Al-Fatiha has an audio `IconButton`. *(amended v2 — was inside PrayerDetailScreen test)*
- `StepCard` gender test: provide `FakeGenderService(isMale: false)`; verify card for step 4 (Ruku) uses `female_step_4.png`; toggle to `isMale: true`; verify `male_step_4.png` used; verify step 1 female → placeholder container (not `Image.asset`).
- Mock `QuranPlayerService` with `FakeQuranPlayerService` (extends `ChangeNotifier`, stubs `playAyah`, `isPlaying = false`).
- **Done-criteria:** `flutter test test/features/guides/` exits 0; all described assertions present and passing; no real network calls made.
- **Basis:** AC-01, AC-06, AC-07, AC-08, AC-09, AC-13, AC-17, Risk R-04 mitigation; widget tests. 2 h.
- **Depends on:** T05-C01, T05-C02, T05-C03, T05-C04

---

## Effort

| Task | Slice | Estimate | Basis |
|------|-------|----------|-------|
| T05-A01 — Copy and rename step images | A | 1.5 h | File copy + JPEG→PNG conversion + dimension check |
| T05-A02 — Declare assets in pubspec.yaml | A | 0.5 h | Single-line edit + build verification |
| T05-B01 — Define public data model types | B | 1.5 h | Type definitions + 2 helper functions |
| T05-B02 — Populate daily prayer data | B | 2 h | Data migration (6 prayers) from existing file |
| T05-B03 — Migrate Janazah + Eid data | B | 1 h | Data migration (2 prayers) from existing file |
| T05-B04 — Author 6 new Occasional Prayer contents | B | 3 h | New content authoring (most effort-intensive) |
| T05-B05 — Populate step description field for 2/3/4-rakat sequences | B | 2 h | Data enrichment — owner-provided text applied to all templates |
| T05-C01 — Two-section list screen (tap → RakatSelectionScreen) | C | 2 h | UI rebuild of SalahGuideScreen; tap target updated |
| T05-C02 — RakatSelectionScreen *(was PrayerDetailScreen)* | C | 1.5 h | New intermediate screen with rakat group cards |
| T05-C03 — StepDetailScreen + StepCard *(was step list in PrayerDetailScreen)* | C | 2.5 h | New step walkthrough screen + gender/audio widget |
| T05-C04 — Three-screen navigation wiring + smoke test *(added v2)* | C | 1 h | End-to-end integration verification |
| T05-D01 — Unit tests: data model | D | 1.5 h | Pure unit tests, no mocking needed |
| T05-D02 — Widget tests: screens + gender | D | 2 h | Widget tests with fake providers |
| **Total** | | **22.5 h** | *(+2 h from B05 added v3)* |

### Acceptance Criterion Coverage

| AC | Task(s) covering it |
|----|---------------------|
| AC-01 Daily + Occasional sections present | T05-C01, T05-D02 |
| AC-02 Witr beneath Isha, not elsewhere | T05-C01, T05-D02 |
| AC-03 Prayer tap → RakatSelectionScreen; rakat card tap → StepDetailScreen; back chain works | T05-C01, T05-C02, T05-C04 |
| AC-04 Fajr shows exactly its applicable steps | T05-B02, T05-D01 |
| AC-05 Janazah excludes Ruku / Sujud | T05-B03, T05-D01 |
| AC-06 Female gender → female image + text only | T05-C03, T05-D02 |
| AC-07 Gender change → immediate re-render | T05-C03, T05-D02 |
| AC-08 Audio button triggers playback; second tap stops | T05-C03, T05-D02 |
| AC-09 No audio button on non-Quran steps | T05-B01, T05-C03, T05-D02 |
| AC-10 Missing images render as placeholder (no exception) | T05-B01, T05-C03, T05-D02 |
| AC-11 pubspec.yaml declares steps/; build succeeds | T05-A01, T05-A02 |
| AC-12 female_step_1.png (no space); male_step_7.png exists | T05-A01 |
| AC-13 Fajr RakatSelectionScreen shows "2 Sunnat" and "2 Fard" tappable cards *(amended v2)* | T05-B02, T05-C02, T05-C04 |
| AC-14 New occasional prayers present and navigable | T05-B04, T05-C01 |
| AC-15 salah_guide_screen.dart ≤ 600 lines; data file exists | T05-C01, T05-B01 |
| AC-16 StepDetailScreen first frame ≤ 300 ms *(amended v2)* | T05-C03 (builder self-report) |
| AC-17 Rakat group cards display "{count} {label}" format *(added v2)* | T05-C02, T05-C04 |
| AC-18 Tapping rakat group card navigates to StepDetailScreen with correct step list *(added v2)* | T05-C02, T05-C03, T05-C04 |
| AC-19 2-rakat prayer shows exactly 17 steps *(added v3)* | T05-B05, T05-C03 |
| AC-20 All step descriptions non-empty *(added v3)* | T05-B05, T05-C03 |
| AC-21 3-rakat Maghrib has correct step count per template *(added v3)* | T05-B05, T05-C03 |

---

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|----|------|-----------|--------|------------|-------|
| R-01 | `salah_guide_data.dart` exceeds 600-line limit (NFR-05) due to Arabic/transliteration text volume for 11 prayers × up to 11 steps each | High | Med | Split into two files: `salah_guide_data.dart` holds types + inclusion maps + helper functions (structural); `salah_guide_content.dart` holds raw string constants (Arabic, transliteration, translation). Both files are imported by the UI. Each file is individually capped at 600 lines. If content alone exceeds 600 lines, further split by category (daily / occasional). NFR-05 permits unlimited aggregate lines across files. | Builder |
| R-02 | Content for 6 new Occasional Prayers (Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, Duha) is missing entirely from the codebase; authoring inaccurate Arabic or transliteration is a silent correctness risk | Med | High | Builder uses well-established Islamic references (standard Hanafi/general-practice texts) for recitation text. All new content is flagged with a `// TODO: owner-review` comment in code. Owner (anjum@hu-manity.co) performs a content review pass before the verification stage. AC-14 confirms navigability but verifier explicitly notes content accuracy is owner-gated. | Owner (content review) / Builder (authoring) |
| R-03 | `male_step_7.jpg` → `.png` conversion may degrade image quality or fail silently (lossy JPEG re-encode into PNG wrapper) | Med | Med | Builder opens the JPEG in an image tool and exports as PNG losslessly (PNG is lossless by definition; the risk is only if the tool introduces a second JPEG compression step). If the original JPEG has artefacts, the builder notes this in progress.md and the PNG copy is visually compared against the source. AC-12 requires the consistent-extension file to exist; no quality metric is formally gated. | Builder |
| R-04 | Audio CDN (everyayah.com) unavailability or latency causes AC-08 timing assertion (1 s) to flake during widget or integration tests | Med | Med | Widget test mocks `QuranPlayerService` (override `isPlaying` via a `FakeQuranPlayerService`). The 1-second timing clause in AC-08 applies to profile-mode manual verification on device, not to automated tests. Builder documents mock strategy in the test file. | Builder |
| R-05 | `context.watch<QuranPlayerService>()` in every `StepCard` triggers full list rebuilds on every CDN buffer event, causing jank | Med | Low | Scope the watch to the minimal subtree — either use `Selector<QuranPlayerService, bool>` that compares only `isPlaying && currentSurah == stepSurah && currentAyah == stepAyah`, or hoist the watch to the play-button widget only. Confirmed acceptable per NFR-04 (one-frame latency applies to gender changes, not audio state). | Builder |
| R-06 | Actual step image dimensions are larger than the estimated 300×400 px, pushing decoded memory above the 20 MB provisional budget (NFR-02) | Low | Med | Builder measures actual image dimensions during Slice A and records them in progress.md. If any image exceeds 600×800 px, builder flags to owner before continuing. UI uses `Image.asset` with explicit `width` and `height` to constrain decoded size. | Builder |
| R-07 | Witr is rendered as a sub-item beneath Isha (FR-02); if the sub-item tap constructs a `MaterialPageRoute` with a null or incorrectly scoped `PrayerInfo`, the push crashes | Low | High | Witr is a full `PrayerInfo` entry in the static data list — it is not a UI-only sub-item. The list widget renders it with visual indentation but passes the same `PrayerInfo` object to `Navigator.push` as every other prayer. No special null path exists. Builder adds an assert in `PrayerDetailScreen` constructor: `assert(prayer != null)`. | Builder |

---

## Dependencies
- Blocks: —
- Blocked by: — (no blocked upstream tickets; `GenderService` and `QuranPlayerService` are already registered in `main.dart` and out of scope for modification)

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
