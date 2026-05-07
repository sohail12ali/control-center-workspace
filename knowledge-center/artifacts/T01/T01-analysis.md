---
ticket: "T01"
artifact: analysis
---

# Analysis: T01

## Context

Mobile app (Android-first) with a Dashboard, Quran reader, and prayer-time/alarm features. User has identified 10 improvement areas spanning UI redesign, alarm reliability, audio playback, and notification design.

## Current State

- Dashboard shows an "upcoming prayer" card somewhere below the header with a "next prayer" label.
- Alarm exists but does not trigger reliably on Android.
- No full-screen alarm UI.
- Alarm sound selection exists but sound is not played on trigger.
- Quran reader plays individual ayahs; no full-surah playback.
- Notification bar does not show playback status.
- Android notifications use the default system style.
- Bookmark feature exists but UX needs improvement.
- Upcoming Islamic dates shown inline on Dashboard.

## Key Findings

- Finding: Android alarm unreliability — likely requires `AlarmManager` with `SCHEDULE_EXACT_ALARM` permission + foreground service to survive Doze/battery optimization. Significance: **High** — core user-trust feature.
- Finding: Full-screen alarm — requires `USE_FULL_SCREEN_INTENT` permission + `Notification.fullScreenIntent`. Significance: **High**.
- Finding: Surah playback — needs a sequential ayah playlist or a direct surah audio URL (e.g., everyayah.com / mp3quran.net API). Significance: **Medium**.
- Finding: Notification bar for playback — requires a `MediaStyle` notification backed by a `MediaSession`. Significance: **Medium**.
- Finding: Rich notification design — `NotificationCompat.BigPictureStyle` or a custom `RemoteViews` layout. Significance: **Medium**.
- Finding: Dashboard card redesign — purely UI, low risk. Significance: **Low-Medium**.
- Finding: Islamic dates page extraction — routing + new screen, low risk. Significance: **Low**.

## Research

Pending — technology choices (audio source, alarm strategy, notification style) to be decided in `tech-select` before planning.

## Recommended Path

1. Clarify open questions (audio source, exact bookmark pain points, alarm platform target — Android only or also iOS).
2. Run `tech-select` for alarm backend and audio/notification strategy.
3. Freeze requirements.
4. Plan by slice: UI slice → Alarm slice → Audio/Notification slice → Quran slice.

## Links
- [[T01-summary]] · [[T01-analysis]] · [[T01-requirements]] · [[T01-decision-log]] · [[T01-questions]] · [[T01-plan]] · [[T01-progress]] · [[T01-verification]]
