# Phase 5: Python Trailer Hardening — Research

**Researched:** 2026-05-03
**Domain:** Python stdlib CLI — header parsing + row builder refactor
**Confidence:** HIGH (all findings from direct code inspection of `quizify_csv_ingest.py`, every test file, README, MILESTONES, and pytest collection)

## Summary

Phase 5 replaces three positional reads (`trailer_cells_decoded[0]/[1]/[2]`) at `quizify_csv_ingest.py:263–265` with a name-keyed lookup driven by a `scoring_index_map: dict[str, int]` built once in `classify_headers`. The CONTEXT.md decisions are tight enough that research only needs to map them onto exact line numbers, enumerate every call site, and design a TRAIL-03 byte-level regression strategy. The phase touches one production file and three test files; the existing 71-test suite (1.09 s) is the budget gate (Pitfall 16).

**Primary recommendation:** Plan three tasks — (1) `classify_headers` 5-tuple return + `_norm_for_match`-based `scoring_index_map` build, (2) `build_row` signature change at line 199 + index-map reads at lines 263–265 + new `convert()` warning loop before line 354, (3) test churn (`conftest.py` fixture, all eight `build_row(...)` call sites in `test_row_builder.py`, the single `classify_headers(...)` unpack in `test_layout.py`, three new test classes, and a TRAIL-03 golden-file). Plus README updates removing the "stay positional" warning at lines 65–69 and 129–132 (CLAUDE.md does not exist, so README + MILESTONES are the only doc surfaces).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Header validation + index-map build | Pure module function (`classify_headers`) | — | Single CSV-open-time check; D-05-01 specifies this owner |
| Per-row scoring extraction | Pure module function (`build_row`) | — | O(1) dict lookup using map computed once; matches existing dict-based positional discipline |
| Missing-column warning emission | CLI orchestrator (`convert`) | — | `convert()` is the only logging surface; `classify_headers` stays pure (D-05-07) |
| User-facing behavior change note | Docs (`MILESTONES.md` v1.1, `README.md`) | — | TRAIL-03 mandates a user-visible bugfix note; README's existing "scoring stays positional" caveat must be deleted |
| Regression coverage (default order) | Test suite (golden file or live-sample roundtrip) | — | Verifies TRAIL-03 — default-order callers see byte-identical output |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-05-01:** `classify_headers` returns 5-tuple `(prefix_raw, dynamic, trailer_raw, scoring_index_map, missing_trio_names)`; map keys use the *display* form from `DEFAULT_TRAILER` (`"Result logic"`, `"Score category"`, `"Score value"`).
- **D-05-02:** Existing strict positional check in `classify_headers` (lines 69–74) is preserved — `--trailer-columns` retains its "this is the order my CSV's trailer is in" semantics.
- **D-05-03:** Reuse `_norm_for_match` (NFC + casefold) at `quizify_csv_ingest.py:146`. Do NOT use `normalize_key` (NFC-only) or `.lower()`.
- **D-05-04:** `build_row` gains `scoring_index_map: dict[str, int]`; lookup form is `trailer_cells_decoded[scoring_index_map[name]] if name in scoring_index_map else ""`.
- **D-05-05:** Trailer list still passed to `build_row` (still used positionally for `Answer tags` `[3]` at line 232 and `Date` `[5]` at line 226).
- **D-05-06:** Test fixture `scoring_index_map_default = {"Result logic": 0, "Score category": 1, "Score value": 2}`.
- **D-05-07:** `convert()` emits the missing-column warnings before the row loop (after `classify_headers` succeeds, before line 354).
- **D-05-08:** Warning template is locked verbatim: `WARNING trailer column 'Result logic' absent from CSV header; emitting empty string for result-logic in all rows`.
- **D-05-09:** Empty cell in present column = silent (D-03 carried forward); warning fires only on header absence.
- **D-05-10:** NO positional fallback (Pitfall 10).
- **D-05-11:** Three new test classes — scrambled order, missing column, default-order regression.
- **D-05-12:** Unit-level tests on `classify_headers` and `build_row` directly, not subprocess.

### Claude's Discretion
- Exact location of `_build_scoring_index_map` helper (top-level vs nested in `classify_headers`).
- Whether `missing_trio_names` is `list[str]` or `tuple[str, ...]`.
- Test-fixture naming for the default scoring index map.
- Commit grouping (single vs split).

