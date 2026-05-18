---
tags: [active]
status: Open
ticket: "T05"
---

# T05: Improve Salah Guide

**Status:** In Progress  
**Stage:** CLARIFY/CANONICAL re-open — Navigation flow amended (D09); C02/C03/C04 need rebuild  
**Owner:** anjum@hu-manity.co  
**Created:** 2026-05-18  
**Due:**  

## Overview

Redesign the existing Salah Guide screen in Noble Salah (Flutter app) to be richer and more structured. Split into Daily Prayers and Occasional Prayers sections, add a three-level navigation hierarchy (SalahGuideScreen → RakatSelectionScreen → StepDetailScreen) with per-rakat-group entry points, step images (gender-aware), and playable audio.

## Current State

All slices A–D complete. NFR-05 file-cap compliance enforced: occasional step sequence file split into 3 parts (_a/_b/_c) + barrel; fourRakatSteps() split to dedicated file. All guide files ≤ 600 lines. dart analyze 0 errors; flutter build apk --debug exits 0.

## Links
- [[T05-summary]] · [[T05-analysis]] · [[T05-requirements]] · [[T05-decision-log]] · [[T05-questions]] · [[T05-plan]] · [[T05-progress]] · [[T05-verification]]
