---
phase: 8
slug: stream-01-ndjson-output
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest -x -q` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~2–3 seconds (currently 1.28s for 111 tests; +~10–15 new tests expected) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -x -q`
- **After every plan wave:** Run `python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green; TRAIL-03 + D-11 README drift tests included
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

> Filled in by the planner during PLAN.md generation. Each task gains an automated command linked to a STREAM-0X requirement, plus an entry mapping to the locked carry-forward regression tests (TRAIL-03 byte-identity, D-11 README drift).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-XX-XX | XX | W | STREAM-01 | T-PII-01 | NDJSON file emits N lines for N rows, no `\r` | unit | `python -m pytest tests/test_ndjson.py::test_line_count_and_separator -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-02 | — | `newline="\n"` defeats CRLF translation | unit | `python -m pytest tests/test_ndjson.py::test_no_cr_bytes -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-03 | T-PII-01 | Per-row failure → exit 1, JSON-Pointer-only stderr | unit | `python -m pytest tests/test_ndjson_validation.py -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-03 | T-PII-01 | Negative-substring assert (no email/phone/free-text) | unit | `python -m pytest tests/test_ndjson_validation.py::test_pii_safe_stderr -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-04 | — | Validation failure → target file does not exist | unit | `python -m pytest tests/test_atomic_write.py::test_no_target_on_validation_failure -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-04 | — | SIGINT mid-stream → no target file | subprocess | `python -m pytest tests/test_atomic_write.py::test_sigint_leaves_no_target -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-04 | — | Unit-level `__exit__(KeyboardInterrupt)` cleans up `.tmp` | unit | `python -m pytest tests/test_ndjson.py::test_exit_unlinks_tmp_on_exception -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-01 | — | Argparse rejects `--ndjson + --post-url` (exit 2) | unit | `python -m pytest tests/test_argparse.py::test_ndjson_post_url_mutex -x` | ✅ existing | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-01 | — | Argparse rejects `--ndjson` without `-o` (exit 2) | unit | `python -m pytest tests/test_argparse.py::test_ndjson_requires_output -x` | ✅ existing | ⬜ pending |
| 8-XX-XX | XX | W | (carry) | — | TRAIL-03 byte-identity stays green | unit | `python -m pytest tests/test_refactor_byte_identity.py -x` | ✅ existing | ⬜ pending |
| 8-XX-XX | XX | W | (carry / D-11) | — | README CLI-reference drift (2/2) | unit | `python -m pytest tests/test_readme_help_alignment.py -x` | ✅ existing | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-01 | — | NDJSON output round-trips structurally to v1.1 array | integration | `python -m pytest tests/test_ndjson.py::test_jq_equivalent_to_array -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-04 | — | `os.replace` is the ONLY promotion path (CI grep) | grep | `! grep -nE "shutil.move\\(|os.rename\\(" quizify-csv-to-json-webhook/quizify_csv_ingest.py` | ✅ existing | ⬜ pending |
| 8-XX-XX | XX | W | STREAM-04 | — | Pitfall 8-D regression: `.tmp` naming preserves multi-suffix | unit | `python -m pytest tests/test_ndjson.py::test_tmp_path_preserves_suffix -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ndjson.py` — stubs for STREAM-01, STREAM-02, line-count, separator, no-CR, jq-structural-equivalence, `__exit__` cleanup, Pitfall 8-D `.tmp` naming
- [ ] `tests/test_ndjson_validation.py` — stubs for STREAM-03 per-row validation, JSON-Pointer prefix format `/<idx><pointer>`, PII-safe negative-substring asserts
- [ ] `tests/test_atomic_write.py` — stubs for STREAM-04 (validation-failure no-target, SIGINT subprocess no-target)
- [ ] `tests/test_argparse.py` — extend (or new) stubs for `--ndjson + --post-url` rejection and `--ndjson` requires `-o` rejection
- [ ] `tests/conftest.py` — synthetic 100-row CSV factory fixture with malformed row at index 50 (T-PII-01-safe; no real PII)

*All planner-named filenames are guidance; planner may consolidate or rename.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-platform `newline="\n"` on Windows | STREAM-02 | CI runs Linux; Windows CRLF translation cannot be exercised in this repo's CI | Spot-check on a Windows machine: `python quizify_csv_ingest.py docs/quizify-submissions.csv -o out.ndjson --ndjson` then `python -c "import sys; b=open('out.ndjson','rb').read(); assert b'\\r' not in b"` |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (4 new test modules + 1 fixture extension)
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner finalizes Per-Task Verification Map)

**Approval:** pending