### Deferred Ideas (OUT OF SCOPE)
- Name-based lookup for non-scoring trailer cells (`Answer tags`, `Date`, `Time to complete`) — captured for future TRAIL-04.
- Promoting missing-trio columns to `LayoutError` under `--validate` — Phase 6 extension.
- Set-equality trailer validation (drop ordering as a contract) — explicitly rejected (D-05-02).
- Broader MILESTONES.md re-styling — only TRAIL-03 bugfix note required.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRAIL-01 | Scoring trio extracted by canonical column-name lookup using NFC+casefold equality | `classify_headers` builds `scoring_index_map` via `_norm_for_match(header) == _norm_for_match(canonical)` for each of `DEFAULT_TRAILER[:3]`; `build_row` reads via `trailer_cells_decoded[scoring_index_map[name]]` |
| TRAIL-02 | Missing canonical trailer column → empty string + PII-safe WARNING; no positional fallback | `classify_headers` returns `missing_trio_names`; `convert()` emits one `logging.warning` per name with the locked D-05-08 template before the row loop; `build_row` falls through to `""` (no `or [N]` branch) |
| TRAIL-03 | Default-order callers see no behavioral change; non-default callers receive bugfix; documented in MILESTONES.md | Default-order CSV → `scoring_index_map = {"Result logic": 0, "Score category": 1, "Score value": 2}` → reads at trailer indices 0/1/2 (identical to v1.0 behavior); golden-file or live-sample regression test against v1.0 output |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.7+ (pinned by D-13) | Everything | Project constraint: no runtime deps [VERIFIED: PROJECT.md D-13, requirements-dev.txt has only pytest] |
| `unicodedata.normalize("NFC", s).casefold()` | stdlib | Trio name comparison | `_norm_for_match` already exists at `quizify_csv_ingest.py:146` — reuse mandated by D-05-03 [VERIFIED: code inspection] |
| `logging.warning` | stdlib | Missing-column emit | Existing PII-safe pattern in `convert` (e.g., line 356, 374); stream is stderr, format `%(levelname)s %(message)s` (line 274) [VERIFIED: code inspection] |
| `pytest` | (dev only, no version pin in requirements-dev.txt) | Test runner | Already the test framework; `pytest.ini` at `quizify-csv-to-json-webhook/pytest.ini` sets `pythonpath = .` [VERIFIED: file inspection] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `caplog` (pytest fixture) | bundled with pytest | Capture `logging.warning` in unit tests for D-05-08 assertion | Use in the missing-column test (D-05-11b) to assert exactly one warning record with the locked message text [CITED: https://docs.pytest.org/en/stable/how-to/logging.html] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `caplog` | `capsys` to capture stderr text | `caplog` gives structured `LogRecord` access (level, message, args) — better for asserting "exactly one WARNING with this exact message"; `capsys` would also work since `configure_logging` writes to stderr, but only if logging is configured first. **Recommend `caplog`.** |
| Helper `_build_scoring_index_map(trailer_raw, trailer_canonical)` (top-level pure function) | Inline loop inside `classify_headers` | Top-level helper is unit-testable in isolation and matches the existing "small pure helpers" style (`_norm_for_match`, `_looks_iso`, `_resolve_quiz_title`). **Recommend top-level helper** [ASSUMED — style preference, not locked]. |
| `tuple[str, ...]` for `missing_trio_names` | `list[str]` | Existing trailer/header typing is `tuple[str, ...]` (e.g., `DEFAULT_TRAILER`, `parse_trailer_arg` return). **Recommend `tuple[str, ...]` for consistency** [ASSUMED — D-05 marks this as Claude's discretion]. |

**Installation:** None — phase adds zero runtime dependencies.

**Version verification:** N/A (stdlib only).

## Architecture Patterns

### System Architecture Diagram

```
CLI args → main() → convert(path, trailer_override, output, quiz_title)
                       │
                       ├─ open CSV (utf-8-sig)
                       ├─ read header row
                       ├─ classify_headers(header, trailer)  ◄── [CHANGE 1]
                       │     ├─ strict positional check (UNCHANGED, lines 64–74)
                       │     ├─ _build_scoring_index_map(trailer_raw, trailer)  [NEW]
                       │     │     for canonical in trailer[:3] of DEFAULT_TRAILER scope:
                       │     │       find idx where _norm_for_match(header[idx]) == _norm_for_match(canonical)
                       │     │       if found → map[canonical_display] = idx
                       │     │       else → missing.append(canonical_display)
                       │     └─ returns (prefix_raw, dynamic, trailer_raw, scoring_index_map, missing_trio_names)
                       │
                       ├─ for name in missing_trio_names:           ◄── [CHANGE 2: NEW WARNING LOOP]
                       │     logging.warning("trailer column %r absent from CSV header; "
                       │                     "emitting empty string for %s in all rows",
                       │                     name, OUTPUT_KEY_BY_CANONICAL[name])
                       │
                       └─ for each data row:
                             ├─ length check (UNCHANGED)
                             ├─ decode_cell over each cell (UNCHANGED)
                             └─ build_row(prefix_d, dynamic_d, trailer_d, headers_d,
                                          quiz_title, scoring_index_map)  ◄── [CHANGE 3]
                                   ├─ contact + tag + dynamic logic (UNCHANGED, lines 215–259)
                                   ├─ row["result-logic"]  = trailer_d[scoring_index_map["Result logic"]]
                                   │                         if "Result logic" in scoring_index_map else ""
                                   ├─ row["score-category"] = … (analogous)
                                   ├─ row["score-value"]    = … (analogous)
                                   │                         ◄── [CHANGE 4: lines 263–265 rewritten]
                                   └─ placeholders + return (UNCHANGED, lines 266–269)

dry_run() also calls classify_headers() at line 286 — its 3-tuple unpack must absorb
the two new return slots with `_, _` (D-05-07 keeps warnings out of dry_run).
```

### Recommended Project Structure
No structural changes — single-file implementation (D-13). All edits in `quizify_csv_ingest.py`; tests stay in `tests/`.

```
quizify-csv-to-json-webhook/
├── quizify_csv_ingest.py         # 5 surgical edits (see Change 1–4 above + dry_run unpack)
├── tests/
│   ├── conftest.py               # +1 fixture (scoring_index_map_default)
│   ├── test_row_builder.py       # 8 build_row(...) call sites updated; +new test class
│   ├── test_layout.py            # 1 classify_headers(...) unpack updated; +new test class
│   └── (new or extended)         # default-order regression — see Validation Architecture
├── docs/
│   └── quizify-submissions.csv   # 42-row sample (TRAIL-03 input)
└── README.md                     # remove positional caveat lines 65–69, 129–132; update wording
```

### Pattern 1: Pure-function header parser returning a position map
**What:** `classify_headers` already validates layout once at CSV open and returns parsed slices. Extending it to also build the scoring index map keeps O(1) per-row downstream and matches the codebase's "header inspection is pure, side-effects in convert" split (D-05-07).
**When to use:** Whenever a row-loop value is a function of headers only — compute once, pass through.
**Example:**
```python
# Source: quizify_csv_ingest.py:69-74 (existing pattern — preserve as-is per D-05-02)
for i, expected in enumerate(trailer):
    hi = n - t_len + i
    if normalize_key(header_row[hi]) != normalize_key(expected):
        raise LayoutError(
            f"Trailer mismatch at column {hi}: expected {expected!r}, got {header_row[hi]!r}"
        )

# NEW (per D-05-01, D-05-03): right after the existing trailer check
scoring_index_map: dict[str, int] = {}
missing_trio_names: list[str] = []
trio_canonicals = DEFAULT_TRAILER[:3]   # ("Result logic", "Score category", "Score value")
trailer_raw = header_row[n - t_len :]
for canonical in trio_canonicals:
    canonical_norm = _norm_for_match(canonical)
    idx = next(
        (i for i, h in enumerate(trailer_raw)
         if _norm_for_match(h) == canonical_norm),
        None,
    )
    if idx is not None:
        scoring_index_map[canonical] = idx
    else:
        missing_trio_names.append(canonical)
return prefix_raw, dynamic, trailer_raw, scoring_index_map, tuple(missing_trio_names)
```

### Pattern 2: Index-map gated read with `""` default
**What:** Replace `trailer_cells_decoded[N] if len(...) > N else ""` with `trailer_cells_decoded[scoring_index_map[name]] if name in scoring_index_map else ""`. Same shape, named guard.
**When to use:** Build_row scoring trio reads (lines 263–265).
**Example:**
```python
# Source: quizify_csv_ingest.py:263-265 (current — replace verbatim)
row["result-logic"] = trailer_cells_decoded[0] if len(trailer_cells_decoded) > 0 else ""
row["score-category"] = trailer_cells_decoded[1] if len(trailer_cells_decoded) > 1 else ""
row["score-value"] = trailer_cells_decoded[2] if len(trailer_cells_decoded) > 2 else ""

# NEW (D-05-04):
row["result-logic"]   = trailer_cells_decoded[scoring_index_map["Result logic"]]   if "Result logic"   in scoring_index_map else ""
row["score-category"] = trailer_cells_decoded[scoring_index_map["Score category"]] if "Score category" in scoring_index_map else ""
row["score-value"]    = trailer_cells_decoded[scoring_index_map["Score value"]]    if "Score value"    in scoring_index_map else ""
```

### Pattern 3: Once-per-CSV warning loop in `convert`
**What:** `convert()` iterates `missing_trio_names` once after `classify_headers` succeeds and before the data row loop, emitting one `logging.warning` per name.
**When to use:** Header-level diagnostics that must appear before any row processing (matches the D-05-07 placement).
**Example:**
```python
# Source: NEW — insert between current line 347 (after classify_headers try/except)
# and current line 349 (dynamic_headers_decoded = ...)

OUTPUT_KEY_BY_CANONICAL = {
    "Result logic":   "result-logic",
    "Score category": "score-category",
    "Score value":    "score-value",
}

for name in missing_trio_names:
    # Locked D-05-08 template; canonical name + output key only — T-PII-01 compliant.
    logging.warning(
        "trailer column %r absent from CSV header; emitting empty string for %s in all rows",
        name,
        OUTPUT_KEY_BY_CANONICAL[name],
    )
```

Note: `logging` formats with `%r` will produce `'Result logic'` (single quotes) which matches the D-05-08 template exactly.

### Anti-Patterns to Avoid
- **Substring match against trailer headers** — Pitfall 9. `"Score" in header` matches both "Score category" and "Score value". Use `_norm_for_match(header) == _norm_for_match(canonical)` (exact equality).
- **Positional fallback `or trailer_cells_decoded[0]`** — Pitfall 10, explicitly forbidden by D-05-10. The phase exists to remove this exact pattern.
- **Using `normalize_key` (NFC-only) or `.lower()` for trio match** — Pitfall 11. Spanish-locale Quizify exports may carry accented or differently-cased headers; only `_norm_for_match` (NFC + casefold) is safe.
- **Subprocess-based test for the new lookup** — Pitfall 16. The 1.09 s baseline is the budget; D-05-12 mandates direct unit calls.
- **Logging the trailer header value or any cell** — T-PII-01. The warning names the canonical (constant) column name only.
- **Returning the index map keyed by the normalized form** — D-05-01 says map keys are the *display* form from `DEFAULT_TRAILER`. Build with normalized comparison, store with display-form keys.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unicode-aware case-insensitive equality | `header.lower() == canonical.lower()` | `_norm_for_match(header) == _norm_for_match(canonical)` (line 146) | NFC normalization + casefold handles accented Spanish headers; `.lower()` does not casefold (Pitfall 11) |
| Capturing log records in tests | `subprocess.run + grep stderr` | pytest `caplog` fixture | Faster (no subprocess), structured access to `LogRecord.message`, `LogRecord.levelname` [CITED: https://docs.pytest.org/en/stable/how-to/logging.html] |
| Locating the trio canonicals | Re-declaring `("Result logic", ...)` | `DEFAULT_TRAILER[:3]` (line 25-32) | Single source of truth; matches CONTEXT.md `code_context` insight |
| Output-key mapping | Hard-coding strings in two places | `OUTPUT_KEY_BY_CANONICAL` constant (or derived as `name.lower().replace(" ", "-")`) | Mapping is locked categorical; constant is more grep-friendly than computation |

**Key insight:** Every primitive needed already exists in `quizify_csv_ingest.py` (`_norm_for_match`, `DEFAULT_TRAILER`, `LayoutError`, `logging.warning`). This phase is composition, not new infrastructure.

## Common Pitfalls

### Pitfall A: dry_run also calls classify_headers
**What goes wrong:** The 3-tuple unpack at `quizify_csv_ingest.py:286` (`_prefix, dynamic, _trailer_h = classify_headers(header, trailer)`) becomes a `ValueError: too many values to unpack` when `classify_headers` returns 5 values.
**Why it happens:** Easy to forget the second call site when refactoring.
**How to avoid:** Update `dry_run` line 286 to `_prefix, dynamic, _trailer_h, _scoring_map, _missing = classify_headers(header, trailer)`. Per D-05-07, `dry_run` does NOT emit the missing-column warnings (it skips the row loop entirely; warnings are a `convert`-only concern).
**Warning signs:** `--dry-run` exits non-zero with `ValueError` after the change; `test_dry_run_with_trailer_columns_override` (test_layout.py:60) and `test_dry_run_stderr_row_count` (test_layout.py:98) fail.

### Pitfall B: `test_layout.py:27` unpacks classify_headers as 3-tuple
**What goes wrong:** `prefix, dynamic, trailer = classify_headers(header)` becomes a `ValueError`.
**Why it happens:** Only one production caller is in scope mentally; the test caller is easy to miss.
**How to avoid:** Update line 27 to `prefix, dynamic, trailer, scoring_index_map, missing_trio_names = classify_headers(header)` and add assertions on the new fields (this becomes the natural home for the "default-order index-map" unit test).
**Warning signs:** `test_sample_csv_header_classification` fails with `ValueError`.

### Pitfall C: 8 build_row(...) call sites in test_row_builder.py
**What goes wrong:** Each call site needs the new `scoring_index_map` arg or pytest collection errors.
**Why it happens:** Mechanical churn; one missed site fails the whole file.
**How to avoid:** Use the `scoring_index_map_default` fixture (D-05-06) and add it to each call. The exact 8 call sites are at lines 113, 130, 137, 149, 174, 201, 207, 220, 232, 278, 287, 298, 314, 324 — totalling **14 call sites** (the CONTEXT.md "all 71 existing tests" framing is correct, but the literal call-site count is 14). Plan to use a sed-friendly migration: every `build_row(prefix_d, dyn_d, trailer_d, headers_d, quiz_title=…)` call gets a trailing positional arg or kwarg.
**Warning signs:** Pytest collects 0 tests from `test_row_builder.py` due to import-time failure.

### Pitfall D: Synthetic short-trailer rows in test_row_builder.py
**What goes wrong:** Some synthetic trailers have only 2-3 cells; if the test passes `scoring_index_map_default = {"Result logic": 0, "Score category": 1, "Score value": 2}` but the trailer has only 2 cells, `trailer_d[2]` raises `IndexError` instead of producing `""`.
**Why it happens:** The current `len(trailer_cells_decoded) > N` bounds check is removed by D-05-04's new form (`if name in scoring_index_map else ""` — bounds check is implicit only when the column is missing from the *header*, not when the *cell* is missing from a single row).
**How to avoid:** Audit every `trailer = ["", "", ...]` literal in `test_row_builder.py`. The conftest fixtures (`full_answers_row`, `red_flag_short_circuit_row`, `multi_select_synthetic_row`) all build 6-cell trailers — safe. The synthetic short-trailer case in `_minimal_decoded_inputs` (line 273) builds 6 cells too — safe. **All current test trailers are 6-cell**, so this is a non-issue *for existing tests*. However, the planner must spec build_row's behavior under "header has the column, but the data row is short" — recommend keeping a defensive bounds check OR documenting that row-length mismatch is already enforced upstream in `convert` (line 355) so build_row never sees a short trailer in practice.
**Warning signs:** `IndexError` in any test that uses a < 6-cell trailer literal.

### Pitfall E: Live fixture CSV is currently dirty
**What goes wrong:** `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` has uncommitted changes at the time of this research (43 insertions / 43 deletions per `git diff --stat`). Running `pytest` *now* produces 16 errors + 16 failures because `Last name` column header is `' "Last name"      '` (the working-copy version has stray whitespace + quotes around contact prefix headers).
**Why it happens:** Some upstream edit (CSV normalization?) modified the fixture; tests assume the committed version.
**How to avoid:** **Plan must call this out as a precondition.** Before ANY Phase 5 implementation, restore the fixture: `git checkout HEAD -- quizify-csv-to-json-webhook/docs/quizify-submissions.csv`, OR confirm with user whether the new fixture content is intentional (in which case the contact-prefix layout check fails for unrelated reasons and Phase 5 cannot land cleanly). **The "71 tests passing in 1.09 s" baseline cited in CONTEXT.md is currently false in the working copy.**
**Warning signs:** `pytest` shows `Contact prefix mismatch at column 1: expected 'Last name', got ' "Last name"      '` errors — these are pre-existing, NOT caused by Phase 5.

### Pitfall F: README's "stays positional" caveat must be removed (not just amended)
**What goes wrong:** README lines 62–69 and 129–132 explicitly tell operators that `--trailer-columns` overrides "remain positional" and "will misalign scoring fields silently." This is the v1.0-correct documentation of the v1.0 bug. After Phase 5, these paragraphs become *false* — they cannot stay as-is, even amended.
**Why it happens:** Easy to miss because the change is "delete a warning that no longer applies" rather than "add new docs."
**How to avoid:** Plan a README task that removes (not edits) lines 62–69's "Note:" block and lines 129–132's bullet, replaces with new wording aligned to TRAIL-01 ("scoring fields are bound by canonical column name; reordering `--trailer-columns` is now safe"). Test `test_readme_help_alignment.py` only checks flag presence, not these paragraphs — no drift-test impact, but reviewer must verify wording.
**Warning signs:** Operators reading post-v1.1 README see contradictory guidance.

### Pitfall G: TRAIL-03 regression — golden file does NOT yet exist
**What goes wrong:** CONTEXT.md `<specifics>` says "if a golden-file fixture for the 42-row output already exists in the test suite, reuse it; otherwise generate once." Search confirms **no golden-file output JSON exists** (`docs/` has only the CSV input and the `webhook-quizify-format-example.json` single-row example, not a 42-row v1.0 output). The closest is `tests/test_structural_invariants.py`'s module-scoped `emitted_payload` fixture — but that runs the *current* CLI, so it's a self-comparison, not a v1.0-vs-v1.1 comparison.
**Why it happens:** v1.0 didn't need byte-level cross-version regression because nothing changed.
**How to avoid:** **Generate the golden file as part of Phase 5 setup.** Recommended approach: (1) on `main` (pre-Phase-5), run `python quizify_csv_ingest.py docs/quizify-submissions.csv -o tests/fixtures/v1.0_default_order_output.json`, (2) commit it before any production change, (3) add `test_default_order_byte_identical_to_v1_0_baseline` that runs the CLI with default args and `assert json.loads(open(golden).read()) == json.loads(stdout)`. Byte-identity comparison is fragile (whitespace, key order); structural-equality (`json.loads ==`) is safer and still proves TRAIL-03 because dict insertion order is preserved by Python 3.7+ and `json.dump(..., indent=2)` is deterministic.
**Warning signs:** Phase 5 ships without a real "v1.0 baseline" file — TRAIL-03 success criterion is then unverifiable.

## Runtime State Inventory

> Phase 5 is a code-only refactor. No databases, no live services, no OS state, no secret rename, no installed-package rename.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by inspection (no DB, no Mem0, no ChromaDB). The script is invoked ad-hoc; outputs go to stdout or `--output PATH`. | None |
| Live service config | None — verified. The Make.com workflow consumes the JSON payload, but Phase 5 does NOT change payload *shape* (default-order callers see byte-identical output per TRAIL-03). | None |
| OS-registered state | None — no Task Scheduler / launchd / systemd / pm2. | None |
| Secrets / env vars | `QUIZIFY_QUIZ_TITLE` is the only env var; unaffected by Phase 5. | None |
| Build artifacts | None — no installed package, no `egg-info`, no compiled binary. `pytest.ini` does set `pythonpath = .` but is path-based, not name-based. | None |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.7+ | Runtime + tests | ✓ | 3.10.19 (verified by pyenv path in pytest run) | — |
| pytest | Test runner | ✓ | (in `requirements-dev.txt`, version unpinned) | — |
| `_norm_for_match` (in-repo) | Trio comparison | ✓ | quizify_csv_ingest.py:146 | — |
| `DEFAULT_TRAILER` (in-repo) | Canonical names | ✓ | quizify_csv_ingest.py:25-32 | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (unpinned in `requirements-dev.txt`; collected 71 tests as of v1.0 close) |
| Config file | `quizify-csv-to-json-webhook/pytest.ini` (`pythonpath = .`) |
| Quick run command | `cd quizify-csv-to-json-webhook && python3 -m pytest -q` |
| Full suite command | `cd quizify-csv-to-json-webhook && python3 -m pytest -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAIL-01 | `classify_headers` returns scoring_index_map matching scrambled `--trailer-columns` order | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_scrambled_order_maps_by_name -x` | ❌ Wave 0 (new test class) |
| TRAIL-01 | `build_row` reads scoring trio from name-keyed indices, not [0/1/2] | unit | `pytest tests/test_row_builder.py::TestScrambledTrailer::test_scrambled_order_binds_correctly -x` | ❌ Wave 0 (new test class) |
| TRAIL-01 | NFC+casefold equality matches accented/case-variant trio header | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_normalization_handles_case_and_diacritics -x` | ❌ Wave 0 |
| TRAIL-02 | Missing trio column → `missing_trio_names` contains canonical name | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_missing_column_listed -x` | ❌ Wave 0 |
| TRAIL-02 | `convert()` emits exactly one logging.warning per missing canonical with locked D-05-08 message text | unit (caplog) | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_warning_message_matches_locked_template -x` | ❌ Wave 0 |
| TRAIL-02 | `build_row` emits `""` for missing trio name (no positional fallback) | unit | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_missing_column_emits_empty_string -x` | ❌ Wave 0 |
| TRAIL-02 | Empty cell in *present* column is silent (D-03 carry-forward) | unit | (existing) `tests/test_row_builder.py::test_empty_scoring_emits_empty_strings` — must stay green after refactor | ✅ |
| TRAIL-02 | PII safety: warning contains no cell content / contact tokens | unit | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_warning_pii_safe -x` | ❌ Wave 0 |
| TRAIL-03 | Default `--trailer-columns` → live 42-row sample output structurally equal to v1.0 baseline | regression | `pytest tests/test_default_order_regression.py -x` | ❌ Wave 0 (file + golden fixture) |
| TRAIL-03 | All 14 existing `build_row(...)` call sites and the 1 `classify_headers(...)` test unpack pass with new signatures | unit | (existing — entire test_row_builder.py + test_layout.py) | ✅ (after mechanical update) |

### Sampling Rate
- **Per task commit:** `pytest -q` (full suite — 1.09 s baseline; budget 2.5 s post-Phase-5 per Pitfall 16).
- **Per wave merge:** `pytest -q --tb=short` (same — fast enough to run unconditionally).
- **Phase gate:** Full suite green; new TRAIL-01/02/03 test classes all green; `caplog` assertion confirms exact D-05-08 message text.

### Wave 0 Gaps
- [ ] `tests/conftest.py` — add `scoring_index_map_default` fixture (D-05-06)
- [ ] `tests/test_layout.py::TestScoringIndexMap` — new test class covering: default-order map, scrambled-order map, normalization (case+diacritic) match, missing-column listing, and the strict positional check still raises LayoutError when trailer lengths don't align (D-05-02 carry-forward proof)
- [ ] `tests/test_row_builder.py::TestScrambledTrailer` — pass `scoring_index_map={"Result logic": 2, "Score category": 1, "Score value": 0}` (reversed) and assert each row field maps to the named-cell value, NOT the positional [0/1/2] cell
- [ ] `tests/test_row_builder.py::TestMissingColumnWarning` — caplog-based tests for the locked D-05-08 message, missing-column → `""`, and PII safety
- [ ] `tests/test_default_order_regression.py` — TRAIL-03 byte/structural identity vs golden fixture
- [ ] `tests/fixtures/v1.0_default_order_output.json` — generate before any production change (see Pitfall G)
- [ ] All 14 `build_row(...)` call sites in `test_row_builder.py` — append `scoring_index_map_default` fixture arg (mechanical churn)
- [ ] `tests/test_layout.py:27` — extend 3-tuple unpack to 5-tuple
- [ ] Restore `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` to committed version OR confirm with user the new content is intentional (Pitfall E precondition)

## Security Domain

> ASVS Level 1, security_enforcement enabled (config.json). Phase 5 surface is narrow: input validation + logging output.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI tool, no auth surface |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | File-system only; OS handles |
| V5 Input Validation | **yes** | CSV header is operator-controlled input; `classify_headers` validates layout (`LayoutError`) and now also normalizes trio names via `_norm_for_match`. The new `scoring_index_map` build is pure dict construction over already-bounded inputs (trailer is `header_row[n - t_len:]`, length `t_len`); no injection surface. |
| V6 Cryptography | no | Nothing crypto-adjacent |
| V7 Error Handling | **yes** | New `logging.warning` calls must follow T-PII-01: column name + output key only, never trailer cell content. The locked D-05-08 template is compliant by construction (categorical-only). |
| V8 Data Protection | **yes (PII)** | T-PII-01 carry-forward: warnings must not leak email/phone/name/free-text. The new warning emits only canonical column names (compile-time constants) and output keys (compile-time constants). |
| V14 Configuration | no | No config files |

### Known Threat Patterns for stdlib Python CSV CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII leakage via diagnostic logging | Information Disclosure | Categorical-only message construction; existing pattern (`map_status` line 127, row-mismatch warning line 356); locked D-05-08 template; `caplog` test asserts no email/phone in message |
| Header-row content used in error message | Information Disclosure | `LayoutError` message *does* contain the offending header value (line 67, 73) — this is **pre-existing, not a Phase 5 regression**. The new warning template names only the *canonical* (constant) name, so Phase 5 does NOT add any new info-disclosure surface. |
| Substring-collision exploit | Tampering | Pitfall 9 — exact NFC+casefold equality, never substring. Mitigated by D-05-03. |
| Positional fallback re-introduces v1.0 mis-bind | Tampering / silent data corruption | Pitfall 10 — explicit code-review check for `or trailer_cells_decoded[N]`; D-05-10 enforces; new tests assert empty-string-on-missing, not fallback. |

## Project Constraints (from CLAUDE.md)

> No `./CLAUDE.md` file exists in the working directory. Only the user-global `~/.claude/CLAUDE.md` (graphify slash command, user email, current date) was visible — none of those directives bear on Phase 5 implementation.

Project-level discipline therefore comes from `PROJECT.md`:
- D-13: stdlib-only at runtime; no new entries to `requirements.txt` (none exists; only `requirements-dev.txt`).
- D-05: locked top-level JSON key order — Phase 5 does NOT change key order, only the *value* of three existing keys.
- T-PII-01: PII-safe stderr logging — warnings carry canonical column names + categorical enum values only, never cell content. Locked D-05-08 template is compliant by construction.
- D-11: README structure locked at 10 sections; drift test (`test_readme_help_alignment.py`) checks that every CLI long-flag appears in README. **Phase 5 adds no new flags**, so the drift test is unaffected — but README content updates (Pitfall F) still need a human content review.

## Code Examples

### Building the scoring_index_map (insert into classify_headers after existing trailer check)
```python
# Source: composed from quizify_csv_ingest.py:69-78 + D-05-01/D-05-03
# Add after line 74 (existing trailer-mismatch check), before line 75 (slicing)
prefix_raw = header_row[:p_len]
dynamic = header_row[p_len : n - t_len]
trailer_raw = header_row[n - t_len :]

scoring_index_map: dict[str, int] = {}
missing_trio_names: list[str] = []
for canonical in DEFAULT_TRAILER[:3]:           # ("Result logic", "Score category", "Score value")
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

### Updated build_row scoring block (replaces lines 263–265)
```python
# Source: D-05-04 verbatim
row["result-logic"]   = trailer_cells_decoded[scoring_index_map["Result logic"]]   if "Result logic"   in scoring_index_map else ""
row["score-category"] = trailer_cells_decoded[scoring_index_map["Score category"]] if "Score category" in scoring_index_map else ""
row["score-value"]    = trailer_cells_decoded[scoring_index_map["Score value"]]    if "Score value"    in scoring_index_map else ""
```

### convert() warning loop (insert between line 347 and line 349)
```python
# Source: composed from D-05-07 + D-05-08
_OUTPUT_KEY_BY_CANONICAL = {
    "Result logic":   "result-logic",
    "Score category": "score-category",
    "Score value":    "score-value",
}
# (Place this dict at module top with other constants, alongside DEFAULT_TRAILER.)

# Inside convert(), after classify_headers succeeds:
for name in missing_trio_names:
    logging.warning(
        "trailer column %r absent from CSV header; "
        "emitting empty string for %s in all rows",
        name,
        _OUTPUT_KEY_BY_CANONICAL[name],
    )
```

### caplog-based test for D-05-08 message
```python
# Source: pytest caplog docs + D-05-08 locked template
# https://docs.pytest.org/en/stable/how-to/logging.html
def test_missing_result_logic_column_emits_locked_warning(tmp_path, caplog):
    import logging
    # Build a CSV whose --trailer-columns omits "Result logic"
    custom_trailer = ("Score category", "Score value", "Answer tags",
                      "Time to complete (mm:ss)", "Date")
    # ... write fixture CSV with that trailer ...
    with caplog.at_level(logging.WARNING):
        rc = convert(csv_path, custom_trailer, output=None, quiz_title="")
    assert rc == 0
    matches = [r for r in caplog.records
               if "absent from CSV header" in r.getMessage()
               and "'Result logic'" in r.getMessage()
               and "result-logic in all rows" in r.getMessage()]
    assert len(matches) == 1, [r.getMessage() for r in caplog.records]
    # PII safety
    msg = matches[0].getMessage()
    assert "@" not in msg
    assert "+" not in msg
```

### TRAIL-03 default-order regression
```python
# Source: NEW test file tests/test_default_order_regression.py
def test_default_order_byte_identical_to_v1_0_baseline(sample_csv_path, tmp_path):
    """TRAIL-03: default --trailer-columns produces structurally identical
    output to the v1.0 baseline (committed before Phase 5 production change).
    """
    import json, subprocess, sys
    SCRIPT = sample_csv_path.parent.parent / "quizify_csv_ingest.py"
    GOLDEN = sample_csv_path.parent.parent / "tests" / "fixtures" / "v1.0_default_order_output.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(sample_csv_path)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    actual = json.loads(result.stdout)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Positional `trailer_cells_decoded[0..2]` lookup | Name-keyed `scoring_index_map[canonical]` lookup | Phase 5 (this) | Non-default `--trailer-columns` callers receive correct scoring fields automatically |
| `LayoutError` for any trailer mismatch | `LayoutError` for trailer-shape mismatch + `logging.warning` for trio-name absence | Phase 5 | Soft-failure for missing trio names lets non-validating runs continue with empty string per D-05-09 |
| `--trailer-columns` overrides documented as "stays positional, will misalign" | `--trailer-columns` overrides documented as "scoring fields bound by canonical name; reorder is safe" | Phase 5 | README content change required (Pitfall F) |

**Deprecated/outdated:**
- D-15 (positional trailer indexing rationale): retired this phase. Update PROJECT.md Key Decisions table — change the "⚠️ Revisit" row's outcome from "✓ Good — split only if v2 scope lands" to "Retired by TRAIL-01 (Phase 5, v1.1)".
- README lines 62–69 "Note:" caveat and lines 129–132 "Limitations" bullet about scoring staying positional.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `caplog` is the cleanest mechanism to assert the locked D-05-08 message; no alternative was tried | Standard Stack / Code Examples | LOW — `capsys` is a drop-in alternative if `configure_logging` config interferes with caplog's handler. |
| A2 | Top-level helper `_build_scoring_index_map` is preferred over inlining inside `classify_headers` | Architecture Patterns | LOW — D-05 marks this as Claude's discretion; either choice satisfies the contract. |
| A3 | `tuple[str, ...]` for `missing_trio_names` matches existing style | Standard Stack | LOW — D-05 marks this as Claude's discretion. |
| A4 | Restoring the dirty `quizify-submissions.csv` to HEAD is the right precondition rather than incorporating the new content | Pitfall E | MEDIUM — if user intentionally edited the fixture, restoring it loses that work. **Plan must surface as an explicit user-confirmation step, not silent restore.** |
| A5 | Generating the v1.0 golden fixture from the *current* `main` branch (post-Phase-4) is equivalent to "v1.0 baseline" because Phases 1–4 made no changes to scoring trio output | Pitfall G / Validation Architecture | LOW — Phase 4 was JS-only (zero Python edits per CONTEXT.md `<domain>`); confirmed by `git log` showing Phase 4 changes only under `make-scripts/` and docs. |
| A6 | The `pytest` `caplog` records intercept `logging.warning` calls correctly even with `configure_logging`'s `force=True` reset | Code Examples | LOW — `caplog.at_level(logging.WARNING)` installs its own handler; pytest's docs state this works alongside basicConfig. If it doesn't, fall back to `capsys.readouterr().err` substring assertion. |

## Open Questions (RESOLVED)

1. **Is the dirty `quizify-submissions.csv` working-copy change intentional?**
   - What we know: 43+/43- diff vs HEAD; tests fail with `Contact prefix mismatch at column 1: expected 'Last name', got ' "Last name"      '`.
   - **RESOLVED:** User confirmed the diff was an accidental line-ending/BOM rewrite (not intentional). CSV reverted via `git checkout --` before plans were spawned; baseline `71 passed in 1.10s` re-confirmed. Plan 01 Task 1 step 1 verifies cleanliness as a non-destructive precondition (no revert action).

2. **Where does the v1.0 golden fixture live — `tests/fixtures/` or `docs/`?**
   - What we know: `docs/` has the canonical input CSV and the single-row example payload; `tests/` has no `fixtures/` subdir today.
   - **RESOLVED:** Adopted recommendation. Plan 01 Task 1 creates `quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json` (test-only artifact, not user-facing); convention follows the recommendation.

3. **Should the `_build_scoring_index_map` helper be top-level or nested?**
   - What we know: D-05 marks this as Claude's discretion; existing helpers (`_norm_for_match`, `_looks_iso`, `_resolve_quiz_title`) are top-level.
   - **RESOLVED:** Top-level (planner's choice in Plan 02 Task 2 production excerpt — matches existing helper style).

4. **Does the user want a single commit for all of Phase 5, or split (production / tests / docs)?**
   - D-05 marks as Claude's discretion.
   - **RESOLVED:** Split implicitly enforced by the wave structure — Plan 01 (Wave 0 fixtures), Plan 02 (Wave 1 production + test churn + new test classes), Plan 03 (Wave 2 regression test + docs). Each plan commits atomically and each ends in a green pytest. The original 3-commit recommendation is preserved by the plan boundaries.

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `quizify-csv-to-json-webhook/quizify_csv_ingest.py` lines 25-32 (DEFAULT_TRAILER), 51-78 (classify_headers), 146-147 (`_norm_for_match`), 199-269 (build_row), 277-307 (dry_run), 310-384 (convert)
- Direct code inspection: `quizify-csv-to-json-webhook/tests/conftest.py` (3 fixtures, all 6-cell trailers)
- Direct code inspection: `quizify-csv-to-json-webhook/tests/test_row_builder.py` (14 build_row call sites)
- Direct code inspection: `quizify-csv-to-json-webhook/tests/test_layout.py:27` (single classify_headers unpack site)
- Direct code inspection: `quizify-csv-to-json-webhook/tests/test_logging_pii.py` (T-PII-01 pattern reference)
- Direct code inspection: `quizify-csv-to-json-webhook/tests/test_structural_invariants.py` (module-scoped fixture pattern, PHASE_3_REQUIRED_KEYS)
- Direct code inspection: `quizify-csv-to-json-webhook/README.md` lines 62-69, 129-132 (positional caveats to delete)
- `pytest --collect-only -q` output: 71 tests across 8 files
- `git diff --stat HEAD` confirming `quizify-submissions.csv` working-copy modification
- `.planning/phases/05-python-trailer-hardening/05-CONTEXT.md` (D-05-01 through D-05-12 locked decisions)
- `.planning/REQUIREMENTS.md` (TRAIL-01/02/03)
- `.planning/research/PITFALLS.md` (Pitfalls 9, 10, 11, 16)
- `.planning/PROJECT.md` (D-05, D-13, T-PII-01, D-15 retirement note)
- `.planning/STATE.md` (v1.1 locked decisions)
- `.planning/MILESTONES.md` (v1.0 stats and TRAIL-03 documentation home)

### Secondary (MEDIUM confidence)
- pytest `caplog` documentation pattern [CITED: https://docs.pytest.org/en/stable/how-to/logging.html] — standard mechanism for asserting log records in unit tests

### Tertiary (LOW confidence)
- None; this phase is so well-bounded by CONTEXT.md that no LOW-confidence claims were necessary.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is in-repo and stdlib; verified by file inspection
- Architecture: HIGH — patterns derived directly from existing code structure and locked D-05 decisions
- Pitfalls: HIGH — Pitfalls A through G all confirmed by direct file inspection (line numbers, call-site counts, existing test fixtures, fixture state)
- Validation: HIGH — pytest collection output confirms exact test count (71); existing test infrastructure documented; gap list is exhaustive

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (30 days; phase scope is small and stable)
