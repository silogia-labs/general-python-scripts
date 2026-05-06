---
phase: 10-make-com-hygiene-node-test-harness
plan: 01
subsystem: make-scripts
tags: [node-test, make-scripts, tdd-red]
gate: RED
requirements:
  - MAKE-TEST-01
  - MAKE-TEST-02
  - MAKE-TEST-03
  - MAKE-COSMETIC-01
  - MAKE-COSMETIC-02
provides:
  - "mapRecord(record) export on both Make.com IIFE modules"
  - "node:test harness with 6 test files + 11 synthetic fixtures"
  - "pytest norecursedirs guard + 5 Python grep gates (deps, private, use-strict, PII)"
requires:
  - "Phase 9 baseline make-scripts/CONVENTIONS.md (CONTRACT-01, MAKE-FIX-01/02 contracts)"
affects:
  - quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
  - quizify-csv-to-json-webhook/make-scripts/score-calculations.js
  - quizify-csv-to-json-webhook/pyproject.toml
tech-stack:
  added:
    - "node:test (Node ≥18 stdlib — zero npm deps)"
    - "node:assert/strict"
  patterns:
    - "Dual-export footer: typeof input guard + module.exports (D-10-02)"
    - "Module-private helpers, single mapRecord export (D-10-04)"
    - "Reflect.ownKeys(globalThis) snapshot diff for global-leak gate (D-10-13)"
key-files:
  created:
    - quizify-csv-to-json-webhook/make-scripts/package.json
    - quizify-csv-to-json-webhook/make-scripts/.gitignore
    - quizify-csv-to-json-webhook/make-scripts/tests/contract-01.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/make-fix-01.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/make-fix-02.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/cosmetic-01.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/cosmetic-02.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/globals.test.js
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/quizify-mapping/happy-path.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/quizify-mapping/peri-meno-row.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/happy-path-low-score.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/red-flags-row.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/severo-row.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/moderado-row.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/activity-non-athlete.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/activity-athlete.json
    - quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/work-remoto.json
    - quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py
    - quizify-csv-to-json-webhook/tests/test_make_scripts_no_pii.py
  modified:
    - quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
    - quizify-csv-to-json-webhook/make-scripts/score-calculations.js
    - quizify-csv-to-json-webhook/pyproject.toml
decisions:
  - "Cosmetic-02 passes naturally in RED plan (out.profile is always reassigned by if/else; profile_base is dead init only). Plan 10-02 will remove the dead init for cleanliness — its RED-before-GREEN evidence is the source-level grep gate, not the test."
metrics:
  duration: "~25 min"
  tasks_completed: 3
  files_created: 19
  files_modified: 3
  completed: 2026-05-05
---

# Phase 10 Plan 01: RED scaffolding — node:test harness + mapRecord wrap Summary

One-liner: Wrap both Make.com IIFE modules in `mapRecord(record)` + dual-export footer, ship the full `node --test` harness with synthetic fixtures, and add pytest grep gates — leaving the `Reomoto` typo and `profile_base` dead init in source for Plan 10-02 to flip GREEN.

## What Was Built

1. **mapRecord wrap (Task 1)** — Both `quizify-mapping.js` and `score-calculations.js` now expose `mapRecord(record)`. The dual-export footer (`if (typeof input !== "undefined") { output = mapRecord(...); }` + `if (typeof module !== "undefined") { module.exports = { mapRecord }; }`) keeps Make.com paste-in functional while enabling `require()` from Node tests. `"use strict";` is the first non-comment line in both modules.

2. **Test harness + fixtures (Task 2)** — `make-scripts/package.json` (private, zero deps, `node --test` script), `.gitignore` (node_modules/, coverage/), 11 synthetic fixtures across two trees, and 6 test files with inline citation comments per D-10-09.

3. **Pytest gates (Task 3)** — `[tool.pytest.ini_options]` with `norecursedirs = ["make-scripts", "node_modules"]`, plus `test_make_scripts_no_deps.py` (4 tests: zero runtime deps, zero dev deps, private flag, use-strict directive) and `test_make_scripts_no_pii.py` (1 test: forbidden-token sweep).

