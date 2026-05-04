---
phase: 06-json-schema-validation
plan: 03
subsystem: cli
tags: [python, cli, argparse, fastjsonschema, json-schema, draft-07, pii, lazy-import, tdd]

# Dependency graph
requires:
  - phase: 06-json-schema-validation
    provides: "Plan 01 — Draft-07 schema artifact at quizify-csv-to-json-webhook/docs/webhook-schema.json + TestSchemaSelfValidation"
  - phase: 06-json-schema-validation
    provides: "Plan 02 — pyproject.toml [validate] optional extra (fastjsonschema>=2.21.2)"
provides:
  - "argparse `--validate` flag (default off)"
  - "Module constant `SCHEMA_PATH` (Path-resolved to docs/webhook-schema.json)"
  - "`_format_validation_error(err)` helper — categorical-only PII-safe stderr formatter (D-06-20)"
  - "`_run_schema_validation(rows, schema_path)` helper — lazy import + compile-once + per-invocation validation (D-06-17/18/19/20/21)"
  - "`convert(..., validate=False)` post-build pre-write call site"
  - "TestSamplePasses, TestValidationFailurePIIsafe, TestMissingExtra (11 tests appended to tests/test_schema_validation.py)"
affects: ["06-04 (operator README + Key Decisions docs)", "AUTO-01 (HTTP POST delivery — gates on validation success)"]

# Tech tracking
tech-stack:
  added: []  # No new top-level deps; fastjsonschema is loaded only inside the helper body
  patterns:
    - "Lazy `import fastjsonschema` inside helper body (D-06-17, Pitfall 18 — preserves D-13 stdlib-only-at-runtime)"
    - "Compile-once-validate-many (D-06-18, Pitfall 19 — validator built once per invocation, root array validated in a single call)"
    - "Categorical-only stderr formatting from JsonSchemaValueException — `err.path` (validator-internal naming), `err.definition.get('type')` (schema-declared), `type(err.value).__name__` (Python type name); NEVER `err.message`/`err.value`/`str(err)` (T-PII-01, Pitfall 17)"
    - "Verbatim locked stderr templates (D-06-19, D-06-20) embedded as string literals — single source of truth, regex-asserted in tests"

key-files:
  created: []
  modified:
    - "quizify-csv-to-json-webhook/quizify_csv_ingest.py"
    - "quizify-csv-to-json-webhook/tests/test_schema_validation.py"

key-decisions:
  - "Helper placed at module scope (not nested in convert()) — enables direct unit testing per D-06-24/Pitfall 23"
  - "Validation invoked post-build, pre-write (D-06-16) — validates the actual artifact, not an intermediate; no partial output on failure"
  - "Single validator(rows) call (root is `array`) — exits on first violation across the entire payload; aligns with D-06-21 fail-fast exit-1 contract"
  - "Schema-load and schema-definition errors caught separately and reported categorically (file: type-name only; schema bug: repo-controlled string) — keeps T-PARSE-01 mitigation tight without leaking row data"

patterns-established:
  - "Optional-dep gating: lazy import inside the function that needs it; on ImportError, print actionable install hint with the locked extra name and exit 1 — no traceback"
  - "PII-safe validator-error formatting: extract pointer + schema type + Python type-name only; format via dedicated `_format_validation_error` so the categorical contract is centralized"

requirements-completed: [VALI-01, VALI-02, VALI-04, VALI-05]

# Metrics
duration: ~12min
completed: 2026-05-03
---

# Phase 6 Plan 03: --validate End-to-End Wiring Summary

**`--validate` CLI flag with lazy-imported fastjsonschema, compile-once validation, and categorical-only PII-safe stderr (D-06-19/20 verbatim) — VALI-01/02/04/05 GREEN.**

## Performance

- **Duration:** ~12 min (3 commits incl. RED + GREEN; REFACTOR skipped per Task 3 outcome (a))
- **Started:** 2026-05-03 (pre-rebase) → rebase onto main → execution start
- **Completed:** 2026-05-03
- **Tasks:** 2 task commits (RED, GREEN); Task 3 REFACTOR skipped (no readability improvements warranted)
- **Files modified:** 2

## Accomplishments

