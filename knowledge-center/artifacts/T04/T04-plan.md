---
ticket: "T04"
artifact: plan
status: frozen
version: v1
created: 2026-05-10
---

# Plan: T04 — Add Hadith Find (Books Tab)

## Approach

T04 is a substantial greenfield feature built on top of a frozen requirements baseline (v4, 41 ACs, decisions D01–D20). The work has three structural concerns:

1. **Data pipeline** — A one-time developer-run Dart CLI script (`tool/build_hadith_db.dart`) fetches all 10 fawazahmed0 collections, builds a SQLite FTS5 database with en/ar/ur columns, and commits the result as a binary asset. This is a prerequisite for every runtime slice.

2. **Navigation refactor** — The current five-tab nav (Dashboard / Quran / Dua / Tools / Settings) is restructured. The Quran tab becomes a Books tab containing Quran, Hadith, and Duas as sub-sections. The Dua card is removed from the Tools grid. This is a structural change with AC coverage across existing screens.

3. **Hadith feature** — A new `HadithDatabase` (separate Drift instance, read-only), `HadithService` (ChangeNotifier, Provider-registered), and three screens (`BooksScreen`, `HadithScreen`, `HadithDetailScreen`) implement the three search modes (FTS, browse, numbered lookup) with full locale support, grade display, copy action, and integrity verification.

**Architectural constraints (from codebase inspection):**
- State management: Provider + ChangeNotifier only (no Riverpod, Bloc). `HadithService extends ChangeNotifier`.
- Drift pattern: raw SQL via `QueryExecutor`, not the typed Drift table API. `HadithDatabase` follows the same singleton + `LazyDatabase` pattern as `AppDatabase`.
- Read-only DB opening: `LazyDatabase(() => NativeDatabase.opened(sqlite3.open(path, mode: OpenMode.readOnly)))` on native; `WasmDatabase.open(...)` on web (D18).
- FTS5 tokenizer: `unicode61` with `remove_diacritics=2` for both en and ar columns (D19).
- `path_provider` must be added to `pubspec.yaml` (not currently present — needed for `getApplicationSupportDirectory()`).
- Build script Dart deps: `package:http` (fetch JSON), `package:sqlite3` (create DB), `package:crypto` (SHA-256). All are available on pub.dev; none require Flutter; all run in `dart run`.

**Sequencing:** Slice A (build pipeline) must complete before Slices C–F can be verified against real data. Slice B (Books tab refactor) is independent and can proceed in parallel. Slices C–F are the feature implementation and depend on Slice A (data) and Slice B (navigation shell). Slice F (NFR scaffolding) runs last as it wraps the complete feature.

---

## Slices

### Slice A — Build Pipeline (`tool/build_hadith_db.dart`)
Dart CLI script that fetches fawazahmed0 JSON at a pinned commit SHA, normalizes all 10 collections into a single SQLite FTS5 database, and emits `hadith.db` + `hadith.db.sha256`. The prebuilt outputs are committed to the repo as binary assets.

**Covers:** FR-03, FR-04, NFR-03 (sidecar SHA), NFR-06 (license comment), NFR-07 (repeatability), AC-07, AC-08, AC-31.

### Slice B — Books Tab Navigation Refactor
Restructure `app_shell.dart`: replace the Quran tab with a Books tab. Create `BooksScreen` with sub-section navigation (Quran, Hadith, Duas). Remove the Dua card from `tools_screen.dart`. Update all internal nav references. Tablet two-pane layout must continue to work.

**Covers:** FR-01, FR-02, FR-14, AC-01–AC-05, AC-26 (Dashboard unchanged), AC-32.

### Slice C — Data Layer (HadithDatabase + HadithService)
`HadithDatabase` singleton using `LazyDatabase` + `NativeDatabase.opened(readOnly)` on native and `WasmDatabase` on web. `HadithService extends ChangeNotifier` exposing: `search(query, locale)`, `browse(collectionKey)`, `browseBooks(collectionKey)`, `browseHadiths(collectionKey, bookKey)`, `lookupByReference(alias, number)`, `getDetail(id)`. `HadithIntegrityService` for SHA-256 verification with SharedPreferences caching. `aliases.json` asset read and parsed. `pubspec.yaml` updated with new assets and `path_provider`.

**Covers:** FR-03, FR-05, FR-06, FR-07, FR-11, FR-15, AC-06, AC-33, AC-38, AC-40, AC-29, AC-36.

### Slice D — Search Modes UI (HadithScreen)
`HadithScreen` with a search bar at the top. Idle state shows browse collection list. Text input activates FTS (en/ar) or browse prompt (ur). Numbered reference regex auto-detects and triggers `lookupByReference`. Results list shows snippet, collection, book, hadith number, grade chip. Empty state message. Urdu informational placeholder for keyword search. Pagination (≤50 per page).

