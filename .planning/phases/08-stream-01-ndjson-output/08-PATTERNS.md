# Phase 8: STREAM-01 NDJSON Output — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 5 (1 prod EDIT, 1 README EDIT, 3 NEW test surfaces)
**Analogs found:** 5 / 5 (all Phase 6/7 in-repo)

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (EDIT — sinks + decorator + sentinel + argparse + convert rewrite) | controller / sink layer / argparse / validation primitive | streaming + file-I/O + transform + request-response (CLI) | self (Phase 7 sinks at lines 49-102; `_run_schema_validation` at 504-550; argparse at 590-637; `convert` at 553-587) | exact (extending the same module, in-repo carry-forward) |
| `quizify-csv-to-json-webhook/README.md` (EDIT — `## CLI reference` row + Quickstart line) | docs (drift contract) | static — feeds the `--help`↔README drift test | existing `## CLI reference` table; existing `--validate` / `--post-url` / `-o` rows | exact (table-row addendum only; D-11 H2 lock) |
| `tests/test_ndjson.py` (NEW — happy path + STREAM-02 byte tests + jq-s array equivalence) | test (integration + unit byte-level) | request-response (CLI via `main(...)`) → file artifact | `tests/test_default_order_regression.py::test_phase7_refactor_byte_identical_to_v1_0_baseline` (lines 55-77 — capsys + `convert()` + golden compare) | exact |
| `tests/test_ndjson_validation.py` (NEW — `_ValidatingSink` unit + per-row failure + T-PII-01 negative-substring) | test (unit) | function-level fastjsonschema | `tests/test_schema_validation.py::TestValidationFailurePIIsafe` (lines 81-180) | exact |
| `tests/test_atomic_write.py` (NEW — `_NdjsonFileSink` `__exit__` cleanup; `with_suffix` `.tmp`; SIGINT subprocess + KeyboardInterrupt unit) | test (unit + subprocess) | file-I/O (atomicity) + signal | `tests/test_default_order_regression.py::test_default_order_byte_identical_to_v1_0_baseline` (lines 26-52, subprocess form); `tests/test_sink_layer.py` for unit-level CM patterns | role-match (only-allowed-subprocess form is the SIGINT exception per Pitfall 16) |
| `tests/conftest.py` (EXTEND — synthetic 100-row CSV factory; `SYNTHETIC_PII_TOKENS`) | fixture | test data factory | existing `conftest.py` lines 14-117 (per-row dict fixtures) | role-match |
| `tests/test_sink_layer.py` (OPTIONAL EXTEND — `_select_sink(args)` extension + 4-branch dispatch) | test (unit) | function-call dispatch | self lines 99-108 (`_select_sink` 3-branch dispatch) | exact |

## Pattern Assignments

### `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — sinks + decorator + sentinel

**Analogs (in-file):**
- `_StdoutSink` / `_FileSink` / `_HttpPostSink` lines 54-93 (existing 3 sinks — same module; gain `__enter__/__exit__` shims, bodies untouched)
- `_select_sink` lines 96-102 (extension point — gains `--ndjson` branch + optional `_ValidatingSink` wrap)
- `_run_schema_validation` + `_format_validation_error` lines 484-550 (lazy import + compile-once + categorical formatter — `_ValidatingSink` reuses pattern + reuses formatter directly)
- `convert` lines 553-587 (sink construction + `try/finally close()` — rewrite to `with sink:` + add NDJSON streaming branch that does NOT materialize via `list(...)`)
- `main` argparse lines 590-637 (existing mutex group + post-parse `parse_trailer_arg` error path — model for `--ndjson` peer flag + post-parse `parser.error` checks)

**Sink Protocol shape — copy from `_FileSink` lines 67-80:**
```python
class _FileSink:
    def __init__(self, output: Path) -> None:
        self._output = output
        self._rows: list[dict] = []

    def write(self, row: dict) -> None:
        self._rows.append(row)

    def close(self) -> None:
        with self._output.open("w", encoding="utf-8") as out_fh:
            json.dump(self._rows, out_fh, indent=2, ensure_ascii=False)
            out_fh.write("\n")
```
**Differences for `_NdjsonFileSink`:** no row buffering (`self._rows` removed); `__init__` only computes paths (does NOT open file); `__enter__` opens `.tmp` with `newline="\n"`; `write` does `json.dump(row, fp, ensure_ascii=False) + fp.write("\n")` (no `indent=2` — NDJSON is compact); `__exit__` closes fp and either `os.replace` (success) or `os.unlink` (exception); `close()` no-op for Protocol compliance. Use locked skeleton from CONTEXT §"Specifics" verbatim.

