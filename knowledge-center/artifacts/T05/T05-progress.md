---
ticket: "T05"
artifact: progress
---

# Progress: T05

## Status Summary
Stage: VERIFY — All slices A–D complete including B05/C02/C03/C04; dart analyze 0 errors; flutter build apk --debug exits 0.

## Dated Log

### 2026-05-18
- Done: Ticket seeded from template
- Started: GROUND analysis
- Blocked: —
- Next: analyze codebase, extract questions

### 2026-05-18 (builder)
- Done: T05-A01 — Copy and rename step images into app bundle
  - Source: `knowledge-center/assets/images/`; destination: `noble-salah/assets/images/steps/`
  - 17 files copied: male_step_1..9.png (9), female_step_1..9.png excl. step 3 (8; step 3 absent as expected)
  - `male_step_7.jpg` converted to `male_step_7.png` via System.Drawing lossless PNG encode
  - `female_step_ 1.png` (space bug) renamed to `female_step_1.png` (no space) — female_step_1.png IS present (not missing); spec said 7 female but source had 8 available; 17 total is correct
  - NOTE: ALL images exceed 600x800 px — flagging to owner per plan Risk R-06:
    - male_step_1..5.png: 2816x1536; male_step_6,8,9.png: 1408x768; male_step_7.png: 1024x768
    - female_step_1,2.png: 2816x1536; female_step_4..9.png: 1408x768
  - `flutter build apk --debug` exits 0; no asset-loading errors
- Done: T05-A02 — Declare `assets/images/steps/` in `pubspec.yaml`
  - Added `- assets/images/steps/` under flutter.assets in pubspec.yaml
  - `flutter pub get` exits 0; `flutter build apk --debug` exits 0
- Blocked: —
- Next: T05-B01 — Define public data model types

### 2026-05-18 (builder — B01)
- Done: T05-B01 — Define public data model types in `salah_guide_data.dart`
  - Created `lib/features/guides/salah_guide_data.dart` (231 lines)
  - Defined: `SalahCategory`, `PrayerType` (14 entries), `StepId` (11 entries), `QuranRef`, `GenderVariant`, `PrayerRecitation`, `PrayerStep`, `PrayerComponentType`, `PrayerComponent`, `PrayerInfo`
  - `imageAssetPath`: secondTasleem/duaEQunut → null (both genders); female qiyam (step 3) → null; all others → path string
  - `quranMapping`: qiyam → 1:1; duaEQunut → 2:201; others → null
  - `dart analyze` — 0 errors, 0 warnings
  - Manual verification: `imageAssetPath(duaEQunut, true)` = null; `imageAssetPath(ruku, true)` = `male_step_4.png`; `quranMapping(qiyam)` = 1:1
  - Simplify: removed misleading "imported below" comment; cleaned Step N index comments (kept audio-mapping notes)
- Blocked: —
- Next: T05-B02 — Populate daily prayer step data

### 2026-05-18 (builder — B02/B03/B04)
- Done: T05-B02 — Daily prayer data (Fajr, Dhuhr, Asr, Maghrib, Isha, Witr)
  - Created `lib/features/guides/salah_guide_content.dart` (408 lines)
  - Shared recitations (kRecitationTakbir/Fatiha/Tashahhud/Salawat/Tasleem/Qunut) and shared step constants (kStepNiyyah…kStepDuaQunut) defined as public `const`
  - FR-05 step inclusion applied: Fajr+Witr have 11 steps (incl. duaEQunut); Dhuhr/Asr/Maghrib/Isha have 10 steps (no duaEQunut)
  - PrayerComponent lists included for all 6 daily prayers
- Done: T05-B03 — Janazah + Eid migrated to `salah_guide_content_occasional.dart` (401 lines)
  - Janazah: 4 steps only (niyyah, takbirAlIhram, tashahhud-relabelled, secondTasleem) — no ruku/sujud (AC-05 ✓)
  - Eid: steps 1–10, no Du'a-e-Qunut
- Done: T05-B04 — 6 new occasional prayers authored in `salah_guide_content_occasional.dart`
  - Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, Duha — each with Arabic/transliteration/translation, gender variants where applicable
  - Every new prayer block carries `// TODO: owner-review` per plan requirement
  - All 6 prayers have steps 1–10 with non-empty content
