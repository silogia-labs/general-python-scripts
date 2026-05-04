# Phase 5: Python Trailer Hardening — Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 8 (5 modified, 2 new, 1 doc-modified)
**Analogs found:** 8 / 8 — all in-repo

## File Classification

| File | Status | Role | Data Flow | Closest Analog | Match Quality |
|------|--------|------|-----------|----------------|---------------|
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (`classify_headers` L51-78) | modify | pure-fn / header-parser | transform (header → tuple) | self (lines 64-78 strict positional check) + `_norm_for_match` L146 | exact (extending existing fn) |
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (`build_row` L199-269) | modify | pure-fn / row-builder | transform (cells → dict) | self lines 263-265 (current bounds-checked positional reads) | exact (replacing existing block) |
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (`convert` L310-384) | modify | CLI orchestrator | event-driven (warning emit before row loop) | self L356 + L374 (existing `logging.warning` PII-safe pattern) | exact |
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (`dry_run` L286) | modify | CLI orchestrator (mechanical unpack) | request-response | self L344 (sibling `convert` unpack site) | exact |
| `quizify-csv-to-json-webhook/tests/conftest.py` | modify | pytest fixture module | request-response | self (existing 3 fixtures L14-104) | exact |
| `quizify-csv-to-json-webhook/tests/test_layout.py` | modify | unit test | request-response | self L25-33 (`test_sample_csv_header_classification`) | exact |
| `quizify-csv-to-json-webhook/tests/test_row_builder.py` | modify (14 sites + 2 new classes) | unit test | request-response | self L284-309 (`test_scoring_pass_through`, `test_empty_scoring_emits_empty_strings`) + `tests/test_logging_pii.py` (caplog/PII assertions) | exact |
| `quizify-csv-to-json-webhook/tests/test_default_order_regression.py` | NEW | unit test (golden-fixture regression) | transform-equality | `tests/test_golden_structure.py` (closest existing golden-style test) — see below | role-match |
| `quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json` | NEW | golden fixture | static data | `docs/webhook-quizify-format-example.json` (single existing JSON sample) | role-match (location differs intentionally) |
| `quizify-csv-to-json-webhook/README.md` (lines 62-69, 129-132) | modify (delete + rewrite) | docs | static | self surrounding paragraphs | exact |
| `.planning/MILESTONES.md` v1.1 entry | modify | docs | static | existing v1.0 / v1.1 entries | exact |

## Pattern Assignments

### `classify_headers` extension (pure-fn / header-parser)

**Analog:** `quizify_csv_ingest.py` itself (existing strict-positional check + `_norm_for_match`).

**Existing strict positional check to PRESERVE** (`quizify_csv_ingest.py:69-74`):
```python
for i, expected in enumerate(trailer):
    hi = n - t_len + i
    if normalize_key(header_row[hi]) != normalize_key(expected):
        raise LayoutError(
            f"Trailer mismatch at column {hi}: expected {expected!r}, got {header_row[hi]!r}"
        )
```

**Normalizer to REUSE** (`quizify_csv_ingest.py:146-147`):
```python
def _norm_for_match(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()
```

**Helper-style precedent** (top-level pure helpers — `_norm_for_match` L146, `_looks_iso` L150-159, `_resolve_quiz_title` L130-143). Naming convention: leading underscore, lowercase-snake, single-purpose, type-annotated, `from __future__ import annotations` already imported at L4.

**Slicing pattern to EXTEND** (`quizify_csv_ingest.py:75-78`):
```python
prefix_raw = header_row[:p_len]
dynamic = header_row[p_len : n - t_len]
trailer_raw = header_row[n - t_len :]
return prefix_raw, dynamic, trailer_raw
```

**Pattern to apply** — append index-map build right before the return; widen return tuple to 5 elements per D-05-01:
```python
# After existing strict check; uses DEFAULT_TRAILER[:3] as canonical scope
scoring_index_map: dict[str, int] = {}
missing_trio_names: list[str] = []
for canonical in DEFAULT_TRAILER[:3]:
    canonical_norm = _norm_for_match(canonical)
    idx = next(
        (i for i, h in enumerate(trailer_raw) if _norm_for_match(h) == canonical_norm),
        None,
    )
    if idx is not None:
        scoring_index_map[canonical] = idx
    else:
        missing_trio_names.append(canonical)
return prefix_raw, dynamic, trailer_raw, scoring_index_map, tuple(missing_trio_names)
```

