---
phase: 06-json-schema-validation
plan: 04
subsystem: docs
tags: [docs, readme, decision-log, d-11, vali-06]
requires:
  - 06-01 (schema artifact at docs/webhook-schema.json)
  - 06-02 (pyproject.toml [validate] extra)
  - 06-03 (--validate flag wired into argparse)
provides:
  - VALI-06: operator-facing documentation for --validate (CLI table row, optional install block, inline schema reference)
  - PROJECT.md decision-log entry confirming VALI-01 ship + D-13 carry-forward
affects:
  - quizify-csv-to-json-webhook/README.md
  - .planning/PROJECT.md
tech-stack:
  added: []
  patterns:
    - D-11 README structure lock (10 H2 sections, in fixed order) — preserved
    - D-06-23 verbatim language for the --validate CLI table row
    - Pitfall 24 install spelling: pip install '.[validate]' (singular, lowercase, dot-bracket)
key-files:
  created: []
  modified:
    - quizify-csv-to-json-webhook/README.md
    - .planning/PROJECT.md
decisions:
  - VALI-01 ship recorded in PROJECT.md Key Decisions table (2026-05-04)
  - D-13 stdlib-only-at-runtime carry-forward confirmed in the new row
  - Zero new H2 sections added to README (D-11 drift test remains green)
metrics:
  duration: ~6 min
  completed: 2026-05-04
  tasks: 2
  commits: 2
---

# Phase 6 Plan 4: Operator Docs for --validate (VALI-06) Summary

Land the operator-facing documentation for the `--validate` flag without violating the D-11 README structure lock. README's `## CLI reference` table now carries a `--validate` row, `## Quickstart` carries an optional `pip install '.[validate]'` block plus an inline reference to `docs/webhook-schema.json`, and `.planning/PROJECT.md` Key Decisions records the v1.1 VALI-01 ship with explicit D-13 stdlib-only-at-runtime preservation. The previously-RED `tests/test_readme_help_alignment.py::test_every_flag_named_in_readme` is now green; the full 94-test suite passes in 1.34s.

## Tasks Completed

| Task | Name                                                                                       | Commit  | Files                                       |
| ---- | ------------------------------------------------------------------------------------------ | ------- | ------------------------------------------- |
| 1    | Extend README.md (D-06-23 — CLI table row + Quickstart install line + inline schema ref)   | 78c7230 | quizify-csv-to-json-webhook/README.md       |
| 2    | Append v1.1 Phase 6 row to PROJECT.md Key Decisions table                                  | 4a285dc | .planning/PROJECT.md                        |

## Verification

- `cd quizify-csv-to-json-webhook && pytest -q tests/test_readme_help_alignment.py` → `2 passed in 0.04s` (D-11 drift test green; previously failing `test_every_flag_named_in_readme` now green).
- `cd quizify-csv-to-json-webhook && pytest -q` → `94 passed in 1.34s` (no regressions).
- `grep -cE '^## ' quizify-csv-to-json-webhook/README.md` → `10` (D-11 H2 lock preserved).
- `grep -cE '^\| \`--validate\` \|' quizify-csv-to-json-webhook/README.md` → `1` (CLI table row present).
- `grep -c "pip install '\.\[validate\]'" quizify-csv-to-json-webhook/README.md` → `1` (Pitfall 24 spelling).
- `grep -c 'docs/webhook-schema.json' quizify-csv-to-json-webhook/README.md` → `3` (CLI table cell + Quickstart formal-contract reference + Quickstart optional-install paragraph; spec required ≥2).
- `grep -c 'VALI-01' .planning/PROJECT.md` → `4` (existing v1.1 entry at line 99 + new ship row at line 102 each mention VALI-01 multiple times; spec required ≥2).
- `grep -ci 'stdlib-only' .planning/PROJECT.md` → `5` (D-13 carry-forward language preserved + reinforced by new row).

## Acceptance Criteria

- [x] README's `## CLI reference` table contains a `--validate` row (default `off`; description names `docs/webhook-schema.json` and the `[validate]` extra; env var `—`).
- [x] README's `## Quickstart` section contains an OPTIONAL second install line `pip install '.[validate]'`.
- [x] README's existing 10 H2 sections are unchanged in count and order — D-11 drift test stays green WITHOUT test edits.
- [x] README inline-references `docs/webhook-schema.json` near the existing `docs/webhook-quizify-format-example.json` reference.
- [x] PROJECT.md Key Decisions table records the v1.1 VALI-01 ship and confirms D-13 stdlib-only-at-runtime preservation.
- [x] `pytest -q tests/test_readme_help_alignment.py` exits 0 (including `test_every_flag_named_in_readme`).
- [x] Full 94-test suite remains green.
- [x] Each task committed atomically.

## Deviations from Plan

None — plan executed exactly as written. Three surgical edits to README.md (CLI table row append, Quickstart inline schema reference + optional install block) and a single row append to PROJECT.md. Note: the plan suggested making three separate Edit calls for the README, but Edits 2 and 3 share an adjacent text region in Quickstart, so they were combined into a single Edit op against the unique three-line "target shape" sentence; the resulting diff matches the plan's intent verbatim and the per-edit acceptance criteria all pass.

## Threat Surface Scan

No new threat surface introduced. README and PROJECT.md changes are descriptive only — no new endpoints, auth paths, file-access patterns, or schema changes. T-DOC-DRIFT-01 (the only mitigate disposition in the plan's threat register) is satisfied: the D-11 drift test, which was RED at plan start, is now GREEN, locking the README ↔ argparse contract.

## Self-Check

Verifying claims:

- README.md edits present and correct: `grep -cE '^\| \`--validate\` \|' README.md` → 1 (FOUND).
- PROJECT.md row appended: `grep -c '2026-05-04' .planning/PROJECT.md` → 1 (FOUND).
- Commits exist: `git log --oneline | grep -E '78c7230|4a285dc'` → 2 hits (FOUND).
- Drift test green: pytest -q tests/test_readme_help_alignment.py → 2 passed (FOUND).
- Full suite green: pytest -q → 94 passed (FOUND).

## Self-Check: PASSED
