---
phase: 05-python-trailer-hardening
plan: 02
subsystem: quizify-csv-to-json-webhook
tags: [python, tdd, trailer-hardening, classify-headers, build-row, caplog, name-based-lookup, TRAIL-01, TRAIL-02]
requires:
  - "Plan 01 (scoring_index_map_default conftest fixture; v1.0 golden output)"
provides:
  - "5-tuple classify_headers (prefix, dynamic, trailer_raw, scoring_index_map, missing_trio_names)"
  - "build_row(scoring_index_map=...) name-keyed scoring trio binding"
  - "convert() PII-safe WARNING per missing canonical trio column (D-05-08 locked template)"
  - "_OUTPUT_KEY_BY_CANONICAL module-level constant"
affects:
  - "Plan 03 (TRAIL-03 regression) — production now matches v1.0 default-order golden fixture"
  - "Plan 03 (docs) — README + MILESTONES updates pending; D-15 may now be retired in PROJECT.md"
tech-stack:
  added: []
  patterns:
    - "NFC+casefold name-keyed lookup (D-05-03 / Pitfall 9 / Pitfall 11)"
    - "%r-formatted PII-safe logging.warning (D-05-08 / T-PII-01)"
    - "5-tuple atomic signature change with synchronized call-site updates"
    - "TDD RED → GREEN (failing tests committed before production change)"
key-files:
  created: []
  modified:
    - quizify-csv-to-json-webhook/quizify_csv_ingest.py
    - quizify-csv-to-json-webhook/tests/test_layout.py
    - quizify-csv-to-json-webhook/tests/test_row_builder.py
decisions:
  - "Used 6-column custom_trailer in TestMissingColumnWarning::test_warning_message_matches_locked_template and ::test_warning_pii_safe (replaced 'Result logic' with 'Notes' placeholder rather than dropping a column) — necessary because build_row still hard-codes trailer_cells_decoded[3] (Answer tags) and [5] (Date) per D-05-05; a 5-column trailer would IndexError on those positional reads. Plan 02's TRAIL-01 scope only covers the trio (indices 0/1/2)."
  - "Inlined the D-05-08 warning string onto a single source line (as opposed to two adjacent string literals) so the phase-level grep gate `grep -c 'absent from CSV header; emitting empty string for'` matches with count == 1."
  - "Removed the literal substring `or trailer_cells_decoded[N]` from the explanatory comment in build_row to keep `grep -cE 'or +trailer_cells_decoded\\['` at exactly 0 (Pitfall 10 grep gate)."
metrics:
  tasks_completed: 2
  duration_minutes: ~12
  completed_date: 2026-05-03
  red_commit: d08b975
  green_commit: 7910ca7
  test_count_baseline: 71
  test_count_after: 80
  test_count_delta: +9
  pytest_runtime_seconds: 1.04
  pytest_runtime_budget_seconds: 2.5
requirements: [TRAIL-01, TRAIL-02]
---

# Phase 05 Plan 02: Name-Based Scoring Trio Binding (TRAIL-01 + TRAIL-02) Summary

Atomic TDD-driven replacement of positional `trailer_cells_decoded[0..2]` indexing with NFC+casefold name-keyed lookup driven by a `scoring_index_map: dict[str, int]` built once in `classify_headers`; `convert()` now emits exactly one PII-safe WARNING per missing canonical trio column using the locked D-05-08 template, with NO positional fallback (D-05-10 / Pitfall 10).

## Tasks Completed

| Task | Name                                                    | Commit  | Files                                                                                                |
| ---- | ------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| 1    | RED — failing tests for TRAIL-01 / TRAIL-02             | d08b975 | tests/test_layout.py (TestScoringIndexMap + 5-tuple unpack at existing call site), tests/test_row_builder.py (TestScrambledTrailer, TestMissingColumnWarning, `import logging`) |
| 2    | GREEN — production change makes all 80 tests pass        | 7910ca7 | quizify_csv_ingest.py (5 surgical edits: `_OUTPUT_KEY_BY_CANONICAL`, classify_headers 5-tuple, dry_run unpack, convert warning loop + build_row call, build_row signature + name-keyed reads), tests/test_row_builder.py (14 build_row call sites + adjusted custom_trailer in caplog tests) |

Wave 0 dependency commits (cherry-picked from main into the worktree branch since the branch was created before main absorbed Plan 01):

| Wave 0 | Name                                                  | Commit  | Files                                                                  |
| ------ | ----------------------------------------------------- | ------- | ---------------------------------------------------------------------- |
| 01-T1  | Generate v1.0 default-order golden output fixture     | 4778c76 | quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json |
| 01-T2  | Add scoring_index_map_default conftest fixture        | 198ad10 | quizify-csv-to-json-webhook/tests/conftest.py                          |

