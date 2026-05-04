# Architecture Research

**Domain:** CSV-to-webhook-JSON CLI with iPaaS consumer surface (v1.1 hardening)
**Researched:** 2026-05-03
**Confidence:** HIGH — based on full source read of `quizify_csv_ingest.py` (427 LOC),
both Make.com JS files, the example payload, and existing test fixtures.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operator invocation                                                  │
│  python quizify_csv_ingest.py <csv_path> [flags]                     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        main() / argparse     │  ← new: --validate flag
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────▼──────────────────────┐
              │           convert()  (or dry_run())        │
              │                                            │
              │  1. open CSV utf-8-sig                     │
              │  2. classify_headers()                     │
              │  3. decode dynamic headers                 │
              │  4. per row: decode + build_row()          │
              │  5. accumulate results[]                   │
              │  6. [NEW v1.1] validate_payload()          │
              │  7. json.dump to stdout / -o file          │
              └──────────────┬──────────┬─────────────────┘
                             │          │
              ┌──────────────▼──┐  ┌────▼──────────────────────────────┐
              │  build_row()    │  │  validate_payload()  [VALI-01 NEW] │
              │                 │  │  stdlib jsonschema via             │
              │  - contact map  │  │  json.loads(schema_json) +        │
              │  - TAG_HEADER   │  │  _validate_against_schema()       │
              │  - shape_answer │  └────────────────────────────────────┘
              │  - TRAIL-01 NEW │
              │    TRAILER_     │
              │    HEADER_MAP   │
              │  - SCORING_     │
              │    PLACEHOLDERS │
              └─────────────────┘

┌─────────────────────── Make.com iPaaS (external, co-owned) ──────────┐
│                                                                       │
│  Module 1: quizify-mapping.js                                         │
│    reads record["product-recommendation"]  ← CONTRACT-01 FIX         │
│    emits tag "peri_menu"                   ← MAKE-FIX-01 FIX         │
│                                                                       │
│  Module 2: score-calculations.js                                      │
│    checks hasTag(tags, "peri-menu")        ← MAKE-FIX-01 FIX         │
│    inverted is_athlete condition L247-250  ← MAKE-FIX-01 FIX         │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | v1.1 Change? |
|-----------|---------------|--------------|
| `main()` (L387-427) | Arg parsing, flag dispatch, exit code return | Add `--validate` flag + wire to `convert()` |
| `classify_headers()` (L51-78) | Splits header row into contact / dynamic / trailer slices | No change |
| `convert()` (L310-384) | Outer loop: open CSV, per-row decode+build, JSON dump | Add conditional `validate_payload()` call after accumulation |
| `dry_run()` (L277-307) | Layout preview with no JSON output | No change; `--validate` runs in `convert()` path only |
| `build_row()` (L199-269) | Assemble one webhook dict from decoded cell slices | Scoring lookup: replace positional `[0..2]` with `TRAILER_HEADER_MAP` (TRAIL-01) |
| `decode_cell()` (L98-100) | HTML entity decode on a single cell string | No change |
| `shape_answer()` (L103-113) | Multi-select vs object-array heuristic | No change |
| `match_tags_to_questions()` (L163-196) | NFC+casefold TAG_HEADER_MAP distribution | No change |
| `_resolve_quiz_title()` (L130-143) | CLI > env > "" precedence | No change |
| `validate_payload()` **[NEW]** | Load schema JSON, run validation loop over results, report errors PII-safely | New function, stdlib-only |
| `quizify-mapping.js` L102 | Read `product-recommendation` key | Fix: `record["product-recommendation"]` (CONTRACT-01) |
| `quizify-mapping.js` L167 | Emit peri-menu tag | Fix: emit `"peri-menu"` not `"peri_menu"` (MAKE-FIX-01) |
| `score-calculations.js` L213 | Check peri tag | Fix: `hasTag(tags, "peri-menu")` (MAKE-FIX-01) |
| `score-calculations.js` L247-250 | activity_profile assignment | Fix: invert condition — `if (data.is_athlete)` → `activity_profile = "athlete"` (MAKE-FIX-01) |

