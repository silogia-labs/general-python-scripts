# Stack Research — v1.2 Delivery & Make.com Hygiene

**Domain:** CLI utility (Python stdlib-only) + co-owned Make.com IIFE JS modules
**Researched:** 2026-05-05
**Confidence:** HIGH (Python additions); HIGH (Node test runner choice)

## TL;DR — Net Stack Delta for v1.2

| Concern | Decision | Net change |
|---------|----------|------------|
| AUTO-01 — HTTP POST delivery | Use `urllib.request` + `urllib.error` from stdlib; hand-rolled retry/backoff in ~30-50 LOC inside `quizify_csv_ingest.py` | **Zero new runtime deps** (D-13 preserved) |
| STREAM-01 — NDJSON streaming | Hand-rolled NDJSON writer using `json.dumps(row, ensure_ascii=False)` per line; gated behind a new `--emit-format ndjson` flag | **Zero new runtime deps** |
| MAKE-TEST-01 — JS test harness | `node:test` built-in (Node 20+; Node 22 LTS preferred) + `node:assert/strict` | **Zero new npm runtime deps**; `package.json` optional and devDeps-free |

This is the right answer because the existing v1.0/v1.1 ethos — stdlib-only at runtime, additions only when justified — applies cleanly here. None of the three v1.2 features cross the threshold that would justify importing `requests`, `httpx`, an NDJSON package, Vitest, or Jest.

## Recommended Stack

### Core Technologies (Python — runtime)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.7+ (existing floor) | Runtime | Already locked by v1.0; v1.2 adds nothing that needs newer syntax |
| `urllib.request` (stdlib) | n/a | HTTP POST delivery (AUTO-01) | Stdlib-only at runtime is D-13. `urllib.request.Request(url, data=..., headers={"Content-Type":"application/json"}, method="POST")` + `urlopen(req, timeout=...)` covers the full POST contract. `requests`/`httpx` would buy retry/connection-pooling sugar we don't need for one-shot egress |
| `urllib.error` (stdlib) | n/a | Error categorization for AUTO-01 | `HTTPError` (status + reason — no body needed for PII-safe logs) and `URLError` (transport — `reason` is categorical: timeout, DNS, refused) cover the entire failure surface for T-PII-01-safe logging |
| `ssl` (stdlib) | n/a | TLS context for HTTPS POST | Default `ssl.create_default_context()` — verifies certs from system CA bundle. No flags to disable verification |
| `json` (stdlib) | n/a | NDJSON line encoding (STREAM-01) | `json.dumps(row, ensure_ascii=False, separators=(",", ":"))` per row + `\n`. D-17 indent=2 only applies to the array-mode emit; NDJSON lines are intentionally compact. Newline is `\n` (LF), never `\r\n` |
| `fastjsonschema` | `>=2.21.2` (already pinned) | Schema validation gate for AUTO-01 | Already shipped as the `[validate]` extra in v1.1. AUTO-01 reuses the same lazy-import path — no changes to `pyproject.toml` runtime |