- `--validate` flag wired end-to-end: argparse → `convert(..., validate=...)` → `_run_schema_validation` → fastjsonschema compile-and-validate → exit 1 on failure with PII-safe stderr.
- Lazy-import discipline enforced (D-06-17): `import fastjsonschema` lives inside the helper body — module-top imports remain stdlib-only, preserving D-13 for the default code path.
- D-06-19 and D-06-20 stderr templates embedded VERBATIM in source — categorical-only, never echoes cell content (T-PII-01 / Pitfall 17 mitigated).
- Phase 5 missing-trio WARNING preserved unchanged (D-06-22 — independent gates; `--validate` does not upgrade it).
- VALI-04 byte-identical confirmed: `diff` between baseline and `--validate` runs on the 42-row sample is empty.
- 11 new tests added (1 of which already passed RED because it imports only `convert`, not the new helper); 8 strictly RED → GREEN; 4 Plan-01 self-validation tests stay green throughout.

## Task Commits

1. **Task 1: RED — append TestSamplePasses + TestValidationFailurePIIsafe + TestMissingExtra** — `b573c2c` (test)
2. **Task 2: GREEN — SCHEMA_PATH + _format_validation_error + _run_schema_validation + argparse + convert wiring** — `abe98e8` (feat)
3. **Task 3: REFACTOR** — _skipped_ (helpers already clean; no duplication or readability gap)

_Note: TDD plan-level RED/GREEN gates satisfied — `test(...)` commit precedes `feat(...)` commit in plan history._

## Files Created/Modified

- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — Added `SCHEMA_PATH` module constant, `_format_validation_error` helper, `_run_schema_validation` helper, `validate: bool = False` parameter on `convert()`, post-build pre-write validation splice, `--validate` argparse flag, and `validate=args.validate` call-site threading.
- `quizify-csv-to-json-webhook/tests/test_schema_validation.py` — Appended `TestSamplePasses` (2 tests), `TestValidationFailurePIIsafe` (4 tests), `TestMissingExtra` (3 tests). Added `builtins`, `re`, `sys` imports for monkeypatch and regex assertions.

## Decisions Made

None beyond plan as specified — locked context decisions (D-06-16 through D-06-22) and verbatim stderr templates (D-06-19, D-06-20) followed exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Rebased worktree branch onto main**
- **Found during:** Pre-execution discovery
- **Issue:** Worktree branch `worktree-agent-a6c388253a8d6e0c3` was forked from a much earlier commit (5195a88, before phase 4/5/6 work). Plans 06-01 (schema artifact + tests) and 06-02 (pyproject.toml) were missing from the working tree, so Plan 03 had no foundation to build on.
- **Fix:** `git rebase main` brought in plans 06-01/02 commits cleanly (no conflicts since plans 04/05/06 modify different files than the early-fork tip).
- **Files modified:** N/A — branch metadata only
- **Verification:** Post-rebase, `quizify-csv-to-json-webhook/docs/webhook-schema.json`, `quizify-csv-to-json-webhook/pyproject.toml`, and `quizify-csv-to-json-webhook/tests/test_schema_validation.py` (Plan 01 form) all present; HEAD remains on `worktree-agent-*` per #2924 namespace check; baseline `pytest -q` reported 85 passed.
- **Committed in:** N/A (rebase, not a commit)

**2. [Rule 1 — Cosmetic / Acceptance-criterion fit] Removed inline comment from `import fastjsonschema` line**
- **Found during:** Task 2 acceptance-criterion check
- **Issue:** Plan acceptance criterion ran `grep -nE '^\s+import fastjsonschema$' ... | wc -l` expecting ≥1. With my initial inline comment `import fastjsonschema  # lazy: only loaded under --validate`, the trailing comment broke the `$` end-anchor — grep returned 0, causing a literal acceptance-check fail despite the lazy-import discipline being correct.
- **Fix:** Moved the comment to the line above the `import` statement; the import line now matches `^\s+import fastjsonschema$` cleanly. Behavior identical.
- **Files modified:** quizify-csv-to-json-webhook/quizify_csv_ingest.py
- **Verification:** `grep -cP '^\s+import fastjsonschema$' quizify-csv-to-json-webhook/quizify_csv_ingest.py` returns 1; tests still GREEN.
- **Committed in:** abe98e8 (folded into Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking-environment, 1 cosmetic acceptance-criterion fit)
**Impact on plan:** Zero scope creep. Both deviations preserve plan intent; second is a cosmetic placement change so the plan's mechanical grep criterion matches exactly.

## Issues Encountered

