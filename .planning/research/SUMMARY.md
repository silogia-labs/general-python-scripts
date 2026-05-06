# Project Research Summary — v1.2 Delivery & Make.com Hygiene

**Project:** Quizify CSV → Webhook JSON
**Domain:** stdlib-Python CLI utility + co-owned Make.com IIFE JS modules
**Researched:** 2026-05-05
**Confidence:** HIGH

## Executive Summary

v1.2 closes the v1.1 deferred bucket: HTTP POST delivery (AUTO-01), NDJSON streaming (STREAM-01), Node test harness for Make.com modules (MAKE-TEST-01) + two trivial JS fixes (MAKE-COSMETIC-01/02). All implementable using stdlib (`urllib.request`, `json`, `ssl`) on Python and built-in `node:test` + `node:assert/strict` on JS. **Zero new runtime dependencies.** D-13 stdlib-only-at-runtime preserved end-to-end.

Approach: minimal targeted refactor of `convert()` — extract `iter_rows` generator + factor output into sink abstraction (`_StdoutSink` / `_FileSink` / `_HttpPostSink`). NDJSON becomes a sink/serializer concern; POST is a third sink. Default path stays byte-identical to v1.1 (TRAIL-03 golden fixture remains green). On JS side: IIFEs gain pure `mapRecord(record)` extraction with conditional `module.exports` guarded by `typeof module !== "undefined"` so deployed Make.com files paste in unchanged.

Dominant risks (all addressable): AUTO-01 — `urlopen` no-timeout default, T-PII-01 leaks via `HTTPError` body echoes, AUTO-01↔VALI-01 race, accidental TLS disablement, silent redirects. STREAM-01 — NDJSON newline correctness, atomic-write on mid-stream abort, per-row vs whole-array validation drift. MAKE-TEST-01 — IIFE-import shape, accidental globals, `package.json` dep creep.

## Key Findings

### Recommended Stack
**Python (runtime):** `urllib.request`/`urllib.error` (explicit `timeout=`, `ssl.create_default_context()`, custom no-redirect opener); `json` for hand-rolled NDJSON line encoding; existing `fastjsonschema>=2.21.2` `[validate]` extra reused for AUTO-01 gating + per-row STREAM-01 validation against `schema["items"]`.
**JS (test-side):** Node 20 LTS minimum (22 LTS preferred); `node:test` + `node:assert/strict`. Vitest/Jest/Mocha rejected as overkill. `make-scripts/package.json` locked to empty deps (CI-gated).
**Test fixtures:** stdlib `http.server.BaseHTTPRequestHandler` in daemon thread for fake-webhook.

### Expected Features (v1.2 must-have)
- **AUTO-01:** `--post-url URL`, `--header "K: V"` (repeatable, CRLF-rejecting), `--timeout SECONDS` (30s default), `Content-Type: application/json`, non-2xx → exit 3, PII-safe stderr (status + categorical reason only), HTTPS-only.
- **AUTO-01 gating:** hard-fail when `--post-url` set without `--validate`.
- **STREAM-01:** `--ndjson` boolean (NOT `--emit-format` enum); generator-backed emission; file-mode target only; per-row validation against `schema["items"]`; atomic write via `.tmp` + `os.replace()`; `newline="\n"`.
- **MAKE-COSMETIC-01:** `Reomoto` → `Remoto` at `score-calculations.js:157`.
- **MAKE-COSMETIC-02:** Remove dead `profile = "profile_base"` at `score-calculations.js:217`.
- **MAKE-TEST-01:** `node --test` harness; regression coverage for CONTRACT-01 + MAKE-FIX-01/02 + MAKE-COSMETIC-01/02; synthetic T-PII-01-safe fixtures; `globalThis` snapshot test; pure `mapRecord(record)` + conditional `module.exports`.

**Locked deferrals (v1.3+):**
- **NDJSON+POST cross-product** — out of scope. v1.2 supports `{array+POST, array+file, NDJSON+file}`. Argparse rejects `--ndjson` + `--post-url`.
- `--retry N` (Make.com idempotency unverified).
- `--idempotency-key`.
- `$QUIZIFY_WEBHOOK_URL` env-var form.

**Anti-features (rejected):** OAuth, persistent retry queue, multi-URL fan-out, RFC 7464, Vitest/Jest/Mocha, `--post-body-from-file`.

### Architecture
1. `main()` — argparse, target resolution, sink construction, validation-gating-of-POST.
2. `convert()` — orchestrates pipeline; chooses buffered vs streaming.
3. `iter_rows()` (new) — pure generator over CSV reader.
4. Sink abstraction (new) — three sinks (~15 LOC each); mutually-exclusive `-o`/`--post-url` argparse group.
5. `_run_schema_validation` — unchanged for buffered; adds `_validate_one(row)` for streaming.
6. `make-scripts/` — isolated sibling tree, own `package.json`, `tests/`, `tests/fixtures/`. `pytest norecursedirs = ["make-scripts", "node_modules"]`.

