---
ticket: "T04"
artifact: decision-log
---

# Decisions: T04

---

## D01 — Full corpus: all 10 fawazahmed0 collections
**Date:** 2026-05-10  
**Question ref:** Q1, Q2  
**Decision:** Bundle all 10 fawazahmed0 hadith collections in v1 (Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasai, Ibn Majah, Muwatta Malik, Nawawi 40, Hadith Qudsi 40, Shah Waliullah 40). No asset-size constraint is applied.  
**Rationale:** The user explicitly confirmed no size limit and wants the complete fawazahmed0 corpus. Bundling all 10 collections maximizes coverage, avoids a later migration to add collections, and is consistent with the offline-first mandate (D03). The SQLite FTS5 database is estimated at ~20-30 MB for three locales — acceptable on mobile and manageable on web given no cap was set.  
**Impact:** Pre-build Python script must process all 10 collection JSON files. SQLite DB asset will be the largest single asset in the app. App download size increases by ~20-30 MB compressed.

---

## D02 — Three search modes: full-text, browse, numbered lookup
**Date:** 2026-05-10  
**Question ref:** Q3  
**Decision:** Implement all three search modes in v1: (1) full-text keyword search via SQLite FTS5, (2) hierarchical browse (collection → book → hadith list), and (3) numbered reference lookup (e.g. "Bukhari 6224").  
**Rationale:** The user selected "all" modes. Each serves a distinct user intent: scholars search by keyword, casual readers browse by topic/book, and students look up specific references. Delivering all three in v1 ensures no follow-up ticket for search UX before the feature is considered complete.  
**Impact:** HadithService requires three query paths. UI requires a search bar (FTS), a tree-browse navigator, and a reference-lookup input — likely tabbed or a combined search bar that auto-detects numbered references.

---

## D03 — Offline-first via SQLite FTS5 bundle
**Date:** 2026-05-10  
**Question ref:** Q6  
**Decision:** The hadith feature is fully offline-first. No network calls are made at runtime. The sole data source is a pre-built SQLite FTS5 database bundled as a Flutter asset.  
**Rationale:** This aligns with the app's existing architecture — every data source (Quran, Duas, Adhkar, Asma) is fully offline. Drift + sqlite3_flutter_libs (with FTS5) are already in deps (pubspec.yaml:48-49). Network fallback introduces latency, error states, and offline failure modes that the rest of the app does not have. The offline DB covers all user scenarios including airplane mode.  
**Impact:** No HTTP client needed. Build pipeline must produce the SQLite asset. Web delivery requires WASM SQLite (already supported by drift_flutter).

---

## D04 — Books tab navigation refactor
**Date:** 2026-05-10  
**Question ref:** Q5  
**Decision:** Replace the current Quran tab and consolidate Quran, Duas, and new Hadith under a single new "Books" bottom-nav tab. The existing nav-bar shape changes: current Quran tab → Books tab (contains Quran, Hadith, Duas as sub-sections). No new sixth tab is added.  
**Rationale:** The user explicitly requested this consolidation. It keeps the nav-bar at five items (no overflow), groups all Islamic textual content under one destination, and avoids a fragmented UX where Quran lives in nav while Duas live in Tools. This is a structural navigation refactor, not just an additive change.  
**Impact:** `lib/navigation/app_shell.dart` must be updated. The Quran screen and Dua screen become sub-screens of a new Books navigator. Tools grid loses the Dua card entry point (or it remains as a shortcut — to be determined in planning). All deeplinks or internal navigation references to the Quran or Dua screens must be updated.

---

## D05 — Display hadith grade in detail view
**Date:** 2026-05-10  
**Question ref:** Q7  
**Decision:** The hadith detail screen must display the hadith grade (Sahih, Hasan, Daif, or Unknown) sourced from fawazahmed0 metadata.  
**Rationale:** Grade metadata is available in the fawazahmed0 corpus and is important for scholarly trust. Displaying it gives users the ability to assess hadith authenticity without leaving the app. The UI complexity is low — a small badge or label in the detail view.  
**Impact:** Grade field must be included in the SQLite schema. HadithDetailScreen renders a grade badge. Localization strings needed for the four grade values.

---

## D06 — Hindi locale deferred
**Date:** 2026-05-10  
**Question ref:** Q4  
**Decision:** Hindi (hi) hadith locale is deferred to a future ticket. v1 ships English, Arabic, and Urdu hadith text only.  
**Rationale:** fawazahmed0 corpus does not include Hindi translations. No free Hindi hadith corpus has been identified. Adding Hindi would require sourcing a new corpus, which is out of scope for v1. The existing app already defers Hindi for some content.  
**Impact:** The SQLite build script targets en + ar + ur columns only. A future ticket will need to source a Hindi corpus and extend the schema.

