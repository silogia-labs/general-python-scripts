---
phase: 06-json-schema-validation
plan: 02
subsystem: packaging
tags: [python, packaging, pyproject, flit-core, optional-extra, pep621]

# Dependency graph
requires:
  - phase: 05-python-trailer-hardening
    provides: stable v1.0.x emit shape that the v1.1 packaging metadata wraps
provides:
  - "quizify-csv-to-json-webhook/pyproject.toml — minimal flit_core PEP 621 metadata"
  - "[project.optional-dependencies] validate = [\"fastjsonschema>=2.21.2\"] — opt-in install path"
  - "[tool.flit.module] name = \"quizify_csv_ingest\" — single-file module declaration"
affects: [06-03 (helper wiring + lazy import will rely on the [validate] extra), 06-04 (README install line documents `pip install '.[validate]'`)]

# Tech tracking
tech-stack:
  added: [flit_core (build backend declaration only — not a runtime dep), fastjsonschema (declared as optional extra; not installed by default)]
  patterns: [PEP 621 packaging with empty [project.dependencies] (D-13 stdlib-only-at-runtime preserved via the `validate` optional extra)]

key-files:
  created: [quizify-csv-to-json-webhook/pyproject.toml]
  modified: []

key-decisions:
  - "Followed locked D-06-01..D-06-05 verbatim — no discretionary deviation."
  - "Omitted [project.dependencies] entirely (Pitfall 20) so a future copy-paste cannot silently break D-13."
  - "Dropped [tool.ruff] / [tool.mypy] / authors blocks present in the sibling confluence-to-markdown/pyproject.toml — not introduced this phase."

patterns-established:
  - "Pattern 3 (flit_core single-module project): hyphenated project name `quizify-csv-to-json-webhook` decoupled from underscored module `quizify_csv_ingest` via [tool.flit.module] name."
  - "Optional-extras as the canonical opt-in dependency surface for this CLI — runtime keeps importing nothing beyond stdlib unless the operator explicitly opts in."

requirements-completed: [VALI-05]

# Metrics
duration: 1min
completed: 2026-05-04
---

# Phase 6 Plan 02: pyproject.toml + [validate] optional extra Summary

**Minimal flit_core PEP 621 packaging metadata for quizify-csv-to-json-webhook 1.1.0 with `validate = ["fastjsonschema>=2.21.2"]` as an opt-in extra; runtime stays stdlib-only (D-13).**

## Performance

- **Duration:** 1 min
- **Started:** 2026-05-04T05:03:39Z
- **Completed:** 2026-05-04T05:04:22Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `quizify-csv-to-json-webhook/pyproject.toml` with all six locked PEP 621 keys (D-06-01..D-06-05).
- Declared `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]` so `pip install '.[validate]'` resolves the schema validator.
- Declared `[tool.flit.module] name = "quizify_csv_ingest"` so flit packages the single-file module despite the hyphen↔underscore mismatch with the project name.
- Kept `[project.dependencies]` ABSENT (Pitfall 20) — D-13 stdlib-only-at-runtime preserved.
- 71-test suite remained green (1.11s) — zero regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author quizify-csv-to-json-webhook/pyproject.toml (D-06-01..D-06-05)** — `548f9aa` (feat)

_No plan-metadata commit yet — orchestrator owns STATE.md / ROADMAP.md and will produce the metadata commit downstream._

## Files Created/Modified
- `quizify-csv-to-json-webhook/pyproject.toml` — NEW; 17 lines; minimal flit_core PEP 621 metadata + `[validate]` optional extra; single trailing newline.

## Decisions Made
- None — plan executed exactly as specified. All six locked keys (D-06-01..D-06-05) present byte-for-byte. Discretionary fields (`description`, `license`) used the strings the plan suggested at the planner's discretion.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Verification Evidence

- **tomllib parse + 6 structural assertions:** `python3 -c "import tomllib; ..."` → `ok` (run from `quizify-csv-to-json-webhook/`).
- **Acceptance grep matrix (all values match plan expectations):**
  - `^name = "quizify-csv-to-json-webhook"` → 1
  - `^version = "1.1.0"` → 1
  - `^requires-python = ">=3.9"` → 1
  - `^validate = \["fastjsonschema>=2.21.2"\]` → 1
  - `flit_core >=3.2,<4` → 1
  - `build-backend = "flit_core.buildapi"` → 1
  - `^\[tool.flit.module\]` → 1
  - `^name = "quizify_csv_ingest"` → 1
  - `^\[project.dependencies\]` → 0 (Pitfall 20)
  - `^dependencies = \[` → 0 (Pitfall 20)
  - `validation\|validate-extras` (case-insensitive) → 0 (Pitfall 24)
  - `fastjsonschema` → 1 (Pitfall 20: only inside the optional extra, never in runtime deps)
- **Existing test suite:** `cd quizify-csv-to-json-webhook && pytest -q` → `71 passed in 1.11s`.

## User Setup Required

None — no external service configuration required. Operators who want validation will run `cd quizify-csv-to-json-webhook && pip install '.[validate]'` after Plan 06-03 wires the helper, but that is a future-plan instruction, not a Plan 06-02 deliverable.

## Next Phase Readiness
- Plan 06-01 (schema artifact) and Plan 06-02 (this plan) are independent Wave 0 deliverables; this plan is complete and unblocks Plan 06-03 (helper wiring) and Plan 06-04 (README docs) by providing the install path the README will document and the extras the helper will lazily import.
- D-13 stdlib-only-at-runtime is preserved: a default `pip install .` will resolve nothing beyond the build backend itself; the `validate` extra is strictly opt-in.

## Self-Check: PASSED

- File `quizify-csv-to-json-webhook/pyproject.toml` exists at the worktree path. (verified by `Read`/`Write` ack)
- Commit `548f9aa` is reachable via `git log --oneline -1` on branch `worktree-agent-ac8923fe238a59fb2`.
- No accidental deletions in the Task 1 commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` → empty).

---
*Phase: 06-json-schema-validation*
*Completed: 2026-05-04*
