# Project Research Summary

**Project:** Quizify CSV → Webhook JSON — v1.1 Contract Hardening & Make.com Alignment
**Domain:** Python stdlib CLI + co-owned iPaaS JS consumer surface (contract hardening milestone)
**Researched:** 2026-05-03
**Confidence:** HIGH

---

## Executive Summary

v1.1 is a correctness-and-hardening milestone, not a feature-expansion milestone. All four targeted work items (TRAIL-01, CONTRACT-01, MAKE-FIX-01, VALI-01) address bugs or silent contract drift that exist in the v1.0 codebase right now; none introduces net-new capability visible to end users. The correct build order is JS fixes first (highest leverage, zero Python risk), then Python trailer hardening, then schema validation last — because the schema should validate the final stable payload shape, not an intermediate one. Two of the four items are single-character or single-line fixes that have been silently mis-routing live customer data since deployment.

The most consequential unresolved decisions before requirements scoping can close are three user-confirmation questions raised by the pitfalls research: whether `activity_profile` (currently inverted for all submissions) flows into any live Airtable formula or email campaign, whether the CSV sample contains a peri-menopausal row needed for manual verification, and whether any Airtable formula currently filters on the hyphen spelling `"peri-menu"`. These are not implementation details — they determine whether the MAKE-FIX-01 fixes are safe to ship as-is or require a coordinated downstream update. They must be resolved before the MAKE-FIX-01 phase can be planned.

The single technically contested decision is the VALI-01 library choice. Three of four researchers disagreed. After weighing all arguments (see VALI-01 Reconciliation section below), the recommendation is `fastjsonschema` 2.21.2 as an optional extra (`pip install '.[validate]'`), not `jsonschema` and not a hand-rolled checker. This preserves D-13's stdlib-only baseline for non-validation users, produces a reusable formal JSON Schema artifact for AUTO-01 in v1.2, and avoids the 2-6 transitive dependency tree that `jsonschema` 4.17.3 brings.

---

## Key Findings

### Recommended Stack

v1.1 requires exactly one new package: `fastjsonschema` 2.21.2, and only for users who explicitly opt into validation via `--validate`. All other v1.1 features (TRAIL-01, CONTRACT-01, MAKE-FIX-01) are pure code changes with zero stack delta. The project remains Python 3.7+, stdlib-only at runtime for the default path.

**Core technologies:**

| Technology | Purpose | Why Recommended |
|------------|---------|-----------------|
| Python 3.7+ stdlib | All runtime logic (conversion, trailer lookup, JSON output) | Existing constraint; unchanged |
| `fastjsonschema` 2.21.2 | Compile-and-call JSON Schema Draft-07 validator for `--validate` mode | Zero transitive runtime deps; no Python version floor; formal schema artifact reusable by AUTO-01 and CI |
| pytest (dev only, unchanged) | Test runner | Already pinned in `requirements-dev.txt` |

**What NOT to use:**

- `jsonschema` 4.17.3 — brings 2-6 transitive packages (attrs, pyrsistent + conditional backports); frozen at 4.17.3 means perpetual security-audit debt; richer API is unnecessary for envelope-only structural checks.
- `jsonschema` 4.18+ — raised Python floor to 3.8+; incompatible with stated 3.7+ constraint.
- Hand-rolled validator — acceptable for pure structural checking but produces no formal schema artifact; defeats the goal of making D-05 machine-checkable for AUTO-01 and CI tooling.
- Module-top `import fastjsonschema` — must be a lazy conditional import inside the validation function to preserve v1.0 "no install required" behavior for non-validation callers.

**Packaging:** Declare `fastjsonschema>=2.21.2` under `[project.optional-dependencies] validate = [...]` in `pyproject.toml`. Gate the import with a `try/except ImportError` that emits a clear `SystemExit` message when `--validate` is passed without the package installed.

---

### VALI-01 Library Reconciliation (Critical Disagreement Resolution)

All four researchers agreed on one point: the schema validates envelope structure only, not question content. They disagreed on the implementation vehicle. The table below resolves this.

| Option | Researcher | Key Argument For | Key Argument Against |
|--------|-----------|------------------|----------------------|
| `fastjsonschema` 2.21.2 | STACK.md | Zero transitive deps; Python 3.3+ compat; formal schema artifact; compile-once model | Not stdlib; requires opt-in packaging |
| `jsonschema` (de facto standard) | FEATURES.md + PITFALLS.md | De facto Python JSON Schema standard | 2-6 transitive packages including C-extension `pyrsistent`; frozen at 4.17.3 creates security debt; Draft 7 vs 2020-12 gotchas (Pitfall 6) |
| Hand-rolled ~30-line structural checker | ARCHITECTURE.md | Preserves D-13 strictly; no new deps | Produces no formal schema file; cannot be consumed by Make.com, AUTO-01, or CI without Python tooling |