---

## Recommended Project Structure (v1.1 — stay single-file)

```
quizify-csv-to-json-webhook/
├── quizify_csv_ingest.py        # single-file impl — stays single-file (D-12)
├── docs/
│   ├── webhook-quizify-format-example.json   # canonical payload shape (existing)
│   └── webhook-schema.json                   # NEW: JSON Schema for VALI-01
├── make-scripts/
│   ├── quizify-mapping.js       # co-owned consumer — CONTRACT-01 + MAKE-FIX-01
│   ├── score-calculations.js    # co-owned consumer — MAKE-FIX-01
│   └── CONVENTIONS.md           # NEW: tag-name canon (CONTRACT-01 drift prevention)
└── tests/
    ├── test_readme_help_alignment.py    # existing — will catch --validate addition
    ├── test_row_builder.py              # existing
    ├── test_cli_emission.py             # existing
    ├── test_structural_invariants.py    # existing
    └── test_validation.py               # NEW: VALI-01 unit tests
```

**Structure rationale:**
- `docs/webhook-schema.json` mirrors `webhook-quizify-format-example.json` co-location; operators can diff them side-by-side. Schema is not inside `tests/` because it is a runtime artifact (loaded by `validate_payload()` when `--validate` is passed).
- `make-scripts/CONVENTIONS.md` is a lightweight 1-page doc that states the single invariant: tag strings shared between Python and JS use kebab-case (e.g., `peri-menu`, not `peri_menu`). This is the right-sized artifact for two 200-line files; a full spec would be over-engineered.
- No new Python module files. D-12 decision (single-file) remains valid at 427 LOC; VALI-01 adds ~40-60 lines, landing at ~490 LOC — well under any justified split threshold.

---

## Architectural Patterns

### Pattern 1: In-band post-accumulation validation (VALI-01)

**What:** `validate_payload()` is called inside `convert()` after `results` is fully assembled, before the `json.dump` call. When `--validate` is False (default), the call is a no-op (or skipped with an early-return guard). When True, iterate `results`, validate each dict against the loaded schema, collect schema-path violations, print them to stderr, and return a failure exit code.

**When to use:** After the accumulation loop, not inside `build_row()`. Keeps `build_row()` a pure function (no I/O). Avoids per-row schema-file I/O (schema is loaded once, before the loop).

**Why not per-row inside build_row():** `build_row()` is a pure function (returns dict + warning strings). Injecting schema validation would couple it to filesystem I/O and break the pure-function contract that the existing test suite relies on.

**Data flow with `--validate`:**

```
convert()
    accumulate results[]
    if args.validate:
        schema = _load_schema(SCHEMA_PATH)          # once
        errors = []
        for i, record in enumerate(results):
            errs = _validate_record(record, schema) # stdlib only
            for err in errs:
                errors.append(f"row {i+1}: {err}")  # schema path only, no cell content
        if errors:
            for e in errors: logging.error(e)
            return 1   # non-zero exit
    json.dump(results, ...)
```

**Data flow without `--validate` (default, preserves v1.0 behavior):**

```
convert()
    accumulate results[]
    json.dump(results, ...)   # identical to v1.0
```

**Dry-run interaction:** `--dry-run` calls `dry_run()`, not `convert()`. `validate_payload()` lives in `convert()`, so `--dry-run --validate` is a legal combination that runs the layout check only (no validation). Document this in CLI reference.

**Stdlib-only constraint (D-13):** Python's stdlib does not include a JSON Schema validator. Two options satisfy D-13:

1. Hand-roll a minimal structural checker (check required keys exist, check types of fixed keys, check `question-N`/`answers-N`/`answers-tags-N` triple pattern). No external dep. Sufficient to validate D-05 key-order invariants and presence. Recommended for v1.1.
2. Add `jsonschema` (PyPI) as a dev+runtime dep, breaking D-13. Not recommended unless the schema complexity justifies it.