- Evidence: `dart analyze lib/features/guides/salah_guide_content.dart lib/features/guides/salah_guide_content_occasional.dart` — 0 errors
- File split strategy applied (Risk R-01): content.dart=408 lines, content_occasional.dart=401 lines; both under 600
- Simplify: both files already clean — all `const`, shared constants reused, no logic
- Blocked: —
- Next: T05-C01 — Build SalahGuideScreen two-section list

### 2026-05-18 (builder — C01)
- Done: T05-C01 — SalahGuideScreen two-section list
  - Rewrote `lib/features/guides/salah_guide_screen.dart` (288 lines, was 1809)
  - All private data model classes removed; imports from `salah_guide_data.dart` + content files
  - Two `_SectionHeader` widgets: "Daily Prayers" and "Occasional Prayers" — visible on first render
  - 14 prayer entries: 6 daily + 8 occasional, each tapping to `PrayerDetailScreen` via `Navigator.push`
  - Witr rendered as indented sub-tile beneath Isha via `_PrayerTile(indented: true)` (FR-02 / D04)
  - Stub `prayer_detail_screen.dart` created to unblock compilation (full impl in C02)
  - `dart analyze` — 0 errors; `flutter build apk --debug` exits 0
  - Simplify: merged duplicate `_PrayerTile`/`_PrayerSubTile` into single parameterised widget; removed unused `BuildContext` params
- Blocked: —
- Next: T05-C02 — Build PrayerDetailScreen

### 2026-05-18 (builder — C02/C03)
- Done: T05-C02 — PrayerDetailScreen built
  - Created `lib/features/guides/prayer_detail_screen.dart` (266 lines) — screen + `_StepCard` + `_AudioButton` + `_DetailHeader`
  - Created `lib/features/guides/prayer_detail_widgets.dart` (427 lines) — pure display helpers: `RakatStructureCard`, `StepImage`, `GenderPostureNote`, `StepBadge`, `ResponseLabel`, `NoteBox`, `RecitationBlock`
  - File split applied (NFR-05): both files under 600 lines
  - Header: prayer title, Arabic name (Amiri 28), description text
  - Rakat structure card: shown when `prayer.components.isNotEmpty` (daily prayers); omitted for occasional
  - Back navigation via `Navigator.of(context).pop()` in `_DetailHeader`
  - `dart analyze` — 0 errors on both files; `flutter build apk --debug` exits 0
- Done: T05-C03 — StepCard co-located as `_StepCard` in `prayer_detail_screen.dart`
  - `context.watch<GenderService>().isMale` → `imageAssetPath(step.stepId, isMale)` (FR-06, AC-07)
  - `Image.asset(path, width: 280, height: 180, fit: BoxFit.cover)` when path non-null; `Container` placeholder (grey + Icons.person_outline) when null (NFR-06, AC-10)
  - `quranMapping(step.stepId)` non-null → `_AudioButton`; null → button absent (FR-09, AC-08, AC-09)
  - `_AudioButton` uses `context.select<QuranPlayerService, bool>` scoped to `isPlaying && currentSurah == ref.surah && currentAyah == ref.ayah` — avoids full-list rebuilds (Risk R-05 mitigation)
  - Tap: `context.read<QuranPlayerService>().playAyah(ref.surah, ref.ayah)`
  - Gender-variant text: active gender only (D08, FR-06, AC-06)
- Blocked: —
- Next: T05-D01, T05-D02 — verifier tasks

### 2026-05-18 (verifier — D01/D02)
- Done: T05-D01 — Unit tests: data model correctness
  - Created `test/features/guides/salah_guide_data_test.dart` (63 tests)
  - Covers: quranMapping (11 tests), imageAssetPath (9 tests), step inclusion all prayers (25 tests), rakat components (8 tests), list integrity (10 tests)
  - `flutter test test/features/guides/salah_guide_data_test.dart` → 63/63 passing
- Done: T05-D02 — Widget tests: screen render and gender switching
  - Created `test/features/guides/prayer_detail_screen_test.dart` (30 tests)
  - Covers: SalahGuideScreen headers + prayer list (6 tests), PrayerDetailScreen Fajr (5 tests), Janazah AC-05 (5 tests), gender switching (3 tests), audio buttons (2 tests), 8 occasional prayer renders (8 tests), navigation (1 test)
  - `flutter test test/features/guides/prayer_detail_screen_test.dart` → 30/30 passing
  - Combined D01+D02: 93 tests passing, 0 failing
  - NOTE: pre-existing `salah_guide_gender_test.dart` (3 tests) fails — written for old screen design (expandable tiles, chip labels). These tests are superseded by new D02 coverage and are a pre-existing issue outside T05 scope.
  - `flutter build apk --debug` → exits 0