**Covers:** FR-05, FR-06, FR-07, FR-10, AC-09–AC-17, AC-23, AC-34, AC-35.

### Slice E — Detail View + Grade + Copy
`HadithDetailScreen` showing Arabic + locale translation stacked, collection/book/number, grade chip (corpus value or "—" for null), copy-to-clipboard action with snackbar. Grade chip localized for en/ar/ur. Hindi fallback banner on detail screen.

**Covers:** FR-08, FR-09, FR-10, AC-18–AC-22.

### Slice F — NFR Scaffolding (Integrity, Platform, Performance, Accessibility)
Integrity unit test for `HadithIntegrityService`. `HttpOverrides` no-network test. Cold-start measurement baseline note (adb command). Desktop smoke test (Windows or macOS). Accessibility semantic labels + contrast annotation. NOTICES/ATTRIBUTION file. `pubspec.yaml` asset registration for `hadith.db`, `hadith.db.sha256`, `aliases.json`.

**Covers:** NFR-01–NFR-07, AC-24, AC-25, AC-27–AC-31, AC-37, AC-39, AC-40, AC-41.

---

## Tasks

### Slice A — Build Pipeline

#### [x] T04-A1 — Implement `tool/build_hadith_db.dart` (8 h)
- [ ] Add `package:http`, `package:sqlite3`, `package:crypto` to `dev_dependencies` (or as a standalone `tool/pubspec.yaml` if preferred — see Planner Note V3)
- [ ] Fetch all 10 fawazahmed0 collection JSON files from jsDelivr at a pinned commit SHA (define SHA constant at top of script)
- [ ] Normalize JSON into flat row structure: `(id, collection_key, book_key, book_name_en, book_name_ar, book_name_ur, hadith_number, text_en, text_ar, text_ur, grade)` — grade is nullable string
- [ ] Create SQLite DB with: `hadiths` base table + `collections` lookup table + `books` lookup table + `hadith_fts` FTS5 virtual table using `tokenize="unicode61 remove_diacritics 2"` covering `text_en` and `text_ar`
- [ ] Populate all tables; verify row counts against expected per-collection hadith counts
- [ ] Write `assets/data/hadith/hadith.db` and `assets/data/hadith/hadith.db.sha256` (two-line format: `v1\n<hex-sha256>`)
- [ ] Add source-URL comment and manual-rebuild procedure comment at top of script
- [ ] Pin the `sqlite3` library version used (log it to stdout)
- **Done-criteria:** `dart run tool/build_hadith_db.dart` on a machine with network produces `hadith.db` and `hadith.db.sha256` in `assets/data/hadith/`. Running twice on the same machine + SQLite version produces byte-identical `hadith.db`. All 10 collections present; row count plausible (Bukhari ≥ 7000, Muslim ≥ 5000).
- **Basis:** FR-04, NFR-07; script complexity is high (10 JSON sources, FTS DDL, SHA computation) but well-bounded.
- **Depends on:** —

#### [x] T04-A2 — Register assets in pubspec.yaml + commit prebuilt outputs (1 h)
- [ ] Add `assets/data/hadith/` directory entry to `pubspec.yaml` flutter.assets section
- [ ] Add `path_provider: ^2.1.0` to `dependencies` (needed for `getApplicationSupportDirectory()` in D18 pattern)
- [ ] Commit `assets/data/hadith/hadith.db`, `assets/data/hadith/hadith.db.sha256`, `assets/data/hadith/aliases.json` (hand-authored alias map — see FR-07)
- [ ] Verify `flutter pub get` succeeds and `flutter build apk --debug` includes the new assets
- **Done-criteria:** `pubspec.yaml` lists the new assets; `flutter pub get` clean; assets visible in build artifact inspection. `path_provider` resolves.
- **Basis:** FR-04, D14, D11.
- **Depends on:** T04-A1

#### [x] T04-A3 — Author `assets/data/hadith/aliases.json` (1 h)
- [ ] Hand-author the alias JSON mapping English abbreviations (bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah, malik, nawawi40, qudsiyyah40, shah-waliullah40) and Arabic abbreviations (البخاري, مسلم, أبو داود, الترمذي, النسائي, ابن ماجه, مالك) to fawazahmed0 collection keys
- [ ] Include both case variants for English (Bukhari / bukhari)
- [ ] Validate JSON syntax
- **Done-criteria:** `aliases.json` is valid JSON; covers all 10 collections; includes Arabic aliases for at least the six Kutub as-Sitta. AC-35 Arabic-alias test can resolve against it.
- **Basis:** D11, FR-07; small scope but must be done before Slice D testing.
- **Depends on:** —

