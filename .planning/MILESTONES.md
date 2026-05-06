# Milestones

History of shipped versions for the Quizify CSV → Webhook JSON initiative inside `general-python-scripts`.

---

## v1.2 Delivery & Make.com Hygiene — 2026-05-06

**Delivered:** Closed the v1.1 deferred bucket — direct webhook delivery, large-file streaming, and Make.com hygiene with a zero-dep regression net. Operators can now POST validated payloads directly to a Make.com webhook over HTTPS in a single shot (`--post-url`, gated on `--validate`, PII-safe categorical errors), emit NDJSON line-delimited output with per-row schema validation and atomic file writes (`--ndjson`), and trust the two co-owned Make.com JS modules behind a `node:test` regression net covering CONTRACT-01 + MAKE-FIX-01/02 + MAKE-COSMETIC-01/02. `convert()` was rebuilt around an `iter_rows()` generator and a pluggable `_Sink` Protocol with byte-identical default output (TRAIL-03 green).

**Stats:**

- Phases: 4 (Refactor Scaffolding / STREAM-01 NDJSON Output / AUTO-01 HTTP POST Delivery / Make.com Hygiene & Node Test Harness)
- Plans: 9 (all complete)
- Requirements: 16/16 (REFACTOR=1, STREAM=4, AUTO=6, MAKE=5)
- Tests: pytest 163 passed / 4 skipped (Pitfall 8-E pre-authorized) + `node --test` 9 passed / 0 failed
- Timeline: 2026-05-05 → 2026-05-06

**Key accomplishments:**

- **REFACTOR-01** — `convert()` rebuilt around `iter_rows()` generator + `_Sink` Protocol (`_StdoutSink`/`_FileSink`/`_NdjsonFileSink`/`_ValidatingSink`/`_HttpPostSink`); default-flag output byte-identical to v1.1 golden fixture (TRAIL-03 carry-forward green).
- **STREAM-01..04** — `--ndjson` file-mode output with `\n` line separator, per-row `schema["items"]` validation (lazy `fastjsonschema`, compile-once, row-prefixed JSON Pointer), atomic `os.replace()` promotion, SIGINT-safe (no partial file at target).
- **AUTO-01..06** — `--post-url` HTTPS-only single-shot POST with mandatory `--validate` gate, repeatable `--header` (CRLF rejected at argparse), `--timeout` (default 30, exit 3 on stall), `_NoRedirectHandler` blocks cross-host redirects, `_log_http_failure` chokepoint emits categorical-only stderr (status + reason class + body byte count, never response body or URL).
- **MAKE-COSMETIC-01/02** — `Reomoto`→`Remoto` typo fix + dead `profile = "profile_base"` initializer removal, both locked behind `node:test` regression cases.
- **MAKE-TEST-01..03** — Zero-dep `node:test` harness; `mapRecord(record)` exposed as pure function on both modules with `module.exports` guarded by `typeof module !== "undefined"` (deployed Make.com files paste in unchanged); `globalThis` snapshot test detects accidental global writes; `pyproject.toml` `norecursedirs` + `make-scripts/.gitignore` keep Python collection clean.
- **CI** — `.github/workflows/ci.yml` runs parallel `pytest` + `make-scripts-test` jobs on push/PR.
- **Security gates (CI grep)** — 0 `CERT_NONE`/`_create_unverified_context`/`verify=False`; exactly 1 `ssl.create_default_context()`; exactly 1 `self._opener.open(`; exactly 1 `Request(...method="POST")`; 0 `shutil.move`/`os.rename`; 0 `import requests` (D-13 stdlib-only-at-runtime preserved).

**Tech debt carried forward:**

