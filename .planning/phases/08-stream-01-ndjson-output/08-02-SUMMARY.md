---
phase: 08-stream-01-ndjson-output
plan: 02
subsystem: quizify-csv-to-json-webhook
tags: [ndjson, atomic-write, fastjsonschema, sink, tdd-green, context-manager, argparse]
type: tdd
wave: 2
status: complete
completed: 2026-05-05
duration_minutes: ~8
requires:
  - Phase 7 sink Protocol (D-07-01) and _select_sink helper (D-07-11)
  - Plan 08-01 RED test scaffolding (20 tests across 4 modules)
  - docs/webhook-schema.json (loaded once per _ValidatingSink instance)
provides:
  - _NdjsonFileSink (context manager; atomic .tmp + os.replace promotion)
  - _ValidatingSink (decorator; lazy fastjsonschema, compile-once, /<idx>/<rest> JSON Pointer)
  - _RowValidationError (sentinel exception with row_index + pointer_message)
  - --ndjson argparse flag + 2 post-parse parser.error checks (D-08-11 locked)
  - extended _format_validation_error(err, row_idx=None) with row-prefix transform
  - extended _select_sink(args, schema_path=None) — 4-branch dispatch (D-08-12)
  - __enter__/__exit__ shims on _StdoutSink/_FileSink/_HttpPostSink (D-08-03)
  - convert() ndjson kwarg + streaming with-sink path (T-RESOURCE-01 follow-through)
affects:
  - Phase 9 (AUTO-01) entry: _ValidatingSink is the reusable per-egress validation primitive
tech-stack:
  added: []
  patterns:
    - Context-manager sink with atomic .tmp + os.replace (POSIX/Win32 atomic)
    - Decorator-style validation wrapping any _Sink (composes with future sinks)
    - Lazy import inside __init__ for optional extras (D-13 / Pitfall 18)
    - argparse.Namespace as sink-selector input to avoid arg-list explosion (D-08-12)
key-files:
  modified:
    - quizify-csv-to-json-webhook/quizify_csv_ingest.py
    - quizify-csv-to-json-webhook/tests/test_sink_layer.py
decisions:
  - "Used Option A from PLAN: extended _format_validation_error signature with row_idx kwarg (single source of truth, default-None preserves batch-mode byte-identity)"
  - "_select_sink signature changed to (args: Namespace, schema_path) per D-08-12 — avoids 5-arg explosion; pre-existing test_sink_layer tests updated via local _ns() helper"
  - "_RowValidationError catches OSError on iter_rows separately from _RowValidationError so file-open errors keep their existing 'cannot open CSV' template"
metrics:
  tasks_completed: 3
  total_tasks: 3
  commits: [556e646, e84609c, 58d02f3]
  pre_phase_8_tests: 111
  post_phase_8_tests: 131  # 127 passed + 4 skipped per Pitfall 8-E
  phase_8_net_contribution: 20
  loc_quizify_csv_ingest_py: 811
---

# Phase 8 Plan 02: NDJSON GREEN Implementation Summary

**One-liner:** Implemented `_NdjsonFileSink` (atomic .tmp + os.replace), `_ValidatingSink` (lazy fastjsonschema, compile-once, row-prefixed JSON Pointer), `_RowValidationError`, the `--ndjson` argparse flag with two locked post-parse rejections, and the `convert()` streaming with-sink path — flipping all 20 Phase 8 RED tests to GREEN while preserving TRAIL-03 byte-identity, D-11 README drift, and D-13 stdlib-only-at-runtime.

## Files Changed

