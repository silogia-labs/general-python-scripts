# Requirements: Quizify CSV → Webhook JSON v1.1

**Defined:** 2026-05-04
**Milestone:** v1.1 Contract Hardening & Make.com Alignment
**Core Value:** Each CSV submission row becomes one webhook-compatible JSON object — without manual restructuring, and now with a verifiable contract end-to-end (Python emit ↔ Make.com consume).

## v1.1 Requirements

Requirements for v1.1. Each maps to exactly one roadmap phase. Continues v1.0's REQ-ID convention with new category prefixes.

### Schema Validation (VALI-XX)

- [ ] **VALI-01**: User can validate the emitted JSON payload against an in-repo JSON Schema by passing `--validate` to the CLI
- [ ] **VALI-02**: When `--validate` is passed and the payload violates the schema, the CLI exits non-zero with a PII-safe stderr message naming the JSON Pointer path of the violation (no cell content leaked; T-PII-01 carry-forward)
- [ ] **VALI-03**: The schema at `quizify-csv-to-json-webhook/docs/webhook-schema.json` validates envelope structure — contact fields by name and type, locked tail order via `required`, presence and well-formedness of `question-N`/`answers-N`/`answers-tags-N` triples via `patternProperties` — without constraining question text values
- [ ] **VALI-04**: Validation is opt-in only — default behavior of all v1.0 CLI invocations is preserved when `--validate` is absent (no-flag callers see zero behavioral change)
- [ ] **VALI-05**: `fastjsonschema` (>= 2.21.2) is an optional extra (`pip install '.[validate]'`); the CLI imports it lazily inside the validation function and prints an actionable stderr error if `--validate` is used without the extra installed
- [ ] **VALI-06**: README documents the `--validate` flag, the `[validate]` extra installation step, and the schema path; the D-11 drift test (`test_readme_help_alignment.py`) passes after the additions

### Trailer Hardening (TRAIL-XX)

- [ ] **TRAIL-01**: Scoring trio (`result-logic`, `score-category`, `score-value`) is extracted from trailer cells by canonical column-name lookup using NFC+casefold equality (replaces positional `trailer_cells_decoded[0..2]`; D-15 retired in favor of name-based binding)
- [ ] **TRAIL-02**: When a canonical trailer column is missing from the CSV, the CLI emits an empty string for that scoring field and logs a PII-safe WARNING naming the absent column. Fallback to positional indexing is explicitly forbidden (per PITFALLS analysis: "the v1.0 bug wearing a different costume")
- [ ] **TRAIL-03**: Default-order callers see no behavioral change; non-default `--trailer-columns` callers receive the bugfix automatically. The behavioral correction for non-default orders is documented in MILESTONES.md (under v1.1) as a bugfix

### Contract Reconciliation (CONTRACT-XX)

- [ ] **CONTRACT-01**: `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` reads `record["product-recommendation"]` (matching D-05 locked Python output) instead of the dead `record.product_result`; manual verification confirms the JS output object exposes the recommendation passthrough whenever the Python payload emits a non-null value

### Make.com JS Fixes (MAKE-FIX-XX)

- [ ] **MAKE-FIX-01**: Peri-menopause tag is canonically `peri_menu` (underscore) across both `quizify-mapping.js` and `score-calculations.js`. The hyphen variant `"peri-menu"` at `score-calculations.js:213` is replaced with `"peri_menu"` so the `peri_menopause_menopause` life-stage classification is detected for matching respondents
- [ ] **MAKE-FIX-02**: `score-calculations.js:247-250` `activity_profile` condition is corrected so `data.is_athlete === true` yields `"athlete"` and otherwise yields `"non_athlete"` (current inverted logic mis-classifies the entire respondent population)
- [ ] **MAKE-FIX-03**: Manual verification steps are documented in `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` (new file) covering: (a) MAKE-FIX-01 verification using sample rows 10 (Karen Retamal) and 35 (Javielys Mancilla) of `docs/quizify-submissions.csv` — both have `Perimenopausia` in `menopause_status`; (b) MAKE-FIX-02 verification using a non-athlete row (sport_level not containing "alto"); (c) CONTRACT-01 verification approach for the `product-recommendation` passthrough; (d) tag canonical-spelling convention (snake_case underscores throughout)

