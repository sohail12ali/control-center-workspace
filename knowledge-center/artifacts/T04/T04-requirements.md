---
ticket: "T04"
artifact: requirements
status: frozen
version: v5
created: 2026-05-10
frozen: 2026-05-10
---

# Requirements: T04 — Add Hadith Find (Books Tab)

## Decision Baseline

All requirements below are frozen against the decisions in [[T04-decision-log]]:
D01 (full corpus), D02 (three search modes), D03 (offline-first), D04 (Books tab nav refactor),
D05 (grade display), D06 (Hindi deferred), D07 (no Dashboard changes), D08 (fawazahmed0 Unlicense approved),
D09 (build script: `tool/build_hadith_db.dart`), D10 (Dua card removed from Tools grid),
D11 (FR-07 alias JSON map with en + ar abbreviations), D12 (sidecar SHA-256 manifest, cached),
D13 (search bar at top of Books > Hadith, single-screen browse+search), D14 (prebuilt .db committed to repo),
D15 (grade chip when present; "—" when absent), D16 (en + ar FTS; Urdu browse-only),
D17 (implementation-detail tightenings applied at validate v2 → v3; AC-37–AC-41 added at validate v3 → v4 cleanup; no new product decisions),
D22 (AC-01/FR-01 amended: nav-bar count corrected 5 → 4 to match D04 consolidation; verifier blocker #4 trigger; requirements v4 → v5).

---

## Functional Requirements

### FR-01 Books Tab — Navigation Refactor
The bottom navigation bar shall be refactored to introduce a "Books" tab that consolidates the existing Quran feature, the existing Duas feature, and the new Hadith feature as distinct sub-sections within a single navigation destination. The current standalone Quran tab is removed. The Books tab replaces it, maintaining exactly four bottom-nav items total (Dashboard, Books, Tools, Settings). *(Amended v5 per D22: original text said "five"; corrected to "four" to match D04 consolidation decision and verified implementation at `app_shell.dart:81-102`.)*

### FR-02 Books Tab — Sub-section Navigation
The Books screen shall present at minimum three navigable sub-sections: Quran, Hadith, and Duas. Tapping a sub-section navigates to the corresponding existing or new screen. All existing Quran and Dua functionality shall remain fully intact after the refactor — no features are removed, only re-homed.

### FR-03 Hadith Data Bundle — Full fawazahmed0 Corpus
The app shall bundle all 10 fawazahmed0/hadith-api collections as a pre-built SQLite database asset:
1. Sahih al-Bukhari
2. Sahih Muslim
3. Sunan Abu Dawud
4. Jami at-Tirmidhi
5. Sunan an-Nasai
6. Sunan Ibn Majah
7. Muwatta Malik
8. Hadith Nawawi 40
9. Hadith Qudsi 40
10. Shah Waliullah 40

Each collection shall include hadith text in English, Arabic, and Urdu. The database shall be fully offline — no network call is made to retrieve hadith data at runtime.

### FR-04 Hadith Data Bundle — Build Pipeline
A one-time developer-run Dart script at `tool/build_hadith_db.dart` shall fetch the fawazahmed0 JSON source files from GitHub/jsDelivr at a pinned commit SHA, normalize them, and produce:
- A single SQLite database file (`assets/data/hadith/hadith.db`) with FTS5 virtual tables for English and Arabic columns.
- A companion SHA-256 manifest file (`assets/data/hadith/hadith.db.sha256`) containing the hex digest of `hadith.db`.

Both output files are committed directly to the repository as binary assets. CI does not re-run the build script or re-fetch data. Both files are registered in `pubspec.yaml` as Flutter assets. The script shall include a source-URL comment referencing fawazahmed0/hadith-api. A comment in the script documents the manual rebuild procedure (update pinned SHA → run script → commit both outputs).

The build script is a Dart CLI tool (not Python) to keep the toolchain homogeneous. It must be runnable on macOS, Linux, and Windows with `dart run tool/build_hadith_db.dart`.

### FR-05 Hadith Search — Full-Text Keyword Search (en + ar)
The Hadith section shall provide a search bar at the top of the screen. Entering free-text input returns matching hadiths from across all 10 collections using SQLite FTS5. FTS is active for English (`unicode61` tokenizer) and Arabic (`unicode61` tokenizer with diacritics normalization) columns only. When the app locale is Urdu, keyword search is not available; the search bar shows an informational placeholder indicating that keyword search is not yet available in Urdu — browse and numbered lookup remain functional.

Search results shall include: hadith text snippet, collection name, book name, hadith number, and grade chip (or "—" if absent). Results shall be returned in under 500 ms (p95) on a mid-range Android device (Snapdragon 665 class) for a corpus of all 10 collections.

### FR-06 Hadith Search — Hierarchical Browse
Below the search bar (idle state, no query entered), the Hadith screen shall display a collection list enabling hierarchical navigation: Collection list → Book list within collection → Hadith list within book → Hadith detail. Each level shall display the localized name where available in the corpus. Browse is functional for all three locales (en, ar, ur).

### FR-07 Hadith Search — Numbered Reference Lookup
The search bar shall detect numbered reference input by regex (pattern: word + integer, e.g. "Bukhari 6224"). A bundled JSON alias map (`assets/data/hadith/aliases.json`) maps collection name abbreviations — both English (e.g. `"bukhari"`, `"muslim"`, `"tirmidhi"`) and Arabic (e.g. `"البخاري"`, `"مسلم"`) — to fawazahmed0 collection keys (e.g. `"eng-bukhari"`). `aliases.json` is a hand-authored, committed asset — it is not generated by `tool/build_hadith_db.dart` or any other build script; it is updated manually whenever a new collection is added. Only ASCII digit sequences (0–9) are matched in the regex for v1; Arabic-Indic digit input (`٠–٩`) is not recognised and will fall back to full-text search or browse prompt. When a numbered reference is detected and the alias resolves unambiguously to a single hadith, the detail view opens immediately. If the alias is unrecognized or the hadith number does not exist in the collection, the input falls back to full-text search (or browse prompt if locale is Urdu).

### FR-08 Hadith Detail View
The hadith detail screen shall display:
- Hadith text in the user's active locale (en / ar / ur), with Arabic always shown alongside the translation
- Collection name and book name
- Hadith number within the collection
- Grade chip (see FR-09)
- A copy-to-clipboard action for the hadith text + a confirmation snackbar

### FR-09 Hadith Grade Display
Every hadith surface (search results list, browse list, detail view) shall display a grade chip. The chip rendering logic is:
- Corpus provides a grade value (Sahih / Hasan / Daif / or an explicit "unknown" marker) → show the grade chip with that value.
- Corpus provides no grade (null / field absent) → show "—" (em dash) in place of the chip; no chip background color is rendered.

Grade chip labels shall be localized for English, Arabic, and Urdu. The two-state distinction (absent vs explicit-unknown) must be preserved in the SQLite schema as a nullable grade column (NULL = absent; non-null string = corpus-supplied value including "unknown").

### FR-10 Locale Support — en / ar / ur
The Hadith feature shall display hadith text in the app's active locale when the locale is English, Arabic, or Urdu. The locale selector for hadith text shall respect the app-wide locale setting. If the active locale is Hindi (hi), the feature shall fall back to English text and display a non-blocking informational banner stating that Hindi hadith text is not yet available.

### FR-11 Offline-First Operation
The Hadith feature shall be fully functional with no network connectivity. The bundled SQLite database shall be the sole runtime data source. No HTTP client, API call, or CDN request shall occur at runtime for any hadith operation.

### FR-12 Platform Coverage
The Hadith feature shall function correctly on Android, iOS, web (Flutter Web + WASM SQLite), and desktop (Windows, macOS, Linux). On web, the SQLite asset is loaded via the drift WASM/IndexedDB pathway already used by the existing AppDatabase. On Android and iOS the native sqlite3_flutter_libs binary is used. Web asset-load latency for a ~20-30 MB `.db` is a known tradeoff accepted at the time of D14 (committed binary); no additional web-specific optimization is required in v1 beyond what drift_flutter provides out of the box.

### FR-13 No Dashboard Changes
The Dashboard screen shall not be modified in this ticket. No "Hadith of the Day" card, widget, or banner is added to the Dashboard.

### FR-14 Tools Grid — Remove Dua Card
The Dua entry card in the Tools grid (`lib/features/tools/tools_screen.dart`) shall be removed. Duas are accessed exclusively via Books → Duas. No shortcut or deep-link to Duas is retained in the Tools grid.

### FR-15 Hadith Database — Separate Drift Instance
The hadith SQLite database shall be opened as a separate `DatabaseConnection` / Drift database instance, distinct from the existing `noble_salah` AppDatabase (schema v2). The hadith DB is a read-only asset-backed database; it shall not run schema migrations against the `noble_salah` DB. This isolates prayer-tracking and tasbih data from the hadith feature entirely. The SQLite connection shall be opened with the `SQLITE_OPEN_READONLY` flag (or equivalent Drift read-only executor) to enforce immutability at the driver level.

---

## Non-Functional Requirements

### NFR-01 Search Latency
Full-text keyword search (FR-05) shall return results in under 500 ms (p95) on a mid-range Android device (Snapdragon 665 class or equivalent) with the full 10-collection SQLite database. Browse navigation transitions (FR-06) shall complete in under 200 ms (p95). The 500 ms threshold applies to English and Arabic FTS queries. Urdu browse-list rendering shall complete in under 300 ms (p95). The web platform is excluded from the p95 latency SLA (asset-load time is network-dependent on first visit); functional correctness on web is required, not latency parity.

### NFR-02 App Cold-Start Impact
The Books tab and Hadith screen shall not increase app cold-start time by more than 300 ms on Android. The SQLite database shall be opened lazily on first Hadith screen visit, not at app launch. The cold-start measurement applies to Android (measured via `adb shell am start -W`); iOS and web cold-start are not measured in v1. The lazy-open requirement is the mechanism by which this budget is protected; the 300 ms ceiling is an Android-specific acceptance criterion.

### NFR-03 SQLite Asset Integrity
The bundled `hadith.db` file shall be verified via its companion `hadith.db.sha256` sidecar manifest on first launch of the Hadith screen. `tool/build_hadith_db.dart` writes `hadith.db.sha256` as a two-line file: the first line is a schema-version constant (e.g. `v1`) and the second line is the hex SHA-256 digest of `hadith.db`. The verification cache key stored in SharedPreferences combines both lines (e.g. `"v1:<hex-digest>"`); a change to either line (version bump or new digest) invalidates the cache and triggers re-verification on next cold start of the Hadith screen. If the checksum fails, the app shall surface an error state on the Hadith screen and shall not crash. The `.sha256` file is generated by `tool/build_hadith_db.dart` and committed alongside `hadith.db`.

### NFR-04 Memory Footprint
The Hadith feature shall not hold more than 50 MB of in-memory hadith data at any time. Paginated queries shall be used for browse and search result lists; page size shall not exceed 50 hadiths per page.

### NFR-05 Accessibility
The Hadith screen shall meet WCAG 2.1 AA contrast ratios for all text elements including the grade chip. All interactive elements shall have semantic labels usable by screen readers (TalkBack on Android / VoiceOver on iOS).

### NFR-06 License Compliance
The bundled hadith data shall originate solely from fawazahmed0/hadith-api (Unlicense / public domain). The build script (`tool/build_hadith_db.dart`) shall include a comment referencing the fawazahmed0 source URL. A `NOTICES` or `ATTRIBUTION` entry for fawazahmed0 shall be added to the app's distribution artifact as good-practice citation.

### NFR-07 Build Repeatability
Running `dart run tool/build_hadith_db.dart` on a machine with network access and the pinned fawazahmed0 commit SHA shall produce byte-identical `hadith.db` and `hadith.db.sha256` output files given the same input JSON. The script must be runnable on macOS, Linux, and Windows (Dart SDK ≥ 3.0). Build time for the full corpus shall not exceed 10 minutes on a standard developer machine.

**Note on AC-08 determinism:** SQLite page layout and FTS index structure can differ across SQLite library versions and OS page-size defaults. "Byte-identical" is defined as: same SQLite library version + same OS = byte-identical. The build script must pin the sqlite3 library version used. A cross-platform byte-identity guarantee is not required; the committed artifact is the canonical binary, and the `.sha256` is computed from it.

---

## Acceptance Criteria

### Navigation Refactor (FR-01, FR-02)
- [ ] AC-01: The bottom nav bar has exactly four items after the refactor (Dashboard, Books, Tools, Settings); the former standalone Quran tab is gone; a "Books" tab exists in its place. *(Amended v5 per D22.)*
- [ ] AC-02: Tapping Books → Quran opens the existing Quran screen with all existing functionality intact (surah list, ayah display, translation, audio if present).
- [ ] AC-03: Tapping Books → Duas opens the existing Dua screen with all existing functionality intact.
- [ ] AC-04: Tapping Books → Hadith opens the new Hadith screen.
- [ ] AC-05: Any existing internal navigation references that previously deep-linked to the Quran or Dua screens resolve correctly under the new Books tab structure.

### Data Bundle (FR-03, FR-04, FR-11, FR-15)
- [ ] AC-06: The app installs and launches with no network connectivity; the Hadith screen loads and all 10 collections are listed in browse mode.
- [ ] AC-07: The build script (`dart run tool/build_hadith_db.dart`) runs without error on a clean checkout (with network) and produces `hadith.db` and `hadith.db.sha256` registered in `pubspec.yaml`.
- [ ] AC-08: Running the build script twice on the same machine with the same SQLite library version produces byte-identical `hadith.db` output.
- [ ] AC-33: The hadith database opens as a separate Drift DatabaseConnection; the existing `noble_salah` AppDatabase schema (prayer_tracking, tasbih tables) is unmodified after T04 is merged.

### Full-Text Search (FR-05)
- [ ] AC-09: Entering "mercy" (English) in the search bar returns hadiths containing that word from at least two different collections within 500 ms on a mid-range Android test device.
- [ ] AC-10: Search results display collection name, book name, hadith number, a text snippet, and a grade chip (or "—" if absent).
- [ ] AC-11: Entering a query that matches no hadiths shows an empty-state message, not an error.
- [ ] AC-34: With locale set to Urdu, the search bar shows a placeholder informing the user that keyword search is not available in Urdu; the browse collection list remains visible and functional.

### Browse (FR-06)
- [ ] AC-12: The browse mode lists all 10 collections by name in the idle (no-query) state.
- [ ] AC-13: Selecting a collection lists its books; selecting a book lists its hadiths by number; selecting a hadith opens the detail view.
- [ ] AC-14: Back navigation from each level returns to the previous level without reloading the full screen.

### Numbered Lookup (FR-07)
- [ ] AC-15: Entering "Bukhari 6224" in the search bar navigates directly to Sahih al-Bukhari hadith 6224 detail view.
- [ ] AC-16: Entering "Muslim 1" in the search bar navigates directly to Sahih Muslim hadith 1.
- [ ] AC-35: Entering "البخاري 1" (Arabic alias) in the search bar navigates to Sahih al-Bukhari hadith 1.
- [ ] AC-17: Entering a reference for a non-existent hadith number (e.g. "Bukhari 99999") falls back to full-text search on that string.

### Detail View & Grade (FR-08, FR-09)
- [ ] AC-18: The detail view shows Arabic text and the locale-appropriate translation side by side (or stacked for RTL).
- [ ] AC-19: Every hadith detail view shows a grade chip with the corpus-supplied value (Sahih / Hasan / Daif / or corpus "unknown") when the grade field is non-null; shows "—" when the grade field is null (absent in corpus).
- [ ] AC-20: The grade chip label is localized in English, Arabic, and Urdu.
- [ ] AC-21: The copy-to-clipboard action copies the hadith text; a confirmation snackbar is shown.

### Locale Fallback (FR-10)
- [ ] AC-22: With app locale set to Hindi, the Hadith screen displays English text and shows an informational (non-blocking) message that Hindi is not yet available.
- [ ] AC-23: With app locale set to Urdu, all 10 collections display Urdu text where available in fawazahmed0; collections without Urdu fall back to English. Keyword search (FTS) is not available in Urdu; an informational placeholder is shown in the search bar.

### Tools Grid (FR-14)
- [ ] AC-32: The Tools grid no longer contains a Dua card; the card count in `tools_screen.dart` is reduced by one and no broken reference to the former Dua entry point remains.

### Asset Integrity (NFR-03)
- [ ] AC-29: A unit test of the `HadithIntegrityService` (or equivalent) confirms that passing a mismatched SHA-256 digest triggers the error state flow without crashing, using a mock asset loader.
- [ ] AC-36: The SharedPreferences cache key used for integrity verification changes when the version constant in `hadith.db.sha256` changes (e.g. `v1` → `v2`), causing re-verification on next cold start of the Hadith screen without requiring a code change.

### Platform (FR-12)
- [ ] AC-24: The Hadith feature passes a manual smoke test on Android, iOS, and Flutter Web (WASM SQLite) — search (en/ar), browse, and detail view all function.
- [ ] AC-25: No crash occurs on web when opening the Hadith screen with a bundled SQLite asset served via WASM.

### Dashboard Unchanged (FR-13)
- [ ] AC-26: The Dashboard screen diff shows zero changes to widget composition, layout, or data sources.

### Non-Functional
- [ ] AC-27: NFR-01: p95 full-text search latency (English query) is under 500 ms on a Snapdragon 665-class device (measured with Flutter DevTools timeline).
- [ ] AC-28: NFR-02: App cold-start time on Android increases by no more than 300 ms (measured via `adb shell am start -W`) compared to the pre-T04 baseline.
- [ ] AC-30: NFR-04: Heap profiler shows no more than 50 MB of hadith-related in-memory data during normal usage.
- [ ] AC-31: NFR-06: A NOTICES/ATTRIBUTION entry for fawazahmed0 exists in the app's distribution artifact.
- [ ] AC-37: NFR-01 Arabic latency: Entering an Arabic keyword (e.g. `رحمة`) returns results from at least two collections within 500 ms on a Snapdragon 665-class device.
- [ ] AC-38: FR-15 read-only enforcement: Attempting a write operation against the hadith Drift database (e.g. a unit test issuing an INSERT) results in an SQLite error, confirming the connection is opened read-only.
- [ ] AC-39: FR-12 desktop: The Hadith feature passes a manual smoke test on at least one desktop platform (Windows or macOS) — browse and detail view function.
- [ ] AC-40: FR-11 no network: A test using `HttpOverrides` (or equivalent) confirms zero outbound HTTP/HTTPS requests occur during any hadith operation (search, browse, detail view).
- [ ] AC-41: NFR-05 accessibility: An automated accessibility scan (`flutter_test` semantics assertions) confirms all Hadith screen interactive elements have semantic labels, and a contrast ratio check confirms WCAG 2.1 AA compliance for grade chip and hadith body text.

---

## Out of Scope

- **Hindi hadith text** — no Hindi corpus exists in fawazahmed0; deferred to a future ticket (D06).
- **Hadith of the Day Dashboard card** — explicitly deferred (D07); Dashboard is unchanged.
- **Network-backed search** — no Dorar.net, sunnah.com, or any other runtime API call (D03).
- **Semantic or AI-powered search** — out of scope for v1.
- **Hadith bookmarks or favorites** — no personalization features in this ticket.
- **Audio recitation of hadiths** — not in scope.
- **Narrator chain (isnad) display** — fawazahmed0 does not provide isnad; out of scope.
- **Hadith commentary or tafsir links** — out of scope.
- **Sunnah.com or any API-key-gated corpus** — not used (D08).
- **New pub.dev hadith packages** (`hadith`, `dorar_hadith`, `hadith_nawawi`) — custom SQLite build is used instead (D03).
- **Urdu FTS keyword search** — deferred to a future ticket (D16); Urdu is browse + numbered lookup only in v1.
- **Arabic-Indic digit input in numbered lookup** — only ASCII digits (0–9) are matched by the reference-detection regex in v1; Arabic-Indic digits (`٠–٩`) are not recognised and fall through to full-text search or browse prompt (FR-07).
- **Web cold-start / asset-load latency SLA** — web is functionally correct but excluded from p95 latency acceptance criteria (NFR-01 note).
- **Cross-platform byte-identical build output** — determinism guarantee is same-machine/same-SQLite-version only (NFR-07 note).
- **Desktop-specific UI optimizations** — desktop must work (FR-12) but no desktop-specific layout is required in v1.
- **CI/CD automation of hadith DB rebuild** — the build script is a developer tool; CI does not run it (D14).

---

## Links
- [[T04-summary]] · [[T04-analysis]] · [[T04-requirements]] · [[T04-decision-log]] · [[T04-questions]] · [[T04-plan]] · [[T04-progress]] · [[T04-verification]]
