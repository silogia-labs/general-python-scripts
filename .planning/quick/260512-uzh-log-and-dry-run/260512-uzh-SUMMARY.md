---
quick_id: 260512-uzh
slug: log-and-dry-run
status: complete
completed: 2026-05-12
plan: 260512-uzh-PLAN.md
requirements: [QUICK-UZH-01, QUICK-UZH-02, QUICK-UZH-03]
commits:
  - 3603403  # feat(ingest): row_built + http_request INFO logs + --dry-run HTTP overload
  - c9bdd55  # test(ingest): dry-run + post-url zero-network coverage (incl. Rule 1 fix)
  - 7431bb2  # docs(ingest): README --dry-run dual-mode documentation
files_modified:
  - quizify-csv-to-json-webhook/quizify_csv_ingest.py
  - quizify-csv-to-json-webhook/README.md
  - quizify-csv-to-json-webhook/tests/test_http_dry_run_and_logs.py
tests: 166 passed, 4 skipped (was 163/4 baseline; +3 new)
---

# Quick task 260512-uzh — log + HTTP dry-run summary

Added two INFO log lines (`row_built`, `http_request`) and overloaded
`--dry-run` so combining it with `--post-url` previews the would-be HTTP
request without touching the network. INFO logs remain gated behind
`-v/--verbose` per the locked logging contract.

## Tasks

### Task 1 — source changes (commit 3603403, `feat(ingest):`)
- `_HttpPostSink.__init__` accepts `dry_run: bool = False`; `_flush_and_post`
  emits `http_request method=POST url=... rows=N bytes=N dry_run=<bool>` via
  `logging.info(...)` BEFORE any network attempt and short-circuits when
  `dry_run=True`.
- `convert(...)` gains a `dry_run` kwarg, threaded into the
  `_select_sink` Namespace and into `_HttpPostSink`.
- Both `convert()` write loops (NDJSON streaming + array-mode) emit one
  `row_built row=<idx> email=<email>` INFO line per yielded row (1-based).
- `main()` guards the layout-inspection `dry_run()` branch behind
  `not args.post_url`, so combining `--dry-run` + `--post-url` falls through
  to `convert()` with `dry_run=True`.
- `configure_logging` and payload shape unchanged; key=value style mirrors
  the existing `_log_http_failure` chokepoint.

Verification: `assert 'row_built' in src; assert 'http_request method=POST'
in src; signatures expose dry_run; full suite green.`

### Task 2 — tests (commit c9bdd55, `test(ingest):`)
- New `tests/test_http_dry_run_and_logs.py` with three tests:
  A. `test_dry_run_post_url_zero_network` — `mock_webhook` records 0 requests.
  B. `test_dry_run_post_url_emits_http_request_log` — stderr contains
     `http_request method=POST` + `url=https://` + `dry_run=true`.
  C. `test_row_built_log_emitted_under_verbose` — stderr contains
     `row_built row=` and `row_built row=1` for normal `-v` conversions.
- Switched from `caplog` to `capsys` because `configure_logging` calls
  `basicConfig(force=True, stream=sys.stderr)` which detaches the caplog
  handler. Added autouse fixture to tear down root-logger handlers between
  tests so the captured-stderr stream doesn't leak into later tests'
  tracebacks (would otherwise trip the PII gate).

### Task 3 — README (commit 7431bb2, `docs(ingest):`)
- Updated the `--dry-run` row in the flags table to document both modes
  (with vs. without `--post-url`) and the visibility requirement (`-v` to
  surface the new `row_built`/`http_request` INFO logs).
- `tests/test_readme_help_alignment.py` still passes.

## Deviations

**[Rule 1 — bug] Array-mode `convert()` did not drive the sink via the
context-manager protocol.** Pre-existing array-mode code did
`sink = _select_sink(...); sink.write(row); sink.close()`. For `_HttpPostSink`
the actual POST happens in `__exit__`, so this path NEVER posted when
invoked through `main(--post-url ...)`. The latent bug was hidden because
`tests/test_http_post.py` exercises `_HttpPostSink` directly (not through
`main()`), and `tests/test_http_post_pii.py` does the same. Fixed by
wrapping the write loop in `with sink:` (mirrors the NDJSON branch). Other
sinks (`_StdoutSink`/`_FileSink`) already implement `__enter__`/`__exit__`
that calls `close()` once, so behaviour is unchanged for them.

Without this fix the new `http_request` INFO log would not have been
reachable via the `main()` flow — exposing the latent bug was a direct
prerequisite for QUICK-UZH-03's dry-run preview.

Fix shipped in the same commit as Task 2 (c9bdd55) to keep the test that
proves the fix co-located with the fix itself.

No other deviations. No payload/schema/CLI shape changes beyond the
plan-specified additions. No new dependencies.

## Test results

`cd quizify-csv-to-json-webhook && python -m pytest -x -q`
→ **166 passed, 4 skipped** (baseline was 163/4; +3 new tests, no regressions).

## Smoke-equivalent

`main(["--post-url", "https://127.0.0.1:<mock>", "--validate", "--dry-run",
"-v", "<live sample CSV>"])` — stderr shows N `row_built` lines + one
`http_request method=POST ... dry_run=true` line; `mock_webhook` records 0
requests; exit 0. Verified by `test_dry_run_post_url_zero_network` and
`test_dry_run_post_url_emits_http_request_log`.

## Self-Check: PASSED

- File `quizify-csv-to-json-webhook/quizify_csv_ingest.py`: modified ✓
- File `quizify-csv-to-json-webhook/README.md`: modified ✓
- File `quizify-csv-to-json-webhook/tests/test_http_dry_run_and_logs.py`:
  created ✓
- Commit 3603403: present in `git log` ✓
- Commit c9bdd55: present in `git log` ✓
- Commit 7431bb2: present in `git log` ✓
- Full test suite: green (166 passed, 4 skipped) ✓