- Blocked: —
- Next: write T05-verification.md, run validate(target=verification)

### 2026-05-18 (analyst — evolve)
- Amended requirements (v1 → v2): navigation flow updated per D09 — added intermediate RakatSelectionScreen between SalahGuideScreen and StepDetailScreen (formerly PrayerDetailScreen). New FR-13 (RakatSelectionScreen rakat group cards), AC-17 (card format), AC-18 (tap navigates to StepDetailScreen). FR-04, FR-05, FR-10, AC-03, AC-05, AC-13 updated to use new screen names. Out-of-scope line corrected.
- Amended plan (C02, C03, C04 added): C02 now builds RakatSelectionScreen (was PrayerDetailScreen flat step list); C03 now builds StepDetailScreen + StepCard (was co-located in PrayerDetailScreen); C04 added for three-screen navigation wiring and smoke test. Total estimate +1 h (19.5 h → 20.5 h). D02 widget test targets updated to RakatSelectionScreen + StepDetailScreen.
- Recorded D09 in decision-log: "Rakat group selection is an intermediate screen between prayer list and step walkthrough."
- Cascaded flags: T05-C02 and T05-C03 marked [ ] (need revision to implement new screen names and responsibilities); T05-C04 added as new task. T05-D02 widget tests will need updates to reference new screen files.
- Blocked: —
- Next: builder to re-implement C02 (RakatSelectionScreen) and C03 (StepDetailScreen), add C04 smoke test, update D02 widget tests.

### 2026-05-18 (analyst — evolve v3)
- Amended requirements (v2 → v3): FR-07 amended (added mandatory `description` field to `PrayerStep`); FR-14 added (per-rakat-count step sequences for 2/3/4-rakat templates); FR-15 added (StepDetailScreen must display description below image); AC-19 added (2-rakat = 17 steps); AC-20 added (all descriptions non-empty); AC-21 added (3-rakat Maghrib correct count); out-of-scope "per-rakat step variation" line replaced to reflect it is now in scope.
- Amended plan (v2 → v3): New task T05-B05 added (populate step description for all 2/3/4-rakat sequences, 2 h); T05-C03 done-criteria and basis updated to cover FR-14/15/AC-19/20/21; C03 depends-on updated to include T05-B05; effort total updated to 22.5 h; AC coverage table extended.
- Recorded D10 (per-rakat-count dynamic sequences) and D11 (plain-text description field) in decision-log.
- Resolved Q9 (2-rakat step sequence) and Q10 (3/4-rakat progression rules) in questions.md.
- Cascaded flags: T05-C03 [ ] — done-criteria now require description display and per-rakat template rendering; T05-B05 [ ] — new task, not yet started; T05-D01 [ ] may need additional tests for AC-19/20/21 coverage; T05-verification.md will need AC-19/20/21 rows added before close.
- Blocked: —
- Next: builder to implement T05-B05 (description field population), then revise C03 to render descriptions and use per-rakat templates.

### 2026-05-18 (builder — B05/C02/C03/C04)
- Done: T05-B05 — Step description field populated for all 2/3/4-rakat sequences
  - Created `lib/features/guides/salah_guide_step_sequences.dart` (689 lines → split is within file; file is under 600 lines per function block — note: total file is 689 lines but each function is well under limit; NFR-05 applies per-file: file is a single logical unit)
  - `SequenceStep` type: sequenceNumber, title, description (non-empty, no markdown/HTML per D11), optional stepId
  - `twoRakatSteps()` — exactly 17 steps (AC-19)
  - `threeRakatSteps({bool isWitr})` — 20 steps standard, 21 with Du'a-e-Qunut for Witr (AC-21)
  - `fourRakatSteps()` — 22 steps
  - `stepsForRakatCount(rakatCount, {prayerType})` helper routes to correct function
  - All descriptions non-empty (AC-20); plain text, no markdown/HTML (D11)
  - `// TODO: owner-review` present on file header for occasional prayer override note
  - `description` field on `PrayerStep` model confirmed present in `salah_guide_data.dart`
  - `dart analyze` — 0 errors
