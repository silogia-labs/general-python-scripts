# Roadmap: Quizify CSV → Webhook JSON

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-03) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Contract Hardening & Make.com Alignment** — Phases 4-6 (shipped 2026-05-04) — see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 Delivery & Make.com Hygiene** — Phases 7-10 (in progress, started 2026-05-05)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-05-03</summary>

- [x] Phase 1: CSV ingestion & column layout (1/1 plans) — completed 2026-05-03
- [x] Phase 2: Core webhook mapping (2/2 plans) — completed 2026-05-03
- [x] Phase 3: Scoring metadata & packaging (2/2 plans) — completed 2026-05-03

</details>

<details>
<summary>✅ v1.1 Contract Hardening & Make.com Alignment (Phases 4-6) — SHIPPED 2026-05-04</summary>

- [x] Phase 4: Make.com JS Contract Fixes (2/2 plans) — completed 2026-05-04
- [x] Phase 5: Python Trailer Hardening (3/3 plans) — completed 2026-05-04
- [x] Phase 6: JSON Schema Validation (4/4 plans) — completed 2026-05-04

</details>

### v1.2 Delivery & Make.com Hygiene (Phases 7-10) — IN PROGRESS

- [x] **Phase 7: Refactor Scaffolding (no-op)** — Extract `iter_rows()` generator + sink abstraction with byte-identical default output. (2/2 plans) — completed 2026-05-06
- [x] **Phase 8: STREAM-01 NDJSON Output** — `--ndjson` flag, per-row validation against `schema["items"]`, atomic file writes. (2/2 plans) — completed 2026-05-05
- [ ] **Phase 9: AUTO-01 HTTP POST Delivery** — `--post-url` gated on `--validate`, HTTPS-only, PII-safe error logging via locked D-06-2x templates.
- [ ] **Phase 10: Make.com Hygiene & Node Test Harness** — Cosmetic typo/dead-code fixes plus `node:test` regression net (parallel-safe with Phases 7-9).

## Phase Details

### Phase 7: Refactor Scaffolding (no-op)
**Goal**: `convert()` is restructured around an `iter_rows()` generator and three pluggable output sinks (`_StdoutSink`, `_FileSink`, `_HttpPostSink` stub) with default invocation behavior unchanged.
**Depends on**: Phase 6 (v1.1 closed; schema artifact + `--validate` in place)
**Requirements**: REFACTOR-01
**Success Criteria** (what must be TRUE):
  1. Default-flag invocation against `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` produces byte-identical output to the v1.1 golden fixture (parallel test to TRAIL-03 stays green).
  2. `iter_rows()` yields one dict per CSV row; nothing accumulates the full list inside the generator path.
  3. `_HttpPostSink` exists as a stub that raises `NotImplementedError` if invoked; argparse exposes a mutually-exclusive `-o`/`--post-url` group.
  4. All 94 v1.1 tests still pass; D-11 README ten-section drift test (2/2) stays green; no new Python runtime dependencies (D-13 preserved).
**Plans:** 2 plans
  - [x] 07-01-PLAN.md — Test scaffolding (RED): byte-identity capsys twin + sink-layer tests + README CLI table row for --post-url.
  - [x] 07-02-PLAN.md — Refactor (GREEN): extract iter_rows + sink Protocol + _HttpPostSink stub; argparse mutex group; convert() rewrite.

### Phase 8: STREAM-01 NDJSON Output
**Goal**: Operators emitting to a file can opt into line-delimited JSON output with per-row schema validation and atomic-write guarantees, without changing default-mode behavior.
**Depends on**: Phase 7 (sink abstraction + `iter_rows()` in place)
**Requirements**: STREAM-01, STREAM-02, STREAM-03, STREAM-04
**Success Criteria** (what must be TRUE):
  1. `python quizify_csv_ingest.py csv -o out.ndjson --ndjson` emits exactly N lines for N rows, each terminated by a single `\n`, no `\r` bytes anywhere; `jq -s . out.ndjson` reproduces the v1.1 golden array structurally.
  2. `--ndjson --validate` against a CSV with a malformed row at position 50 of 100 exits non-zero with a JSON-Pointer-only stderr (no cell content); the final output path does not exist (only the `.tmp` sibling).
  3. Argparse rejects `--ndjson` combined with `--post-url` and rejects `--ndjson` writing to stdout (file-mode target only); error messages are categorical and PII-safe.
  4. SIGINT mid-stream leaves no partial file at the target path (verified by SIGINT test); `os.replace()` is the only path that promotes `.tmp` to final.
  5. Default array-mode invocation remains byte-identical to v1.1 (TRAIL-03 golden-fixture regression test green); D-05 top-level key order unchanged; D-13 stdlib-only-at-runtime preserved.
