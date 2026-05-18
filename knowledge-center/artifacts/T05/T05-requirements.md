---
ticket: "T05"
artifact: requirements
status: frozen
version: v3
amended: 2026-05-18
---

# Requirements: T05 — Improve Salah Guide

## Functional Requirements

### FR-01 — Daily / Occasional prayer split
The redesigned Salah Guide screen MUST present two clearly labelled sections: **Daily Prayers** and **Occasional Prayers**. The section headers must be visible without scrolling past either section's content.

### FR-02 — Daily Prayers list
The Daily Prayers section MUST list the following prayers in order: Fajr, Dhuhr, Asr, Maghrib, Isha (with Witr shown as a sub-item beneath Isha).

### FR-03 — Occasional Prayers list
The Occasional Prayers section MUST list exactly the following 8 prayers: Jumu'ah, Funeral (Janazah), Tasbeeh, Istikhara, Eid, Tarawih, Tahajjud, Duha. No additional entries are in scope for this ticket.

### FR-04 — Per-prayer navigation to RakatSelectionScreen *(amended v2)*
Tapping any prayer entry MUST navigate (via `Navigator.push` / `MaterialPageRoute`) to a **RakatSelectionScreen** for that prayer. The back action MUST return to the Salah Guide list. RakatSelectionScreen is an intermediate screen that shows the prayer's rakat groups before launching the step walkthrough (see FR-13).

### FR-05 — Flat 11-step posture sequence *(screen renamed to StepDetailScreen in v2)*
The **StepDetailScreen** (reached via RakatSelectionScreen → rakat group card tap) MUST present steps as a flat, ordered sequence drawn from the universal 11-step posture list: (1) Niyyah, (2) Takbir al-Ihram, (3) Qiyam / Al-Fatiha, (4) Ruku, (5) I'tidal, (6) First Sujud, (7) Jalsa, (8) Second Sujud, (9) Tashahhud, (10) Second Tasleem, (11) Du'a-e-Qunut. Each prayer defines only the steps it actually uses; steps not applicable to a given prayer MUST NOT appear for that prayer.

**Canonical per-prayer step inclusion table (authoritative for builder and verifier):**

| Step | Daily (Fajr, Dhuhr, Asr, Maghrib, Isha) | Witr | Janazah | Eid | Jumu'ah | Tarawih | Tahajjud | Duha | Tasbeeh | Istikhara |
|------|------------------------------------------|------|---------|-----|---------|---------|----------|------|---------|-----------|
| 1 Niyyah | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| 2 Takbir al-Ihram | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| 3 Qiyam / Al-Fatiha | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 4 Ruku | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 5 I'tidal | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 6 First Sujud | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 7 Jalsa | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 8 Second Sujud | yes | yes | no | yes | yes | yes | yes | yes | yes | yes |
| 9 Tashahhud | yes | yes | yes* | yes | yes | yes | yes | yes | yes | yes |
| 10 Second Tasleem | yes | yes | yes* | yes | yes | yes | yes | yes | yes | yes |
| 11 Du'a-e-Qunut | Fajr only | yes | no | no | no | no | no | no | no | no |

*Janazah has four takbirs followed by salam — steps 9 and 10 represent the closing salam sequence; the label may be customised in the data model to reflect Janazah-specific wording.

Note: this table is the baseline. The builder may refine step labels or add Janazah-specific takbir steps within the existing step slots, but MUST NOT add new step numbers outside 1–11 without an `evolve` change to this requirement.

### FR-06 — Gender-aware step display
Each step card MUST display content (image and text) for the active gender only, derived from `GenderService.isMale` via `context.watch<GenderService>()`. The inactive gender's content MUST NOT be rendered. When the user changes their gender setting elsewhere in the app, the detail screen MUST reactively update without requiring navigation or restart.

### FR-07 — Step posture images and description *(amended v3)*
Each step card MUST display a posture image. The image shown MUST correspond to: (a) the active gender, and (b) the step number. Images MUST be served from `assets/images/steps/` in the app bundle, declared in `pubspec.yaml`. Steps for which no final image exists MUST render a placeholder (a grey silhouette container of the same fixed dimensions as a real image) until the owner supplies the asset.

Each `PrayerStep` MUST carry a `description` field — a plain-English string combining the physical action instruction and recitation text for that step. The field MUST NOT be empty or null for any step in any prayer sequence. No markdown or HTML is permitted in this field.