**Primary recommendation: `fastjsonschema` 2.21.2 as optional extra.**

Rationale:
1. AUTO-01 (v1.2 HTTP POST gating) explicitly depends on VALI-01 being "in place." A hand-rolled checker cannot be consumed by non-Python tooling; a formal JSON Schema Draft-07 file can be loaded directly by Make.com and CI validators.
2. D-13 is preserved for the default non-validation path. The optional-extra pattern (`pip install '.[validate]'`) is the least disruptive relaxation: stdlib is still the runtime baseline; validation is an explicit capability tier.
3. `fastjsonschema`'s zero-transitive-deps property is meaningfully different from `jsonschema`'s 2-6-package tree.
4. The PITFALLS.md Draft-mismatch warning (Pitfall 6) applies specifically to `jsonschema`'s implicit draft selection; `fastjsonschema` is pinned to Draft-07 by design.

**What would change the call:**
- Choose `jsonschema` if: human-readable validation diagnostics (error iterators, `best_match`) become a user-facing requirement.
- Choose hand-rolled if: the schema is never published or consumed outside the script, and AUTO-01 is definitively descoped.
- Choose hard dependency (not optional extra) if: `--validate` becomes default-on in a future version.

**Critical implementation constraint:** The import MUST be lazy (inside the validation function, guarded by `try/except ImportError`). A module-top import breaks the "no install required" guarantee and causes immediate CI failures on clean virtualenvs (Pitfall 3).

---

### Expected Features

All five v1.1 items are P1; none is deferrable if the milestone goal ("lock down the JSON contract end-to-end") is to be met.

**Must have (table stakes for v1.1):**

| Feature | Description | Why Non-Deferrable |
|---------|-------------|-------------------|
| MAKE-FIX-01b: Fix inverted `activity_profile` | `score-calculations.js:247-250` — `if (!data.is_athlete)` assigns `"athlete"` to non-athletes | Correctness bug affecting 100% of submissions since deployment |
| MAKE-FIX-01a: Fix `peri_menu` tag mismatch | Emitter uses `"peri_menu"` (underscore); checker uses `"peri-menu"` (hyphen); `is_peri_meno` always false | All perimenopausal submissions receive wrong `life_stage` |
| CONTRACT-01: Remove `product_result` dead key | `quizify-mapping.js:103` reads a key the Python CLI never emits; always resolves to `null` | Spurious null column in every downstream Airtable record |
| TRAIL-01: Name-based scoring lookup | Replace positional `trailer_cells_decoded[0..2]` with `TRAILER_SCORE_MAP` + `_lookup_trailer_cell()` | Positional binding silently mis-assigns scoring fields when `--trailer-columns` is non-default |
| VALI-01: Opt-in JSON Schema validation | `--validate` flag; `fastjsonschema` optional extra; schema at `schema/quizify-webhook.schema.json` | Prerequisites AUTO-01 in v1.2; provides CI fast-fail path |

**Defer (v1.2+):**
- AUTO-01: HTTP POST delivery mode — depends on VALI-01 landing first.
- STREAM-01: Streaming/NDJSON output — no evidence of >50k-row exports.
- JS test harness (Jest/Vitest) — justified only if `make-scripts/` grows beyond ~500 LOC.
- `--validate-output json` structured error format.

---

### Architecture Approach

v1.1 makes targeted, bounded additions to the single-file `quizify_csv_ingest.py` architecture. The file grows from ~427 to ~480-490 LOC; D-12 (single-file) is preserved. All JS changes are one-line or one-character fixes requiring no toolchain addition.

**New artifacts introduced by v1.1:**

| Artifact | Location | Purpose |
|----------|----------|---------|
| `quizify-webhook.schema.json` | `quizify-csv-to-json-webhook/schema/` | JSON Schema Draft-07 envelope spec; runtime artifact loaded by `--validate` |
| `pyproject.toml` | `quizify-csv-to-json-webhook/` | Declares `[validate]` optional extra |
| `CONVENTIONS.md` | `quizify-csv-to-json-webhook/make-scripts/` | Tag-naming canon; drift prevention without tooling overhead |
| `tests/test_validation.py` | `quizify-csv-to-json-webhook/tests/` | VALI-01 unit tests (function-level, not subprocess) |