---

### Slice B — Books Tab Navigation Refactor

#### [x] T04-B1 — Create `BooksScreen` with sub-section navigation (3 h)
- [ ] Create `lib/features/books/books_screen.dart` with three navigable sub-sections: Quran, Hadith, Duas
- [ ] Use `Navigator` push pattern (same as other screens) rather than a nested `TabBar` — Books acts as a landing page with three large tappable cards/tiles matching the app's visual style
- [ ] Tapping Quran → pushes `QuranScreen`; Duas → pushes `DuaScreen`; Hadith → pushes `HadithScreen` (stub for now, filled in Slice D)
- [ ] Localize the screen title and sub-section labels (add ARB keys: `books`, `hadith`, and any missing keys)
- **Done-criteria:** `BooksScreen` renders with three sub-section entries. Navigation to Quran and Duas works. A placeholder `HadithScreen` stub routes correctly.
- **Basis:** FR-01, FR-02, D04.
- **Depends on:** —

#### [x] T04-B2 — Refactor `app_shell.dart`: Quran tab → Books tab (2 h)
- [ ] Replace `QuranScreen()` in `_screens` list with `BooksScreen()`
- [ ] Update the second `destinations` entry: change icon to `Icons.menu_book_outlined` (or similar books icon) and label to `localizations.books`
- [ ] Update tablet two-pane layout: the persistent right-pane QuranScreen companion must remain — when Books is selected and user is in Quran sub-section, the two-pane Quran view should still work. Decision: keep the right pane as `QuranScreen` companion for Books tab as well (the most natural behaviour given D04 intent)
- [ ] Ensure `_selectedIndex == 1` now maps to BooksScreen; adjust the `quranSelected` guard on the tablet layout accordingly (it now means "Books selected" rather than "Quran tab selected")
- [ ] Add `books` localization key to all ARB files (en, ar, ur, hi)
- **Done-criteria:** Five nav items; second item is "Books" with correct icon/label; tapping it shows `BooksScreen`; tablet layout not broken; Dashboard screen diff shows zero changes (AC-26).
- **Basis:** FR-01, D04, AC-01.
- **Depends on:** T04-B1

#### [x] T04-B3 — Remove Dua card from `tools_screen.dart` + fix nav references (1 h)
- [ ] Locate the Dua `_ToolCard` entry in `tools_screen.dart` — **note:** inspection shows the current Tools grid does NOT include a Dua card (the 12 tools listed are: Prayer Calendar, Islamic Calendar, Islamic Dates, Ramadan Calendar, Qibla, Tasbih, Dhikr, Wudu, Salah Guide, Qada Counter, Asma ul-Husna, Adhkar Morning, Adhkar Evening). Verify this at build time. If no Dua card exists, AC-32 requires only confirming no broken reference — record the finding and mark AC-32 green with a note.
- [ ] Audit all files for any `DuaScreen` import or `Navigator.push(... DuaScreen ...)` that is not in `BooksScreen` — fix any dangling references
- [ ] Remove the Dua tab import from `app_shell.dart` (it moves to `books_screen.dart`)
- **Done-criteria:** `tools_screen.dart` has no Dua card and no broken import. `BooksScreen` is the only entry point to `DuaScreen`. `flutter analyze` passes.
- **Basis:** FR-14, D10, AC-32.
- **Depends on:** T04-B1

#### [x] T04-B4 — Verify existing nav AC coverage (1 h)
- [ ] Manually verify AC-02 (Books → Quran works), AC-03 (Books → Duas works), AC-04 (Books → Hadith stub works), AC-05 (no broken deep-links)
- [ ] Run `flutter analyze` — zero errors
- [ ] Run existing widget tests — no regressions from nav refactor
- **Done-criteria:** All Slice B ACs pass manual verification. No analyzer warnings from refactored files.
- **Basis:** AC-01–AC-05, AC-26, AC-32.
- **Depends on:** T04-B2, T04-B3

---

### Slice C — Data Layer

#### [x] T04-C1 — Implement `HadithDatabase` (3 h)
- [ ] Create `lib/data/database/hadith_database.dart` — singleton following the `AppDatabase` pattern
- [ ] On native: copy `hadith.db` from asset bundle to `getApplicationSupportDirectory()` on first use or when SHA differs (compare on-disk file hash against `hadith.db.sha256` sidecar). Open with `NativeDatabase.opened(sqlite3.open(path, mode: OpenMode.readOnly))` wrapped in `LazyDatabase`
- [ ] On web: `WasmDatabase.open(...)` loading asset bytes (mirror existing `AppDatabase` web path using `DriftWebOptions`)
- [ ] Expose raw `runSelect` query surface (same pattern as `AppDatabase`) — no migrations needed (read-only)
- [ ] Add `@visibleForTesting injectExecutor()` seam for unit tests
- **Done-criteria:** `HadithDatabase.instance` opens without error in a debug run on Android. The connection is opened read-only (verified manually by checking that `execute('INSERT INTO...')` throws). Unit test with injected in-memory executor passes.
- **Basis:** FR-15, D18, AC-33, AC-38.
- **Depends on:** T04-A2