| File | Type | Lines |
|------|------|-------|
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` | modified | +191 / -13 (net +178) |
| `quizify-csv-to-json-webhook/tests/test_sink_layer.py` | modified | +9 / -3 |

## Symbols Added / Modified

| Symbol | Kind | Notes |
|--------|------|-------|
| `_NdjsonFileSink` | NEW class | CM; atomic write via `.tmp` + `os.replace`; `__exit__` unlinks `.tmp` on any exception incl. `KeyboardInterrupt` |
| `_RowValidationError` | NEW exception | `row_index: int`, `pointer_message: str` |
| `_ValidatingSink` | NEW class | Decorator over inner `_Sink`; lazy `import fastjsonschema`; compiles `schema['items']` once |
| `--ndjson` | NEW argparse flag | `store_true`; outside the existing `-o/--post-url` mutex group |
| `_format_validation_error(err, row_idx=None)` | EXTENDED | Default-None preserves batch-mode output; when set, transforms pointer to `/<idx>/<rest>` per RFC 6901 |
| `_select_sink(args, schema_path=None)` | SIGNATURE CHANGE | 4-branch dispatch per D-08-12 |
| `_StdoutSink.__enter__/__exit__` | NEW shim | Always calls `close()` — preserves v1.1 byte-identity |
| `_FileSink.__enter__/__exit__` | NEW shim | Same as above |
| `_HttpPostSink.__enter__/__exit__` | NEW shim | Same as above |
| `convert(... ndjson=False)` | EXTENDED | NDJSON streaming path; default array-mode path preserved EXACTLY |
| `main()` | EXTENDED | `--ndjson` flag + 2 post-parse `parser.error` checks |

## Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 3 tasks executed and committed | ✅ 3/3 | 556e646 / e84609c / 58d02f3 |
| All 20 Plan 01 RED tests GREEN | ✅ | `pytest tests/test_ndjson*.py tests/test_atomic_write.py tests/test_argparse_ndjson.py` — 16 passed, 4 skipped (Pitfall 8-E) |
| 111 pre-existing tests still GREEN | ✅ | full suite: 127 passed (111 baseline + 16 new green) |
| TRAIL-03 byte-identity GREEN | ✅ | `tests/test_default_order_regression.py` — 3/3 |
| D-11 README drift GREEN (2/2) | ✅ | `tests/test_readme_help_alignment.py` — 2/2 |
| D-13 stdlib-only preserved | ✅ | `grep -nE "^import fastjsonschema\|^from fastjsonschema" quizify_csv_ingest.py` returns nothing (lazy inside `_ValidatingSink.__init__` and `_run_schema_validation`) |
| `os.replace` single promotion path | ✅ | `grep -c "os.replace(" quizify_csv_ingest.py` == 1 |
| No `shutil.move` / `os.rename` | ✅ | `grep -cE "shutil.move\(\|os.rename\(" quizify_csv_ingest.py` == 0 |
| `parser.error(` count | ✅ | == 2 (the two locked NDJSON checks) |
| `args.ndjson` references | ✅ | == 4 (definition + 2 post-parse checks + main->convert thread) |
| Total test count | ✅ | 127 passed + 4 skipped = 131 (≥131 target met) |

## Carry-forward Locks Status

| Lock | Status | Notes |
|------|--------|-------|
| D-05 (tail-key order) | ✅ Preserved | `_NdjsonFileSink.write` uses `json.dump(row, fp, ensure_ascii=False)` — `build_row`'s ordered dict order intact |
| D-11 (10-section README) | ✅ Preserved | No README changes in this plan; Plan 01 already pre-staged the `--ndjson` row |
| D-13 (stdlib-only at runtime) | ✅ Preserved | `fastjsonschema` import stays lazy inside `_ValidatingSink.__init__` |
| T-PII-01 (PII-safe stderr) | ✅ Preserved | `_format_validation_error` reuses categorical-only attributes; argparse rejection messages are categorical |
| TRAIL-03 (byte-identity) | ✅ Preserved | Default array-mode `convert()` path UNCHANGED in structure (list-materialize → batch-validate → try/finally close); NDJSON path is in a separate branch |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing `test_sink_layer.py` tests called `_select_sink(output, post_url)`**
- **Found during:** Task 3 verification — 3 sink-layer tests failed with `AttributeError: 'NoneType' object has no attribute 'post_url'` because `_select_sink` signature changed per D-08-12.
- **Fix:** Added local `_ns(output=None, post_url=None, ndjson=False, validate=False)` helper in the test file that returns an `argparse.Namespace`; updated the 3 existing assertions to call `_select_sink(_ns(...))`. The plan explicitly authorized the signature change ("D-08-12 — recommended: change signature to ... Update the single existing caller in `convert()` accordingly"); the test caller required the same update.
- **Files modified:** `quizify-csv-to-json-webhook/tests/test_sink_layer.py`
- **Commit:** rolled into 58d02f3

No architectural deviations. No auth gates encountered.

## TDD Gate Compliance

This plan is the GREEN half of the RED→GREEN split started by Plan 08-01. The `test(...)` RED gate landed in 1c40eb5 (Plan 01). The corresponding `feat(...)` GREEN gate is satisfied by:
- 556e646 — `feat(08-02): add _NdjsonFileSink + _RowValidationError + CM shims (Task 1)`
- e84609c — `feat(08-02): add _ValidatingSink + row-idx prefix on _format_validation_error (Task 2)`
- 58d02f3 — `feat(08-02): wire --ndjson argparse + _select_sink + convert() rewrite (Task 3)`

All three Task commits are `feat(...)` and follow the RED commits in git log order. REFACTOR phase deferred (no cleanup needed; locked skeletons are already minimal).

## Phase 9 (AUTO-01) Entry Conditions

`_ValidatingSink` is the reusable per-egress validation primitive Phase 9 will compose:
- Wraps any inner `_Sink` (including a future real `_HttpPostSink`).
- Compiles `schema['items']` once per instance.
- Raises `_RowValidationError` (with row index + pointer) on first failure — propagates through nested with-blocks so any inner sink's `__exit__` cleanup fires.
- `__enter__/__exit__/close` delegate to inner — never owns inner's lifecycle.

## Self-Check: PASSED

- `quizify_csv_ingest.py` modified file exists (verified via `wc -l` → 811 lines)
- `tests/test_sink_layer.py` modified file exists (verified via test run)
- All 3 commits exist in `git log --oneline -5`: 58d02f3, e84609c, 556e646
- 127 tests passed + 4 skipped (Pitfall 8-E expected); 0 failed
- Grep gates verified: `os.replace` count == 1; no `shutil.move`/`os.rename`; no top-level `fastjsonschema` import; `class _NdjsonFileSink`/`class _ValidatingSink` count == 1 each
