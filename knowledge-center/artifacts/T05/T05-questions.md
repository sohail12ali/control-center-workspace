---
ticket: "T05"
artifact: questions
---

# Open Questions: T05

| # | Question | Status | Stage | Owner | Decision |
|---|----------|--------|-------|-------|----------|
| Q1 | What exactly does "audio sourced from Quran audio already in the app" mean? Is it (a) playing the CDN recitation for Quranic verses per step via `QuranPlayerService.playAyah()`, (b) a separate set of audio files for each step posture, or (c) something else entirely? | resolved | CLARIFY | anjum@hu-manity.co | D01 — Reuse `QuranPlayerService`; play per-verse CDN audio for the recitation in each step. |
| Q2 | Should the per-prayer detail view be a separate pushed screen (new route), or an in-page expansion/modal within the existing `SalahGuideScreen`? | resolved | CLARIFY | anjum@hu-manity.co | D02 — New pushed screen via `Navigator.push` (new `MaterialPageRoute`). |
| Q3 | The ticket brief names 11 steps (Niyyah through Du'a-e-Qunut). The existing screen organises steps per rakat/section within each prayer, not as a global 11-step sequence. Should the redesign use the 11-step sequence as a universal posture guide, or keep the rakat-by-rakat structure that already exists? | resolved | CLARIFY | anjum@hu-manity.co | D03 — Flat 11-step global sequence; no rakat-by-rakat breakdown. |
| Q4 | Where should Witr sit — Daily Prayers (since it follows Isha) or Occasional Prayers? The current screen lists it separately. | resolved | CLARIFY | anjum@hu-manity.co | D04 — Witr is part of Daily Prayers, listed under Isha. |
| Q5 | For the Occasional Prayers section, which prayers are in scope? The brief lists Jumu'ah, Funeral, Tasbeeh, Istikhara, Eid. Janazah (Funeral) and Eid already exist in the current screen. Are Jumu'ah, Tasbeeh, and Istikhara the only new content to author, and is the final list exactly those 5? | resolved | CLARIFY | anjum@hu-manity.co | D05 — Include all 8: Jumu'ah, Funeral (Janazah), Tasbeeh, Istikhara, Eid, Tarawih, Tahajjud, Duha (plus others that make sense). |
| Q6 | Missing images: female_step_1 (filename has a leading-space bug), female_step_3, male_step_10, female_step_10, male_step_11, female_step_11 are all absent. Should the builder use a placeholder (grey silhouette container) until the owner supplies them, or block on images being provided first? | resolved | CLARIFY | anjum@hu-manity.co | D06 — Use placeholder assets now; owner will supply real images later. |
| Q7 | Should the 11-step image sequence apply to all prayers equally, or only to the 5 daily Fard prayers? For example, does Janazah (no ruku/sujud) or Eid (extra takbirs) use the same 11 images? | resolved | CLARIFY | anjum@hu-manity.co | D07 — Steps/images shown only when needed; not every prayer uses all 11 steps (e.g. Funeral prayer has no ruku/sujud in the same way). |
| Q8 | Should both gender variants (male text + female text) continue to be shown side-by-side with the inactive one muted, or should only the user's gender variant be shown (with the other hidden entirely)? | resolved | CLARIFY | anjum@hu-manity.co | D08 — Show only the active gender's image (and text); hide the other entirely. |

| Q9 | What are the exact step names, physical actions, and recitation texts for each step in a 2-rakat prayer? | resolved | CANONICAL | anjum@hu-manity.co | Owner provided full 17-step 2-rakat sequence on 2026-05-18. Drives FR-07 (description field), FR-14 (per-rakat templates), FR-15 (display), AC-19/20/21. Recorded in D10, D11. |
| Q10 | How do step sequences differ for 3-rakat and 4-rakat prayers? | resolved | CANONICAL | anjum@hu-manity.co | Owner provided rakat progression rules: 3-rakat = Steps 1–11 + repeat Steps 4–11 + Steps 4–9 + Tashahhud/Durood/Tasleem; 4-rakat = rak'ah 1 + rak'ah 2 + mid-prayer Tashahhud (short) + rak'ah 3 + rak'ah 4 + full Tashahhud/Durood/Tasleem. Witr (3-rakat) adds Du'a-e-Qunut before second Sajdah of final rak'ah. Recorded in D10, FR-14. |

## Summary

- **Open**: 0
- **Resolved**: 10
- **Deferred**: 0

## Blocking analysis
All blockers resolved. Q9 and Q10 answered by owner-provided step sequence (2026-05-18); requirements v3 drafted accordingly.

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
