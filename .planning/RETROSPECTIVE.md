# Retrospective: Quizify CSV → Webhook JSON

Living retrospective. Each milestone appends a section before the "Cross-Milestone Trends" footer.

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-05-03
**Phases:** 3 | **Plans:** 5 | **Tests at close:** 71

### What Was Built

- Phase 1: UTF-8-SIG CSV reader + deterministic header classification (6 contact + dynamic + 6 trailer); `--dry-run` PII-safe preview.
- Phase 2-01: Pure-function row builder + per-question tag distribution + answer shape heuristic + CLI JSON emission with PII-safe stderr logging.
- Phase 2-02: Verification harness — golden-file structural diff vs canonical example + 12 invariants over the live 42-row sample.
- Phase 3-01: Scoring trio pass-through + 4 reserved placeholders + `--quiz-title` precedence (CLI > env > "").
- Phase 3-02: 169-line operator README + automated `--help` drift smoke test.

### What Worked

- **TDD gate caught test-side bugs early.** RED commits authored failing tests before implementation; this surfaced the consent-tag off-by-one (live CSV places `Consiento` at q-20, plan diagram said q-19) and two false assumptions about strict equality between emitted shape and the example payload (`answers-3` plain string and `product-recommendation` placeholder defaults). All three were caught during verification of GREEN commits, not after merge.
- **Module-scoped fixture for invariant tests.** `tests/test_structural_invariants.py` invokes the CLI exactly once across 12 tests via a module-scoped fixture — total 0.06s for the file, mitigates T-RESOURCE-01, and gives a clean property-style suite over the live sample. Reusable pattern.
- **Negative-substring assertions for PII safety.** `tests/test_logging_pii.py` synthesizes rows with PII tokens (email, phone, free-text answer) and asserts those substrings never appear in stderr. This is more durable than positive assertions about message wording — the test stays green as long as the substantive constraint holds.
- **README↔`--help` drift smoke test.** `tests/test_readme_help_alignment.py` regex-extracts long-form flags from `argparse --help` and asserts each appears in `README.md`. Cheap (~40ms), catches the most common doc-rot pattern (new flag added without README update).
- **Single-file implementation kept the surface boring.** 427-line script + flat `tests/` directory. No premature package split. Stdlib-only at runtime.

### What Was Inefficient

- **Three test-side bugs needed fixing during GREEN verification** (consent index, strict type equality on `answers-3`, placeholder type divergence). Each was a Rule-1 bug in tests authored during RED — they passed the "tests fail before implementation" gate but encoded incorrect assumptions about the example payload. Lesson: when authoring RED tests against a sample fixture, spot-check a representative sample row with `jq` against the example before locking the assertion.
- **REQUIREMENTS.md traceability table drifted.** During execution, only WEB-04/05 and OPS-01 got their checkboxes flipped at phase close — Phase 1 and Phase 2 closed without updating CONV-01..06 / WEB-01..03 in the file, even though the SUMMARY.md files clearly cover them. Caught at milestone close (had to refresh 8 stale rows). Lesson: add a phase-transition checklist item to flip REQUIREMENTS.md checkboxes for every requirement the phase claims to ship.
- **No formal milestone audit.** `/gsd-audit-milestone` was not run before close — opted for the lighter "refresh REQUIREMENTS.md inline" path instead. Acceptable given the small surface (3 phases, 5 plans, 71 tests all passing) but a heavier project would warrant the audit.

### Patterns Established

