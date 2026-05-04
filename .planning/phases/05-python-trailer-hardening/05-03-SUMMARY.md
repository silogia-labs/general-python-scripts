---
phase: 05-python-trailer-hardening
plan: 03
subsystem: quizify-csv-to-json-webhook
tags: [python, regression, golden-fixture, docs, readme, milestones, trailer-hardening, TRAIL-03, pitfall-F]
requires:
  - "Plan 01 (v1.0_default_order_output.json golden fixture, scoring_index_map_default conftest fixture)"
  - "Plan 02 (5-tuple classify_headers + name-keyed build_row + convert() warning loop)"
provides:
  - "TRAIL-03 empirical regression: post-Phase-5 default-order CLI output structurally equal to v1.0 baseline"
  - "Operator-facing README documenting NFC+casefold name-based scoring trio binding"
  - "v1.1 milestone entry documenting TRAIL-03 user-facing bugfix and D-15 retirement"
  - "PROJECT.md Key Decisions D-15 row marked retired by TRAIL-01 (Phase 5, v1.1)"
affects:
  - "Phase 5 close: all four ROADMAP success criteria empirically verified"
  - "Phase 6 (schema validation) — operator docs no longer contradict Phase 5 reality"
tech-stack:
  added: []
  patterns:
    - "subprocess.run + json.loads structural equality against committed golden fixture"
    - "Pitfall F mitigation via verbatim-string deletion (not amend) of stale README caveats"
key-files:
  created:
    - quizify-csv-to-json-webhook/tests/test_default_order_regression.py
  modified:
    - quizify-csv-to-json-webhook/README.md
    - .planning/MILESTONES.md
    - .planning/PROJECT.md
decisions:
  - "Added a Current-Milestone v1.1 section to MILESTONES.md (it previously contained only the v1.0 entry) so the TRAIL-03 user-facing-bugfix note has a coherent home matching MILESTONES.md style. The plan's example placement assumed the v1.1 heading already existed at line 22; in practice MILESTONES.md only had v1.0, so the heading was created above the v1.0 entry. PROJECT.md already documents the v1.1 milestone scope, so this is a doc-style alignment, not a scope addition."
  - "Removed the v1.0 'Limitations' bullet about positional scoring/statusDate reads entirely (4 lines deleted) rather than rewriting it — the rewritten 'Trailer block' bullet in the Column Assumptions section already documents the post-Phase-5 behavior in the right place."
  - "Updated PROJECT.md D-15 Key-Decisions row in-place (kept original rationale prose, replaced the ⚠️ Revisit outcome with explicit 'Retired by TRAIL-01 (Phase 5, v1.1)' wording) rather than appending a new row, matching CONTEXT.md's 'D-15 retired with this phase; update PROJECT.md decisions log accordingly' carry-forward."
metrics:
  tasks_completed: 2
  duration_minutes: ~5
  completed_date: 2026-05-03
  task1_commit: 90ade92
  task2_commit: 70f08e7
  test_count_baseline: 80
  test_count_after: 81
  test_count_delta: +1
  pytest_runtime_seconds: 1.08
  pytest_runtime_budget_seconds: 2.5
requirements: [TRAIL-03]
---

# Phase 05 Plan 03: TRAIL-03 Regression Test + Operator Docs Summary

Closed Phase 5 by adding the TRAIL-03 default-order regression test (subprocess invocation + structural-equality compare against the v1.0 golden fixture captured in Plan 01), deleting the now-false "scoring stays positional / reorderings misalign silently" caveats from `README.md` (Pitfall F), and adding a v1.1 milestone entry to `MILESTONES.md` documenting TRAIL-03 as a user-facing bugfix with D-15 retired.

## Tasks Completed

| Task | Name                                                          | Commit  | Files                                                                                          |
| ---- | ------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------- |
| 1    | TRAIL-03 default-order regression vs v1.0 golden fixture      | 90ade92 | quizify-csv-to-json-webhook/tests/test_default_order_regression.py (new, 52 lines)             |
| 2    | TRAIL-01/02/03 README + MILESTONES updates (Pitfall F)        | 70f08e7 | quizify-csv-to-json-webhook/README.md, .planning/MILESTONES.md, .planning/PROJECT.md           |

## Verification

### Test results

- `cd quizify-csv-to-json-webhook && python3 -m pytest tests/test_default_order_regression.py -x` → `1 passed in 0.05s`.
- `cd quizify-csv-to-json-webhook && python3 -m pytest tests/test_readme_help_alignment.py -x` → `2 passed in 0.04s` (D-11 drift test unaffected by prose-only README edits — confirmed Phase 5 added no new CLI flags).
- `cd quizify-csv-to-json-webhook && python3 -m pytest -q` → `81 passed in 1.08s` (under the 2.5s Pitfall 16 budget). +1 over Plan 02's 80-test baseline.

### Phase 5 critical gates (all PASS)

