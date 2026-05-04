# Phase 6: JSON Schema Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 06-json-schema-validation
**Areas discussed:** Packaging surface for [validate] extra, Schema file location & naming, additionalProperties / strictness policy, Validation timing & --validate × Phase-5 missing-trio

---

## Packaging Surface for [validate] Extra

### Q1 — Delivery mechanism for fastjsonschema

| Option | Description | Selected |
|--------|-------------|----------|
| Add minimal pyproject.toml with [validate] extra | Create pyproject.toml at quizify-csv-to-json-webhook/ with [project.optional-dependencies] validate = ['fastjsonschema>=2.21.2']. Honors locked STATE decision. Local-install only. | ✓ |
| Document direct pip install (no pyproject) | README says `pip install fastjsonschema>=2.21.2`. Simpler but contradicts the locked install path decision. | |
| Add to requirements-dev.txt only | Bundle into existing dev deps. Cheapest but conflates dev vs runtime-optional. | |
| pyproject.toml + console_scripts entry | Adds a `quizify-csv` console script. Beyond Phase 6 scope. | |

**User's choice:** Add minimal pyproject.toml with [validate] extra (Recommended).
**Notes:** Locks D-06-01 through D-06-05. Preserves D-13 (no runtime deps).

### Q2 — Build backend + Python floor

| Option | Description | Selected |
|--------|-------------|----------|
| flit_core, requires-python = '>=3.9' | Mirrors confluence-to-markdown sibling. 3.9 floor honest about PEP 585 use. | ✓ |
| setuptools, requires-python = '>=3.9' | More universal; slightly more config. | |
| hatchling, requires-python = '>=3.10' | Modern default; new backend not used elsewhere. | |
| flit_core, requires-python = '>=3.10' | Sibling backend with raised floor. | |

**User's choice:** flit_core, requires-python = '>=3.9' (Recommended).
**Notes:** D-06-02 (flit_core), D-06-03 (>=3.9).

### Q3 — Module shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single-module project (py-modules) | Declare `quizify_csv_ingest` as top-level py-module. Preserves single-file CLI claim. | ✓ |
| Restructure into package directory | Move into `quizify_csv_ingest/` with `__init__.py` + `__main__.py`. Bigger refactor, outside scope. | |
| Keep flat, no module declaration | pyproject metadata only, no module packaging. Tests already use pythonpath. | |

**User's choice:** Single-module project (Recommended).
**Notes:** D-06-04.

### Q4 — README integration

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing sections, no new headings | Add --validate row to existing CLI reference table; install line under Quickstart; no new H2. D-11 drift test passes. | ✓ |
| Add a new 'Schema validation' section | Promote to its own H2. More discoverable but BREAKS 10-section lock. | |
| Append to 'Configuration' section only | Compact but obscure for users grepping 'validate'. | |

**User's choice:** Extend existing sections, no new headings (Recommended).
**Notes:** D-06-23. test_readme_help_alignment.py passes without allowlist edits.

---

## Schema File Location & Naming

### Q1 — Schema artifact path

| Option | Description | Selected |
|--------|-------------|----------|
| docs/webhook-schema.json | Next to docs/webhook-quizify-format-example.json. Schema + example payload colocated. | ✓ |
| schema/quizify-webhook.schema.json | New top-level schema/ directory; .schema.json suffix for tool recognition. | |
| docs/quizify-webhook.schema.json | Hybrid: docs/ colocation with .schema.json suffix. | |

**User's choice:** docs/webhook-schema.json (Recommended).
**Notes:** D-06-06.

### Q2 — Schema $id and $schema

| Option | Description | Selected |
|--------|-------------|----------|
| Draft-07 URL + $id repo-relative path | Explicit Draft-07; $id is repo path string. Self-validation works; no URL rot. | ✓ |
| $schema only, no $id | Slightly simpler; no cross-schema refs needed. | |
| Draft-07 + $id = file basename | Minimal but valid. | |

**User's choice:** Draft-07 URL + $id repo-relative path (Recommended).
**Notes:** D-06-07.

---

## additionalProperties / Strictness Policy

### Q1 — additionalProperties policy

| Option | Description | Selected |
|--------|-------------|----------|
| Strict at top level (additionalProperties=false on row) | Row accepts only known contact fields + tail keys + question-N triples via patternProperties. Catches contract drift. | ✓ |
| Strict everywhere (top + answer objects) | Maximum drift catching. Risks failing on Quizify's variable answer-object shape. | |
| Permissive: additionalProperties unset | Validates required fields + patterns only. Loses drift-detection value. | |
| Strict on top, permissive on nested objects | Asymmetric ownership: we own envelope, Quizify owns answer content. | |

**User's choice:** Strict at top level (Recommended).
**Notes:** D-06-10. With D-06-14 (permissive on nested answers), the asymmetric-ownership spirit is preserved without explicit selection of the fourth option — top-level strict + nested-permissive falls out of D-06-10 + D-06-14 in combination.

### Q2 — Required fields