**Plans:** 2 plans
  - [x] 08-01-PLAN.md — RED scaffolding: test stubs for STREAM-01..04 + Pitfall 8-D regression + argparse rejections + synthetic 100-row CSV fixture + README `--ndjson` row (D-11 pre-stage).
  - [x] 08-02-PLAN.md — GREEN implementation: `_NdjsonFileSink` (CM) + `_ValidatingSink` decorator + `_RowValidationError` + `__enter__/__exit__` shims + `--ndjson` argparse flag + 2 post-parse `parser.error` checks + `_select_sink` extension + `convert()` rewrite.

### Phase 9: AUTO-01 HTTP POST Delivery
**Goal**: Operators can deliver the validated JSON-array payload directly to a Make.com webhook over HTTPS in a single shot, with PII-safe error surfaces and no schema-invalid payloads ever leaving the process.
**Depends on**: Phase 8 (sink contract + per-row validation primitives proven; `_validate_one` reusable for AUTO-01 gating)
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04, AUTO-05, AUTO-06
**Success Criteria** (what must be TRUE):
  1. POST to a mock webhook with a malformed CSV plus `--post-url --validate` results in **0 server requests received** (validation gate works); exit code is the validation-failure code, not the HTTP-failure code.
  2. `--post-url` invoked without `--validate` exits 2 at argparse with a categorical message naming the dependency; `http://` URLs are rejected at argparse; CRLF in `--header` values is rejected at argparse.
  3. A non-2xx response from the mock server produces exactly one request (no retry), exit code 3, and stderr matching the locked D-06-2x templates — status code + reason class + body byte count only, with negative-substring tests asserting no email / phone / free-text / response-body-byte content from `quizify-submissions.csv`-derived synthetic fixtures appears anywhere on stderr (T-PII-01 carry-forward).
  4. A 302 redirect to a different host produces exit non-zero with a categorical `http_unexpected_redirect` log line (target URL never logged); CI grep gate on `CERT_NONE` / `_create_unverified_context` / `verify=False` stays clean; default `ssl.create_default_context()` is the only TLS context constructed.
  5. `--timeout SECONDS` (default 30) is passed on every `urlopen()` call (CI grep gate verifies); a deliberately-stalled mock server triggers exit 3 with a categorical `network_timeout` reason.
  6. D-13 stdlib-only-at-runtime preserved (only `urllib.request` / `urllib.error` / `ssl` from stdlib added); D-05 JSON key order unchanged; D-11 README ten-section lock + drift test stays green after AUTO-01 documentation lands.
**Plans:** 2 plans
  - [x] 09-01-PLAN.md — RED scaffolding (TDD): mock_webhook fixture + 4 response handlers + AUTO-01..06 integration/PII/argparse/grep-gate test suites; pre-stage README CLI rows. (32 RED tests collected, 29 failing as expected, 127 baseline green; 2026-05-06)
  - [x] 09-02-PLAN.md — GREEN implementation (TDD): _NoRedirectHandler, _log_http_failure, _parse_header, _https_url, real _HttpPostSink body, 3 new argparse flags + 2 post-parse checks, _HttpDeliveryError → exit 3 wiring; final README. (29 RED tests turned GREEN; 5/5 CI grep gates pass; 158 tests total; 2026-05-05)