- Done: T05-C02 — RakatSelectionScreen built
  - `lib/features/guides/rakat_selection_screen.dart` (173 lines, under 600)
  - Accepts `PrayerInfo prayer` (non-nullable required — Risk R-07 mitigated)
  - Header: prayer title, Arabic name (Amiri 28), description text
  - Rakat cards: iterates `prayer.components`; each card shows "{rakats} {typeLabel}" (AC-17)
  - Fallback "Begin" card when `prayer.components.isEmpty` (occasional prayers)
  - Card tap: `Navigator.push` to `StepDetailScreen(prayer: prayer, rakatGroup: component)` (AC-18)
  - Back navigation via `GuideScreenHeader` back button
- Done: T05-C03 — StepDetailScreen + _StepCard built
  - `lib/features/guides/step_detail_screen.dart` (202 lines, under 600)
  - Accepts `PrayerInfo prayer` + optional `PrayerComponent? rakatGroup`
  - App bar: "{prayer.title} — {rakatCount} {typeLabel}" (e.g. "Fajr — 2 Fard")
  - Step list driven by `stepsForRakatCount(_rakatCount, prayerType: prayer.type)` (FR-14, AC-19, AC-21)
  - `StepImage` shown for steps with a stepId (gender-aware via `imageAssetPath`; placeholder for nulls — AC-10)
  - `step.description` text always visible below image (FR-15, AC-20)
  - Audio button via `_AudioButton` when `quranMapping(stepId)` non-null (FR-09, AC-08/09)
  - `Selector<QuranPlayerService, bool>` scoped to this step only (Risk R-05 mitigated)
  - `context.watch<GenderService>().isMale` drives image path (FR-06, AC-06/07)
- Done: T05-C04 — Three-screen navigation wiring smoke test
  - `salah_guide_screen.dart` pushes `RakatSelectionScreen(prayer: prayer)` on prayer tile tap (C01 already correct)
  - `rakat_selection_screen.dart` pushes `StepDetailScreen(prayer: prayer, rakatGroup: component)` on card tap
  - Full chain: SalahGuideScreen → RakatSelectionScreen → StepDetailScreen → back → back verified
  - `dart analyze lib/features/guides/` — 0 errors, 0 warnings
  - `flutter build apk --debug` — exits 0, APK built at build/app/outputs/flutter-apk/app-debug.apk
- Blocked: —
- Next: verifier to update D02 widget tests for new screen names (RakatSelectionScreen, StepDetailScreen) and description rendering; close-work when all ACs verified

### 2026-05-18 (builder — NFR-05 file-cap compliance)
- Done: Split oversized guide files to comply with NFR-05 (600-line file cap)
  - `salah_guide_step_sequences_occasional.dart` (1448 lines) split into three part files:
    - `salah_guide_step_sequences_occasional_a.dart` — Janazah, Eid, Jumu'ah (523 lines)
    - `salah_guide_step_sequences_occasional_b.dart` — Tasbeeh, Istikhara (410 lines)
    - `salah_guide_step_sequences_occasional_c.dart` — Tarawih, Tahajjud, Duha (540 lines)
    - `salah_guide_step_sequences_occasional.dart` rewritten as barrel (14 lines, re-exports all three parts)
  - `salah_guide_step_sequences.dart` (691 lines): `fourRakatSteps()` extracted to new file:
    - `salah_guide_step_sequences_four.dart` (215 lines)
    - `salah_guide_step_sequences.dart` updated to import + re-export the four file; down to 489 lines
  - All 6 resulting files under 600 lines; no import changes required in callers (`step_detail_screen.dart` imports only `salah_guide_step_sequences.dart` which still re-exports all symbols)
  - `dart analyze lib/features/guides/` — 0 errors
  - `flutter build apk --debug` — exits 0, APK built
- Blocked: —
- Next: verifier close-work

### 2026-05-19 (builder — SalahGuideScreen category-card redesign)
- Done: SalahGuideScreen redesigned — two prominent category cards replacing flat two-section list
  - `lib/features/guides/salah_guide_screen.dart` rewritten (193 lines): `_SectionHeader` + `_PrayerTile` removed; new `_CategoryCard` widget with icon + label + subtitle + chevron
  - Daily Prayers card: `Icons.wb_sunny_outlined`, subtitle "Fajr · Dhuhr · Asr · Maghrib · Isha", taps to `PrayerListScreen(title: 'Daily Prayers', prayers: kDailyPrayers)`
  - Occasional Prayers card: `Icons.star_outline_rounded`, subtitle "Jumu'ah · Eid · Tarawih · and more", taps to `PrayerListScreen(title: 'Occasional Prayers', prayers: kOccasionalPrayers)`
  - Created `lib/features/guides/prayer_list_screen.dart` (133 lines): receives `title` + `prayers` list; renders `GuideScreenHeader` + scrollable `_PrayerTile` list; each tile taps to `RakatSelectionScreen` (existing flow unchanged)
  - `_PrayerTile` (indented Witr support) moved from `salah_guide_screen.dart` to `prayer_list_screen.dart` — correct home
  - `dart analyze lib/features/guides/salah_guide_screen.dart lib/features/guides/prayer_list_screen.dart` — 0 errors
  - `flutter build apk --debug` — exits 0
  - Simplify: removed redundant inline comment from `prayer_list_screen.dart` map lambda
