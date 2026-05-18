---
ticket: "T05"
artifact: decision-log
---

# Decisions: T05

| ID | Date | Decision | Rationale | Alternatives Rejected | Source |
|----|------|----------|-----------|----------------------|--------|
| D01 | 2026-05-18 | Audio: reuse `QuranPlayerService.playAyah(surah, ayah)` to play CDN-hosted Quran recitation per step | Service already exists, registered in `main.dart`, and has the right API surface. No new audio infrastructure needed. | (b) Separate local audio files per posture — would require significant content creation and app bundle growth. (c) Unspecified alternative — ruled out. | Q1 owner answer |
| D02 | 2026-05-18 | Navigation: per-prayer detail view opens as a new pushed screen via `Navigator.push` (`MaterialPageRoute`) | Clean separation of list vs detail; consistent with Flutter navigation conventions already used in the app. | In-page expansion/modal — would complicate the already complex `SalahGuideScreen` widget tree. | Q2 owner answer |
| D03 | 2026-05-18 | Step structure: flat 11-step global sequence (Niyyah → Du'a-e-Qunut) used as the universal posture guide | Simpler model for user consumption; consistent ordering across prayers regardless of rakat count. | Rakat-by-rakat structure — the existing screen already shows this; the redesign moves to a posture-first view. | Q3 owner answer |
| D04 | 2026-05-18 | Witr is categorised under Daily Prayers, listed beneath Isha | Witr is performed after Isha; grouping it there reflects practice and avoids an orphaned "Other" category. | Occasional Prayers — rejected by owner; Witr is performed daily. Separate category — unnecessary fragmentation. | Q4 owner answer |
| D05 | 2026-05-18 | Occasional Prayers list: Jumu'ah, Funeral (Janazah), Tasbeeh, Istikhara, Eid, Tarawih, Tahajjud, Duha (plus additional prayers where appropriate) | Owner confirmed all 8 explicitly; broader scope surfaces more utility from a single screen. | Limiting to the original 5 (Jumu'ah, Funeral, Tasbeeh, Istikhara, Eid) — insufficient per owner direction. | Q5 owner answer |
| D06 | 2026-05-18 | Missing step images: use placeholder asset (grey silhouette container) at build time; owner will supply real images post-build | Unblocks builder; preserves layout and sizing contract so real images drop in without UI changes. | Block on images — would stall the ticket indefinitely and add external dependency to the critical path. | Q6 owner answer |
| D07 | 2026-05-18 | Step/image applicability: each prayer defines only the steps it actually uses; not all 11 steps appear for every prayer | Funeral prayer (no ruku/sujud) and Eid (extra takbirs) have different posture sequences. Per-prayer step lists avoid displaying inapplicable posture images. | Apply all 11 steps universally — would show incorrect postures for prayers with non-standard structure. | Q7 owner answer |
| D08 | 2026-05-18 | Gender display: show only the active gender's image and content; hide the inactive gender entirely | Cleaner UI; reduces visual noise; consistent with the gender setting the user has already chosen. | Side-by-side with inactive muted — current text behaviour, but owner prefers full hide for images and text in the new design. | Q8 owner answer |
| D09 | 2026-05-18 | Rakat group selection is an intermediate screen between prayer list and step walkthrough | When a user taps a prayer, they first see the prayer's rakat groups as tappable cards (e.g. "2 Sunnat", "2 Fard"). Tapping a rakat group card launches the full 11-step StepDetailScreen for that rakat type. The count shown tells the user how many rakats they are about to pray. The step sequence is the same for all rakat groups — the 11 steps from FR-05. This introduces a three-level navigation hierarchy: SalahGuideScreen → RakatSelectionScreen (formerly PrayerDetailScreen) → StepDetailScreen. | Flat navigation (SalahGuideScreen → PrayerDetailScreen with embedded step list) — rejected because owner requires the intermediate rakat-group selection step before the posture walkthrough. | Owner clarification 2026-05-18 |

## Amendment 2026-05-18 — Navigation flow: add RakatSelectionScreen intermediate layer

**Trigger:** Owner clarification — navigation must include a rakat group selection step before the step walkthrough.