#### [x] T04-C2 — Implement `HadithIntegrityService` (2 h)
- [ ] Create `lib/domain/services/hadith_integrity_service.dart`
- [ ] On first Hadith screen visit: read `hadith.db.sha256` sidecar asset → parse version line + hex digest → compute SHA-256 of the on-disk `hadith.db` copy → compare
- [ ] Cache result in SharedPreferences using the combined key `"${version}:${hexDigest}"` — re-verify only when key changes (AC-36)
- [ ] If mismatch: expose an error state that `HadithScreen` can display; do not crash
- [ ] Inject-able asset loader for unit testability (AC-29)
- **Done-criteria:** Unit test passes: `HadithIntegrityService` with mismatched digest triggers error state. Cache key changes when version constant changes (AC-36). No crash on mismatch.
- **Basis:** NFR-03, AC-29, AC-36.
- **Depends on:** T04-A2

#### [x] T04-C3 — Implement `HadithService` (4 h)
- [ ] Create `lib/domain/services/hadith_service.dart` extending `ChangeNotifier`
- [ ] Expose:
  - `Future<List<HadithResult>> search(String query, AppLocale locale)` — FTS5 query on `hadith_fts` for en/ar; returns `HadithResult` list with snippet, collection, book, number, grade
  - `Future<List<CollectionMeta>> getCollections()` — all 10 collections from `collections` table
  - `Future<List<BookMeta>> getBooks(String collectionKey)` — books within a collection
  - `Future<List<HadithSummary>> getHadiths(String collectionKey, String bookKey, {int page, int pageSize = 50})` — paginated
  - `Future<HadithDetail> getDetail(int hadithId)` — full detail including all locale columns
  - `Future<HadithDetail?> lookupByReference(String alias, int number)` — resolve alias via `aliases.json` map, then query by `(collection_key, hadith_number)`
- [ ] Parse `aliases.json` once on first use (cache in memory)
- [ ] Grade field: null DB value → null in model → UI renders "—"; non-null string → rendered as chip
- [ ] Unrecognized alias: return null → caller falls back to FTS search (Planner Note V2)
- [ ] Register `HadithService` in `main.dart` `MultiProvider` alongside existing services
- **Done-criteria:** `HadithService.search('mercy', en)` returns non-empty results against the real `hadith.db`. `lookupByReference('Bukhari', 6224)` returns the correct hadith. `lookupByReference('nonexistent', 1)` returns null. `getHadiths(...)` respects `pageSize=50`.
- **Basis:** FR-05–FR-09, D11, D15, D19, AC-09, AC-10, AC-12, AC-13.
- **Depends on:** T04-C1, T04-A3

---

### Slice D — Search Modes UI

#### [x] T04-D1 — Implement `HadithScreen` (browse + search + numbered lookup) (5 h)
- [ ] Create `lib/features/hadith/hadith_screen.dart`
- [ ] Scaffold: `SliverAppBar` + search bar (same style as `AsmaUlHusnaScreen` search pattern); below: collection list in idle state
- [ ] Idle state: `ListView` of all 10 collections (from `HadithService.getCollections()`) — tapping a collection pushes a `HadithBrowseScreen` (book list)
- [ ] Text input: debounce 300 ms → call `HadithService.search(query, locale)` → show `HadithResultsList` below search bar; show empty-state widget if no results (AC-11)
- [ ] Numbered reference detection: regex `^(\w[\w\s]*?)\s+(\d+)$` (case-insensitive) on each keystroke after debounce → if matched, call `lookupByReference` → if result found, push `HadithDetailScreen` immediately; if not found, fall through to FTS
- [ ] Urdu locale: search bar shows placeholder text from l10n key `hadithSearchUnavailableUrdu`; FTS is skipped; browse list remains functional (AC-34)
- [ ] `HadithIntegrityService` check on screen open: if error state, show an error banner (not a crash)
- [ ] Paginate results: infinite scroll / load-more for browse lists (page size 50, AC-30)
- **Done-criteria:** AC-09 (en FTS returns results from ≥2 collections), AC-11 (empty state), AC-12 (all 10 collections in browse), AC-13 (browse drill-down), AC-14 (back navigation), AC-15 (Bukhari 6224 direct nav), AC-16 (Muslim 1 direct nav), AC-17 (non-existent number falls back to FTS), AC-34 (Urdu placeholder visible), AC-35 (Arabic alias البخاري 1 navigates correctly).
- **Basis:** FR-05–FR-07, FR-10, D13, D16.
- **Depends on:** T04-C3, T04-B1