Type-annotation style: `dict[str, int]`, `tuple[str, ...]` (matches `DEFAULT_TRAILER`'s type and `parse_trailer_arg` return at L43-48).

---

### `build_row` signature change (pure-fn / row-builder)

**Analog:** `quizify_csv_ingest.py:199-269` (the function being modified — replace lines 263-265 in place; preserve everything else).

**Existing block to REPLACE** (`quizify_csv_ingest.py:263-265`):
```python
row["result-logic"] = trailer_cells_decoded[0] if len(trailer_cells_decoded) > 0 else ""
row["score-category"] = trailer_cells_decoded[1] if len(trailer_cells_decoded) > 1 else ""
row["score-value"] = trailer_cells_decoded[2] if len(trailer_cells_decoded) > 2 else ""
```

**Adjacent positional reads to PRESERVE UNCHANGED** (D-05-05 — out of scope for trailer hardening):
- `quizify_csv_ingest.py:226` — `status_date = trailer_cells_decoded[5]`
- `quizify_csv_ingest.py:232` — `answer_tags_csv = trailer_cells_decoded[3]`

**Signature pattern** (`quizify_csv_ingest.py:199-205`) — extend with one new positional-or-keyword arg per D-05-04:
```python
def build_row(
    prefix_cells_decoded: list[str],
    dynamic_cells_decoded: list[str],
    trailer_cells_decoded: list[str],
    dynamic_headers_decoded: list[str],
    quiz_title: str,
    scoring_index_map: dict[str, int],   # NEW (D-05-04)
) -> tuple[dict, list[str]]:
```

**Replacement pattern (verbatim from D-05-04 / RESEARCH.md):**
```python
row["result-logic"]   = trailer_cells_decoded[scoring_index_map["Result logic"]]   if "Result logic"   in scoring_index_map else ""
row["score-category"] = trailer_cells_decoded[scoring_index_map["Score category"]] if "Score category" in scoring_index_map else ""
row["score-value"]    = trailer_cells_decoded[scoring_index_map["Score value"]]    if "Score value"    in scoring_index_map else ""
```

Pitfall 10 — **never** write `... or trailer_cells_decoded[0]`. The "missing trio name" branch MUST emit `""` literal.

---

### `convert()` warning loop (CLI orchestrator)

**Analog:** existing PII-safe `logging.warning` calls in the same function.

**Existing PII-safe warning at `quizify_csv_ingest.py:356-361`** — once-per-row mismatch:
```python
logging.warning(
    "row %d row length mismatch: expected %d fields, got %d",
    idx,
    expected_len,
    len(row),
)
```

**Existing PII-safe warning at `quizify_csv_ingest.py:374`** — forwarded `build_row` warnings:
```python
for w in warnings_out:
    # `w` is constructed in build_row from column names + categorical
    # values only — never cell content (T-PII-01).
    logging.warning("row %d %s", idx, w)
```

**Existing once-only flag pattern from `dry_run` L294-305** (FYI — not needed for new warnings since they fire before the row loop):
```python
row_warned = False
...
if len(row) != expected_len and not row_warned:
    logging.warning("row length mismatch ...")
    row_warned = True
```

**Logging config** (`quizify_csv_ingest.py:272-274`):
```python
def configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", stream=sys.stderr, force=True)
```
Format `"%(levelname)s %(message)s"` produces `WARNING <msg>` — matches the locked D-05-08 string head exactly.

**Pattern to apply** — module-top constant + once-per-CSV loop inserted in `convert()` between the existing `classify_headers` unpack (L344) and the row loop (L354). Insert `_OUTPUT_KEY_BY_CANONICAL` near `DEFAULT_TRAILER` (L25-32) for grep-locality:
```python
_OUTPUT_KEY_BY_CANONICAL = {
    "Result logic":   "result-logic",
    "Score category": "score-category",
    "Score value":    "score-value",
}
```

Inside `convert()` after `classify_headers` succeeds:
```python
for name in missing_trio_names:
    logging.warning(
        "trailer column %r absent from CSV header; "
        "emitting empty string for %s in all rows",
        name,
        _OUTPUT_KEY_BY_CANONICAL[name],
    )
```
`%r` produces single-quoted form (`'Result logic'`) — matches the locked D-05-08 template.

---

### `dry_run` unpack (mechanical churn)

**Analog:** sibling unpack at `quizify_csv_ingest.py:344` inside `convert`.

**Current site** (`quizify_csv_ingest.py:286`):
```python
_prefix, dynamic, _trailer_h = classify_headers(header, trailer)
```

**Pattern to apply** — extend to 5-tuple, discard the two new slots with `_` prefix (D-05-07: dry_run does NOT emit warnings):
```python
_prefix, dynamic, _trailer_h, _scoring_map, _missing = classify_headers(header, trailer)
```

---

### `tests/conftest.py` — new fixture (D-05-06)

**Analog:** existing fixtures `dynamic_headers` (L19-24), `full_answers_row` (L27-72), `red_flag_short_circuit_row` (L75-88), `multi_select_synthetic_row` (L91-104).

**Style/imports already present** (L1-11):
```python
"""Shared pytest fixtures for Phase 2 row-builder + CLI tests."""
from __future__ import annotations
import csv
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
```

**Fixture pattern** (L19-24 — minimal type-annotated):
```python
@pytest.fixture
def dynamic_headers() -> list[str]:
    """20 dynamic headers from the live sample CSV (raw, not yet decoded)."""
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    return header[6:-6]
```

**Pattern to apply** — append a new function-scope fixture matching D-05-06 verbatim:
```python
@pytest.fixture
def scoring_index_map_default() -> dict[str, int]:
    """Default-order scoring index map matching DEFAULT_TRAILER[:3] positions.

    Used by every test_row_builder.py call site that previously omitted the
    scoring map (post-Phase-5, build_row requires it as the 6th arg).
    """
    return {"Result logic": 0, "Score category": 1, "Score value": 2}
```

---

### `tests/test_layout.py` — line 27 unpack + new TestScoringIndexMap class

**Analog (current 3-tuple unpack site):** `tests/test_layout.py:25-33`:
```python
def test_sample_csv_header_classification() -> None:
    header = _read_header_row()
    prefix, dynamic, trailer = classify_headers(header)
    assert len(prefix) == len(CONTACT_PREFIX)
    assert prefix[0] == "First name"
    assert len(dynamic) == 20
    ...
    assert trailer[0] == "Result logic"
```

**Analog (test class structure — same file uses module-level test functions; class grouping is the natural home for related new tests).** Imports already in place (L12):
```python
from quizify_csv_ingest import CONTACT_PREFIX, DEFAULT_TRAILER, classify_headers, parse_trailer_arg
```
**Note:** `LayoutError` is NOT yet imported in this file — add it for the strict-positional carry-forward proof test.

**Pattern to apply for L27 unpack:**
```python
prefix, dynamic, trailer, scoring_index_map, missing_trio_names = classify_headers(header)
# Add inline assertions on the new fields:
assert scoring_index_map == {"Result logic": 0, "Score category": 1, "Score value": 2}
assert missing_trio_names == ()
```

**Pattern to apply for new `TestScoringIndexMap` class** — group five assertions per RESEARCH validation map: default-order, scrambled-order, normalization (case+diacritic), missing-column listing, strict positional check still raises `LayoutError`. Use module-level helper `_read_header_row` (L19-22) for default-order; build synthetic header rows for scrambled / missing tests (no fixture CSV files needed — keeps unit-level per D-05-12).

---

### `tests/test_row_builder.py` — 14 call sites + TestScrambledTrailer + TestMissingColumnWarning

**Analog (current call-site shape — `tests/test_row_builder.py:113`):**
```python
row, warnings = build_row(prefix, dyn, trailer, decoded_headers, quiz_title="")
```

**14 call-site lines** (per RESEARCH §Pitfall C): 113, 130, 137, 149, 174, 201, 207, 220, 232, 278, 287, 298, 314, 324.

**Pattern to apply at every call site** — append the new arg via the conftest fixture; mechanical churn:
```python
row, warnings = build_row(prefix, dyn, trailer, decoded_headers,
                          quiz_title="", scoring_index_map=scoring_index_map_default)
```
Each test function that calls `build_row` must add `scoring_index_map_default` to its signature alongside existing `dynamic_headers`/`full_answers_row` fixtures.

**Existing scoring-positive analog** (`tests/test_row_builder.py:284-292`) — `test_scoring_pass_through`:
```python
def test_scoring_pass_through() -> None:
    prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
    trailer_d = ["Score", "Signos de Alarma", "500", "", "00:30", "2024-01-15"]
    row, _ = build_row(prefix_d, dyn_d, trailer_d, headers_d, quiz_title="")
    assert row["result-logic"] == "Score"
    assert row["score-category"] == "Signos de Alarma"
    assert row["score-value"] == "500"
    assert isinstance(row["score-value"], str)
```
Use this exact shape for `TestScrambledTrailer.test_scrambled_order_binds_correctly`, but pass `scoring_index_map={"Result logic": 2, "Score category": 1, "Score value": 0}` and a reversed `trailer_d` so a positional-fallback regression would fail visibly.

**Existing empty-scoring analog** (`tests/test_row_builder.py:295-309`) — `test_empty_scoring_emits_empty_strings`:
```python
def test_empty_scoring_emits_empty_strings() -> None:
    prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
    trailer_d = ["", "", "", "", "", "2024-01-15"]
    row, warnings_out = build_row(prefix_d, dyn_d, trailer_d, headers_d, quiz_title="")
    assert row["result-logic"] == ""
    ...
    for w in warnings_out:
        assert "result-logic" not in w
        ...
```
This test verifies D-09 carry-forward (cell empty in present column → silent). Must pass post-refactor with `scoring_index_map_default` arg.

**Caplog analog for TestMissingColumnWarning** — closest pattern is `tests/test_logging_pii.py` but that file uses subprocess + stderr capture (out of scope per Pitfall 16 / D-05-12). Use pytest's bundled `caplog` fixture instead. Reference shape (composed from RESEARCH.md §Code Examples + pytest docs):
```python
import logging

class TestMissingColumnWarning:
    def test_warning_message_matches_locked_template(self, tmp_path, caplog):
        # Build CSV whose --trailer-columns omits "Result logic"
        ...
        with caplog.at_level(logging.WARNING):
            rc = convert(csv_path, custom_trailer, output=tmp_path / "out.json", quiz_title="")
        assert rc == 0
        matches = [r for r in caplog.records
                   if "absent from CSV header" in r.getMessage()
                   and "'Result logic'" in r.getMessage()
                   and "result-logic in all rows" in r.getMessage()]
        assert len(matches) == 1, [r.getMessage() for r in caplog.records]

    def test_missing_column_emits_empty_string(self, scoring_index_map_default):
        # Direct build_row unit test — no convert/CSV needed
        scoring_map = {"Score category": 1, "Score value": 2}  # "Result logic" missing
        row, _ = build_row(..., scoring_index_map=scoring_map)
        assert row["result-logic"] == ""

    def test_warning_pii_safe(self, tmp_path, caplog):
        # Adapt the PII-token absence pattern from tests/test_logging_pii.py
        ...
        msg = matches[0].getMessage()
        assert "@" not in msg
        assert "+" not in msg
```

**PII-safety assertion pattern to copy** — `tests/test_logging_pii.py:55-58`:
```python
assert leak_email not in result.stderr
assert leak_phone not in result.stderr
assert "Leakage" not in result.stderr
```

---

### `tests/test_default_order_regression.py` (NEW) — TRAIL-03

**Analog (closest existing golden-style):** `tests/test_golden_structure.py` — verifies output structure but does NOT compare against a checked-in JSON file. No exact analog exists in-repo (Pitfall G). Use the structural-equality pattern from RESEARCH.md §Code Examples.

**Existing CLI-subprocess test analog** (`tests/test_layout.py:60-76`) — for shape of subprocess invocation + `capture_output=True, text=True, timeout=60`:
```python
result = subprocess.run(
    [sys.executable, str(SCRIPT), "--dry-run", str(FIXTURE), "--trailer-columns", TRAILER_CLI],
    capture_output=True, text=True, timeout=60, check=False,
)
assert result.returncode == 0
```

**Pattern to apply:**
```python
"""TRAIL-03: default-order callers see no behavioral change vs v1.0 baseline."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
GOLDEN = ROOT / "tests" / "fixtures" / "v1.0_default_order_output.json"


def test_default_order_byte_identical_to_v1_0_baseline() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    actual = json.loads(result.stdout)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected
```

**Exception to D-05-12** — this single TRAIL-03 regression test is allowed to be subprocess-driven because it specifically exercises the CLI entry point as a v1.0 user would. All other new tests stay unit-level.

---

### `tests/fixtures/v1.0_default_order_output.json` (NEW) — golden fixture

**Analog (location convention):** `docs/webhook-quizify-format-example.json` is the only existing JSON sample but is a single-row user-facing example, not a 42-row test fixture. Recommended placement: `tests/fixtures/` (new dir), per RESEARCH Open Question #2.

**Generation procedure** (Pitfall G — generate BEFORE any production change):
```bash
cd quizify-csv-to-json-webhook
python3 quizify_csv_ingest.py docs/quizify-submissions.csv \
    -o tests/fixtures/v1.0_default_order_output.json
git add tests/fixtures/v1.0_default_order_output.json
git commit -m "test: capture v1.0 default-order baseline before TRAIL-01 refactor"
```

**Format already locked by `convert()`** (`quizify_csv_ingest.py:382`): `json.dump(results, out_fh, indent=2, ensure_ascii=False)` + trailing `\n`.

**Precondition check** — Pitfall E: confirm `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` working-copy state with the user before generating the golden file. Currently dirty (43+/43-).

---

### `README.md` lines 62-69 + 129-132 — delete + rewrite

**Analog:** surrounding paragraphs (the "Trailer block" bullet at L62-69 and "Limitations" bullet at L129-132) — the same file, lines just above and below. New wording must match the README's existing prose tone: present-tense, operator-facing, no jargon.

**Lines 62-69 to REWRITE — current (delete):**
```
- **Trailer block (last 6 columns by default):** `Result logic`,
  `Score category`, `Score value`, `Answer tags`,
  `Time to complete (mm:ss)`, `Date`. Override with
  `--trailer-columns "name1,name2,..."`. Note: scoring keys and `statusDate`
  currently read trailer indices `0`, `1`, `2`, and `5` of the resolved
  trailer; `--trailer-columns` overrides that change those positions will
  misalign scoring fields. If you reorder the trailer, keep `Result logic`,
  `Score category`, `Score value`, and `Date` in the default positions.
```

**Pattern to apply (replacement):** preserve the trailer enumeration and `--trailer-columns` syntax, drop the "stays positional / will misalign" sentence, replace with TRAIL-01 wording: scoring trio is now bound by canonical column name; reordering `--trailer-columns` is safe for the scoring trio. `statusDate` and `Answer tags` remain positional (TRAIL-04 candidate, v1.2).

**Lines 129-132 to DELETE entirely** — this bullet ("scoring/statusDate reads remain positional") is the v1.0-correct documentation of the v1.0 bug. After Phase 5 it is *false*; remove the bullet and renumber surrounding bullets if needed (the list has no numbering — markdown bullets, no renumber).

---

### `.planning/MILESTONES.md` v1.1 entry — TRAIL-03 user-facing-bugfix note

**Analog:** existing v1.0 / v1.1 entries in the same file (style/format already established).

**Pattern to apply:** brief note under v1.1 milestone declaring TRAIL-03 a *user-facing bugfix* for non-default `--trailer-columns` callers. Default-order callers see no behavioral change. D-15 retired in favor of name-based scoring binding.

---

## Shared Patterns

### Normalization (used in classify_headers index-map build)
**Source:** `quizify_csv_ingest.py:146-147`
**Apply to:** Every trio name comparison in the new index-map build.
```python
def _norm_for_match(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()
```
Pitfall 11 — never substitute `normalize_key` (NFC-only) or `.lower()` (no casefold). Pitfall 9 — never substring; only equality.

### PII-safe categorical-only logging
**Source:** `quizify_csv_ingest.py:116-127` (`map_status` warning composition) + L356-361 (`convert` row-mismatch warning) + L374 (forwarded build_row warnings).
**Apply to:** New `convert()` missing-column warning loop. Message must contain only categorical/constant tokens (canonical column name from `DEFAULT_TRAILER`, output key from `_OUTPUT_KEY_BY_CANONICAL`, the literal phrase `"all rows"`). Never trailer-cell content, never row index, never PII.
```python
logging.warning(
    "trailer column %r absent from CSV header; "
    "emitting empty string for %s in all rows",
    name,
    _OUTPUT_KEY_BY_CANONICAL[name],
)
```

### Pure-fn-returning-tuple discipline
**Source:** `classify_headers` L51-78 returns a 3-tuple of pure header slices; `match_tags_to_questions` returns a 2-tuple; `map_status` returns a 2-tuple. Side-effects (logging) live in `convert`/`dry_run`.
**Apply to:** Extended `classify_headers` 5-tuple — must remain logging-free. The new `missing_trio_names` is a *return value*, NOT a `logging.warning` call inside `classify_headers` (D-05-07).

### Type-annotation style
**Source:** All function signatures in `quizify_csv_ingest.py`.
**Apply to:** New helper + extended `classify_headers` + `build_row` signature.
- `from __future__ import annotations` is imported at L4 — use bare-string-form types freely.
- `tuple[str, ...]` for ordered name collections (matches `DEFAULT_TRAILER`, `parse_trailer_arg` return).
- `list[str]` for mutable cell lists.
- `dict[str, int]` for the new `scoring_index_map`.

### Test-fixture composition (conftest.py)
**Source:** `tests/conftest.py:14-104` — function-scope fixtures, type-annotated returns, docstring describing CSV-fidelity intent.
**Apply to:** New `scoring_index_map_default` fixture — same shape, single-line return.

### caplog over capsys for unit-level log assertions
**Source:** RESEARCH.md §Standard Stack — `caplog` gives structured `LogRecord` access; `capsys` is a fallback if `configure_logging`'s `force=True` interferes.
**Apply to:** `TestMissingColumnWarning` — pattern in `tests/test_logging_pii.py` (subprocess + `result.stderr` substring) is FORBIDDEN here per D-05-12 / Pitfall 16. Use `caplog.at_level(logging.WARNING)` + iterate `caplog.records`.

---

## No Analog Found (use RESEARCH.md patterns)

| File | Role | Reason |
|------|------|--------|
| `tests/test_default_order_regression.py` | golden-fixture regression test | No prior file-on-disk-comparison test exists in `tests/`. `test_golden_structure.py` does structural assertions but does NOT load a checked-in JSON. The pattern in RESEARCH.md §Code Examples ("default-order regression") is the prescription — copy it verbatim. |
| `tests/fixtures/v1.0_default_order_output.json` | static golden artifact | No prior `tests/fixtures/` directory; no prior multi-row JSON fixture. Generation procedure documented above (Pitfall G). |

---

## Metadata

**Analog search scope:**
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (production, 384 lines — full read of L1-160 + L195-395)
- `quizify-csv-to-json-webhook/tests/conftest.py` (full read, 105 lines)
- `quizify-csv-to-json-webhook/tests/test_layout.py` (full read, 111 lines)
- `quizify-csv-to-json-webhook/tests/test_logging_pii.py` (full read, 117 lines)
- `quizify-csv-to-json-webhook/tests/test_row_builder.py` (full read, 347 lines)
- `quizify-csv-to-json-webhook/tests/` directory listing (8 test files)
- `quizify-csv-to-json-webhook/docs/` directory listing (CSV input + single-row JSON example)
- `quizify-csv-to-json-webhook/README.md` lines 55-140 (positional-caveat sections)

**Files scanned:** 8

**Pattern extraction date:** 2026-05-03