**Key architectural constraints confirmed:**
- `validate_payload()` lives in `convert()` after accumulation loop, not inside `build_row()`. `build_row()` remains pure.
- `--dry-run` does NOT validate payload shape; `--dry-run --validate` must produce a documented behavior, not silent flag-drop.
- TRAIL-01 passes `trailer_headers_decoded` as a new arg to `build_row()`. The `_trailer_h` return value from `classify_headers()` is already computed but discarded; no new I/O needed.
- Schema file is a runtime artifact (loaded via `pathlib`), not a test fixture. Lives in `schema/`, not `tests/`.
- TRAIL-01 name lookup MUST use NFC+casefold equality, not substring containment. Substring matching on `"score"` would match both `"Score category"` and `"Score value"` (Pitfall 9).

---

### Critical Pitfalls

**Top 5 by severity and likelihood:**

1. **`is_athlete` inversion fix requires user confirmation before merge** — The fix changes which customers are tagged `"athlete"` vs `"non_athlete"` in Airtable and Make.com output. This is a HARD GATE: user confirmation must be recorded in MILESTONES.md before the fix is merged (Pitfall 14).

2. **`additionalProperties: false` at root level breaks dynamic-column tolerance** — Use `patternProperties` for the `question-N`/`answers-N`/`answers-tags-N` dynamic block; apply `additionalProperties: false` only to fixed-key blocks, or omit it in favor of `required`-only presence checks (Pitfall 1).

3. **`required` array must cover ALL D-05 tail keys including four reserved placeholders** — Cross-reference schema `required` array against `PHASE_3_REQUIRED_KEYS` in `test_structural_invariants.py` (Pitfall 2).

4. **PII leakage through `fastjsonschema` error output** — `JsonSchemaValueException` carries the failing value. Log only schema path and expected type, never the instance value. Add T-PII-01 test for validation errors (Pitfall 4).

5. **Silent positional fallback in TRAIL-01 re-introduces the bug being fixed** — Without `--validate`, a miss emits `""` + WARNING naming the missing column. No integer-index fallback branch. Grep for `trailer_cells_decoded[0]` after implementation to confirm removal (Pitfall 10).

---

### Peri-Menopause Canonical Spelling: Disagreement and Resolution

**ARCHITECTURE.md:** align to `"peri-menu"` (hyphen), changing the emitter to match the checker.
**FEATURES.md:** align to `"peri_menu"` (underscore), changing the checker to match the emitter.

**Recommended resolution: `peri_menu` (underscore).** Fix `score-calculations.js:213`; do not touch `quizify-mapping.js:167`.

Rationale: Every compound tag in the emitter uses underscores without exception (`has_red_flags`, `goal_athlete`, `consent_given`, `no_pelvic_symptom`, `goal_sleep`). The emitter is the canonical source; changing the emitter would risk breaking any downstream consumer that currently reads `"peri_menu"` from tags. Changing only the checker is the minimal, safe fix.

**If wrong:** Confirm whether Airtable formulas filter on tag strings directly (OQ-3). That answer also determines which direction to fix.

---

## Open Questions (Block Requirements Scoping)

These three questions must be answered before the MAKE-FIX-01 phase can be planned.

### OQ-1: `is_athlete` inversion — live Airtable or campaign impact?

**Question:** Has `activity_profile` been used in any live Airtable formula, automation, view, or email campaign segmentation?

**Why it blocks scoping:** If yes, the fix changes customer segment membership and requires a coordinated downstream update plan. If no, the fix is safe to merge immediately.

**Who answers:** Project owner / Airtable admin.

**Default if unanswered:** Treat as YES. Include coordinated-update step in MAKE-FIX-01 plan.

---

### OQ-2: Peri-menopausal row coverage in `quizify-submissions.csv`

**Question:** Does `docs/quizify-submissions.csv` contain any row where `Perimenopausia/Menopausia` includes `"Peri"`?

**How to check:** `grep -i "peri" quizify-csv-to-json-webhook/docs/quizify-submissions.csv`

**Why it blocks scoping:** MAKE-FIX-01a verification requires a perimenopausal row for manual end-to-end confirmation. If absent, a synthetic fixture must be created before the verification checklist can close.

---

### OQ-3: Airtable `peri-menu` (hyphen) formula consumers

**Question:** Does any Airtable formula, automation, or email-template condition filter on `"peri-menu"` (hyphen)?

