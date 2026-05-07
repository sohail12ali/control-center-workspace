---
ticket: "T01"
artifact: decision-log
---

# Decisions: T01

## D01 — Framework: Flutter, follow existing patterns {#D01}
**Decision:** The app is built with Flutter (Dart 3.11.5+). All new code MUST follow the established Flutter patterns already in the codebase.  
**Rationale:** User confirmed — check existing pattern and follow the same. Framework identified from `pubspec.yaml`.  
**Impact:** All implementation tasks target Flutter/Dart. No new framework dependencies unless decided via `tech-select`.

## D02 — Alarm platform scope: Android only {#D02}
**Decision:** Alarm reliability work is scoped to Android only. iOS alarm behaviour is out of scope for this ticket.  
**Rationale:** User has only tested Android platform to date.  
**Impact:** Alarm fixes focus on `AndroidScheduleMode`, `SCHEDULE_EXACT_ALARM`, Doze/battery-optimization handling. iOS-specific alarm paths untouched.

## D03 — Surah playback audio source: everyayah.com, follow existing reciter {#D03}
**Decision:** Surah playback MUST stream from `https://everyayah.com/data/{reciter}/{surah}{ayah}.mp3` — the same CDN and reciter (`Alafasy_128kbps`) already used by `QuranPlayerService`.  
**Rationale:** User said "see the code" — existing pattern in `lib/domain/services/quran_player_service.dart` (line 44–47) uses everyayah.com. Consistency is the goal.  
**Impact:** Surah playback builds on or extends `QuranPlayerService`; no new audio source negotiation needed.

## D04 — Bookmark UX gaps: multiple bookmarks + navigation fix {#D04}
**Decision:** The bookmark improvement MUST: (1) support multiple bookmarks (current implementation in `QuranService` stores a list but UI only exposes one effectively), and (2) fix navigation back to a bookmarked ayah so the reader scrolls/jumps correctly to the saved position.  
**Rationale:** User stated: "It does not handle multiple bookmarks and navigating back to bookmarked is not perfect."  Code in `lib/domain/services/quran_service.dart` (lines 189–223) supports a list in storage but the UI (`quran_screen.dart` lines 507–525) needs a proper bookmarks list view and reliable scroll-to-ayah.  
**Impact:** New "Bookmarks" list UI needed; `QuranScreen` navigation to surah+ayah must be reliable.

## D05 — Notification design: rich card with prayer name + time {#D05}
**Decision:** Android notifications MUST display a visually designed card showing the prayer name and time — not plain default notification text. Use `NotificationCompat.BigPictureStyle` or custom `RemoteViews` to match the app's card aesthetic.  
**Rationale:** User stated: "Make it a bit fancy — show prayer time and name in design card, time etc — current is just plain text."  
**Impact:** `notification_service.dart` notification build logic must be extended. Consider a custom `RemoteViews` layout in `android/app/src/main/res/layout/`.

## D06 — Quick Alarm page: enhance existing screen, add today's prayer times display {#D06}
**Decision:** The existing `QuickAlarmScreen` (`lib/features/alarms/quick_alarm_screen.dart`) MUST be enhanced to also show today's full prayer schedule (times + names) alongside the existing alarm toggles. It is not replaced — it is extended.  
**Rationale:** User said "See the page" — the existing page has alarm toggles; the ticket requirement adds today's schedule display. Extending keeps the alarm-toggle UX intact.  
**Impact:** `QuickAlarmScreen` gets a prayer-times section; `NextPrayerService` or `PrayerTimesService` injected for today's times.

## D07 — Quran audio reciter: Alafasy_128kbps (everyayah.com) {#D07}
**Decision:** All Quran audio (ayah and surah playback) MUST use the `Alafasy_128kbps` reciter on everyayah.com, consistent with the current `QuranPlayerService` default (line 11).  
**Rationale:** User said "see the code" — reciter is already set and in use.  
**Impact:** Surah playlist builder uses the same `_buildUrl(surah, ayah)` pattern; no reciter-selection UI change required in this ticket.

## D08 — MediaStyle/MediaSession package: audio_service {#D08}
**Decision:** Use `audio_service: ^0.18.15` for MediaSession + MediaStyle foreground notification during Quran audio playback. Do NOT write a custom Kotlin platform channel.  
**Rationale:** `just_audio` and `audio_session` are already in `pubspec.yaml` — they are `audio_service`'s peer dependencies. `audio_service` is the Flutter community standard for background audio + MediaStyle notifications and eliminates all custom platform-channel work. R05 mitigation confirmed: plugin accepted.  
**Impact:** `audio_service` added to `pubspec.yaml`. `QuranPlayerService` extended with an `AudioHandler` wrapper. Foreground service lifecycle and MediaSession metadata managed by the package. MediaStyle notification (play/pause/stop controls) delivered automatically on Android 8+.

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