For v1.1, implement option 1: a purpose-built `_validate_record(record, schema_dict)` that checks the subset of invariants derivable from the locked contract (D-05 key ordering is enforced by checking key list against expected sequence). This is 30-40 lines and satisfies the requirement without a new dep.

**Schema file (`docs/webhook-schema.json`) strategy:** Hand-write a minimal envelope schema rather than auto-generating from the example payload. Auto-generation from the example would embed question-specific values (`question-1` = "Rango de edad") as required string values, which is wrong — the schema validates structure, not quiz-specific content. The hand-written schema encodes:
- Required top-level keys in D-05 order: `email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags`, `quiz_title`, then `question-N`/`answers-N`/`answers-tags-N` pattern (checked by regex), then `result-logic`, `score-category`, `score-value`, then `product-recommendation`, `product-link-type`, `title`, `type-page-url`.
- Type constraints only for fixed-type keys (`email: string`, `tags: array`, `product-recommendation: null|string`, etc.).
- No constraints on `question-N` values (they are quiz-specific strings).

The schema file is a documentation artifact even when `--validate` is not used; operators can read it to understand the locked contract.

**D-05 key order in schema:** JSON Schema `properties` ordering is not normatively significant in the spec, but the hand-rolled validator can check `list(record.keys())` against the expected ordered sequence for the fixed keys (contact block + scoring tail), while treating the dynamic `question-N` block as ordered by N. This directly encodes D-05 as a machine-checkable invariant.

**PII-safe error reporting:** Validation errors report schema path and expected type, never cell content. Example safe message: `"row 3: key 'email' expected string, got null"` — this is schema-structural. Unsafe (forbidden): `"row 3: email 'user@example.com' failed pattern"`. Implement by catching structure-check failures that only reference key names and Python types, not cell values.

---

### Pattern 2: TRAILER_HEADER_MAP — name-based scoring lookup (TRAIL-01)

**What:** Replace positional `trailer_cells_decoded[0]`, `[1]`, `[2]` with a name-based lookup analogous to `TAG_HEADER_MAP`. Add a module-level constant:

```python
TRAILER_SCORE_MAP = {
    "result-logic":    "result logic",      # NFC+casefold substring of trailer header
    "score-category":  "score category",
    "score-value":     "score value",
    "status-date":     "date",              # also used for statusDate (trailer index 5 today)
}
```

**Lookup function** (new, ~15 lines):

```python
def _lookup_trailer_cell(
    canonical: str,
    trailer_headers: list[str],
    trailer_cells_decoded: list[str],
) -> str:
    kw = TRAILER_SCORE_MAP[canonical]
    kw_norm = _norm_for_match(kw)
    for i, h in enumerate(trailer_headers):
        if kw_norm in _norm_for_match(h):
            return trailer_cells_decoded[i] if i < len(trailer_cells_decoded) else ""
    return ""
```

`build_row()` receives `trailer_headers_decoded` (already available in `convert()` as `_trailer_h` from `classify_headers()` — currently unused after classification). Pass it through to `build_row()`.

**Signature change to `build_row()`:**

```python
# Before (v1.0):
def build_row(prefix_cells_decoded, dynamic_cells_decoded, trailer_cells_decoded,
              dynamic_headers_decoded, quiz_title) -> tuple[dict, list[str]]:

# After (v1.1):
def build_row(prefix_cells_decoded, dynamic_cells_decoded, trailer_cells_decoded,
              dynamic_headers_decoded, trailer_headers_decoded, quiz_title) -> tuple[dict, list[str]]:
```

**NFC+casefold vs exact match:** Use NFC+casefold substring match (same as `TAG_HEADER_MAP`), not exact match. Rationale: trailer headers are operator-controlled via `--trailer-columns`; an operator supplying `"Result Logic"` or `" result logic "` should still bind correctly. Substring match on the known keyword (`"result logic"`) handles case and leading/trailing whitespace variation without a special trim step. Exact match would break on trivial casing differences and undermine the robustness goal.

