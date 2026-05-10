---
ticket: "T04"
artifact: analysis
created: 2026-05-10
---

# Analysis: T04 — Add Hadith Find

## Context

Noble Salah is a Flutter app (v1.0.10+12, SDK ^3.11.5) with five nav-bar tabs: Dashboard, Quran, Dua, Tools, and Settings. It targets Android, iOS, web (T02 active), and desktop. All existing Islamic text content — Quran (114 surahs as per-surah JSON bundles), Duas (32 hardcoded Dart objects), Adhkar (JSON bundle), Asma ul-Husna (JSON bundle) — is delivered fully offline with no external API calls. The database layer (`AppDatabase` / Drift) is already web-compatible via WASM SQLite. There is no hadith feature of any kind today.

## Current State

- `lib/navigation/app_shell.dart:69-75` — five screens hardcoded; no hadith screen or hook.
- `lib/features/tools/tools_screen.dart:30-200` — Tools grid has 13 cards; no hadith card.
- `lib/data/database/app_database.dart:9` — Drift DB named `noble_salah`, schema v2; holds only `prayer_tracking`, `tasbih_custom_phrases`, `tasbih_recitation_history`. No hadith table.
- `assets/data/` — contains `adhkar_routine.json`, `asma_ul_husna.json`, `ayah_of_day.json`, `chapters_en.json`, `chapters_ur.json`, `cities.json`. No hadith data.
- `assets/quran/` — 114 per-surah JSON files (~7.3 MB total). Pattern: load-on-demand with a 3-surah LRU cache.
- `lib/domain/services/dua_service.dart:311-320` — Dua search: in-memory list, no text search (category filter only).
- `lib/domain/services/city_search_service.dart:20-32` — City search: case-insensitive substring scan over preloaded JSON array. Pattern reusable for hadith.
- `lib/domain/services/asma_service.dart:25-31` — Asma search: case-insensitive substring on transliteration + meaning. Same reusable pattern.
- `pubspec.yaml:48-49` — Drift (`^2.22.0`) + `drift_flutter` (`^0.2.0`) + `sqlite3_flutter_libs` already in deps; SQLite FTS5 extension is bundled.

## Key Findings

- **No hadith infrastructure exists.** Zero hadith data, services, screens, or navigation hooks. This is a greenfield addition. Significance: full design freedom, but also full build cost.

- **App architecture strongly favors offline-first JSON or SQLite bundles.** Every data source (Quran, Adhkar, Dua, Asma, Cities) is either a bundled JSON or a drift-backed SQLite. No API clients, HTTP packages, or network cache layers exist. Significance: adding a network-dependent hadith API requires introducing a new architectural dependency and error-handling patterns.

- **Drift + SQLite FTS5 is already present.** `sqlite3_flutter_libs` bundles the SQLite3 binary including FTS5 extension on mobile. On web, drift uses WASM SQLite which also supports FTS5. This means full-text search over a local hadith SQLite database is immediately available with zero new dependencies. Significance: high — the hardest part of performant offline search is already solved.

- **T02 web target is active.** Any hadith solution must run on web (Flutter Web + WASM SQLite). Network-only approaches are acceptable for web if offline mobile is also handled, but any bundled asset approach must keep asset size in check for web load times. The existing Quran bundle is 7.3 MB; a comparable hadith bundle is acceptable.

- **Three viable pub.dev packages exist, none is a strong fit:**
  - `hadith` (v1.0.1, MIT, pub score 150): offline, six Kutub as-Sitta collections from sunnah.com. Unknown bundle size. No text search — only hierarchical browse by book/hadith number. Last updated 13 months ago.
  - `hadith_nawawi` (v0.0.4, MIT, pub score 160): 40 Hadith Nawawi only, includes UI widgets and search. Very limited corpus.
  - `dorar_hadith` (v0.4.0, MIT, pub score 140): wraps Dorar.net API (online), full-text search with grade/narrator/book filters, SQLite result caching. Requires network. Arabic-centric.

- **Best free open hadith corpus: fawazahmed0/hadith-api (Unlicense / public domain).** Covers 10 collections (Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasai, Ibn Majah, Muwatta Malik, Nawawi 40, Hadith Qudsi 40, Shah Waliullah 40) in Arabic + English + Urdu + Bengali + French + Indonesian + Russian + Turkish + Tamil. Static JSON files served via jsDelivr CDN. No rate limits. Can be downloaded at build time and bundled as assets — avoiding runtime network dependency. Each collection is separate JSON; selective bundling possible.

- **Sunnah.com API** offers the most complete data (same collections, better metadata including hadith grades and references) but requires API key, is not public for commercial use, and has rate limits. Not suitable without licensing.

