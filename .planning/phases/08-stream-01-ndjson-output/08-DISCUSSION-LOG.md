# Phase 8: STREAM-01 NDJSON Output - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 08-stream-01-ndjson-output
**Areas discussed:** Sink shape, Per-row validation injection, Atomic write & SIGINT, Argparse rejections

---

## Sink shape

| Option | Description | Selected |
|--------|-------------|----------|
| New `_NdjsonFileSink` class | Standalone class implementing `_Sink` Protocol; `_FileSink` untouched (TRAIL-03 risk-free). Slight duplication of output handling. | ✓ |
| Flag-toggled `_FileSink(ndjson=True)` | Single class, two internal modes via `if self._ndjson`. Less code, but any future edit risks regressing one mode while fixing the other. | |
| Subclass `_NdjsonFileSink(_FileSink)` | OO-cleanest but adds a class hierarchy this codebase has avoided. | |

**User's choice:** New `_NdjsonFileSink` class
**Notes:** Keeps Phase 7's `_FileSink` byte-identical-by-construction. Three sink classes become four; `_select_sink` gains a third branch.

---

## Per-row validation injection

| Option | Description | Selected |
|--------|-------------|----------|
| `_ValidatingSink` decorator | Wraps any inner sink. Compiles `schema['items']` once. Raises sentinel on failure; inner sink closes without `os.replace`. Reusable by Phase 9 for pre-egress validation. | ✓ |
| Validate-and-yield wrapper around `iter_rows()` | Generator wraps `iter_rows()` output; sink stays validation-agnostic. Cleaner separation but couples validation to iteration; less reusable for Phase 9's POST gate. | |
| Inline check in `convert()` | Compile + per-row validate directly in `convert()`. Most direct; costs duplication of validation logic across array and NDJSON modes. | |

**User's choice:** `_ValidatingSink` decorator
**Notes:** Decorator + sentinel exception (`_RowValidationError`) lets `convert()` exit 1 cleanly while letting `_NdjsonFileSink.__exit__` see `exc_type is not None` and unlink `.tmp`. Wrapper must delegate `__enter__/__exit__` to inner sink.

---

## Atomic write & SIGINT

| Option | Description | Selected |
|--------|-------------|----------|
| Context manager + `__exit__` decides | `__enter__` opens .tmp; `__exit__(exc_type, ...)` either `os.replace` on success or `os.unlink` .tmp on exception. SIGINT propagates as `KeyboardInterrupt` through `__exit__`. No explicit signal handler. | ✓ |
| Explicit `commit()` / `abort()` methods | Two-phase API; `convert()` wraps loop in try/except. Breaks uniform `_Sink` Protocol. | |
| try/finally + `_committed` flag in `close()` | Implicit, easy to misuse on exception paths. | |
| Explicit SIGINT handler | Adds global state; CPython default + try/finally already covers it. | |

**User's choice:** Context manager + `__exit__` decides
**Notes:** All sinks gain trivial `__enter__/__exit__` shims so `convert()` uses a uniform `with sink:` loop across modes. STREAM-04 invariant ("no target file on SIGINT") is satisfied structurally.

---

## Argparse rejections

| Option | Description | Selected |
|--------|-------------|----------|
| `--ndjson` outside mutex + post-parse `parser.error()` checks | Phase 7 mutex group preserved. Two clear post-parse checks for `--ndjson + --post-url` and `--ndjson + no -o`. Categorical messages, exit 2. | ✓ |
| Restructure into nested groups | Pure-argparse rejection; argparse can't cleanly express "A requires B and forbids C" without subparsers. | |
| Custom `argparse.Action` on `--ndjson` | Order-dependent on CLI argument order; surprising and harder to test. | |

**User's choice:** Outside mutex + post-parse `parser.error()` checks
**Notes:** Help text on `--ndjson` documents both constraints inline.

---

## Claude's Discretion

- Exact name of the sentinel exception class (proposed `_RowValidationError`).
- JSON Pointer + row-index format on stderr (must be PII-safe, consistent with D-06-2x templates).
- Whether `_select_sink` becomes `_select_sink(args)` or keeps positional parameters.
- Test file naming and placement; whether SIGINT test is subprocess-driven or simulates `KeyboardInterrupt` via fake sink.
- Whether `_StdoutSink`/`_FileSink` `__exit__` calls `close()` always (today's behavior) or only on success (NDJSON semantics) — array-mode sinks should preserve today's "always emit on close".

## Deferred Ideas

- NDJSON × `--post-url` cross-product (v1.3+).
- Per-row validation in array mode (out of scope for v1.2).
- Atomic write retrofit to non-NDJSON `_FileSink` (preserves TRAIL-03 byte-identity).
- `--retry`, `--idempotency-key`, `$QUIZIFY_WEBHOOK_URL`, RFC 7464 JSON Text Sequences — all v1.3+ or out of scope.
- HTTP POST delivery body — Phase 9.
- Make.com hygiene + node:test — Phase 10.
