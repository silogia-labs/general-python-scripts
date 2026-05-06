---
phase: 07-refactor-scaffolding-no-op
plan: 01
subsystem: quizify-csv-to-json-webhook
tags: [refactor, tdd-red, sink-layer, iter_rows, readme-drift]
requires:
  - v1.1 test suite (94 tests) green
  - tests/fixtures/v1.0_default_order_output.json
provides:
  - tests/test_default_order_regression.py::test_phase7_refactor_byte_identical_to_v1_0_baseline (capsys twin)
  - tests/test_default_order_regression.py::test_phase7_iter_rows_symbol_exists (RED gate)
  - tests/test_sink_layer.py (full RED scaffolding for sink layer + iter_rows + mutex)
  - README.md `--post-url` row + Limitations softening
affects:
  - Plan 02 (Wave 2) executes against this RED scaffolding
tech-stack:
  added: []
  patterns: [tdd-red, capsys, patch.object-counter, caplog]
key-files:
  created:
    - quizify-csv-to-json-webhook/tests/test_sink_layer.py
  modified:
    - quizify-csv-to-json-webhook/tests/test_default_order_regression.py
    - quizify-csv-to-json-webhook/README.md
decisions:
  - Test 11's CSV header source is docs/quizify-submissions.csv (the single canonical fixture); the plan's fallback inline csv.reader path was used since tests/fixtures/quizify-submissions.csv does not exist and conftest does not export _read_sample_header.
  - Wave 1 verification uses pytest --ignore (not --deselect) for tests/test_sink_layer.py because the file-level ImportError is raised at collection time and --deselect does not skip that. This is the canonical pytest idiom for "skip an entire module that fails to import"; the plan's wave_operator_note used --deselect verbatim, which fails for module-level ImportErrors. Documented for Plan 02 — Plan 02 drops both flags, so this is a Wave-1-only operator concern.
metrics:
  duration_minutes: ~10
  tasks_completed: 3
  files_changed: 3
  completed_date: 2026-05-05
---

# Phase 7 Plan 01: RED Test Scaffolding + README Pre-Stage Summary

Land the failing-RED unit-level test scaffolding (capsys byte-identity twin, sink layer, iter_rows non-prefetch proof, argparse mutex, stderr preservation) and pre-stage the README `--post-url` CLI row before Plan 02's no-op refactor lands.

## What Was Built

Three commits across the test layer + README, with `quizify_csv_ingest.py` deliberately UNCHANGED (D-13 / sub_repos-of-one untouched):

