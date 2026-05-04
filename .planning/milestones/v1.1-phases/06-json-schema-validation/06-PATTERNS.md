# Phase 6: JSON Schema Validation - Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 5 (3 CREATE, 2 EDIT)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Action | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `quizify-csv-to-json-webhook/pyproject.toml` | CREATE | packaging-config | declarative metadata | `confluence-to-markdown/pyproject.toml` | role-match (sibling flit_core; differs on dependencies vs optional-dependencies) |
| `quizify-csv-to-json-webhook/docs/webhook-schema.json` | CREATE | static asset (schema) | declarative contract | `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` | shape-reference (target shape; not a schema itself) |
| `quizify-csv-to-json-webhook/tests/test_schema_validation.py` | CREATE | test (unit, pytest classes) | request-response (helper-direct) | `tests/test_layout.py::TestScoringIndexMap` (class style), `tests/test_logging_pii.py` (PII assertion idiom), `tests/test_default_order_regression.py` (the one allowed subprocess smoke) | role-match (closest existing test analogs) |
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` | EDIT | CLI runtime + helper | request-response (argparse → convert → json.dump) | self (additive edits inside `convert()` and `main()` argparse block) | exact (mirror existing patterns) |
| `quizify-csv-to-json-webhook/README.md` | EDIT | static doc asset | n/a | self (existing `## CLI reference` table + `## Quickstart`) | exact (extend in place; D-11 lock) |

---

## Pattern Assignments

### `quizify-csv-to-json-webhook/pyproject.toml` (NEW — packaging metadata)

**Analog:** `confluence-to-markdown/pyproject.toml` (lines 1-21)

**Build-backend pattern to MIRROR verbatim** (lines 18-20):
```toml
[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"
```

**Project-table pattern to ADAPT** (lines 1-16):
```toml
[project]
name = "confluence-to-md"
version = "0.1.0"
description = "Confluence Space to Markdown exporter"
authors = [{name = "User", email = "user@example.com"}]
dependencies = [...]                # <-- DIVERGE: must be ABSENT or empty (Pitfall 20)
requires-python = ">=3.8"           # <-- DIVERGE: must be ">=3.9" (D-06-03)
readme = "README.md"
license = {text = "MIT"}
```

**Pattern DIVERGENCES** (intentional, locked by 06-CONTEXT.md):
- `name = "quizify-csv-to-json-webhook"` (D-06-05) — note hyphen↔underscore split vs the importable `quizify_csv_ingest`.
- `version = "1.1.0"` (D-06-05).
- `requires-python = ">=3.9"` (D-06-03 — sibling uses 3.8 because PEP 585 generics are not used there).
- **NO `[project.dependencies]` array** (D-13 + Pitfall 20). Sibling has 4 runtime deps; we have zero.
- ADD `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]` (D-06-01).
- ADD `[tool.flit.module] name = "quizify_csv_ingest"` (D-06-04 — sibling does NOT have this because its project name underscore-substitutes correctly; ours does not).
- DROP `[tool.ruff]` and `[tool.mypy]` blocks (sibling has them; not introduced this phase).

---

### `quizify-csv-to-json-webhook/docs/webhook-schema.json` (NEW — Draft-07 artifact)

**Analog:** `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` (target-shape reference, NOT a schema)

**What to extract from the analog:** The set of keys and value-shapes the schema must accept. Top-level is a JSON array of row objects (lines 1-2: `[\n    {`). Each row has fixed contact fields, then `question-N`/`answers-N`/`answers-tags-N` triples (line 13 onward). The `answers-N` shape is asymmetric (line 14-19 = `{answer_name, id}`; lines 22-29 = `{answer_name, answer_img, answer_tag, id}`; line 32 = bare string `"Ninguno"`) — this is the exact reason for D-06-13 `oneOf(string, array<object>)` and D-06-14 (no `additionalProperties: false` on the answer object).