- **Search approach options ranked:**
  1. **SQLite FTS5 (local)** — fastest for offline full-text search; requires pre-building a SQLite DB from the corpus at build time and bundling it as an asset (~5-20 MB depending on collections). Consistent with existing Drift layer. Works on mobile and web.
  2. **In-memory Dart substring scan** — works for small corpora (e.g., Nawawi 40 = 42 hadiths, Hadith Qudsi = 40). Fails at scale: Bukhari has 7,563 hadiths, Muslim has 5,362. Memory and scan time become unacceptable.
  3. **Numbered lookup** — browse by collection → book → hadith number. Zero search infrastructure needed; works with any bundled JSON. Good for "I know the reference" UX; poor for "find a hadith about topic X" UX.
  4. **REST API (dorar.net / sunnah.com)** — best search quality (Arabic morphological search at dorar.net), requires network, introduces latency and offline failure mode.
  5. **Semantic/AI search** — highest quality relevance but requires server infrastructure, API costs, and significant build effort. Out of scope for first version.

- **Locale coverage is a key decision variable.** The app already supports en, ar, ur, hi. fawazahmed0 corpus covers en + ur + ar; Hindi (hi) is not available in any free corpus. The existing localization framework (`flutter_gen`, ARB files) and multilingual Quran pattern show the team can handle per-locale data.

- **Corpus size estimation (fawazahmed0, English + Arabic + Urdu):**
  - Bukhari (~7,500 hadiths × 3 locales): ~8-12 MB JSON
  - All 6 Kutub as-Sitta combined: ~40-60 MB raw JSON; ~10-15 MB as compressed SQLite FTS5 DB.
  - Nawawi 40 only: ~200 KB. Hadith Qudsi only: ~100 KB.
  - A curated "essentials" bundle (Nawawi 40 + Hadith Qudsi + Bukhari short hadiths): ~1-3 MB.

## Research

- fawazahmed0/hadith-api: https://github.com/fawazahmed0/hadith-api — Unlicense, 10 collections, 8+ languages, jsDelivr CDN delivery, no rate limits.
- pub.dev `hadith` v1.0.1: https://pub.dev/packages/hadith — offline 6 collections, no text search.
- pub.dev `dorar_hadith` v0.4.0: https://pub.dev/packages/dorar_hadith — Dorar.net API wrapper, online, FTS, Arabic-centric.
- pub.dev `hadith_nawawi` v0.0.4: https://pub.dev/packages/hadith_nawawi — 40 Nawawi only, offline, has search.
- Drift FTS5: https://drift.simonbinder.eu/docs/advanced-features/fts/ — FTS5 virtual tables work in drift on both native and WASM.
- Sunnah.com API: requires API key, not public for production use.
- Dorar.net API: free, Arabic FTS, no auth required, rate limits undocumented.

## Recommended Path

Build an offline-first hadith feature using a **curated bundled SQLite database with FTS5**, sourced from the fawazahmed0/hadith-api corpus (Unlicense). Start with a focused corpus — Nawawi 40, Hadith Qudsi 40, and one or two Kutub as-Sitta (e.g., Bukhari, Muslim) — in English and Arabic, with Urdu as a secondary locale. A Python build script pre-processes the JSON, builds a SQLite DB with an FTS5 virtual table, and the resulting `.db` file is bundled as a Flutter asset (estimated 3-8 MB). At runtime, `AppDatabase` opens the hadith DB via Drift using the existing web/native executor split. A new `HadithService` exposes `search(query, {collection, locale})` and `browse(collection, book)`. A new `HadithScreen` is added to the Tools grid (no new nav-bar tab needed unless scope expands). This approach requires zero new runtime dependencies, leverages all existing patterns (Drift, offline asset loading, AppShell nav), and works on web via WASM SQLite. A fallback browse-by-number view serves users when search returns no results. Hindi locale coverage is deferred until a corpus source is identified.

---

## Analysis Patches (post-clarification 2026-05-10)

The following decisions supersede portions of the analysis above. See [[T04-decision-log]] for full rationale.

### Superseded: corpus scope (Recommended Path paragraph)
The recommended path suggested starting with a "curated" subset (Nawawi 40 + Hadith Qudsi + Bukhari + Muslim, ~3-8 MB). **User decision (D01):** all 10 fawazahmed0 collections are bundled in v1. No size constraint applies. Estimated SQLite asset ~20-30 MB for en + ar + ur.

### Superseded: UI placement (Recommended Path paragraph — "new HadithScreen in Tools grid")
The recommended path suggested placing Hadith as a new card in the Tools grid with no nav-bar change. **User decision (D04):** a new "Books" tab replaces the current Quran tab. Quran, Duas, and Hadith are consolidated as sub-sections of Books. This is a nav-bar refactor; `lib/navigation/app_shell.dart:69-75` and the Tools grid Dua entry both require structural changes.

### Superseded: search modes (Recommended Path paragraph)
The recommended path described FTS5 search plus a browse fallback. **User decision (D02):** all three modes are mandatory in v1: full-text keyword search, hierarchical browse (collection → book → hadith), and numbered reference lookup (e.g. "Bukhari 6224").

### Confirmed: offline-first, fawazahmed0 Unlicense, Hindi deferred, grade display
These align with the original recommended path and are now formally decided (D03, D06, D08, D05).

## Links
- [[T04-summary]] · [[T04-analysis]] · [[T04-requirements]] · [[T04-decision-log]] · [[T04-questions]] · [[T04-plan]] · [[T04-progress]] · [[T04-verification]]