1. **`tests/test_default_order_regression.py`** — appended two functions:
   - `test_phase7_refactor_byte_identical_to_v1_0_baseline` (capsys-based unit-level twin of TRAIL-03; passes today because the existing `convert()` already produces v1.0/v1.1 baseline output — this is the gate that Plan 02 must keep green).
   - `test_phase7_iter_rows_symbol_exists` (FAILS-RED today as designed — the deterministic gate for REFACTOR-01 SC#2).
2. **`tests/test_sink_layer.py`** (new) — 13 tests covering:
   - `_HttpPostSink` stub: silent construct, `NotImplementedError` citing "Phase 9", no-op close.
   - argparse mutex group: `SystemExit(2)` on `-o + --post-url`; OSError-on-missing-CSV returns `rc=1` (sink never instantiated); valid-CSV path propagates `NotImplementedError` (locked except clause does NOT catch it).
   - `_select_sink` factory: stdout / file / http-post dispatch.
   - `iter_rows` shape + **non-prefetch counter-patch proof** via `patch.object` on `build_row` — the load-bearing test that distinguishes a real generator from a hidden `list(reader)`.
   - `_RowStream.exit_code` initialized to 0; flips to 1 on row-length mismatch alongside the Phase-5-locked WARNING template.
   - Empty-CSV ERROR record equals `"CSV is empty"` exactly (v1.1 surface preserved).
   - LayoutError ERROR record is non-empty and not collapsed into the empty-CSV message.
3. **`README.md`** — appended `--post-url URL` row (4 columns matching the existing `Flag | Default | Description | Env var` header) and softened the Limitations bullet to reference v1.2 Phase 9 delivery + Phase 7 stub. D-11 ten-section lock preserved.

## Tests / Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Phase 7 byte-identity twin + iter_rows symbol gate | `30acd3e` |
| 2 | sink layer RED scaffolding | `0c652b1` |
| 3 | README `--post-url` row + Limitations softening | `4e4e515` |

## Verification Results

- **Phase 7 sub-suite RED check:** `pytest tests/test_default_order_regression.py -k phase7` reports `1 passed, 1 failed` — the failure is `test_phase7_iter_rows_symbol_exists` raising `AssertionError` because `iter_rows` does not exist yet. Intended RED.
- **`tests/test_sink_layer.py`:** ImportError at collection (`cannot import name '_FileSink' from 'quizify_csv_ingest'`). Intended RED.
- **Existing v1.1 suite (Wave-1 deselect form):** `pytest --ignore=tests/test_sink_layer.py --deselect tests/test_default_order_regression.py::test_phase7_iter_rows_symbol_exists tests/` → **95 passed, 1 deselected**. The 95 = 94 v1.1 baseline + the new structural twin (which passes coincidentally because pre-refactor `convert()` already matches the baseline — harmless and expected per the plan's verification note).
- **README drift test:** `pytest tests/test_readme_help_alignment.py -v` → **2 passed**. D-11 ten-section lock and substring presence both green.
- **D-13 grep gate:** `grep -E '^\s*(import|from)\s+(urllib|ssl|requests)\b' quizify_csv_ingest.py` → no matches. Source file untouched by this plan.

## Deviations from Plan

### 1. [Rule 1 — Bug] Wave 1 verification: `--deselect` swapped for `--ignore` for the new sink-layer file

- **Found during:** Final verification step.
- **Issue:** The plan's `<wave_operator_note>` and `<verification>` block instructed `pytest --deselect tests/test_sink_layer.py ...`. `--deselect` operates on collected items, but `tests/test_sink_layer.py` raises `ImportError` at collection time (its top-level `from quizify_csv_ingest import _HttpPostSink, ...` is the RED contract). pytest aborts with `Interrupted: 1 error during collection` before deselect logic runs.
- **Fix:** Used `--ignore=tests/test_sink_layer.py` instead. This is the canonical pytest idiom for "skip a module that won't import." Behavior matches the plan's intent: the v1.1 baseline stays green at the Wave-1 commit boundary while the RED tests sit in the repo as collection-skipped.
- **Files modified:** None (verification command only).
- **Plan 02 impact:** None — Plan 02 drops the deselect/ignore entirely (`pytest tests/`) once `iter_rows` and the sink symbols exist.

### 2. [Rule 3 — Blocking] Test 11 fixture path corrected

- **Found during:** Task 2 authoring.
- **Issue:** Plan referenced `tests/fixtures/quizify-submissions.csv` and a `tests.conftest._read_sample_header` helper that does not exist in this repo (only `tests/fixtures/v1.0_default_order_output.json` lives there).
- **Fix:** Used the canonical `docs/quizify-submissions.csv` path (the same path `conftest.py:11` and the existing TRAIL-03 test use) and the inline `csv.reader` block the plan flagged as the fallback. No new conftest helper added (per the plan's explicit instruction).
- **Files modified:** `tests/test_sink_layer.py` (path resolution only).

## Auto-Fix Attempts

None on Tasks 1 / 2. One on the final verification step (above, deviation 1).

## Self-Check: PASSED

- `quizify-csv-to-json-webhook/tests/test_default_order_regression.py` — exists, contains both new functions (verified by `pytest -k phase7` collecting them).
- `quizify-csv-to-json-webhook/tests/test_sink_layer.py` — exists, raises ImportError on collection (verified).
- `quizify-csv-to-json-webhook/README.md` — `--post-url` row present, Limitations softened (verified by drift test green).
- Commits `30acd3e`, `0c652b1`, `4e4e515` — all present in `git log`.
