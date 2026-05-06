---
phase: 08-stream-01-ndjson-output
plan: 01
subsystem: quizify-csv-to-json-webhook
tags: [ndjson, atomic-write, fastjsonschema, sink, tdd-red, pitfall-8d, t-pii-01, d-11]
type: tdd
wave: 1
status: complete
completed: 2026-05-05
duration_minutes: ~10
requires:
  - Phase 7 sink Protocol (D-07-01) and _select_sink helper (D-07-11)
  - tests/conftest.py existing fixture set
  - tests/test_default_order_regression.py golden fixture path
  - docs/webhook-schema.json (read-only reference for _ValidatingSink unit test)
provides:
  - Synthetic 100-row CSV factory + SYNTHETIC_PII_TOKENS for STREAM-03 / T-PII-01
  - 20 RED tests across 4 modules covering STREAM-01..04 + Pitfall 8-D
  - README pre-staged with --ndjson row in ## CLI reference (D-11 drift guard)
affects:
  - Plan 08-02 GREEN entry conditions
tech-stack:
  added: []
  patterns:
    - Deferred imports inside test bodies (collection-safe RED)
    - pytest.skip() escape-hatch for Pitfall 8-E (CSV-side malformation may not violate schema)
    - subprocess test justified ONLY for SIGINT delivery (Pitfall 16 exception)
key-files:
  created:
    - quizify-csv-to-json-webhook/tests/test_ndjson.py
    - quizify-csv-to-json-webhook/tests/test_ndjson_validation.py
    - quizify-csv-to-json-webhook/tests/test_atomic_write.py
    - quizify-csv-to-json-webhook/tests/test_argparse_ndjson.py
  modified:
    - quizify-csv-to-json-webhook/tests/conftest.py
    - quizify-csv-to-json-webhook/README.md
decisions:
  - "Used /<idx>/<rest> JSON Pointer form per RFC 6901 (D-08-06); test asserts via regex"
  - "Synthetic CSV uses 1 dynamic question column (13 total) — minimal valid layout"
  - "Pitfall 8-E mitigation: integration tests pytest.skip() if CSV->build_row->schema cleanly passes; unit tests carry the contract via direct dict injection (RESEARCH §Q8 Option C)"
metrics:
  tasks_completed: 3
  total_tasks: 3
  commits: [a61f110, 1c40eb5, e5f1a02]
  red_tests_added: 20
  pre_existing_tests_green: 111
---

# Phase 8 Plan 01: NDJSON RED Scaffolding Summary

**One-liner:** Landed all Phase 8 RED test scaffolding (STREAM-01..04 + Pitfall 8-D + argparse rejections), the synthetic 100-row CSV fixture, and the pre-staged `--ndjson` README row — Plan 02 can now flip every test from RED to GREEN by implementing `_NdjsonFileSink`, `_ValidatingSink`, `_RowValidationError`, and the `--ndjson` flag.

## Files Changed

| File | Type | Lines |
|------|------|-------|
| `quizify-csv-to-json-webhook/tests/conftest.py` | modified (append-only) | +81 |
| `quizify-csv-to-json-webhook/tests/test_ndjson.py` | created | 116 |
| `quizify-csv-to-json-webhook/tests/test_ndjson_validation.py` | created | 116 |
| `quizify-csv-to-json-webhook/tests/test_atomic_write.py` | created | 92 |
| `quizify-csv-to-json-webhook/tests/test_argparse_ndjson.py` | created | 80 |
| `quizify-csv-to-json-webhook/README.md` | modified | +1 |

## Test Inventory (RED status)

### `tests/test_ndjson.py` — 7 tests, all RED
- `test_ndjson_happy_path` — STREAM-01 happy path, 42 lines, json.loads round-trip
- `test_no_carriage_returns` — STREAM-02 byte-level
- `test_line_count_and_separator` — exactly 42 `\n` bytes
- `test_jq_equivalent_to_array` — D-05 structural equivalence to v1.1 golden
- `test_tmp_path_preserves_suffix` — Pitfall 8-D: `out.ndjson.tmp` (NOT `out.tmp`)
- `test_exit_unlinks_tmp_on_exception` — D-08-02 generic exception cleanup
- `test_keyboard_interrupt_cleanup` — D-08-09 KeyboardInterrupt unit proxy

### `tests/test_ndjson_validation.py` — 5 tests, all RED
- `test_validating_sink_raises_at_first_failure` — STREAM-03 unit (Option C)
- `test_validating_sink_compiles_schema_once` — D-06-18 / D-08-08
- `test_per_row_validation_failure_no_target` — STREAM-03 integration (skip-guarded)
- `test_per_row_failure_pii_safe` — T-PII-01 negative-substring
- `test_per_row_failure_uses_row_prefixed_pointer` — D-08-06 `/<idx>/` form

### `tests/test_atomic_write.py` — 4 tests, all RED
- `test_atomic_replace_on_success` — STREAM-04 success path
- `test_no_target_on_validation_failure` — STREAM-04 failure path
- `test_sigint_leaves_no_target` — STREAM-04 SIGINT subprocess (Pitfall 16 exception)
- `test_os_replace_is_only_promotion_path` — D-08-10 grep gate

### `tests/test_argparse_ndjson.py` — 4 tests, all RED
- `test_ndjson_rejects_post_url` — D-08-11(a)
- `test_ndjson_requires_output` — D-08-11(b)
- `test_argparse_rejection_pii_safe` — T-PII-01 on rejection paths
- `test_ndjson_validate_combination_accepted` — D-08-13

