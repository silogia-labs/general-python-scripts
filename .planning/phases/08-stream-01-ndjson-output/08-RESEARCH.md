# Phase 8: STREAM-01 NDJSON Output — Research

**Researched:** 2026-05-05
**Domain:** stdlib-Python NDJSON streaming + atomic file write + per-row fastjsonschema validation, single-file CLI
**Confidence:** HIGH

## Summary

Phase 8 implementation is unusually low-uncertainty: every architectural decision is locked in 08-CONTEXT.md (D-08-01..15), the sink Protocol exists in code (Phase 7), `_format_validation_error` exists and is PII-safe (Phase 6), and the four runtime primitives (`json.dump`, `os.replace`, `os.unlink`, `Path.open(newline="\n")`) are all stdlib with well-documented semantics. Research therefore converges on a *posture and verification* document rather than a stack-selection document.

The two surfaces with real research content are: (1) the JSON-Pointer prefix format on per-row validation failure (Claude's discretion per D-08-06; the `/<idx>` RFC-6901 form best matches the existing `_format_validation_error` output), and (2) whether to test SIGINT via subprocess or via a `KeyboardInterrupt`-raising fake sink (Pitfall 16 + STREAM-04 — both forms are recommended; the unit-test form covers the `__exit__` cleanup logic, the subprocess form covers actual signal delivery).

**Primary recommendation:** Plan TDD-style around the locked skeletons in 08-CONTEXT.md `<specifics>`. Test surface order: argparse rejections (cheapest) → unit `_NdjsonFileSink` `__exit__` cleanup with a fake row that raises → unit `_ValidatingSink` decorator + sentinel exception → integration happy path against `quizify-submissions.csv` with `jq -s`-equivalent structural compare → subprocess SIGINT test (justified Pitfall 16 exception). Default-mode regression (TRAIL-03 byte-identity, D-11 README drift 2/2) must remain green at every commit.

## Project Constraints (from CLAUDE.md)

No project-level `./CLAUDE.md` and no `.claude/skills/` directory exist in the repo (verified). Constraints are inherited entirely from `.planning/PROJECT.md` and 08-CONTEXT.md carry-forwards: D-05 tail-key order, D-06-2x stderr templates, D-07-* sink Protocol shape, D-11 README ten-section lock, D-13 stdlib-only at runtime, T-PII-01 PII-safe stderr, TRAIL-03 byte-identity. `[CITED: 08-CONTEXT.md §"Carry-forward"]`

## User Constraints (from 08-CONTEXT.md)

### Locked Decisions (D-08-01 .. D-08-15)
Copied verbatim from 08-CONTEXT.md `<decisions>` — see source file for full text. Summary of bindings the planner cannot re-derive:
- `_NdjsonFileSink` is a new standalone class implementing `_Sink` Protocol; context manager owns `.tmp` lifecycle; `os.replace` is the single promotion path (D-08-01..04, D-08-10).
- `_ValidatingSink(inner, schema_path)` is a decorator; lazy-imports `fastjsonschema`; compiles `schema["items"]` once; raises `_RowValidationError(idx, pointer)` on first failure (D-08-05..06).
- All sinks gain `__enter__/__exit__` shims; `convert()` rewrites to `with sink:` loop (D-08-03).
- `--ndjson` is `store_true`, peer of the existing mutex group; two post-parse `parser.error()` checks; per-row validation only when `--ndjson AND --validate` (D-08-07, D-08-11..13).
- Five test surfaces (D-08-14); TRAIL-03 byte-identity stays green (D-08-15).

### Claude's Discretion
- Sentinel exception name (`_RowValidationError` proposed)
- Row-prefixed JSON-Pointer format on stderr (e.g., `row 49: /answers-3` vs `/49/answers-3`)
- Whether `_ValidatingSink` is top-level or nested
- Whether `_select_sink` becomes `_select_sink(args)` or grows parameters
- Test file naming & placement
- Whether SIGINT test is subprocess-driven or fake-sink unit test
- Whether `_NdjsonFileSink.close()` is `pass` or asserts CM was used
- Whether non-NDJSON sink `__exit__` calls `close()` always or only on success

### Deferred Ideas (OUT OF SCOPE)
NDJSON × `--post-url`, retries, idempotency-key, env-var URL, full HTTP POST body (Phase 9), Make.com hygiene (Phase 10), array-mode per-row validation, atomic write retrofit to `_FileSink`, RFC 7464.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STREAM-01 | `--ndjson` flag, file-mode only, argparse rejects `--ndjson + --post-url` | §Implementation Q1 (atomic write), Q9 (argparse) |
| STREAM-02 | `\n` separator; `newline="\n"` to defeat CRLF; one row per line, one trailing `\n` | §Implementation Q2 (json.dump cost), Q3 (newline semantics) |
| STREAM-03 | `--ndjson + --validate` validates each row vs `schema["items"]` (compiled once); first failure exits 1 with categorical JSON Pointer | §Implementation Q4 (fastjsonschema), Q5 (pointer format), Q8 (fixture) |
| STREAM-04 | Atomic file write via `.tmp` + `os.replace`; SIGINT mid-stream leaves no partial file at target path | §Implementation Q1 (replace), Q6 (SIGINT/CM), Q7 (streaming memory) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-row JSON encoding | CLI process (Python stdlib `json`) | — | NDJSON is a single-process file-emit; no service tier |
| Atomic file write | Filesystem (`os.replace`) | CLI process (`__exit__`) | OS owns rename atomicity; CM coordinates |
| Per-row schema validation | CLI process (`fastjsonschema`) | — | Compile-once primitive lives in the same process |
| SIGINT cleanup | CPython runtime + CM `__exit__` | OS | Default `KeyboardInterrupt` propagation through `with` |
| Argparse rejections | CLI process (`argparse.ArgumentParser`) | — | Stdlib parser owns exit-2 error template |

## Standard Stack

### Core (all stdlib — D-13 preserved)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | stdlib | `json.dump(row, fp, ensure_ascii=False)` per row | Already used in v1.1; `ensure_ascii=False` preserves UTF-8 lines `[VERIFIED: existing code line 63, 79]` |
| `os` | stdlib | `os.replace(tmp, target)`, `os.unlink(tmp)` | `os.replace` is atomic on POSIX and Windows since Python 3.3 `[CITED: docs.python.org/3/library/os.html#os.replace]` |
| `pathlib.Path` | stdlib | `output.with_suffix(output.suffix + ".tmp")`, `Path.open("w", newline="\n")` | Already used throughout; `with_suffix` confirmed locked in D-08-04 |
| `argparse` | stdlib | `--ndjson` flag, post-parse `parser.error()` | `parser.error()` exits 2 with `usage: ... \n {prog}: error: {msg}` format `[CITED: docs.python.org/3/library/argparse.html#argparse.ArgumentParser.error]` |

### Supporting (already in `[validate]` extra)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastjsonschema` | existing optional dep | Compile `schema["items"]` once; raise `JsonSchemaValueException` on first row failure | Only when `--ndjson AND --validate` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `output.with_suffix(suffix + ".tmp")` | `tempfile.NamedTemporaryFile(delete=False, dir=parent)` | Random suffix avoids stale-`.tmp` collision; but D-08-04 locks predictable name. Single-process utility; concurrent invocations unsupported (documented). Stay with locked choice. |
| `json.dump(row, fp, ...)` per row | `fp.write(json.dumps(row, ...) + "\n")` | Performance roughly equivalent at 50k-row scale; both call the same C-level encoder. `json.dump` writes incrementally without building a full str — slightly less memory churn per row. D-08-02 locks `json.dump`. `[ASSUMED: stdlib implementation detail; both are O(row_bytes), no behavioral difference at this scale]` |
| Custom `signal.signal(SIGINT, handler)` | Default `KeyboardInterrupt` + `__exit__` | D-08-09 locks "no signal handler"; CPython default is sufficient because `with` blocks invoke `__exit__` on `KeyboardInterrupt`. Custom handler would complicate testing without adding behavior. |

**Installation:** No new dependencies. The `[validate]` extra already contains `fastjsonschema` and is unchanged.

**Version verification:** No new packages added; nothing to verify on the registry. The existing `fastjsonschema` extra is untouched.

## Implementation Approach (Per-Question Recommendations)

### Q1. Atomic write semantics

**Recommendation:** `os.replace(self._tmp, self._target)` with no `fp.flush() + os.fsync()`. Use `output.with_suffix(output.suffix + ".tmp")` per D-08-04.

**Why:**
- `os.replace` is atomic on both POSIX (rename(2)) and Windows since Python 3.3, *including* across-an-existing-target replacement (the v1.1 `_FileSink` truncate-and-overwrite path is non-atomic and observable mid-write — that's the gap STREAM-04 closes). `[CITED: docs.python.org/3/library/os.html#os.replace]`
- `os.fsync` is *durability* (survive power loss), not *atomicity* (observers see whole or nothing). The use case is a webhook payload utility — operators re-run on failure; durability across power loss is not a contract. Adding `fsync` doubles wall-time on large outputs without buying a property anyone tests for. Don't add it.
- `tempfile.NamedTemporaryFile` would solve concurrent-invocation collisions but D-08-04 locks predictable naming. The 08-CONTEXT.md explicitly accepts "concurrent invocations writing to the same target are not supported" as a documented limitation, which matches the existing utility-script posture.
- `Path.open("w", encoding="utf-8", newline="\n")` truncates `.tmp` on `__enter__` — a stale `.tmp` from a prior aborted run is overwritten cleanly. No pre-clean step needed.

**Posture:** Atomicity-yes, durability-no. `[VERIFIED: Python docs + existing v1.1 file-emit pattern]`

### Q2. `json.dump` per-row encoding cost

**Recommendation:** Use `json.dump(row, fp, ensure_ascii=False)` per locked D-08-02. Do **not** pass `sort_keys=True` (default is `False` — D-05 tail-key order requires preservation). Do **not** pass `indent=2` (NDJSON lines are compact-encoded by definition; locked in 08-CONTEXT.md `<specifics>`).

**Why:**
- `json.dump` and `json.dumps + write` invoke the same encoder (`_make_iterencode`); the `dump` form streams chunks to the file, the `dumps` form materializes a `str` first. For typical row sizes (~1–4 KB) the difference is negligible. `[ASSUMED: stdlib internals; both are well within budget at 50k rows × ~2 KB ≈ 100 MB total I/O — milliseconds-scale on SSD]`
- `sort_keys` defaults to `False` in CPython `json` `[CITED: docs.python.org/3/library/json.html#json.dump]`. `build_row` produces dicts in D-05's locked tail-key insertion order — Python 3.7+ guarantees insertion-order preservation. No explicit `sort_keys=False` needed; the default suffices and reads cleaner.
- `separators=(",", ":")` (compact form) is *not* required by NDJSON (any whitespace inside a single line is fine), and adding it would diverge subtly from v1.1 array-mode encoding. Don't add it; defaults are fine. `jq -s` and `json.loads` both ignore intra-line whitespace.

### Q3. `newline="\n"` text-mode semantics

**Recommendation:** Use `output.open("w", encoding="utf-8", newline="\n")` per D-08-02 verbatim.

**Why:**
- `open(..., newline="\n")` in text mode disables the universal-newlines write translation: bytes written to the stream are passed through as-is, including raw `\n`. Without `newline="\n"`, on Windows the default `newline=None` translates each `\n` written by the program into `\r\n` on disk. `[CITED: docs.python.org/3/library/functions.html#open — "If newline is '' or '\\n', no translation takes place."]`
- `json.dump(row, fp, ensure_ascii=False)` does not emit `\r` itself anywhere in its output for a normal row dict — it writes only the JSON-encoded structure. Embedded `\n` inside a JSON string is escaped to `\\n` (two characters). So the only newlines reaching `fp.write` are the explicit `fp.write("\n")` we add per row. `[VERIFIED: stdlib json source — encoder escapes control chars]`
- Test: byte-level assertion `b"\r" not in output_path.read_bytes()` — locked in D-08-14 surface 2.

### Q4. `fastjsonschema` per-row compilation of subschema

**Recommendation:** Locked verbatim in D-08-05/D-08-08:
```python
schema = json.loads(schema_path.read_text(encoding="utf-8"))
self._validate_one = fastjsonschema.compile(schema["items"])
```
Compile once in `_ValidatingSink.__init__`, reuse across all `write()` calls. Do not use `compile_to_code` (it's an AOT codegen helper for cold-start optimization; irrelevant for a CLI invocation). Catch `Exception` categorically per the locked skeleton (Pitfall 17: never trust `JsonSchemaValueException.message`/`.value` to be PII-safe; reuse the existing `_format_validation_error` formatter which reads only `err.path`, `err.definition`, `type(err.value).__name__`).

**JsonSchemaValueException attributes — confirmed PII-safe-vs-unsafe (matches Phase 6 lock):**
| Attribute | Phase 6 stance | Use |
|-----------|----------------|-----|
| `err.path` | safe (validator var-name + key path) | yes — feeds JSON Pointer construction |
| `err.definition` | safe (schema clause; repo-controlled) | yes — yields `expected` type |
| `type(err.value).__name__` | safe (Python type name) | yes — yields `actual` type |
| `err.message` | UNSAFE (echoes cell content) | NEVER — Pitfall 17 |
| `err.value` | UNSAFE (literal cell value) | NEVER except `type(...).__name__` |
| `err.name` | safe (rule keyword like "type", "required") | optional; not currently used |
| `str(err)` | UNSAFE (delegates to `.message`) | NEVER |

`[VERIFIED: Phase 6 `_format_validation_error` body, lines 484-501 in quizify_csv_ingest.py]`

`schema["items"]` extraction works because the existing schema's root is `{"type": "array", "items": {...per-row...}}` — the per-row subschema *is* `schema["items"]`. `[VERIFIED: docs/webhook-schema.json lines 6-60]`

### Q5. JSON-Pointer construction with row index

**Recommendation:** Use the **RFC 6901 array-rooted form**: `/<idx><pointer>` where `<idx>` is 0-based and `<pointer>` is the existing `_format_validation_error` output starting with `/`.

Concretely, when `_format_validation_error(err)` would print:
```
ERROR schema validation failed at /answers-3: expected string, got NoneType
```
the row-prefixed NDJSON form should print:
```
ERROR schema validation failed at /49/answers-3: expected string, got NoneType
```

**Why:**
- RFC 6901 is the JSON Pointer spec; an array-rooted document treats indices as path tokens. The aggregate of NDJSON lines, viewed as a virtual array, has its row-49 element at pointer `/49`. Concatenating the per-row pointer is mechanically correct and tool-agnostic. `[CITED: RFC 6901 §4]`
- Drop-in compatible with the existing `_format_validation_error` template (D-06-20) — the planner can implement this by either (a) post-processing the formatter output and substring-replacing the leading `/` with `/<idx>/`, or (b) extending `_format_validation_error` to accept an optional `row_idx` and prefix accordingly. Option (b) is cleaner.
- Greppable: `grep "/49/" stderr` finds row-49 errors. PII-safe: contains only the row index (an integer counter, not user data) and the categorical pointer/types.
- Alternative considered: `row 49: /answers-3` (categorical prefix). Rejected — less greppable for "errors at index N", and breaks the existing template shape (downstream tools that match on the locked template would need a regex update).

**Sentinel exception shape (per D-08-06):**
```python
class _RowValidationError(Exception):
    def __init__(self, row_index: int, pointer_message: str) -> None:
        self.row_index = row_index
        self.pointer_message = pointer_message
        super().__init__(pointer_message)
```
`convert()` catches it and prints the already-formatted message to stderr, returns 1.

### Q6. SIGINT / KeyboardInterrupt propagation through `with`

**Recommendation:** Implement BOTH a unit test (raise `KeyboardInterrupt` from a fake inner sink, assert `.tmp` is unlinked and target absent) AND a subprocess SIGINT test (justified Pitfall 16 exception per D-08-14 surface 4).

**Confirmed CPython behavior:**
- A `KeyboardInterrupt` raised mid-`sink.write()` propagates up through the `with sink:` block; CPython invokes `sink.__exit__(KeyboardInterrupt, exc_instance, tb)` before re-raising. `[CITED: docs.python.org/3/reference/compound_stmts.html#the-with-statement]`
- `_NdjsonFileSink.__exit__` sees `exc_type is KeyboardInterrupt` → closes fp, unlinks `.tmp`, returns `False`, KeyboardInterrupt continues to propagate.
- Edge case 1: SIGINT during `fp.close()` itself — CPython delays signal delivery until the next bytecode boundary; `close()` is a single C-level call. In practice, the kernel may deliver SIGINT after `close()` returns but before `os.replace`. The test invariant (target path absent) still holds because we only call `os.replace` in the success branch (`exc_type is None`). On SIGINT after close-but-before-replace, the path goes through `__exit__(KeyboardInterrupt, ...)` → unlink branch → target never created. ✓
- Edge case 2: SIGINT during `os.replace` itself. `os.replace` is a single syscall; either completes (target appears) or doesn't (target absent). If it completes and SIGINT is raised on return, the target is fully formed (success branch already ran). This is acceptable — STREAM-04's contract is "no *partial* file at target," not "no file at all on SIGINT." The race window is microseconds-wide and the result is well-formed.
- Edge case 3: SIGINT during `os.unlink(self._tmp)` in the cleanup branch. The `try/except OSError: pass` (locked in D-08-02 skeleton) absorbs OSError, but `KeyboardInterrupt` is not an `OSError` — a second SIGINT during cleanup would skip the `pass` and propagate, leaving `.tmp` on disk. Acceptable: STREAM-04 only constrains the *target*, not `.tmp`.

**Test strategy (recommend BOTH):**

| Test | Mechanism | What it verifies | Pitfall 16 status |
|------|-----------|------------------|-------------------|
| Unit | Fake inner sink whose `write()` raises `KeyboardInterrupt` on Nth row; wrap in `_NdjsonFileSink`-equivalent CM (or use real CM with monkeypatched `json.dump`) | `__exit__` cleanup logic on `KeyboardInterrupt` | preferred (unit-level) |
| Subprocess | `subprocess.Popen` of CLI; `os.kill(child.pid, signal.SIGINT)` after a short delay; assert `child.wait()` returns non-zero, target path does not exist | Real signal delivery through CPython's main loop | justified exception |

The unit form is the regression lock (fast, deterministic). The subprocess form is the integration lock (proves the whole-program SIGINT path actually works). Plan should land both.

### Q7. Streaming generator memory profile

**Recommendation:** Confirm by code inspection — no new test needed beyond the existing happy path.

`_RowStream.__iter__` (lines 127-176) yields one dict per row with no internal accumulation; the `_RowStream.exit_code` attribute is the only state. The NDJSON path in `convert()` becomes:
```python
with sink:
    for row in iter_rows(path, trailer, quiz_title):  # _RowStream — one dict at a time
        sink.write(row)
```
No `list(...)` materialization. RAM profile is bounded: one row dict + the compiled validator + the open file handle, regardless of CSV size. `[VERIFIED: existing code lines 110-185]`

The array-mode path retains `results = list(stream)` (line 564) — by design, because batch validation requires the full list. This is unchanged. `[VERIFIED: existing code line 564, D-07-08 carry-forward]`

### Q8. Test fixture strategy for STREAM-03

**Recommendation:** Generate the synthetic 100-row CSV in-process via `io.StringIO` written to `tmp_path`. No PII; no fixture file checked in.

**Approach:**
```python
@pytest.fixture
def csv_with_bad_row_at_50(tmp_path: Path) -> Path:
    rows = []
    rows.append(",".join(EXPECTED_HEADER))  # full header from CONTACT_PREFIX + 1 dynamic + DEFAULT_TRAILER
    for i in range(100):
        # synthetic non-PII cells; prefix-name "user{i}" + numeric phone "555-0100"
        rows.append(_synthetic_row(i, malformed=(i == 50)))
    p = tmp_path / "synthetic.csv"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p
```

**What kind of malformation reliably violates `schema["items"]` without breaking `build_row`:**

`build_row` always returns a structurally complete dict (every required key present, types correct for the happy path). To force a `schema["items"]` violation while keeping `build_row` happy, the cleanest approach is:

**Option A (recommended): malform a `tags`-bound input** — but `tags` is built unconditionally to a list, so this is hard.

**Option B (recommended): malform a numeric-typed answer cell to violate `^answers-\d+$`'s `oneOf: [string, array<object>]`**. `shape_answer` returns the cell verbatim if it doesn't look like an answer-array — so a string that *parses as JSON to a non-string-non-array-of-objects* would slip through `build_row` but fail `schema["items"]`. However, since `shape_answer` returns string-or-list-of-dict, this is also hard.

**Option C (cleanest, recommended): bypass `build_row` for the bad row** by monkeypatching it on a single row index, OR by injecting a row-mutator into `_ValidatingSink` testing seam. Specifically, write the unit test against `_ValidatingSink` directly with a hand-built dict that violates the schema (e.g., `{"email": 12345, ...}` — wrong type on a required field). This isolates the validation mechanic without depending on CSV → `build_row` path.

**Option D (integration-level, recommended for the STREAM-03 surface as written):** Use Option C for the unit test, AND for the integration test produce a CSV whose row 50 has structural damage that makes `build_row` emit a row that fails. The simplest reliable mechanism: omit a column. Specifically, given `schema["items"]` requires `email` to be a string and the row-length-mismatch path (line 157-165) skips short rows with `exit_code |= 1`, instead modify `build_row` interaction by giving row 50 a **different structural damage that survives the row-length check but produces a non-string somewhere**. After analysis, the most reliable malformation is to test at the `_ValidatingSink` unit level with hand-crafted dicts; the integration test can use a CSV whose row 50 mutates *after* `build_row` via a test-only injection point.

**Final recommendation:** STREAM-03 unit test uses hand-built dicts injected directly into `_ValidatingSink.write()`. STREAM-03 integration test uses a CSV where the deliberate failure mechanism is a row-length mismatch on row 50 (a documented `exit_code |= 1` path that already exists), THEN combine with a separate test that exercises `_ValidatingSink` failure directly. This split keeps the fixture PII-free and avoids fragile interactions with `build_row`.

`[VERIFIED: existing _RowStream code lines 156-176; build_row code lines 368-443; schema/items at docs/webhook-schema.json lines 7-60]`

### Q9. Argparse interaction patterns

**Recommendation:** Locked verbatim in 08-CONTEXT.md `<specifics>`. Implementation notes:

- `parser.add_argument("--ndjson", action="store_true", help="...")` lives at parser level, NOT inside the existing mutex group (D-07-10 mutex group preserved verbatim per D-08-11).
- Post-parse checks call `parser.error("...")`, which:
  1. Prints `usage: <prog> ...` to stderr (the parser's full usage line)
  2. Prints `<prog>: error: <msg>` to stderr
  3. Calls `sys.exit(2)`
  `[CITED: docs.python.org/3/library/argparse.html#argparse.ArgumentParser.error]`
- Test pattern with pytest:
  ```python
  with pytest.raises(SystemExit) as exc:
      main(["--ndjson", "--post-url", "https://x", "in.csv"])
  assert exc.value.code == 2
  captured = capsys.readouterr()
  assert "--ndjson cannot be combined with --post-url" in captured.err
  ```
- Negative-substring assertion (T-PII-01): assert no email/phone/name fixture appears in `captured.err`. Since the messages are categorical, this is structurally satisfied — but the test should still assert it, matching the v1.1 PII-safe test pattern.

The existing Phase 7 mutex group does NOT need restructuring — `--ndjson` is a peer flag. `[VERIFIED: 08-CONTEXT.md D-08-11]`

### Q10. README CLI-reference table drift test (D-11)

**Recommendation:** Add one row to the existing `## CLI reference` table. Do NOT add a new H2.

The drift test (`tests/test_readme_help_alignment.py` lines 53-63) extracts every long flag from `--help` via `re.findall(r"--[a-z][a-z0-9-]+", help_text)` and asserts each appears as a substring of the README. Adding `--ndjson` to argparse will cause the test to fail until README contains the literal string `--ndjson`.

**Required README delta:**
- Add to `## CLI reference` table a single row whose first column is `--ndjson` (so the substring match succeeds).
- Recommended row content:
  | Flag | Default | Description |
  |------|---------|-------------|
  | `--ndjson` | off (array mode) | Emit line-delimited JSON. Requires `-o/--output`; cannot combine with `--post-url`. With `--validate`, validates each row against `schema["items"]` and exits 1 on first failure with a categorical JSON Pointer. |
- Optional: one usage example near the existing `-o` example showing `python quizify_csv_ingest.py docs/quizify-submissions.csv -o out.ndjson --ndjson --validate`.
- Required H2 sections (`## Purpose`, `## Quickstart`, `## CLI reference`, `## Configuration`, `## Column assumptions`, `## Output shape`, `## Limitations`, `## Privacy notes`, `## Exit codes`, `## Development`) — count and presence unchanged. `[VERIFIED: tests/test_readme_help_alignment.py REQUIRED_SECTIONS]`

The drift test is subprocess-based (`subprocess.run([sys.executable, ..., "--help"])`) — Pitfall 16 has an existing exception for this test; it stays as-is.

## Architecture Patterns

### System Architecture (NDJSON path)

```
argv ── argparse parse_args ──┬── post-parse mutex check (--ndjson + --post-url) ── exit 2
                              ├── post-parse requires-output check (--ndjson alone) ── exit 2
                              └── convert(path, ..., ndjson=True, validate=?, output=Path)
                                      │
                                      ├── iter_rows(path, trailer, quiz_title) → _RowStream
                                      │
                                      ├── sink = _select_sink(args)
                                      │     │
                                      │     └── --ndjson + --output ──► _NdjsonFileSink(output)
                                      │           if --validate ──► _ValidatingSink(_NdjsonFileSink, SCHEMA_PATH)
                                      │
                                      └── with sink:                          ◄── __enter__ opens .tmp
                                              for row in stream:                   (or delegates to inner)
                                                  sink.write(row)              ◄── _ValidatingSink.write:
                                                                                   validate(row) → if fail
                                                                                   raise _RowValidationError
                                                                                   else inner.write(row)
                                          (normal exit) ──► __exit__ closes fp, os.replace(tmp, target)
                                          (any exception) ──► __exit__ closes fp, unlink(tmp), re-raise
                                          (KeyboardInterrupt) ──► same as exception path
```

### Sink Composition

`_ValidatingSink` is a transparent decorator: its `__enter__/__exit__/close` delegate to the wrapped inner sink. The CM lifecycle is therefore owned by `_NdjsonFileSink` regardless of validation wrapping — which is exactly what STREAM-04 needs (validation failure → `_RowValidationError` propagates → `_NdjsonFileSink.__exit__` sees `exc_type is _RowValidationError` → unlinks `.tmp` → target absent).

### Anti-Patterns to Avoid
- **Catching `_RowValidationError` inside `_ValidatingSink.write` and returning silently** — would prevent CM cleanup and leave `.tmp` on disk. The locked skeleton raises and lets `convert()` catch.
- **Calling `os.replace` outside `_NdjsonFileSink.__exit__`** — D-08-10 locks single promotion path. CI grep gate is recommended.
- **Adding `signal.signal(SIGINT, ...)`** — D-08-09 forbids; default `KeyboardInterrupt` propagation is sufficient.
- **Eagerly importing `fastjsonschema` at module top** — Pitfall 18; D-13 stdlib-at-runtime; existing lazy-import pattern preserved.
- **Forwarding `JsonSchemaValueException.message` or `str(err)` to stderr** — Pitfall 17; reuse `_format_validation_error`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Mkstemp + manual rename + sync logic | `os.replace` on a sibling `.tmp` | Already atomic on POSIX + Windows; stdlib |
| JSON encoding | Custom serializer for compact output | `json.dump(row, fp, ensure_ascii=False)` | Stdlib; matches v1.1 byte conventions |
| Per-row JSON schema validation | Python-level type checks | `fastjsonschema.compile(schema["items"])` | Compiled once, ~100x faster than re-parse per row |
| SIGINT cleanup | Custom signal handler | Default `KeyboardInterrupt` + `with` block | CPython delivers signal at bytecode boundary; `__exit__` runs |
| Argparse mutex extension | Restructure existing group | Peer flag + post-parse `parser.error()` | Argparse mutex groups don't support multi-flag conditional logic; post-parse is the idiomatic Python pattern |
| JSON Pointer formatting | New formatter | Existing `_format_validation_error` + row-index prefix | Already PII-safe (D-06-20) |

**Key insight:** Phase 8 is almost entirely composition of existing primitives. The two genuinely new classes (`_NdjsonFileSink`, `_ValidatingSink`) are <30 lines each per the locked skeletons. The temptation to "improve" beyond the locked shape (e.g., add `fsync`, use `tempfile`, install a SIGINT handler, build a custom validator) should be resisted — every such addition expands the test surface without buying a property in the SC list.

## Common Pitfalls (Phase-8-specific, beyond carry-forwards)

### Pitfall 8-A: `__exit__` swallowing the exception
**What goes wrong:** Returning a truthy value from `__exit__` suppresses the exception; the caller sees a clean exit and the target file is replaced with valid-looking but incomplete data.
**Why it happens:** Python convention can mislead — `contextmanager`-decorated generators have `yield` semantics that differ from raw `__exit__`.
**How to avoid:** Always `return False` (or no return — implicit `None` is falsy). The locked skeleton in 08-CONTEXT.md `<specifics>` already does this; planner must preserve.
**Warning signs:** A SIGINT or validation-failure test passes the "target absent" assertion but exit code is unexpectedly 0.

### Pitfall 8-B: Decorator `__exit__` not delegating to inner
**What goes wrong:** `_ValidatingSink.__exit__` doing its own cleanup logic instead of `return self._inner.__exit__(exc_type, exc, tb)` — `_NdjsonFileSink.__exit__` never runs, `.tmp` leaks, target may or may not get replaced.
**Why it happens:** Pattern is "decorator wraps behavior" → developer adds custom `__exit__` body.
**How to avoid:** Locked skeleton: `return self._inner.__exit__(exc_type, exc, tb)`. One line. Test: validation failure path asserts `.tmp` is gone after the run.
**Warning signs:** Stale `.tmp` files appear after test runs.

### Pitfall 8-C: Validating an already-encoded line
**What goes wrong:** Putting validation *after* `json.dump` (e.g., re-parsing the line and validating). Wastes CPU; also `fastjsonschema` validates Python dicts, not JSON strings.
**Why it happens:** Pipeline-of-bytes mental model.
**How to avoid:** `_ValidatingSink.write(row)` validates the dict, then delegates to inner which does the encoding. Locked in skeleton.

### Pitfall 8-D: `with_suffix` stripping multi-suffix paths
**What goes wrong:** `Path("out.ndjson").with_suffix(".tmp")` yields `out.tmp`, NOT `out.ndjson.tmp`. The locked form is `output.with_suffix(output.suffix + ".tmp")` which yields `out.ndjson.tmp` correctly.
**Why it happens:** `with_suffix` replaces the *final* suffix; appending to `output.suffix` is the workaround.
**How to avoid:** Use the locked form verbatim. Test: assert `tmp_path.name == output_path.name + ".tmp"` for at least one run.
**Warning signs:** `.tmp` cleanup test fails with "file not found" because the actual `.tmp` lives at a different path. `[CITED: docs.python.org/3/library/pathlib.html#pathlib.PurePath.with_suffix]`

### Pitfall 8-E: NDJSON exit code conflated with row-length-mismatch exit code
**What goes wrong:** `_RowStream.exit_code` accumulates `|= 1` on row-length mismatches. `_RowValidationError` also exits 1. A test asserting "exit 1 because row 50 was malformed" might be passing for a different reason (row-length mismatch on a different row).
**Why it happens:** Both signals collapse to the same exit code (D-06-21 lock).
**How to avoid:** Tests on STREAM-03 should assert *both* the exit code AND a categorical-substring match on stderr (`"schema validation failed at /50/"`) to disambiguate.

## Code Examples

### NDJSON happy-path test (locked skeleton, planner adapts)
```python
def test_ndjson_happy_path(tmp_path: Path, capsys) -> None:
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    assert out.exists()
    # No \r anywhere
    raw = out.read_bytes()
    assert b"\r" not in raw
    # One trailing newline; line count == row count
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == EXPECTED_ROW_COUNT
    # Each line round-trips
    rows = [json.loads(line) for line in lines]
    # Structural equivalence to v1.1 golden array
    golden = json.loads(GOLDEN_ARRAY_PATH.read_text(encoding="utf-8"))
    assert rows == golden  # D-05 tail-key order preserved by build_row
```

### Validation-failure cleanup test
```python
def test_ndjson_validation_failure_no_target(tmp_path: Path, capsys) -> None:
    csv_path = _make_csv_with_bad_row_at(tmp_path, idx=50)
    out = tmp_path / "out.ndjson"
    rc = main([str(csv_path), "-o", str(out), "--ndjson", "--validate"])
    assert rc == 1
    assert not out.exists()  # STREAM-04 invariant on target
    err = capsys.readouterr().err
    assert "/50/" in err  # row-prefixed JSON Pointer
    # T-PII-01: no email/phone/free-text from synthetic fixture
    for pii_token in SYNTHETIC_PII_TOKENS:
        assert pii_token not in err
```

### SIGINT subprocess test (Pitfall 16 justified exception)
```python
def test_ndjson_sigint_no_target(tmp_path: Path) -> None:
    out = tmp_path / "out.ndjson"
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), str(LARGE_SAMPLE_CSV),
         "-o", str(out), "--ndjson"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(0.05)  # let it start writing
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=10)
    assert proc.returncode != 0
    assert not out.exists()  # STREAM-04 invariant
```

## Validation Architecture

> Phase 8 sits squarely under Nyquist validation. `workflow.nyquist_validation` config not located in this repo; treating as enabled per default.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing); stdlib `unittest` patterns also accepted |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing from v1.1) |
| Quick run command | `pytest quizify-csv-to-json-webhook/tests/ -x` |
| Full suite command | `pytest quizify-csv-to-json-webhook/tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| STREAM-01 | `--ndjson + -o file.ndjson` writes line-delimited file | integration | `pytest tests/test_ndjson.py::test_ndjson_happy_path -x` | ❌ Wave 0 |
| STREAM-01 | `--ndjson + --post-url` rejected at argparse exit 2 | unit | `pytest tests/test_ndjson.py::test_ndjson_rejects_post_url -x` | ❌ Wave 0 |
| STREAM-01 | `--ndjson` without `-o` rejected at argparse exit 2 | unit | `pytest tests/test_ndjson.py::test_ndjson_requires_output -x` | ❌ Wave 0 |
| STREAM-02 | No `\r` bytes in output; one trailing `\n` per row | unit (byte-level) | `pytest tests/test_ndjson.py::test_no_carriage_returns -x` | ❌ Wave 0 |
| STREAM-02 | Line count equals row count | integration | `pytest tests/test_ndjson.py::test_line_count_matches_rows -x` | ❌ Wave 0 |
| STREAM-03 | Per-row validation; first failure exits 1 with categorical pointer | integration | `pytest tests/test_ndjson.py::test_per_row_validation_failure -x` | ❌ Wave 0 |
| STREAM-03 | `_ValidatingSink` raises `_RowValidationError` at first failure | unit | `pytest tests/test_ndjson.py::test_validating_sink_raises -x` | ❌ Wave 0 |
| STREAM-03 | T-PII-01 negative-substring on per-row failure stderr | unit | `pytest tests/test_ndjson.py::test_per_row_failure_pii_safe -x` | ❌ Wave 0 |
| STREAM-04 | Atomic write: target appears only on success | integration | `pytest tests/test_ndjson.py::test_atomic_replace_on_success -x` | ❌ Wave 0 |
| STREAM-04 | Validation failure → target absent | integration | `pytest tests/test_ndjson.py::test_validation_failure_no_target -x` | ❌ Wave 0 |
| STREAM-04 | SIGINT mid-stream → target absent (subprocess) | subprocess | `pytest tests/test_ndjson.py::test_sigint_no_target -x` | ❌ Wave 0 |
| STREAM-04 | KeyboardInterrupt mid-write → `__exit__` cleanup (unit) | unit | `pytest tests/test_ndjson.py::test_keyboard_interrupt_cleanup -x` | ❌ Wave 0 |
| Regression | TRAIL-03 byte-identity unchanged | regression | `pytest tests/test_default_order_regression.py -x` | ✅ |
| Regression | D-11 README drift 2/2 green | regression | `pytest tests/test_readme_help_alignment.py -x` | ✅ |
| Regression | All v1.1 + Phase 7 tests still pass | regression | `pytest tests/` | ✅ (111 tests at Phase 7 close) |

### Sampling Rate
- **Per task commit:** `pytest quizify-csv-to-json-webhook/tests/ -x`
- **Per wave merge:** `pytest quizify-csv-to-json-webhook/tests/ -v` (full suite, no `-x`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ndjson.py` — covers STREAM-01..04 (planner may split into `test_ndjson.py` + `test_atomic_write.py` per D-08 discretion)
- [ ] Synthetic 100-row CSV factory in `conftest.py` (or fixture-local helper) — `_make_csv_with_bad_row_at(tmp_path, idx)`
- [ ] PII-token list for negative-substring tests — extend the existing PII-safe pattern from `tests/test_logging_pii.py`
- [ ] Framework install: none — pytest + fastjsonschema already present

### Validation Tier Coverage
- **Unit-level:** `_NdjsonFileSink.__exit__` cleanup (success + exception + KeyboardInterrupt branches); `_ValidatingSink.write` raise behavior; argparse rejections; JSON-Pointer formatting helper.
- **Integration-level:** Full `convert()` invocation with NDJSON sink + golden CSV; structural compare against v1.1 array via `[json.loads(line) for line in lines] == golden_list`.
- **Subprocess-level:** SIGINT mid-stream test (Pitfall 16 justified). Use `proc.send_signal(signal.SIGINT)` after a brief delay; assert `not out.exists()` after `proc.wait()`.
- **Regression-level:** TRAIL-03 byte-identity, D-11 README drift, D-06-19/20/21 stderr templates and exit codes — all run unchanged.

## Risks & Pitfalls

### Phase-8-specific risks (beyond carry-forwards)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `with_suffix` misuse strips `.ndjson` → wrong `.tmp` path | LOW | MEDIUM (test breaks late) | Use locked `output.with_suffix(output.suffix + ".tmp")`; assertion in unit test |
| Decorator `__exit__` not delegating → `.tmp` leaks | MEDIUM | LOW (cosmetic — STREAM-04 only constrains target) | Test: `.tmp` absent after validation-failure run |
| Per-row validation re-compiling schema per row | LOW | MEDIUM (50k-row slowdown) | Locked: compile once in `__init__`; assert via mock that `fastjsonschema.compile` called exactly once |
| SIGINT race during `os.replace` | LOW | LOW (target either complete or absent — both fine) | Documented in research; no code mitigation |
| PII leak via `JsonSchemaValueException.message` | LOW (Pitfall 17 lock) | HIGH (T-PII-01 violation) | Locked: reuse `_format_validation_error`; negative-substring test |
| README drift test fails when `--ndjson` added | CERTAIN | LOW (caught immediately) | Add `--ndjson` row to `## CLI reference` in same commit |
| Non-NDJSON sink `__exit__` discriminates on `exc_type` and breaks v1.1 byte-identity | MEDIUM | HIGH (TRAIL-03 fail) | Per 08-CONTEXT.md "Claude's Discretion": keep non-NDJSON `__exit__` calling `close()` always (matches today's behavior); only `_NdjsonFileSink` discriminates |
| Test fixture leaks PII into git | LOW | HIGH | Synthetic-only fixtures generated in `tmp_path`; never committed |

### Carry-forward risks (verify, don't re-mitigate)
- T-PII-01: locked, verified by negative-substring tests
- D-13: locked, no new runtime imports (fastjsonschema is the existing optional dep)
- D-11: locked, drift test catches violations
- TRAIL-03: locked, byte-identity test stays green

## Test Strategy (file-by-file, mapped to STREAM-01..04)

**Recommended file layout** (planner discretion per D-08-14):
- `tests/test_ndjson.py` — all five STREAM-01..04 surfaces + per-row validation + argparse rejections
- `tests/conftest.py` — extend with `_make_csv_with_bad_row_at(tmp_path, idx)` fixture factory and `SYNTHETIC_PII_TOKENS` list
- (No new file for atomic-write — keep co-located with NDJSON tests)

**Test-by-test mapping to success criteria:**

| Test name | SC | Tier | What it locks |
|-----------|----|----|---------------|
| `test_ndjson_happy_path` | SC#1 (line count + `\n` only + jq -s array equiv) | integration | STREAM-01 + STREAM-02 happy path |
| `test_no_carriage_returns` | SC#1 | unit (byte-level) | STREAM-02 newline contract |
| `test_jq_s_array_equivalence` | SC#1 | integration | NDJSON ↔ v1.1 array structural equality |
| `test_per_row_validation_failure_no_target` | SC#2 | integration | STREAM-03 + STREAM-04 (target absent on validation fail) |
| `test_validating_sink_raises_at_first_failure` | SC#2 | unit | `_ValidatingSink` mechanic |
| `test_per_row_failure_pii_safe` | SC#2 | unit | T-PII-01 carry-forward on new surface |
| `test_ndjson_rejects_post_url` | SC#3 (argparse rejection) | unit | STREAM-01 mutex |
| `test_ndjson_requires_output` | SC#3 (argparse rejection) | unit | STREAM-01 file-only |
| `test_argparse_rejection_pii_safe` | SC#3 | unit | T-PII-01 on argparse stderr |
| `test_sigint_no_target` | SC#4 (SIGINT) | subprocess (Pitfall 16 justified) | STREAM-04 real-signal |
| `test_keyboard_interrupt_cleanup` | SC#4 | unit | `__exit__` cleanup logic isolated from signal delivery |
| `test_atomic_tmp_path_naming` | SC#4 (atomic) | unit | D-08-04 `.tmp` naming contract |
| `test_default_array_byte_identity` (existing) | SC#5 (regression) | regression | TRAIL-03 stays green |
| `test_readme_help_alignment` (existing) | SC#5 | regression | D-11 stays green |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `json.dump` and `json.dumps + write` have negligible perf difference at 50k rows | Q2 | LOW — both are O(row_bytes); even 2x diff is sub-second at this scale |
| A2 | SIGINT during `fp.close()` falls into `__exit__(KeyboardInterrupt, ...)` deterministically | Q6 edge case 1 | LOW — CPython signal-at-bytecode-boundary semantics are documented; worst case is target file appears (success branch ran), which is acceptable per STREAM-04 wording |
| A3 | RFC 6901 array-rooted `/<idx><pointer>` form is the most greppable + spec-aligned format | Q5 | LOW — alternatives are equally valid; this is a discretion call with weak preference |
| A4 | Synthetic fixture row malformation is easier via direct `_ValidatingSink` injection than via CSV → `build_row` damage | Q8 | MEDIUM — if planner finds a clean CSV-side malformation that's robust, that's a stronger integration test. The unit-level approach is the fallback. |

**Empty/non-empty:** A1, A2, A3 are LOW-risk. A4 should be re-examined during planning — if the planner identifies a clean CSV-mutation that violates `schema["items"]` while passing `build_row`, that's preferred for the STREAM-03 integration test.

## Open Questions

1. **Optimal CSV-side malformation for STREAM-03 integration test**
   - What we know: `build_row` always returns structurally complete dicts; `shape_answer` returns string-or-list; row-length mismatch path skips rows entirely.
   - What's unclear: Whether there's a CSV input that survives `_RowStream.__iter__` validation but produces a `build_row` output that violates `schema["items"]`.
   - Recommendation: Start with `_ValidatingSink` unit-level injection for the validation mechanic; if CSV-end-to-end is desired, planner can experiment in TDD-RED with a row whose `Subscribed to newsletter` value triggers an unusual `map_status` path, OR use a test-only monkeypatch on `build_row` for one row index.

2. **Whether `--ndjson` warrants a usage-section README example**
   - What we know: D-11 forbids new H2; existing `## CLI reference` table accepts new rows; existing `## Quickstart` has examples.
   - What's unclear: Whether to add a `--ndjson` example to Quickstart or just to the table.
   - Recommendation: Add a brief one-line example to `## Quickstart` AND a row to `## CLI reference`. Both stay within existing sections (D-11 preserved).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | ≥3.9 (D-06-03 floor) | — |
| pytest | Tests | ✓ | existing | — |
| fastjsonschema | `--validate` per-row | ✓ (in `[validate]` extra) | existing | — |
| jq | Optional integration test | not required | — | Stdlib `json.loads` per line is sufficient |
| `os.replace`, `os.unlink` | NDJSON atomic write | ✓ (stdlib) | — | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `jq` (replaced by `[json.loads(line) for line in lines]` in tests — no shell dependency).

## Sources

### Primary (HIGH confidence)
- Python stdlib docs: `os.replace`, `pathlib.Path.with_suffix`, `argparse.ArgumentParser.error`, `open(newline=...)`, `json.dump` — all CITED inline.
- RFC 6901 (JSON Pointer §4) — array-index path tokens.
- Existing repo code (VERIFIED inline):
  - `quizify-csv-to-json-webhook/quizify_csv_ingest.py` lines 49-102 (sinks), 110-185 (`_RowStream`/`iter_rows`), 484-501 (`_format_validation_error`), 504-549 (`_run_schema_validation`), 553-587 (`convert`), 590-637 (`main`/argparse).
  - `quizify-csv-to-json-webhook/docs/webhook-schema.json` lines 6-60 (schema root + `items`).
  - `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` (drift contract).
- 08-CONTEXT.md `<decisions>` D-08-01..15 (locked).
- 07-CONTEXT.md `<decisions>` D-07-01..16 (carry-forward).
- 06-CONTEXT.md (referenced for D-06-2x).
- `.planning/research/PITFALLS.md` Pitfalls 6, 7, 8, 13, 16, 17, 18 — Phase-8-relevant.

### Secondary (MEDIUM confidence)
- None — no WebSearch or external docs needed; all decisions verifiable in repo + Python docs.

### Tertiary (LOW confidence)
- A1, A2, A3, A4 in Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entirely stdlib + existing optional dep
- Architecture: HIGH — locked in 08-CONTEXT.md; reuses Phase 7 sink shape
- Pitfalls: HIGH — Pitfalls 6/7/8 from v1.2 research directly map; Phase-8-specific 8-A..E derive from locked skeletons

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (stable stdlib semantics; no fast-moving deps)

## RESEARCH COMPLETE
