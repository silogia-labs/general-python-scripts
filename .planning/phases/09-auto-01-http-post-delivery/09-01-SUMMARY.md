---
phase: 09
plan: 01
subsystem: http-post-delivery
tags: [http, urllib, ssl, pii-safe, tdd-red, mock-server]
type: tdd-red
requires:
  - phase-7-refactor-scaffolding-stub-_HttpPostSink
  - phase-8-ndjson-baseline-127-green
provides:
  - mock_webhook-fixture
  - test-surface-AUTO-01..06-RED
  - readme-cli-reference-prestage
affects:
  - quizify-csv-to-json-webhook/tests/conftest.py
  - quizify-csv-to-json-webhook/tests/test_http_post.py
  - quizify-csv-to-json-webhook/tests/test_http_post_pii.py
  - quizify-csv-to-json-webhook/tests/test_argparse_post_url.py
  - quizify-csv-to-json-webhook/tests/test_security_grep_gates.py
  - quizify-csv-to-json-webhook/README.md
tech-stack:
  added: [http.server, threading, urllib.error mocking]
  patterns: [mock-server-fixture, negative-substring-PII-suite, comment-stripped-grep-gates]
key-files:
  created:
    - quizify-csv-to-json-webhook/tests/test_http_post.py
    - quizify-csv-to-json-webhook/tests/test_http_post_pii.py
    - quizify-csv-to-json-webhook/tests/test_argparse_post_url.py
    - quizify-csv-to-json-webhook/tests/test_security_grep_gates.py
  modified:
    - quizify-csv-to-json-webhook/tests/conftest.py
    - quizify-csv-to-json-webhook/README.md
decisions:
  - "Pre-staged --header and --timeout README rows (drift test verified one-way: --help flags must be IN README, not vice versa). De-stubbed --post-url row simultaneously."
  - "PII suite uses caplog (logging.error) NOT capsys for primary capture (RESEARCH Q9); capsys.err checked too for defense-in-depth."
  - "302 test asserts len(received) == 1 (NOT 0) per RESEARCH Q10 / Pitfall 7 — original POST IS received before client-side _NoRedirectHandler refuses."
  - "Grep-gate tests strip line-leading comments (Nyquist hygiene) so a comment mentioning the gate pattern cannot self-invalidate it."
  - "Network-side reasons (tls/dns/refused/generic) tested via mock.patch.object(_HttpPostSink, '_post_once') with synthetic URLError exceptions — implementation must expose a _post_once seam (Plan 09-02)."
metrics:
  duration_minutes: ~15
  tasks_completed: 3
  files_changed: 6
  red_tests_collected: 32
  red_tests_failing: 29
  baseline_tests_passing: 127
  completed_date: 2026-05-06
---

# Phase 9 Plan 01: HTTP POST Delivery RED Scaffolding Summary

RED-only TDD scaffolding for AUTO-01..06: 4 new test files + extended conftest fixture + README pre-stage. 32 tests collected; 29 fail as expected (RED) because `_HttpPostSink` is still the Phase 7 stub. The 3 incidental passes are the Phase-7 carry-forward mutex test and the two grep gates that already structurally hold against the stub (`no_cert_disabling`, `no_requests_lib`). Plan 09-02 will turn the 29 RED tests GREEN.

## Files Created / Modified

| File | Status | Purpose |
|------|--------|---------|
| tests/conftest.py | modified | +85 lines: `_ReusableHTTPServer`, `_BaseHandler`, `mock_webhook`, 4 response factories |
| tests/test_http_post.py | created | 8 integration tests via mock_webhook (AUTO-01/02/03/05/06) |
| tests/test_http_post_pii.py | created | TestHTTPErrorPIIsafe + 4 mock-injected URLError parametrizations (T-PII-01) |
| tests/test_argparse_post_url.py | created | 11 pure-unit argparse rejection tests (AUTO-02/03/04/05) |
| tests/test_security_grep_gates.py | created | 5 source-level CI grep gates (D-09-18 + bonus) |
| README.md | modified | CLI-reference: de-stub `--post-url`, pre-stage `--header` + `--timeout` rows; Limitations bullet updated |

## Test Counts

- **New RED tests collected:** 32 (target was ≥ 25)
- **Currently failing (expected RED):** 29
- **Currently passing (incidental):** 3
  - `test_post_url_output_mutex` — Phase 7 mutex already in place
  - `test_no_cert_disabling` — stub trivially passes (no SSL code yet)
  - `test_no_requests_lib` — stub uses no third-party libs
- **Baseline tests (excluding 4 new RED files):** 127 passed, 4 skipped — UNCHANGED.

## Carry-Forward Gates

| Gate | Status |
|------|--------|
| D-11 README drift (`tests/test_readme_help_alignment.py`) | 2/2 GREEN |
| D-11 ten-section H2 lock | 10 sections preserved |
| TRAIL-03 byte-identity (`tests/test_default_order_regression.py`) | 3/3 GREEN |
| 127 baseline tests | GREEN (unchanged from Phase 8 close) |

## Conftest Pattern Conformance (RESEARCH refinements)

