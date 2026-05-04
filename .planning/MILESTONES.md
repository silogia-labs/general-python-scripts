# Milestones

History of shipped versions for the Quizify CSV → Webhook JSON initiative inside `general-python-scripts`.

---

## Current Milestone: v1.1 Contract Hardening & Make.com Alignment (in progress)

### Phase 5: Python Trailer Hardening — TRAIL-01 / TRAIL-02 / TRAIL-03 (shipped)

**User-facing change (TRAIL-03 bugfix):** Operators passing
`--trailer-columns` in a non-default order previously saw silently
mis-bound scoring fields — `result-logic`, `score-category`, and
`score-value` always read trailer cell positions `[0]`, `[1]`, `[2]`
regardless of the canonical column name at that position. Phase 5 binds
the scoring trio by canonical column name (NFC + casefold equality), so
any valid `--trailer-columns` ordering produces correctly-bound output.
Default-order callers see no behavioral change (verified by the
`tests/test_default_order_regression.py` regression test against a v1.0
output baseline). Missing trio columns emit an empty string for the
corresponding output key plus a PII-safe stderr `WARNING` naming the
absent canonical column.

**Decisions retired:** D-15 (positional trailer indexing rationale) is
retired in favor of name-based binding. The PROJECT.md Key Decisions
table's D-15 row is updated to "Retired by TRAIL-01 (Phase 5, v1.1)".

---

## v1.0 MVP — 2026-05-03

**Delivered:** A stdlib-only Python CLI (`quizify-csv-to-json-webhook/quizify_csv_ingest.py`) that converts Quizify.io CSV exports into webhook-shaped JSON arrays, with deterministic column classification, PII-safe stderr logging, scoring metadata pass-through, `--quiz-title` precedence handling, and an operator README guarded by an automated `--help` drift smoke test.

**Stats:**

- Phases: 3 (CSV ingestion / Core webhook mapping / Scoring metadata & packaging)
- Plans: 5 (all complete)
- Tests: 71 passing in 1.09s
- LOC (script + tests + README): ~2,239
- Files changed: 61 (+12,112 insertions)
- Timeline: 2026-05-03 (single-day milestone, init through phase 3 close)
- Git range: `e6bbe64` (project init) → `bf7a203` (phase 3 state record)

**Key accomplishments:**

1. UTF-8-SIG CSV reader with deterministic header classification (6 contact + dynamic + 6 trailer); `--dry-run` preview that does not leak cell content to stderr.
2. Pure-function row builder mapping contact/status/answers + per-question tag distribution via NFC+casefold substring match (`TAG_HEADER_MAP`); HTML entities decoded uniformly via `html.unescape`.
3. PII-safe stderr logging (T-PII-01) verified by negative substring assertions against email/phone/free-text patterns from the live sample.
4. Verification harness: golden-file structural diff vs canonical example payload + 12 invariants over the live 42-row sample using a module-scoped fixture (single CLI invocation; T-RESOURCE-01 mitigation).
5. Scoring trio (`result-logic`/`score-category`/`score-value`) pass-through + 4 reserved placeholder keys (`product-recommendation`, `product-link-type`, `title`, `type-page-url`) emitted in locked D-05 tail order; `--quiz-title` flag with `$QUIZIFY_QUIZ_TITLE` env fallback and `""` default, decoded via `html.unescape`.
6. 169-line operator README per locked 10-section structure (D-11) + automated drift test (`tests/test_readme_help_alignment.py`) that catches future flag additions without doc updates.

**Archived:**

- `.planning/milestones/v1.0-ROADMAP.md` — full phase details + decisions + deferred items
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 11/11 v1 requirements with shipped outcomes
- `.planning/milestones/v1.0-phases/` — raw execution history (CONTEXT, RESEARCH, PLAN, SECURITY, VALIDATION, SUMMARY, VERIFICATION per phase)

**Tag:** `v1.0`
