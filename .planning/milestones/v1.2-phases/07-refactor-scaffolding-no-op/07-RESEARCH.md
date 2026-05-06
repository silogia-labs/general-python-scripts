# Phase 7: Refactor Scaffolding (no-op) — Research

**Researched:** 2026-05-05
**Domain:** Internal restructuring of a single-file stdlib Python CLI — extract `iter_rows()` generator and three sink classes (`_StdoutSink`, `_FileSink`, `_HttpPostSink` stub) without changing default-flag output.
**Confidence:** HIGH (decisions locked in 07-CONTEXT.md; all questions resolved against in-repo source-of-truth).

## Summary

Phase 7 is a pure refactor with byte-identical default behavior. CONTEXT.md (D-07-01..D-07-16) locks the sink Protocol shape, the `_RowStream` wrapper shape, validation placement, the `_HttpPostSink` stub depth, the argparse mutex group, and the test strategy. This research's job is to **pin those locked decisions to exact code locations** and **resolve the planner's discretionary calls** (empty-CSV mechanism, sink factory placement, test file naming, exception flow under the wrapper).

**Primary recommendation:**
1. Extract a `_RowStream` class owning lines 433-493 of `quizify_csv_ingest.py` (file-open through per-row `build_row` yield), with `exit_code: int` attribute mutated on length mismatches.
2. Expose a thin top-level `iter_rows(path, trailer, quiz_title) -> _RowStream` factory (ROADMAP SC#2 names this symbol).
3. Catch `LayoutError` and an internal sentinel `_EmptyCsvError` at the `list(stream)` call site in `convert()`; keep validation (lines 495-498) and emit code (lines 500-506) structurally unchanged but route output through `_select_sink(args)`.
4. Add the parallel byte-identical test as a **second function in `tests/test_default_order_regression.py`** (not a new file) — it's the same fixture, same script, same oracle.
5. Add `convert(..., post_url: str | None = None)` as a trailing kwarg — all four existing test call sites pass `output=` by keyword, so the new kwarg is safely appendable.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSV → row dicts | Core / pure-functional | — | `iter_rows()`/`_RowStream` owns parse + decode + build; no I/O beyond file read |
| Output dispatch | Sink layer (new) | — | `_StdoutSink`/`_FileSink`/`_HttpPostSink` adapter — Protocol structural typing |
| Validation gate | Core / `convert()` | — | Stays in caller (D-07-08), pre-sink, post-`list()` materialization |
| CLI surface | argparse in `main()` | — | Mutex group is a pure argparse construct; sinks consume `args.output` / `args.post_url` |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFACTOR-01 | `convert()` refactored to use `iter_rows()` generator + sink abstraction (`_StdoutSink` / `_FileSink` / `_HttpPostSink`); default-flag invocation produces byte-identical output to v1.1 (golden-fixture regression test parallel to TRAIL-03). | Sink Protocol + `_RowStream` design pinned to lines 413-507; byte-identical regression test placed alongside TRAIL-03 (tests/test_default_order_regression.py:26-52) reusing the existing v1.0 golden fixture (which is also the v1.1 oracle since v1.1 preserved byte identity per TRAIL-03). |
</phase_requirements>

<user_constraints>
## User Constraints (from 07-CONTEXT.md)

### Locked Decisions (D-07-01 … D-07-16)
- **D-07-01**: Sink interface = `typing.Protocol` with `write(row: dict) -> None` and `close() -> None`. `_StdoutSink`/`_FileSink` buffer internally and call `json.dump` once on `close()` to preserve byte-identical output. `typing.Protocol` is stdlib (D-13 preserved).
- **D-07-02**: `_StdoutSink()` (no args); `close()` emits `json.dump(self._rows, sys.stdout, indent=2, ensure_ascii=False)` + `sys.stdout.write("\n")`. Mirrors lines 500-502 verbatim.
- **D-07-03**: `_FileSink(output: Path)`; `close()` opens with `output.open("w", encoding="utf-8")`, same `json.dump` args, trailing `"\n"`. Mirrors lines 503-506. Atomic `os.replace` deferred to Phase 8 STREAM-04.
- **D-07-04**: `_HttpPostSink.__init__(self, url: str)` stores url silently — NO validation in Phase 7. `write()` raises `NotImplementedError("HTTP POST delivery lands in Phase 9")`. `close()` is a no-op.
- **D-07-05**: `_RowStream` wrapper owns file open + `classify_headers` + missing-trio warnings + per-row build + mutable `exit_code`. `__iter__` yields one dict per row.
- **D-07-06**: `iter_rows()` is the public symbol (ROADMAP SC#2); `_RowStream` is the implementation. Factory shape preferred (carries `exit_code` cleanly).
- **D-07-07**: `LayoutError` + empty-CSV exception handling moves to caller (`convert()`).
- **D-07-08**: Schema validation stays batch in `convert()`, post-`list(stream)`, pre-sink-open. NO per-row validation in Phase 7. NO `_ValidatingSink`.
- **D-07-09**: `_run_schema_validation` body (lines 364-410) UNCHANGED.
- **D-07-10**: `parser.add_mutually_exclusive_group()` containing `-o`/`--output` and `--post-url`. NO `--ndjson` in Phase 7.
- **D-07-11**: `args.output` field name preserved; new `args.post_url`. `_select_sink(args)` factory selects.
- **D-07-12**: NO `--post-url requires --validate` gate in Phase 7 (Phase 9 surface).
- **D-07-13**: Parallel TRAIL-03 byte-identical regression test is the gate. Pitfall 16 → unit-level via `capsys` preferred over subprocess.
- **D-07-14/15/16**: `_HttpPostSink` stub test, mutex test, no new test deps.

### Claude's Discretion (resolved below)
- `iter_rows()` shape → factory function returning `_RowStream` instance (Q4).
- `_select_sink(args) -> _Sink` location → top-level helper (Q7).
- Sinks live in single-file `quizify_csv_ingest.py` (D-06-04 carry-forward; CONTEXT explicit preference).
- Empty-CSV mechanism → internal `_EmptyCsvError` sentinel raised by `_RowStream.__iter__` (Q5).
- Test placement → extend `tests/test_default_order_regression.py` for byte-identity; new `tests/test_sink_layer.py` for stub + mutex (Q10).
- `_HttpPostSink` attribute → `self.url` (public — phase 9 will read it).
- `NotImplementedError` text → `"HTTP POST delivery lands in Phase 9"` (CONTEXT specifies Phase 9 reference).

### Deferred Ideas (OUT OF SCOPE — do not implement)
- NDJSON / `--ndjson` flag (Phase 8).
- Per-row validation, `_ValidatingSink` decorator (Phase 8).
- Atomic `os.replace` for `_FileSink` (Phase 8 STREAM-04).
- HTTPS-only check, `--header`, `--timeout`, redirect handling, retry, `--post-url` requires `--validate` gate (Phase 9).
- `$QUIZIFY_WEBHOOK_URL` / `--post-url-env` (v1.3+).
- Restructure into package directory with `_sinks.py` (rejected — D-06-04).
</user_constraints>

## Project Constraints (from CLAUDE.md / PROJECT.md)

- **D-13** stdlib-only at runtime — `typing.Protocol` is stdlib (PEP 544, Python 3.8+); no new runtime imports in Phase 7. `_HttpPostSink` does NOT import `urllib.request` or `ssl` until Phase 9.
- **D-05** locked top-level key order — sinks NEVER reorder; they receive built rows from `build_row` and pass through.
- **D-11** README ten-section lock — `tests/test_readme_help_alignment.py:18-29` lists the 10 required H2s; `--post-url` MUST appear as a substring of README.md (line 53 in test asserts every long flag from `--help` is in README) — add it inside the existing `## CLI reference` table (README.md:41-49).
- **T-PII-01** PII-safe stderr — `_HttpPostSink.write`'s `NotImplementedError` is categorical only (no row content).
- **D-03** empty cells emit `""` — sink-agnostic; unchanged.
- **TRAIL-03** byte-identical default output — golden lives at `tests/fixtures/v1.0_default_order_output.json` (referenced from `test_default_order_regression.py:23`).

## Per-Decision Recommendation (Research Questions resolved)

### Q1. Byte-identical regression test — where it lives
**File:** `quizify-csv-to-json-webhook/tests/test_default_order_regression.py`
**Existing function:** `test_default_order_byte_identical_to_v1_0_baseline` (line 26). It uses `subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE)])` and compares `json.loads(result.stdout)` against `tests/fixtures/v1.0_default_order_output.json`.
**Phase 7 add:** Append a new function in the same file. Per D-07-13 + Pitfall 16 carry-forward, **use unit-level `capsys` instead of subprocess** for the new test:
```python
def test_phase7_refactor_byte_identical_to_v1_0_baseline(capsys, tmp_path):
    from quizify_csv_ingest import convert
    rc = convert(FIXTURE, None, None, "")  # default args, stdout sink
    captured = capsys.readouterr()
    assert rc == 0
    assert json.loads(captured.out) == json.loads(GOLDEN.read_text(encoding="utf-8"))
```
The existing TRAIL-03 subprocess test stays as-is (it's the v1.0/v1.1 oracle and remains green; double coverage at unit + subprocess level is desirable for a refactor phase). [VERIFIED: tests/test_default_order_regression.py:1-53]

### Q2. Test count baseline
**Confirmed: 94 tests collected** via `python -m pytest --collect-only -q`. [VERIFIED: pytest run]
Phase 7 adds 3 new tests → final count ≥ 97 (D-07-14, D-07-15 each = 1; D-07-13 unit-level = 1). SC#4's "all 94 v1.1 tests still pass" is preserved (no test removals).

### Q3. `typing.Protocol` import on Python 3.9
**Confirmed safe.** `pyproject.toml` declares `requires-python = ">=3.9"`. [VERIFIED: pyproject.toml:5] `typing.Protocol` ships in `typing` since Python 3.8 (PEP 544, [CITED: docs.python.org/3/library/typing.html#typing.Protocol]). No `runtime_checkable` decorator needed — Phase 7 sinks are statically-checked structurally; no `isinstance(s, _Sink)` call planned. D-13 preserved.

### Q4. `_RowStream` shape — Python idiom check
**Locked design works.** A class with `__iter__` returning a generator (via `yield` inside `__iter__`) is idiomatic Python. Two subtleties:
- **File handle lifetime:** Use `with self.path.open(...) as fh:` inside `__iter__`. The `with` block remains open for the lifetime of the generator (until exhaustion, GC, or `.close()` on the generator). For `convert()`'s `list(stream)` materialization the file is fully drained before any sink opens — no leak. [VERIFIED: Python contextmanager semantics + generator close protocol]
- **`exit_code` mutation:** Set `self.exit_code = 0` in `__init__`, mutate to `|= 1` inside `__iter__` on length mismatch. Caller reads `stream.exit_code` AFTER `list(stream)` returns. Works because `__iter__` yields BEFORE the mutation surfaces in iteration; the final value is whatever the loop body last wrote.

**Recommended class skeleton:**
```python
class _RowStream:
    def __init__(self, path: Path, trailer: tuple[str, ...] | None, quiz_title: str) -> None:
        self.path = path
        self.trailer = trailer
        self.quiz_title = quiz_title
        self.exit_code = 0
    def __iter__(self) -> Iterator[dict]:
        # body: lines 436-493 of today's convert()
        ...

def iter_rows(path: Path, trailer: tuple[str, ...] | None, quiz_title: str) -> _RowStream:
    return _RowStream(path, trailer, quiz_title)
```

### Q5. LayoutError + empty-CSV under the wrapper
**Recommendation:** Define a module-private sentinel `class _EmptyCsvError(Exception): pass`. Inside `_RowStream.__iter__`:
```python
try:
    header = next(reader)
except StopIteration:
    raise _EmptyCsvError() from None
# classify_headers raises LayoutError; let it propagate
```
In `convert()`, wrap the materialization:
```python
stream = iter_rows(path, trailer, quiz_title)
try:
    results = list(stream)
except _EmptyCsvError:
    logging.error("CSV is empty")
    return 1
except LayoutError as err:
    logging.error("%s", err)
    return 1
exit_code = stream.exit_code
```
This **preserves the exact stderr messages and exit codes from lines 444-446 and 451-453 verbatim**. The pre-existing `path.open(...) OSError` catch (lines 436-439) moves into a wrapper around the `iter()` call OR stays in `convert()` by performing the open inside `_RowStream.__iter__` and catching `OSError` at the `list()` site — recommend the latter (logic adjacent to its trigger). [VERIFIED: lines 436-453 of quizify_csv_ingest.py]

### Q6. `_run_schema_validation` integration point
**Unchanged in Phase 7.** Inserts between `results = list(stream)` and `_select_sink(args)`. Exact replacement for today's lines 495-498:
```python
if validate:
    rc = _run_schema_validation(results, SCHEMA_PATH)
    if rc != 0:
        return rc
```
[VERIFIED: lines 495-498]. Body of `_run_schema_validation` (lines 364-410) untouched per D-07-09.

### Q7. `_select_sink(args)` factory
**Recommendation: top-level module function** for symmetry with `_run_schema_validation`, `_resolve_quiz_title`, `_format_validation_error` (all top-level underscore-prefixed helpers in this module). Signature:
```python
def _select_sink(output: Path | None, post_url: str | None) -> _Sink:
    if post_url is not None:
        return _HttpPostSink(post_url)
    if output is not None:
        return _FileSink(output)
    return _StdoutSink()
```
Take primitives, not the argparse namespace — keeps the helper testable without constructing a fake `Namespace`. Argparse mutex guarantees `post_url` and `output` are not both set.

### Q8. Argparse mutex syntax + behavior
**Locked verbatim in 07-CONTEXT.md `<specifics>`.** Replaces line 517:
```python
group = parser.add_mutually_exclusive_group()
group.add_argument("-o", "--output", type=Path, default=None,
                   help="Write JSON array to PATH (UTF-8). Default: stdout.")
group.add_argument("--post-url", default=None,
                   help="(Phase 9) HTTP POST delivery target. Stub in Phase 7.")
```
**Behavior on `-o X --post-url Y`:** argparse calls `parser.error(...)` which prints to stderr `argument --post-url: not allowed with argument -o/--output` and `SystemExit(2)`. [CITED: docs.python.org/3/library/argparse.html#mutual-exclusion]
**`--emit-json` does NOT join the group** (Q13) — it's a self-documenting no-op flag (lines 519-523), not an output target. Confirmed by re-reading its help text ("default behavior; accepted for self-documenting scripts"). All other flags (`--dry-run`, `-v`, `--trailer-columns`, `--validate`, `--quiz-title`) stay at parser level, unchanged.

### Q9. README updates + drift test
**README.md edit:** Add ONE row to the existing CLI reference table (lines 41-49 of README.md):
```markdown
| `--post-url URL` | `—` | (Phase 9) HTTP POST delivery target. Stub in v1.2 Phase 7; raises `NotImplementedError` if invoked. Mutually exclusive with `-o`. | — |
```
**Drift test guarantees:** `tests/test_readme_help_alignment.py:53-63` extracts `--[a-z][a-z0-9-]+` from `--help` output and asserts each appears as a substring in README.md. So `--post-url` (3 chars + 8 lowercase) MUST appear somewhere in README.md — the table row above satisfies this. [VERIFIED: tests/test_readme_help_alignment.py:53-63]
**Section count guarantee:** D-11 ten-section lock — only adding a row to existing `## CLI reference`; NO new H2. [VERIFIED: tests/test_readme_help_alignment.py:18-29]
**Update Limitations section** (README.md:148-149): The line "HTTP POST / webhook-send mode and JSON Schema validation are deferred to v2." needs softening — JSON Schema validation already shipped in v1.1, and HTTP POST is now a v1.2 Phase 9 deliverable with a Phase 7 stub. Recommend: `"HTTP POST / webhook-send mode is deferred to v1.2 Phase 9 (a CLI stub at --post-url is present in Phase 7 and raises NotImplementedError)."` — keeps the H2 but updates content.

### Q10. Test naming and placement
**Final recommendation:**
| Test | File | Function name |
|------|------|---------------|
| (a) byte-identical default | `tests/test_default_order_regression.py` (extend) | `test_phase7_refactor_byte_identical_to_v1_0_baseline` |
| (b) `_HttpPostSink` stub | `tests/test_sink_layer.py` (new) | `test_http_post_sink_stub_raises_on_write`, `test_http_post_sink_construct_accepts_url_silently`, `test_http_post_sink_close_is_noop` |
| (c) argparse mutex | `tests/test_sink_layer.py` (new) | `test_argparse_output_post_url_mutex_rejection`, `test_argparse_post_url_alone_parses` |

Add a 4th test class `TestSelectSink` in the same new file: assert `_select_sink(None, None)` is `_StdoutSink`, `_select_sink(Path("x"), None)` is `_FileSink`, `_select_sink(None, "https://x")` is `_HttpPostSink`. Reuse `conftest.py`'s `sample_csv_path` for byte-identity. [VERIFIED: tests/conftest.py:14-16]

### Q11. Pitfalls forward (from PITFALLS.md, Phase 7 lens)
| Pitfall | Phase 7 relevance | Mitigation |
|---------|-------------------|------------|
| #6 NDJSON trailing-newline | Not Phase 7 (Phase 8). Today's `json.dump + write("\n")` pattern in `_StdoutSink`/`_FileSink` is byte-identical preserve. | Keep the explicit `out.write("\n")` after `json.dump` — it's the single trailing newline TRAIL-03 expects. |
| #7 partial-file atomicity | Not Phase 7 (Phase 8 STREAM-04). `_FileSink` uses simple direct-open. | None — explicitly deferred (D-07-03). |
| #16 (carry-forward, unit-level tests) | Direct: byte-identity test should be `capsys`-driven, not `subprocess`. | Per Q1, new test uses `capsys`; existing TRAIL-03 subprocess test stays for safety. |
| #17 `JsonSchemaValueException.message` | Carry-forward only — `_run_schema_validation` body untouched (D-07-09). | Verified by Q6. |
| #18 lazy `import fastjsonschema` | Carry-forward only — `_run_schema_validation` body untouched. | Verified by Q6. |
| **NEW: generator-state surprise** | `_RowStream.__iter__` containing `yield` makes `__iter__` itself a generator function. Calling `iter(stream)` twice creates two independent generators — but `exit_code` is on the instance, so re-iterating would re-run the file open and append exit_code mutations. **Mitigation:** Document `_RowStream` as single-iteration-only OR add `self._consumed = False` guard. Recommend the simpler path: comment `# single-iteration; re-iterating reopens the file and resets state`. Phase 8 may add a guard if needed. | Documented constraint. |
| **NEW: `_HttpPostSink` import-time inertness** | `_HttpPostSink` class definition must NOT import `urllib.request` or `ssl` (D-13 + D-07-04). | Verify via grep: `import urllib` / `import ssl` should not appear in the module after Phase 7. |

### Q12. Phase 8/9 forward-compatibility
| Future need | Phase 7 design enables it? | Notes |
|-------------|-----------------------------|-------|
| Phase 8 STREAM-01 NDJSON per-row write | YES | Add `_NdjsonFileSink(_FileSink)` overriding `write()` to flush per row; `close()` no-ops the buffered dump. Sink Protocol unchanged. |
| Phase 8 STREAM-04 atomic `os.replace` | YES | `_FileSink.close()` becomes `tmp.write → os.replace(tmp, target)`; Phase 7 callers see no API change. |
| Phase 8 per-row validation against `schema["items"]` | YES | Per-row validation can wrap sink at `_select_sink` factory layer (`_ValidatingSink` decorator) OR fold into `_RowStream.__iter__` post-`build_row`. Phase 7's batch-validation in `convert()` doesn't block either path. |
| Phase 9 `--post-url` requires `--validate` | YES | Add `if args.post_url and not args.validate: parser.error(...)` after `parser.parse_args()` — purely additive. |
| Phase 9 HTTPS-only / headers / timeout / redirect / retry | YES | `_HttpPostSink.__init__` gains parameters (url, headers, timeout); `_HttpPostSink.write()` body lands. Phase 7 callers don't see the new init params because `_select_sink` constructs from `args`. |
| Phase 9 PII-safe error templates (D-06-2x lock) | YES | Errors arise inside `_HttpPostSink.write()`; the Protocol surface doesn't expose them — caller treats sink errors as exit non-zero. |
| **Latent conflict?** | NONE FOUND | The Protocol-with-buffer-and-close shape gracefully accommodates both batch (array) and stream (NDJSON) modes. |

### Q13. `--emit-json` flag
**Stays at parser level, NOT in mutex group.** [VERIFIED: lines 519-523 + Q8 above] It's a no-op self-documenting flag; semantically orthogonal to output destination. No conflict with `--post-url`.

### Q14. Module-level constants
**`SCHEMA_PATH` is at line 124** — `Path(__file__).resolve().parent / "docs" / "webhook-schema.json"`. [VERIFIED: line 124] Untouched by the refactor; `_run_schema_validation` continues to receive it from `convert()`.

### Q15. Backwards compatibility — `convert()` signature
**External callers (tests):**
- `tests/test_schema_validation.py:55,73` — `convert(FIXTURE, None, out, "Autoevaluacion")` — 4 positional args.
- `tests/test_row_builder.py:461,491` — `convert(csv_path, custom_trailer, output=tmp_path/"out.json", quiz_title="")` — 2 positional + 2 keyword.
- All test imports are `from quizify_csv_ingest import convert`.

**Recommended new signature** (additive, backwards-compatible):
```python
def convert(
    path: Path,
    trailer: tuple[str, ...] | None,
    output: Path | None,
    quiz_title: str,
    validate: bool = False,
    post_url: str | None = None,   # NEW — keyword-defaultable, after validate
) -> int:
```
Adding `post_url=None` as a trailing kwarg with a default does NOT break any of the 4 existing call sites. [VERIFIED: grep above]
**Threading from `main()`:** `return convert(args.csv_path, trailer_override, args.output, quiz_title, validate=args.validate, post_url=args.post_url)` — replace line 551.

## Test Inventory

### Existing tests (94 total, all must stay green)
| File | Phase 7 risk | Why |
|------|--------------|-----|
| `test_default_order_regression.py` (1 test, subprocess) | LOW — TRAIL-03 oracle | Default invocation must remain byte-identical; this is THE primary gate. |
| `test_readme_help_alignment.py` (2 tests) | MEDIUM — must add `--post-url` to README CLI table | Drift test extracts long flags from `--help` and asserts each is in README. |
| `test_schema_validation.py` (~22 tests, calls `convert()`) | LOW — `convert()` signature additive | All call sites unaffected by new trailing kwarg. |
| `test_row_builder.py` (calls `convert()` for end-to-end) | LOW — same reasoning | |
| `test_layout.py`, `test_logging_pii.py`, `test_quiz_title_precedence.py`, `test_cli_emit.py`, `test_golden_structure.py`, `test_structural_invariants.py` | LOW | None call argparse directly; sinks/iter_rows are internal. |

### New tests (Phase 7 — 3+ added; final ≥ 97)
| Test | File | Coverage |
|------|------|---------|
| `test_phase7_refactor_byte_identical_to_v1_0_baseline` | `tests/test_default_order_regression.py` (extend) | SC#1 — `convert()` via `capsys` byte-identical to golden |
| `test_http_post_sink_stub_raises_on_write` | `tests/test_sink_layer.py` (new) | SC#3 — `_HttpPostSink({}).write({})` raises `NotImplementedError` mentioning Phase 9 |
| `test_http_post_sink_construct_silently` | `tests/test_sink_layer.py` | D-07-04 — no validation on construction |
| `test_http_post_sink_close_is_noop` | `tests/test_sink_layer.py` | D-07-04 — close() returns None, no exceptions |
| `test_argparse_output_post_url_mutex_rejection` | `tests/test_sink_layer.py` | SC#3 — `parse_args(["-o", "x", "--post-url", "https://y", "in.csv"])` → `SystemExit` |
| `test_argparse_post_url_alone_parses` | `tests/test_sink_layer.py` | D-07-10 — `--post-url` alone parses to `args.post_url == "https://y"` |
| `test_select_sink_factory_dispatch` | `tests/test_sink_layer.py` | D-07-11 — three branches return correct sink type |

### Wave 0 Gaps
- [ ] Create `tests/test_sink_layer.py` (new file).
- [ ] No fixture-creation needed — reuse `tests/conftest.py:sample_csv_path` and `tests/fixtures/v1.0_default_order_output.json`.
- [ ] No new framework or test-dep installs (D-07-16 — stdlib pytest only).

## Sampling Rate
- **Per task commit:** `cd quizify-csv-to-json-webhook && pytest -q tests/test_sink_layer.py tests/test_default_order_regression.py`
- **Per wave merge:** `cd quizify-csv-to-json-webhook && pytest -q`
- **Phase gate:** Full suite green (≥97 tests, was 94) before `/gsd-verify-work`.

## Pitfalls Surfaced (Phase 7 specific, beyond the carry-forward list)

1. **Generator re-iteration:** `_RowStream.__iter__` is itself a generator function. `iter(stream)` twice = two file reopens. Mitigate via single-line docstring constraint. (Q11 detail.)
2. **`exit_code` read order:** Caller MUST read `stream.exit_code` AFTER `list(stream)` returns; reading before iteration gives the initial 0. Document inline in `convert()`.
3. **`_HttpPostSink` accidental import drag:** Forbid `import urllib.request` / `import ssl` in `quizify_csv_ingest.py` until Phase 9. Add CI-style grep gate as a Phase 7 verification step.
4. **README drift detection:** The drift test asserts substring containment of EVERY long flag, including `--post-url`. Forgetting the README row breaks the test. Add as an explicit task.
5. **`json.dump` arg drift inside sinks:** Both `_StdoutSink` and `_FileSink` MUST call `json.dump(rows, fh, indent=2, ensure_ascii=False)` followed by an explicit `"\n"`. Diverging args → byte-identity broken. Lock these args verbatim from lines 501 and 505.
6. **Argparse help-text cell drift in mutex group:** Argparse renders mutex groups slightly differently in `--help` output; the `-o, --output PATH` string format may shift. Run `python quizify_csv_ingest.py --help` after the refactor and verify the drift test still passes.

## Phase 8/9 Forward-Compatibility Check

✅ Phase 8 STREAM-01..04 implementable without Phase 7 rework. `_NdjsonFileSink` subclasses `_FileSink`, overrides `write()` to flush per row + drops batch buffer; atomic `os.replace` adds in `close()`. Mutex group gains `--ndjson` as a third member.
✅ Phase 9 AUTO-01..06 implementable. `_HttpPostSink.__init__` gains url/headers/timeout params; `write()` body lands. `--post-url requires --validate` is a 1-line `parser.error` add. HTTPS-only / CRLF rejection are argparse-level type validators.
⚠️ One latent concern: Phase 8 STREAM-03 says `--ndjson + --validate` validates each row against `schema["items"]`. The Phase 7 batch validation lives in `convert()` and validates the full array. Phase 8 will need to either (a) refactor `_run_schema_validation` to handle both modes, or (b) introduce a parallel `_validate_one(row, compiled_validator)` helper. **No Phase 7 rework required** — Phase 7's choice (D-07-08) explicitly leaves this to Phase 8's design surface.

## Open Questions

1. **`_RowStream.__iter__` file-open exception placement.** Today's `path.open(...)` `OSError` (lines 436-439) catches a missing/unreadable CSV. Under the wrapper, this surfaces on `next()` of `iter(stream)` (i.e., the first iteration). Q5 recommends catching at the `list(stream)` site in `convert()`. Trivially solvable but worth flagging to the planner — pick one mechanism and stick with it.
   - **Recommendation:** Catch `(OSError, _EmptyCsvError, LayoutError)` together at the `list(stream)` call site for stylistic consistency.

2. **Does `_select_sink` belong in `convert()` or `main()`?** CONTEXT marks this Claude's discretion. Recommendation: in `convert()` (so internal callers like `tests/test_schema_validation.py` get sink-routing through the same code path). `main()` only translates argparse → `convert()` kwargs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | core CLI | ✓ | (project floor 3.9) | — |
| pytest | tests | ✓ (existing test run worked) | — | — |
| `fastjsonschema` (optional `[validate]`) | `--validate` only — not Phase 7 | per dev install | — | Phase 7 byte-identity test does NOT invoke `--validate` |

No external services / network deps. No new tools introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in repo, exact version per `requirements-dev.txt`) |
| Config file | `pyproject.toml` (no `[tool.pytest.ini_options]` section observed); pytest auto-discovers `tests/` |
| Quick run command | `cd quizify-csv-to-json-webhook && pytest -q tests/test_sink_layer.py tests/test_default_order_regression.py` |
| Full suite command | `cd quizify-csv-to-json-webhook && pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REFACTOR-01 (SC#1) | Default invocation byte-identical | unit (capsys) | `pytest tests/test_default_order_regression.py::test_phase7_refactor_byte_identical_to_v1_0_baseline -x` | ❌ Wave 0 (extend file) |
| REFACTOR-01 (SC#2) | `iter_rows()` yields one dict per row | unit | `pytest tests/test_sink_layer.py::test_iter_rows_is_generator_no_accumulation -x` | ❌ Wave 0 |
| REFACTOR-01 (SC#3a) | `_HttpPostSink.write` raises | unit | `pytest tests/test_sink_layer.py::test_http_post_sink_stub_raises_on_write -x` | ❌ Wave 0 |
| REFACTOR-01 (SC#3b) | argparse mutex rejects both | unit | `pytest tests/test_sink_layer.py::test_argparse_output_post_url_mutex_rejection -x` | ❌ Wave 0 |
| REFACTOR-01 (SC#4) | 94 v1.1 tests still pass + D-11 drift green | full suite | `pytest -q` | ✅ |
| REFACTOR-01 (SC#4) | No new runtime deps (D-13) | grep gate | `! grep -E '^(import|from) (urllib|ssl|requests)' quizify_csv_ingest.py` | manual |

### Sampling Rate
- **Per task commit:** quick run command above
- **Per wave merge:** full suite command above
- **Phase gate:** Full suite green + grep gate green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_sink_layer.py` — covers REFACTOR-01 SC#2/SC#3
- [ ] Extend `tests/test_default_order_regression.py` with Phase 7 unit-level twin

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The v1.0 golden fixture at `tests/fixtures/v1.0_default_order_output.json` is also the v1.1 byte-identity oracle (since v1.1 TRAIL-03 preserved it). | Q1 | If v1.1 actually drifted from v1.0 byte-for-byte, Phase 7's parallel test would be checking against the wrong oracle. Mitigation: TRAIL-03 (lines 26-44 of test file) currently passes, which empirically proves the oracle is correct as of v1.1. [VERIFIED: 94 tests pass in collection] |
| A2 | argparse mutex on `-o`/`--post-url` produces the exact `SystemExit(2)` exit code documented in argparse. | Q8 | Trivial verification by running the test; built into argparse. [CITED: docs.python.org/3/library/argparse.html] |
| A3 | Adding `--post-url` to the CLI reference table satisfies the drift test's substring match for the exact flag string `--post-url`. | Q9 | [VERIFIED: regex `--[a-z][a-z0-9-]+` at test_readme_help_alignment.py:55 matches `--post-url`] |

All other Phase 7 claims are `[VERIFIED]` against the in-repo source files cited inline.

## Sources

### Primary (HIGH confidence)
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (full file, 555 lines) — refactor target.
- `quizify-csv-to-json-webhook/tests/test_default_order_regression.py` — TRAIL-03 oracle.
- `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` — D-11 drift contract.
- `quizify-csv-to-json-webhook/tests/conftest.py` — fixture inventory.
- `quizify-csv-to-json-webhook/pyproject.toml` — Python floor + project metadata.
- `quizify-csv-to-json-webhook/README.md` — D-11 ten-section structure.
- `.planning/milestones/v1.2-phases/07-refactor-scaffolding-no-op/07-CONTEXT.md` — locked decisions.
- `.planning/research/PITFALLS.md` — Pitfall 16 carry-forward.
- `.planning/ROADMAP.md` — Phase 7 success criteria.
- `.planning/REQUIREMENTS.md` — REFACTOR-01 text.

### Secondary (MEDIUM)
- [CITED: docs.python.org/3/library/typing.html#typing.Protocol] — Protocol availability since Python 3.8.
- [CITED: docs.python.org/3/library/argparse.html#mutual-exclusion] — `add_mutually_exclusive_group()` exit-code-2 behavior.

## Metadata

**Confidence breakdown:**
- Sink Protocol design: HIGH — locked verbatim in CONTEXT.md `<specifics>`.
- `_RowStream` shape: HIGH — derived from line-pinned existing `convert()` body.
- Test placement: HIGH — empirically verified file inventory and existing fixture reuse.
- Phase 8/9 forward-compat: MEDIUM — based on the locked design in v1.2 research; final implementation may surface adjustments.

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days; stable refactor of single-file CLI).
