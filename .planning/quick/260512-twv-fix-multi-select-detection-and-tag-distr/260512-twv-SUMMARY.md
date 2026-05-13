---
quick_id: 260512-twv
description: Fix multi-select detection by header pattern; align tests with new payload
status: complete
date: 2026-05-13
---

# Quick Task 260512-twv — Summary

## What changed

Resolves the three deferred failures from quick task `260512-tb2`. Root
cause was a real script bug, not just test drift.

### Script bug fix

`shape_answer` previously decided string-vs-object-array purely by the
`", "` separator heuristic. That worked when multi-select cells happened
to contain comma-separated values, but failed for single-token answers
like `"Ninguno"` at multi-select questions (q-3, q-14, q-15, q-16). The
example payload emits these as strings regardless of token count.

Added `MULTI_SELECT_HEADER_KEYWORDS = ("signos de alarma", "piso pélvico",
"disparadores", "limitaciones")` and a `_is_multi_select_header()` helper.
`shape_answer` now takes the header text and short-circuits to a string
when the header matches a multi-select pattern, regardless of cell content.

### Test alignment

- `test_specific_tag_distribution_matches_example`: `consent_given` lands
  at q-20 (the "Consiento..." header), not q-19 — fixed assertion + exclusion.
- `test_multi_select_questions_emit_strings`: dropped the `", " in v`
  assertion; the contract is "emit as string", not "emit a multi-token string".
- `test_aligned_row_top_level_keyset_matches_example`: excluded
  `product_result` from the keyset check (per user direction — defer to a
  later contract decision).
- `test_full_answers_synthetic_row_shape`: q-3 ("Ninguno") now correctly
  emits as a string (matches example shape).

### Baseline regenerated

`tests/fixtures/v1.0_default_order_output.json` re-emitted with the new
multi-select logic.

## Test result

`163 passed, 4 skipped, 0 failed` (up from 160/3).

## Deferred

- `product_result` field still not emitted. The two example payloads show
  it as either `0` or `"7"` — needs a product decision before adding.
- `docs/quizify-submissions-2.csv` and
  `docs/webhook-quizify-format-example-2.json` kept untracked as reference.