### FR-08 — Asset pipeline: copy and rename step images
All available step images MUST be copied from `knowledge-center/assets/images/` into `assets/images/steps/` and declared in `pubspec.yaml` before the UI build begins. The filename bug (`female_step_ 1.png` has a leading space) MUST be corrected to `female_step_1.png` on copy. The JPEG/PNG inconsistency (`male_step_7.jpg` vs `.png`) MUST be resolved — the builder MUST use a consistent extension; if converting, the resulting file MUST visually match the original.

### FR-09 — Per-step audio playback
Steps that map to a Quranic verse MUST expose a play/stop button. Tapping play MUST invoke `QuranPlayerService.playAyah(surah, ayah)` with the correct surah/ayah mapping for that step. Tapping stop (or play on a currently-playing step) MUST invoke `QuranPlayerService.stop()` or `QuranPlayerService.pause()`. Steps with no Quranic verse mapping MUST NOT show an audio button.

**Canonical step-to-Quran mapping (authoritative for builder and verifier):**

| Step | Verse mapped | Surah | Ayah(s) | Notes |
|------|-------------|-------|---------|-------|
| 1 Niyyah | no | — | — | Silent intention; no audio button |
| 2 Takbir al-Ihram | no | — | — | Takbir is not a Quranic verse |
| 3 Qiyam / Al-Fatiha | yes | 1 (Al-Fatiha) | 1–7 | Play full surah via `playAyah(1, 1)` through `playAyah(1, 7)` or `playSurah(1)` |
| 4 Ruku | no | — | — | Tasbih; not a Quranic verse |
| 5 I'tidal | no | — | — | Short dua; not a Quranic verse |
| 6 First Sujud | no | — | — | Tasbih; not a Quranic verse |
| 7 Jalsa | no | — | — | Short dua; not a Quranic verse |
| 8 Second Sujud | no | — | — | Tasbih; not a Quranic verse |
| 9 Tashahhud | no | — | — | Tashahhud is a hadith-sourced dua, not a Quran verse |
| 10 Second Tasleem | no | — | — | Tasleem phrase; not a Quranic verse |
| 11 Du'a-e-Qunut | yes | 2 (Al-Baqarah) | 201 | Standard Qunut dua with Quranic basis; play `playAyah(2, 201)` |

For prayers where a step recites an additional surah after Al-Fatiha (e.g. a short surah in Qiyam), the builder MAY expose a second audio button mapped to the surah of the app's choice (e.g. Al-Ikhlas, Surah 112) but this is optional scope (not verified by AC-08).

### FR-10 — Rakat / structure summary preserved *(superseded by FR-13 for navigation; retained for data accuracy)*
Each Daily Prayer's rakat structure data (Sunnah + Fard counts) MUST remain in the data model (`PrayerInfo.components`) so it can be rendered on RakatSelectionScreen as tappable group cards (FR-13). The static `_PrayerStructureCard` display is replaced by the interactive rakat group cards; no separate summary widget is required.

### FR-14 — Per-rakat-count step sequences *(added v3)*
Step sequences shown in `StepDetailScreen` MUST be generated per rakat count (2, 3, or 4 rakats) from canonical templates — not a fixed flat 11-step list. The canonical sequences are:

- **2-rakat prayer:** The owner-provided 17-step sequence — Niyyah, Takbeeratul Ihram, Qiyam/Sana, Ta'awwudh & Basmalah, Surah Al-Fatiha, Additional Surah, Ruku, Qaumah, First Sajdah, Jalsah, Second Sajdah, Stand for 2nd Rak'ah, 2nd Rak'ah (Steps 4–11 repeated), Tashahhud, Durood Ibrahim, Tasleem (right), Tasleem (left). Total: 17 steps.
- **3-rakat prayer:** Rak'ah 1 (Steps 1–11 from 2-rakat template), Stand + Rak'ah 2 (Steps 4–11 repeated), Stand + Rak'ah 3 (Steps 4–9 only), then Tashahhud, Durood Ibrahim, Tasleem ×2. Witr (3-rakat) additionally includes Du'a-e-Qunut before the second Sajdah of the final rak'ah.
- **4-rakat prayer:** Rak'ah 1 (Steps 1–11), Stand + Rak'ah 2 (Steps 4–11), mid-prayer Tashahhud (At-Tahiyyat only, short), Stand + Rak'ah 3 (Steps 4–11), Rak'ah 4 (Steps 4–11), then full Tashahhud, Durood Ibrahim, Tasleem ×2.

Each `PrayerInfo` MUST declare its rakat count so the step generator can select the correct template. For prayers with multiple rakat groups (e.g. Fajr: 2 Sunnah + 2 Fard), each group uses its own rakat-count template independently.