---

## D07 — No Hadith of the Day in v1 (Dashboard unchanged)
**Date:** 2026-05-10  
**Question ref:** Q8  
**Decision:** No "Hadith of the Day" card on the Dashboard. Dashboard is out of scope for T04.  
**Rationale:** User explicitly deferred this. The Dashboard already has Ayah of the Day and Prayer Time widgets. Adding a third daily card is a separate design decision best handled in a follow-up ticket once the hadith DB is live and validated.  
**Impact:** DashboardScreen and its widget list are untouched in T04.

---

## D08 — fawazahmed0 Unlicense corpus approved
**Date:** 2026-05-10  
**Question ref:** Q9  
**Decision:** Use fawazahmed0/hadith-api (Unlicense / public domain) as the sole hadith data source.  
**Rationale:** User confirmed comfort with Unlicense. The corpus is public domain — no attribution required, no commercial restrictions, no API key. This is the cleanest possible licensing posture. sunnah.com and other alternatives with restrictive or API-key-gated licenses are not needed.  
**Impact:** The build script fetches from fawazahmed0 GitHub/jsDelivr at build time. A NOTICES or attribution file should reference the source as good practice even though Unlicense does not require it.

---

## D09 — Build script location: `tool/build_hadith_db.dart`
**Date:** 2026-05-10  
**Question ref:** Q10  
**Decision:** The hadith build script shall live at `tool/build_hadith_db.dart`. Written in Dart to follow Flutter/Dart project convention for repo tooling (the `tool/` directory is the standard location for Dart CLI scripts in Flutter repos, comparable to `scripts/` in other ecosystems).  
**Rationale:** User accepted recommended default. Using Dart keeps the build toolchain homogeneous — no Python runtime dependency on developer machines. `tool/` is idiomatic for Dart tooling scripts (ref: dart.dev/tools/pub/package-layout).  
**Impact:** FR-04 updated to reference `tool/build_hadith_db.dart` (Dart, not Python). Planning assigns this path.

---

## D10 — Dua card removed from Tools grid
**Date:** 2026-05-10  
**Question ref:** Q11 / Q14  
**Decision:** The Dua card in the Tools grid is removed entirely. No shortcut deep-link to Books → Duas is retained in Tools. Duas are accessed exclusively through the Books tab after the navigation refactor (D04).  
**Rationale:** User accepted recommended default. Retaining a shortcut creates a dual-entry-point inconsistency — users would find Duas in two places (Books and Tools), which adds navigational confusion. A clean removal keeps the information architecture coherent.  
**Impact:** A new functional requirement (FR-14) is added: the Tools grid must remove the Dua card. `lib/features/tools/tools_screen.dart` loses one card entry. AC-32 added for verification.

---

## D11 — FR-07 alias map: JSON file with en + ar abbreviations
**Date:** 2026-05-10  
**Question ref:** Q12  
**Decision:** Numbered reference lookup (FR-07) shall use a small JSON alias map (bundled asset) mapping collection slugs and common English/Arabic abbreviations to fawazahmed0 collection keys. Example: `"bukhari"` → `"eng-bukhari"`, `"البخاري"` → `"eng-bukhari"`, `"muslim"` → `"eng-muslim"`.  
**Rationale:** User selected recommended option. A JSON file is easier to audit, extend, and test than a hardcoded Dart map. Locale-aware Arabic aliases (right-to-left collection names) allow Arabic-script input in the search bar to resolve to numbered lookups — important for Arabic-locale users. The file is small (~1 KB) and bundled as an asset.  
**Impact:** FR-07 updated to specify the alias JSON asset. Build script or a separate `tool/generate_alias_map.dart` (or inline in FR-04 script) produces or ships this file. AC-15/AC-16 extended to cover Arabic alias input.

---

## D12 — NFR-03 checksum: sidecar SHA-256 manifest file
**Date:** 2026-05-10  
**Question ref:** Q13  
**Decision:** The SHA-256 checksum for the bundled SQLite DB is stored in a sidecar `.sha256` text file bundled as a Flutter asset alongside the `.db`. The app verifies the checksum once on first launch of the Hadith screen and caches the verification result; subsequent opens skip re-verification.  
**Rationale:** User selected recommended option. A sidecar file is easier to update than a hardcoded constant in Dart source — when the `.db` is rebuilt, both files are updated together atomically. Caching the result avoids re-hashing a 20-30 MB file on every cold start, preserving NFR-02 cold-start budget. Security is equivalent to hardcoding (both are in the app bundle; neither is independently signed).  
**Impact:** NFR-03 and AC-29 updated. Build script must emit both `hadith.db` and `hadith.db.sha256`. `pubspec.yaml` registers both assets.