**`__enter__/__exit__` shim for existing 3 sinks (D-08-03)** — apply to `_StdoutSink`, `_FileSink`, `_HttpPostSink`:
```python
def __enter__(self):
    return self
def __exit__(self, exc_type, exc, tb):
    self.close()  # always emit on close — preserves v1.1 byte-identity for non-NDJSON modes
    return False
```
Critical: non-NDJSON sinks call `close()` UNCONDITIONALLY (matches today's `try/finally close()` at convert lines 582-586). Only `_NdjsonFileSink.__exit__` discriminates on `exc_type` (D-08 Discretion last bullet, also Risks table row 7).

**Lazy-import + compile-once for `_ValidatingSink.__init__`** — copy pattern from `_run_schema_validation` lines 520-538:
```python
try:
    import fastjsonschema  # lazy, D-13 / D-06-17 / Pitfall 18
except ImportError:
    print(
        "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'",
        file=sys.stderr,
    )
    return 1   # in convert()-level wiring, not in _ValidatingSink.__init__
schema = json.loads(schema_path.read_text(encoding="utf-8"))
validator = fastjsonschema.compile(schema)  # D-08-08: pass schema["items"] in NDJSON path
```
**Differences for `_ValidatingSink`:** compile `schema["items"]` (not full schema); ImportError handling stays in `convert()` / wiring layer (NOT inside `__init__`) so the missing-extra D-06-19 template path stays single-sourced. Reuse `_format_validation_error` for the per-row pointer message.

**Categorical PII-safe formatter — reuse line 484-501 verbatim (no edits):**
```python
def _format_validation_error(err) -> str:
    pointer = "/" + "/".join(err.path[1:]) if len(err.path) > 1 else "/"
    expected = (err.definition or {}).get("type", "<unknown>")
    if isinstance(expected, list):
        expected = "|".join(expected)
    actual = type(err.value).__name__
    return f"ERROR schema validation failed at {pointer}: expected {expected}, got {actual}"
```
**For per-row mode:** prepend row index per RFC 6901 — research recommends extending `_format_validation_error(err, row_idx=None)` and substring-replacing the leading `/` with `/<idx>/`, OR post-processing in `_ValidatingSink.write` before raising. Final stderr template: `ERROR schema validation failed at /49/answers-3: expected string, got NoneType` (research §Q5).

**Sentinel exception (D-08-06):** new module-private class. Carries `row_index: int` + `pointer_message: str`. Caught in `convert()` → log + return 1.

**Argparse extension — copy mutex pattern from lines 597-601, add peer flag and post-parse checks (locked skeleton, CONTEXT §"Specifics"):**
```python
# Existing Phase 7 mutex group untouched (lines 597-601):
group = parser.add_mutually_exclusive_group()
group.add_argument("-o", "--output", type=Path, default=None, help="...")
group.add_argument("--post-url", default=None, help="...")

# NEW peer flag (outside group):
parser.add_argument("--ndjson", action="store_true",
    help="Emit line-delimited JSON; requires -o/--output, mutually exclusive with --post-url.")

args = parser.parse_args(argv)

# NEW post-parse checks (after parse_args, before convert()):
if args.ndjson and args.post_url:
    parser.error("--ndjson cannot be combined with --post-url")  # exit 2
if args.ndjson and not args.output:
    parser.error("--ndjson requires -o/--output (no stdout NDJSON)")  # exit 2
```
Note: `parser.error()` is the same exit-2 pathway as the existing trailer-columns error (lines 622-627 use `print + return 2` — the new checks use the more idiomatic `parser.error` per CONTEXT D-08-11 lock).

**`convert()` rewrite — model the NDJSON branch on the array branch's existing structure (lines 553-587):**
- Keep array-mode path (`results = list(stream)` line 564 + batch `_run_schema_validation` line 577 + non-CM `try/finally sink.close()` line 582-586) — UNCHANGED so TRAIL-03 stays green.
- New NDJSON branch: NO `list(...)` materialization; `with sink: for row in iter_rows(...): sink.write(row)`. Validation wrapping happens at sink construction (in `_select_sink`), not inside the loop.
- Catch `_RowValidationError` at `convert()` level → print already-formatted message via `logging.error` (or `print(..., file=sys.stderr)` to match `_run_schema_validation` line 547) → return 1.

**`_select_sink` extension (D-07-11 / D-08-12):**
- Today: `_select_sink(output, post_url) -> _Sink` (lines 96-102, 3-branch).
- New shape (planner's discretion — recommend `_select_sink(args)` to avoid 5-arg explosion): 4-branch dispatch in this order: `--post-url` → `_HttpPostSink`; `--ndjson + --output` → `_NdjsonFileSink(output)` optionally wrapped by `_ValidatingSink(inner, SCHEMA_PATH)` when `--validate`; `--output` (no `--ndjson`) → `_FileSink`; else → `_StdoutSink`.

---

### `quizify-csv-to-json-webhook/README.md` — `## CLI reference` table row + Quickstart line

**Analog:** existing `## CLI reference` table (locked H2) + existing `--validate` / `--post-url` rows.

**Drift-test contract** — `tests/test_readme_help_alignment.py` lines 53-63:
```python
flags = set(re.findall(r"--[a-z][a-z0-9-]+", help_text))
flags.discard("--help")
readme = _readme_text()
missing = sorted(f for f in flags if f not in readme)
assert not missing, ...
```
Adding `--ndjson` to argparse → README must contain literal substring `--ndjson` or test fails. Add ONE row to `## CLI reference` table; optionally one usage example to `## Quickstart`. NO new H2 (D-11). REQUIRED_SECTIONS list at lines 18-29 of the drift test must remain unchanged.

---

### `tests/test_ndjson.py` (NEW) — STREAM-01 + STREAM-02 happy path

**Analog:** `tests/test_default_order_regression.py::test_phase7_refactor_byte_identical_to_v1_0_baseline` lines 55-77 (capsys + `convert()` + golden-array compare).

**Imports / structure pattern (copy from analog):**
```python
from __future__ import annotations
import json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
GOLDEN = ROOT / "tests" / "fixtures" / "v1.0_default_order_output.json"
```

**Happy-path test pattern (from research §"Code Examples"):**
```python
def test_ndjson_happy_path(tmp_path: Path) -> None:
    out = tmp_path / "out.ndjson"
    rc = main([str(FIXTURE), "-o", str(out), "--ndjson"])
    assert rc == 0
    raw = out.read_bytes()
    assert b"\r" not in raw                                  # STREAM-02 byte-level
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 42                                   # row count
    rows = [json.loads(line) for line in lines]
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert rows == golden                                     # D-05 tail-key order via build_row
```

**Argparse rejection tests (T-PII-01 + exit 2)** — copy `pytest.raises(SystemExit)` + `capsys` pattern from research §Q9:
```python
def test_ndjson_rejects_post_url(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--ndjson", "--post-url", "https://x", "in.csv"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--ndjson cannot be combined with --post-url" in err
```

---

### `tests/test_ndjson_validation.py` (NEW) — STREAM-03 + T-PII-01

**Analog:** `tests/test_schema_validation.py::TestValidationFailurePIIsafe` lines 81-180.

**PII-leak negative-substring pattern — copy from `test_failure_stderr_does_not_leak_cell_content` lines 144-163:**
```python
leak_email = "leak@example.com"
leak_phone = "+52 55 9999 9999"
leak_name = "LeakageName"
# ...run path that triggers _ValidatingSink failure...
err = capsys.readouterr().err
assert leak_email not in err
assert leak_phone not in err
assert leak_name not in err
assert "data[" not in err   # raw err.path leak guard
```

**JSON-Pointer form assertion — adapt from `test_failure_pointer_uses_json_pointer_form` lines 165-180 to assert row-prefixed form:**
```python
m = re.match(r"^ERROR schema validation failed at (\S+):", err)
pointer = m.group(1)
assert pointer.startswith("/50/")   # row-prefix per RFC 6901 (research §Q5)
```

**`_ValidatingSink` unit test — direct injection pattern (research §Q8 Option C):**
```python
def test_validating_sink_raises_at_first_failure(tmp_path):
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import _ValidatingSink, _NdjsonFileSink, _RowValidationError, SCHEMA_PATH
    inner = _NdjsonFileSink(tmp_path / "out.ndjson")
    sink = _ValidatingSink(inner, SCHEMA_PATH)
    bad_row = {"email": 12345}  # wrong type on required field
    with sink:
        with pytest.raises(_RowValidationError):
            sink.write(bad_row)
    # STREAM-04 invariant — target absent
    assert not (tmp_path / "out.ndjson").exists()
```

---

### `tests/test_atomic_write.py` (NEW) — STREAM-04 + Pitfall 8-D

**Analogs:** `tests/test_default_order_regression.py::test_default_order_byte_identical_to_v1_0_baseline` lines 26-52 (subprocess form); `tests/test_sink_layer.py::test_select_sink_*` lines 99-108 (unit isinstance pattern).

**`with_suffix` `.tmp` naming assertion (Pitfall 8-D):**
```python
def test_atomic_tmp_path_naming():
    from quizify_csv_ingest import _NdjsonFileSink
    sink = _NdjsonFileSink(Path("out.ndjson"))
    assert sink._tmp.name == "out.ndjson.tmp"   # NOT "out.tmp"
```

**KeyboardInterrupt unit test — fake-sink pattern (research §Q6 unit form):**
```python
def test_keyboard_interrupt_cleanup(tmp_path):
    out = tmp_path / "out.ndjson"
    sink = _NdjsonFileSink(out)
    with pytest.raises(KeyboardInterrupt):
        with sink:
            sink.write({"email": "x"})
            raise KeyboardInterrupt
    assert not out.exists()         # STREAM-04 target invariant
    assert not (out.parent / "out.ndjson.tmp").exists()  # cleanup confirmed
```

**SIGINT subprocess test — copy subprocess pattern from `test_default_order_byte_identical_to_v1_0_baseline` lines 32-38:**
```python
import subprocess, signal, sys, time
proc = subprocess.Popen(
    [sys.executable, str(SCRIPT), str(LARGE_CSV), "-o", str(out), "--ndjson"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
time.sleep(0.05)
proc.send_signal(signal.SIGINT)
proc.wait(timeout=10)
assert proc.returncode != 0
assert not out.exists()
```
Pitfall 16 justified exception: SIGINT delivery cannot be unit-tested cleanly (D-08-14 surface 4).

---

### `tests/conftest.py` (EXTEND) — synthetic 100-row CSV factory

**Analog:** existing `conftest.py` lines 14-117 (fixture style — `tmp_path` consumers; per-row dict fixtures).

**New fixture pattern (research §Q8):**
```python
SYNTHETIC_PII_TOKENS = (
    "synth-name-50", "555-0100", "synth-50@example.test",
    # any token used in the synthetic row 50 cells
)

@pytest.fixture
def csv_with_bad_row_at_50(tmp_path: Path) -> Path:
    rows = [",".join(EXPECTED_HEADER)]
    for i in range(100):
        rows.append(_synthetic_row(i, malformed=(i == 50)))
    p = tmp_path / "synthetic.csv"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p
```
No PII checked into git; all data generated in `tmp_path`.

---

## Shared Patterns

### Lazy-Import Optional Dependency (D-13 / D-06-17 / Pitfall 18)
**Source:** `quizify_csv_ingest.py:520-528` (`_run_schema_validation`)
**Apply to:** `_ValidatingSink.__init__` only (NDJSON-mode validation primitive)
```python
try:
    import fastjsonschema  # lazy
except ImportError:
    print("ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'",
          file=sys.stderr)
    return 1
```
**Critical:** keep the ImportError handling at the wiring layer (`convert()` or `_select_sink`), NOT inside `_ValidatingSink.__init__`. The D-06-19 template lives once.

### PII-Safe Categorical stderr (T-PII-01 / Pitfall 17 / D-06-20)
**Source:** `quizify_csv_ingest.py:484-501` (`_format_validation_error`)
**Apply to:** every new stderr surface — `_RowValidationError` formatting, argparse rejections.
**Rule:** NEVER use `err.message` / `err.value` / `str(err)` / cell content. Only `err.path`, `(err.definition or {}).get("type")`, `type(err.value).__name__`. Reuse the function directly; do not re-implement.

### Compile-Once Validator (D-06-18)
**Source:** `quizify_csv_ingest.py:537-548` (`_run_schema_validation`)
**Apply to:** `_ValidatingSink.__init__` — `fastjsonschema.compile(schema["items"])` exactly once per instance; held on `self._validate_one`. Test gate: assert via mock that `fastjsonschema.compile` is called exactly once across an N-row run.

### Single-File Module Discipline (D-06-04 / D-08 carry-forward)
**Source:** `quizify_csv_ingest.py` whole file — Phase 7 sinks live as private module classes (lines 49-102), Phase 6 validation lives as private module functions (lines 484-550).
**Apply to:** `_NdjsonFileSink`, `_ValidatingSink`, `_RowValidationError` all live in the same file. No new module created.

### Argparse Mutex + Post-Parse Validation (D-07-10 / D-08-11)
**Source:** `quizify_csv_ingest.py:597-601` (existing mutex group); `quizify_csv_ingest.py:622-627` (existing trailer post-parse error).
**Apply to:** `--ndjson` peer flag + 2 `parser.error(...)` calls. The new errors use `parser.error` (research §Q9 idiomatic) which exits 2 — same exit code as the existing pattern.

### Subprocess Test Pattern (Pitfall 16 justified exceptions only)
**Source:** `tests/test_default_order_regression.py:32-38`; `tests/test_readme_help_alignment.py:36-44`.
**Apply to:** SIGINT mid-stream test ONLY. All other Phase 8 tests stay unit-level (capsys + `pytest.raises(SystemExit)` + direct `_ValidatingSink` injection).

### Capsys + `pytest.raises(SystemExit)` for Argparse Tests
**Source:** `tests/test_sink_layer.py:63-68` (`test_argparse_output_post_url_mutex_rejection`).
```python
with pytest.raises(SystemExit) as excinfo:
    main(["-o", "out.json", "--post-url", "https://y", "in.csv"])
assert excinfo.value.code == 2
```
**Apply to:** `test_ndjson_rejects_post_url`, `test_ndjson_requires_output`. Add `capsys.readouterr().err` substring assertions (T-PII-01 negative-substring + categorical message present).

## No Analog Found

| File / Pattern | Role | Why no in-repo analog |
|---|---|---|
| Context-manager sink (`__enter__/__exit__` discriminating on `exc_type`) | sink (CM lifecycle owner) | No existing CM sinks. Pattern comes from CONTEXT.md §"Specifics" locked skeleton + `os.replace`/`os.unlink` stdlib semantics (research §Q1, Q6). |
| `os.replace` atomic-promote test (success path produces target only after `__exit__`) | test (atomicity invariant) | No prior atomic-write test in suite. Drive purely from STREAM-04 contract: target appears iff success branch ran. |
| `_RowValidationError` sentinel propagating through nested `with` blocks | sentinel exception | No prior nested-CM exception flow. Behavior locked in CONTEXT D-08-06 + Pitfall 8-A/8-B. |

Planner: for these, follow CONTEXT §"Specifics" locked skeletons and research §Q1/Q5/Q6 verbatim — no codebase pattern to copy.

## Metadata

**Analog search scope:**
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (full file, 642 lines)
- `quizify-csv-to-json-webhook/tests/conftest.py`
- `quizify-csv-to-json-webhook/tests/test_sink_layer.py` (Phase 7 sinks + argparse mutex)
- `quizify-csv-to-json-webhook/tests/test_schema_validation.py` (Phase 6 validation + PII)
- `quizify-csv-to-json-webhook/tests/test_default_order_regression.py` (TRAIL-03 + Phase 7 byte-identity twin)
- `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` (D-11 drift contract)

**Files scanned:** 6 (production + tests). No external analogs needed — Phase 8 composes existing Phase 6/7 primitives.

**Pattern extraction date:** 2026-05-05
