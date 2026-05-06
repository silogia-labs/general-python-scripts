# Phase 7: Refactor Scaffolding (no-op) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 07-refactor-scaffolding-no-op
**Areas discussed:** Sink interface shape, iter_rows() boundary, Validation placement, _HttpPostSink stub depth

---

## Sink interface shape

| Option | Description | Selected |
|--------|-------------|----------|
| write_one + close (Recommended) | `write(row)` per-row + `close()` finalizes; StdoutSink/FileSink buffer-then-dump on close to keep byte-identical default; Phase 8 NDJSON overrides write() to flush per row. Streaming-native. | ✓ |
| write_all (single call) | `sink.write_all(rows)` once after iter_rows() exhausts. Minimal diff but Phase 8 NDJSON needs interface change — rework debt. | |
| Context manager (`__enter__`/`__exit__` + write) | Same streaming shape as option 1 with Python context-manager idiom. Atomic writes drop in naturally for Phase 8. | |
| You decide | Defer to planner. | |

**User's choice:** write_one + close
**Notes:** Locked as `_Sink` Protocol with `write(row: dict) -> None` and `close() -> None`. `_StdoutSink`/`_FileSink` accumulate internally and `json.dump` once on `close()` to preserve byte-identical default.

---

## iter_rows() boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Owns everything; returns `(gen, exit_state)` (Recommended) | `_RowStream` wrapper class owns file open + classify_headers + missing-trio warnings + per-row build + mutable `exit_code`. `__iter__` yields one dict per row. | ✓ |
| Pure generator; convert() owns header phase | convert() handles file open + classify_headers + LayoutError; iter_rows() is a thin generator with shared mutable for row-mismatch tracking. | |
| Generator yields tagged items (data \| warning) | iter_rows() yields tagged 2-tuples; caller dispatches. Pure functional but adds ceremony at every call site. | |
| You decide | Defer to planner. | |

**User's choice:** _RowStream wrapper class
**Notes:** Caller in `convert()` materializes via `list(stream)` (validation requires the full list); SC#2 still satisfied because the generator itself doesn't accumulate. LayoutError + empty-CSV exception handling moves to caller (`convert()` wraps `list(stream)` in try/except).

---

## Validation placement

| Option | Description | Selected |
|--------|-------------|----------|
| Stay batch in convert(), pre-sink-open (Recommended) | Build all rows, validate full list, then on success open sink and stream rows in. Byte-identical preserved exactly; Phase 9 pre-egress gate works. | ✓ |
| Move per-row into the pipeline now | Compile schema['items'] once, validate(row) inline. Pays forward to Phase 8 streaming but changes failure timing — for Phase 7 default array mode would still need to buffer to stay byte-identical. | |
| Wrap validation in a sink decorator | `_ValidatingSink` wraps any underlying sink. Composable but same timing-change risk; adds a decorator class Phase 8/9 may not need. | |
| You decide | Defer to planner. | |

**User's choice:** Stay batch in convert()
**Notes:** `_run_schema_validation` body is NOT modified. Phase 8 will introduce per-row validation as part of NDJSON's behavior change, not snuck into Phase 7.

---

## _HttpPostSink stub depth

| Option | Description | Selected |
|--------|-------------|----------|
| Accepts url; raises on write() (Recommended) | `__init__(url)` stores URL silently (no validation — Phase 9). `write(row)` raises NotImplementedError. `close()` no-op. Argparse `--post-url` lands as plain string. | ✓ |
| Bare stub; raises on `__init__` | Class exists but raises NotImplementedError immediately. SC#3 test only verifies argparse parses the flag; sink instantiation untested until Phase 9. | |
| Full Phase-9 argparse + URL validation now | Land `--post-url` with HTTPS-only check, `--header` CRLF rejection, `--timeout`, `--validate` gate. Front-loads Phase 9 wiring. Scope creep risk. | |
| You decide | Defer to planner. | |

**User's choice:** Accepts url; raises on write()
**Notes:** Lets Phase 7 ship the SC#3 test end-to-end (argparse parses → sink instantiates → first write raises) without leaking any Phase 9 behavior. The `--post-url` requires `--validate` gate is explicitly NOT landed in Phase 7.

---

## Claude's Discretion

- Whether `iter_rows()` is exposed as a top-level function returning `_RowStream`, or as a class method, or as `_RowStream.__iter__` accessed via `iter(stream)` — planner's call.
- The `_select_sink(args) -> _Sink` factory's exact signature and location.
- Whether sinks live in the same module or move to a new submodule (preference: single-file per D-06-04 carry-forward).
- Empty-CSV detection mechanism inside `_RowStream` (sentinel exception vs early-set exit_code).
- Test file naming and placement.
- Underscore-prefix vs public for `_RowStream`, `_Sink` (preference: keep underscored except `iter_rows`).
- Exact `NotImplementedError` message text in `_HttpPostSink.write()` (must reference Phase 9, no PII).

## Deferred Ideas

- NDJSON output, atomic file replace, per-row validation in the streaming pipeline → Phase 8.
- HTTP POST behavior (HTTPS check, headers, timeout, retry, redirect, env-var URL, idempotency key) → Phase 9 / v1.3+.
- `_ValidatingSink` decorator → Phase 8 may revive.
- `_HttpPostSink.__init__` URL validation in Phase 7 → rejected.
- `--post-url` requires `--validate` argparse gate in Phase 7 → rejected.
- Make.com hygiene + node:test harness → Phase 10 (parallel-safe).
- Restructuring into a package directory → D-06-04 carry-forward.