## Verification Results

- `cd quizify-csv-to-json-webhook/make-scripts && node --test` → 9 tests, **7 pass / 2 fail** (both failures are cosmetic-01: positive `'Remoto'` assertion + negative-regression sweep — both diagnose `'Reomoto'` typo at score-calculations.js:157).
- `cd quizify-csv-to-json-webhook && pytest -q` → **163 passed, 4 skipped** (158 baseline + 4 from `test_make_scripts_no_deps.py` + 1 from `test_make_scripts_no_pii.py`).
- `pytest --collect-only -q | grep -c '\.test\.js'` → **0** (`norecursedirs` honored).
- `grep -RE 'Karen|Retamal|Javielys|Mancilla' make-scripts/tests/fixtures/` → **no matches** (T-PII-01 satisfied).
- `grep -v '^[[:space:]]*//' make-scripts/score-calculations.js | grep -cE '"Reomoto"|"profile_base"'` → **2** (RED gate intact for Plan 10-02).
- D-11 README ten-section drift test (`test_readme_help_alignment.py`) → **2/2 green** (untouched).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guard `Array.isArray` in `process_multi_select_tag`**
- **Found during:** Task 1 (during refactor verification).
- **Issue:** The original `process_multi_select_tag(answer_array, ...)` calls `.length` on `answer_array` directly. Under Make.com the field is always populated by the question loop, but synthetic fixtures may omit those keys → `undefined.length` throws under strict mode.
- **Fix:** Added `Array.isArray(answer_array) && ...` guard before `.length` access in `quizify-mapping.js`.
- **Why correctness:** Required for the module to be `require()`-able with arbitrary synthetic fixtures (precondition for the test harness — D-10-01).
- **Commit:** d49f89a

**2. [Rule 1 - Bug] Guard null email before `.toLowerCase()`**
- **Found during:** Task 1.
- **Issue:** Original code does `output.email.toLowerCase().includes(...)` — if `output.email` is `null` (no email key in input), TypeError under strict mode.
- **Fix:** Wrapped in `output.email && (...)` guard.
- **Commit:** d49f89a

### Plan inconsistency observation (NOT a deviation — preserved per D-10-10)

**Cosmetic-02 passes naturally in RED plan.** The plan expected `cosmetic-02.test.js` to fail in this RED plan, but the dead initializer `let profile = "profile_base";` at line 217 has no runtime effect — every code path through the if/else block reassigns `profile` to one of `red_flags`/`high_complexity`/`moderate_complexity`/`low_complexity`. So `out.profile === "profile_base"` is unreachable, and `JSON.stringify(out).includes("profile_base")` is false. The test passes. RED-before-GREEN evidence for MAKE-COSMETIC-02 is therefore preserved at the **source-grep level** (the literal `"profile_base"` string is still in `score-calculations.js`), not at the assertion level. Plan 10-02 will remove the dead initializer as cleanliness; the cosmetic-02 test continues to assert the contract going forward.

The plan-level `<verify>` block (`test "$FAIL" -ge 1 || exit 1`) is satisfied by cosmetic-01's two failures.

## Threat Flags

None.

## Self-Check: PASSED

- FOUND: quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js (modified)
- FOUND: quizify-csv-to-json-webhook/make-scripts/score-calculations.js (modified)
- FOUND: quizify-csv-to-json-webhook/make-scripts/package.json
- FOUND: quizify-csv-to-json-webhook/make-scripts/.gitignore
- FOUND: all 6 test files + 9 fixtures + 2 Python tests
- FOUND: commit d49f89a (refactor — Task 1)
- FOUND: commit 79d9d8e (test harness — Task 2)
- FOUND: commit a04f2d9 (pytest gates — Task 3)

## TDD Gate Compliance

This plan is the RED gate for Plan 10-02 (cosmetic GREEN flip). The `test(10-01): add node:test harness ...` commit (79d9d8e) lands the failing tests; cosmetic-01 fails on the preserved typo. Plan 10-02 will land the corresponding `feat`/`fix` GREEN commit.