**Before:**
- FR-04: Tapping a prayer navigates directly to a detail screen showing the flat step list.
- FR-10: The detail screen shows a Sunnah + Fard rakat count summary card.
- Navigation flow: SalahGuideScreen → PrayerDetailScreen (step list + rakat card).
- AC-03: Tapping any prayer card navigates to a detail screen.
- AC-05: The detail screen for Janazah does NOT show Ruku or Sujud steps.
- Out of scope: "A rakat-by-rakat step breakdown within a prayer."
- Out of scope line removed: flat 11-step posture guide replaces rakat-by-rakat view.

**After:**
- FR-04 revised: Tapping a prayer navigates to a RakatSelectionScreen showing rakat group cards.
- FR-10 retired / replaced by new FR-13: the rakat count is surfaced as tappable card labels rather than a static summary.
- New FR-13: RakatSelectionScreen — prayer's rakat groups displayed as tappable cards with count.
- Navigation flow: SalahGuideScreen → RakatSelectionScreen → StepDetailScreen.
- AC-03 revised: tapping prayer → RakatSelectionScreen; tapping rakat card → StepDetailScreen.
- New AC-17, AC-18 added for rakat card display and navigation.
- Out-of-scope line updated: bespoke rakat-by-rakat navigation is now in scope as the intermediate layer (the old flat-only assumption is removed).

**Cascades:** T05-plan.md — C02, C03 task descriptions need update; new task C04 required.

## Amendment 2026-05-18 — Step content, per-rakat sequences, and description field

**Trigger:** Owner-confirmed change (2026-05-18) — full step content for a 2-rakat prayer provided; steps must vary by rakat count; each step must carry description text.

**Before:**
- FR-07: `SalahStep` (as `PrayerStep`) had no mandatory `description` field — only `title`, `action`, optional `recitation`, optional `genderVariant`.
- FR-05: Step sequence was a flat 11-step posture list — the same 11 steps for every prayer regardless of rakat count.
- Out-of-scope: "per-rakat step variation" explicitly excluded.
- No AC covering step count per rakat count or non-empty descriptions.

**After:**
- FR-07 amended: `PrayerStep` MUST carry a `description` field (instructional text + recitation string, plain English, no markdown/HTML).
- FR-14 added: step sequences MUST be generated per rakat count (2/3/4) from canonical templates; not a fixed flat list.
- FR-15 added: `StepDetailScreen` MUST display step description below the posture image.
- AC-19 added: 2-rakat prayer shows exactly 17 steps.
- AC-20 added: step descriptions are non-empty for all steps.
- AC-21 added: 3-rakat Maghrib has correct step count (mid-prayer Tashahhud step included).
- Out-of-scope: "per-rakat step variation" line removed (now in scope).

**Cascades:** T05-plan.md — new task B05 (populate step content for all sequences); C03 done-criteria updated (show description below image); AC coverage table updated.

| ID | Date | Decision | Rationale | Alternatives Rejected | Source |
|----|------|----------|-----------|----------------------|--------|
| D10 | 2026-05-18 | Step sequences are generated dynamically per rakat count; base sequences are canonical 2/3/4-rakat templates. A 2-rakat prayer runs the owner-provided 17-step sequence; a 3-rakat prayer runs rak'ah 1 + rak'ah 2 (Steps 4–11) + rak'ah 3 (Steps 4–9) + Tashahhud/Durood/Tasleem; a 4-rakat prayer runs rak'ah 1 + rak'ah 2 (mid-prayer Tashahhud short) + rak'ah 3 + rak'ah 4 + full Tashahhud/Durood/Tasleem. Witr (3-rakat) adds Du'a-e-Qunut before second Sajdah of final rak'ah. | The previous flat 11-step posture guide did not distinguish rakat progression — users had no guidance on when to stand for a new rak'ah, when to do the mid-prayer Tashahhud, or when the prayer ends. Per-rakat sequences fix this. | Flat 11-step sequence for all rakat counts — rejected because it omits the transitional steps (stand for rak'ah 2, mid-prayer Tashahhud, Durood, Tasleem) that tell the user the structure of the prayer. | Owner clarification 2026-05-18 |
| D11 | 2026-05-18 | Step `description` field is plain English instruction text — no markdown, no HTML. Combines the physical action and the recitation text in a single readable string. | Plain text is the simplest format for rendering in a `Text` widget; it avoids needing a markdown renderer and keeps the data model format-agnostic. Arabic/transliteration content is retained in existing `recitation` fields where present. | Markdown — would require a markdown-rendering widget; unnecessary complexity for instructional text. HTML — same objection, plus unsafe for direct rendering. | Owner data review 2026-05-18 |

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