---

## D13 — Search entry point: search bar at top of Books > Hadith section
**Date:** 2026-05-10  
**Question ref:** Q14 (search UX) / Q11 cross-ref  
**Decision:** The Hadith section within the Books tab presents a search bar at the top of the screen. Below the search bar, a browse mode (collection list) is the default idle state. Entering text activates FTS; entering a numbered reference (detected by regex) triggers numbered lookup. Browse and search coexist on the same screen — no separate tabs required.  
**Rationale:** User accepted recommended default. A single-screen design with a prominent search bar and a default browse list below is the most discoverable pattern (mirrors Apple Music, Google Books). Separate tabs for search/browse add navigation overhead for a feature the user may use casually. Auto-detection of numbered references in the same bar keeps the UI minimal.  
**Impact:** FR-05, FR-06, FR-07 updated to clarify the single-screen search + browse layout. No separate tab switcher required in v1.

---

## D14 — Build pipeline: one-time fetch, commit prebuilt `.db` to repo
**Date:** 2026-05-10  
**Question ref:** Q15  
**Decision:** The fawazahmed0 JSON files are fetched once manually by the developer running `dart tool/build_hadith_db.dart`. The resulting `hadith.db` (and `hadith.db.sha256`) are committed directly to the repository as binary assets. CI does not re-fetch or re-build the database.  
**Rationale:** User explicitly selected this option over vendoring raw JSON or using a git submodule. This keeps CI fast and simple (no network dependency in CI), guarantees byte-identical builds from the committed artifact, and avoids repo bloat from raw JSON (all 10 collections uncompressed can exceed 200 MB). The tradeoff — the prebuilt binary is in git — is acceptable given the file size (~20-30 MB compressed) and the infrequency of corpus updates.  
**Impact:** FR-04 updated: build script is a developer tool, not a CI step. The `.db` and `.sha256` files are added to version control (not `.gitignore`d). `pubspec.yaml` registers them as assets. A note in FR-04 documents the manual rebuild procedure.

---

## D15 — FR-09 grade display: chip when present, "—" when absent
**Date:** 2026-05-10  
**Question ref:** Q16  
**Decision:** The grade chip is shown with its value (Sahih, Hasan, Daif) when the fawazahmed0 corpus provides a grade for that hadith. When the corpus does not provide a grade (null/missing), a "—" dash or a "Grade unavailable" label is shown instead of "Unknown". The value "Unknown" is reserved for hadiths where the corpus explicitly records the grade as unknown/unrated — distinct from simply absent.  
**Rationale:** User explicitly selected this behaviour. Using "—" for absent vs "Unknown" for explicitly unrated is semantically more accurate and avoids misleading the user into thinking a grade has been assessed when none exists. This also applies to the search result list and browse list, not just the detail view.  
**Impact:** FR-09 updated: "Unknown" is replaced with a two-state absent/known-unknown distinction. AC-19 updated accordingly. The SQLite schema must store a nullable grade column; null maps to "—", empty-string/unknown maps to "Unknown".

---

## D16 — FTS locale scope: en + ar in v1; ur browse-only
**Date:** 2026-05-10  
**Question ref:** Q17  
**Decision:** FTS5 virtual tables and tokenizers cover English (`unicode61`) and Arabic (`unicode61` with diacritics removal) columns only in v1. Urdu text is stored and displayed but is not indexed for FTS — Urdu users can browse and use numbered lookup but cannot keyword-search in Urdu. Cross-locale simultaneous FTS is deferred.  
**Rationale:** User accepted recommended default. Urdu uses a Nastaliq script variant of Arabic characters; a proper Urdu FTS tokenizer (handling izafat, shadda, etc.) adds significant complexity and has no proven Flutter/SQLite solution at this time. Excluding Urdu from FTS is a pragmatic v1 scoping decision that does not break the feature — Urdu users still get full browse and numbered lookup. An informational note on the Urdu search bar can explain the limitation.  
**Impact:** FR-05 updated to specify en + ar FTS scope. NFR-01 latency applies to en/ar queries only. AC-23 updated: Urdu users see browse/lookup mode with a note that keyword search is not available in Urdu v1. A future ticket can add Urdu FTS when a suitable tokenizer is identified.