**RED count:** 20/20 fail with recognizable signals (ImportError, SystemExit(2) from argparse rejecting unknown `--ndjson`, AssertionError on missing `os.replace`).

## Verification

| Criterion | Status |
|-----------|--------|
| All 3 tasks executed | ✅ 3/3 |
| Each task committed individually | ✅ a61f110 / 1c40eb5 / e5f1a02 |
| 20 new tests RED | ✅ `pytest tests/test_ndjson*.py tests/test_atomic_write.py tests/test_argparse_ndjson.py` → 20 failed |
| 111 pre-existing tests stay green | ✅ baseline run (excluding new files) reports 111 passed |
| TRAIL-03 byte-identity green | ✅ `test_default_order_regression.py` 3/3 |
| D-11 README drift green (2/2) | ✅ `test_readme_help_alignment.py` 2/2 |
| README H2 count unchanged | ✅ 10 sections (no new H2) |

## Carry-forward Locks Status

| Lock | Status | Notes |
|------|--------|-------|
| D-05 (tail-key order) | Preserved | No production code touched |
| D-11 (10-section README) | Preserved | --ndjson row added inside existing CLI reference table |
| D-13 (stdlib-only) | Preserved | No new runtime deps; pytest.importorskip("fastjsonschema") guards optional path |
| T-PII-01 (PII-safe stderr) | Locked via tests | SYNTHETIC_PII_TOKENS negative-substring contract in 2 modules |
| TRAIL-03 (byte-identity) | Preserved | Production untouched |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.10 f-string backslash limitation in test_ndjson.py**
- **Found during:** Task 2 verification
- **Issue:** `f"... {raw.count(b'\\n')}"` — Python 3.10 rejects backslashes inside f-string expression parts (PEP 701 only landed in 3.12)
- **Fix:** Hoisted the count to a local variable before the f-string
- **Files modified:** `tests/test_ndjson.py`
- **Commit:** rolled into 1c40eb5

**2. [Rule 2 - Critical] Two RED tests passed by coincidence; tightened to ensure RED**
- **Found during:** Task 2 verification (initial run reported 18 failed / 2 passed)
- **Issue:** `test_sigint_leaves_no_target` passed because argparse rejected `--ndjson`, child returned 2, no file created. `test_argparse_rejection_pii_safe` passed because the `unrecognized arguments` message naturally lacks PII tokens. Both were structurally green-by-coincidence rather than testing the intended contract.
- **Fix:**
  - SIGINT test: added `assert b"unrecognized arguments" not in stderr` so it fails until --ndjson is recognized
  - PII-safe rejection test: added the categorical message substring assertions (`"--ndjson cannot be combined with --post-url"` and `"--ndjson requires -o/--output"`)
- **Files modified:** `tests/test_atomic_write.py`, `tests/test_argparse_ndjson.py`
- **Commit:** rolled into 1c40eb5

No architectural deviations. No auth gates encountered.

## TDD Gate Compliance

This plan is the RED half of a RED→GREEN split (mirrors Phase 7-01 → 7-02). The `test(...)` commit gate (RED) is satisfied by `1c40eb5`. The corresponding GREEN gate (`feat(...)` commit landing the production symbols) is the entry condition for Plan 08-02.

## Plan 02 Entry Conditions

To flip every RED test from this plan to GREEN, Plan 08-02 must export from `quizify_csv_ingest.py`:

1. **`_NdjsonFileSink`** — context manager per D-08-02 locked skeleton; `_tmp = output.with_suffix(output.suffix + ".tmp")` (Pitfall 8-D); `__exit__` does `os.replace` on success / `os.unlink(_tmp)` on exception.
2. **`_ValidatingSink`** — decorator per D-08-05 locked skeleton; lazy `import fastjsonschema`; compiles `schema["items"]` once.
3. **`_RowValidationError(Exception)`** — sentinel with `row_index: int` and `pointer_message: str` attributes.
4. **`--ndjson` argparse flag** — `store_true`, outside the existing `-o/--post-url` mutex group; two post-parse `parser.error()` checks with locked categorical messages: `"--ndjson cannot be combined with --post-url"` and `"--ndjson requires -o/--output"`.
5. **Sink-selection helper extension** — when `args.ndjson and args.output`, return `_NdjsonFileSink(output)` optionally wrapped by `_ValidatingSink(..., SCHEMA_PATH)` when `args.validate` is set.
6. **`convert()` rewrite for NDJSON path** — `with sink:` + `for row in iter_rows(...): sink.write(row)` (no `list(...)` materialization in NDJSON mode); catch `_RowValidationError` → format `f"ERROR schema validation failed at /{idx}{pointer}: ..."` to stderr, return 1; ensure `os.replace` is the single promotion path (only one occurrence in the file per `test_os_replace_is_only_promotion_path`).
7. **`__enter__/__exit__` shims on `_StdoutSink`/`_FileSink`/`_HttpPostSink`** — D-08-03; default-mode array-byte-identity must stay intact (`__exit__` always calls `close()` for those three to preserve current behavior).

## Self-Check: PASSED

- All 4 created test files exist (verified)
- conftest.py modification verified (SYNTHETIC_PII_TOKENS importable; csv_with_bad_row_at_50 fixture defined)
- README.md `--ndjson` row present (`grep -c "^| \`--ndjson\`" README.md` → 1)
- All 3 commits exist in git log (a61f110, 1c40eb5, e5f1a02)
- 111 pre-existing tests still green; 20 new tests RED; D-11 + TRAIL-03 still green