- **D-prefixed locked decisions in CONTEXT.md** (D-01..D-15) referenced by ID throughout PLAN, SUMMARY, and tests. Made deviation tracking precise (e.g. "honors D-05 superset semantic" vs "diverges from D-07").
- **Auto-fixed deviations with Rule-N classification** in SUMMARY.md (Rule 1 = bug found during execution, Rule 3 = blocking issue requiring plan deviation). Standardized way to record "what changed and why" without bloating the plan.
- **TAG_HEADER_MAP as a single config surface.** Per-question tag routing entirely driven by a 3-entry dict in the script; no hardcoded indices in production code (only in synthetic-aligned tests where the index is the test's whole point).
- **`SCORING_PLACEHOLDERS` module constant** + `row.update(SCORING_PLACEHOLDERS)` pattern (relying on Python 3.7+ dict insertion order) — terser than four explicit assignments, identical key-order outcome, makes defaults greppable.

### Key Lessons

1. **Spot-check fixtures during RED.** Tests authored against a sample fixture should be sanity-checked with `jq` against the example before locking assertions. Three of the auto-fixed deviations could have been caught earlier this way.
2. **Update REQUIREMENTS.md at every phase close, not just milestone close.** The traceability table is meant to be a live mirror of phase progress. Letting it drift forces a refresh sweep at milestone close that's noisy and risks missing items.
3. **Negative substring assertions beat positive wording assertions for safety contracts.** PII tests asserting "stderr does NOT contain `silverpaezp@gmail.com`" stay green as the message wording evolves; "stderr matches `WARNING: row X has bad status`" would not.
4. **Module-scoped fixtures are the right scope for invariant tests.** Function-scoped means N CLI invocations for N tests; class-scoped requires unittest-style organization. Module-scoped is the sweet spot for property-style suites over a real fixture.

### Cost Observations

- Single-day milestone (2026-05-03 init through phase 3 close).
- Model mix: not tracked at this granularity — config sets `model_profile: balanced`, default workflow.
- Notable: heavy reuse of stdlib (`csv`, `html`, `json`, `os`, `argparse`, `unicodedata`) kept the dependency surface at zero.

---

## Milestone: v1.1 — Contract Hardening & Make.com Alignment

**Shipped:** 2026-05-04
**Phases:** 3 | **Plans:** 9 | **Tests at close:** 94 (+23 from v1.0)

### What Was Built

- Phase 4-01: Three bundled JS edits in one wave — `product_result` ghost deletion (CONTRACT-01), `peri-menu`→`peri_menu` underscore canon (MAKE-FIX-01), `!` negation removal in `activity_profile` (MAKE-FIX-02). All consumer-side; zero Python risk.
- Phase 4-02: `make-scripts/CONVENTIONS.md` documenting tag canonical-spelling, CONTRACT-01 verification via synthetic inline JSON (T-PII-01 preserved), and row-10/35 references for MAKE-FIX-01.
- Phase 5-01: Wave 0 preconditions — `scoring_index_map_default` conftest fixture + v1.0 default-order golden output JSON committed before any production change (Pitfall G mitigation).
- Phase 5-02: TDD name-based scoring trio binding — 5-tuple `classify_headers`, name-keyed `build_row(scoring_index_map=...)`, PII-safe WARNING for missing trio columns, 14 test_row_builder call-site updates synchronized atomically with the signature change.
- Phase 5-03: TRAIL-03 default-order regression test against the committed v1.0 golden + README/MILESTONES updates removing all "scoring stays positional" caveats (Pitfall F).
- Phase 6-01: Hand-written Draft-07 schema (`docs/webhook-schema.json`) + `TestSchemaSelfValidation` proves the schema is well-formed independently of any CLI wiring.
- Phase 6-02: Minimal flit_core PEP 621 `pyproject.toml` with `validate = ["fastjsonschema>=2.21.2"]` as opt-in extra; `[project.dependencies]` empty (D-13 preserved).
- Phase 6-03: `--validate` argparse flag + `_run_schema_validation` (lazy import + compile-once) + `_format_validation_error` (categorical-only PII-safe JSON-Pointer stderr); 11 new tests including 3 PII-safe synthetic-mutation tests.
- Phase 6-04: Operator README documents `--validate`, the `[validate]` install path, and the schema location, all within the D-11 ten-section lock.

### What Worked

- **Wave 0 / Wave 1 / Wave 2 sequencing for Phase 5.** Plan 05-01 committed the v1.0 golden fixture and conftest fixture *before* Plan 05-02 changed `classify_headers`. This let the TRAIL-03 regression test in Plan 05-03 compare post-change CLI output against an immutable pre-change baseline — proving zero behavioral change for default callers wasn't a circular argument. Pitfall G was identified during planning and mitigated structurally rather than reactively.
- **Atomic 5-tuple signature change in Plan 05-02.** Rather than threading `scoring_index_map` through as a kwarg with default value (which would have left old callers silently passing stale data), `classify_headers` was promoted from 3-tuple to 5-tuple in the same commit that updated all 14 `build_row` call sites in the test suite. RED commits authored failing tests against the new signature first, so the GREEN refactor was mechanically driven.
- **Schema-first / wire-second for Phase 6.** Plans 06-01 (schema artifact) and 06-02 (packaging) ran in parallel with no dependency on each other; Plan 06-03 (CLI wiring) only started once both artifacts existed and self-validated. This kept the schema's correctness independent of CLI behavior — a regression in the schema would fail `TestSchemaSelfValidation` before any user-facing flag was touched.
- **Lazy-import preserves D-13 cleanly.** `import fastjsonschema` lives only inside `_run_schema_validation`'s body, after the schema-path check. Default invocations never load the optional dep; missing-extra paths fail with a locked D-06-19 verbatim string before any Python ImportError stack would surface. Tests assert no traceback ever appears.
- **PII-safe by construction, not by review.** `_format_validation_error` accepts only the `JsonSchemaValueException` instance and reads `.path` (JSON Pointer string) — it has no syntactic access to the row dict at all. Negative substring assertions over a synthetic email/phone/free-text mutation prove the contract holds.
- **Cross-phase integration check (`v1.1-INTEGRATION-CHECK.md`)** as a milestone-close artifact caught nothing new but provided durable evidence — required emit-key list cross-referenced against schema `required` list cross-referenced against JS reads. Cheap to write at close, expensive to reconstruct later.
- **The milestone audit (`/gsd-audit-milestone`) was actually run this time.** Caught the stale REQUIREMENTS.md checkboxes and stale `nyquist_compliant: false` draft markers — both administrative, no behavioral gap. Lesson from v1.0 retrospective applied.

### What Was Inefficient

- **REQUIREMENTS.md traceability checkboxes drifted again.** Same v1.0 lesson, same v1.1 outcome: TRAIL-01/02/03 and VALI-01..06 stayed `[ ] Pending` despite passing tests, until the milestone audit caught it. The "flip checkboxes at phase close, not milestone close" lesson from v1.0 was acknowledged but not enforced — no automation, no checklist gate. Worth promoting to a hook or a phase-transition CLI step.
- **Two `VALIDATION.md` frontmatters still mark `nyquist_compliant: false` despite green coverage.** Phases 5 and 6 both have green test counts that meet phase requirements, but the frontmatter was authored as `draft` at start-of-phase and never flipped. Marker is stale, not load-bearing — but it confused the audit until the file body was inspected.
- **Worktree branch lacked Wave 0 commits (Phase 4 deviation).** A worktree spawned for a Phase 4 plan didn't include Plan 04-01's earlier commits, requiring a Rule-3 blocking deviation to recover. Worktree spawning currently doesn't auto-rebase off the latest in-phase commits — a known sharp edge in the executor.
- **Three reverted-then-reapplied commits in Phase 6 history** (`f2b3178` test → `2348609` revert → `3255320` test re-add): a TDD RED commit landed, was reverted to fix file location, then re-applied. Net-neutral but noisy in the git log. Could be avoided by spec-checking RED test file paths against the plan before commit.

### Patterns Established

- **5-tuple atomic signature change with synchronized call-site updates.** `classify_headers` going from 3 to 5 fields in one commit, with 14 test call sites updated in the same commit, sets the precedent: never thread new state through old signatures with defaults — promote the signature.
- **Wave 0 fixture commits as preconditions for downstream regression tests.** Plan 05-01's role was *only* to land the v1.0 golden output JSON before any production code changed. This pattern is reusable any time a milestone needs to prove "no behavioral change" for a subset of callers — commit the immutable baseline first, change behavior second, regress against the baseline third.
- **`%r`-formatted PII-safe `logging.warning` template** (D-05-08). `logging.warning("missing canonical scoring trio column: %r", canonical_name)` — `%r` quotes the canonical (categorical) value but `canonical_name` is by construction one of `{"result-logic","score-category","score-value"}`, never row content. Locked verbatim per D-05-08.
- **Synthetic inline-JSON fixtures for JS verification (`make-scripts/CONVENTIONS.md`).** Verification of JS contract fixes uses a hand-written `{ "first-name": "Test", "email": "test@example.com", ... }` literal in the doc, never a hand-edit of `quizify-submissions.csv` (which would invite copy-pasting real PII into version control). Pitfall #12 + T-PII-01 carry-forward.
- **D-{N}-{N} hierarchical decision IDs.** Phase 6 introduced D-06-01 through D-06-25 — sub-numbering inside a per-phase decision log. Makes "which phase introduced this decision" greppable without hunting through commit messages. Worth keeping for v1.2.

### Key Lessons

1. **Promote checkbox-flipping to a phase-transition gate, not a milestone-close audit step.** Same lesson v1.0 surfaced; v1.1 hit it again. The mitigation is mechanical, not behavioral — a `gsd-sdk` hook on phase close that scans the SUMMARY.md `provides:` list and refreshes REQUIREMENTS.md rows would close it.
2. **VALIDATION.md frontmatter `status: draft` should auto-flip to `final` when all `nyquist_compliant` gates pass.** Currently human-authored at phase start and never revisited. Either auto-update or remove the field — leaving it stale degrades audit signal.
3. **Wave 0 preconditions are the cheapest way to prove "no behavioral change."** Land the baseline as a committed fixture *before* the change. Without this, regression tests become tautologies ("we generated this golden after the change, so the change matches it").
4. **Lazy-import + locked verbatim error templates is the cleanest way to ship optional extras.** Users who don't install the extra get an actionable message *and* zero ImportError pollution. The locked template (D-06-19) tested verbatim across 3 test cases ensures the message itself doesn't drift.
5. **Run `/gsd-audit-milestone` before close, every milestone.** v1.0 skipped it ("small surface, refresh REQUIREMENTS.md inline"); v1.1 ran it and caught real (administrative) drift. The audit cost is low; the cost of shipping with stale traceability is reputation.

### Cost Observations

- 2-day milestone (2026-05-03 evening through 2026-05-04 evening); 71 commits over the range.
- Nine plans across three phases (avg 3.0 plans/phase, up from v1.0's 1.67).
- New runtime dependencies: 0 (the `[validate]` extra is opt-in; default install footprint unchanged).
- New test count: +23 (71 → 94), all sub-second.
- Notable: parallel waves in Phase 6 (Plans 06-01 and 06-02 ran independently) collapsed what would have been a 3-day milestone into 2.

---

## Cross-Milestone Trends

| Trend | v1.0 | v1.1 | v1.2 |
|-------|------|------|------|
| Tests at close | 71 | 94 | — |
| Plans per phase (avg) | 1.67 | 3.0 | — |
| Auto-fixed deviations | 5 | 3+ | — |
| New runtime dependencies | 0 | 0 (opt-in extra only) | — |
| Phases in milestone | 3 | 3 | — |
| Milestone duration | 1 day | 2 days | — |
| Audit run pre-close? | no | yes (passed) | — |

**Recurring pattern (2 consecutive milestones):** REQUIREMENTS.md traceability checkboxes drift during execution and require a refresh sweep at milestone close. Lesson 1 above is the structural fix.
