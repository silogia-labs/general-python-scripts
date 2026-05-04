# Roadmap: Quizify CSV → Webhook JSON

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-03) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Contract Hardening & Make.com Alignment** — Phases 4-6 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-05-03</summary>

- [x] Phase 1: CSV ingestion & column layout (1/1 plans) — completed 2026-05-03
- [x] Phase 2: Core webhook mapping (2/2 plans) — completed 2026-05-03
- [x] Phase 3: Scoring metadata & packaging (2/2 plans) — completed 2026-05-03

</details>

### 🚧 v1.1 Contract Hardening & Make.com Alignment (In Progress)

**Milestone Goal:** Lock down the JSON contract between the Python CLI and the Make.com automation — fixing live correctness bugs in the JS consumer, hardening the Python trailer scoring lookup against mis-binding, and adding opt-in JSON Schema validation for CI fast-fail and AUTO-01 prereq.

- [x] **Phase 4: Make.com JS Contract Fixes** — Fix live correctness bugs in both JS modules and document the co-owned consumer surface (completed 2026-05-04)
- [ ] **Phase 5: Python Trailer Hardening** — Replace positional trailer-cell indexing with name-based lookup; retire D-15
- [ ] **Phase 6: JSON Schema Validation** — Add opt-in `--validate` flag backed by a formal JSON Schema Draft-07 artifact

## Phase Details

### Phase 4: Make.com JS Contract Fixes
**Goal**: Both Make.com JS modules correctly process the Python CLI's JSON payload — the `product-recommendation` passthrough flows without data loss, perimenopausal respondents receive the correct `peri_menopause_menopause` life-stage tag, all respondents receive the correct `activity_profile` classification, and the co-owned consumer surface has documented conventions.
**Depends on**: Nothing (JS-only edits; zero Python risk; independent of Phases 5-6)
**Requirements**: CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02, MAKE-FIX-03

**Phase grouping rationale:** CONTRACT-01 and MAKE-FIX-01..03 are grouped together because they are all pure JS edits to the same two files (`quizify-mapping.js`, `score-calculations.js`). Reviewing both files in a single pass reduces the risk of cross-file omissions. MAKE-FIX-03 (CONVENTIONS.md + manual verification docs) is co-located here because its only purpose is to document how to verify the fixes in this phase — separating it would create a phase solely for writing a Markdown file, which is PM theater.

**Success Criteria** (what must be TRUE):
  1. Running a Make.com scenario with a row whose Python payload carries a non-null `product-recommendation` value produces a JS output object that exposes that value (the `product_result` dead key is gone; CONTRACT-01 verified).
  2. Running the Make.com scenario against sample rows 10 (Karen Retamal) and 35 (Javielys Mancilla) — both have `Perimenopausia` in `menopause_status` — produces output where `is_peri_meno` is `true` and `life_stage` includes `peri_menopause_menopause` (MAKE-FIX-01 verified).
  3. Running the Make.com scenario against a non-athlete respondent (sport_level not containing "alto") produces `activity_profile: "non_athlete"`; running against an athlete respondent produces `activity_profile: "athlete"` (MAKE-FIX-02 verified; inverted logic corrected).
  4. `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` exists and documents: tag canonical-spelling convention (snake_case underscores), CONTRACT-01 verification approach, MAKE-FIX-01 verification rows, MAKE-FIX-02 verification approach (MAKE-FIX-03 delivered).
**Plans**: 2 plans
- [x] 04-01-PLAN.md — Bundled JS edits: CONTRACT-01 deletion + MAKE-FIX-01 hyphen→underscore + MAKE-FIX-02 negation removal (Wave 1) — completed 2026-05-04
- [x] 04-02-PLAN.md — Create make-scripts/CONVENTIONS.md verification doc covering the four mandated topics (Wave 2; depends on 04-01)

### Phase 5: Python Trailer Hardening
**Goal**: The scoring trio (`result-logic`, `score-category`, `score-value`) is extracted from CSV trailer cells by canonical column-name lookup — not positional index — so any valid `--trailer-columns` ordering produces correct scoring output and missing columns produce a PII-safe warning rather than silent mis-assignment.
**Depends on**: Phase 4 (logical ordering; phases are independent in practice but JS fixes ship first to minimize live data quality impact)
**Requirements**: TRAIL-01, TRAIL-02, TRAIL-03

