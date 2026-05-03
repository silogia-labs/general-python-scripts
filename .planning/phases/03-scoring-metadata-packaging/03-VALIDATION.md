---
phase: 3
slug: scoring-metadata-packaging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already pinned in `quizify-csv-to-json-webhook/requirements-dev.txt`) |
| **Config file** | `quizify-csv-to-json-webhook/pytest.ini` (sets `pythonpath = .`) |
| **Quick run command** | `cd quizify-csv-to-json-webhook && pytest -q tests/test_row_builder.py tests/test_quiz_title_precedence.py tests/test_readme_help_alignment.py` |
| **Full suite command** | `cd quizify-csv-to-json-webhook && pytest -q` |
| **Estimated runtime** | ~1.0 seconds (Phase 2: 49 tests in <0.5s; Phase 3 adds ~15-20 tests) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (~0.4s)
- **After every plan wave:** Run full suite command (~1.0s)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | WEB-04, WEB-05 | — | N/A (test scaffolding) | unit/golden | `pytest -q tests/test_row_builder.py tests/test_quiz_title_precedence.py` | ❌ W0 (extend + new) | ⬜ pending |
| 03-01-02 | 01 | 1 | WEB-04 | — | Empty scoring → `""`; no silent data loss | unit | `pytest tests/test_row_builder.py::test_scoring_pass_through tests/test_row_builder.py::test_empty_scoring_emits_empty_strings` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | WEB-04 | — | 4 reserved placeholders match locked defaults | golden + invariant | `pytest tests/test_golden_structure.py::test_reserved_placeholders_match_defaults tests/test_structural_invariants.py::test_every_row_has_reserved_placeholders` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | WEB-04 | — | Per-row dict key order matches D-05 | golden + invariant | `pytest tests/test_golden_structure.py::test_key_order_locked tests/test_structural_invariants.py::test_key_order_locked` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 2 | WEB-05 | T-V5-01 | CLI > env > default precedence | subprocess | `pytest tests/test_quiz_title_precedence.py` | ❌ W0 (NEW) | ⬜ pending |
| 03-01-06 | 01 | 2 | WEB-05 | — | `html.unescape` applied; whitespace preserved | unit | `pytest tests/test_quiz_title_precedence.py::test_resolve_quiz_title_html_unescape_applied tests/test_quiz_title_precedence.py::test_resolve_quiz_title_whitespace_preserved` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 3 | OPS-01 | T-V8-01 | README documents privacy posture, missing IDs, exit codes | manual review + smoke | `pytest tests/test_readme_help_alignment.py::test_readme_has_all_required_sections` | ❌ W0 (NEW) | ⬜ pending |
| 03-02-02 | 02 | 3 | OPS-01 | — | README CLI flag list matches `--help` output | smoke | `pytest tests/test_readme_help_alignment.py::test_every_flag_named_in_readme` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `quizify-csv-to-json-webhook/tests/test_quiz_title_precedence.py` — NEW: subprocess + unit tests for WEB-05 (CLI > env > default, decode, whitespace)
- [ ] `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` — NEW: README drift smoke test (sections present, flags named) for OPS-01
- [ ] Extend `quizify-csv-to-json-webhook/tests/test_row_builder.py` — add 3 tests: scoring pass-through, empty-scoring `""`, `quiz_title` threading through `build_row`
- [ ] Extend `quizify-csv-to-json-webhook/tests/test_golden_structure.py` — drop `PHASE_3_KEYS` strip filter; add positional-order test; add scoring + placeholder + `quiz_title` assertions; update `_build_aligned_csv` / `run_aligned` to populate scoring trailer cells and pass `--quiz-title "Autoevaluacion"`
- [ ] Extend `quizify-csv-to-json-webhook/tests/test_structural_invariants.py` — invert `PHASE_3_KEYS` from "must NOT leak" to "must be present"; add 6 invariant tests (quiz_title, scoring trio, placeholders, key order, default-empty)
- [ ] Framework install: none — `pytest` already available via `requirements-dev.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README content quality (clarity, accuracy of column-assumption prose, privacy phrasing) | OPS-01 | Cannot fully automate prose quality; smoke test only verifies sections + flag names exist | Reviewer reads `quizify-csv-to-json-webhook/README.md` end-to-end and confirms (a) Quickstart command runs cleanly against `docs/quizify-submissions.csv`, (b) Configuration table accurately reflects precedence, (c) Limitations section calls out missing IDs, comma-in-cell heuristic, and reserved placeholder keys, (d) Privacy Notes section matches Phase 2 stderr-warning posture |
| Visual diff of golden-file output vs `docs/webhook-quizify-format-example.json` | WEB-04 | Structural diff (test_golden_structure.py) catches key ordering / shape; visual diff catches "feels wrong" issues | After plan execution, run `python quizify_csv_ingest.py docs/quizify-submissions.csv --quiz-title "Autoevaluacion" -o /tmp/out.json` and `diff <(jq -S . /tmp/out.json) <(jq -S . docs/webhook-quizify-format-example.json)` to spot-check that real differences are only `id`-absent (D-07) and `product-recommendation` value (D-02 emits `null` vs example's `"Basic"`) |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