#### [x] T04-D2 — Implement `HadithBrowseScreen` (book list → hadith list) (2 h)
- [ ] `HadithBrowseScreen(collectionKey)`: shows book list from `HadithService.getBooks(collectionKey)`
- [ ] Tapping a book pushes `HadithListScreen(collectionKey, bookKey)`
- [ ] `HadithListScreen`: paginated list of hadiths (number + snippet + grade chip); tapping pushes `HadithDetailScreen`
- [ ] Back navigation at each level returns to the previous level (AC-14)
- [ ] Localized book names when available (from DB); fall back to English
- **Done-criteria:** AC-13 full browse drill-down works; AC-14 back navigation confirmed; grade chip visible on list items (AC-10 applies here too per FR-09).
- **Basis:** FR-06, FR-09, D02.
- **Depends on:** T04-C3, T04-B1

---

### Slice E — Detail View + Grade + Copy

#### [x] T04-E1 — Implement `HadithDetailScreen` (3 h)
- [ ] Create `lib/features/hadith/hadith_detail_screen.dart`
- [ ] Display: Arabic text (always shown, Amiri font, RTL), locale translation below (or side-by-side on wide screen), collection name + book name + hadith number header, grade chip
- [ ] Grade chip rendering: non-null grade string → colored chip with localized label (Sahih=green, Hasan=teal, Daif=orange, unknown=grey); null grade → "—" text, no chip background (AC-19)
- [ ] Grade chip labels: add ARB keys `gradeSahih`, `gradeHasan`, `gradeDaif`, `gradeUnknown` for en/ar/ur
- [ ] Copy-to-clipboard action: `IconButton` in AppBar or FAB → `Clipboard.setData(...)` → `ScaffoldMessenger.showSnackBar(...)` with confirmation (AC-21)
- [ ] Hindi fallback: if `AppLocale.hi`, display English text + non-blocking `MaterialBanner` with l10n key `hadithHindiFallback` (AC-22)
- [ ] Semantic labels on all interactive elements (copy button, grade chip) for AC-41 compliance
- **Done-criteria:** AC-18 (Arabic + translation shown), AC-19 (grade chip / dash logic), AC-20 (grade localized), AC-21 (copy + snackbar), AC-22 (Hindi banner).
- **Basis:** FR-08, FR-09, FR-10, D05, D15.
- **Depends on:** T04-C3

---

### Slice F — NFR Scaffolding

#### [x] T04-F1 — Unit tests: HadithIntegrityService + HadithService + read-only enforcement (3 h)
- [ ] Unit test `HadithIntegrityService` with mock asset loader: mismatched digest → error state (AC-29); cache key invalidation on version change (AC-36)
- [ ] Unit test `HadithService.lookupByReference` with injected in-memory DB: known alias resolves, unknown alias returns null (Planner Note V2)
- [ ] Unit test read-only enforcement: inject executor backed by NativeDatabase with read-only flag; attempt INSERT; expect `SqliteException` (AC-38)
- [ ] `HttpOverrides` test: run hadith search + browse + detail fetch through `HadithService` with `HttpOverrides` that throws on any HTTP call; expect zero throws (AC-40)
- **Done-criteria:** All four test categories pass (`flutter test`). AC-29, AC-36, AC-38, AC-40 covered.
- **Basis:** NFR-03, FR-11, FR-15.
- **Depends on:** T04-C1, T04-C2, T04-C3

#### [x] T04-F2 — NOTICES/ATTRIBUTION entry + license comment in build script (0.5 h)
- [ ] Add fawazahmed0 attribution entry to `NOTICES` or `ATTRIBUTION` file at repo root (create if absent)
- [ ] Confirm `tool/build_hadith_db.dart` has source-URL comment and manual-rebuild comment (part of T04-A1, verify here)
- **Done-criteria:** AC-31 satisfied — NOTICES file exists with fawazahmed0 entry. `flutter build apk --release` packages it.
- **Basis:** NFR-06, D08.
- **Depends on:** T04-A1

