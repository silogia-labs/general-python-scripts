---
quick_id: 260512-tb2
description: Update script to new CSV layout (drop "Lead Verified" column)
status: complete
date: 2026-05-13
---

# Quick Task 260512-tb2 — Summary

## What changed

The new CSV (`docs/quizify-submissions-2.csv`) dropped the `"Lead Verified"`
column from position 4. Migrated the script and tests to the 5-column contact
prefix; renamed the new fixture files to canonical names; regenerated the
v1.0 golden baseline against the new sample.

## Files

- **Script:** `quizify_csv_ingest.py` — `CONTACT_PREFIX` shrunk to 5 cols;
  `build_row` index shift (phone 4→3, status_raw 5→4).
- **Fixtures renamed:** `quizify-submissions-2.csv` → `quizify-submissions.csv`,
  `webhook-quizify-format-example-2.json` → `webhook-quizify-format-example.json`.
- **Golden regenerated:** `tests/fixtures/v1.0_default_order_output.json`.
- **Tests updated:** `conftest.py`, `test_atomic_write.py`,
  `test_quiz_title_precedence.py`, `test_golden_structure.py`,
  `test_logging_pii.py`, `test_row_builder.py`, plus row-count `42 → 15`
  across 7 test files.

## Test result

`160 passed, 4 skipped, 3 failed` (down from 28 failing pre-migration).

## Deferred

3 remaining failures are example-payload **content** drift, not layout:

1. `product_result: 0` is a new top-level field in the example JSON —
   the script does not currently emit it. Real schema addition or
   Quizify-internal noise?
2. `test_specific_tag_distribution_matches_example` expects
   `consent_given` at q-19; depends on which sample row drives the assertion
   and how the new TAG_HEADER_MAP entries (`pelvic_symptom`, `trigger`) interact.
3. `test_multi_select_questions_emit_strings` — new example payload has q-14
   shaped as an object-array instead of a multi-select string. The test's
   pinned multi-select index list needs to follow.

These need product/contract decisions — separate from the mechanical
column-removal migration.
