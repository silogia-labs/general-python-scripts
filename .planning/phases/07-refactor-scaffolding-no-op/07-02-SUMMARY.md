---
phase: 07-refactor-scaffolding-no-op
plan: 02
subsystem: quizify-csv-to-json-webhook
tags: [refactor, tdd-green, sink-layer, iter_rows, no-op]
requires:
  - 07-01 RED scaffolding (commits 30acd3e, 0c652b1, 4e4e515, be6f217)
  - v1.1 test suite (94 tests) green
provides:
  - quizify_csv_ingest._Sink Protocol
  - quizify_csv_ingest._StdoutSink / _FileSink / _HttpPostSink
  - quizify_csv_ingest._select_sink factory
  - quizify_csv_ingest._EmptyCsvError sentinel
  - quizify_csv_ingest._RowStream + iter_rows()
  - argparse mutually-exclusive group (-o / --post-url)
affects:
  - Phase 8 (NDJSON streaming) — sink layer is the extension point
  - Phase 9 (HTTP POST delivery) — _HttpPostSink stub turns real
tech-stack:
  added: []
  patterns: [protocol-sink, generator-with-attribute, mutually-exclusive-argparse, sentinel-exception]
key-files:
  created: []
  modified:
    - quizify-csv-to-json-webhook/quizify_csv_ingest.py
decisions:
  - D-07-01..D-07-16 all honored verbatim
  - _run_schema_validation body byte-identical (D-07-09)
  - NotImplementedError propagates out of convert() (Plan 01 contract)
  - D-13 grep gate clean: no urllib/ssl/requests imports
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_changed: 1
  completed_date: 2026-05-05
---

# Phase 7 Plan 02: Refactor Scaffolding GREEN Summary

Land the no-op refactor that turns Wave 1's RED scaffolding GREEN: extract `iter_rows` + `_RowStream`, introduce three-sink layer with `_HttpPostSink` stub, add `--post-url` argparse mutex group. Default-flag output remains byte-identical to v1.1 baseline.

## What Was Built

Single-commit refactor against `quizify-csv-to-json-webhook/quizify_csv_ingest.py`:

1. **Imports:** added `from typing import Iterator, Protocol` (stdlib; D-13 preserved).
2. **Sink layer (between `class LayoutError` and `def normalize_key`):**
   - `_Sink` Protocol (`write(row)`, `close()`).
   - `_StdoutSink` — buffers rows, dumps once on `close()` via `json.dump(..., indent=2, ensure_ascii=False)` + `"\n"`.
   - `_FileSink(output: Path)` — same buffering, opens path on `close()`.
   - `_HttpPostSink(url)` — stores URL silently; `write()` raises `NotImplementedError("HTTP POST delivery lands in Phase 9")`; `close()` is no-op.
   - `_select_sink(output, post_url)` factory: `post_url → _HttpPostSink`, else `output → _FileSink`, else `_StdoutSink`.
3. **`_EmptyCsvError`** sentinel + `_RowStream` class — owns file open, header read, `classify_headers`, missing-trio WARNINGs (D-05-08 verbatim), per-row decode/build/yield loop, `exit_code` mutation on row-length mismatch.
4. **`iter_rows(path, trailer, quiz_title)`** — public factory returning `_RowStream` (ROADMAP SC#2).
5. **`convert()` rewrite** — `stream = iter_rows(...); results = list(stream)` wrapped in `try/except (_EmptyCsvError, LayoutError, OSError)`; validate gate unchanged; `sink = _select_sink(output, post_url)`; `try: for row in results: sink.write(row); finally: sink.close()`. New `post_url` keyword param. `NotImplementedError` is NOT caught — propagates (Plan 01 `test_post_url_with_real_csv_raises_not_implemented` enforces).
6. **`main()` argparse** — replaced standalone `-o/--output` with `parser.add_mutually_exclusive_group()` containing both `-o/--output` and `--post-url`. Final `convert()` call threads `post_url=args.post_url`.

## Tests / Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Refactor + sink layer + iter_rows + argparse mutex | `61a2fde` |
| 2 | Verification-only (D-13 grep gate + full suite) | (no commit; verification task) |

## Verification Results

- **Full pytest suite (no `--deselect`/`--ignore`):** `111 passed` in 1.20s. All Wave 1 RED tests are now GREEN; all v1.1 baseline tests still pass; D-11 README drift test green.
- **D-13 grep gate** (`grep -nE '^[[:space:]]*(import|from)[[:space:]]+(urllib|ssl|requests)\b' quizify_csv_ingest.py`): no matches (exit 1). Clean.
- **Byte-identity smoke** (`python quizify_csv_ingest.py docs/quizify-submissions.csv | diff - tests/fixtures/v1.0_default_order_output.json`): empty diff. Default-flag output matches v1.0/v1.1 baseline byte-for-byte.
- **REFACTOR-01 SC#1-#4:** all satisfied (TRAIL-03 + capsys twin both green; non-prefetch counter-patch test green; mutex + NotImplementedError propagation tests green; 94 v1.1 + D-11 drift + D-13 grep gate all clean).

## Deviations from Plan

None — plan executed exactly as written. Locked verbatim shapes from `<interfaces>` were copied without modification; structural anchors (`class LayoutError`, `def normalize_key`, `def convert`, `def main`) located via grep as instructed; insertion points used symbol boundaries, not line numbers.

## TDD Gate Compliance

Plan-level type is `execute` (Wave 2 GREEN of a multi-wave TDD pair). Wave 1 RED commits in `git log`:
- `30acd3e` test(07-01): byte-identity twin + iter_rows symbol gate
- `0c652b1` test(07-01): sink layer RED scaffolding
- `4e4e515`, `be6f217` README + supporting changes

Wave 2 GREEN commit: `61a2fde refactor(07-02): extract iter_rows + sink layer; add --post-url mutex`. Sequence verified: test → refactor. No REFACTOR-phase commit needed (the refactor IS the GREEN gate; no separate cleanup).

## Auto-Fix Attempts

None. Single-pass refactor; full test suite green on first run.

## Self-Check: PASSED

- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — verified contains `class _HttpPostSink`, `def iter_rows`, `add_mutually_exclusive_group`, `post_url=args.post_url`, `_select_sink(`, and the locked `_run_schema_validation` body byte-identical.
- Commit `61a2fde` — present in `git log` (verified via `git rev-parse --short HEAD`).
- 111 tests pass, byte-identity diff empty, D-13 grep gate clean.