## Verification

### TDD Gate Compliance

- RED gate: `test(05-02)` commit `d08b975` exists; at the time of that commit, 9 new tests fail (5 in TestScoringIndexMap, 1 in test_sample_csv_header_classification's extended unpack, 1 in TestScrambledTrailer, 3 in TestMissingColumnWarning); 71 baseline tests still pass.
- GREEN gate: `feat(05-02)` commit `7910ca7` follows; all 80 tests pass.
- REFACTOR: not needed; both gates clean.

### Phase 5 critical gates (all PASS)

| Gate                                                                                       | Expected | Observed |
| ------------------------------------------------------------------------------------------ | -------- | -------- |
| `grep -cE "or +trailer_cells_decoded\\[" quizify_csv_ingest.py`                            | 0        | 0        |
| `grep -cE "trailer_cells_decoded\\[[0-2]\\]" quizify_csv_ingest.py`                        | 0        | 0        |
| `grep -c "absent from CSV header; emitting empty string for" quizify_csv_ingest.py`        | 1        | 1        |
| `grep -c "_norm_for_match(canonical)\\|_norm_for_match(h)" quizify_csv_ingest.py`          | >= 2     | 3        |
| `grep -c "scoring_index_map: dict\\[str, int\\]" quizify_csv_ingest.py`                    | >= 1     | 2        |
| `grep -c "_OUTPUT_KEY_BY_CANONICAL" quizify_csv_ingest.py`                                 | >= 2     | 2        |
| `grep -c "for name in missing_trio_names" quizify_csv_ingest.py`                           | == 1     | 1        |
| `grep -c "_prefix, dynamic, _trailer_h, _scoring_map, _missing" quizify_csv_ingest.py`     | >= 1     | 1        |
| `grep -c "scoring_index_map=scoring_index_map_default" tests/test_row_builder.py`          | >= 14    | 14       |

### Test results

- `cd quizify-csv-to-json-webhook && python3 -m pytest -q` → `80 passed in 1.04s` (under 2.5s Pitfall 16 budget).
- `tests/test_layout.py::TestScoringIndexMap` (5 tests) — all pass; `test_sample_csv_header_classification` extended 5-tuple unpack passes.
- `tests/test_row_builder.py::TestScrambledTrailer` (1 test) — passes (reversed map proves name-keyed binding, not positional).
- `tests/test_row_builder.py::TestMissingColumnWarning` (3 tests) — pass (locked D-05-08 template + PII safety + empty-string emit).
- `tests/test_row_builder.py::test_empty_scoring_emits_empty_strings` — passes (D-03 / D-05-09 carry-forward: empty cell in present column stays silent).
- All 14 existing `build_row(...)` call sites updated to inject `scoring_index_map_default` fixture.

### caplog warning produced (sample)

```
WARNING root:quizify_csv_ingest.py:387 trailer column 'Result logic' absent from CSV header; emitting empty string for result-logic in all rows
```

`%r` produces single-quoted form (`'Result logic'`); message contains zero PII tokens (no `@`, no `+`, no email/phone/name from sample row).

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 - Blocking] Worktree branch lacked Wave 0 commits**

- Found during: pre-Task 1 setup (the conftest fixture `scoring_index_map_default` was missing from the worktree branch).
- Cause: this worktree branch was created from a main-tip predating the Plan 01 wave-0 commits `d43ab3b` and `d4d23c3`.
- Fix: cherry-picked the two Wave 0 commits onto the worktree branch (now appearing as `4778c76` and `198ad10` after rewrite). After cherry-pick, baseline `pytest -q` reports `71 passed in 1.11s` — confirming Wave 0 preconditions are present before Task 1 begins. No production code touched.
- Files modified by cherry-pick: `quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json` (new), `quizify-csv-to-json-webhook/tests/conftest.py` (appended fixture).

**2. [Rule 1 — Test-design adjustment] caplog tests originally used a 5-column custom_trailer; corrected to 6 columns to keep build_row's positional reads at indices 3 and 5 (out of TRAIL-01 scope per D-05-05)**

