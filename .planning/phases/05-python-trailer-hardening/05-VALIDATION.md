---
phase: 5
slug: python-trailer-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (unpinned in `requirements-dev.txt`; 71 tests at v1.0 close, baseline 1.10s) |
| **Config file** | `quizify-csv-to-json-webhook/pytest.ini` (`pythonpath = .`) |
| **Quick run command** | `cd quizify-csv-to-json-webhook && python3 -m pytest -q` |
| **Full suite command** | `cd quizify-csv-to-json-webhook && python3 -m pytest -q --tb=short` |
| **Estimated runtime** | ~1.1s baseline (budget: ≤2.5s post-Phase-5 per Pitfall 16) |

---

## Sampling Rate

- **After every task commit:** Run `cd quizify-csv-to-json-webhook && python3 -m pytest -q`
- **After every plan wave:** Run `cd quizify-csv-to-json-webhook && python3 -m pytest -q --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green; new TRAIL-01/02/03 test classes all green
- **Max feedback latency:** ~2 seconds (full suite, by design — fast enough to run unconditionally per Pitfall 16)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD-01 | TBD | 0 | precondition | — | Confirm clean working tree (CSV reverted; baseline 71 green) | preflight | `git diff --stat quizify-csv-to-json-webhook/docs/quizify-submissions.csv && cd quizify-csv-to-json-webhook && python3 -m pytest -q` | ✅ (verified 71 passed in 1.10s post-revert) | ✅ green |
| TBD-02 | TBD | 0 | TRAIL-03 | — | Generate v1.0 golden output JSON for the 42-row sample BEFORE any production change | preflight | `cd quizify-csv-to-json-webhook && python3 quizify_csv_ingest.py docs/quizify-submissions.csv > tests/fixtures/v1.0_default_order_output.json` | ❌ W0 (Pitfall G) | ⬜ pending |
| TBD-03 | TBD | 0 | TRAIL-01/02 | — | conftest.py: add `scoring_index_map_default` fixture | unit-fixture | `pytest --collect-only tests/conftest.py` | ❌ W0 (D-05-06) | ⬜ pending |
| TBD-04 | TBD | 1 | TRAIL-01 | — | classify_headers returns scoring_index_map matching scrambled --trailer-columns | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_scrambled_order_maps_by_name -x` | ❌ W0 | ⬜ pending |
| TBD-05 | TBD | 1 | TRAIL-01 | — | NFC+casefold equality (Pitfall 11) | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_normalization_handles_case_and_diacritics -x` | ❌ W0 | ⬜ pending |
| TBD-06 | TBD | 1 | TRAIL-01 | — | build_row reads trio from name-keyed indices, not [0/1/2] | unit | `pytest tests/test_row_builder.py::TestScrambledTrailer::test_scrambled_order_binds_correctly -x` | ❌ W0 | ⬜ pending |
| TBD-07 | TBD | 1 | TRAIL-02 | T-PII-01 | Missing trio column → `missing_trio_names` contains canonical name | unit | `pytest tests/test_layout.py::TestScoringIndexMap::test_missing_column_listed -x` | ❌ W0 | ⬜ pending |
| TBD-08 | TBD | 1 | TRAIL-02 | T-PII-01 | convert() emits exactly one logging.warning per missing canonical with locked D-05-08 message | unit (caplog) | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_warning_message_matches_locked_template -x` | ❌ W0 | ⬜ pending |
| TBD-09 | TBD | 1 | TRAIL-02 | — | build_row emits "" for missing trio name (no positional fallback — Pitfall 10) | unit | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_missing_column_emits_empty_string -x` | ❌ W0 | ⬜ pending |
| TBD-10 | TBD | 1 | TRAIL-02 | T-PII-01 | Empty cell in *present* column is silent (D-03 carry-forward) | unit | `pytest tests/test_row_builder.py::test_empty_scoring_emits_empty_strings` (existing — must stay green) | ✅ | ⬜ pending |
| TBD-11 | TBD | 1 | TRAIL-02 | T-PII-01 | Warning contains no cell content / contact tokens | unit | `pytest tests/test_row_builder.py::TestMissingColumnWarning::test_warning_pii_safe -x` | ❌ W0 | ⬜ pending |
| TBD-12 | TBD | 2 | TRAIL-03 | — | Default --trailer-columns → 42-row sample output structurally equal to v1.0 baseline | regression | `pytest tests/test_default_order_regression.py -x` | ❌ W0 | ⬜ pending |
| TBD-13 | TBD | 2 | TRAIL-03 | — | All 14 build_row(...) call sites + 1 classify_headers unpack pass with new signatures | unit | `cd quizify-csv-to-json-webhook && python3 -m pytest -q` | ✅ (after mechanical update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are placeholders pending planner output; the verification map will be re-keyed by the planner against actual plan IDs.*

---

## Wave 0 Requirements

- [x] CSV working-copy reverted to committed state; baseline `71 passed in 1.10s` confirmed (Pitfall E resolved before chain resumed)
- [ ] `quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json` — golden fixture for TRAIL-03 regression (Pitfall G)
- [ ] `quizify-csv-to-json-webhook/tests/conftest.py` — add `scoring_index_map_default = {"Result logic": 0, "Score category": 1, "Score value": 2}` fixture (D-05-06)
- [ ] `quizify-csv-to-json-webhook/tests/test_layout.py::TestScoringIndexMap` — new test class: default-order map, scrambled-order map, NFC+casefold (case+diacritic) match, missing-column listing, strict positional check still raises LayoutError when lengths don't align
- [ ] `quizify-csv-to-json-webhook/tests/test_row_builder.py::TestScrambledTrailer` — pass reversed map `{"Result logic": 2, "Score category": 1, "Score value": 0}` and assert each row field maps to the named-cell value, NOT the positional [0/1/2] cell
- [ ] `quizify-csv-to-json-webhook/tests/test_row_builder.py::TestMissingColumnWarning` — caplog tests for D-05-08 locked message text, missing-column → `""`, PII safety
- [ ] `quizify-csv-to-json-webhook/tests/test_default_order_regression.py` — TRAIL-03 structural identity vs golden fixture
- [ ] All 14 `build_row(...)` call sites in `test_row_builder.py` — append `scoring_index_map_default` fixture arg (mechanical churn; one-line per call)
- [ ] `quizify-csv-to-json-webhook/tests/test_layout.py:27` — extend 3-tuple unpack of `classify_headers` return to 5-tuple
- [ ] `quizify-csv-to-json-webhook/quizify_csv_ingest.py:286` (`dry_run`) — extend 3-tuple unpack to 5-tuple

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README content updates (Pitfall F: lines ~62–69 "Note:" block + ~129–132 Limitations bullet stating `--trailer-columns` reorderings "remain positional"/"misalign scoring fields silently") | TRAIL-03 docs | README content semantics; D-11 drift test only checks flag-name coverage | Read updated README sections; confirm wording reflects name-based binding and TRAIL-02 missing-column warning behavior |
| MILESTONES.md (or equivalent v1.1 milestone-notes file) entry: TRAIL-03 user-facing behavior change for non-default `--trailer-columns` callers | TRAIL-03 docs | Operator-facing release-note prose | Read entry under v1.1; confirm bugfix is described in operator terms (not implementation terms) |
| No `or trailer_cells_decoded[N]` (or any positional fallback) in production code post-Phase-5 (Pitfall 10) | TRAIL-01/02 | Negative-existence check; not an automated test | `grep -nE "trailer_cells_decoded\[[0-2]\]" quizify-csv-to-json-webhook/quizify_csv_ingest.py` — every match must be inside a `scoring_index_map[...]` lookup, never a fallback or default expression |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (golden fixture, fixture additions, new test classes, signature-update churn)
- [ ] No watch-mode flags (single-shot pytest only)
- [ ] Feedback latency < 2.5s (Pitfall 16 budget)
- [ ] `nyquist_compliant: true` set in frontmatter (after planner re-keys task IDs against actual plans)

**Approval:** pending