**Why it blocks scoping:** The recommended fix writes `"peri_menu"` (underscore) to Make.com output. If Airtable reads `"peri-menu"`, the fix changes formula match behavior silently.

**Who answers:** Project owner / Airtable admin.

**Default if unanswered:** Search Airtable formulas for both spellings before merging. Document in MILESTONES.md.

---

## Implications for Roadmap

Researchers converged on a 3-phase build order. One researcher proposed CONTRACT-01 as a separate first phase; all four agreed JS fixes precede Python work, and TRAIL-01 precedes VALI-01. The synthesis collapses CONTRACT-01 into the JS-fixes phase.

### Phase 1: JS Contract Fixes (CONTRACT-01 + MAKE-FIX-01)

**Rationale:** Live correctness bugs affecting 100% of submissions. Pure JS edits — zero Python risk, no new deps, no test infrastructure changes. Both JS modules are touched in both features; reviewing them together in one phase is safer than two separate passes.

**Delivers:**
- `product_result` dead key removed from `quizify-mapping.js:103`
- `peri_menu` tag normalized across `quizify-mapping.js:167` (already correct) and `score-calculations.js:213`
- `activity_profile` condition corrected in `score-calculations.js:247-250`
- `make-scripts/CONVENTIONS.md` created

**Features addressed:** CONTRACT-01, MAKE-FIX-01a, MAKE-FIX-01b

**Pitfalls to avoid:** OQ-1 (is_athlete user confirmation) is a HARD GATE. OQ-3 (Airtable hyphen consumers) must be checked. OQ-2 (sample coverage) must be verified before verification checklist can close.

**Prerequisites:** OQ-1 and OQ-3 user confirmations resolved.

**Research flag:** Standard patterns — no phase-level research needed.

---

### Phase 2: Python Trailer Hardening (TRAIL-01)

**Rationale:** Python-only, isolated to `build_row()` + `convert()`. No new deps. Must land before VALI-01 so the schema validates the hardened payload shape, not the positional D-15 behavior.

**Delivers:**
- `TRAILER_SCORE_MAP` constant + `_lookup_trailer_cell()` function
- `build_row()` signature updated (`trailer_headers_decoded` added)
- `convert()` passes decoded trailer headers (currently discarded as `_trailer_h`)
- README `## Column assumptions` and `## Limitations` updated
- `tests/test_row_builder.py` updated with out-of-order `--trailer-columns` fixture
- D-15 formally retired from Key Decisions

**Features addressed:** TRAIL-01

**Pitfalls to avoid:** Pitfall 9 (substring collision — use equality, not `in`), Pitfall 10 (positional fallback — none allowed), Pitfall 11 (normalization — use `_norm_for_match()`, not `.lower()`).

**Research flag:** Standard patterns — follows existing `TAG_HEADER_MAP` + `_norm_for_match()` pattern exactly.

---

### Phase 3: JSON Schema Validation (VALI-01)

**Rationale:** Depends on Phase 2 (TRAIL-01) complete. Most new code and test infrastructure. D-11 drift test will fail the moment `--validate` is added to argparse — this is expected; README update is part of the same commit.

**Delivers:**
- `schema/quizify-webhook.schema.json` (JSON Schema Draft-07, hand-authored)
- `pyproject.toml` with `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`
- `validate_payload()` + `_validate_record()` + `_load_schema()` in `quizify_csv_ingest.py`
- `--validate` flag in argparse; wired into `convert()`
- Lazy `fastjsonschema` import with clear `SystemExit` message
- `tests/test_validation.py` (function-level unit tests, not subprocess)
- README updated: `--validate` in CLI reference table; `--dry-run --validate` behavior documented
- Exit-code table updated (code 1 for validation failure)

**Features addressed:** VALI-01

**Pitfalls to avoid:** Pitfall 1 (additionalProperties + dynamic columns), Pitfall 2 (required subset), Pitfall 3 (lazy import), Pitfall 4 (PII in errors), Pitfall 5 (answers-N anyOf), Pitfall 6 (explicit $schema declaration), Pitfall 8 (--dry-run interaction), Pitfall 15 (D-11 drift test), Pitfall 16 (test time budget ≤ 2.5s).

**Research flag:** Confirm `fastjsonschema` 2.21.2 API during plan authoring: `compile()` call signature and `JsonSchemaValueException` attribute names for PII-safe path extraction. Low-effort Context7 lookup.

---

### Phase Ordering Rationale