## Future Requirements (v1.2+)

Deferred to a future release. Tracked but not in v1.1 roadmap.

### HTTP Delivery

- **AUTO-01**: CLI can POST the emitted JSON to a configured webhook URL (per-row or batched, with retries and exponential backoff). Depends on VALI-01 being available to gate POSTs on envelope validity.

### Performance

- **STREAM-01** (was T-RESOURCE-01): NDJSON / streaming output mode for very large CSVs (>50k rows). Write each record as it's built rather than accumulating the full array in memory.

### Make.com JS Maintenance

- **MAKE-COSMETIC-01**: Fix `Reomoto` typo at `score-calculations.js:157` (should be `Remoto`)
- **MAKE-COSMETIC-02**: Remove dead-code initialization `profile = "profile_base"` at `score-calculations.js:217` (always overwritten by lines 220-233)
- **MAKE-TEST-01**: Introduce a Node.js test harness (e.g., `node --test` stdlib runner) for `make-scripts/` if/when the JS files grow beyond ~500 LOC combined

## Out of Scope

Explicitly excluded for v1.1. Documented to prevent scope creep and lock decisions.

| Feature | Reason |
|---------|--------|
| Adding a Node.js test runner for `make-scripts/` JS modules in v1.1 | v1.1 ships manual verification only; preserves v1.0's stdlib-only ethos. Two short JS files (~290 LOC combined) don't justify a Node toolchain. Revisit in v1.2 as MAKE-TEST-01 if scope grows. |
| Auto-generating `webhook-schema.json` from the example payload | Auto-generation would embed quiz-specific Spanish question strings as required schema values, coupling our schema to Quizify's localization decisions outside our control. Hand-write to keep the schema envelope-only. |
| Validating Quizify question text against an allowlist | Question text is the join key for Make.com Module 1's `QUESTION_CONFIG`; constraining it would couple our schema to Quizify's product/localization decisions. We validate triple presence and well-formedness, not values. |
| Fallback-to-positional behavior in TRAIL-01 | Per PITFALLS analysis: "the v1.0 bug wearing a different costume". TRAIL-01 fix must be assertive (warn + omit), not silent fallback to `trailer_cells_decoded[0..2]`. |
| Rewriting Make.com workflow scoring logic in Python | Module 2 (`score-calculations.js`) ignores our scoring trio and recomputes from raw answers; out-of-scope refactor that would require Make.com architecture decisions and break the iPaaS topology. |
| Default-on schema validation | Would force a v2.0 semver bump and break callers piping malformed payloads. v1.1 ships strict-when-enabled, opt-in only. AUTO-01 in v1.2 may promote to default-on within the POST path only. |
| Production-grade JSON Schema diagnostics | `fastjsonschema` raises minimal `JsonSchemaValueException` optimized for performance, not human readability. v1.1 reports JSON Pointer + expected type only. Promote to richer diagnostics in a later milestone if real operator need emerges. |
| Validating against the live Make.com workflow scoring rules | Out-of-scope contract verification; we validate envelope structure of our own emit. Cross-system semantic validation is a v2 initiative. |

## Traceability

Filled by `gsd-roadmapper` during phase planning.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VALI-01 | Phase 6 | Pending |
| VALI-02 | Phase 6 | Pending |
| VALI-03 | Phase 6 | Pending |
| VALI-04 | Phase 6 | Pending |
| VALI-05 | Phase 6 | Pending |
| VALI-06 | Phase 6 | Pending |
| TRAIL-01 | Phase 5 | Pending |
| TRAIL-02 | Phase 5 | Pending |
| TRAIL-03 | Phase 5 | Pending |
| CONTRACT-01 | Phase 4 | Pending |
| MAKE-FIX-01 | Phase 4 | Pending |
| MAKE-FIX-02 | Phase 4 | Pending |
| MAKE-FIX-03 | Phase 4 | Pending |

**Coverage:**

- v1.1 requirements: 13 total
- Mapped to phases: 13 (Phase 4: 4, Phase 5: 3, Phase 6: 6)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 after roadmap creation (traceability filled)*
