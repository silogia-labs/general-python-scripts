---
phase: 04-make-com-js-contract-fixes
plan: "01"
subsystem: make-com-js
tags: [contract-fix, bug-fix, make-com, javascript]
dependency_graph:
  requires: []
  provides: [CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02]
  affects: [quizify-mapping.js, score-calculations.js]
tech_stack:
  added: []
  patterns: [IIFE-module, snake_case-tags, D-05-hyphen-key-contract]
key_files:
  modified:
    - quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
    - quizify-csv-to-json-webhook/make-scripts/score-calculations.js
decisions:
  - "D-04-03: Delete product_result ghost line entirely — no comment stub (pure deletion)"
  - "D-04-02: Consumer-side fix for peri_menu — emitter at quizify-mapping.js:167 is correct and untouched"
  - "D-04-01: Remove ! negation on activity_profile condition — no downstream migration needed"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-05-04"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 04 Plan 01: Make.com JS Contract Fixes Summary

Three surgical line-level edits correcting dead key emission, tag-spelling mismatch, and inverted athlete classification across the two Make.com IIFE consumer modules.

## What Was Done

### Task 1 — CONTRACT-01: Delete dead `product_result` key (quizify-mapping.js line 103)

Deleted the line `product_result: record.product_result || null,` from the `output` object literal in `quizify-mapping.js`. This key was always `null` because Python's D-05-locked output uses the hyphenated key `product-recommendation`, not `product_result`. The line directly above it (line 102) already correctly reads `record["product-recommendation"]` and was not touched. Trailing comma on line 102 is valid ES5+ and was left as-is.

**Commit:** b2cc9e2

### Task 2 — MAKE-FIX-01: Replace `"peri-menu"` with `"peri_menu"` (score-calculations.js line 213)

Changed `hasTag(tags, "peri-menu")` to `hasTag(tags, "peri_menu")` on line 213 of `score-calculations.js`. The emitter at `quizify-mapping.js:167` already used the underscore spelling (`peri_menu`) — only the consumer had the outlier hyphen. Before this fix, peri-menopause respondents received `life_stage_unspecified` instead of `peri_menopause_menopause` because `hasTag` performs exact-match and the tag never matched the hyphenated argument.

**Commit:** e7b1e87

### Task 3 — MAKE-FIX-02: Remove `!` negation from `activity_profile` condition (score-calculations.js line 248)

Changed `if (!data.is_athlete) {` to `if (data.is_athlete) {` on line 248 of `score-calculations.js`. Before the fix, non-athletes (`data.is_athlete === false` or `undefined`) were classified as `"athlete"` and athletes as `"non_athlete"`. The `let activity_profile = "non_athlete"` default initializer on line 247 was not modified; the `activity_profile = "athlete"` branch on line 249 was not modified; no `else` branch was added. For all 42 current sample rows where `data.is_athlete` is `undefined` (falsy), the condition is not entered and `"non_athlete"` applies correctly.

**Commit:** 2de4dde

## Grep Gate Evidence (all 6 gates — run post-commit)

```
Gate 1 (expect 0): 0  — grep -c "product_result" quizify-mapping.js
Gate 2 (expect 1): 1  — grep -c "product_recommendation" quizify-mapping.js
Gate 3 (expect 0): 0  — grep -c '"peri-menu"' score-calculations.js
Gate 4 (expect 1): 1  — grep -c "peri_menu" quizify-mapping.js
Gate 5 (expect 0): 0  — grep -c '!data.is_athlete' score-calculations.js
Gate 6 (expect 1): 1  — grep -c 'if (data.is_athlete)' score-calculations.js
```

All 6 gates green.

## Make.com Runtime Verification (operator responsibility)

Shell-grep gates confirm text changes landed. Make.com runtime semantic verification is the operator's responsibility per Plan 02 (CONVENTIONS.md). Per RESEARCH.md and VALIDATION.md:

- **CONTRACT-01**: Use synthetic inline-JSON fixture with `"product-recommendation": "programa-piso-pelvico"` in Make.com module test interface. Verify Module 1 output has `product_recommendation: "programa-piso-pelvico"` and no `product_result` key.
- **MAKE-FIX-01**: Run scenario against CSV row 10 (Karen Retamal) and row 35 (Javielys Mancilla) — both carry `Perimenopausia`. Verify `is_peri_meno: true` and `life_stage` includes `peri_menopause_menopause`.
- **MAKE-FIX-02**: Run with any non-athlete row (e.g. row 5 or row 34, `sport_level = "Recreacional 2-3x/sem"`). Verify `activity_profile: "non_athlete"`. For athlete path, use a synthetic fixture with `is_athlete: true` passed directly to Module 2.

## Deviations from Plan

None — plan executed exactly as written. All three edits were single-character or single-line changes matching the exact pre-conditions documented in RESEARCH.md.

## Threat Flags

None. Phase 4 Plan 01 is three text-level edits to existing IIFE consumer modules. No new input-validation surface, no new auth/session/PII paths. CONTRACT-01 narrows the surface by one dead key.

## Self-Check: PASSED

- [x] quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js exists and modified
- [x] quizify-csv-to-json-webhook/make-scripts/score-calculations.js exists and modified
- [x] Commit b2cc9e2 exists (CONTRACT-01)
- [x] Commit e7b1e87 exists (MAKE-FIX-01)
- [x] Commit 2de4dde exists (MAKE-FIX-02)
- [x] All 6 grep gates green
