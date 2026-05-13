---
quick_id: 260512-uzh
slug: log-and-dry-run
type: execute
wave: 1
depends_on: []
files_modified:
  - quizify-csv-to-json-webhook/quizify_csv_ingest.py
  - quizify-csv-to-json-webhook/README.md
  - quizify-csv-to-json-webhook/tests/test_http_dry_run_and_logs.py
autonomous: true
requirements: [QUICK-UZH-01, QUICK-UZH-02, QUICK-UZH-03]
must_haves:
  truths:
    - "Each row successfully built into a webhook dict emits a one-line INFO log identifying the row (row index + email)."
    - "Each HTTP POST about to be dispatched emits a one-line INFO log (method, url, row_count, bytes)."
    - "Running with `--post-url <https-url> --dry-run` performs all build/validate steps, logs the would-be HTTP request with `dry_run=true`, performs ZERO network I/O, and exits 0."
    - "Running `--dry-run` WITHOUT `--post-url` continues to behave as today (layout inspection mode) — no semantic change."
    - "`--verbose` is required to surface the new INFO logs (existing logging contract preserved)."
  artifacts:
    - path: "quizify-csv-to-json-webhook/quizify_csv_ingest.py"
      provides: "Two new INFO log lines (row_built, http_request) + --dry-run overload for --post-url path"
    - path: "quizify-csv-to-json-webhook/README.md"
      provides: "Updated --dry-run documentation noting HTTP dry-run overload"
    - path: "quizify-csv-to-json-webhook/tests/test_http_dry_run_and_logs.py"
      provides: "Test for --dry-run + --post-url: zero network calls, exit 0, INFO lines emitted"
  key_links:
    - from: "main() in quizify_csv_ingest.py"
      to: "convert() / _HttpPostSink._flush_and_post"
      via: "args.dry_run propagated to convert(...) and short-circuits actual urlopen while still emitting the http_request INFO line"
      pattern: "dry_run=args.dry_run"
---

<objective>
Add observability (per-row INFO log + per-HTTP-request INFO log) and a no-network HTTP dry-run mode to `quizify_csv_ingest.py`.

Purpose: Operators currently have no visibility into which row produced which HTTP request, and no safe way to preview what would be POSTed. This adds both with minimal surface area.

Output: Modified script + README + one new test file. No payload/schema changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@quizify-csv-to-json-webhook/quizify_csv_ingest.py
@quizify-csv-to-json-webhook/README.md
@quizify-csv-to-json-webhook/tests/test_http_post.py
@quizify-csv-to-json-webhook/tests/conftest.py

<interfaces>
Existing relevant identifiers (verified by grep):

- `build_row(...) -> tuple[dict, list[str]]` (line 670) — returns the per-row webhook dict.
- `iter_rows(path, trailer, quiz_title)` — generator that yields the dicts produced by `build_row` (consumed in `convert()` at lines 896/916).
- `_HttpPostSink.__init__(self, url, headers=None, timeout=30.0)` (line 188) — buffer-and-POST sink. Buffers in `self._rows`; sends ONCE on `__exit__` via `_flush_and_post` (line 230).
- `_HttpPostSink._flush_and_post(self)` (line 230) — single chokepoint that builds the `urllib.request.Request` and calls `self._post_once(req)`.
- `_log_http_failure(...)` (line 128) — existing categorical stderr format (key=value pairs). NEW logs MUST mirror this style.
- `configure_logging(verbose)` (line 748) — sets level INFO when `--verbose`, WARNING otherwise. KEEP AS-IS.
- `_build_parser()` (line 944) — already declares `parser.add_argument("--dry-run", action="store_true")` at line 952. The existing semantic is "layout inspection mode" (calls `dry_run()` at line 753). We OVERLOAD this flag: when combined with `--post-url`, it becomes HTTP dry-run.
- `main()` (line 995) — at line 1023, `if args.dry_run: return dry_run(...)`. This branch must be guarded so it only triggers when `--post-url` is absent. When BOTH are set, fall through to `convert(...)` with a new `dry_run=True` kwarg.
- `convert(...)` (line 860) — needs new `dry_run: bool = False` kwarg, propagated into `_select_sink` / `_HttpPostSink`.
- `_select_sink(args, schema_path=None)` (line 368) — constructs `_HttpPostSink(args.post_url, args.header, args.timeout)`. Add a `dry_run` arg to `_HttpPostSink.__init__` and propagate.
</interfaces>

