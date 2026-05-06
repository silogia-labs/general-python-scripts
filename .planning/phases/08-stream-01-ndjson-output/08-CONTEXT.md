# Phase 8: STREAM-01 NDJSON Output - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--ndjson` opt-in line-delimited JSON output to `quizify-csv-to-json-webhook/quizify_csv_ingest.py`, file-target only, with per-row schema validation when paired with `--validate` and atomic file-write semantics. Default array-mode output remains byte-identical to v1.1 (TRAIL-03 stays green). NDJSON × `--post-url` is rejected at argparse and explicitly deferred to v1.3+. No new Python runtime dependencies (`json.dumps`, `os.replace`, `os.unlink` are stdlib; `fastjsonschema` is the existing `[validate]` extra).

This phase introduces the first per-row validation primitive (`_ValidatingSink`) and the first context-manager sink — both designed to be reusable by Phase 9 (AUTO-01).

</domain>

<decisions>
## Implementation Decisions

### Sink Layer — NDJSON

- **D-08-01 (`_NdjsonFileSink` is a new standalone class — NOT a subclass and NOT a `_FileSink(ndjson=True)` mode flag):** Implements the existing `_Sink` Protocol from Phase 7 (`write(row) + close()`). `_FileSink` and `_StdoutSink` are NOT modified — TRAIL-03 byte-identity is therefore unaffected by code paths in this phase. Three sink classes remain in `quizify_csv_ingest.py` (single-file rule, D-06-04 carry-forward); `_NdjsonFileSink` joins them as the fourth. `_HttpPostSink` stub from Phase 7 is untouched.

- **D-08-02 (`_NdjsonFileSink` is a context manager — `__enter__` / `__exit__` own the .tmp lifecycle):** `__init__(output: Path)` only computes paths (`self._target = output`, `self._tmp = output.with_suffix(output.suffix + '.tmp')`); it does NOT open the file. `__enter__` opens the `.tmp` file with `output.open("w", encoding="utf-8", newline="\n")` (STREAM-02: defeats Windows CRLF translation). `write(row)` does `json.dump(row, fp, ensure_ascii=False)` followed by `fp.write("\n")` — one row, one `\n`, no trailing whitespace, no `\r`. `__exit__(exc_type, ...)`: closes the fp; if `exc_type is None`, calls `os.replace(self._tmp, self._target)`; otherwise best-effort `os.unlink(self._tmp)` and never suppresses (`return False`). `close()` exists for `_Sink` Protocol compliance and is a no-op when CM is used.

- **D-08-03 (All sinks gain trivial `__enter__` / `__exit__`):** `_StdoutSink`, `_FileSink`, and `_HttpPostSink` get `__enter__` returning `self` and `__exit__` that calls `self.close()` on normal exit and skips `close()` (or calls a no-op equivalent) on exception. This lets `convert()` use a uniform `with sink:` loop across all sink modes — NDJSON gets atomic semantics for free, default modes stay byte-identical because `close()` is what they did before. Adding `__enter__/__exit__` to `_StdoutSink`/`_FileSink` is a structural-only change; their `write()`/`close()` bodies are untouched.

- **D-08-04 (`.tmp` naming is `target.with_suffix(target.suffix + '.tmp')`):** For `out.ndjson` the temp is `out.ndjson.tmp`. No PID, no random suffix — single-process utility, simple and predictable. If a stale `.tmp` exists from a prior aborted run, it gets overwritten by the new `__enter__`'s `open("w", ...)`. Documented as a known limitation: concurrent invocations writing to the same target are not supported (matches the existing utility-script posture).

### Validation — Per-Row Injection

- **D-08-05 (`_ValidatingSink` decorator wraps the inner sink — NOT inline in `convert()`, NOT a generator wrapper around `iter_rows()`):** `_ValidatingSink(inner: _Sink, schema_path: Path)` is the new validation primitive. Constructor lazy-imports `fastjsonschema` (D-13 / D-06-17 carry-forward), reads `schema_path`, calls `fastjsonschema.compile(schema['items'])` once (D-06-18 carry-forward; STREAM-03 "compiled once"). `write(row)` validates first, raises a sentinel `_RowValidationError(row_index, json_pointer)` on the first failure, otherwise delegates to `self._inner.write(row)`. `close()` delegates to inner. `__enter__/__exit__` delegate to inner — critical so the wrapped `_NdjsonFileSink`'s .tmp lifecycle is preserved through the wrapper.

