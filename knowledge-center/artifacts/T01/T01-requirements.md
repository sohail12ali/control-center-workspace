---
ticket: "T01"
artifact: requirements
---

# Requirements: T01

## Functional Requirements

### Dashboard — Prayer Card Redesign
1. The upcoming-prayer card MUST be repositioned to appear immediately after the header (top of content area).
2. The "next prayer" label MUST be removed.
3. The current prayer name and its time MUST be displayed in large (headline) typography and MUST be the visual focal point of the card.
4. The time remaining until the next prayer MUST be displayed beneath the headline in body-size text.
5. The card MUST include an icon appropriate to the prayer time (e.g., Fajr → dawn icon, Dhuhr → sun, Maghrib → sunset, Isha → moon).
6. Tapping the time-remaining text MUST navigate the user to the Quick Alarm page.

### Quick Alarm Page
7. The existing `QuickAlarmScreen` MUST be enhanced (not replaced) to also display today's full prayer schedule (names + times) alongside the existing alarm toggles.

### Islamic Dates
9. The upcoming Islamic dates section MUST be extracted from the Dashboard into its own dedicated page.

### Alarm — Android Fix
10. Prayer alarms MUST trigger reliably on Android, including under Doze mode and battery optimization.

### Full-Screen Alarm
11. When a prayer alarm fires, a full-screen alarm UI MUST be shown (overlay/lock-screen style).

### Alarm Sound
12. When a prayer alarm fires, the user's selected alarm sound MUST play.

### Quran — Full Surah Playback
13. The Quran reader MUST provide an option to play an entire surah continuously, streaming from `everyayah.com` using the `Alafasy_128kbps` reciter (same as existing ayah playback).

### Notification Bar — Playback Status
14. While any audio is playing (Quran or alarm sound), a persistent notification MUST appear in the notification bar showing playback status (play/pause/stop controls).

### Android Notification Design
15. All app notifications MUST use a rich, visually designed layout (not plain default Android notification style). Prayer notifications MUST show the prayer name and time prominently in a card-style layout consistent with the app's visual design.

### Quran — Bookmarks
16. The bookmark feature MUST support multiple saved bookmarks (the storage layer already supports a list; the UI must expose it fully).
17. Navigating to a bookmark MUST reliably scroll/jump the reader to the correct surah and ayah position.

## Non-Functional Requirements
1. Alarm reliability: alarm MUST fire within ±5 seconds of scheduled time on Android 10+.
2. Audio playback MUST continue when the app is backgrounded.
3. UI changes MUST be consistent with the existing app design language/theme.
4. No regression to existing features.

## Acceptance Criteria
- [ ] Prayer card appears at the top of the Dashboard, immediately after the header.
- [ ] Prayer card shows prayer name + time in large text with no "next prayer" label.
- [ ] Prayer card shows time-remaining in body text; tapping navigates to Quick Alarm page.
- [ ] Prayer card icon matches the prayer time of day.
- [ ] Quick Alarm page lists all of today's prayer times.
- [ ] Islamic dates have their own page; Dashboard no longer shows them inline.
- [ ] Alarm fires reliably on Android (tested on Android 10, 12, 14).
- [ ] Full-screen alarm UI appears when alarm triggers.
- [ ] Selected alarm sound plays when alarm fires.
- [ ] Quran reader has a "Play Surah" option that plays all ayahs sequentially.
- [ ] Playback notification appears in notification bar with controls while audio is active.
- [ ] All notifications use the new rich design.
- [ ] Bookmarks list UI shows all saved bookmarks (surah + ayah + saved date).
- [ ] Tapping a bookmark navigates reliably to the correct surah and ayah in the reader.

## Out of Scope
- iOS alarm behavior changes (unless trivially shared with Android fix).
- New audio content / reciter additions.
- Backend/server changes unrelated to audio source selection.

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