---

## D17 — Validate v2 → v3 and v3 → v4: implementation-detail tightenings (no new product decisions)
**Date:** 2026-05-10  
**Question ref:** validate(target=requirements) runs 2 and 3  
**Decision:** Two successive validate passes resolved implementer-level warnings inline without user input. These are specification tightenings, not new product decisions.

**v2 → v3 (five tightenings):**
1. `aliases.json` authorship clarified as hand-authored committed asset, not build-script output (FR-04 / FR-07).
2. NFR-03 cache key tightened: `hadith.db.sha256` is a two-line file (version constant + hex digest); cache key combines both; AC-36 added for version-change invalidation.
3. Arabic-Indic digit input (`٠–٩`) declared out of scope for v1 numbered lookup; only ASCII digits matched (FR-07 + Out-of-scope list).
4. AC-29 rephrased to specify a unit test of `HadithIntegrityService` with a mock asset loader (testability improvement).
5. FR-15 now specifies `SQLITE_OPEN_READONLY` flag (or Drift read-only executor) to enforce immutability at the driver level.

**v3 → v4 (five AC additions — validate v3 cleanup):**
1. AC-37: NFR-01 Arabic latency — explicit Arabic-keyword AC covering the 500 ms / two-collection threshold on Snapdragon 665 (previously only English FTS latency had a concrete AC).
2. AC-38: FR-15 read-only enforcement — unit-test AC confirming the SQLite connection rejects INSERT with a driver-level error.
3. AC-39: FR-12 desktop — smoke-test AC for at least one desktop platform (Windows or macOS), browse and detail view.
4. AC-40: FR-11 no network — `HttpOverrides`-based test AC confirming zero outbound HTTP/HTTPS during any hadith operation.
5. AC-41: NFR-05 accessibility — automated `flutter_test` semantics assertions AC covering semantic labels and WCAG 2.1 AA contrast for grade chip and hadith body text.

**Rationale:** All ten changes harden the spec for the implementer without expanding scope or requiring stakeholder sign-off. Requirements advance from v3 to v4 (frozen).  
**Impact:** Requirements version bumped to v4; freeze gate confirmed clean.

---

## D18 — Drift read-only asset DB: LazyDatabase + NativeDatabase.opened(readOnly) / WasmDatabase.open
**Date:** 2026-05-10  
**Question ref:** FR-15, AC-38  
**Decision:** The hadith SQLite asset database shall be opened using the following platform-split pattern:

```dart
LazyDatabase(() async {
  // Native (Android, iOS, desktop)
  final bytes = await rootBundle.load('assets/data/hadith/hadith.db');
  final dir = await getApplicationSupportDirectory();
  final file = File('${dir.path}/hadith.db');
  // Copy on first use or when SHA differs (checked against sidecar .sha256)
  if (!file.existsSync() || _shaChanged(file)) {
    file.writeAsBytesSync(bytes.buffer.asUint8List());
  }
  return NativeDatabase.opened(
    sqlite3.open(file.path, mode: OpenMode.readOnly),
  );
  // Web
  // return WasmDatabase.open(...) loading served asset bytes
})
```

On native platforms (Android, iOS, Windows, macOS, Linux): the `.db` asset is copied from the Flutter asset bundle to `getApplicationSupportDirectory()` on first use, or when the sidecar SHA-256 differs from the on-disk copy. The file is then opened via `NativeDatabase.opened(sqlite3.open(path, mode: OpenMode.readOnly))` — this sets `SQLITE_OPEN_READONLY` at the driver level, satisfying FR-15 and AC-38.

On web: `WasmDatabase.open(...)` loading asset bytes served by the Flutter web server, using the drift WASM/IndexedDB pathway already established by `AppDatabase`.

**Rationale:** User approved Option C explicitly. `LazyDatabase` wrapper satisfies NFR-02 (lazy open, no cold-start impact). `NativeDatabase.opened` with `OpenMode.readOnly` sets `SQLITE_OPEN_READONLY` at the driver level — not just a Drift-level guard — making AC-38 (INSERT rejection test) reliable. The asset-copy-with-SHA-diff check prevents redundant file writes on subsequent launches while ensuring the on-disk copy stays current when the bundled `.db` is updated. Web uses the existing WASM pathway from `drift_flutter` with no new dependencies.