- **D-08-06 (Sentinel exception `_RowValidationError` carries row index + JSON Pointer; `convert()` catches it and exits 1):** New module-private exception class. Format on stderr: a categorical line built from row index + the existing `_format_validation_error` PII-safe formatter (D-06-20 / Pitfall 17 carry-forward). NEVER include cell content. Row-index prefixing is planner's discretion (e.g., `row 49: <pointer>` vs `/49<pointer>`) — must be PII-safe and machine-greppable. Exit code 1 (matches D-06-21 carry-forward). Because the exception propagates through `convert()`, it travels through every active `with sink:` block — `_NdjsonFileSink.__exit__` sees `exc_type is not None` and unlinks the `.tmp`, satisfying STREAM-01 SC#2 ("the final output path does not exist").

- **D-08-07 (Per-row validation is opt-in only when `--ndjson` AND `--validate`):** Default array-mode validation timing is unchanged (post-build, pre-write — D-07-08 / D-06-16 carry-forward). The decorator is wired in `_select_sink` (or equivalent) only when both flags are set. `--ndjson` without `--validate` writes every row unvalidated (operator's choice). `--validate` without `--ndjson` continues to use the existing batch `_run_schema_validation` against the full `results` list — body untouched (D-07-09 carry-forward).

- **D-08-08 (`schema['items']` extraction reuses the existing `SCHEMA_PATH` and JSON load):** No new schema artifact, no schema mutation. `_ValidatingSink.__init__` reads the schema once via `json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))` and pulls `schema['items']`. The compiled validator is held on the instance. The existing top-level `_run_schema_validation` is untouched and continues to validate the full array in non-NDJSON mode.

### Atomic Write & SIGINT

- **D-08-09 (SIGINT handling = CPython default + `try/finally` semantics from `__exit__`):** No `signal.signal(...)` handler is installed. SIGINT raises `KeyboardInterrupt`, which propagates through the `with _NdjsonFileSink(...) as sink:` block; `__exit__` sees `exc_type is KeyboardInterrupt`, closes fp, unlinks `.tmp`, and re-raises (returns `False`). Target file is never created. STREAM-04's "SIGINT mid-stream leaves no partial file at the target path" is satisfied structurally, not by special-casing the signal.

- **D-08-10 (`os.replace()` is the single promotion path):** Only `_NdjsonFileSink.__exit__`'s success branch calls `os.replace(self._tmp, self._target)`. No other code path in `quizify_csv_ingest.py` touches the target file. Test asserts that on validation failure / SIGINT / generic exception, the target path does NOT exist after the run. CI grep gate (planner's call) on `os.replace` to keep the surface auditable.

### Argparse

- **D-08-11 (`--ndjson` is `store_true`, lives OUTSIDE the existing `-o/--post-url` mutex group, with two post-parse `parser.error()` checks):** Phase 7's mutex group stays exactly as it was. `--ndjson` is added as a peer flag. After `parser.parse_args()`, `main()` calls:
  - if `args.ndjson and args.post_url`: `parser.error("--ndjson cannot be combined with --post-url")` (exits 2).
  - if `args.ndjson and not args.output`: `parser.error("--ndjson requires -o/--output (no stdout NDJSON)")` (exits 2).
  Both error messages are categorical and PII-safe (T-PII-01). `parser.error` writes to stderr and exits 2 — argparse's default behavior. Help text on `--ndjson` documents both constraints inline.

- **D-08-12 (`args.ndjson` threads through to `convert()` as a named parameter):** `convert()` gains `ndjson: bool = False`. The sink-selection helper (`_select_sink` in current code) gains a third branch; recommended order: `--post-url` → `_HttpPostSink`; `--ndjson + --output` → `_NdjsonFileSink(output)` (optionally wrapped by `_ValidatingSink`); `--output` (no `--ndjson`) → `_FileSink`; else → `_StdoutSink`. Validation wrapping happens at the same layer.