**Schema layout pattern** (RESEARCH §"Pattern 4: Schema layout" lines 286-333) — copy this exact JSON structure into the file. Anchor points:
- `"$schema": "http://json-schema.org/draft-07/schema#"` (D-06-07; HTTP not HTTPS; trailing `#`; Pitfall 22).
- `"$id": "quizify-csv-to-json-webhook/docs/webhook-schema.json"` (D-06-07; no GitHub URL).
- Root `{"type": "array", "items": {...}}` (D-06-09).
- `"additionalProperties": false` AT ROW LEVEL (D-06-10).
- `"required": [...]` covers contact + locked D-05 tail (D-06-11).
- `"patternProperties"` keys EXACTLY `"^question-\\d+$"`, `"^answers-\\d+$"`, `"^answers-tags-\\d+$"` (D-06-13; Pitfall 21 — anchors required on both ends).
- Type-only string constraints — NEVER `minLength` (D-06-12).

---

### `quizify-csv-to-json-webhook/tests/test_schema_validation.py` (NEW — 4 test classes)

**Primary analog (class style):** `tests/test_layout.py::TestScoringIndexMap` (lines 121-181)
**PII-assertion analog:** `tests/test_logging_pii.py` (lines 32-117)
**Smoke-subprocess analog (use sparingly, see Pitfall 23):** `tests/test_default_order_regression.py` (lines 32-44)
**Conftest fixtures available:** `sample_csv_path` (line 14-16), `dynamic_headers` (line 19-24), `scoring_index_map_default` (line 107-117) in `tests/conftest.py`.

**Imports + ROOT/FIXTURE pattern** (mirror `tests/test_layout.py` lines 1-22):
```python
"""Phase 6 schema validation tests (D-06-25 a/b/c/d)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
SCHEMA_PATH = ROOT / "docs" / "webhook-schema.json"
```

**Class-grouping pattern** (mirror `test_layout.py::TestScoringIndexMap` line 121):
```python
class TestSchemaSelfValidation:
    """VALI-03: schema is itself valid Draft-07."""
    def test_schema_self_validates_against_draft07(self) -> None:
        ...
```

Four classes per VALIDATION.md task map: `TestSchemaSelfValidation`, `TestSamplePasses`, `TestValidationFailurePIIsafe`, `TestMissingExtra`.

**Skip-if-extra-not-installed pattern** (idiomatic pytest; new to this file but standard):
```python
fastjsonschema = pytest.importorskip("fastjsonschema")
```
Place at module top OR inside each class that needs it — RESEARCH §"Wave 0 Gaps" line 661 specifies `pytest.importorskip("fastjsonschema")` for tests that need the lib installed to run.

**PII-leak assertion idiom to MIRROR** (from `tests/test_logging_pii.py` lines 32-58):
```python
def test_warning_for_unexpected_status_does_not_contain_email(tmp_path: Path) -> None:
    leak_email = "leak@example.com"
    leak_phone = "+52 55 9999 9999"
    ...
    # Diagnostic was emitted
    assert "unexpected status value" in result.stderr.lower()
    # PII tokens absent from stderr
    assert leak_email not in result.stderr
    assert leak_phone not in result.stderr
    assert "Leakage" not in result.stderr
```

Apply the same `leak_email`/`leak_phone`/`leak_name` triple to `TestValidationFailurePIIsafe` — assert the formatted D-06-20 message `"ERROR schema validation failed at <pointer>: expected <type>, got <type>"` contains only categorical tokens and that `leak_email not in stderr`, `leak_phone not in stderr`, `leak_name not in stderr` (D-06-25 c, T-PII-01).

**Helper-direct (NOT subprocess) pattern** (D-06-24, Pitfall 23) — call the validation helper directly with Python data:
```python
from quizify_csv_ingest import _run_schema_validation, _format_validation_error  # names planner's call
```
Mirrors `test_layout.py` lines 12-18 (direct symbol imports from `quizify_csv_ingest`). This is the dominant test idiom — only `tests/test_default_order_regression.py` and `tests/test_cli_emit.py` use `subprocess.run`, and both are explicitly tagged as the rare end-to-end path.