<naming_decision>
**Flag name: reuse `--dry-run`** (do NOT introduce `--dry-run-http`).
Rationale: scope explicitly says "combined with `--post-url`". The existing `--dry-run` already short-circuits writes; extending it to short-circuit HTTP egress is a natural overload. When `--dry-run` is passed without `--post-url`, behavior is UNCHANGED (still calls `dry_run()` for layout summary). README must call out both modes.
</naming_decision>

<log_visibility_decision>
**INFO logs gated behind `--verbose`** (existing contract preserved).
Rationale: changing default verbosity is a logging-contract change with PII implications (emails would land in default stderr). The two new INFO lines DO carry an email substring (row identifier). Keeping them at INFO + behind `--verbose` matches existing `configure_logging` semantics and avoids surprise. Document in README.
</log_visibility_decision>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add row_built + http_request INFO logs and --dry-run HTTP overload</name>
  <files>quizify-csv-to-json-webhook/quizify_csv_ingest.py</files>
  <behavior>
    - When `iter_rows` yields a row in `convert()`, emit `logging.info("row_built row=%d email=%s", idx, email)` ONCE per yielded row. Both code paths in `convert()` (NDJSON streaming branch ~line 896 AND default array-mode ~line 916) must emit the log. `idx` is 1-based row index over yielded rows. `email` comes from `row.get("email", "-")`.
    - In `_HttpPostSink._flush_and_post` (line 230), BEFORE the `with self._post_once(req) as resp:` call (line 240), emit `logging.info("http_request method=POST url=%s rows=%d bytes=%d dry_run=%s", self._url, len(self._rows), len(payload), "true" if self._dry_run else "false")`.
    - Add `dry_run: bool = False` to `_HttpPostSink.__init__` (line 188); store as `self._dry_run`.
    - In `_flush_and_post`: if `self._dry_run` is True, emit the http_request INFO line then `return` (skip `self._post_once`, skip exception handling — no network touched).
    - Add `dry_run: bool = False` kwarg to `convert()` (line 860); thread it into the `sink_args` Namespace (line 878) as `dry_run=dry_run`.
    - In `_select_sink` (line 368), pass `dry_run=getattr(args, "dry_run", False)` into `_HttpPostSink(...)` constructor at line 375.
    - In `main()` (line 1023): change `if args.dry_run:` to `if args.dry_run and not args.post_url:` so the existing layout-inspection `dry_run()` only runs when no post URL. Pass `dry_run=args.dry_run` into the `convert(...)` call at line 1026.
    - DO NOT change `configure_logging`. DO NOT change payload shape. DO NOT change `--verbose` semantics.
  </behavior>
  <action>Implement all bullets in the &lt;behavior&gt; block exactly as specified. Use `logging.info(...)` (not `print`) so the existing `configure_logging` level gates apply. The http_request log must be emitted BEFORE any network attempt so it appears even on timeout. Use the same key=value style as `_log_http_failure` for grep/log-aggregation parity. Per QUICK-UZH-03, when `--dry-run` is combined with `--post-url`, ensure the function returns 0 (no `_HttpDeliveryError` path is reachable).</action>
  <verify>
    <automated>cd quizify-csv-to-json-webhook && python -c "import quizify_csv_ingest as m; import inspect; src = inspect.getsource(m); assert 'row_built' in src; assert 'http_request method=POST' in src; assert 'dry_run' in inspect.signature(m._HttpPostSink.__init__).parameters; assert 'dry_run' in inspect.signature(m.convert).parameters; print('OK')"</automated>
  </verify>
  <done>Script imports cleanly, `_HttpPostSink.__init__` and `convert` both accept `dry_run`, both INFO log strings present in source, existing `dry_run()` layout mode still reachable when `--post-url` is absent.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Test --dry-run + --post-url performs zero network I/O and emits INFO lines</name>
  <files>quizify-csv-to-json-webhook/tests/test_http_dry_run_and_logs.py</files>
  <behavior>
    - Test A `test_dry_run_post_url_zero_network`: run `main([...,  "--post-url", url, "--validate", "--dry-run", "-v", str(valid_csv)])` against the `mock_webhook` fixture using `_respond_200`. Assert `len(received) == 0` (no network) AND the call returns/exits 0.
    - Test B `test_dry_run_post_url_emits_http_request_log`: same invocation, capture stderr via `caplog` (or `capsys`). Assert stderr contains a line matching `http_request method=POST url=https://` AND `dry_run=true`.
    - Test C `test_row_built_log_emitted_under_verbose`: run a normal (non-dry-run, non-post) conversion to stdout with `-v`; assert stderr contains at least one `row_built row=` line.
    - Reuse the fixture pattern from `tests/test_http_post.py` (sys.path insert, `mock_webhook` fixture from conftest, build a tiny valid CSV via existing fixtures dir or inline header matching `classify_headers` expectations — copy header from `tests/fixtures/` if a minimal valid CSV exists, otherwise construct a 1-row CSV mirroring `tests/test_http_post.py::test_happy_path_one_request` style).
  </behavior>
  <action>Create the new test file at the path above. Follow the existing test conventions verbatim: top-of-file `sys.path.insert(0, str(ROOT))`, lazy imports inside test functions, use `mock_webhook` fixture for the loopback URL. For the valid CSV, look in `tests/fixtures/` for an existing minimal CSV; if none, inline a header derived from `classify_headers` requirements (mirror what `tests/test_http_post.py` integration tests use). Use `caplog.set_level(logging.INFO, logger="root")` or capture stderr via `capsys` — match whichever pattern other tests in this repo already use.</action>
  <verify>
    <automated>cd quizify-csv-to-json-webhook && python -m pytest tests/test_http_dry_run_and_logs.py -x -q</automated>
  </verify>
  <done>All three tests pass. `received` list from `mock_webhook` is empty in dry-run tests. INFO lines are visible in captured stderr.</done>
