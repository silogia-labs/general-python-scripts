---
phase: 1
slug: csv-ingestion-column-layout
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
updated: 2026-05-03
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `quizify-csv-to-json-webhook/pytest.ini` (`pythonpath = .`) |
| **Quick run command** | `pytest quizify-csv-to-json-webhook/tests/ -q` |
| **Full suite command** | same |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest quizify-csv-to-json-webhook/tests/ -q`
- **After every plan wave:** Full suite
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-01 | 01-01 | 1 | CONV-02 | T-01 / V9 | No cell values in stderr summary | unit | `pytest quizify-csv-to-json-webhook/tests/ -q` | ✅ | ✅ green |
| T-02 | 01-02 | 1 | CONV-01 | T-01 / V9 | stderr-only diagnostics | integration | `pytest quizify-csv-to-json-webhook/tests/ -q` | ✅ | ✅ green |
| T-03 | 01-01 | 1 | D-05 trailer CLI | T-01 / V9 | trailer parse / override path | unit + integration | `pytest quizify-csv-to-json-webhook/tests/ -q` | ✅ | ✅ green |

---

## Requirement ↔ Test Coverage

| Requirement | Tests |
|-------------|--------|
| **CONV-02** | `test_sample_csv_header_classification` |
| **CONV-01** (Phase 1 scope: CLI input + stderr diagnostics, JSON deferred) | `test_dry_run_stderr_row_count`, `test_dry_run_with_trailer_columns_override`, `test_invalid_trailer_columns_exit_code` |
| **D-05** (`--trailer-columns`) | `test_parse_trailer_arg_roundtrip`, `test_parse_trailer_arg_rejects_empty`, `test_dry_run_with_trailer_columns_override`, `test_invalid_trailer_columns_exit_code` |

---

## Wave 0 Requirements

- [x] `quizify-csv-to-json-webhook/tests/test_layout.py` — classification, dry-run, trailer override, invalid trailer exit code
- [x] `quizify-csv-to-json-webhook/requirements-dev.txt` — pytest pin

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| *(none)* | — | — | — |

---

## Validation Audit 2026-05-03

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |

**Gaps closed**

1. **D-05 trailer override** — was implicit only via manual UAT; added `parse_trailer_arg` unit tests and subprocess tests with `--trailer-columns` / invalid empty trailer (exit 2).
2. **Per-task map stale** — Wave 0 / file-exists flags outdated; refreshed after tests landed.

---

## Validation Sign-Off

- [x] Wave 0 test files exist
- [x] `nyquist_compliant: true`

**Approval:** verified 2026-05-03