- Phase 9 SUMMARY frontmatter missing `requirements-completed` field (cosmetic; manual verification step required by milestone audit's 3-source matrix). Recorded in v1.2-MILESTONE-AUDIT.md.

**Deferred to v1.3+:**

- NDJSON+POST cross-product (partial-success semantics need design)
- `--retry N` exponential backoff (Make.com idempotency unverified)
- `--idempotency-key` (Make.com idempotency-key support unverified)
- `$QUIZIFY_WEBHOOK_URL` / `--post-url-env` (defer unless operator pain reported)

---

## v1.1 Contract Hardening & Make.com Alignment — 2026-05-04

**Delivered:** Locked the JSON contract end-to-end between the Python CLI and the Make.com automation pipeline. Three live Make.com correctness bugs fixed in the now-co-owned JS modules; positional trailer-cell scoring lookup retired in favor of NFC+casefold name-based binding (D-15 retired); opt-in JSON Schema Draft-07 validation shipped via a new `--validate` flag backed by `fastjsonschema` as an optional extra (runtime stays stdlib-only by default).

**User-facing change (TRAIL-03 bugfix):** Operators passing `--trailer-columns` in a non-default order previously saw silently mis-bound scoring fields — `result-logic`, `score-category`, and `score-value` always read trailer cell positions `[0]`, `[1]`, `[2]` regardless of the canonical column name at that position. Phase 5 binds the scoring trio by canonical column name, so any valid `--trailer-columns` ordering produces correctly-bound output. Default-order callers see no behavioral change (verified by `tests/test_default_order_regression.py` against a committed v1.0 golden fixture). Missing trio columns emit `""` plus a PII-safe stderr `WARNING` naming the absent canonical column.

**Stats:**

- Phases: 3 (Make.com JS Contract Fixes / Python Trailer Hardening / JSON Schema Validation)
- Plans: 9 (all complete)
- Tests at close: 94 passing in 1.28s (up from 71 at v1.0 close → +23 tests)
- Files changed: 59 (+17,349 / −92)
- Commits: 71 in v1.0..HEAD range
- Timeline: 2026-05-03 → 2026-05-04 (2-day milestone)

**Key accomplishments:**

1. **Phase 4 — JS contract fixes (CONTRACT-01, MAKE-FIX-01..03):** Deleted `product_result` ghost line in `quizify-mapping.js`; replaced `peri-menu` → `peri_menu` (underscore canon) at `score-calculations.js:213` so the `peri_menopause_menopause` life-stage classification fires; removed `!` negation in `activity_profile` so the entire respondent population stops being mis-classified; new `make-scripts/CONVENTIONS.md` documents tag canonical-spelling, CONTRACT-01 verification via synthetic inline-JSON fixture (T-PII-01 preserved), and the row-10/row-35 references for MAKE-FIX-01.
2. **Phase 5 — Trailer hardening (TRAIL-01, TRAIL-02):** Refactored `classify_headers` to a 5-tuple returning `(prefix, dynamic, trailer_raw, scoring_index_map, missing_trio_names)`; rewrote `build_row` to bind the scoring trio by NFC+casefold canonical-name lookup against `scoring_index_map`; emits `""` plus a PII-safe `logging.warning("missing canonical scoring trio column: %r", canonical_name)` for absent columns (D-05-08 locked template). 14 `test_row_builder` call sites synchronized; new `TestScoringIndexMap` / `TestScrambledTrailer` / `TestMissingColumnWarning` classes added.
3. **Phase 5 — Default-order regression lock (TRAIL-03):** New `tests/test_default_order_regression.py` replays the CLI against `docs/quizify-submissions.csv` and structurally compares against a committed v1.0 golden fixture (`tests/fixtures/v1.0_default_order_output.json`) — proves zero behavioral change for unflagged callers. Operator README updated to remove "scoring stays positional" caveats; `D-15` row in PROJECT.md Key Decisions table marked retired.
4. **Phase 6 — Schema artifact + packaging (VALI-03, VALI-05):** Hand-written Draft-07 schema at `quizify-csv-to-json-webhook/docs/webhook-schema.json` covers contact fields by name+type, locked D-05 tail-key presence via `required`, and `question-N`/`answers-N`/`answers-tags-N` triple well-formedness via `patternProperties` (without constraining question text values). `pyproject.toml` adds minimal flit_core PEP 621 metadata with `validate = ["fastjsonschema>=2.21.2"]` as an optional extra; `[project.dependencies]` stays empty (D-13 stdlib-only-at-runtime preserved via lazy import inside the validation helper).
5. **Phase 6 — `--validate` flag end-to-end (VALI-01, VALI-02, VALI-04):** New `--validate` argparse flag (default off, opt-in only); `_run_schema_validation` lazy-imports fastjsonschema and compiles the schema once per invocation; `_format_validation_error` produces categorical-only PII-safe stderr output identifying the JSON Pointer path (no cell content leaked); `--validate` exits 0 on the bundled 42-row sample with byte-identical stdout to default invocation; missing-extra path exits 1 with locked D-06-19 verbatim message and no traceback. 11 new tests across `TestSamplePasses` / `TestValidationFailurePIIsafe` / `TestMissingExtra` (3 PII-safe tests with synthetic-fixture mutation).
6. **Phase 6 — README documentation lock (VALI-06):** Operator README extended (within D-11 ten-section lock) to document the `--validate` CLI flag, the `pip install '.[validate]'` extra installation step, and the schema file path. `tests/test_readme_help_alignment.py` (D-11 drift test, 2/2) green after additions.

**Cross-phase integration verified** (per `.planning/v1.1-INTEGRATION-CHECK.md` and milestone audit):

- P5→P6 emit/schema alignment: schema accepts `""` on trio fields (TRAIL-02 fallback); live `--validate` against 42-row sample exits 0 with 140,665 bytes byte-identical to default.
- P5→P4 hyphen-key contract: Python emits `record["product-recommendation"]`-style hyphenated keys; JS reads same at `quizify-mapping.js:102`.
- P4↔P5 tag spelling: `peri_menu` underscore matches across `score-calculations.js:213` and `quizify-mapping.js:166`.

**Deferred to v1.2+** (tracked in archived REQUIREMENTS.md and PROJECT.md):

- AUTO-01 — HTTP POST delivery (gates on VALI-01 success)
- STREAM-01 — NDJSON / streaming output for >50k-row CSVs
- MAKE-COSMETIC-01 — `Reomoto` typo at `score-calculations.js:157`
- MAKE-COSMETIC-02 — dead `profile = "profile_base"` initializer at `score-calculations.js:217`
- MAKE-TEST-01 — Node.js test harness for `make-scripts/` (gated on JS LOC growth)

**Decisions retired:**

- **D-15** (positional trailer indexing rationale) — retired by TRAIL-01 in favor of NFC+casefold name-based binding. PROJECT.md Key Decisions D-15 row updated.

**Audit:** ✓ passed (`.planning/milestones/v1.1-MILESTONE-AUDIT.md`) — 13/13 requirements satisfied, cross-phase integration clean, all E2E flows green. Tech debt is administrative-only (stale draft markers in two VALIDATION.md frontmatters; coverage is real).

**Archived:**

- `.planning/milestones/v1.1-ROADMAP.md` — full phase details + success criteria + decisions
- `.planning/milestones/v1.1-REQUIREMENTS.md` — 13/13 v1.1 requirements with shipped outcomes
- `.planning/milestones/v1.1-MILESTONE-AUDIT.md` — passed audit
- `.planning/milestones/v1.1-phases/` — raw execution history (CONTEXT, RESEARCH, PLAN, VALIDATION, SUMMARY, VERIFICATION per phase)

**Tag:** `v1.1`

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