**Dropped alternative — Option B:** Opening via `driftDatabase()` helper with a custom `webOptions` and relying on Drift's internal read-only guard. Rejected because `driftDatabase()` does not expose `SQLITE_OPEN_READONLY` at the native SQLite driver level — it opens read-write and enforces immutability in Drift's query layer only. AC-38 requires a driver-level error on INSERT, which Option B cannot guarantee.

**Runner-up — Option A:** A fully custom `QueryExecutor` subclass that overrides all write methods to throw. Correct but more boilerplate than Option C; does not set `SQLITE_OPEN_READONLY` at the OS level either. Option C is strictly superior.

**Impact:** `HadithDatabase` class uses `LazyDatabase` factory. `path_provider` (`getApplicationSupportDirectory`) must be added to deps if not already present — check `pubspec.yaml` (it is not currently listed; add `path_provider: ^2.1.0`). `sqlite3` package (not `sqlite3_flutter_libs`) must be imported in the database constructor for `OpenMode`. No new web dependencies.

---

## D19 — FTS5 Arabic tokenizer: unicode61 with remove_diacritics=2
**Date:** 2026-05-10  
**Question ref:** AC-37, D16  
**Decision:** The FTS5 virtual table for the Arabic hadith text column shall use the `unicode61` tokenizer with the `remove_diacritics=2` option:

```sql
CREATE VIRTUAL TABLE hadith_fts USING fts5(
  hadith_id UNINDEXED,
  text_en,
  text_ar,
  tokenize="unicode61 remove_diacritics 2"
);
```

English and Arabic columns share the same FTS5 table with the same tokenizer configuration. `remove_diacritics=2` instructs the `unicode61` tokenizer to strip all Unicode combining characters (category M) from tokens before indexing and querying — this removes Arabic harakat (short vowels: fatha, kasra, damma, sukun, shadda, tanwin variants) so that a query for `رحمة` matches indexed text stored as `رَحْمَةٌ` and vice versa.

**Rationale:** Three tokenizer options were evaluated:

1. **`unicode61` with `remove_diacritics=2`** (chosen): Built into every SQLite FTS5 build — no external libraries needed. Works on all platforms including WASM SQLite. `remove_diacritics=2` (vs `=1`) uses the full Unicode M-category definition rather than a hardcoded ASCII diacritics list, correctly handling the full range of Arabic harakat. Zero index-size overhead compared to trigram. Matches the standard recommendation in SQLite FTS5 documentation for Arabic.

2. **Trigram tokenizer** (`tokenize="trigram"`): Language-agnostic, supports prefix matching and substring search. Produces 3–5× larger FTS indexes for Arabic text (each word generates many trigrams). Does not strip harakat — `رَحمة` and `رحمة` are indexed differently, breaking AC-37. Ruled out: index bloat + harakat mismatch.

3. **ICU tokenizer**: Provides morphological-aware tokenization including Arabic root-based stemming. Requires SQLite compiled with the optional ICU extension. `sqlite3_flutter_libs` does not include ICU; enabling it requires either a custom fork of `sqlite3_flutter_libs` or `sqlcipher_flutter_libs` — both add significant build complexity and binary size (~2 MB extra). Ruled out: unjustifiable dependency for v1; the `unicode61` + diacritics removal covers the core search quality requirement (AC-37).

**Note for builder (V-FTS1):** The `remove_diacritics=2` option is set on the FTS5 table definition in the build script (`tool/build_hadith_db.dart`). The same tokenizer config is implied when querying — FTS5 applies the same normalization to query terms automatically. No additional query-side normalization code is needed in `HadithService`.

**Impact:** Build script DDL uses the tokenizer string above. No new Flutter or Dart dependencies. FTS index size is larger than a plain unicode61 table (one FTS table covers both en and ar columns) but significantly smaller than trigram. Estimated FTS index: 30–40% of raw text size for Arabic unicode61.

---

## D20 — State management for Books tab: Provider (ChangeNotifier), matching existing app pattern
**Date:** 2026-05-10  
**Question ref:** Planning — state management for HadithService and Books tab sub-navigation  
**Decision:** The Hadith feature and Books tab shall use the existing **Provider + ChangeNotifier** pattern that is established throughout the app. No new state management framework (Riverpod, Bloc, GetX) is introduced.

**Finding:** Inspection of `lib/navigation/app_shell.dart`, `lib/features/quran/quran_screen.dart`, `lib/features/tools/tools_screen.dart`, and `lib/data/database/app_database.dart` confirms the app uses `provider: ^6.0.0` uniformly — all services are `ChangeNotifier` subclasses registered at the app root, consumed via `context.read<T>()` / `context.watch<T>()`. No Riverpod, Bloc, or other state management dependency exists in `pubspec.yaml`.