- Found during: first GREEN pytest run — both caplog tests crashed with `IndexError: list index out of range` at `trailer_cells_decoded[5]` (status_date) because the plan's example CSV row used a 5-column custom_trailer where Date sat at index 4.
- Cause: the plan's example CSV row in `<behavior>` showed a 5-column custom_trailer (`("Score category", "Score value", "Answer tags", "Time to complete (mm:ss)", "Date")`), but `build_row` still positionally reads `trailer_cells_decoded[3]` (Answer tags) and `[5]` (Date). The plan locks D-05-05: "Date and Answer tags positional reads stay; out of TRAIL-01 scope." So the test's custom_trailer must remain 6 columns.
- Fix: replaced the omitted "Result logic" with a placeholder column "Notes" at index 0 (rather than dropping the column entirely). Net effect: the trailer still has 6 columns; "Result logic" is genuinely absent from the trio (so `missing_trio_names == ("Result logic",)`); Answer tags is at index 3 and Date at index 5 — both untouched. The locked D-05-08 warning fires; `result-logic` emits `""`; the rest of the row builds correctly.
- Files modified: `tests/test_row_builder.py` (TestMissingColumnWarning::test_warning_message_matches_locked_template and ::test_warning_pii_safe — both use 6-col custom_trailer with "Notes" as the placeholder column 0).

**3. [Rule 1 — Lint avoidance] Reformatted comment in build_row to keep Pitfall 10 grep gate at zero**

- Found during: post-GREEN gate-check run — `grep -cE "or +trailer_cells_decoded\\[" quizify_csv_ingest.py` reported 1 because an explanatory comment ("NEVER fall back to a positional read (no \`or trailer_cells_decoded[N]\`)") contained the exact forbidden substring.
- Fix: rewrote the comment to convey the same intent ("NEVER add a positional fallback to indices 0/1/2 — the empty-string branch is the ONLY behavior on a missing canonical name") without using the literal phrase that the grep gate searches for. The semantic guidance for future maintainers is preserved.
- Files modified: `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (comment-only edit at lines 288-294 of the GREEN commit).

**4. [Rule 1 — Lint avoidance] Inlined the D-05-08 warning string onto a single source line**

- Found during: post-GREEN gate-check run — `grep -c "absent from CSV header; emitting empty string for" quizify_csv_ingest.py` reported 0 because the string was split across two adjacent string literals (`"trailer column %r absent from CSV header; "` + `"emitting empty string for %s in all rows"`).
- Cause: while Python concatenates adjacent string literals at compile time (the runtime message is identical), `grep` operates on raw source bytes and cannot bridge the line break.
- Fix: inlined the message onto one source line so the phase-level grep gate matches with count == 1. The runtime emitted log message is character-for-character identical to the dual-line form.
- Files modified: `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (convert() warning loop body).

### Asked-for-permission issues

None — all four deviations above are Rule 1 / Rule 3 (auto-fix blocking, no architectural change).

## Threat Surface Scan

Reviewed all files modified in this plan against the plan's `<threat_model>`. The four registered threats (T-05-02-01 substring-collision, T-05-02-02 positional-fallback regression, T-05-02-03 PII leakage in WARNING, T-05-02-05 normalization mismatch) are all mitigated as planned:

- T-05-02-01: only `==` equality on `_norm_for_match`-normalized strings is used (no `in`-substring); confirmed by reading the production loop body.
- T-05-02-02: grep gate `grep -cE "or +trailer_cells_decoded\\["` returns 0; `TestScrambledTrailer::test_scrambled_order_binds_correctly` would catch a regression at runtime.
- T-05-02-03: warning message uses `%r` on `name` (compile-time canonical from `DEFAULT_TRAILER[:3]`) and `%s` on `_OUTPUT_KEY_BY_CANONICAL[name]` (compile-time dict value). No row index, no cell content. `TestMissingColumnWarning::test_warning_pii_safe` asserts `@`, `+`, and PII tokens absent from the message — all green.
- T-05-02-05: `_norm_for_match` (NFC+casefold) is the ONLY normalizer used inside `classify_headers` for the trio match; confirmed by `grep -cE "_norm_for_match\\(canonical\\)|_norm_for_match\\(h\\)" → 3`.

No new security-relevant surface introduced beyond the registered threats. No `## Threat Flags` section needed.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: quizify-csv-to-json-webhook/quizify_csv_ingest.py (modified, 5-tuple classify_headers + name-keyed build_row + convert warning loop)
- FOUND: quizify-csv-to-json-webhook/tests/test_layout.py (modified, TestScoringIndexMap class + extended unpack)
- FOUND: quizify-csv-to-json-webhook/tests/test_row_builder.py (modified, 14 call sites updated + 2 new test classes)
- FOUND commit: d08b975 (RED) — `git log --oneline | grep d08b975` matches.
- FOUND commit: 7910ca7 (GREEN) — `git log --oneline | grep 7910ca7` matches.

## Next Steps

TRAIL-01 + TRAIL-02 implemented. Plan 03 may now run:
- TRAIL-03 regression test against the v1.0 golden fixture at `tests/fixtures/v1.0_default_order_output.json`.
- README + MILESTONES updates documenting the name-keyed binding and the PII-safe missing-column WARNING.
- D-15 retirement annotation in PROJECT.md decision-log.