| Gate                                                                                                  | Expected | Observed |
| ----------------------------------------------------------------------------------------------------- | -------- | -------- |
| `grep -ciE 'remain positional\|misalign scoring\|misalign those fields\|stays positional' README.md`  | 0        | 0        |
| `grep -ciE 'canonical column name\|name-based\|NFC' README.md`                                        | >= 1     | 1        |
| `grep -c 'result-logic' README.md`                                                                    | >= 1     | 3        |
| `grep -c 'Answer tags' README.md`                                                                     | >= 1     | 2        |
| `grep -c 'TRAIL-03' .planning/MILESTONES.md`                                                          | >= 1     | 2        |
| `grep -c 'D-15' .planning/MILESTONES.md`                                                              | >= 1     | 2        |
| `grep -ciE 'Phase 5\|TRAIL-01\|TRAIL-02\|trailer hardening' .planning/MILESTONES.md`                  | >= 1     | 3        |
| `grep -cE 'trailer_cells_decoded\[[0-2]\]' quizify_csv_ingest.py` (Pitfall 10 negative existence)     | 0        | 0        |
| `grep -cE 'or +trailer_cells_decoded\[' quizify_csv_ingest.py` (Pitfall 10 negative existence)        | 0        | 0        |
| `git diff --stat quizify_csv_ingest.py` (production untouched in Plan 03)                             | empty    | empty    |
| `git diff --stat tests/fixtures/v1.0_default_order_output.json` (golden untouched in Plan 03)         | empty    | empty    |

### README diff summary

- **Replaced** `quizify-csv-to-json-webhook/README.md` lines 62-69 (the "Trailer block" bullet, including the stale "Note: scoring keys and `statusDate` currently read trailer indices `0`, `1`, `2`, and `5`..." caveat) with a TRAIL-01-correct rewrite (8 prose lines about NFC + casefold name-based binding for the trio, positional reads still acknowledged for `Answer tags` index 3 and `Date` index 5, missing-trio-column behavior documented as "" + PII-safe stderr WARNING).
- **Deleted** `quizify-csv-to-json-webhook/README.md` lines 129-132 entirely (the v1.0 Limitations bullet asserting "scoring/`statusDate` reads remain positional" / "reorderings... will misalign those fields silently"). Both statements are FALSE post-Phase-5 (`statusDate` is still positional, but the trio is not — and the rewritten Trailer block bullet covers the right wording in the right section). The Limitations section now jumps from the empty-keys/string-typed bullet directly to the "Reserved placeholder keys" bullet.
- **Net change:** README.md: +8 lines, −13 lines (D-11 ten-section structure preserved; drift test green).

### MILESTONES.md edit summary

- **Added** a new top-level `## Current Milestone: v1.1 Contract Hardening & Make.com Alignment (in progress)` heading above the v1.0 MVP entry (the file previously contained only v1.0 content; PROJECT.md already documented the v1.1 milestone scope but MILESTONES.md hadn't been opened for v1.1 yet).
- **Added** a `### Phase 5: Python Trailer Hardening — TRAIL-01 / TRAIL-02 / TRAIL-03 (shipped)` subsection containing: (a) operator-facing description of the TRAIL-03 bugfix (non-default `--trailer-columns` callers no longer see silently mis-bound scoring fields), (b) the empirical proof point (regression test against v1.0 baseline), (c) missing-column behavior summary, and (d) explicit D-15 retirement note pointing back to PROJECT.md.

### PROJECT.md edit summary

- **Updated** the D-15 row in the Key Decisions table: the rationale prose is preserved verbatim ("Matches D-15 verbatim; avoids extra config surface"), the outcome column was rewritten from "⚠️ Revisit — silent mis-binding risk if `--trailer-columns` is passed in non-default order; add name-based lookup in v1.x if a real export needs it" to "Retired by TRAIL-01 (Phase 5, v1.1) — replaced with NFC+casefold name-based binding; default-order callers see no behavioral change (verified by `tests/test_default_order_regression.py`)". This is the carry-forward action specified in `05-CONTEXT.md` line 61.

## Phase 5 ROADMAP success criteria — empirical verification status

| SC | Description                                                          | Verifier                                                                       | Status |
| -- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------ |
| 1  | TRAIL-03: default-order callers see no behavioral change             | `tests/test_default_order_regression.py::test_default_order_byte_identical_to_v1_0_baseline` | ✓ PASS |
| 2  | TRAIL-01: scrambled-order `--trailer-columns` binds scoring correctly | `tests/test_row_builder.py::TestScrambledTrailer` (Plan 02)                    | ✓ PASS |
| 3  | TRAIL-02: missing trio column emits "" + PII-safe WARNING            | `tests/test_row_builder.py::TestMissingColumnWarning` (Plan 02)                | ✓ PASS |
| 4  | 71-test baseline + new tests all green                               | `pytest -q` → 81 passed in 1.08s                                               | ✓ PASS |

All four ROADMAP Phase 5 success criteria empirically verified by automated tests.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 — Missing critical doc surface] MILESTONES.md had no v1.1 heading at all**