#### [x] T04-F3 — Accessibility semantic labels + contrast annotation (1 h)
- [ ] Wrap grade chip in `Semantics(label: 'Grade: ${chip.value}', child: ...)` 
- [ ] Wrap copy button in `Semantics(label: l10n.copyHadith, ...)`
- [ ] Wrap collection list tiles with `Semantics` labels
- [ ] Verify theme color tokens: grade chip colors (Sahih green, Hasan teal, Daif orange) must meet WCAG 2.1 AA contrast ratio ≥ 4.5:1 against chip background — use `AppTokens` color definitions and record computed ratios in a code comment (see Planner Note V4 on contrast tooling)
- [ ] Write `flutter_test` semantics assertion smoke test: render `HadithDetailScreen` with a mock service; assert `find.bySemanticsLabel` finds the copy button and grade chip labels (AC-41)
- **Done-criteria:** AC-41 automated semantics test passes. Grade chip colors have contrast-ratio comments. TalkBack/VoiceOver labels confirmed present.
- **Basis:** NFR-05, AC-41.
- **Depends on:** T04-E1

#### [x] T04-F4 — Platform smoke test documentation + cold-start baseline note (1 h)
- [ ] Record manual smoke-test checklist in `T04-verification.md`: Android (en FTS, ar FTS, browse, numbered lookup, detail, copy), iOS (same), Web WASM (AC-24, AC-25), Desktop Windows or macOS (AC-39)
- [ ] Record adb cold-start measurement command and pre-T04 baseline (measure before merging; builder runs `adb shell am start -W com.noblewave.noble_salah/.MainActivity` twice and records average; the post-T04 delta must be ≤ 300 ms, AC-28)
- [ ] Note: p95 search latency measurement via Flutter DevTools timeline for AC-27 and AC-37; builder records device model and latency in verification artifact
- **Done-criteria:** `T04-verification.md` has a smoke-test checklist covering AC-24, AC-25, AC-27, AC-28, AC-37, AC-39. Builder has a repeatable measurement procedure.
- **Basis:** NFR-01, NFR-02, FR-12, AC-24, AC-25, AC-27, AC-28, AC-37, AC-39.
- **Depends on:** T04-D1, T04-D2, T04-E1

---

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T04-A1 — Build script `tool/build_hadith_db.dart` | 8 h | 10 JSON sources, FTS DDL, SHA, pinned deps, cross-platform Dart CLI |
| T04-A2 — pubspec.yaml asset registration + path_provider | 1 h | Mechanical; one dep + one assets line |
| T04-A3 — Author `aliases.json` | 1 h | 10 collections × 2 locales; hand-authored + validation |
| T04-B1 — `BooksScreen` creation | 3 h | New screen; l10n keys; sub-section nav |
| T04-B2 — `app_shell.dart` refactor | 2 h | Nav restructure; tablet two-pane adjustment |
| T04-B3 — Remove Dua card + nav audit | 1 h | May be a no-op if Dua card absent (verify first) |
| T04-B4 — Slice B verification pass | 1 h | Manual + `flutter analyze` + existing tests |
| T04-C1 — `HadithDatabase` | 3 h | LazyDatabase + read-only native/web split; test seam |
| T04-C2 — `HadithIntegrityService` | 2 h | SHA logic + SharedPreferences cache + injectable loader |
| T04-C3 — `HadithService` | 4 h | 6 query methods + alias parsing + ChangeNotifier + Provider registration |
| T04-D1 — `HadithScreen` (browse + search + lookup) | 5 h | Most complex UI; three modes; debounce; regex; locale branching |
| T04-D2 — `HadithBrowseScreen` + `HadithListScreen` | 2 h | Two screens; pagination; back nav |
| T04-E1 — `HadithDetailScreen` | 3 h | Arabic layout; grade chip; copy action; Hindi fallback; semantics |
| T04-F1 — Unit tests (integrity + service + read-only + no-network) | 3 h | Four test areas; mock loaders; HttpOverrides |
| T04-F2 — NOTICES + license comment | 0.5 h | File creation + content |
| T04-F3 — Accessibility semantics + contrast | 1 h | Semantics wrapping; contrast check; one automated test |
| T04-F4 — Platform smoke-test docs + cold-start baseline | 1 h | Documentation task; measurement commands |
| **Total** | **41.5 h** | |

---

### Acceptance Criterion Coverage

