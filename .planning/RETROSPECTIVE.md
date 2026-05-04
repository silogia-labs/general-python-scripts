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

## Cross-Milestone Trends

(First milestone — trends will emerge at v1.1+.)

| Trend | v1.0 | v1.1 | v1.2 |
|-------|------|------|------|
| Tests at close | 71 | — | — |
| Plans per phase (avg) | 1.67 | — | — |
| Auto-fixed deviations | 5 | — | — |
| New runtime dependencies | 0 | — | — |
