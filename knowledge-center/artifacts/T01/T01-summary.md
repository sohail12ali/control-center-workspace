---
tags: [completed]
status: Complete
ticket: "T01"
---

# T01: Prayer, Alarm & Quran Feature Enhancements

**Status:** Complete  
**Stage:** VERIFY — Done  
**Owner:** Noble Wave  
**Created:** 2026-05-06  
**Due:**  

## Overview

A broad feature sprint covering the Dashboard prayer card redesign, a new Quick Alarm page, full-screen alarm support with sound playback, Android notification overhaul, and Quran improvements (full surah playback, notification bar integration, improved bookmarks). Islamic dates section to be extracted into its own page.

## Current State

VERIFY complete. 14/14 AC PASS (static), 0 blockers, 6 warns (none fatal). 10 stale tests flagged (test-maintenance debt). Ticket closed.

## Scope Summary

1. **Dashboard** — Redesign upcoming prayer card: place it top-of-page (after header), remove "next prayer" label, large prayer name + time as focal point, time-remaining text below, tap-to-alarm navigation, prayer-time icons.
2. **Quick Alarm Page** — New page accessible from prayer card tap; shows today's full prayer schedule.
3. **Islamic Dates** — Move upcoming Islamic dates section to its own dedicated page.
4. **Android Alarm** — Fix alarm not triggering reliably on Android.
5. **Full-Screen Alarm** — Add full-screen alarm experience.
6. **Alarm Sound** — Alarm plays the user-selected sound.
7. **Quran — Surah Playback** — Option to play an entire surah (not just ayah by ayah).
8. **Notification Bar** — Show playback status in notification bar while audio is active.
9. **Android Notification Design** — Rich, visually designed notification (not plain default).
10. **Quran Bookmarks** — Improve the bookmark feature UX/functionality.

## Close Note

**Closed:** 2026-05-06  
**Closed by:** verifier (close-work)  
**Result:** 14/14 AC PASS (static). 0 blockers. 6 warnings — none fatal (scope-edge, test debt, device-test gap). All 15/15 plan tasks complete. `dart analyze lib/` clean.  
**Outstanding items for follow-on work:**
- 10 stale unit tests in `athan_preferences_service_test.dart` asserting old `_alarmClockMode` default of `false` — update before next release.
- WARN-AC5: confirm with product whether Sunrise should appear in `_TodayScheduleSection` (currently excluded by data model).
- WARN-DEVICE: physical-device Doze and lock-screen full-screen intent tests not executed — recommended before release.

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
