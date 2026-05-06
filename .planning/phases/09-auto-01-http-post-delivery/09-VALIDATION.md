---
phase: 9
slug: auto-01-http-post-delivery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 9 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest -x -q` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~3–4 seconds (current 1.28s + ~1s mock-server tests + ~0.5s timeout) |

## Sampling Rate

- After every task commit: `python -m pytest -x -q`
- After every plan wave: `python -m pytest`
- Before `/gsd-verify-work`: full suite green; TRAIL-03 + D-11 README drift gates included.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 9-XX | XX | 1 | AUTO-01 | T-PII-01 | Happy-path POST sends array body once; status 200 → exit 0 | integration | `python -m pytest tests/test_http_post.py::test_happy_path_sends_one_request -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-01 | — | `len(received) == 1` (no retry) | integration | `python -m pytest tests/test_http_post.py::test_exactly_one_request -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-02 | — | `--post-url` without `--validate` → exit 2 categorical | unit | `python -m pytest tests/test_argparse_post_url.py::test_post_url_requires_validate -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-02 | T-PII-01 | Schema-invalid CSV + `--post-url --validate` → 0 server requests | integration | `python -m pytest tests/test_http_post.py::test_validation_failure_no_egress -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-03 | — | Repeatable `--header`; CRLF rejected at argparse | unit | `python -m pytest tests/test_argparse_post_url.py::test_header_crlf_rejected -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-03 | — | Header missing-colon / empty-name / invalid-name rejected | unit | `python -m pytest tests/test_argparse_post_url.py::test_header_validation -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-04 | T-PII-01 | `--timeout` default 30; stalled server → exit 3 + `network_timeout` | integration | `python -m pytest tests/test_http_post.py::test_timeout -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-05 | — | `http://` URL → argparse exit 2 | unit | `python -m pytest tests/test_argparse_post_url.py::test_https_required -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-05 | T-PII-01 | 302 cross-host → exit 3 + `http_unexpected_redirect`; target URL never logged | integration | `python -m pytest tests/test_http_post.py::test_302_rejected -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-05 | — | CI grep gate: no `CERT_NONE`/`_create_unverified_context`/`verify=False` | grep | `! grep -nE "CERT_NONE\|_create_unverified_context\|verify=False" quizify-csv-to-json-webhook/quizify_csv_ingest.py` | ⬜ |
| 9-XX | XX | 1 | AUTO-05 | — | CI grep gate: exactly 1 `ssl.create_default_context()` | grep | `[ "$(grep -c 'ssl.create_default_context' quizify-csv-to-json-webhook/quizify_csv_ingest.py)" = "1" ]` | ⬜ |
| 9-XX | XX | 1 | AUTO-04/06 | — | CI grep gate: exactly 1 `self._opener.open(` (single-shot, timeout always passed) | grep | `[ "$(grep -c 'self._opener.open(' quizify-csv-to-json-webhook/quizify_csv_ingest.py)" = "1" ]` | ⬜ |
| 9-XX | XX | 1 | AUTO-06 | T-PII-01 | 502 → exit 3, stderr matches `http_failure reason=http_server_error status=502 reason_class=5xx body_bytes=<N>` | integration | `python -m pytest tests/test_http_post.py::test_502_categorical -x` | ⬜ |
| 9-XX | XX | 1 | AUTO-06 | T-PII-01 | Negative-substring: PII tokens + response-body markers never on stderr | integration | `python -m pytest tests/test_http_post_pii.py -x` | ⬜ |
| 9-XX | XX | 1 | (D-13) | — | CI grep gate: no `requests` library import | grep | `! grep -nE "^(import\|from) requests" quizify-csv-to-json-webhook/quizify_csv_ingest.py` | ⬜ |
| 9-XX | XX | 1 | (carry / D-11) | — | README drift 2/2 green | unit | `python -m pytest tests/test_readme_help_alignment.py -x` | ⬜ |
| 9-XX | XX | 1 | (carry / TRAIL-03) | — | Default array byte-identity stays green | unit | `python -m pytest tests/test_default_order_regression.py -x` | ⬜ |

## Wave 0 Requirements

- [ ] `tests/test_http_post.py` — happy path, request-count, 502, 302, timeout integration tests via `mock_webhook`
- [ ] `tests/test_http_post_pii.py` — `TestHTTPErrorPIIsafe` negative-substring suite
- [ ] `tests/test_argparse_post_url.py` — argparse HTTPS, `--post-url requires --validate`, `--header` CRLF/missing/invalid, `--timeout` invalid
- [ ] `tests/conftest.py` — `mock_webhook(factory)` fixture, handler factories (`_Handler200`, `_Handler502`, `_Handler302`, `_HandlerHang`), `allow_reuse_address=True`, daemon thread + `shutdown()`+`server_close()`+`thread.join(timeout=2.0)` cleanup, `log_message = pass`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end POST to real Make.com webhook | AUTO-01 | Live Make.com endpoint can't be exercised in CI without secrets | Operator runs `python quizify_csv_ingest.py docs/quizify-submissions.csv --post-url https://hook.make.com/... --validate --header "Authorization: Bearer $TOKEN"` against a staging webhook; verify Make.com receives one record and downstream automation fires. |
| TLS chain validation against real CA | AUTO-05 | CI may have non-default CA bundle | Operator confirms POST to a known-good HTTPS endpoint succeeds and POST to a self-signed cert fails with `tls_error`. |

## Validation Sign-Off

- [ ] Per-task verification map filled by planner
- [ ] Wave 0 covers all MISSING references (3 new test modules + 1 fixture extension)
- [ ] No watch-mode flags
- [ ] Feedback latency < 4s
- [ ] `nyquist_compliant: true` set after planner finalizes per-task map

**Approval:** pending
