---
phase: 2
slug: core-webhook-mapping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing in `quizify-csv-to-json-webhook/`) |
| **Config file** | `quizify-csv-to-json-webhook/pytest.ini` |
| **Quick run command** | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py` |
| **Full suite command** | `cd quizify-csv-to-json-webhook && pytest -q` |
| **Estimated runtime** | ~3 seconds (pure-stdlib, no I/O fixtures of significance) |

---

## Sampling Rate

- **After every task commit:** Run `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py`
- **After every plan wave:** Run `cd quizify-csv-to-json-webhook && pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | — | — | Test scaffolding | unit | `cd quizify-csv-to-json-webhook && pytest -q --collect-only tests/test_row_builder.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CONV-03, CONV-04, CONV-05 | — | Contact + status mapping does not echo PII to logs | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py::test_contact_and_status_mapping` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | CONV-06 | — | HTML entity decoding applied uniformly | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py::test_html_entity_decode` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | WEB-02, WEB-03 | — | Multi-select detected via `, ` heuristic; single-answer emits object array without `id` | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py::test_answer_shape_heuristic` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | WEB-01 | — | Tag-map distributes per-question tags; unmatched flow into top-level `tags` with WARNING | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py::test_tag_distribution` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | WEB-02 | — | Empty-cell row emits all `question-N`/`answers-N`/`answers-tags-N` keys with `""` | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py::test_empty_cells_emit_all_keys` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 2 | CONV-03..06, WEB-01..03 | — | CLI default emits JSON to stdout; `--dry-run` retains Phase 1 layout preview; `-o PATH` writes file | integration | `cd quizify-csv-to-json-webhook && pytest -q tests/test_cli_emit.py` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 2 | — | T-PII-01 (logging) | Stderr WARNING text contains no PII (no email, phone, free-text answer) | unit | `cd quizify-csv-to-json-webhook && pytest -q tests/test_logging_pii.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | WEB-02, WEB-03 | — | Aligned fixture row produces JSON whose key set + per-key types match `webhook-quizify-format-example.json` (with `id` and Phase 3 keys excluded) | golden | `cd quizify-csv-to-json-webhook && pytest -q tests/test_golden_structure.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | WEB-02 | — | Sample CSV rows yield JSON satisfying structural invariants (every dynamic N has all 3 keys; status/statusDate/tags top-level present) | property-style | `cd quizify-csv-to-json-webhook && pytest -q tests/test_structural_invariants.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `quizify-csv-to-json-webhook/tests/test_row_builder.py` — stubs for row-builder unit tests (CONV-03..06, WEB-01..03)
- [ ] `quizify-csv-to-json-webhook/tests/test_cli_emit.py` — stub for end-to-end CLI integration test
- [ ] `quizify-csv-to-json-webhook/tests/test_logging_pii.py` — stub for PII-in-logs assertions
- [ ] `quizify-csv-to-json-webhook/tests/test_golden_structure.py` — stub for golden-file structural diff (Plan 02-02)
- [ ] `quizify-csv-to-json-webhook/tests/test_structural_invariants.py` — stub for structural invariants over the live sample CSV
- [ ] `quizify-csv-to-json-webhook/tests/conftest.py` — shared fixtures: aligned-example fixture row, red-flag-short-circuit row, multi-select fixture row, sample-CSV path

*Existing `tests/test_layout.py` (Phase 1) covers header classification — no changes.*

---

## Sample Size Targets (Nyquist signal classes)

| Signal class | Minimum fixtures | Rationale |
|--------------|------------------|-----------|
| Contact + status + statusDate mapping | 3 rows: Yes/subscribed, No/unsubscribed, unexpected-value/warning | Cover D-11 branches |
| HTML entity decoding | 2 rows: `&gt;`/`&lt;` present and absent | Confirm uniform application across keys |
| Multi-select detection | 3 fixtures: `, ` present (string), space-joined (object array per D-05), single-token (object array) | Verify heuristic + sample-derived edge case from research |
| Tag distribution | 3 rows: tag matches answered q, tag matches empty-answer q, tag unmatched (fallback path) | Cover D-01..04 |
| Empty cells | 1 fixture: red-flag short-circuit row (most blanks) | Confirm D-09 stable indexing |
| Golden structural | 1 aligned fixture | Plan 02-02 |
| Structural invariants over sample | All sample CSV rows | Property-style assertions |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual diff of converted output vs `webhook-quizify-format-example.json` | WEB-02, WEB-03 | Final eyeball pass before sign-off; structural test cannot catch all readability issues | Run `python -m quizify_csv_ingest docs/quizify-submissions.csv \| less` and compare key ordering / formatting against the example file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