### FR-15 — StepDetailScreen displays step description *(added v3)*
`StepDetailScreen` MUST display each step's `description` text below the posture image (or placeholder). The description MUST be visible without interaction — it is not behind a tap or expand action. Font and layout are at the builder's discretion, but the text MUST be legible at default system font size.

### FR-13 — RakatSelectionScreen — rakat group cards *(added v2)*
The RakatSelectionScreen for each prayer MUST display the prayer's rakat groups as a list of tappable cards. Each card MUST:
- Show the group label (e.g. "Sunnat", "Fard", "Witr") and the rakat count (e.g. "2").
- Be formatted as "{count} {label}" (e.g. "2 Sunnat", "2 Fard", "3 Witr").
- On tap, navigate (via `Navigator.push` / `MaterialPageRoute`) to **StepDetailScreen**, passing the applicable `PrayerInfo` (step list) and the selected rakat group context.

The back action from StepDetailScreen MUST return to RakatSelectionScreen. The back action from RakatSelectionScreen MUST return to SalahGuideScreen.

The step sequence shown in StepDetailScreen is the same 11-step sequence defined in FR-05 — the rakat group card is only an entry point and rakat count indicator. For prayers with no component breakdown (some occasional prayers), RakatSelectionScreen MAY show a single "Begin" card, or navigate directly to StepDetailScreen — this is left to the builder, but the three-screen hierarchy MUST be maintained for all Daily Prayers and any prayer whose `PrayerInfo.components` is non-empty.

### FR-11 — New Occasional Prayer content authored
Content (steps, recitations, gender-variant text) for Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, and Duha MUST be authored and included. Janazah and Eid content already exists in the current screen and MUST be migrated to the new data model.

### FR-12 — Data / UI separation
The prayer data model (`SalahInfo`, `Step`, `GenderVariant`, and related types) MUST be extracted from `salah_guide_screen.dart` into a dedicated file (e.g. `salah_guide_data.dart`) so that data and UI are not co-located in the same 1800-line file.

---

## Non-Functional Requirements

### NFR-01 — Startup / navigation performance
The Salah Guide list screen MUST render its first frame within 300 ms of the navigation call on a mid-range device (equivalent to a 2019-era Android device, ~2 GB RAM). The prayer detail screen MUST render its first frame within 300 ms of the `Navigator.push` call.

### NFR-02 — Image memory budget
Step images MUST be loaded at display resolution (no upscaling). The total decoded image memory for a single detail screen MUST NOT exceed 20 MB. This budget is provisional based on estimated ~300 × 400 px image size; the builder MUST verify actual image dimensions during FR-08 and flag to the owner if the real budget exceeds 20 MB.

### NFR-03 — Audio state isolation
Audio triggered from the Salah Guide detail screen MUST NOT conflict with any concurrently-playing Quran audio in other app screens. The `QuranPlayerService` stop/pause API already provides this isolation; the implementation MUST use it rather than creating a separate audio player instance.

### NFR-04 — Reactivity
Gender changes propagate to the open detail screen within one frame (Provider `context.watch` contract). No additional async work is permitted between the `GenderService` notification and the UI rebuild.

### NFR-05 — Code size
`salah_guide_screen.dart` MUST NOT grow beyond 600 lines after the redesign (data extracted to `salah_guide_data.dart`; sub-widgets extracted as needed). No single extracted file (widget or data) MUST exceed 600 lines. There is no aggregate line-count constraint across all files.

### NFR-06 — Placeholder visual contract
Placeholder images MUST be a fixed-size grey container of the same width and height as the real step images, so that swapping in real assets later requires only replacing the file — no layout changes. The placeholder MUST display a centred icon (e.g. `Icons.person_outline`) to signal intent.

---

## Acceptance Criteria