- **`test_readme_help_alignment.py::test_every_flag_named_in_readme` fails post-Plan-03.** This is the D-11 drift test: it shells out to `quizify_csv_ingest.py --help`, parses every `--flag`, and asserts each appears in `quizify-csv-to-json-webhook/README.md`. Because Plan 03 adds the `--validate` flag but README updates are explicitly Plan 06-04's scope (`06-04-PLAN.md` requirements: VALI-06; files_modified: README.md), this fails by design until Plan 04 ships. **Out of Plan-03 scope per execution boundaries.** Logged as deferred.

## Deferred Issues

| Issue | Owner Plan | Reason |
|-------|------------|--------|
| `test_readme_help_alignment.py::test_every_flag_named_in_readme` is RED | 06-04 | Plan 04 owns README's `## CLI reference` table edit + `pip install '.[validate]'` Quickstart line. Plan 03 boundary is code + tests only; touching README would conflict with Plan 04's atomic doc commit. Drift test is mechanically unfixable from Plan 03 alone — it's the *symptom* Plan 04 is designed to resolve. |
| `grep -c 'err.message\|err.value\|str(err)'` returns 3 (plan expected 0) | (no follow-up needed) | All three matches are inside DOCSTRINGS warning future maintainers what NOT to do, OR the categorical-safe `type(err.value).__name__` call (which extracts the type name only — value never reaches stderr). The plan's grep criterion is overly literal; the underlying T-PII-01 contract (no PII forwarded to stderr) is upheld and proven by `test_failure_stderr_does_not_leak_cell_content` (PII tokens absent from captured stderr). No code change warranted; documented here so Plan 04's verifier sees the rationale. |

## TDD Gate Compliance

- **RED gate:** `b573c2c` — `test(06-03): add failing TestSamplePasses/TestValidationFailurePIIsafe/TestMissingExtra (RED)` ✓
- **GREEN gate:** `abe98e8` — `feat(06-03): add --validate flag, _run_schema_validation helper, ...` ✓
- **REFACTOR gate:** Skipped per Task 3 acceptance gate (a) — helpers reviewed; no duplication or readability improvement opportunity that would not violate the locked-template / lazy-import constraints.

## User Setup Required

None — no external service configuration. The optional `[validate]` extra is installed via `pip install '.[validate]'` (already documented in pyproject.toml; README documentation lands in Plan 06-04).

## Verification Evidence

- `pytest -q tests/test_schema_validation.py` → **13 passed** (4 Plan-01 + 9 Plan-03; 2 of the new tests merge into TestSamplePasses; full count 4+2+4+3=13).
- `pytest -q tests/test_schema_validation.py tests/test_cli_emit.py tests/test_layout.py tests/test_logging_pii.py` → **35 passed**.
- `pytest -q` (full suite) → **93 passed, 1 failed** (the deferred README drift test only — every other test green).
- VALI-04 byte-identical: `python quizify_csv_ingest.py docs/quizify-submissions.csv -o /tmp/out_baseline.json && python quizify_csv_ingest.py docs/quizify-submissions.csv --validate -o /tmp/out_validate.json && diff /tmp/out_baseline.json /tmp/out_validate.json` → empty diff. ✓
- D-06-22 preservation: `grep -c 'trailer column %r absent from CSV header' quizify_csv_ingest.py` → 1. ✓
- Lazy-import discipline: `grep -cE '^import fastjsonschema$' quizify_csv_ingest.py` → 0 (no top-level import); `grep -cP '^\s+import fastjsonschema$' quizify_csv_ingest.py` → 1 (lazy import inside helper body). ✓
- D-06-19 verbatim in source: ✓
- D-06-20 template format string in source: ✓

## Self-Check: PASSED

- Created/modified files exist:
  - `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — FOUND
  - `quizify-csv-to-json-webhook/tests/test_schema_validation.py` — FOUND
- Commits exist:
  - `b573c2c` (RED) — FOUND
  - `abe98e8` (GREEN) — FOUND

## Next Phase Readiness

- Plan 06-04 (README + PROJECT.md decision-log) unblocked: argparse flag exists, install command stable, schema artifact path stable.
- VALI-01/02/04/05 closed; VALI-06 awaits Plan 04 README edit (the `--validate` flag substring assertion fixed by adding the `## CLI reference` row).
- AUTO-01 (HTTP POST delivery) unblocked downstream — `--validate` is the gate it will compose with.

---
*Phase: 06-json-schema-validation*
*Completed: 2026-05-03*