</task>

<task type="auto">
  <name>Task 3: Update README --dry-run documentation</name>
  <files>quizify-csv-to-json-webhook/README.md</files>
  <action>Update the `--dry-run` row in the flags table (line 53) to document BOTH modes: (a) without `--post-url`: prints layout summary to stderr (existing behavior); (b) with `--post-url`: performs all build + validate steps and logs each would-be HTTP request with `dry_run=true` but performs zero network I/O. Add a one-line note that the new `row_built` and `http_request` INFO logs are visible only with `-v/--verbose` (matches existing logging contract). DO NOT alter any other rows or shape of the table.</action>
  <verify>
    <automated>grep -q "dry_run=true" quizify-csv-to-json-webhook/README.md &amp;&amp; grep -q "row_built\\|http_request" quizify-csv-to-json-webhook/README.md &amp;&amp; cd quizify-csv-to-json-webhook &amp;&amp; python -m pytest tests/test_readme_help_alignment.py -x -q</automated>
  </verify>
  <done>README documents the dual-mode `--dry-run` behavior and notes the new INFO logs require `-v`. The existing README/help-alignment test still passes.</done>
</task>

</tasks>

<verification>
- Full test suite: `cd quizify-csv-to-json-webhook && python -m pytest -x -q` is green.
- Manual smoke: `python quizify_csv_ingest.py --post-url https://example.test/hook --validate --dry-run -v <csv>` exits 0, prints `http_request ... dry_run=true` to stderr, never opens a socket.
- Existing `--dry-run` (no `--post-url`) behavior unchanged: layout summary still printed.
</verification>

<success_criteria>
- All three must_haves truths observable.
- No changes to webhook payload shape or schema.
- No regressions in existing test suite.
- New test file passes.
</success_criteria>

<output>
After completion, create `.planning/quick/260512-uzh-log-and-dry-run/260512-uzh-SUMMARY.md` summarizing what shipped.
</output>