**`--trailer-columns` backwards compatibility:** Today the flag overrides the *names* of trailer columns (for `classify_headers()`), and scoring reads positions `[0..2]` within whatever is resolved. After TRAIL-01, scoring reads by *name* within the resolved trailer. The flag remains unchanged in syntax. Backwards compat is preserved if the operator supplies trailer names that include `"result logic"`, `"score category"`, `"score value"`, `"date"` as substrings — which they will for any standard Quizify export. Non-standard trailer columns that don't contain those substrings will fall back to `""` (current fallback behavior for missing cells), which is strictly better than silent positional mis-binding. Document the name-lookup behavior in the README `## Column assumptions` section (replacing the current positional-caveat warning).

**Where `trailer_headers_decoded` comes from:** In `convert()` at L344, `classify_headers()` returns `_prefix_h, dynamic_h, _trailer_h`. Currently `_trailer_h` is discarded (note the leading underscore). Change the variable name to `trailer_h` and pass `[decode_cell(h) for h in trailer_h]` to `build_row()` alongside `dynamic_headers_decoded`. No new I/O; the data was already computed by `classify_headers()`.

---

### Pattern 3: Consumer Contract Checklist (CONTRACT-01 + MAKE-FIX-01 drift prevention)

**What:** A small `make-scripts/CONVENTIONS.md` (10-20 lines) that states the invariants shared across the Python→JS boundary. Combined with a comment block in each JS file pointing to the Python schema.

**CONVENTIONS.md content skeleton:**

```markdown
# Make.com JS Conventions

These files are co-owned consumers of the Python CLI contract defined in
`docs/webhook-schema.json`. Any change to Python output keys or tag strings
must be reflected here.

## Tag string format
All tags exchanged between `quizify-mapping.js` and `score-calculations.js`
use kebab-case: `peri-menu`, `postpartum`, `menstrual`, `consent_given`.
Exception: tags that are Python identifiers use snake_case (`consent_given`,
`goal_athlete`). When in doubt, match what `TAG_HEADER_MAP` emits in
`quizify_csv_ingest.py`.

## Key names from Python payload
Read using bracket notation matching D-05 locked keys exactly:
  record["product-recommendation"]   (not record.product_result)
  record["type-page-url"]
  record["result-logic"]
  record["score-category"]
  record["score-value"]
```

**Comment block to add at the top of each JS file:**

```javascript
// Contract: payload shape defined by quizify_csv_ingest.py
// Schema:   ../docs/webhook-schema.json
// Conventions: ./CONVENTIONS.md
// D-05: key order is locked — do not read keys by position, always by name.
```