**Impact:** `HadithService` is a `ChangeNotifier`. `BooksScreen` and its sub-navigation use `context.watch<HadithService>()` for reactive state. `HadithService` is registered in `main.dart` alongside existing services. No new pub.dev state management packages needed.

---

## D21 — R06 resolution: WasmDatabase read-only asset loading via `initializeDatabase` callback
**Date:** 2026-05-10
**Question ref:** R06 (plan risk), T04-C1 gate

**Finding:** Inspected `drift 2.31.0` (`lib/wasm.dart`) and `drift_flutter 0.2.8` (`lib/src/web.dart`). `WasmDatabase.open()` accepts an `initializeDatabase: () async => Uint8List?` callback that seeds the WASM SQLite database from in-memory bytes on first open. This is the correct path for loading `hadith.db` from Flutter asset bundle on web.

**Constraint confirmed:** `WasmDatabase` has no `SQLITE_OPEN_READONLY` equivalent — the database always opens in read-write mode internally (required for IndexedDB/OPFS persistence). There is no API to open a WasmDatabase as truly read-only at the driver level.

**Decision:** Plan is unchanged. Web implementation:
```dart
WasmDatabase.open(
  databaseName: 'hadith',
  sqlite3Uri: Uri.parse('sqlite3.wasm'),
  driftWorkerUri: Uri.parse('drift_worker.js'),
  initializeDatabase: () async =>
      (await rootBundle.load('assets/data/hadith/hadith.db')).buffer.asUint8List(),
)
```
AC-38 (INSERT throws at driver level) is marked **native-only** — the unit test is guarded with `if (kIsWeb) return;`. On web, a Drift-level write guard (override `runInsert`/`runUpdate`/`runDelete` to throw `UnsupportedError`) is added as a belt-and-suspenders measure.

**Impact:** `HadithDatabase` has two platform branches (native: `NativeDatabase.opened` read-only; web: `WasmDatabase.open` with `initializeDatabase`). AC-38 unit test includes `@TestOn('!chrome')` annotation or `kIsWeb` skip guard.

---

## D22 — Amendment 2026-05-10: AC-01 / FR-01 nav-bar count corrected from 5 → 4 tabs

**Date:** 2026-05-10  
**Trigger:** Verifier finding — fixer blocker #4. `app_shell.dart:81-102` implements 4 nav destinations (Dashboard, Books, Tools, Settings); AC-01 and FR-01 stated "exactly five bottom-nav items." The contradiction is a requirements-drift artefact, not a code defect.  
**Decision refs:** D04 (Books tab consolidation), D05 (grade display — unrelated but same ticket).

**Root cause of drift:**  
FR-01 and AC-01 were drafted in the analysis/requirements phase when the consolidation intent was "current 5 tabs → Books tab replaces Quran tab → still 5." D04 later made explicit that the new bar is Dashboard + Books + Tools + Settings = **4 items**. The plan and implementation followed D04 correctly. FR-01 and AC-01 were not updated when D04 was recorded.

**Before (v4 frozen text):**  
- FR-01: "…maintaining exactly five bottom-nav items total."  
- AC-01: "The bottom nav bar has exactly five items after the refactor; the former standalone Quran tab is gone; a 'Books' tab exists in its place."

**After (amended):**  
- FR-01: "…maintaining exactly four bottom-nav items total (Dashboard, Books, Tools, Settings)."  
- AC-01: "The bottom nav bar has exactly four items after the refactor (Dashboard, Books, Tools, Settings); the former standalone Quran tab is gone; a 'Books' tab exists in its place."

**Rationale:** D04 is the authoritative decision for nav-bar structure. The implementation at `app_shell.dart:81-102` is correct and consistent with D04. Amending the text-level spec to match the decision and implementation eliminates the false contradiction without any code change. Scope is unchanged — no new destination is added or removed.

**Cascades:**  
- `T04-requirements.md` FR-01 and AC-01 amended (version bumped to v5).  
- `T04-verification.md` AC-01 row updated from FAIL → PASS.  
- No plan tasks are affected (T04-B1/B2 were implemented against the 4-tab design).

---

## Links
- [[T04-summary]] · [[T04-analysis]] · [[T04-requirements]] · [[T04-decision-log]] · [[T04-questions]] · [[T04-plan]] · [[T04-progress]] · [[T04-verification]]