### Phase 10: Make.com Hygiene & Node Test Harness
**Goal**: The two co-owned Make.com JS modules ship cosmetic fixes locked behind a zero-dependency `node:test` regression net that retroactively covers v1.1 fixes and prevents accidental global writes or npm dependency creep.
**Depends on**: Nothing in v1.2 — fully independent of Phases 7-9 and parallel-safe from day 1.
**Requirements**: MAKE-COSMETIC-01, MAKE-COSMETIC-02, MAKE-TEST-01, MAKE-TEST-02, MAKE-TEST-03
**Success Criteria** (what must be TRUE):
  1. The `Reomoto` → `Remoto` typo at `score-calculations.js:157` is locked by a `node:test` case that fails before the fix and passes after; the dead `profile = "profile_base"` initializer at `score-calculations.js:217` is removed and a test asserts `profile_base` does not appear in module output.
  2. `node --test quizify-csv-to-json-webhook/make-scripts/` runs green with regression coverage for CONTRACT-01, MAKE-FIX-01 (`peri_menu` underscore), MAKE-FIX-02 (`activity_profile` non-athlete default), and MAKE-COSMETIC-01/02 — each assertion cites a `make-scripts/CONVENTIONS.md` line (no opaque snapshots).
  3. Both JS modules expose a pure `mapRecord(record)` function with `module.exports` guarded by `typeof module !== "undefined"`; deployed Make.com files paste in unchanged; `"use strict";` is at the top of every module; a `globalThis` snapshot test detects accidental global writes across `mapRecord(fixture)` calls.
  4. `make-scripts/package.json` ships with empty `dependencies` and empty `devDependencies` (CI gate enforces); `pyproject.toml` `[tool.pytest.ini_options]` adds `norecursedirs = ["make-scripts", "node_modules"]`; `make-scripts/.gitignore` blocks `node_modules/` and `coverage/`.
  5. JS test fixtures are synthetic-only (T-PII-01 carry-forward — no PII from `quizify-submissions.csv` in `make-scripts/tests/fixtures/`); README documentation additions for `make-scripts/` testing keep the D-11 ten-section lock + drift test green.
**Plans:** 2/3 plans executed
  - [x] 10-01-PLAN.md — RED scaffolding: mapRecord+footer wrap (typo+dead-init PRESERVED), 6 node:test files, fixtures, package.json, .gitignore, pyproject.toml norecursedirs, 2 Python grep-gate tests.
  - [x] 10-02-PLAN.md — GREEN cosmetic fixes: Reomoto→Remoto at score-calculations.js:157; remove dead profile_base init at :217. Flips 6/6 node:test files green.
  - [ ] 10-03-PLAN.md — CI wiring + README docs: fresh .github/workflows/ci.yml with parallel pytest + make-scripts-test jobs; ### Make.com module tests subsection under ## Development (D-11 lock preserved).

## Progress

| Phase | Milestone | Plans Complete | Status   | Completed  |
| ----- | --------- | -------------- | -------- | ---------- |
| 1. CSV ingestion & column layout    | v1.0 | 1/1 | Complete    | 2026-05-03 |
| 2. Core webhook mapping             | v1.0 | 2/2 | Complete    | 2026-05-03 |
| 3. Scoring metadata & packaging     | v1.0 | 2/2 | Complete    | 2026-05-03 |
| 4. Make.com JS Contract Fixes       | v1.1 | 2/2 | Complete    | 2026-05-04 |
| 5. Python Trailer Hardening         | v1.1 | 3/3 | Complete    | 2026-05-04 |
| 6. JSON Schema Validation           | v1.1 | 4/4 | Complete    | 2026-05-04 |
| 7. Refactor Scaffolding (no-op)     | v1.2 | 2/2 | Complete    | 2026-05-06 |
| 8. STREAM-01 NDJSON Output          | v1.2 | 2/2 | Complete    | 2026-05-05 |
| 9. AUTO-01 HTTP POST Delivery       | v1.2 | 2/2 | Complete    | 2026-05-05 |
| 10. Make.com Hygiene & Node Tests   | v1.2 | 2/3 | In Progress|  |