- **D-08-13 (`--ndjson` does NOT require `--validate`):** STREAM-03 reads "`--ndjson + --validate` validates each row" — the validate flag is optional. NDJSON without validation is a supported configuration (operator's choice; matches array mode's default-off). Phase 9 will land `--post-url requires --validate`; that gate is NOT introduced here.

### Testing

- **D-08-14 (Five test surfaces; placement is planner's discretion):**
  1. **NDJSON happy path:** `--ndjson -o tmp.ndjson` against `quizify-submissions.csv` produces N lines for N rows; each line round-trips via `json.loads`; `jq -s . tmp.ndjson` (or stdlib equivalent: `json.loads('[' + ','.join(lines) + ']')`) reproduces the v1.1 golden array structurally (same set of dicts, same key order per row — D-05).
  2. **No `\r` bytes anywhere:** byte-level assertion on the produced file.
  3. **STREAM-03 per-row validation failure:** synthetic 100-row CSV with malformed row at index 50; `--ndjson --validate` exits 1; stderr contains JSON Pointer with no cell content (negative-substring tests against email/phone/free-text from the synthetic fixture); target path does not exist; `.tmp` may or may not exist (test the *target* invariant only, per STREAM-04 wording).
  4. **STREAM-04 SIGINT mid-stream:** subprocess test (justified exception to Pitfall 16 — SIGINT cannot be raised cleanly inside a unit test without subprocess) that sends SIGINT mid-write and asserts target path does not exist after the child exits. Optional alternative: simulate via `KeyboardInterrupt` raised from a fake sink in a unit test, which exercises the same `__exit__` code path. Planner's call on subprocess-vs-unit; subprocess is Pitfall-16-acceptable for SIGINT specifically.
  5. **Argparse rejections:** `--ndjson --post-url ...` exits 2 with the categorical message; `--ndjson` alone (no `-o`) exits 2; both via pytest's `capsys` + `pytest.raises(SystemExit)`.

- **D-08-15 (Default-mode regression test stays green):** TRAIL-03 byte-identity test inherited from Phase 7 must remain green — D-05 / D-13 / D-11 carry-forward. No new test dependencies (no `responses`, no `requests-mock`, no `pyfakefs` — `tmp_path` from pytest is sufficient for atomic-write verification).

### Carry-forward (locked, not re-asked)

- **D-05 (locked tail-key order):** Each NDJSON line uses the same `build_row` output as array mode; key order preserved. `ensure_ascii=False` on `json.dump`.
- **D-06-2x (validation surfaces):** `_run_schema_validation` body untouched; new per-row failure path uses the SAME `_format_validation_error` PII-safe formatter and exit code 1.
- **D-07-01 / D-07-08 / D-07-09 (Phase 7 sink Protocol, validation timing for array mode, schema function body):** all preserved. NDJSON adds new code paths; old paths remain byte-identical.
- **D-11 (10-section README lock):** README updates only inside existing sections. Likely additions: `--ndjson` row in `## CLI reference` table; brief line in usage examples. NO new H2. D-11 drift test (`tests/test_readme_help_alignment.py`) must stay green.
- **D-13 (stdlib-only at runtime):** `os.replace`, `os.unlink`, `json.dump` are stdlib. `fastjsonschema` import stays inside `_ValidatingSink.__init__` (lazy, only when `--validate` is set), preserving the missing-extra path (D-06-19).
- **T-PII-01 (PII-safe stderr):** All new stderr surfaces (per-row validation, argparse rejections) are categorical only. Negative-substring tests required.
- **TRAIL-03 default-order golden-fixture regression:** must stay green.

### Claude's Discretion

- Exact name of the sentinel exception class (`_RowValidationError` proposed; planner may use a different name as long as it is module-private).
- Exact format of the row-prefixed JSON Pointer on stderr (e.g., `row 49: /answers-3` vs `/49/answers-3` vs `[row=49] <pointer>`) — must be PII-safe and consistent with existing D-06-2x templates.
- Whether `_ValidatingSink` is a top-level class or nested helper — top-level is preferred for testability.
- Whether `_select_sink` becomes `_select_sink(args)` or stays the current `_select_sink(output, post_url)` and gains `ndjson`, `validate`, `schema_path` parameters — planner's call.
- Test file naming: extend `tests/test_sinks.py` (or whatever Phase 7 picked) vs new `tests/test_ndjson.py` + `tests/test_atomic_write.py` — planner's call. Reuse `conftest.py` fixtures.
- Whether the SIGINT test is subprocess-driven or simulates `KeyboardInterrupt` via a fake sink in a pure unit test — both satisfy STREAM-04. Subprocess is the Pitfall-16-acceptable exception when truly testing signal delivery.
- Whether `_NdjsonFileSink.close()` is `pass` or asserts the CM was used (defensive) — planner's call.
- Whether `_StdoutSink`/`_FileSink` `__exit__` calls `close()` only on `exc_type is None` (matches NDJSON semantics) or on every exit (matches today's behavior). Today's behavior is "always emit on close" — preserve it for non-NDJSON modes to keep array-mode byte-identity intact even on partial-failure paths. For NDJSON only, `__exit__` discriminates.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 8: STREAM-01 NDJSON Output" — phase goal, dependencies (Phase 7), five success criteria (line count + `\n`-only + `jq -s` array equivalence; per-row validation failure → no target file; `--ndjson + --post-url` and `--ndjson + stdout` argparse rejections; SIGINT leaves no target; default array byte-identity preserved).
- `.planning/REQUIREMENTS.md` §"Streaming (STREAM)" — STREAM-01..04 verbatim text. Locked deferral: NDJSON × POST cross-product is v1.3 candidate.

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (tail-key order), D-11 (10-section README lock), D-13 (stdlib-only at runtime).
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 (PII-safe stderr); D-03 (empty cells emit `""`).

### Phase 7 carry-forwards (immediate predecessor)
- `.planning/phases/07-refactor-scaffolding-no-op/07-CONTEXT.md` — D-07-01 (sink Protocol shape), D-07-04 (`_HttpPostSink` stub depth — NOT modified by Phase 8), D-07-05/06 (`_RowStream` / `iter_rows()`), D-07-08 (array-mode validation timing — preserved), D-07-09 (`_run_schema_validation` body untouched), D-07-10 (Phase 7 mutex group preserved verbatim), D-07-11 (sink-selection helper extension point).

### Phase 6 carry-forwards (validation primitives)
- `.planning/milestones/v1.1-phases/06-json-schema-validation/06-CONTEXT.md` — D-06-16 (post-build pre-write timing for array mode), D-06-17 (lazy `import fastjsonschema`), D-06-18 (compile once), D-06-19 (missing-extra template), D-06-20 (PII-safe formatter `_format_validation_error`), D-06-21 (exit code 1), D-06-22 (validate × missing-trio independence).

### v1.2 milestone research
- `.planning/research/SUMMARY.md`, `.planning/research/STACK.md`, `.planning/research/FEATURES.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md` — v1.2 research (sink abstraction, NDJSON, atomic writes).
- `.planning/research/PITFALLS.md` §"Pitfall 16" — keep tests at unit level, not subprocess-driven (justified exception: SIGINT delivery test).
- `.planning/research/PITFALLS.md` §"Pitfall 17" — never forward `JsonSchemaValueException.message` raw (carry-forward; `_ValidatingSink` reuses `_format_validation_error`).
- `.planning/research/PITFALLS.md` §"Pitfall 18" — keep `import fastjsonschema` lazy.

### Files being edited or created
- **EDITED:** `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — add `_NdjsonFileSink` (context manager), `_ValidatingSink` (decorator), `_RowValidationError` (sentinel); add `__enter__/__exit__` shims to `_StdoutSink`, `_FileSink`, `_HttpPostSink`; extend `_select_sink` (or replace with `_select_sink(args)`); add `--ndjson` argparse flag + two post-parse `parser.error` checks; thread `ndjson` (and `validate` for sink wrapping) through `convert()`; rewrite `convert()`'s sink usage to `with sink: for row in stream: sink.write(row)`.
- **EDITED:** `quizify-csv-to-json-webhook/README.md` — add `--ndjson` row to existing `## CLI reference` table; mention `--ndjson + --validate` per-row behavior in usage examples. NO new H2 (D-11).
- **NEW or EDITED:** test file(s) for the five surfaces in D-08-14. Placement is planner's call. Reuse `tests/conftest.py` fixtures.
- **NOT EDITED:** `_run_schema_validation`, `_format_validation_error`, `build_row`, `classify_headers`, `iter_rows`/`_RowStream` (Phase 7), `_HttpPostSink` body, `_StdoutSink.write/close`, `_FileSink.write/close`, schema artifact `quizify-csv-to-json-webhook/docs/webhook-schema.json`.

### Sample / verification fixtures
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row real export. NDJSON happy-path test compares structurally against the v1.1 golden array.
- Synthetic 100-row CSV with malformed row at index 50 — generated in test (no PII; T-PII-01-safe).

### Sibling carry-forward
- `.planning/milestones/v1.1-phases/05-python-trailer-hardening/05-CONTEXT.md` — D-05-08 missing-trio WARNING template; `_RowStream` already preserves the call site, NDJSON does not interact with this path.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_Sink` Protocol (`quizify_csv_ingest.py:49`) — `_NdjsonFileSink` and `_ValidatingSink` both conform.
- `_StdoutSink` / `_FileSink` / `_HttpPostSink` (`quizify_csv_ingest.py:54-95`) — gain `__enter__/__exit__` shims; bodies untouched.
- `_select_sink(output, post_url)` (`quizify_csv_ingest.py:96`) — extension point for the third branch (`ndjson`) and for wrapping with `_ValidatingSink`.
- `iter_rows(...)` / `_RowStream` (`quizify_csv_ingest.py:179`) — reused as-is. NDJSON streams via `for row in iter_rows(...): sink.write(row)` (no `list(...)` materialization in NDJSON mode — directly satisfies the streaming intent).
- `_run_schema_validation` and `_format_validation_error` (Phase 6) — `_ValidatingSink` reuses `_format_validation_error` for PII-safe pointer rendering.
- `SCHEMA_PATH` constant — reused; no new schema artifact.

### Established Patterns
- Single-file CLI by design (D-06-04). All four sinks + decorator + sentinel exception live in `quizify_csv_ingest.py`.
- Lazy / conditional imports for optional extras (D-13). `fastjsonschema` import stays inside `_ValidatingSink.__init__`.
- First-only / once-only side effects. Schema compile happens once per `_ValidatingSink` instance (matches D-06-18).
- Pure functions returning tuples for stateless work; classes only when state is necessary. `_NdjsonFileSink` and `_ValidatingSink` justify class state (file handle + .tmp path; compiled validator + row index).

### Integration Points
- Argparse setup at `quizify_csv_ingest.py:~595-605` — `--ndjson` added as a peer flag outside the existing mutex group; two post-parse `parser.error()` checks added.
- `convert()` at `quizify_csv_ingest.py:561` — sink usage rewritten to `with sink: for row in iter_rows(...): sink.write(row)`. Validation wrapping happens at sink-construction time, not inside the loop.
- Default-mode array path: `list(iter_rows(...))` materialization + `_run_schema_validation(results, SCHEMA_PATH)` + `with _StdoutSink_or_FileSink:` — preserved exactly as Phase 7 left it.
- NDJSON-mode path: no `list(...)` — rows stream straight through `_ValidatingSink` (optional) into `_NdjsonFileSink`. Memory profile is bounded regardless of CSV size (T-RESOURCE-01 follow-through).

</code_context>

<specifics>
## Specific Ideas

- **`_NdjsonFileSink` skeleton (locked verbatim — planner may rename internal attributes):**
  ```python
  class _NdjsonFileSink:
      def __init__(self, output: Path):
          self._target = output
          self._tmp = output.with_suffix(output.suffix + ".tmp")
          self._fp = None

      def __enter__(self):
          self._fp = self._tmp.open("w", encoding="utf-8", newline="\n")
          return self

      def write(self, row: dict) -> None:
          json.dump(row, self._fp, ensure_ascii=False)
          self._fp.write("\n")

      def __exit__(self, exc_type, exc, tb):
          self._fp.close()
          if exc_type is None:
              os.replace(self._tmp, self._target)
          else:
              try:
                  os.unlink(self._tmp)
              except OSError:
                  pass
          return False  # never suppress

      def close(self) -> None:  # _Sink Protocol compliance; no-op when CM is used
          pass
  ```

- **`_ValidatingSink` skeleton (locked shape — planner may adjust exception message format):**
  ```python
  class _ValidatingSink:
      def __init__(self, inner: "_Sink", schema_path: Path):
          import fastjsonschema  # lazy, D-13 / D-06-17
          schema = json.loads(schema_path.read_text(encoding="utf-8"))
          self._validate_one = fastjsonschema.compile(schema["items"])
          self._inner = inner
          self._idx = 0

      def __enter__(self):
          self._inner.__enter__()
          return self

      def write(self, row: dict) -> None:
          try:
              self._validate_one(row)
          except Exception as exc:  # JsonSchemaValueException; caught categorically per Pitfall 17
              raise _RowValidationError(self._idx, _format_validation_error(exc)) from None
          self._inner.write(row)
          self._idx += 1

      def __exit__(self, exc_type, exc, tb):
          return self._inner.__exit__(exc_type, exc, tb)

      def close(self) -> None:
          self._inner.close()
  ```

- **Argparse shape (locked):**
  ```python
  parser.add_argument("--ndjson", action="store_true",
      help="Emit line-delimited JSON; requires -o/--output, mutually exclusive with --post-url.")
  # existing Phase 7 mutex group unchanged
  args = parser.parse_args()
  if args.ndjson and args.post_url:
      parser.error("--ndjson cannot be combined with --post-url")
  if args.ndjson and not args.output:
      parser.error("--ndjson requires -o/--output (no stdout NDJSON)")
  ```

- **STREAM-04 invariant test (name-of-art):** assert that after a validation-failure run with `--ndjson --validate`, the target path does not exist. The `.tmp` may or may not — STREAM-04 only constrains the *target*. Same shape for SIGINT.

- **`json.dump(row, fp, ensure_ascii=False)`** — note the absence of `indent=2`. NDJSON lines are compact-encoded by definition. D-05 tail-key order is still preserved because `build_row` produces ordered dicts.

</specifics>

<deferred>
## Deferred Ideas

- **NDJSON × `--post-url` cross-product** — v1.3+ per REQUIREMENTS Future Requirements list. Make.com webhook content-type is `application/json` of an array; partial-success semantics need design.
- **`--retry N` exponential backoff, `--idempotency-key`** — Phase 9 / v1.3+; Make.com idempotency unverified.
- **`$QUIZIFY_WEBHOOK_URL` / `--post-url-env`** — defer unless operator pain reported.
- **HTTP POST delivery (HTTPS-only check, header parsing with CRLF rejection, `--timeout`, `--post-url requires --validate` argparse gate, redirect handling)** — Phase 9 (AUTO-01..06). Phase 8's `_ValidatingSink` decorator is the primitive Phase 9 will reuse for pre-egress validation.
- **`_HttpPostSink` body** — Phase 9. Stays a stub in Phase 8.
- **Per-row validation in array mode** — NOT introduced. Array mode keeps batch validation timing (D-07-08 / D-06-16). Could be unified later by wrapping any sink with `_ValidatingSink`, but that's a behavior change that needs its own discussion.
- **Atomic write for non-NDJSON `_FileSink`** — explicitly not retrofitted. v1.1 `_FileSink` does direct-open; preserving that keeps TRAIL-03 byte-identity safe and avoids touching code paths v1.2 doesn't need to touch.
- **RFC 7464 JSON Text Sequences** — out of scope per REQUIREMENTS; NDJSON is the dominant ecosystem standard.
- **Make.com hygiene + node:test harness** — Phase 10. Independent of Phase 8.

</deferred>

---

*Phase: 08-stream-01-ndjson-output*
*Context gathered: 2026-05-05*