### Core Technologies (JS — test-side, MAKE-TEST-01)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Node.js | 20.x LTS minimum; 22.x LTS preferred | Test harness runtime | `node:test` is stable since Node 20. Node 22 LTS (Oct 2024) is the long-term floor for new tooling in 2026 |
| `node:test` (built-in) | n/a | Test runner | Zero deps, ships with Node, watch mode + coverage + mocks built in. For two ~200 LOC IIFE modules with no framework integration, anything else is overkill (see Alternatives) |
| `node:assert/strict` (built-in) | n/a | Assertions | Pairs with `node:test`; strict-equality semantics by default |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | — | — | v1.2 introduces no new runtime libraries. Existing `fastjsonschema>=2.21.2` extra remains the only optional dep |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` (existing) | Python tests | AUTO-01 + STREAM-01 tests live alongside existing 94 tests; use stdlib `http.server.BaseHTTPRequestHandler` in a thread for fake-webhook fixtures (no `responses`/`pytest-httpserver` needed) |
| `node --test` | Run JS suite | `node --test quizify-csv-to-json-webhook/make-scripts/*.test.js`. Add `npm test` script if a minimal `package.json` is introduced; otherwise document the raw command in `make-scripts/CONVENTIONS.md` |
| `node --test --watch` | Local TDD loop | Built-in watch mode; no nodemon needed |
| `node --experimental-test-coverage` | Optional coverage | Stable in Node 22; only enable if tests grow beyond smoke level |

## Integration Points with Existing CLI

### AUTO-01 — argparse additions

```text
--post-url URL        Webhook URL to POST the JSON payload to (HTTPS recommended)
--post-timeout SEC    Per-attempt timeout in seconds (default: 30)
--post-retries N      Retry count on transient errors (default: 2; total attempts = N+1)
```

Wiring in `main()`:
1. After `convert()` builds `results` and `--validate` returns 0, dispatch to a new `_post_payload(results, args)`.
2. `_post_payload` does: `body = json.dumps(results, ensure_ascii=False).encode("utf-8")` → `urllib.request.Request(...)` → exponential backoff loop (`time.sleep(2**attempt)`) only on `URLError` / 5xx / 429 / 408. Other 4xx is non-retryable.
3. Logging: `logging.info("POST %s -> %d", url, status)` on success; `logging.error("POST failed: %s after %d attempts", categorical_reason, attempts)` on terminal failure. **Never** log request body, response body, or `err.read()` content (T-PII-01).
4. Exit code: 0 on 2xx, 1 on terminal failure.

### STREAM-01 — argparse additions

```text
--emit-format {array,ndjson}    Default: array (D-17, byte-identical to v1.1)
```

Behavior:
- Default path stays `json.dump(results, ..., indent=2, ensure_ascii=False)` — D-17 byte-identical (TRAIL-03 golden fixture must remain green).
- `ndjson` path streams: builds `row_dict`, validates if `--validate`, writes `json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"` to stdout/`-o` per row, **without** accumulating `results` in memory. This is the T-RESOURCE-01 follow-through: removes the >50k-row / >250MB RAM ceiling.
- AUTO-01 + STREAM-01 interaction: NDJSON + POST is out of scope unless target webhook accepts NDJSON; document in REQUIREMENTS.

### MAKE-TEST-01 — file layout

```
quizify-csv-to-json-webhook/make-scripts/
  quizify-mapping.js                  (existing IIFE; minimal change — extract pure transform if needed)
  score-calculations.js               (existing IIFE; ditto)
  quizify-mapping.test.js             (NEW — node:test suite)
  score-calculations.test.js          (NEW — node:test suite)
  test-harness/
    load.js                           (NEW — small ~30 LOC shim that exposes a pure transform(input) for each module)
    fixtures/
      input-row.example.json          (synthetic, T-PII-01-safe; mirrors a single Python emit row)
  CONVENTIONS.md                      (existing; extend with "Running tests: `node --test`")
  package.json                        (NEW, optional — see below)
```

The harness shim is needed because `quizify-mapping.js` is a Make.com IIFE: it reads `input.quiz_response` at module top-level and ends with `return output`. Two viable approaches:
1. **Refactor (recommended):** extract a pure `transform(input)` function in each module; production wrapper at the end (`return transform({ quiz_response: input.quiz_response })`) keeps Make.com behavior identical. Tests target the pure function. Adds <10 LOC per module.
2. **Wrap-and-eval:** read source as text, wrap as `new Function("input", source.replace(/return /, "return "))`. Brittle and harder to debug — only use if MAKE-COSMETIC-01/02 must land without touching surrounding code.

Recommend approach 1; ships alongside MAKE-COSMETIC-01/02 in the same diff.

Optional minimal `package.json`:
```json
{ "name": "quizify-make-scripts-tests", "private": true, "type": "module", "scripts": { "test": "node --test" }, "engines": { "node": ">=20" } }
```
No `dependencies`, no `devDependencies`. Place inside `make-scripts/` to scope the JS toolchain to that surface and keep the Python project root clean. The repo introduces JavaScript tooling for the first time — keeping it siloed prevents creep.

## Installation

```bash
# Python — no change from v1.1
pip install '.[validate]'   # only if --validate / --post-url used

# Node — no install step required; just need Node 20+ on PATH
node --version              # confirm >= v20
node --test quizify-csv-to-json-webhook/make-scripts
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `urllib.request` | `requests` 2.x | If we ever need: connection pooling across many POSTs in one invocation, multipart uploads, or sophisticated auth (OAuth2, AWS SigV4). None apply to AUTO-01 (single one-shot POST) — and adding `requests` would break D-13 |
| `urllib.request` | `httpx` 0.27+ | If we needed async or HTTP/2. Neither applies; AUTO-01 is sync, single-request |
| Hand-rolled retry loop | `tenacity` | If retry policy grew to >5 distinct conditions or needed jitter/circuit-breaker. Two-condition (transient vs permanent) is trivially expressible inline |
| Hand-rolled NDJSON | `ndjson` / `jsonlines` (PyPI) | These libraries are ~50 LOC each and trade nothing for a dependency. `for row in rows: out.write(json.dumps(row) + "\n")` is the entire library |
| `node:test` | Vitest 2.x | If `make-scripts/` ever grows TypeScript, Vite integration, snapshot testing, or browser-mode needs. Vitest is the right answer for any non-trivial JS codebase — but two ~200-LOC IIFE files don't qualify |
| `node:test` | Jest 29.x | Jest is the legacy default; for new projects in 2026 Vitest has surpassed it. For library/CLI-shaped surfaces, `node:test` is the recommended pick |
| `node:test` | Mocha + Chai | Configuration overhead with no upside over the built-in for this scope |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `requests`, `httpx`, `aiohttp` | Breaks D-13 stdlib-only-at-runtime; v1.0/v1.1 ethos is to add deps only when justified, and one-shot POST is not justification | `urllib.request` |
| `ndjson` / `jsonlines` PyPI packages | Trivially hand-rollable in 3 lines; adds an install-time dep with zero feature value | `json.dumps(row) + "\n"` per line |
| Logging response body / `err.read()` on HTTPError | T-PII-01 — payload echoes contain PII (email, phone, free-text answers). Status + categorical reason only | Log `err.code` + `err.reason` (categorical) |
| `verify=False` / disabled TLS | Webhook delivery is the egress point; trusting target cert is mandatory | `ssl.create_default_context()` (default) |
| Vitest / Jest / Mocha for `make-scripts/` | Two small IIFE files; tooling overhead exceeds value. v1.1 explicitly deferred this gating it on LOC growth | `node:test` + `node:assert/strict` |
| Babel / TypeScript compile step in `make-scripts/` | Make.com runs raw IIFE JS; introducing a build step creates source/runtime drift risk. CONVENTIONS.md mandates "what runs in Make.com is what's in the file" | Plain JS — no build step |
| `pytest-httpserver` / `responses` for AUTO-01 tests | Stdlib `http.server.BaseHTTPRequestHandler` in a daemon thread is sufficient for fake-webhook fixtures | Stdlib `http.server` |

## Stack Patterns by Variant

**If `--post-url` is set (AUTO-01):**
- `--validate` is implicitly required (AUTO-01 gates on VALI-01 success per PROJECT.md). Either auto-enable or hard-fail with a clear error if `--post-url` is set without `--validate`.
- Recommend: hard-fail. Rationale: explicit > implicit, and silently flipping a flag complicates the audit trail.

**If `--emit-format=ndjson` (STREAM-01):**
- `--validate` becomes per-row instead of whole-array. Lazy-compile validator once, call per row. This is a behavior change worth documenting in README + a new decision row.
- Output path differs: `json.dumps(row, separators=(",",":"))` — compact, never indented.
- Cannot be combined with `--post-url` in v1.2 (defer to v1.3 if/when target webhook supports NDJSON streaming).

**If `make-scripts/` LOC grows past ~500 or adds a third module:**
- Revisit `node:test` vs Vitest. The trigger is when `node:test`'s lack of snapshot/UI starts costing time, not when LOC crosses a magic number.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.7+ | `urllib.request` | All needed APIs (`Request`, `urlopen`, `HTTPError`, `URLError`, `timeout=`) stable since 3.6 |
| Python 3.7+ | `fastjsonschema>=2.21.2` | Already verified in v1.1 |
| Node 20.x LTS | `node:test` stable | First stable release; sufficient for v1.2 needs |
| Node 22.x LTS | `node:test` + `--experimental-test-coverage` | Coverage promoted to stable; mock-timer ergonomics improved. Recommended floor for new contributor docs |

## Open Questions for PLAN Phase

1. **AUTO-01 retry policy:** which HTTP statuses are retried? Recommend: 408, 429, 500, 502, 503, 504 + all `URLError`. Other 4xx is permanent.
2. **AUTO-01 + `--validate` coupling:** auto-enable or hard-fail? Recommend hard-fail.
3. **STREAM-01 flag name:** `--ndjson` vs `--emit-format=ndjson`. The latter scales to future formats. Recommend `--emit-format`.
4. **MAKE-TEST-01 IIFE refactor:** export a pure `transform()` function or wrap-and-eval the existing IIFE? Recommend refactor.

## Sources

- [Node.js v22.21.1 Test runner documentation](https://nodejs.org/docs/latest-v22.x/api/test.html) — verified `node:test` stable, watch mode, coverage status (HIGH)
- [Node.js v25.9.0 Test runner documentation](https://nodejs.org/api/test.html) — current API surface (HIGH)
- [Vitest — Comparisons with Other Test Runners](https://vitest.dev/guide/comparisons.html) — Vitest team's own positioning vs `node:test` (HIGH)
- [vitest-dev/vitest Discussion #4631 — Comparison with native node test runner](https://github.com/vitest-dev/vitest/discussions/4631) — community consensus on small-library use case (MEDIUM)
- [PkgPulse — node:test vs Vitest vs Jest (2026)](https://www.pkgpulse.com/blog/node-test-vs-vitest-vs-jest-native-test-runner-2026) — 2026 adoption trends (MEDIUM)
- [Python urllib.request — official docs](https://docs.python.org/3/library/urllib.request.html) — `Request`, `urlopen`, `timeout` parameter (HIGH)
- Existing repo: `.planning/PROJECT.md` (D-13, T-PII-01, VALI-01 lineage), `.planning/MILESTONES.md` (v1.2 deferred-bucket scope), `quizify_csv_ingest.py` (CLI integration surface) — direct read (HIGH)

---
*Stack research for: v1.2 Delivery & Make.com Hygiene (AUTO-01, STREAM-01, MAKE-TEST-01)*
*Researched: 2026-05-05*