| Refinement | Implemented |
|-----------|-------------|
| `allow_reuse_address = True` (Pitfall 10) | yes |
| `log_message` overridden to `pass` (Pitfall 9) | yes |
| `_respond_hang` finite 2.0s sleep (Pitfall 2) | yes |
| Teardown: `shutdown()` → `server_close()` → `thread.join(timeout=2.0)` | yes |
| 13-byte `b"Bad Gateway!!"` body for explicit `body_bytes=13` | yes |
| `Location: http://other.example.test/x` on 302 | yes |
| `b"server_response_marker"` sentinel on 200/hang | yes |
| `do_POST` captures `(verb, body, headers_dict)` for AUTO-03 inspection | yes |

## Decision Taken: README Pre-Stage Scope

Read `tests/test_readme_help_alignment.py` first. Drift test is **one-way**: every long flag in `--help` must appear in README; the reverse is not enforced. Therefore:

- Pre-staged BOTH `--header` and `--timeout` rows (decision rule branch B from PLAN.md).
- De-stubbed `--post-url` row.
- Updated Limitations bullet to drop `NotImplementedError` stub language.
- Drift test confirmed green AFTER edits; Plan 09-02 can wire the argparse flags without further README edits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical correctness] Updated Limitations bullet**
- **Found during:** Task 3 verification (acceptance criterion `NotImplementedError count == 0`)
- **Issue:** Plan only described table-row edits, but the Limitations section retained a "raises NotImplementedError if invoked" sentence that contradicted the de-stubbed CLI-reference row and violated the acceptance criterion.
- **Fix:** Rewrote that bullet to point at the new contract instead.
- **Files modified:** README.md (Limitations bullet)
- **Commit:** 91f51ec

No other deviations. Mock-server skeleton, RED test set, and grep gates match RESEARCH / CONTEXT / VALIDATION verbatim.

## Threat-Model Conformance

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-09-01-01 (Info Disclosure: test fixtures) | mitigate | Synthetic markers only (`marker_email_50@example.test`, `+15555550042`, `marker_freetext_xyzzy`); `quizify-submissions.csv` PII never enters mock-server bodies |
| T-09-01-02 (Info Disclosure: BaseHTTPRequestHandler logs) | mitigate | `_BaseHandler.log_message = pass` |
| T-09-01-03 (Repudiation: thread leak) | mitigate | Finite 2.0s `_respond_hang`; teardown shutdown + join(timeout=2.0) |
| T-09-01-04 (Tampering: port flake) | mitigate | `allow_reuse_address = True` |
| T-09-01-05 (Self-invalidating grep gates) | mitigate | All 5 grep tests count against `re.sub(r"^\s*#.*$", "", SRC, MULTILINE)` |

## Commits

| # | Hash | Type | Message |
|---|------|------|---------|
| 1 | 190a17c | test | mock_webhook fixture + 4 response factories |
| 2 | 1f10984 | test | RED test suites for AUTO-01..06 (32 tests) |
| 3 | 91f51ec | docs | Pre-stage --header / --timeout; de-stub --post-url |

## TDD Gate Compliance

This plan is the **RED gate** of Phase 9's two-plan RED/GREEN split (mirroring Phase 8). Two `test(...)` commits land here; the GREEN gate (`feat(09-02): ...`) lands in Plan 09-02.

## Handoff Note for Plan 09-02

All AUTO-01..06 tests are RED and collected. Plan 09-02 must:

1. Implement `_HttpPostSink.__init__(self, url, headers, timeout)` — replace 1-arg Phase 7 stub.
2. Add `_NoRedirectHandler` (HTTPRedirectHandler subclass; redirect_request raises HTTPError with reason `http_unexpected_redirect`).
3. Add `_log_http_failure(reason, *, status, reason_class, body_bytes)` emitting via `logging.error("http_failure reason=%s status=%s reason_class=%s body_bytes=%s", ...)`.
4. Add `_parse_header(s)` and `_https_url(s)` argparse `type=` callables with the locked rejection vocabulary.
5. Add `--header` (action=append, default=[]) and `--timeout` (type=float, default=30.0; parser.error("timeout_invalid") if <= 0) flags; add post-parse check `if args.post_url and not args.validate: parser.error("post_url_requires_validate")`; add `type=_https_url` to `--post-url`.
6. Build a single `OpenerDirector` once (one `ssl.create_default_context()`, one `_NoRedirectHandler`); the POST happens via exactly ONE `self._opener.open(request, timeout=...)` call.
7. Surface a `_post_once` seam so `tests/test_http_post_pii.py` can `mock.patch.object(_HttpPostSink, "_post_once", side_effect=URLError(...))` to drive network-side reasons.
8. Catch `HTTPError` / `URLError` / `socket.timeout` and map to the 8 locked reasons; `sys.exit(3)` after `_log_http_failure(...)`.

After 09-02 lands, all 32 tests should be GREEN, plus the existing 127 baseline. Total target: 159 tests passing at Phase 9 close.

## Self-Check: PASSED

Files verified to exist:
- FOUND: quizify-csv-to-json-webhook/tests/conftest.py (modified)
- FOUND: quizify-csv-to-json-webhook/tests/test_http_post.py
- FOUND: quizify-csv-to-json-webhook/tests/test_http_post_pii.py
- FOUND: quizify-csv-to-json-webhook/tests/test_argparse_post_url.py
- FOUND: quizify-csv-to-json-webhook/tests/test_security_grep_gates.py
- FOUND: quizify-csv-to-json-webhook/README.md (modified)

Commits verified in `git log --oneline -5`:
- FOUND: 190a17c
- FOUND: 1f10984
- FOUND: 91f51ec