**Build order (de-risked):** (1) refactor scaffolding (no-op) → (2) STREAM-01 → (3) AUTO-01 → (4) MAKE-COSMETIC + MAKE-TEST (parallel from day 1).

**Flag-shape decision:** `--ndjson` boolean wins over `--emit-format` enum for v1.2 (ecosystem standard via jq/JSONL/Wikipedia; only one alternate format in scope; D-11 README pressure).

### Critical Pitfalls
1. `urlopen` no-timeout default — explicit `timeout=` everywhere; CI grep gate.
2. HTTP error body PII leakage — categorical-only logging; lock new D-06-2x; `TestHTTPErrorPIIsafe` negative-substring class.
3. VALI-01 ↔ AUTO-01 race — argparse mutual-requirement; integration test asserts 0 server requests on schema failure.
4. Silent TLS disable / redirects — `ssl.create_default_context()`; CI grep gate; HTTPS-only argparse; custom opener refusing redirects.
5. NDJSON newline + atomic-write — `newline="\n"`; `.tmp` + `os.replace()`; SIGINT mid-stream test.
6. Per-row vs whole-array validation drift — extract `schema["items"]` once; 6-cell cross-mode matrix in INTEGRATION-CHECK.md.
7. MAKE-TEST-01: IIFE-import + globals + dep creep — pure `mapRecord`; conditional `module.exports`; `"use strict";`; `globalThis` snapshot; CI gate on empty deps.

**Cosmetic-fix verification (Phase 4 entry gates):** verify `Reomoto` not load-bearing; verify `profile = "profile_base"` genuinely dead.

## Implications for Roadmap

**Suggested phases: 4.** Phase 4 parallelizable from day 1.

### Phase 1 — Refactor Scaffolding (no-op)
Extract `iter_rows()` + sink abstraction. Output byte-identical. POST sink stub raises `NotImplementedError`. Argparse mutually-exclusive `-o`/`--post-url` group.

### Phase 2 — STREAM-01 NDJSON
`--ndjson` boolean; NDJSON serializer; per-row validation against `schema["items"]`; atomic-write; SIGINT test. Argparse rejects `--ndjson` + `--post-url`.

### Phase 3 — AUTO-01 HTTP POST
`--post-url`/`--header`/`--timeout`; `_HttpPostSink`; HTTPS-only; mutual-requirement with `--validate`; exit code 3; D-06-2x PII templates; mock-server integration tests including "0 requests on schema failure" and "503 → 1 request (no retry)". **Needs research-phase** for empirical Make.com 4xx body shape.

### Phase 4 — MAKE-COSMETIC + MAKE-TEST (parallel)
IIFE → `mapRecord(record)` extraction; conditional `module.exports`; `"use strict";`; zero-deps `package.json`; regression tests for v1.1 fixes + cosmetics; `globalThis` snapshot; pytest `norecursedirs` updated. **Needs research-phase** for empirical Make.com IIFE sandbox semantics. **Entry gates:** cosmetic typo not load-bearing; dead initializer dead.

### Research-Phase Flags
- **Phase 3:** Make.com 4xx response body shape; webhook redirect behavior; receipt-200 vs scenario-completion semantics.
- **Phase 4:** IIFE sandbox semantics for `module`, `"use strict"`, `console`.
- **Phases 1, 2:** Skip research-phase (pure refactor / textbook stdlib patterns).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Stdlib-only both runtimes; zero new deps. |
| Features | HIGH (overall); MEDIUM (cosmetic load-bearing) | Flag conventions track curl/HTTPie/jq; `node:test` unambiguous. Phase 4 entry-gate verification on cosmetics. |
| Architecture | HIGH | Sink abstraction small, low-risk; `make-scripts/` isolation mechanical. |
| Pitfalls | HIGH (Python + NDJSON); MEDIUM (Make.com IIFE sandbox) | Sandbox specifics inferred — empirical validation in Phase 4. |

**Overall:** HIGH.

### Gaps to Resolve in Phase Research
- Make.com webhook 4xx response body shape (Phase 3).
- Make.com IIFE sandbox semantics for `module` / `"use strict"` / `console` (Phase 4).
- NDJSON+POST design (defer to v1.3 plan).
- v1.3 candidate triggers: retry policy, idempotency-key, env-var URL form.

## Sources

**Primary (HIGH):** Python stdlib docs (`urllib.request`, `urllib.error`, `http.client`, `ssl`, `csv`, `json`, `os.replace`); Node.js v22 Test runner docs; HTTPie 3.2.4 docs; jq 1.8 Manual; ndjson.com / jsonlines.org; in-repo `PROJECT.md`, `MILESTONES.md`, `quizify_csv_ingest.py`.

**Secondary (MEDIUM):** Vitest comparisons; vitest-dev/vitest Discussion #4631; PkgPulse 2026 node:test vs Vitest vs Jest; Better Stack / AppSignal Node test runner guides.

**Tertiary (LOW — needs Phase research validation):** Make.com IIFE sandbox semantics; Make.com webhook 4xx response-body shape.
