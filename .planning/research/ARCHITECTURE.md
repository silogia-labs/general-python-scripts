# Architecture Research — v1.2 Integration

**Project:** Quizify CSV → Webhook JSON (v1.2)
**Mode:** Project / subsequent-milestone integration
**Confidence:** HIGH

## Executive Summary

v1.2 adds three orthogonal capabilities to a deliberately small single-file CLI: HTTP POST delivery (AUTO-01), streaming/NDJSON output (STREAM-01), and a Node test harness for the co-owned Make.com modules (MAKE-TEST-01). The dominant architectural risk is **scope creep on `convert()`**, which already carries CSV reading, header classification, decoding, row building, missing-trio warnings, validation, and dual-target emission.

**Recommendation:** minimal targeted refactor — factor the *output side* of `convert()` into a tiny sink abstraction (3 sinks: stdout, file, POST), and factor the *emission shape* into a writer that emits either "buffered JSON array" or "NDJSON line-per-row." Row building, classification, decoding, and validation stay where they are. The `make-scripts/` Node toolchain lives as a fully isolated subtree with its own `package.json`.

**Build order:** refactor scaffolding → STREAM-01 NDJSON → AUTO-01 POST → MAKE-COSMETIC + MAKE-TEST (parallelizable from day 1).

## Current shape (v1.1, locked)

```
main(argv)
  └── convert(path, trailer, output, quiz_title, validate)
        ├── open CSV (utf-8-sig)
        ├── classify_headers → (prefix, dynamic, trailer_raw, scoring_index_map, missing)
        ├── per-row: decode_cell → build_row → results.append(...)
        ├── if validate: _run_schema_validation(results, SCHEMA_PATH)
        └── emit:
              ├── output is None → json.dump(results, sys.stdout, indent=2)
              └── output is Path → json.dump(results, fh, indent=2)
```

## Proposed shape (v1.2)

```
main(argv)
  ├── parse args → resolve target (stdout | file | POST URL)
  ├── resolve emission mode (array | ndjson)
  └── convert(path, trailer, sink, quiz_title, validate, ndjson)
        ├── classify_headers (unchanged)
        ├── row generator: for each CSV row → decode → build_row → yield row_dict
        ├── if validate AND not ndjson → buffer rows, validate once, then write
        │   if validate AND ndjson     → validate-per-row against schema["items"]
        └── sink.write(rows, ndjson=ndjson)

Sinks (each implements .write(iterable_of_dicts, ndjson: bool) → int):
  ├── _StdoutSink
  ├── _FileSink
  └── _HttpPostSink (urllib.request, D-13 preserved)
```

## Component Boundaries

| Component | Responsibility |
|-----------|----------------|
| `main()` | argparse, target resolution, sink construction, validation-gating-of-POST |
| `convert()` | Orchestrates CSV→rows pipeline; chooses buffered vs streaming |
| `iter_rows()` (new) | Pure generator: `(reader, classification, quiz_title) → Iterator[dict]` |
| Sink (new) | Encapsulates *where* output goes and *how* (array vs NDJSON) |
| `_run_schema_validation` | Unchanged for buffered; gains `_validate_one(row)` for streaming |
| `make-scripts/` (sibling tree) | JS modules + Node tests, fully isolated |

## Integration Decisions

### Q1 — Sink abstraction, not inline branching

Three sinks (~15 LOC each). Mutually-exclusive argparse group for `-o/--output` vs `--post-url`. AUTO-01 + `--validate` gate enforced in `main()`: if `args.post_url and not args.validate`, exit 2 with categorical error.

### Q2 — Generator-based streaming, NDJSON via flag

`iter_rows` extracted from current for-loop. NDJSON is a sink/serializer concern. **`--ndjson` is a new flag** — do NOT overload `--emit-json`. Streaming validation compiles `schema["items"]` once and validates each row dict.

**Default (no `--ndjson`) is byte-identical to v1.1** — protected by golden-fixture regression test analogous to `test_default_order_regression.py`.

### Q3 — MAKE-TEST-01 layout

```
make-scripts/
├── CONVENTIONS.md / quizify-mapping.js / score-calculations.js   (existing)
├── package.json          (NEW — declares "test": "node --test tests/")
├── package-lock.json     (NEW — committed)
├── .gitignore            (NEW — node_modules/, coverage/)
└── tests/
    ├── quizify-mapping.test.js
    ├── score-calculations.test.js
    └── fixtures/synthetic-rows.json   (T-PII-01-safe)
```

**Runner: `node:test` + `node:assert/strict`** (Node 18+, zero deps). Mirrors D-13 spirit on the JS side.

**Isolation:**
- flit_core's `[tool.flit.module]` already includes only the single Python module — `make-scripts/` is not packaged.
- pytest: add `[tool.pytest.ini_options] testpaths = ["tests"]; norecursedirs = ["make-scripts", "node_modules"]`.
- No top-level `package.json` — keep scoped to `make-scripts/`.

**IIFE → testable refactor:** Conditional `module.exports` guarded by `typeof module !== "undefined"` so deployed Make.com files paste in unchanged.

## Build Order

| # | Item | Rationale |
|---|------|-----------|
| 1 | Refactor scaffolding: extract `iter_rows` generator + sink abstraction (no new features) | De-risks 2/3. Output byte-identical; lands as no-op refactor commit. |
| 2 | STREAM-01 (`--ndjson`, NDJSON serializer, per-row validation) | Must precede AUTO-01 so `_HttpPostSink` shape is known. |
| 3 | AUTO-01 (`--post-url`, `_HttpPostSink`, validation gating, T-PII-01 HTTP carry-forward) | Builds on (1)+(2). |
| 4 | MAKE-COSMETIC-01/02 + MAKE-TEST-01 (Node harness; cosmetics land as first regression tests) | Independent of Python; parallelizable. |

## Anti-Patterns

1. **Inline sink branching inside `convert()`** — 6+ branches; HTTP error handling repeats.
2. **Overloading `--emit-json` for NDJSON** — breaks D-11 README drift test.
3. **Streaming `--validate` that revalidates the full array schema per row** — instead extract `schema["items"]` once.
4. **Top-level `package.json`** — mis-signals ownership in a multi-tool Python repo.
5. **POST without `--validate`** — violates v1.1 contract.

## Files Affected

**Modified:** `quizify_csv_ingest.py`, `pyproject.toml`, `README.md`, `make-scripts/score-calculations.js`.
**New:** `make-scripts/package.json`, `package-lock.json`, `.gitignore`, `tests/*.test.js`, `tests/fixtures/synthetic-rows.json`; new Python tests for sinks, NDJSON path, POST mock, validation-gating.
**Unchanged (load-bearing):** `docs/webhook-schema.json`, `docs/webhook-quizify-format-example.json`, `tests/test_default_order_regression.py` + golden fixture (v1.1→v1.2 byte-identity gate).

## Open Questions

1. **POST body shape:** Pitfalls research recommends POST sends a JSON-array body (not NDJSON); reconcile with STREAM-01 which is `-o file.ndjson` only. Likely defer NDJSON+POST cross-product to v1.3.
2. **Retry policy** for `_HttpPostSink`: none (recommended — Make.com idempotency unverified).
3. **`--post-url-env`:** first-class env-var flag to keep webhook URL out of `ps aux`/shell history.
4. **`--ndjson` + `-o`:** no magic file-extension switching; explicit flag only.
