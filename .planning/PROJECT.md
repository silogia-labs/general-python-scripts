# Quizify CSV → Webhook JSON

## What This Is

This initiative lives inside the `general-python-scripts` utilities repository. It ships a small Python helper (`quizify-csv-to-json-webhook/quizify_csv_ingest.py`) that turns Quizify.io CSV exports (from https://app.quizify.io) into JSON arrays shaped like `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`, so integrations that expect webhook-style records can consume exports without manual rework. The JSON is consumed by a Make.com (Integromat) automation pipeline; the two JS modules in `quizify-csv-to-json-webhook/make-scripts/` (`quizify-mapping.js`, `score-calculations.js`) are co-owned consumer surfaces of this initiative as of v1.1. v1.0 (2026-05-03) delivered the full CSV→JSON pipeline; v1.1 hardens the contract end-to-end and aligns the Make.com side.

## Core Value

Each CSV submission row becomes one webhook-compatible JSON object with correct contact fields, ordered `question-N` / `answers-N` / `answers-tags-N` keys, scoring fields, and tags — including sensible behavior when Quizify omits answer IDs (omit, not invent) or encodes characters as HTML entities (decoded uniformly).

## Current State

**Active: v1.1 Contract Hardening & Make.com Alignment (planning, started 2026-05-03)** — see Current Milestone section below.

**Shipped: v1.0 MVP (2026-05-03)** — see `.planning/MILESTONES.md` and `.planning/milestones/v1.0-ROADMAP.md` for full details.

- 71 tests passing (1.09s) across layout, row-builder, CLI emission, PII logging, golden-file structure, structural invariants, quiz-title precedence, and README/`--help` drift.
- Stdlib-only runtime (Python 3.7+); pytest as the only dev dependency.
- Single-file implementation: `quizify_csv_ingest.py` (427 lines) + 169-line operator README.
- CLI surface: `csv_path` positional + `--dry-run`, `-v`/`--verbose`, `--trailer-columns`, `-o`/`--output`, `--emit-json`, `--quiz-title` (with `$QUIZIFY_QUIZ_TITLE` env fallback).

## Current Milestone: v1.1 Contract Hardening & Make.com Alignment

**Goal:** Lock down the JSON contract between the Python CLI and the Make.com automation by adding opt-in strict JSON Schema validation, eliminating positional mis-bind risk in trailer scoring, reconciling the field-name mismatch with `quizify-mapping.js`, and fixing two correctness bugs in the now-in-scope Make.com JS modules.

**Target features:**

- **VALI-01** — Opt-in JSON Schema validation (default off; strict-when-enabled via `--validate` flag, exits non-zero on schema violation). Schema validates envelope structure (contact fields, locked tail order, presence of `question-N`/`answers-N`/`answers-tags-N` triples), not question text values.
- **TRAIL-01** — Name-based scoring lookup for `--trailer-columns` (replaces positional `[0..2]`); preserves PII-safe stderr logging.
- **CONTRACT-01** — Fix `quizify-mapping.js:102` to read `record["product-recommendation"]` (aligns with locked D-05 key order; resolves silent-null bug where Module 1 expected a key the CLI never emits).
- **MAKE-FIX-01** — Reconcile peri-menopause tag mismatch between `quizify-mapping.js` (emits `peri_menu`) and `score-calculations.js` (checks `peri-menu`); fix inverted `activity_profile` condition at `score-calculations.js:247-250`.

**Deferred (post-v1.1):**

- **AUTO-01** — HTTP POST delivery mode (v1.2 candidate; depends on VALI-01 being in place).
- **STREAM-01** — Streaming/NDJSON output for >50k rows (T-RESOURCE-01).
- Make.com JS cosmetic items (`Reomoto` typo at line 157, dead-code initialization at line 217).
- Local JS test harness (deferred — manual verification only in v1.1).

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

### Active

(See `.planning/REQUIREMENTS.md` for the canonical v1.1 REQ-ID list once written. v1.1 target categories: Schema Validation, Trailer Hardening, Contract Reconciliation, Make.com JS Fixes.)

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
- Codebase: ~2,070 LOC Python (script + tests) + 169-line operator README, all under `quizify-csv-to-json-webhook/`. Stdlib-only at runtime.
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
*Last updated: 2026-05-03 — v1.1 Contract Hardening milestone started (post v1.0 MVP)*