- [ ] AC-01: Opening the Salah Guide screen shows two sections, "Daily Prayers" and "Occasional Prayers", each with its labelled prayers. No prayer from FR-02/FR-03 is missing.
- [ ] AC-02: Witr appears beneath Isha in the Daily Prayers section and is NOT listed elsewhere.
- [ ] AC-03: Tapping any prayer card navigates to RakatSelectionScreen. Tapping a rakat group card navigates to StepDetailScreen. The system back button or back arrow from StepDetailScreen returns to RakatSelectionScreen; back from RakatSelectionScreen returns to SalahGuideScreen — no crash at any level.
- [ ] AC-04: The StepDetailScreen for Fajr shows exactly the steps applicable to Fajr in the correct order; no steps marked inapplicable to Fajr are shown.
- [ ] AC-05: The StepDetailScreen for Janazah does NOT show Ruku or Sujud steps (they are not part of Janazah).
- [ ] AC-06: With gender set to Female, each step card shows the female posture image (or female placeholder) and female text. The male image and text are not rendered.
- [ ] AC-07: Changing gender in app settings while the detail screen is open causes the detail screen to immediately re-render with the new gender's image and text — no navigation required.
- [ ] AC-08: The play button on a step with a Quran verse mapping (steps 3 and 11 per FR-09 mapping table) triggers audio playback; `QuranPlayerService.isPlaying` transitions to `true` within 1 s of the tap (verified in profile mode or via widget test). Tapping the button again stops playback and `isPlaying` returns to `false`.
- [ ] AC-09: Steps with no Quran verse mapping (e.g. Niyyah) do NOT show an audio button.
- [ ] AC-10: Missing step images (female_step_1, female_step_3, male/female steps 10–11) render as a grey silhouette placeholder of the same fixed dimensions. No image-load exception is thrown.
- [ ] AC-11: `pubspec.yaml` declares `assets/images/steps/` and all step image files within it. `flutter pub get` and `flutter build` complete without asset errors.
- [ ] AC-12: `female_step_1.png` (no leading space) and a consistent-extension `male_step_7.png` exist in `assets/images/steps/`.
- [ ] AC-13: The Fajr RakatSelectionScreen shows at least two tappable rakat group cards (e.g. "2 Sunnat" and "2 Fard"). Tapping either card opens StepDetailScreen with the Fajr step sequence.
- [ ] AC-17: Each rakat group card displays the count and label in the format "{count} {label}" (e.g. "2 Sunnat", "2 Fard"). *(added v2)*
- [ ] AC-18: Tapping a rakat group card on any prayer's RakatSelectionScreen navigates to StepDetailScreen showing the full applicable step sequence for that prayer. *(added v2)*
- [ ] AC-14: Content for Jumu'ah, Tasbeeh, Istikhara, Tarawih, Tahajjud, and Duha is present and navigable from the Occasional Prayers section.
- [ ] AC-15: `salah_guide_screen.dart` is ≤ 600 lines. `salah_guide_data.dart` exists and contains the prayer data model.
- [ ] AC-16: The detail screen renders its first frame within 300 ms on a mid-range device (Pixel 3a or equivalent; verified via Flutter DevTools frame timing in `--profile` mode). Builder self-report in progress.md is acceptable if no physical device is available; the verifier may re-run on available hardware.
- [ ] AC-19: A 2-rakat prayer (e.g. Fajr Fard) shown in StepDetailScreen has exactly 17 steps, matching the owner-provided sequence. *(added v3)*
- [ ] AC-20: The `description` field is non-empty for every step across all prayer sequences (2-rakat, 3-rakat, 4-rakat templates and all per-prayer variants). *(added v3)*
- [ ] AC-21: The step sequence for a 3-rakat prayer (e.g. Maghrib Fard) includes a mid-prayer position step between rak'ah 2 and rak'ah 3 — specifically, the Tashahhud (At-Tahiyyat) is NOT shown after rak'ah 2 for Maghrib; instead rak'ah 3 proceeds directly after the second Sajdah of rak'ah 2, and the full Tashahhud appears only after rak'ah 3. The total step count is correct per the 3-rakat template. *(added v3)*

---

## Out of Scope

- Changing the app entry points to `SalahGuideScreen` (Dashboard and ToolsScreen `MaterialPageRoute` calls remain unchanged).
- Named routes or deep-linking to individual prayer detail screens.
- Bespoke local audio files for posture steps (e.g. recorded takbir, tasbih audio). Audio is Quran CDN only, via `QuranPlayerService`.
- A prayer-specific rakat-by-rakat step breakdown was previously out of scope (v2). As of v3 this is IN SCOPE — per-rakat-count step sequences are now a requirement (FR-14). What remains out of scope is a step sequence that differs per individual rakat group card (e.g. "2 Sunnat" vs "2 Fard" of the same prayer showing different steps). The rakat count (2/3/4) drives the template; the rakat group label (Sunnat/Fard) is only an entry-point label. *(updated v3)*
- Side-by-side display of both gender variants (the inactive gender is fully hidden per D08).
- In-app image upload or crowdsourced step image replacement.
- Tarawih night-by-night breakdown (Tarawih is a single entry in the Occasional Prayers list).
- Any changes to `GenderService`, `QuranPlayerService`, or `main.dart` registration.

---

## Open Questions

None. All 8 original clarification questions resolved (see [[T05-questions]] and [[T05-decision-log]]). Navigation flow amended per D09 (2026-05-18 owner clarification).

---

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
