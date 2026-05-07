---
ticket: "T01"
artifact: plan
---

# Plan: T01

## Approach

Flutter/Dart app (D01), Android-first (D02). Work spans UI layout, Android platform channels, and Quran audio — three distinct blast radii. The plan groups into four independent-to-loosely-dependent slices ordered by risk and dependency:

1. **UI** — pure widget work, no platform risk; ships fast and de-risks the sprint early.
2. **Alarm** — highest platform risk (Android Doze, exact alarm, full-screen intent); isolated from other slices; tackled second so discoveries don't block UI.
3. **Notification** — builds on foreground-service infrastructure introduced in Alarm slice; delivers MediaStyle for audio and rich card for prayer events, resolving the FR14/FR15 overlap (MediaStyle = Quran audio only; rich static card = prayer alarm events per validate finding).
4. **Quran** — surah playback and bookmarks UX; depends on Notification slice (needs MediaStyle notification in place) and extends existing `QuranPlayerService` (D03, D07).

Single-layer flat task list per slice. **Recommended build order:** Slice 1 → Slice 2 (both independent, can run in parallel) → S3-T1 tech-select (parallelisable with Slice 2) → Slice 3 → Slice 4.

---

## Slices

### Slice 1 — UI
**Covers:** FR1–FR6 (Dashboard prayer card), FR7 (Quick Alarm page enhancement), FR9 (Islamic Dates extraction)  
**Key files (known from analysis):** `dashboard_screen.dart`, `quick_alarm_screen.dart`, routing layer  
**Done when:** All Dashboard card ACs pass, Quick Alarm shows today's times + toggles intact, Islamic Dates on own page with nav entry point.

### Slice 2 — Alarm
**Covers:** FR10 (Android alarm reliability), FR11 (full-screen alarm UI), FR12 (alarm sound)  
**Key files:** `notification_service.dart`, `AndroidManifest.xml`, alarm scheduling logic  
**Done when:** Alarm fires within ±5 s on Android 10/12/14 under Doze; full-screen UI appears with prayer name + time + dismiss; selected sound plays on trigger.

### Slice 3 — Notification
**Covers:** FR14 (notification bar / MediaStyle for Quran audio), FR15 (rich notification card for prayer events)  
**Key files:** `notification_service.dart`, `android/app/src/main/res/layout/` (RemoteViews), `QuranPlayerService`  
**Done when:** Quran audio shows MediaStyle notification with play/pause/stop; prayer alarm notification uses rich card with prayer name + time; no notification-style conflict at runtime.

### Slice 4 — Quran
**Covers:** FR13 (full surah playback), FR16–FR17 (bookmarks UX)  
**Key files:** `quran_player_service.dart`, `quran_screen.dart`, `quran_service.dart`  
**Done when:** "Play Surah" plays all ayahs sequentially via everyayah.com/Alafasy_128kbps (D03, D07); bookmarks list shows all saved entries; tapping a bookmark reliably navigates to correct surah+ayah.

---

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R01 | Android exact-alarm restriction on OEM devices (Samsung/Xiaomi battery saver kills `AlarmManager` despite `SCHEDULE_EXACT_ALARM`) | High | High | Use `AlarmManager.setAlarmClock` + request `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`; verify on emulator + physical device in Doze; document known OEM workarounds. |
| R02 | `USE_FULL_SCREEN_INTENT` behaviour changed on Android 14 (requires new permission declaration + user grant) | Medium | High | Declare `USE_FULL_SCREEN_INTENT` in manifest; runtime-check and prompt user to grant if on API 34+; fall back to heads-up notification if denied. |
| R03 | FR11/FR14/FR15 notification conflict (same alarm event could trigger three different notification styles) | High | Medium | Resolved in Approach: MediaStyle → Quran audio only; full-screen intent + rich static card → alarm events. Enforced by routing in `notification_service.dart`. Builder must not merge these paths. |
| R04 | `everyayah.com` CDN latency or downtime during surah playback | Low | High | Buffer first ayah before starting playback; surface a user-visible error if CDN unreachable; do not cache full surah (storage cost) — retry on network restore. |
| R05 | Flutter `MediaSession` / `MediaStyle` notification requires a platform channel or plugin — no first-party Flutter API | Medium | Medium | Evaluate `audio_service` package (well-maintained, handles foreground service + MediaSession) via `tech-select` before Slice 3 tasking. If plugin accepted, no custom platform channel needed. |
| R06 | Regression — ticket touches `notification_service.dart`, `quran_player_service.dart`, `quran_screen.dart`, `dashboard_screen.dart`, `quick_alarm_screen.dart`, routing, and `AndroidManifest.xml` across 4 slices | Medium | High | Verifier must run a regression pass against all existing features after each slice before advancing; builder must not touch files outside slice scope without flagging. |