| AC | Requirement | Covered by |
|----|-------------|-----------|
| AC-01 | Four nav items; Books tab present (amended v5 per D22) | T04-B2 |
| AC-02 | Books → Quran works | T04-B1, T04-B4 |
| AC-03 | Books → Duas works | T04-B1, T04-B4 |
| AC-04 | Books → Hadith works | T04-B1, T04-D1 |
| AC-05 | No broken deep-links | T04-B3, T04-B4 |
| AC-06 | Offline: all 10 collections in browse | T04-C3, T04-D1 |
| AC-07 | Build script runs, produces both outputs | T04-A1, T04-A2 |
| AC-08 | Byte-identical output on same machine | T04-A1 (pinned SHA + sqlite3 version) |
| AC-09 | en FTS: "mercy" → ≥2 collections in <500 ms | T04-D1, T04-C3, T04-F4 |
| AC-10 | Results show snippet/collection/book/number/grade | T04-D1, T04-D2 |
| AC-11 | No-results → empty-state, not error | T04-D1 |
| AC-12 | Browse idle: all 10 collections listed | T04-D1, T04-C3 |
| AC-13 | Browse: collection → book → hadith → detail | T04-D1, T04-D2 |
| AC-14 | Back navigation at each browse level | T04-D2 |
| AC-15 | "Bukhari 6224" → direct to detail | T04-D1, T04-C3 |
| AC-16 | "Muslim 1" → direct to detail | T04-D1, T04-C3 |
| AC-17 | Non-existent reference → FTS fallback | T04-D1, T04-C3 |
| AC-18 | Detail: Arabic + locale translation shown | T04-E1 |
| AC-19 | Grade chip vs "—" logic | T04-E1, T04-C3 |
| AC-20 | Grade chip label localized (en/ar/ur) | T04-E1 |
| AC-21 | Copy action + snackbar | T04-E1 |
| AC-22 | Hindi locale → English text + banner | T04-E1 |
| AC-23 | Urdu locale: corpus Urdu text where available; FTS placeholder | T04-D1, T04-C3 |
| AC-24 | Smoke test: Android, iOS, Web WASM | T04-F4 |
| AC-25 | No crash on web WASM open | T04-C1, T04-F4 |
| AC-26 | Dashboard diff: zero changes | T04-B2 (Dashboard not touched) |
| AC-27 | NFR-01 en p95 <500 ms | T04-A1 (FTS index), T04-F4 (measurement) |
| AC-28 | NFR-02 cold-start ≤300 ms delta | T04-C1 (lazy open), T04-F4 (baseline) |
| AC-29 | Unit test: SHA mismatch → error state | T04-C2, T04-F1 |
| AC-30 | Heap ≤50 MB; page size ≤50 | T04-D1, T04-D2 (pagination) |
| AC-31 | NOTICES/ATTRIBUTION entry for fawazahmed0 | T04-F2 |
| AC-32 | Tools grid: no Dua card; no broken ref | T04-B3 |
| AC-33 | Separate Drift instance; AppDatabase schema unchanged | T04-C1 |
| AC-34 | Urdu: search placeholder; browse functional | T04-D1 |
| AC-35 | Arabic alias "البخاري 1" → Bukhari 1 | T04-D1, T04-A3 |
| AC-36 | Cache key invalidation on version constant change | T04-C2, T04-F1 |
| AC-37 | NFR-01 Arabic p95 <500 ms (رحمة, ≥2 collections) | T04-A1 (FTS tokenizer), T04-F4 |
| AC-38 | Read-only enforcement: INSERT throws | T04-C1, T04-F1 |
| AC-39 | Desktop smoke test (Windows or macOS) | T04-F4 |
| AC-40 | Zero outbound HTTP during hadith ops | T04-C1, T04-F1 |
| AC-41 | Semantic labels + WCAG 2.1 AA contrast automated test | T04-F3 |

**AC coverage: 41/41**

---

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| R01 — fawazahmed0 JSON schema changes between pinning and first build (field renames, missing locales) | Low | High | Pin an explicit commit SHA in the script; inspect schema before writing normalizer; add schema-version assertion in script | Builder (T04-A1) |
| R02 — `hadith.db` asset size exceeds acceptable threshold on web (>30 MB compressed causes slow first load) | Med | Med | Run script and measure actual compressed size before committing; if >30 MB, report to planner for scope discussion | Builder (T04-A1) |
| R03 — SQLite FTS5 Arabic search quality: unicode61 remove_diacritics=2 insufficient for root-variant matching (e.g. كتب / كتاب not matched) | Med | Med | AC-37 only requires matching a single Arabic keyword across ≥2 collections — root stemming is NOT required in v1; builder verifies AC-37 with `رحمة` specifically | Builder (T04-F4) |
| R04 — `NativeDatabase.opened(sqlite3.open(path, mode: OpenMode.readOnly))` API mismatch with current `sqlite3_flutter_libs` / `drift` version | Low | High | Verify API availability with installed drift ^2.22.0 + sqlite3_flutter_libs ^0.5.0 before implementing T04-C1; fallback: use `NativeDatabase` with a custom `QueryExecutor` that blocks writes | Builder (T04-C1) |
| R05 — Books tab tablet two-pane layout broken by nav refactor | Med | Med | Existing tablet logic references `_selectedIndex == 1` as "Quran selected"; after refactor this means "Books selected" — builder must test tablet layout explicitly | Builder (T04-B2) |
| R06 — `WasmDatabase.open()` API for read-only asset loading not supported by `drift_flutter ^0.2.0` | Med | High | Investigate drift_flutter web API for read-only asset DB before T04-C1; may need to load asset bytes and initialize WasmDatabase differently; fallback: copy asset bytes into IndexedDB (write) then open read-only — if not feasible, web opens in read-write mode with Drift-level write guard and AC-38 is web-excluded | Builder (T04-C1) |
| R07 — Cold-start budget exceeded (>300 ms) even with lazy open | Low | Med | `LazyDatabase` defers open to first query on Hadith screen; first Hadith screen visit may be slow but does not count as "cold start" per NFR-02 definition | Builder (T04-F4) |
| R08 — Byte-identical build output (AC-08) not achievable due to SQLite page-layout variance | Low | Med | NFR-07 note explicitly scopes "byte-identical" to same machine + same SQLite version; builder documents the pinned sqlite3 version; CI does not re-run the script (D14) | Builder (T04-A1) |