**Success Criteria** (what must be TRUE):
  1. Running the CLI against the 42-row sample with default `--trailer-columns` order produces identical output to v1.0 — no behavioral regression for default-order callers (TRAIL-03 verified).
  2. Running the CLI with `--trailer-columns` in a non-default order (e.g., score-value listed before result-logic) produces correctly bound scoring fields — each field maps to its named column, not its list position (TRAIL-01 verified).
  3. Running the CLI against a CSV where a canonical trailer column is absent causes the CLI to emit an empty string for that field and log a PII-safe WARNING naming the missing column — no positional fallback occurs (TRAIL-02 verified).
  4. The 71 existing tests continue to pass after the change; the new name-based lookup tests are green.
**Plans**: 3 plans
- [x] 05-01-PLAN.md — Wave 0 preconditions: scoring_index_map_default conftest fixture + v1.0 default-order golden output JSON (Pitfall G)
- [ ] 05-02-PLAN.md — TDD: name-based scoring trio binding (TRAIL-01) + missing-column PII-safe WARNING (TRAIL-02); classify_headers 5-tuple, build_row signature change, convert warning loop, 14 test_row_builder call-site updates, TestScoringIndexMap/TestScrambledTrailer/TestMissingColumnWarning classes
- [ ] 05-03-PLAN.md — TRAIL-03 default-order regression test vs v1.0 golden + README/MILESTONES updates (Pitfall F: remove 'scoring stays positional' caveats)

### Phase 6: JSON Schema Validation
**Goal**: Operators and CI pipelines can validate the CLI's emitted JSON envelope against a formal JSON Schema Draft-07 artifact by passing `--validate`; violations produce a PII-safe, actionable error message; users who do not pass `--validate` see zero behavioral change; the schema and the `[validate]` optional extra are fully documented.
**Depends on**: Phase 5 (schema must validate the hardened, name-bound payload shape; validating against the pre-TRAIL-01 positional behavior would require a re-check after Phase 5)
**Requirements**: VALI-01, VALI-02, VALI-03, VALI-04, VALI-05, VALI-06

**Success Criteria** (what must be TRUE):
  1. Running `python quizify_csv_ingest.py sample.csv --validate` (with `fastjsonschema` installed) against the 42-row sample exits 0 and produces the same JSON output as without `--validate` — no behavioral difference for valid payloads (VALI-01, VALI-04 verified).
  2. Running `python quizify_csv_ingest.py sample.csv --validate` against a deliberately malformed payload (e.g., missing a required tail key) exits non-zero and prints a PII-safe stderr message identifying the JSON Pointer path of the violation — no cell content appears in the error output (VALI-02 verified; T-PII-01 preserved).
  3. Running `python quizify_csv_ingest.py sample.csv --validate` without `fastjsonschema` installed prints an actionable stderr message explaining how to install `pip install '.[validate]'` and exits non-zero without a Python traceback (VALI-05 verified).
  4. `quizify-csv-to-json-webhook/docs/webhook-schema.json` (or `schema/quizify-webhook.schema.json`) exists, passes JSON Schema Draft-07 self-validation, and covers: all contact fields by name and type, locked D-05 tail-key presence via `required`, and `question-N`/`answers-N`/`answers-tags-N` triple well-formedness via `patternProperties` — without constraining question text values (VALI-03 verified).
  5. The operator README documents the `--validate` flag, the `[validate]` optional extra installation step, and the schema file path; `test_readme_help_alignment.py` passes after the additions (VALI-06 verified; D-11 drift test satisfied).
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. CSV ingestion & column layout | v1.0 | 1/1 | Complete | 2026-05-03 |
| 2. Core webhook mapping | v1.0 | 2/2 | Complete | 2026-05-03 |
| 3. Scoring metadata & packaging | v1.0 | 2/2 | Complete | 2026-05-03 |
| 4. Make.com JS Contract Fixes | v1.1 | 2/2 | Complete    | 2026-05-04 |
| 5. Python Trailer Hardening | v1.1 | 1/3 | In Progress|  |
| 6. JSON Schema Validation | v1.1 | 0/? | Not started | - |
