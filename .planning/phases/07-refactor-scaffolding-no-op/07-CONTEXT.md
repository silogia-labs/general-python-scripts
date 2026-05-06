# Phase 7: Refactor Scaffolding (no-op) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure `convert()` in `quizify-csv-to-json-webhook/quizify_csv_ingest.py` around an `iter_rows()` generator path and three pluggable output sinks (`_StdoutSink`, `_FileSink`, `_HttpPostSink` stub). Default-flag invocation against `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` MUST produce byte-identical output to the v1.1 golden fixture (parallel test to TRAIL-03 stays green). All 94 v1.1 tests still pass. D-11 README ten-section drift test stays green. D-13 stdlib-only-at-runtime preserved (no new runtime imports). Argparse exposes a mutually-exclusive `-o`/`--post-url` group. `_HttpPostSink` is a stub: it accepts a URL silently in `__init__` (no validation — that's Phase 9) but raises `NotImplementedError` on `write()`.

This phase introduces NO new behavior. NDJSON output is Phase 8. Actual HTTP POST delivery is Phase 9. Make.com hygiene + node:test is Phase 10. Per-row schema validation is a Phase 8 concern, not a Phase 7 concern.

</domain>

<decisions>
## Implementation Decisions

### Sink Interface

- **D-07-01 (Sink Protocol = `write(row) + close()`):** Sinks conform to a `typing.Protocol` exposing `write(row: dict) -> None` and `close() -> None`. Streaming-native: callers iterate `_RowStream` and call `sink.write(row)` per yield. `_StdoutSink` and `_FileSink` internally accumulate rows into a `list[dict]` and call `json.dump(...)` exactly once on `close()` — this preserves byte-identical default output (D-05 tail-key order, indent=2, ensure_ascii=False, trailing newline). Phase 8 NDJSON will introduce a new `_NdjsonFileSink` (or override `write()` on `_FileSink` behind the `--ndjson` flag) that flushes per row instead of buffering. Choosing `Protocol` over `ABC` because it's structural (no inheritance ceremony) and lighter for a 3-class internal hierarchy. Use of `typing.Protocol` does NOT add a runtime dependency — it ships in stdlib (`typing`) since Python 3.8 (D-13 preserved; project floor is 3.9 per D-06-03).
- **D-07-02 (`_StdoutSink` writes to `sys.stdout`):** Constructor takes no args. Internally `self._rows: list[dict] = []`. `close()` emits `json.dump(self._rows, sys.stdout, indent=2, ensure_ascii=False)` followed by `sys.stdout.write("\n")`. Mirrors today's lines 500-502 exactly.
- **D-07-03 (`_FileSink` writes to `output: Path`):** Constructor takes `output: Path`. Internally accumulates rows. `close()` opens the path with `output.open("w", encoding="utf-8")`, calls `json.dump(...)` with the same args as `_StdoutSink`, writes `"\n"`. **Note for Phase 8:** atomic `os.replace(tmp, target)` lands in Phase 8 STREAM-04 — Phase 7 keeps the simpler direct-open behavior to stay byte-identical. Mirrors today's lines 503-506.
- **D-07-04 (`_HttpPostSink` stub depth — accepts url, raises on write):** `__init__(self, url: str)` stores `self.url = url` silently. NO URL validation, NO HTTPS-only check, NO header parsing, NO timeout — those are all Phase 9. `write(self, row)` raises `NotImplementedError("HTTP POST delivery lands in Phase 9")`. `close(self)` is a no-op. This shape lets Phase 7 ship the mutex-group success criterion (SC#3) with a real test that verifies argparse parses `--post-url`, the sink instantiates, and the first row write raises — without leaking any Phase 9 behavior.

### iter_rows() boundary

- **D-07-05 (`_RowStream` wrapper class owns header phase + per-row build + exit-code state):** A small `_RowStream` class (or factory returning a generator-with-attribute object) owns: file open with `encoding="utf-8-sig", newline=""`, `csv.reader`, `next(reader)` for header, `classify_headers(...)` call, missing-trio `logging.warning` emissions, the per-row decode/build loop, and a mutable `self.exit_code` attribute that gets `|= 1` on row-length mismatches. `__iter__` yields one built `dict` per CSV row; nothing accumulates the full list inside the generator path (ROADMAP SC#2). The caller in `convert()` materializes via `list(stream)` (validation requires the full list — see D-07-08) but the materialization happens at the call site, not inside the generator.
- **D-07-06 (`iter_rows()` is the public/conceptual name; `_RowStream` is the implementation):** ROADMAP SC#2 names the symbol `iter_rows()`. Planner's discretion: either expose `iter_rows(path, trailer, quiz_title) -> _RowStream` as a thin factory function, OR rename `_RowStream.__iter__` and have callers invoke `iter_rows()` directly as a generator function with exit-code surfaced via a different mechanism. Prefer the factory-returning-`_RowStream` shape because it cleanly carries `exit_code` state out of the generator without globals or callbacks.
- **D-07-07 (LayoutError + empty-CSV exception handling moves to caller):** Today's `convert()` catches `LayoutError` (line 451) and `StopIteration` for "CSV is empty" (line 444) BEFORE the row loop. After the refactor, both surface on the FIRST `next()` of `_RowStream`. `convert()` must wrap iteration (`list(stream)`) in `try/except LayoutError` returning 1 with the same `logging.error("%s", err)` message, and detect the empty-CSV path either by catching `StopIteration` inside `_RowStream.__iter__` and re-raising as a sentinel exception OR by having `_RowStream` detect emptiness and log+set exit_code itself. Planner's call on which mechanism — both must produce identical stderr output and exit code to today.

### Validation Placement

- **D-07-08 (Schema validation stays batch in `convert()`, pre-sink-open):** Validation timing remains exactly as today (lines 495-498): build the full row list, then if `validate=True` call `_run_schema_validation(results, SCHEMA_PATH)`, return on non-zero before opening any sink. NO per-row validation introduced in Phase 7. NO `_ValidatingSink` decorator class introduced in Phase 7. This preserves byte-identical default output, preserves D-06-16 (post-build pre-write), preserves the existing 94 tests' assumptions about validation timing, and leaves Phase 8's STREAM-01 SC#2 ("no final file on validation failure") to design per-row validation as part of NDJSON's actual behavior change.
- **D-07-09 (`_run_schema_validation` body unchanged):** The function at lines 364-410 is NOT modified. Its `import fastjsonschema` lazy import (D-06-17), single `compile()` call (D-06-18), `_format_validation_error` PII-safe formatting (D-06-20 / Pitfall 17), missing-extra template (D-06-19), exit code 1 on all failures (D-06-21) — all preserved verbatim.

### Argparse

- **D-07-10 (Mutually-exclusive group: `-o`/`--output` and `--post-url`):** Replace today's standalone `parser.add_argument("-o", "--output", ...)` (line 517) with `group = parser.add_mutually_exclusive_group()` containing both `-o`/`--output` (existing `type=Path, default=None`, existing help text) and `--post-url` (new, `default=None`, no other validators in Phase 7). The `--ndjson` flag is NOT added in Phase 7 (Phase 8). All other flags (`--dry-run`, `-v`/`--verbose`, `--trailer-columns`, `--emit-json`, `--validate`, `--quiz-title`) stay at parser level, unchanged.
- **D-07-11 (`args.output` field name preserved; new `args.post_url`):** No rename. `args.output: Path | None` continues to drive `_FileSink` vs `_StdoutSink` selection. `args.post_url: str | None` drives `_HttpPostSink` selection. Sink selection helper (e.g., `_select_sink(args) -> _Sink`) is planner's choice — single function, three branches: `args.post_url` → `_HttpPostSink(args.post_url)`; `args.output` → `_FileSink(args.output)`; else → `_StdoutSink()`. Argparse's mutex group guarantees the first two are not both set.
- **D-07-12 (No `--post-url` requires `--validate` gate in Phase 7):** Phase 9 success criterion #2 says argparse must reject `--post-url` without `--validate` (exit 2 at argparse). Phase 7 does NOT land that gate — selecting `--post-url` alone parses successfully and crashes at first `write()`. Justification: the SC#3 mutex-group test only requires the *flag pair* to be mutually exclusive; the validation-gate is Phase 9's surface. Keeping it out of Phase 7 reduces the no-op refactor's blast radius.

### Test Strategy

- **D-07-13 (Parallel TRAIL-03 golden-fixture regression test is the gate):** The single most important test for this phase asserts that `python quizify_csv_ingest.py docs/quizify-submissions.csv` (default flags, no `-o`, no `--post-url`, no `--validate`) produces byte-for-byte identical stdout to the v1.1 golden fixture used by TRAIL-03. Planner picks the file location (likely a new `tests/test_refactor_byte_identity.py` or extend an existing test module) — Pitfall 16 carry-forward (unit-level, not subprocess-driven) applies: prefer calling `convert(path, ...)` with stdout captured via pytest's `capsys` over `subprocess.run`.
- **D-07-14 (`_HttpPostSink` stub test):** A test asserts: (a) `parser.parse_args(["--post-url", "https://example.test/hook", "docs/quizify-submissions.csv"])` succeeds; (b) `_HttpPostSink("https://example.test/hook")` constructs without raising; (c) calling `_HttpPostSink(...).write({})` raises `NotImplementedError` whose message mentions Phase 9 (or similar deferred-feature signal).
- **D-07-15 (Argparse mutex test):** A test asserts that `parser.parse_args(["-o", "out.json", "--post-url", "https://x", "in.csv"])` raises `SystemExit` (argparse mutex-group rejection). Verifies SC#3 mutex behavior end-to-end at the argparse layer.
- **D-07-16 (No new test dependencies):** All new tests use stdlib `unittest`/pytest already in the test suite. No `mock_server` / `responses` / `requests-mock` introduced — `_HttpPostSink` doesn't touch the network in Phase 7, so no HTTP mocking is needed.

### Carry-forward (locked, not re-asked)

- **D-05 (locked tail-key order):** `result-logic`, `score-category`, `score-value`, `answer-tags`, `time-to-complete`, `product-recommendation` order preserved in every emitted row. `_StdoutSink`/`_FileSink` reuse the existing `build_row` output; sink layer never reorders.
- **D-06-2x (validation surfaces locked):** All Phase 6 stderr templates and exit codes preserved. `_run_schema_validation` body untouched.
- **D-11 (10-section README lock):** README updates land inside existing sections only. Likely additions: `--post-url` row in `## CLI reference` table (Default: `—`; Description: `Stub in v1.2 Phase 7; HTTP POST delivery lands in Phase 9`). NO new H2.
- **D-13 (stdlib-only at runtime):** No new runtime imports. `typing.Protocol` is stdlib. `_HttpPostSink` does not import `urllib.request` / `ssl` in Phase 7 (those land in Phase 9).
- **T-PII-01 (PII-safe stderr):** Sink layer never logs row content. `_HttpPostSink.write`'s `NotImplementedError` message is categorical only.
- **D-03 (empty cells emit `""`):** Sink layer is row-agnostic; D-03 is a `build_row` concern, untouched.
- **D-15 (already retired in Phase 5):** Phase 7 does not revive any positional-trailer logic.
- **Phase 5 missing-trio WARNING:** `_RowStream` continues to emit per-missing-name `logging.warning` (D-05-08 template) before the row-yield loop — same call site as today's lines 459-464.

### Claude's Discretion

- Whether `iter_rows()` is exposed as a top-level function returning a `_RowStream`, or as a class method `_RowStream.iter_rows()`, or as `_RowStream.__iter__` directly accessed via `iter(stream)` — planner's call. The CONTRACT is: a generator-shaped object yielding one built dict per CSV row, with an `exit_code` attribute reachable from `convert()`.
- The `_select_sink(args) -> _Sink` factory's exact signature and location (top-level function vs nested in `main` vs class method) — planner's call.
- Whether sinks live in the same `quizify_csv_ingest.py` module or move to a new `quizify_csv_ingest/_sinks.py` — planner's call, BUT prefer single-file (D-06-04 carry-forward: "single-module py-modules, no package directory restructure"). Phase 9 may revisit if the sink layer grows.
- The empty-CSV detection mechanism inside `_RowStream` (sentinel exception vs early-set `exit_code` and exhausted iterator) — planner's call as long as the resulting stderr message and exit code match today's `logging.error("CSV is empty")` + `return 1`.
- Test file naming and placement (extend `tests/test_convert.py` vs new `tests/test_sinks.py` + `tests/test_refactor_byte_identity.py`) — planner's call. Reuse `conftest.py` fixtures.
- Whether `_HttpPostSink.__init__` stores `self.url` or `self._url` (private convention) — planner's call. The attribute name is not part of the public surface.
- The exact `NotImplementedError` message text in `_HttpPostSink.write()` — planner's call as long as it references Phase 9 / deferred / not-yet-implemented in a categorical way (no PII, no row data).
- Whether to surface `iter_rows()` / `_RowStream` / `_Sink` Protocol in the public API (e.g., docstring + `__all__`) or keep them underscore-prefixed internal — planner's call. Preference: keep all underscore-prefixed except `iter_rows` (which ROADMAP SC#2 names explicitly).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 7: Refactor Scaffolding (no-op)" — phase goal, dependencies, four success criteria. SC#1 (byte-identical default output), SC#2 (`iter_rows()` yields one dict per row, no list accumulation in generator path), SC#3 (`_HttpPostSink` stub + argparse mutex group), SC#4 (94 v1.1 tests + D-11 drift test green, no new runtime deps).
- `.planning/REQUIREMENTS.md` §"Refactor & Regression Lock (REFACTOR)" — REFACTOR-01 text.

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (tail-key order), D-11 (10-section README lock), D-13 (stdlib-only at runtime).
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 (PII-safe stderr); D-03 (empty cells emit `""` verbatim).

### v1.2 milestone context
- `.planning/research/SUMMARY.md`, `.planning/research/STACK.md`, `.planning/research/FEATURES.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md` — v1.2 research outputs (sink abstraction, NDJSON, HTTP POST). Phase 7 implements the scaffolding referenced by Phases 8 and 9.

### Phase 6 carry-forwards (most recent prior phase)
- `.planning/milestones/v1.1-phases/06-json-schema-validation/06-CONTEXT.md` — D-06-16 (post-build pre-write validation timing), D-06-17 (lazy import), D-06-18 (compile once), D-06-19/20/21 (locked stderr templates and exit code), D-06-22 (validate × missing-trio independence), D-06-04 (single-module shape preserved).

### Pitfalls and known landmines
- `.planning/research/PITFALLS.md` §"Pitfall 16" — keep new tests at unit level, not subprocess-driven.
- `.planning/research/PITFALLS.md` §"Pitfall 17" — never forward `JsonSchemaValueException.message` raw (carry-forward; `_run_schema_validation` body untouched).
- `.planning/research/PITFALLS.md` §"Pitfall 18" — keep `import fastjsonschema` lazy (carry-forward; preserved by D-07-09).

### Files being edited or created
- **EDITED:** `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — add `_Sink` Protocol, `_StdoutSink`, `_FileSink`, `_HttpPostSink` stub, `iter_rows()`/`_RowStream` extraction; refactor `convert()` body; update `main()` argparse mutex group with `--post-url`; thread `args.post_url` through to `convert()` (or to a `_select_sink` factory).
- **EDITED:** `quizify-csv-to-json-webhook/README.md` — add `--post-url` row to existing `## CLI reference` table only; NO new sections (D-11).
- **NEW or EDITED:** test file(s) for byte-identical regression (TRAIL-03 parallel), `_HttpPostSink` stub behavior, argparse mutex rejection — placement is planner's call (D-07-13 / D-07-14 / D-07-15).
- **NOT EDITED:** `_run_schema_validation`, `_format_validation_error`, `build_row`, `classify_headers`, `dry_run`, `configure_logging` — function bodies unchanged. Only `convert()` and `main()` are restructured.

### Sample / verification fixture
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row sample, default-flag invocation must produce byte-identical golden output.
- v1.1 golden-fixture file referenced by TRAIL-03 — verify exact path during planning (likely `tests/fixtures/...` or inline string in `tests/test_*.py`).

### Sibling carry-forward
- `.planning/milestones/v1.1-phases/05-python-trailer-hardening/05-CONTEXT.md` — D-05-08 missing-trio WARNING template; `_RowStream` preserves the call site verbatim.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `convert()` at `quizify-csv-to-json-webhook/quizify_csv_ingest.py:413-507` — the function being refactored. Key sub-blocks:
  - Lines 433-453: file open + header read + `classify_headers` + `LayoutError` catch → moves into `_RowStream.__iter__` (with exception re-raise to `convert()` for the exit-code-1 path).
  - Lines 459-464: missing-trio `logging.warning` loop → moves into `_RowStream.__iter__`, before the per-row yield loop.
  - Lines 466-469: `dynamic_headers_decoded`, `expected_len`, `p_len`, `t_len` precomputation → inside `_RowStream.__iter__` setup.
  - Lines 471-493: per-row loop with length-mismatch warning + `decode_cell` + `build_row` → becomes the `yield` body inside `_RowStream.__iter__`.
  - Lines 495-498: post-build validation gate → STAYS in `convert()` as today, with `results = list(stream)` providing the input list.
  - Lines 500-506: stdout vs file write → REPLACED by `with sink: for row in results: sink.write(row)` pattern.
- `_run_schema_validation` at `quizify-csv-to-json-webhook/quizify_csv_ingest.py:364-410` — body untouched (D-07-09).
- `build_row` (lines ~250-303), `classify_headers`, `decode_cell`, `_OUTPUT_KEY_BY_CANONICAL`, `SCORING_PLACEHOLDERS`, `CONTACT_PREFIX`, `DEFAULT_TRAILER`, `LayoutError` — all reused as-is by `_RowStream`.
- `argparse` setup at `quizify-csv-to-json-webhook/quizify_csv_ingest.py:512-534` — `-o`/`--output` (line 517) becomes the first leg of the new mutex group; `--post-url` is the new second leg. Other flags untouched.
- `tests/conftest.py` fixtures (Phase 5 `scoring_index_map_default`, etc.) — reusable for sink/iter_rows tests.

### Established Patterns
- **Pure functions returning tuples** — `classify_headers` returns a 5-tuple. `_RowStream` is the first stateful class in this module; planner should keep the class minimal (3 attributes max: `path`, `trailer`, `quiz_title`, plus mutated `exit_code`).
- **First-only / once-only side effects** — schema compile happens once per invocation (carry-forward). Sink `close()` happens once per invocation per sink instance.
- **Lazy / conditional imports** — preserved (D-13). No new conditional imports introduced in Phase 7.
- **`tuple[str, ...]` typing throughout for ordered name collections** — match style; sink type hint uses the new `_Sink` Protocol.
- **Single-file CLI by design** — preserved. Sinks live in `quizify_csv_ingest.py`, NOT a new `_sinks.py` module unless the planner has strong justification.

### Integration Points
- `argparse` setup: `-o`/`--output` and `--post-url` move into `parser.add_mutually_exclusive_group()`. `args.output` and `args.post_url` are read by `convert()` (or a `_select_sink(args)` helper).
- `convert()` signature: gain `post_url: str | None = None` parameter (alongside existing `output: Path | None`) OR accept the args namespace directly. Planner's call — prefer explicit named parameters for testability.
- Sink instantiation point: a `_select_sink(args) -> _Sink` factory (or inline `if/elif/else` chain) inside `convert()` after validation passes and before the write loop.
- Validation point: `_run_schema_validation(results, SCHEMA_PATH)` continues to fire post-`list(stream)`, pre-`with sink:`. Same line-of-execution as today.
- Test integration: byte-identity test reuses the v1.1 golden fixture (file path TBD by planner via grep on TRAIL-03 references).

</code_context>

<specifics>
## Specific Ideas

- Sink Protocol shape (LOCKED VERBATIM):
  ```python
  class _Sink(Protocol):
      def write(self, row: dict) -> None: ...
      def close(self) -> None: ...
  ```
- `_StdoutSink` / `_FileSink` MUST buffer rows internally and call `json.dump(...)` exactly once on `close()` to preserve byte-identical default output (D-05 tail-key order, indent=2, ensure_ascii=False, trailing `\n`).
- `_HttpPostSink.__init__(self, url: str)` stores `self.url = url` with NO validation. `write()` raises `NotImplementedError` referencing Phase 9. `close()` is a no-op.
- Argparse mutex shape (LOCKED VERBATIM):
  ```python
  group = parser.add_mutually_exclusive_group()
  group.add_argument("-o", "--output", type=Path, default=None,
                     help="Write JSON array to PATH (UTF-8). Default: stdout.")
  group.add_argument("--post-url", default=None,
                     help="(Phase 9) HTTP POST delivery target. Stub in Phase 7.")
  ```
- TRAIL-03 parallel test — name-of-art only; planner picks final test function name (e.g., `test_refactor_byte_identical_default_invocation`).
- `iter_rows` symbol name appears verbatim in ROADMAP SC#2 — preserve it as a public-facing identifier (not underscore-prefixed).

</specifics>

<deferred>
## Deferred Ideas

- **NDJSON output (`--ndjson` flag, per-row write, atomic file replace)** — Phase 8 (STREAM-01 through STREAM-04). Sink Protocol shape (D-07-01) is designed to accommodate it without rework.
- **Per-row validation inside the streaming pipeline** — Phase 8 STREAM-01 SC#2 (no final file on validation failure). Will introduce per-row validation as part of NDJSON's actual behavior change.
- **`_ValidatingSink` decorator** — considered, rejected for Phase 7 (timing-change risk). Phase 8 may revive.
- **Atomic file writes (`os.replace(.tmp, target)`)** — Phase 8 STREAM-04. Phase 7 `_FileSink` uses simple direct-open for byte-identical preservation.
- **HTTP POST delivery with HTTPS-only check, header parsing with CRLF rejection, `--timeout` default 30, `--post-url` requires `--validate` gate, redirect handling, retry behavior** — Phase 9 (AUTO-01 through AUTO-06). All explicitly excluded from Phase 7.
- **`--ndjson` × `--post-url` cross-product** — deferred to v1.3+ per REQUIREMENTS Future Requirements list (Make.com webhook content-type is `application/json` of an array, not NDJSON).
- **`$QUIZIFY_WEBHOOK_URL` env var / `--post-url-env` flag** — deferred per REQUIREMENTS Future Requirements list.
- **`--retry N` exponential backoff, `--idempotency-key`** — deferred per REQUIREMENTS Future Requirements list.
- **Restructuring `quizify_csv_ingest.py` into a package directory with `_sinks.py` submodule** — D-06-04 carry-forward; rejected unless a planner identifies a strong reason.
- **`_HttpPostSink.__init__` URL validation in Phase 7** — explicitly rejected (D-07-04). HTTPS-only and other validation is Phase 9.
- **`--post-url` requires `--validate` argparse gate in Phase 7** — explicitly rejected (D-07-12). Phase 9 surface.
- **Make.com hygiene + node:test harness** — Phase 10. Fully independent of Phase 7-9; parallel-safe.

</deferred>

---

*Phase: 07-refactor-scaffolding-no-op*
*Context gathered: 2026-05-05*