- Found during: Task 2-B (the plan's locator anchor was "the v1.1 milestone section, around line 22 `## Current Milestone: v1.1 Contract Hardening & Make.com Alignment`").
- Issue: MILESTONES.md as committed contained only the v1.0 MVP entry; there was no v1.1 heading anywhere. PROJECT.md `## Current Milestone: v1.1 Contract Hardening & Make.com Alignment` documents v1.1 scope, but the corresponding MILESTONES.md section was never opened.
- Fix: created the `## Current Milestone: v1.1 Contract Hardening & Make.com Alignment (in progress)` heading above the v1.0 entry (most-recent-first, matching the file's existing time-order convention) and placed the Phase 5 subsection inside it. No content removed; v1.0 entry untouched.
- Why this is the correct call: the plan's `<action>` block explicitly notes "the exact placement is flexible (this section can live as a top-level subsection of the v1.1 milestone)". Creating the v1.1 heading is the natural extension of "live as a top-level subsection of the v1.1 milestone" when that subsection's container does not yet exist.

**2. [Rule 1 — Verifiable gate alignment] PROJECT.md D-15 row updated in-place rather than left untouched**

- Found during: Task 2 cross-check against `05-CONTEXT.md` §"Carry-forward (locked, not re-asked)" line 61: "D-15 (positional trailer indexing rationale) is retired with this phase; update PROJECT.md decisions log accordingly."
- Issue: the plan's task-list `<action>` block names two files (README.md, MILESTONES.md), but the phase context locks PROJECT.md as a third edit target. Without the PROJECT.md edit, the D-15 retirement note in MILESTONES.md ("The PROJECT.md Key Decisions table's D-15 row is updated to 'Retired by TRAIL-01 (Phase 5, v1.1)'") would be a forward-reference to an edit that was never made.
- Fix: updated the D-15 row outcome column in `PROJECT.md` Key Decisions table to "Retired by TRAIL-01 (Phase 5, v1.1) — replaced with NFC+casefold name-based binding; default-order callers see no behavioral change (verified by `tests/test_default_order_regression.py`)". Rationale prose preserved verbatim. No other PROJECT.md content touched.
- Why this is Rule 1 (auto-fix bug, not Rule 4 architectural): the carry-forward in CONTEXT.md mandates the PROJECT.md edit; omitting it would create a documented inconsistency between MILESTONES.md and PROJECT.md.

### Asked-for-permission issues

None — both deviations above are Rule 1 / Rule 2 (auto-fix non-architectural).

## Threat Surface Scan

Reviewed all files modified in this plan against the plan's `<threat_model>`. The three registered threats (T-05-03-01 operator-confusion via stale README caveat, T-05-03-02 golden-fixture tampering, T-05-03-03 PII in golden fixture — accept) are all mitigated as planned:

- T-05-03-01 (mitigate): Pitfall F grep gate `grep -ciE 'remain positional|misalign scoring|misalign those fields|stays positional' README.md` returns 0 — both stale claims (line 62-69 Note, line 129-132 Limitations bullet) are deleted, replaced with TRAIL-01-correct prose.
- T-05-03-02 (mitigate): `git diff --stat quizify-csv-to-json-webhook/tests/fixtures/v1.0_default_order_output.json` returns empty — golden file untouched in Plan 03. Regression test passes against the unmodified Wave 0 baseline.
- T-05-03-03 (accept): no new fixture content added; the v1.0 baseline file was committed in Wave 0 and is mirrored from `docs/quizify-submissions.csv`. No new PII surface introduced this plan.

No new security-relevant surface introduced beyond the registered threats. No `## Threat Flags` section needed.

## Known Stubs

None. The plan introduces no placeholder UI or empty-data flows; the regression test is fully wired to a real golden fixture and the README/MILESTONES prose describes shipped behavior.

## TDD Gate Compliance

Plan 03 is `type: execute` (not `type: tdd`); no RED/GREEN gate enforcement applies. The TRAIL-03 regression test in Task 1 functions as a verification harness for Plan 02's already-shipped GREEN production change rather than as a TDD RED step — it passed on first run because Plan 02 delivered correctly (which is exactly what TRAIL-03 is designed to confirm).

## Self-Check: PASSED

- FOUND: quizify-csv-to-json-webhook/tests/test_default_order_regression.py
- FOUND: quizify-csv-to-json-webhook/README.md (modified, stale caveats deleted, name-based binding documented)
- FOUND: .planning/MILESTONES.md (modified, v1.1 heading + Phase 5 subsection added)
- FOUND: .planning/PROJECT.md (modified, D-15 row outcome updated)
- FOUND commit: 90ade92 (Task 1 — `git log --oneline | grep 90ade92` matches)
- FOUND commit: 70f08e7 (Task 2 — `git log --oneline | grep 70f08e7` matches)

## Next Steps

Phase 5 complete — TRAIL-01, TRAIL-02, TRAIL-03 all shipped; ready for `/gsd-verify-work`.