| Option | Description | Selected |
|--------|-------------|----------|
| All contact fields + tail keys + quiz_title | Strongest envelope. Matches what build_row always emits. | ✓ |
| Only the locked D-05 tail keys | Looser; doesn't match emit behavior. | |
| All except phone | Slightly looser on the most-missing PII field. | |

**User's choice:** All contact fields + tail keys + quiz_title (Recommended).
**Notes:** D-06-11.

### Q3 — Empty value handling

| Option | Description | Selected |
|--------|-------------|----------|
| Allow empty strings; type-only constraints | type:string for all string fields, no minLength. Aligned with D-03 + Phase 5 TRAIL-02. | ✓ |
| Forbid empty strings on contact fields (minLength:1) | Stricter envelope. Could fail real exports. Contradicts D-03. | |
| Forbid empty strings only on scoring trio | Conflicts with Phase 5 TRAIL-02 contract. | |

**User's choice:** Allow empty strings; type-only constraints (Recommended).
**Notes:** D-06-12. This decision has the cascading effect of making D-06-22 (--validate × Phase-5 missing-trio independence) coherent.

### Q4 — Triple well-formedness

| Option | Description | Selected |
|--------|-------------|----------|
| patternProperties for keys, lenient values | Three regex-keyed entries; type-only on values. Validates shape, not completeness. | ✓ |
| patternProperties + dependentSchemas for completeness | Stronger; enforces every question-N has matching answers-N + answers-tags-N. Overkill for v1.1. | |
| Loose: just type-check keys | Doesn't satisfy VALI-03 strictly. | |

**User's choice:** patternProperties for keys, lenient values (Recommended).
**Notes:** D-06-13.

---

## Validation Timing & --validate × Phase-5 Missing-Trio

### Q1 — Validation insertion point

| Option | Description | Selected |
|--------|-------------|----------|
| Post-build, pre-write, on full list | After row loop, before json.dump. Validates the actual artifact. No partial output on failure. | ✓ |
| Per-row inside the build loop | Fails fast but mixes concerns. | |
| Post-write by re-reading | Wasteful I/O. | |
| Validate on root array (single pass) | Top-level array validation; pointer leaks row index. | |

**User's choice:** Post-build, pre-write (Recommended).
**Notes:** D-06-16.

### Q2 — --validate × Phase-5 missing-trio

| Option | Description | Selected |
|--------|-------------|----------|
| No upgrade — WARNING + schema check are independent gates | Phase-5 WARNING fires on header absence; schema permits empty strings. Both signals shown. | ✓ |
| Upgrade: --validate promotes missing-trio to LayoutError | Stronger 'don't ship malformed' stance. Bypasses fastjsonschema for an error it can't catch. | |
| Tighten schema: minLength:1 on trio | Lets fastjsonschema reject empty trio. Contradicts D-03 + locked D-06-12. | |

**User's choice:** No upgrade — independent gates (Recommended).
**Notes:** D-06-22. Resolves the question Phase 5's CONTEXT.md `<deferred>` flagged.

### Q3 — Stderr template for validation failure

| Option | Description | Selected |
|--------|-------------|----------|
| Pointer + expected type, no field name | `ERROR schema validation failed at /email: expected string, got null`. Categorical only; T-PII-01 safe. | ✓ |
| Pointer only | Most conservative; operator must read schema to interpret. | |
| Pointer + fastjsonschema's full message | May echo offending value; PII-unsafe. Rejected. | |

**User's choice:** Pointer + expected type (Recommended).
**Notes:** D-06-20. Template locked verbatim.

### Q4 — Exit code for validation failures

| Option | Description | Selected |
|--------|-------------|----------|
| Exit 1 — same as other CLI errors | Standard non-zero. CI scripts already check `$? -ne 0`. | ✓ |
| Exit 2 — distinct for validation | Reserves a code; one more thing to document. | |
| Exit 3 — three-way distinct | Maximum CI granularity; bigger documentation surface. | |

**User's choice:** Exit 1 (Recommended).
**Notes:** D-06-21.

---

## Claude's Discretion

Captured in CONTEXT.md `<decisions> ### Claude's Discretion`. Includes:
- Schema authorship style (inline vs $defs extraction; per-property descriptions)
- Validation helper placement (module-top vs nested in convert())
- Test file names and class organization
- Single-line vs multi-line stderr message shape (template content locked, line shape free)
- Compiled-validator threading through convert() signature vs ad-hoc
- Optional schema property descriptions

## Deferred Ideas

Captured in CONTEXT.md `<deferred>`. Summary:
- AUTO-01 (HTTP POST delivery) — v1.2 candidate; unblocked by this phase
- Production-grade JSON Schema diagnostics — explicitly out of scope per REQUIREMENTS.md
- Default-on validation — explicitly out of scope
- Validating Quizify question text values — explicitly forbidden
- dependentSchemas triple-completeness enforcement — overkill for v1.1
- Console_scripts entry (quizify-csv shim) — outside Phase 6 scope
- Restructuring quizify_csv_ingest.py into a package directory
- Three-way exit-code scheme — rejected for v1.1
- additionalProperties:false on nested answer objects — rejected (asymmetric ownership)
- Promoting Phase 5 missing-trio WARNING to LayoutError under --validate — rejected (independent gates)
