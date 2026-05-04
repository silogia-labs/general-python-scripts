# Quizify CSV → Webhook JSON

## What This Is

This initiative lives inside the `general-python-scripts` utilities repository. It ships a small Python helper (`quizify-csv-to-json-webhook/quizify_csv_ingest.py`) that turns Quizify.io CSV exports (from https://app.quizify.io) into JSON arrays shaped like `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`, so integrations that expect webhook-style records can consume exports without manual rework. The JSON is consumed by a Make.com (Integromat) automation pipeline; the two JS modules in `quizify-csv-to-json-webhook/make-scripts/` (`quizify-mapping.js`, `score-calculations.js`) are co-owned consumer surfaces of this initiative as of v1.1. v1.0 (2026-05-03) delivered the full CSV→JSON pipeline; v1.1 hardens the contract end-to-end and aligns the Make.com side.

## Core Value

Each CSV submission row becomes one webhook-compatible JSON object with correct contact fields, ordered `question-N` / `answers-N` / `answers-tags-N` keys, scoring fields, and tags — including sensible behavior when Quizify omits answer IDs (omit, not invent) or encodes characters as HTML entities (decoded uniformly).

## Current State

**Shipped: v1.1 Contract Hardening & Make.com Alignment (2026-05-04)** — see `.planning/MILESTONES.md` and `.planning/milestones/v1.1-ROADMAP.md`.
**Shipped: v1.0 MVP (2026-05-03)** — see `.planning/milestones/v1.0-ROADMAP.md`.

**Planning next milestone (v1.2 — TBD).** Likely candidates surfaced from v1.1 deferred bucket: AUTO-01 (HTTP POST delivery, gated on VALI-01), STREAM-01 (NDJSON streaming for >50k-row CSVs), MAKE-COSMETIC-01/02 (Make.com JS housekeeping), MAKE-TEST-01 (Node test harness if `make-scripts/` LOC grows).

- 94 tests passing (1.28s) across layout, row-builder, CLI emission, PII logging, golden-file structure, structural invariants, quiz-title precedence, README/`--help` drift, default-order regression (TRAIL-03), scoring-index-map binding (TRAIL-01/02), and schema validation (VALI-01..05) including PII-safe failure-stderr tests.
- Runtime stays stdlib-only (D-13 preserved via lazy import); `fastjsonschema>=2.21.2` is an opt-in `[validate]` extra installable via `pip install '.[validate]'`.
- Single-file implementation: `quizify_csv_ingest.py` + `pyproject.toml` (PEP 621 / flit_core); operator README extended with `--validate` documentation (D-11 ten-section lock preserved).
- Co-owned consumer surface: `quizify-csv-to-json-webhook/make-scripts/` (`quizify-mapping.js`, `score-calculations.js`) + `make-scripts/CONVENTIONS.md`.
- CLI surface: `csv_path` positional + `--dry-run`, `-v`/`--verbose`, `--trailer-columns`, `-o`/`--output`, `--emit-json`, `--quiz-title` (with `$QUIZIFY_QUIZ_TITLE` env fallback), `--validate` (opt-in JSON Schema gate).
- Schema artifact: `quizify-csv-to-json-webhook/docs/webhook-schema.json` (Draft-07).

## Next Milestone Goals (v1.2 — TBD)

Candidates surfaced from v1.1 close (defer/promote at next `/gsd-new-milestone`):

- **AUTO-01** — HTTP POST delivery mode. v1.1 unblocked this by shipping VALI-01 (gates POSTs on schema validity).
- **STREAM-01** — Streaming/NDJSON output for >50k-row CSVs (T-RESOURCE-01 carry-forward).
- **MAKE-COSMETIC-01** — Fix `Reomoto` typo at `score-calculations.js:157`.
- **MAKE-COSMETIC-02** — Remove dead `profile = "profile_base"` initializer at `score-calculations.js:217`.
- **MAKE-TEST-01** — Introduce Node.js test harness for `make-scripts/` if/when JS files grow beyond ~500 LOC combined.

<details>
<summary>Previous Milestone Goal Section — v1.1 (shipped 2026-05-04)</summary>

**Goal:** Lock down the JSON contract between the Python CLI and the Make.com automation by adding opt-in strict JSON Schema validation, eliminating positional mis-bind risk in trailer scoring, reconciling the field-name mismatch with `quizify-mapping.js`, and fixing two correctness bugs in the now-in-scope Make.com JS modules.

**Target features (all shipped):**

- **VALI-01** — Opt-in JSON Schema validation via `--validate` flag (✓ shipped Phase 6).
- **TRAIL-01** — Name-based scoring lookup (✓ shipped Phase 5; D-15 retired).
- **CONTRACT-01** — `quizify-mapping.js:102` reads `record["product-recommendation"]` (✓ shipped Phase 4).
- **MAKE-FIX-01..03** — Peri-menopause tag canonicalization, `activity_profile` inversion fix, `make-scripts/CONVENTIONS.md` (✓ shipped Phase 4).

</details>

## Requirements

### Validated

- ✓ Utilities-repo pattern (folder per helper script, minimal coupling) — existing across this repository
- ✓ A CLI converts Quizify CSV exports into JSON matching the documented webhook example structure — v1.0 (CONV-01..02, WEB-02)
- ✓ Conversion handles dynamic question columns, trailing score/tag columns, and HTML entities in cells — v1.0 (CONV-06, WEB-04, WEB-01)
- ✓ Contact + subscription mapping (firstName/lastName/email/phone/status/statusDate) — v1.0 (CONV-03..05)
- ✓ Per-question tag distribution via configured pattern→header keyword map — v1.0 (WEB-01, `TAG_HEADER_MAP`)
- ✓ Answer shape heuristic with `id` omitted rather than guessed — v1.0 (WEB-03)
- ✓ Scoring pass-through (`result-logic`/`score-category`/`score-value`) + 4 reserved placeholder keys — v1.0 (WEB-04)
- ✓ `quiz_title` precedence (CLI > env > "") — v1.0 (WEB-05)
- ✓ Operator README with automated `--help` drift test — v1.0 (OPS-01)
- ✓ JS consumer reads the canonical hyphenated emit key — v1.1 (CONTRACT-01)
- ✓ Peri-menopause tag canonical-spelling lock (`peri_menu` underscore on both sides) — v1.1 (MAKE-FIX-01)
- ✓ `activity_profile` JS condition correctness — v1.1 (MAKE-FIX-02)
- ✓ Manual verification protocol documented in `make-scripts/CONVENTIONS.md` (T-PII-01-safe synthetic fixtures) — v1.1 (MAKE-FIX-03)
- ✓ Scoring trio bound by canonical column name (NFC+casefold), retiring D-15 — v1.1 (TRAIL-01)
- ✓ Missing-trio-column → `""` + PII-safe WARNING (no positional fallback) — v1.1 (TRAIL-02)
- ✓ Default-order callers see zero behavioral change (golden-fixture regression test) — v1.1 (TRAIL-03)
- ✓ Hand-written Draft-07 schema covers contact, locked tail, and `question-N`/`answers-N`/`answers-tags-N` triple well-formedness without constraining text — v1.1 (VALI-03)
- ✓ Opt-in `--validate` flag exits non-zero on violation with PII-safe JSON-Pointer-only stderr — v1.1 (VALI-01, VALI-02)
- ✓ Default-off / zero-behavioral-change for unflagged callers — v1.1 (VALI-04, byte-identical stdout verified)
- ✓ `fastjsonschema>=2.21.2` as `[validate]` optional extra; lazy import preserves D-13 stdlib-only-at-runtime; missing-extra path exits with locked D-06-19 verbatim message — v1.1 (VALI-05)
- ✓ README documents `--validate` flag, install line, schema path; D-11 drift test (2/2) green — v1.1 (VALI-06)

### Active

(None — awaiting `/gsd-new-milestone` for v1.2 requirements definition. Candidates carried forward in **Next Milestone Goals** section above.)

### Out of Scope

| Feature | Reason |
|---------|--------|
| Changing Quizify's export format or product behavior | External dependency |
| Perfect reconstruction of numeric answer `id` values missing from CSV | D-07: omit unknown rather than invent IDs (validated this milestone) |
| Interactive Quizify authentication / scraping | Exports are manual CSV downloads; stay offline-first |
| GUI | Utility script only |
| Multi-tenant Quiz configuration UI | Single-quiz mapping driven by headers is sufficient through v1.x |

## Context

- Target payload shape: `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`.
- Representative export: `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` (42 rows, 20 dynamic question columns).
- CSV layout: 6 leading contact columns (`First name`, `Last name`, `Email`, `Phone`, `Subscribed to newsletter`, `Date`), a block of dynamic quiz question columns whose titles vary by quiz, then 6 trailing fields (`Result logic`, `Score category`, `Score value`, `Answer tags`, `Time to complete (mm:ss)`, `Date`).
- Codebase: Python (script + tests) + operator README + Draft-07 schema artifact + `pyproject.toml` (PEP 621 / flit_core), all under `quizify-csv-to-json-webhook/`; co-owned `make-scripts/` (Make.com IIFE modules) on the consumer side. Stdlib-only at runtime by default; `pip install '.[validate]'` adds `fastjsonschema>=2.21.2` for the opt-in `--validate` gate (lazy-imported).
- Peer scripts in the same repo (Confluence export, GitHub inventory, etc.) remain unrelated; reuse only general Python style conventions.
- Threat-model carry-forward: T-PII-01 (PII-safe stderr logging — warnings name columns + categorical enum values only, never cell content; verified by negative substring assertions). Any new log surfaces in future milestones must preserve this contract.

## Constraints

- **Technology**: Python 3.7+; prefer standard library; add dependencies only when justified (none added in v1.0).
- **Data quality**: Cells may contain HTML entities (`&gt;`, `&lt;`) that must appear as plain characters in JSON strings (`html.unescape` applied uniformly).
- **Privacy**: Treat exports as PII; default log level is WARNING; warnings name columns + categorical values, never cell content.
- **Output stability**: Top-level JSON key order is locked by D-05 (and is a strict superset of the example payload — scoring trio added before the 4 reserved placeholders). Future milestones must not reorder keys without an explicit ADR-style decision.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Defer full-repo codebase map at init | Narrow deliverable with explicit CSV/JSON fixtures under `quizify-csv-to-json-webhook/docs/` | ✓ Good — v1.0 shipped without it |
| Skip parallel domain research agents during init | Contract files in-repo defined mapping expectations | ✓ Good — saved time, no missed scope |
| Workflow prefs from `~/.gsd/defaults.json` (YOLO, balanced models, git-track planning docs) | Existing saved defaults | ✓ Applied throughout |
| TDD gate enforced for plans 02-01 and 03-01 | RED commits precede GREEN, verifying tests actually fail before implementation lands | ✓ Good — caught test-side bugs early (consent index off-by-one, type-equality false assumptions) |
| `id` key omitted entirely in object-array answers (D-07) rather than nulled | Match human intent — CSV does not carry IDs, so absence is more honest than a `null` placeholder | ✓ Good — `test_id_key_never_present_in_object_array` enforces |
| Single-file implementation (`quizify_csv_ingest.py`, 427 lines) over package layout | Surface is small and self-contained; no third-party deps | ✓ Good — split only if v2 scope (HTTP POST, schema validation) lands |
| Stdlib-only at runtime; no `requirements.txt` (D-13) | Reduces install friction; fits utility-script repo pattern | ✓ Good — `requirements-dev.txt` carries pytest only |
| README structure locked at 10 sections (D-11) | Operator predictability; drift test catches additions | ✓ Good — `tests/test_readme_help_alignment.py` enforces |
| Scoring extraction by index `trailer_cells_decoded[0..2]` rather than by canonical name (D-15) | Matches D-15 verbatim; avoids extra config surface | Retired by TRAIL-01 (Phase 5, v1.1) — replaced with NFC+casefold name-based binding; default-order callers see no behavioral change (verified by `tests/test_default_order_regression.py`) |
| Module-scoped fixture for invariant tests (single CLI invocation across 12 tests) | T-RESOURCE-01 mitigation; fast (0.06s for the file) | ✓ Good — pattern reusable in future verification harnesses |
| `quizify-csv-to-json-webhook/make-scripts/` (Make.com JS modules) treated as co-owned consumer surface starting v1.1 | These two files are the immediate downstream consumers of our JSON payload; bugs and contract drift here are indistinguishable from CLI bugs from a user-outcome perspective | v1.1 — confirmed during scoping; was implicitly out-of-scope in v1.0 |
| VALI-01 ships opt-in (default off) with `--validate` flag; strict-when-enabled (exits non-zero on schema violation) | Keeps v1.0's permissive default behavior intact for unflagged callers; gives CI/automation pipelines a fast-fail path. Unlocks AUTO-01 in v1.2 to gate POST on validation success. Avoids forcing v2.0 semver bump | v1.1 |
| CONTRACT-01 fixes the Make.com side rather than emitting an alias key from Python | D-05 JSON tail-key order is locked; introducing `product_result` as an alias would override D-05 without justification. Single-line fix in `quizify-mapping.js:102` is correct | v1.1 |
| No new JS test toolchain in v1.1 (manual verification against `quizify-submissions.csv` sample only) | Preserves v1.0's stdlib-only ethos; two short files don't justify a Node test runner. Revisit if `make-scripts/` grows beyond ~500 LOC | v1.1 — deferred to v1.2 if scope expands |
| VALI-01 shipped (Phase 6 / D-06-01..D-06-25, 2026-05-04): `--validate` flag (opt-in) backed by Draft-07 schema at `docs/webhook-schema.json`; `fastjsonschema>=2.21.2` as optional `[validate]` extra; lazy import preserves D-13 stdlib-only-at-runtime; PII-safe stderr templates locked (D-06-19, D-06-20) | Closes v1.1 schema validation goal without forcing a runtime dependency on default callers; gives CI/automation a fast-fail path while keeping default behavior byte-for-byte unchanged | ✓ Shipped — v1.1 (2026-05-04) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):

1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):

1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-04 after v1.1 Contract Hardening & Make.com Alignment milestone*