- **JS first:** Live correctness bugs; zero Python risk. Every additional day means more customers mis-classified.
- **TRAIL-01 before VALI-01:** Schema must validate the final payload shape. TRAIL-01 does not change output shape semantically, but validating against D-15 (positional) behavior and then changing to TRAIL-01 adds an unnecessary re-check step.
- **VALI-01 last:** Most new code, most new test infrastructure, D-11 drift test interaction, and dependency on TRAIL-01 payload stability make this the natural anchor point.
- **CONTRACT-01 + MAKE-FIX-01 grouped:** Single coherent review of both JS files reduces cross-file miss risk.

---

### Research Flags

**Needs phase-level research during planning:**
- **Phase 3 (VALI-01):** Confirm `fastjsonschema` 2.21.2 API: `compile()` signature, `JsonSchemaValueException` attribute for PII-safe path extraction, `patternProperties` behavior alongside `required`. Context7 lookup recommended.

**Standard patterns (skip research-phase):**
- **Phase 1 (JS fixes):** Mechanical one-character and one-line edits.
- **Phase 2 (TRAIL-01):** Follows existing `TAG_HEADER_MAP` / `_norm_for_match()` pattern exactly.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Library versions verified against PyPI metadata directly. Transitive dep trees confirmed. `fastjsonschema` recommendation grounded in dep-footprint analysis, not preference. |
| Features | HIGH | All findings from direct in-repo source code and CSV sample. Bug root causes confirmed by line-level inspection. No ecosystem speculation. |
| Architecture | HIGH | Full source read of all three files. Change surface precisely bounded. D-05/D-11/D-12/D-13/D-15 implications fully mapped. |
| Pitfalls | HIGH | All pitfalls grounded in direct code inspection and existing test suite analysis. No speculative pitfalls. |

**Overall confidence:** HIGH

### Gaps to Address

| Gap | How to Handle |
|-----|--------------|
| OQ-1: `activity_profile` Airtable/campaign impact | User confirmation required before Phase 1 can close. Default: treat as YES. |
| OQ-2: Peri-menopausal row in CSV sample | `grep -i "peri" docs/quizify-submissions.csv` at Phase 1 plan authoring. If absent, create synthetic fixture. |
| OQ-3: Airtable `peri-menu` hyphen consumers | User confirmation / Airtable audit before Phase 1 can close. |
| `fastjsonschema` exception attributes for PII-safe path logging | Confirm `JsonSchemaValueException` attribute names during Phase 3 plan authoring. Context7 lookup. |
| Canonical peri-menopause tag spelling | Resolved: `peri_menu` (underscore). Document in PROJECT.md Key Decisions before Phase 1 planning. |
| `CONVENTIONS.md` tag-naming convention scope | Declare underscore-first (matching emitter convention), not kebab-first. Document mixed historical convention; normalize toward underscore for new tags going forward. |

---

## Sources

### Primary (HIGH confidence — direct source code inspection)

- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (427 LOC, complete read) — architecture, trailer indexing, build_row signature, TAG_HEADER_MAP pattern
- `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` (188 LOC, complete read) — CONTRACT-01 ghost key, MAKE-FIX-01 peri tag emitter
- `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` (296 LOC, complete read) — MAKE-FIX-01 peri tag checker, activity_profile inversion
- `quizify-csv-to-json-webhook/tests/test_structural_invariants.py` — `PHASE_3_REQUIRED_KEYS` frozenset as canonical contract reference
- `quizify-csv-to-json-webhook/tests/test_logging_pii.py` — T-PII-01 pattern for validation error logging
- `.planning/PROJECT.md` — Key Decisions D-05, D-11, D-12, D-13, D-15; constraints; v1.1 feature specs; milestone history

### Primary (HIGH confidence — verified via PyPI API)

- PyPI `fastjsonschema` 2.21.2 metadata — `requires_python` (absent), `requires_dist` (devel-only extras), confirming zero transitive runtime deps
- PyPI `jsonschema` 4.17.3 metadata — `requires_python: >=3.7`, `requires_dist`: attrs, pyrsistent + conditional backports
- Context7 `/websites/horejsek_github_io_python-fastjsonschema` — Draft-07 support, Python compat, compile model confirmed

### Secondary (MEDIUM confidence)

- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` (42-row sample, 10 rows reviewed) — sample coverage assessment for OQ-2; full peri-menopausal coverage unverified
- `.planning/MILESTONES.md` — v1.0 delivery record; 71 tests / 1.09s baseline

---

*Research completed: 2026-05-03*
*Ready for roadmap: yes — pending resolution of OQ-1, OQ-2, OQ-3 before Phase 1 planning can close*
