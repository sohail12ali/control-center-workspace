---
ticket: "T02"
artifact: questions
stage: CLARIFY
---

# Open Questions: T02

| # | Question | Status | Stage | Owner | Decision |
|---|----------|--------|-------|-------|----------|
| Q1 | **Persistence on web v1**: Should prayer tracking and tasbih history persist across browser page refreshes on web? The simplest path is an in-memory stub (data lost on refresh). The durable path requires migrating the DB layer to drift/WASM (adds 2–3 days). | resolved | CLARIFY | anjum | [[T02-decision-log#D1 — Persistence: drift/WASM (durable IndexedDB)\|D1]] |
| Q2 | **Web deployment target**: Where will the web build be hosted? (e.g. Firebase Hosting, GitHub Pages, a dedicated domain, or just a local PWA for testing). This affects CORS config for the Quran audio CDN and PWA manifest domain. | resolved | CLARIFY | anjum | [[T02-decision-log#D2 — Hosting: GitHub Pages primary, keep options open\|D2]] |
| Q3 | **PWA / installability**: Should the web build be a Progressive Web App with an installable manifest and service worker offline caching? Or a plain hosted SPA is fine for v1? | resolved | CLARIFY | anjum | [[T02-decision-log#D3 — Ship as PWA\|D3]] |
| Q4 | **Auth / accounts on web**: The mobile app uses no cloud auth today (everything is local). Should the web version stay fully local (same model), or does going to web motivate adding a cloud sync / sign-in story? | resolved | CLARIFY | anjum | [[T02-decision-log#D4 — Stay fully local on web (no auth, no cloud sync)\|D4]] |
| Q5 | **Athan notifications on web**: Web Push Notifications exist but are not supported by `flutter_local_notifications`. Should v1 simply hide the notification scheduling section on web (show an informational banner), or is browser Web Push a v1 requirement? | resolved | CLARIFY | anjum | [[T02-decision-log#D5 — Hide athan notifications on web (no Web Push in v1)\|D5]] |
| Q6 | **Qibla on web**: The device magnetometer is not accessible from browsers. The proposed fallback is a static Qibla bearing card showing the great-circle direction from the user's saved location with a compass-rose SVG (no live needle). Is that acceptable for web v1, or should the Qibla tab be hidden entirely? | resolved | CLARIFY | anjum | [[T02-decision-log#D6 — Hide compass-dependent UI on web; keep static Qibla bearing\|D6]] |
| Q7 | **Build flavor vs single codebase**: Should web be a separate Flutter flavor/entry-point (e.g. `lib/main_web.dart`) that can have entirely different initialisation, or should the single `lib/main.dart` handle both with `kIsWeb` guards? (Single codebase with guards is simpler and is the recommended approach.) | resolved | CLARIFY | anjum | [[T02-decision-log#D7 — Single `main.dart` with `kIsWeb` guards\|D7]] |
| Q8 | **Onboarding on web**: The current 4-page onboarding covers Location, Notifications, Battery, and Prayer Calculation. Pages 2 (Notifications) and 3 (Battery) are Android-only. On web should onboarding be shortened to Location + Prayer Calculation only, or skipped entirely? | resolved | CLARIFY | anjum | [[T02-decision-log#D8 — Skip onboarding on web; ask permissions on demand\|D8]] |

## Summary

- **Open**: 0
- **Resolved**: 8
- **Deferred**: 0

## Links
- [[T02-summary]] · [[T02-analysis]] · [[T02-requirements]] · [[T02-decision-log]] · [[T02-questions]] · [[T02-plan]] · [[T02-progress]] · [[T02-verification]]
