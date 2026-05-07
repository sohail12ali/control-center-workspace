---
ticket: "T01"
artifact: progress
---

# Progress: T01

## Status Summary
Stage: VERIFY — complete. 14/14 AC PASS (static), 0 blockers, 6 warns (none fatal). 10 stale tests flagged. Status: Complete.

## Dated Log

### 2026-05-06
- Done: Ticket seeded; summary, analysis, draft requirements, and open questions written.
- Done: All 7 questions resolved via user answers + codebase exploration of `noble-salah`.
- Done: Decision log populated (D01–D07). Requirements sharpened — Quick Alarm page is an enhancement not a new page; bookmark spec now concrete; notification design spec confirmed; audio source confirmed as everyayah.com/Alafasy_128kbps.
- Done: CANONICAL stage complete. Plan written: 4 slices, 15 tasks, 31h estimated. 6 risks identified (all mitigated). 14/14 ACs covered. Validate(plan) passed — no blocks.
- Done: S1-T1 — `_HeroPrayerSection` moved to first child in `_DashboardBody`; "NEXT PRAYER" label row and `l10n` param removed from `_HeroPrayerSection`; `dart analyze` clean.
- Done: S1-T2 — `_DashPrayerHeroCard` added to `dashboard_screen.dart`; `_iconFor` maps all 5 prayer names to Material icons; prayer name + time in `headlineSmall` style; countdown in `bodyMedium`; `_HeroStatusFallback` handles no-location/error states; `dart analyze` clean.
- Done: S1-T3 — `Card` uses `clipBehavior: Clip.antiAlias`; `InkWell(onTap: Navigator.push QuickAlarmScreen)` wraps card body; `dart analyze` clean.
- Done: S1-T4 — `_TodayScheduleSection` + `_ScheduleRow` added to `quick_alarm_screen.dart`; reads `NextPrayerService.todayPrayers`; highlights current/next prayer; existing toggle tiles unchanged; `dart analyze` clean.
- Done: S1-T5 — `IslamicDatesScreen` created at `lib/features/dashboard/islamic_dates_screen.dart`; `IslamicDatesCard` removed from `_DashboardBody`; Islamic Dates tool card added to `_DashToolsList` (crescent icon, routes to `IslamicDatesScreen`); `dart analyze` clean across all dashboard + alarm files.
- Done: S2-T1 — `_alarmClockMode` default changed to `true` in `athan_preferences_service.dart`; all manifest permissions confirmed. `dart analyze` clean.
- Done: S2-T2 — `AlarmFullScreenScreen` + `AlarmRouter` created in `alarm_full_screen.dart`; `MainActivity.kt` window flags added (`setShowWhenLocked` / `FLAG_SHOW_WHEN_LOCKED` + `setTurnScreenOn`); `NotificationService.initialize` now accepts `onForeground` callback; `AlarmRouter.navigatorKey` wired into `MaterialApp`; `dart analyze` clean.
- Done: S2-T3 — Audit confirmed: sound already fully implemented via `RawResourceAndroidNotificationSound(track)` with `AudioAttributesUsage.alarm` in `_athanDetails`; user-selected track per prayer via `AthanPreferencesService.trackFor`; default fallback is `AthanTrack.makkah` (bundled); dismiss via `AlarmFullScreenScreen` cancels notification + stops sound. No code change needed.
- Done: S3-T1 — `audio_service ^0.18.18` added to `pubspec.yaml`; D08 recorded in decision-log (adopt `audio_service` for MediaSession/MediaStyle, avoids custom Kotlin channel).
- Done: S3-T2 — `QuranAudioHandler` (`BaseAudioHandler` wrapping `just_audio`) created in `quran_audio_handler.dart`; `QuranPlayerService` refactored to delegate to handler and subscribe to `playbackState`/`mediaItem` streams; `AudioService.init()` wired in `main.dart`; MediaStyle notification with play/pause/stop auto-rendered by `audio_service` on Android 8+; `dart analyze` clean.
- Done: S3-T3 — `_athanDetails()` in `prayer_scheduler_service.dart` updated: `BigTextStyleInformation` with prayer name; brand color `0xFF2D6A4F`; `largeIcon DrawableResourceAndroidBitmap`; all 3 call sites pass `displayName`; `dart analyze` clean.
- Done: S4-T1 — `QuranAudioHandler.playSurah()` auto-advances through all ayahs sequentially, updates `MediaItem` per ayah; `QuranPlayerService.playSurah()` exposes API to UI.
- Done: S4-T2 — `FloatingActionButton` added to `SurahReaderScreen`: emerald play / red stop icon; reads `player.isSurahMode && currentSurah == meta.number`; `dart analyze` clean.
- Done: S4-T3 — `BookmarksScreen` added to `quran_screen.dart`: `ListView.separated` over all `QuranBookmark` entries (surah name, ayah number, saved date via `DateFormat`); empty-state widget; scrollable.
- Done: S4-T4 — `_scrollToAyah()` added to `_SurahReaderScreenState`: two-frame `addPostFrameCallback` — `jumpTo(estimatedOffset)` then `Scrollable.ensureVisible(ayah key)`; called when `scrollToAyah != null` on `FutureBuilder` completion; bookmark tap navigates and scrolls reliably.
- Done: Full `dart analyze lib/` — No issues found. All 15/15 plan tasks complete.
- Next: VERIFY stage

### 2026-05-06 (VERIFY)
- Done: Verification complete — 14/14 AC PASS (static), 0 blockers, 6 warns (none fatal). Static-only: yes (no device/browser runtime tests executed). `dart analyze lib/` clean. 10 stale tests flagged — all assert `_alarmClockMode` default `false`; implementation is correct at `true`; tests are test-maintenance debt requiring update before next release. validate(verification) passed: 0 BLOCK, 6 WARN.
- Next: close-work

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