**Monkeypatch-import-to-fail idiom** (for `TestMissingExtra` / VALI-05 / D-06-25 d):
```python
def test_missing_fastjsonschema_extra_emits_actionable_stderr(monkeypatch, capsys):
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *a, **kw):
        if name == "fastjsonschema":
            raise ImportError("No module named 'fastjsonschema'")
        return real_import(name, *a, **kw)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = _run_schema_validation([], SCHEMA_PATH)
    assert rc == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == (
        "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'"
    )
    assert "Traceback" not in captured.err
```
The `monkeypatch` + `capsys` fixture pair is standard pytest — no existing analog in this repo (current tests use `subprocess.run`'s `capture_output=True` instead). This is the cleanest unit-level approach per RESEARCH §Pitfall 18.

**Sample-passes pattern** (for `TestSamplePasses` / VALI-01 / D-06-25 b) — mirror RESEARCH Example 4 (lines 549-565):
```python
def test_sample_csv_payload_validates(tmp_path: Path) -> None:
    fastjsonschema = pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import convert
    out = tmp_path / "out.json"
    rc = convert(FIXTURE, None, out, quiz_title="Autoevaluacion")
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = fastjsonschema.compile(schema)
    validator(payload)  # raises on failure → test fails
```

Note the `tmp_path` fixture usage — already canonical in `tests/test_cli_emit.py` lines 50-78 and `tests/test_logging_pii.py` lines 32-117.

---

### `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (EDIT — argparse + helper + wire)

**Analog:** self (additive edits within existing patterns).

**argparse-flag addition pattern** (mirror lines 437-451 — the existing `--dry-run`, `--verbose`, `--emit-json`, `--quiz-title` flags):

Existing pattern at line 442-446:
```python
parser.add_argument(
    "--emit-json",
    action="store_true",
    help="Explicit JSON emission flag (default behavior; accepted for self-documenting scripts).",
)
```

**Add this block alongside** (RESEARCH Example 1 lines 497-502):
```python
parser.add_argument(
    "--validate",
    action="store_true",
    help="Validate emitted JSON against docs/webhook-schema.json (requires '[validate]' extra).",
)
```

**`convert()` signature extension pattern** — current signature lines 342-347:
```python
def convert(
    path: Path,
    trailer: tuple[str, ...] | None,
    output: Path | None,
    quiz_title: str,
) -> int:
```

Add a new keyword arg `validate: bool = False` (preserves backward compatibility for tests that call `convert()` with 4 positional args — e.g., the new `TestSamplePasses` test does NOT pass `validate=True` when it precomputes the output and validates externally). Default `False` honors VALI-04.

**Validation-call insertion point** (D-06-16 — post-build, pre-write) — splice between line 421 (`results.append(row_dict)` loop close) and line 423 (`if output is None:` write block):
```python
# After the for-loop at line 422, before the json.dump branches at line 423:
if validate:
    rc = _run_schema_validation(results, SCHEMA_PATH)
    if rc != 0:
        return rc
# (existing write branches unchanged)
```

**Module-level constant pattern to MIRROR** — current line 11-14 imports + line 16 `CONTACT_PREFIX` define module-top constants. Add (RESEARCH Open Question #2):
```python
SCHEMA_PATH = Path(__file__).resolve().parent / "docs" / "webhook-schema.json"
```
Place this near `SCORING_PLACEHOLDERS` (line 117) — same idiom (compile-time constant, no runtime side effects).

**Helper-function pattern** (mirror the pure-function discipline at lines 48-105: `normalize_key`, `parse_trailer_arg`, `classify_headers`):

Existing pattern — pure function, returns int/tuple, raises only categorical exceptions:
```python
def parse_trailer_arg(s: str) -> tuple[str, ...]:
    parts = [p.strip() for p in s.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        raise ValueError("empty trailer-columns")
    return tuple(parts)
```

**New helper to ADD** — copy RESEARCH §"Pattern 1" (lines 213-243) verbatim, with `_format_validation_error` extracted per RESEARCH Example 2 (lines 510-526). The two functions live at module scope (top-level), NOT nested inside `convert()` (RESEARCH Open Question #1 recommendation).

**Lazy-import pattern** (NEW — no existing analog; this is the novel pattern Phase 6 introduces). The closest existing pattern is `import unicodedata` at line 13 (stdlib, eager). The lazy version (D-06-17, Pitfall 18):
```python
def _run_schema_validation(rows: list[dict], schema_path: Path) -> int:
    try:
        import fastjsonschema  # lazy: only imported under --validate
    except ImportError:
        print(
            "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'",
            file=sys.stderr,
        )
        return 1
    ...
```
The existing `print(..., file=sys.stderr)` idiom for one-shot CLI errors appears at line 461: `print("ERROR invalid trailer-columns", file=sys.stderr)` — mirror that exact form for both D-06-19 and D-06-20 messages (NOT `logging.error`, which formats with the `%(levelname)s` prefix per line 306 — would produce `ERROR ERROR --validate requires...`).

**PII-safe stderr pattern** (T-PII-01 carry-forward) — mirror lines 387-392 of `convert()`:
```python
for name in missing_trio_names:
    logging.warning(
        "trailer column %r absent from CSV header; emitting empty string for %s in all rows",
        name,
        _OUTPUT_KEY_BY_CANONICAL[name],
    )
```
Notice: `name` is from the locked `DEFAULT_TRAILER` (compile-time), `_OUTPUT_KEY_BY_CANONICAL[name]` is from a compile-time dict (line 37-41). Zero row-data interpolation. The validation helper follows the same discipline — `err.path` (categorical), `err.rule` (categorical), `err.definition.get("type")` (schema-declared, categorical), `type(err.value).__name__` (Python type name, categorical). NEVER `err.message` or `err.value` (Pitfall 17).

**Wiring `args.validate` into `convert()` from `main()`** — current call site at line 469:
```python
return convert(args.csv_path, trailer_override, args.output, quiz_title)
```
Extend to:
```python
return convert(args.csv_path, trailer_override, args.output, quiz_title, validate=args.validate)
```

---

### `quizify-csv-to-json-webhook/README.md` (EDIT — D-11 in-place extensions)

**Analog:** self (existing 10 H2 sections — `tests/test_readme_help_alignment.py` enforces no new sections).

**Pattern** (D-06-23): Two surgical edits, both inside existing sections:
1. Add a row to the existing CLI reference table (`| --validate | off | Validate emitted JSON against docs/webhook-schema.json (requires '[validate]' extra) | — |`).
2. Add `pip install '.[validate]'` line as an OPTIONAL second install step under `## Quickstart`.
3. Optionally inline-reference `docs/webhook-schema.json` where the example payload `docs/webhook-quizify-format-example.json` is already mentioned.

NO new H2. NO renaming. The drift test (`test_readme_help_alignment.py`) is the gate — VALI-06.

---

## Shared Patterns

### Pattern A — PII-safe categorical-only stderr (T-PII-01 carry-forward)
**Source:** `quizify_csv_ingest.py` lines 387-392 (`convert()`'s missing-trio WARNING) + `tests/test_logging_pii.py` lines 53-58 (assertion idiom)
**Apply to:** Validation helper's failure-path stderr formatting; all 4 new test classes' assertions.

**Idiom (production code):**
```python
# Compile-time constants only — never row indices, never cell content.
print(
    f"ERROR schema validation failed at {pointer}: expected {expected}, got {actual}",
    file=sys.stderr,
)
```
where `pointer`, `expected`, `actual` derive ONLY from `err.path`, `err.definition.get("type")`, `type(err.value).__name__`. NEVER `err.message`, NEVER `err.value`.

**Idiom (test):**
```python
leak_email = "leak@example.com"
leak_phone = "+52 55 9999 9999"
# ... trigger failure ...
assert leak_email not in stderr
assert leak_phone not in stderr
assert "Leakage" not in stderr
```

---

### Pattern B — Stderr with bare `print(..., file=sys.stderr)` for one-shot CLI errors
**Source:** `quizify_csv_ingest.py` line 461 (`print("ERROR invalid trailer-columns", file=sys.stderr)`)
**Apply to:** D-06-19 missing-extra message, D-06-20 validation-failure message.

**NOT** `logging.error(...)` — that prefixes with `%(levelname)s` per line 306 and would produce a doubled `ERROR ERROR` prefix on the locked templates. The existing line 461 pattern is the established style for once-only, exit-1 CLI errors.

---

### Pattern C — Pure-function helpers + module-top constants
**Source:** `quizify_csv_ingest.py` lines 16-32 (`CONTACT_PREFIX`, `DEFAULT_TRAILER`), 37-41 (`_OUTPUT_KEY_BY_CANONICAL`), 117-122 (`SCORING_PLACEHOLDERS`); pure-function helpers at 48-58, 173-174.
**Apply to:** `SCHEMA_PATH` constant + `_run_schema_validation` and `_format_validation_error` helpers.

Discipline: helpers take inputs, return ints/tuples, raise only `ValueError`/`LayoutError` for categorical errors; no global mutation; no per-call file I/O beyond explicit path arguments.

---

### Pattern D — Test conftest reuse
**Source:** `tests/conftest.py` lines 14-117 (fixtures `sample_csv_path`, `dynamic_headers`, `scoring_index_map_default`).
**Apply to:** `TestSamplePasses` reuses `sample_csv_path` (or its module-level `FIXTURE` constant equivalent). `TestValidationFailurePIIsafe` builds synthetic rows in-test (no existing fixture for malformed payloads — by design).

No new conftest fixtures required (RESEARCH §"Wave 0 Gaps" line 661).

---

### Pattern E — Class-grouped tests with docstring contract reference
**Source:** `tests/test_layout.py::TestScoringIndexMap` lines 121-126 — class-level docstring cites the requirement IDs (`TRAIL-01`, `D-05-01`, `D-05-03`, `D-05-02`).
**Apply to:** All 4 new test classes — class-level docstring cites VALI-01/02/03/05 + relevant decision IDs (D-06-19, D-06-20, T-PII-01).

---

### Pattern F — `tmp_path` for output-file tests
**Source:** `tests/test_cli_emit.py` lines 50-78 (`test_output_flag_writes_file`), `tests/test_logging_pii.py` lines 32-117 (`test_warning_for_*_does_not_contain_*`).
**Apply to:** `TestSamplePasses` if it exercises `convert(..., output=tmp_path/"out.json", ...)`.

---

## No Analog Found

| File | Role | Reason | Planner reference |
|------|------|--------|-------------------|
| `quizify-csv-to-json-webhook/docs/webhook-schema.json` (the schema BODY itself, distinct from the layout shell) | static asset (Draft-07 schema) | No JSON Schema artifact has ever been authored in this repo. The shape-reference is the example payload, but the schema KEYWORDS (`$schema`, `$id`, `patternProperties`, `oneOf`, `additionalProperties: false`) have no codebase precedent. | Use RESEARCH §"Pattern 4: Schema layout" (06-RESEARCH.md lines 286-333) as the literal template. |
| Lazy-import-inside-function (production code) | helper pattern | No existing function in `quizify_csv_ingest.py` does `import X` inside its body — every existing import is at module top (lines 5-14). | Use RESEARCH §"Pattern 1" (06-RESEARCH.md lines 213-243) as the literal template. The `try/except ImportError` block is the novel idiom. |
| Monkeypatch `builtins.__import__` to simulate ImportError (test code) | test idiom | No existing test in `tests/` uses `monkeypatch` (`grep -l monkeypatch tests/` returns empty per quick scan — current tests use subprocess capture instead). | Use RESEARCH §Pitfall 18 + standard pytest `monkeypatch` documentation. The `_run_schema_validation` helper is unit-callable per D-06-24, so this is the cleanest test path. |

---

## Metadata

**Analog search scope:**
- `confluence-to-markdown/` — sibling project with flit_core pyproject.
- `quizify-csv-to-json-webhook/` — primary project (source + tests + docs).

**Files scanned:** 9
- `confluence-to-markdown/pyproject.toml`
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py`
- `quizify-csv-to-json-webhook/tests/conftest.py`
- `quizify-csv-to-json-webhook/tests/test_cli_emit.py`
- `quizify-csv-to-json-webhook/tests/test_logging_pii.py`
- `quizify-csv-to-json-webhook/tests/test_layout.py`
- `quizify-csv-to-json-webhook/tests/test_default_order_regression.py`
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`
- `.planning/phases/06-json-schema-validation/{06-CONTEXT.md, 06-RESEARCH.md, 06-VALIDATION.md}`

**Pattern extraction date:** 2026-05-04