This lightweight approach avoids introducing a JSON-based consumer-contract format (e.g., OpenAPI, AsyncAPI) that would require tooling and create more maintenance surface. The goal is making drift visible to a human reviewer, not automated enforcement (which is deferred to v1.2's potential JS test harness).

---

## Data Flow

### Normal (no --validate)

```
CSV file (utf-8-sig)
    ↓ open + csv.reader
classify_headers()
    → prefix_h, dynamic_h, trailer_h
        ↓
decode dynamic_h → dynamic_headers_decoded
decode trailer_h → trailer_headers_decoded   [NEW in TRAIL-01]
        ↓ per row
decode_cell() on all cells
build_row(prefix_d, dynamic_d, trailer_d, dynamic_headers_decoded,
          trailer_headers_decoded, quiz_title)
    → row_dict, warnings
        ↓
logging.warning() per warning (PII-safe)
results.append(row_dict)
        ↓
json.dump(results, stdout/file)
```

### With --validate (VALI-01)

```
[same as above through results.append]
        ↓
validate_payload(results, schema_path=SCHEMA_PATH)
    schema_dict = json.loads(schema_path.read_text())   # once
    for i, record in enumerate(results):
        errs = _validate_record(record, schema_dict)
        logging.error("row %d: %s", i+1, err)           # schema-path only
    if any errors → return 1
        ↓ (only if no errors, or --validate not passed)
json.dump(results, stdout/file)
```

**Exit code propagation:** `validate_payload()` returns `bool` (True = valid). `convert()` checks the return and ORs exit code with `1` on failure, same pattern as row-skip failures today (L362: `exit_code |= 1`).

---

## Integration Points

### Python CLI → Make.com JS boundary

| Boundary | Communication | Invariant | v1.1 Change |
|----------|--------------|-----------|-------------|
| `quizify_csv_ingest.py` → `quizify-mapping.js` | JSON payload passed via Make.com data store | D-05 key names; locked tail order | CONTRACT-01 fixes JS to read `record["product-recommendation"]` |
| `quizify-mapping.js` → `score-calculations.js` | `output.tags` array passed as `data.tags` | Tag strings must be consistent between emitter and checker | MAKE-FIX-01 aligns `peri-menu` string across both files |
| Python `--validate` → schema file | `json.loads` at runtime | Schema is the machine-readable contract; D-05 encoded in `required` array order | VALI-01 creates `docs/webhook-schema.json` |

### Internal Python boundaries

| Boundary | v1.0 | v1.1 Change |
|----------|------|-------------|
| `convert()` → `build_row()` | passes `trailer_cells_decoded` list | also passes `trailer_headers_decoded` list (TRAIL-01) |
| `convert()` → `validate_payload()` | does not exist | new call after accumulation, before json.dump (VALI-01) |
| `main()` → `convert()` | passes `trailer_override`, `output`, `quiz_title` | also passes `validate: bool` from `args.validate` (VALI-01) |

---

## D-05 / D-11 / D-12 / D-13 / D-15 Implications

| Decision | v1.1 Impact |
|----------|-------------|
| **D-05** (locked key order) | Schema must assert the exact key sequence for fixed keys (contact block + scoring tail). The hand-rolled validator checks `list(record.keys())` order for the fixed-key bookends. VALI-01 makes D-05 machine-checkable for the first time. |
| **D-11** (README 10-section lock + drift test) | Adding `--validate` to argparse causes `test_every_flag_named_in_readme` to fail immediately (the test scans `--help` output for long flags). This is the safety net working as designed. README update is mandatory before the test passes. Add `--validate` row to `## CLI reference` table and document dry-run interaction in `## Column assumptions`. |
| **D-12** (single-file) | Preserved. `validate_payload()` + `_validate_record()` + `_load_schema()` are module-level functions in `quizify_csv_ingest.py`. No sibling module. ~50 additional lines land at ~480 LOC — no split justified. |
| **D-13** (stdlib-only at runtime) | Preserved. Hand-rolled structural validator uses only `json`, `pathlib.Path`, `typing`. No `jsonschema` package. The schema file is loaded via `Path.read_text()` + `json.loads()`. |
| **D-15** (scoring by trailer index [0..2]) | Explicitly retired by TRAIL-01. Replace with `TRAILER_SCORE_MAP` + `_lookup_trailer_cell()`. The README `## Limitations` bullet about positional mis-binding risk is removed. The `## Column assumptions` caveat about `--trailer-columns` reordering is updated to describe name-based lookup. |

---

## Anti-Patterns

### Anti-Pattern 1: Validating inside build_row()

**What people do:** Call `validate_payload()` or a schema check inside `build_row()` for per-row immediacy.
**Why it's wrong:** `build_row()` is a pure function tested in isolation. Injecting schema I/O breaks the pure-function contract, couples the function to a file path, and makes unit tests order-dependent on filesystem state.
**Do this instead:** Validate after the accumulation loop in `convert()`. Schema is loaded once, not per row.

### Anti-Pattern 2: Adding `jsonschema` as a runtime dep for VALI-01

**What people do:** `pip install jsonschema` and use `jsonschema.validate()` for a "real" JSON Schema validator.
**Why it's wrong:** D-13 prohibits runtime deps. The envelope invariants are well-bounded (fixed keys, simple types, pattern-based dynamic keys). A full JSON Schema validator is ~10x the code surface needed.
**Do this instead:** Hand-roll a ~30-line structural checker that encodes only the D-05 invariants. Revisit if schema complexity grows beyond what hand-rolling can maintain (not anticipated in v1.x scope).

### Anti-Pattern 3: Exact-match trailer header lookup

**What people do:** Check `trailer_header == "Result logic"` (exact string equality) in `_lookup_trailer_cell()`.
**Why it's wrong:** Operator-supplied `--trailer-columns` values may differ in casing or whitespace. Exact match breaks the robustness goal that `--trailer-columns` is meant to provide.
**Do this instead:** NFC+casefold substring match on a known keyword (e.g., `"result logic"` as substring of `"Result logic"` or `"Result Logic"`), consistent with `TAG_HEADER_MAP` and `match_tags_to_questions()`.

### Anti-Pattern 4: Using `product_result` alias in Python to fix CONTRACT-01

**What people do:** Emit both `product-recommendation` and `product_result` from Python to avoid touching the JS.
**Why it's wrong:** D-05 key order is locked. Adding an alias key without an explicit ADR would silently mutate the contract and potentially break downstream consumers that rely on exact key ordering. The correct fix is one line in `quizify-mapping.js:102`.
**Do this instead:** Fix the JS consumer (CONTRACT-01). Do not change Python output.

---

## Suggested Build Order

Given the four features and their dependencies:

**1. CONTRACT-01 (quizify-mapping.js:102)** — First. One-line JS fix, no Python changes, no test infrastructure changes. Immediately eliminates the silent-null bug in production. Independent of all other features.

**2. MAKE-FIX-01 (tag mismatch + activity_profile inversion)** — Second, immediately after CONTRACT-01. Still pure JS edits. No Python changes. Groups both JS co-owned surface fixes together so the JS side is fully reconciled before touching Python.

**3. TRAIL-01 (TRAILER_HEADER_MAP)** — Third. Python-only change. Requires: (a) add `TRAILER_SCORE_MAP` constant, (b) add `_lookup_trailer_cell()`, (c) propagate `trailer_headers_decoded` from `convert()` to `build_row()` (signature change), (d) replace three positional reads in `build_row()` with lookup calls, (e) update `statusDate` lookup (currently `trailer_cells_decoded[5]` — also replace with `_lookup_trailer_cell("status-date", ...)`). Update README `## Column assumptions` and `## Limitations` to remove the positional-mis-binding caveat. Write / update tests in `test_row_builder.py` to cover name-based lookup including out-of-order trailer headers. TRAIL-01 does NOT need `--validate` — it is orthogonal.

**4. VALI-01 (--validate flag + validate_payload())** — Last. Depends on: (a) TRAIL-01 being done (so the validated payload already uses name-based lookup), (b) schema design being finalized. Steps: write `docs/webhook-schema.json`, add `_load_schema()` + `_validate_record()` + `validate_payload()` to `quizify_csv_ingest.py`, add `--validate` to argparse in `main()`, wire into `convert()`, write `tests/test_validation.py`. The drift test (`test_every_flag_named_in_readme`) will fail after `--validate` is added to argparse — update README as part of this step. Exit-code table gets a new row for validation failure (reuse code 1).

**Rationale for this order:**
- JS fixes ship first because they are production bugs with zero Python risk surface.
- TRAIL-01 before VALI-01: the schema validates what the final payload emits; validating a payload that still uses positional trailer reads would validate D-15 behavior rather than the hardened TRAIL-01 behavior.
- VALI-01 last because it touches the most new test infrastructure and depends on a stable schema definition, which is only meaningful after the payload contract is finalized.

---

## Sources

- Source read: `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (complete, 427 LOC)
- Source read: `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` (complete, 188 LOC)
- Source read: `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` (complete, 296 LOC)
- Source read: `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`
- Source read: `quizify-csv-to-json-webhook/README.md`
- Source read: `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py`
- Source read: `.planning/PROJECT.md` (decisions D-05, D-11, D-12, D-13, D-15; v1.1 feature specs)
- Source read: `.planning/MILESTONES.md` (v1.0 delivery record)

---
*Architecture research for: Quizify CSV-to-webhook CLI v1.1 Contract Hardening*
*Researched: 2026-05-03*