**High×High risks: 0** (R01 and R04 are Low×High — both have concrete mitigations.)

---

## Planner Notes for Builder

### V1 — p95 Sample Size for NFR-01 / AC-27 / AC-37
The acceptance criteria for search latency (AC-27: en FTS <500 ms, AC-37: ar FTS <500 ms) use "p95" as the threshold. For verification purposes, the builder should run 20 search queries of the same term on a Snapdragon 665-class device and take the 95th-percentile reading from Flutter DevTools Timeline (Dart frame raster time). 20 samples is the minimum viable sample for a p95 estimate in a manual test scenario. Record the device model, OS version, and all 20 timings in `T04-verification.md`. If no physical Snapdragon 665 device is available, use an Android emulator and note the deviation — verifier will flag if the emulator result is not representative.

### V2 — Unrecognized-Alias Fallback Behaviour
FR-07 specifies that an unrecognized alias falls back to full-text search. The builder must implement this path explicitly in `HadithService.lookupByReference`: if the alias JSON map has no entry for the parsed alias string (case-insensitive), return `null`. The caller (`HadithScreen`) must handle null by falling through to `search(originalQuery)`. This prevents a silent no-op when a user types e.g. "Darimi 1" (not in the alias map). The fallback-to-FTS path should be covered by a unit test in T04-F1.

### V3 — Build Script Dart Dependencies
`tool/build_hadith_db.dart` needs `package:http` (HTTP GET for JSON files), `package:sqlite3` (create/write SQLite — NOT `sqlite3_flutter_libs` which is Flutter-only), and `package:crypto` (SHA-256 via `sha256.convert()`). The cleanest approach is to add these to the root `pubspec.yaml` under `dev_dependencies` (they are already available in the Dart ecosystem and do not affect the Flutter app bundle). Do NOT add `package:sqlite3` to `dependencies` — it must stay `dev_dependencies` or `dependency_overrides`; the Flutter app uses `sqlite3_flutter_libs` at runtime which bundles its own SQLite binary. Alternatively, create a standalone `tool/pubspec.yaml` — but this adds `dart pub get` friction; the `dev_dependencies` approach is simpler.

### V4 — AC-41 Contrast Tooling
AC-41 requires WCAG 2.1 AA contrast verification for grade chip colors and hadith body text. Flutter's `flutter_test` does not have a built-in contrast checker. The builder should: (a) compute the luminance contrast ratio manually using `Color.computeLuminance()` in a unit test asserting `ratio >= 4.5`, OR (b) use the `accessibility_tools` package (pub.dev) in test mode, OR (c) embed computed contrast-ratio values as code comments next to color definitions in `AppTokens` or the grade chip widget, plus write a unit test that asserts the ratio against the hardcoded values. Option (c) is the most pragmatic — it avoids a new dev dependency and makes the contract explicit in code. The `flutter_test` semantics assertion part (interactive element labels) is standard and does not need additional tooling.

### V5 — Malformed `aliases.json` Handling
`HadithService` parses `aliases.json` from the asset bundle once on first use. If the JSON is malformed (unlikely for a committed asset, but worth handling for robustness), the parse should catch `FormatException` and log an error, then treat the alias map as empty (all references fall back to FTS). Do not crash. This is a defensive coding note — no separate AC, but it contributes to the overall stability of AC-17 (non-existent reference fallback).

---

## Dependencies
- **Blocks:** T05 (Hadith of the Day card, if ticketed) — depends on `HadithService` and `HadithDatabase` existing
- **Blocked by:** None — requirements frozen, all tech decisions resolved

## Links
- [[T04-summary]] · [[T04-analysis]] · [[T04-requirements]] · [[T04-decision-log]] · [[T04-questions]] · [[T04-plan]] · [[T04-progress]] · [[T04-verification]]