**High×High risks:** R01, R02 (both mitigated; mitigations must be verified in acceptance criteria).  
**Med×High risks:** R02, R06 (both mitigated above).

---

## Tasks / Effort

### Slice 1 — UI  _(no dependencies)_

- [x] **S1-T1** Reposition prayer card to top of Dashboard (after header widget); remove "next prayer" label from widget tree. **1h**  
  _Done when:_ Card renders immediately below header in all scroll states; label string absent from widget tree.

- [x] **S1-T2** Redesign prayer card: headline typography for prayer name + time; body text for time-remaining; icon widget mapped to prayer period (Fajr/Sunrise/Dhuhr/Asr/Maghrib/Isha). **2h**  
  _Done when:_ Each of the 6 prayer periods shows the correct icon; name + time render in headline style; time-remaining in body style; no "next prayer" label.

- [x] **S1-T3** Wire prayer card tap → navigate to `QuickAlarmScreen` via named route. **1h**  
  _Done when:_ Tapping card (or time-remaining text) pushes `QuickAlarmScreen`; back navigation returns to Dashboard; no crash on rapid tap.

- [x] **S1-T4** Add today's full prayer schedule section to `QuickAlarmScreen` (names + times); existing alarm toggles must remain functional. **2h**  
  _Done when:_ Screen renders today's 6 prayer times alongside pre-existing toggles; toggling an alarm still schedules/cancels it correctly.

- [x] **S1-T5** Extract Islamic Dates section from Dashboard into a new `IslamicDatesScreen`; add a navigation entry point (link, action, or menu item) from Dashboard. **2h**  
  _Done when:_ Dashboard no longer renders Islamic dates inline; `IslamicDatesScreen` renders same data; a tappable element on Dashboard routes to it.

**Slice 1 subtotal: 8h**

---

### Slice 2 — Alarm  _(no dependencies)_

- [x] **S2-T1** Audit and fix Android alarm scheduling: switch to `AlarmManager.setAlarmClock`; declare `SCHEDULE_EXACT_ALARM`; trigger `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` intent on first alarm set; verify under Doze. **3h**  
  _Done when:_ Alarm fires within ±5 s on Android 10, 12, 14 (emulator Doze-forced + at least one physical device); `SCHEDULE_EXACT_ALARM` declared in manifest. Note: emulator-only Doze testing does not satisfy R01 mitigation — physical device required.

- [x] **S2-T2** Implement full-screen alarm UI (`USE_FULL_SCREEN_INTENT` + `AlarmFullScreenActivity`): turns screen on, shows over lock screen, displays prayer name + time + dismiss button; Android 14 runtime grant requested. **3h**  
  _Done when:_ On alarm trigger, full-screen activity launches regardless of lock state; prayer name + time visible; dismiss stops alarm; `USE_FULL_SCREEN_INTENT` declared in manifest; on API 34+ app requests grant and falls back to heads-up notification if denied.

- [x] **S2-T3** Wire alarm sound to user-selected sound: play on alarm trigger via `MediaPlayer`/`AudioManager`; fall back to system default ringtone if none selected; stop on dismiss. **2h**  
  _Done when:_ Alarm plays user-selected sound or system ringtone; sound stops on dismiss; silent if user explicitly muted.

**Slice 2 subtotal: 8h**

---

### Slice 3 — Notification  _(blocked-by: S2-T1, S2-T2 for foreground service infrastructure)_

