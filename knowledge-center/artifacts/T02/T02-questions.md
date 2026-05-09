---
ticket: "T02"
artifact: questions
stage: CLARIFY
---

# Open Questions: T02

| # | Question | Status | Stage | Owner | Decision |
|---|----------|--------|-------|-------|----------|
| Q1 | **Persistence on web v1**: Should prayer tracking and tasbih history persist across browser page refreshes on web? The simplest path is an in-memory stub (data lost on refresh). The durable path requires migrating the DB layer to drift/WASM (adds 2–3 days). | open | CLARIFY | anjum | |
| Q2 | **Web deployment target**: Where will the web build be hosted? (e.g. Firebase Hosting, GitHub Pages, a dedicated domain, or just a local PWA for testing). This affects CORS config for the Quran audio CDN and PWA manifest domain. | open | CLARIFY | anjum | |
| Q3 | **PWA / installability**: Should the web build be a Progressive Web App with an installable manifest and service worker offline caching? Or a plain hosted SPA is fine for v1? | open | CLARIFY | anjum | |
| Q4 | **Auth / accounts on web**: The mobile app uses no cloud auth today (everything is local). Should the web version stay fully local (same model), or does going to web motivate adding a cloud sync / sign-in story? | open | CLARIFY | anjum | |
| Q5 | **Athan notifications on web**: Web Push Notifications exist but are not supported by `flutter_local_notifications`. Should v1 simply hide the notification scheduling section on web (show an informational banner), or is browser Web Push a v1 requirement? | open | CLARIFY | anjum | |
| Q6 | **Qibla on web**: The device magnetometer is not accessible from browsers. The proposed fallback is a static Qibla bearing card showing the great-circle direction from the user's saved location with a compass-rose SVG (no live needle). Is that acceptable for web v1, or should the Qibla tab be hidden entirely? | open | CLARIFY | anjum | |
| Q7 | **Build flavor vs single codebase**: Should web be a separate Flutter flavor/entry-point (e.g. `lib/main_web.dart`) that can have entirely different initialisation, or should the single `lib/main.dart` handle both with `kIsWeb` guards? (Single codebase with guards is simpler and is the recommended approach.) | open | CLARIFY | anjum | |
| Q8 | **Onboarding on web**: The current 4-page onboarding covers Location, Notifications, Battery, and Prayer Calculation. Pages 2 (Notifications) and 3 (Battery) are Android-only. On web should onboarding be shortened to Location + Prayer Calculation only, or skipped entirely? | open | CLARIFY | anjum | |

## Summary

- **Open**: 8
- **Resolved**: 0
- **Deferred**: 0

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