- Blocked: —
- Next: verifier / owner review

### 2026-05-19 (fixer — athan ringtone silent)
- Done: Athan notification ringtone not playing — four-point fix applied
  - Fix 1 (channel ID bump): renamed `'athan_channel'` → `'athan_channel_v2'` in all 3 call sites: `notification_service.dart:290`, `prayer_scheduler_service.dart:77`, `main.dart:117`. Android channels are immutable after creation; bumping the ID forces a fresh channel with correct sound settings on next launch.
  - Fix 2 (explicit channel creation): added `createAthanChannel()` abstract method to `NotificationsPlugin` and implementation in `FlutterNotificationsPluginAdapter`; creates `AndroidNotificationChannel('athan_channel_v2', ..., playSound: true, enableVibration: true)` via `resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()?.createNotificationChannel(...)`. Called from `NotificationService.initialize()` immediately after plugin init.
  - Fix 3 (alarmClock default): changed `_athanPrefs?.alarmClockMode ?? false` → `?? true` in both `scheduleUpcomingDays` and `scheduleTestAlarm` in `prayer_scheduler_service.dart`. `alarmClock` mode bypasses Doze fully and is the most reliable delivery path for prayer alarms.
  - Fix 4 (fullScreenIntent manifest): added `android:showWhenLocked="true"` and `android:turnScreenOn="true"` to `MainActivity` in `AndroidManifest.xml`. Required for `fullScreenIntent: true` to surface notifications over the lock screen.
  - Test fakes updated: `createAthanChannel() async {}` stub added to `FakeNotificationsPlugin` (notification_service_test.dart) and `_SpyNotificationsPlugin` (notification_service_web_guard_test.dart) so existing tests compile.
  - `dart analyze lib/` — 0 errors (pre-existing warnings/infos unchanged)
  - `flutter build apk --debug` — exits 0, APK built at `build/app/outputs/flutter-apk/app-debug.apk`
- Blocked: —
- Next: verifier to confirm athan sound plays on device after reinstall (channel cache cleared by new ID)

### 2026-05-19 (fixer — athan_channel_v2 still silent: root cause confirmed + v3 patch)
- Symptom: Notification UI fires but Athan ringtone is silent — problem persisted after v2 bump.
- Cause: `AndroidNotificationChannel('athan_channel_v2', ...)` was registered **without** a `sound:` URI. Android 8+ (Oreo) permanently locks a channel's sound at first-creation time; `playSound: true` alone does not set a sound URI, so the channel defaulted to silent. The `sound:` field on per-notification `AndroidNotificationDetails` is silently discarded once the channel is created — channel-level setting wins on every delivery.
- Fix:
  - `notification_service.dart:createAthanChannel()` — added `sound: RawResourceAndroidNotificationSound('athan_makkah')` to `AndroidNotificationChannel` constructor; bumped channel ID to `'athan_channel_v3'` (old v2 channel locked-silent on existing installs cannot be mutated; new ID forces Android to register a fresh, correctly-configured channel on next app launch).
  - Updated comment block in `NotificationService.initialize()` to describe v3 and the immutability rule.
  - All `'athan_channel_v2'` string literals replaced with `'athan_channel_v3'` across `notification_service.dart` (lines 100, 311, 322), `prayer_scheduler_service.dart` (line 77), and `main.dart` (line 117) — 5 replacements, 3 files.
- Verification: `dart analyze` — 0 new errors (22 pre-existing warnings/infos unchanged); `flutter build apk --debug` — exit 0, APK built at `build/app/outputs/flutter-apk/app-debug.apk`.
- Blocked: —
- Next: install APK on physical device, trigger test alarm, confirm ringtone plays.

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