- [x] **S3-T1** `tech-select`: evaluate `audio_service` package for MediaSession/MediaStyle foreground service; record decision as D08. **1h**  
  _Done when:_ D08 logged in `T01-decision-log.md`; either package added to `pubspec.yaml` or custom platform-channel approach documented with rationale.

- [x] **S3-T2** Implement MediaStyle notification for Quran audio: persistent notification with play/pause/stop actions while audio plays; dismisses when audio stops. **3h**  
  _Done when:_ Starting Quran playback shows a MediaStyle notification on Android 8+; controls (play/pause/stop) are functional from the notification shade; notification disappears when playback ends.

- [x] **S3-T3** Implement rich prayer alarm notification: custom `RemoteViews` or `BigPictureStyle` card showing prayer name + time; visually distinct from plain-text default; does not use MediaStyle. **3h**  
  _Done when:_ Prayer alarm notification renders prayer name + time in a designed card layout; no plain-text notification visible; layout consistent with app visual style; inspected via notification shade on Android 10+.

**Slice 3 subtotal: 7h**

---

### Slice 4 — Quran  _(blocked-by: S3-T2 for MediaStyle notification during surah playback)_

- [x] **S4-T1** Extend `QuranPlayerService` with sequential surah playback: auto-advance through all ayahs of the selected surah using everyayah.com/Alafasy_128kbps (D03, D07); expose play/pause/stop. **3h**  
  _Done when:_ Starting surah playback plays ayah 1→N sequentially; auto-advances on completion; stops at last ayah; play/pause/stop work from the in-screen UI. (Notification-bar controls wired in S3-T2/S4-T2 — not a gate here.)

- [x] **S4-T2** Add "Play Surah" UI control to Quran reader screen; show active-playback state while surah plays. **1h**  
  _Done when:_ "Play Surah" button visible in reader; tapping starts S4-T1 playback; button/icon reflects playing vs stopped state.

- [x] **S4-T3** Implement Bookmarks list UI: show all saved entries (surah name + ayah number + saved date); scrollable; empty state handled. **2h**  
  _Done when:_ Bookmarks list renders all entries from `QuranService` storage; each row shows surah name, ayah number, saved date; empty-state widget shown when no bookmarks; list is scrollable.

- [x] **S4-T4** Fix bookmark navigation: tapping a bookmark navigates to correct surah and reliably scrolls the reader to the bookmarked ayah. **2h**  
  _Done when:_ Tapping any bookmark opens the Quran reader at the correct surah and scrolls to the correct ayah within 1 s of load; tested across at least 3 different surah+ayah positions.

**Slice 4 subtotal: 8h**

---

## Effort Summary

| Slice | Tasks | Hours |
|-------|-------|-------|
| Slice 1 — UI | 5 | 8h |
| Slice 2 — Alarm | 3 | 8h |
| Slice 3 — Notification | 3 | 7h |
| Slice 4 — Quran | 4 | 8h |
| **Total** | **15** | **31h** |

## AC Coverage

| AC | Covered by |
|----|-----------|
| Prayer card at top, after header | S1-T1 |
| Prayer name + time in large text, no label | S1-T1, S1-T2 |
| Time-remaining in body text; tap navigates to Quick Alarm | S1-T2, S1-T3 |
| Prayer card icon matches prayer time | S1-T2 |
| Quick Alarm lists today's prayer times | S1-T4 |
| Islamic dates on own page; Dashboard clear | S1-T5 |
| Alarm fires reliably on Android 10/12/14 | S2-T1 |
| Full-screen alarm UI on trigger | S2-T2 |
| Selected alarm sound plays on trigger | S2-T3 |
| Quran "Play Surah" plays all ayahs sequentially | S4-T1, S4-T2 |
| Playback notification in notification bar with controls | S3-T2 |
| All notifications use rich design | S3-T3 |
| Bookmarks list shows all saved entries | S4-T3 |
| Tapping bookmark navigates reliably to correct surah + ayah | S4-T4 |

**Coverage: 14/14 ACs mapped.**

---

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
