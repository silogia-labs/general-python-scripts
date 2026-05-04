# Phase 6: JSON Schema Validation - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an opt-in `--validate` CLI flag to `quizify-csv-to-json-webhook/quizify_csv_ingest.py` that runs the emitted JSON envelope through a hand-written JSON Schema Draft-07 artifact at `quizify-csv-to-json-webhook/docs/webhook-schema.json`. Default behavior (no flag) is byte-for-byte unchanged. When `--validate` is passed and `fastjsonschema` is missing, the CLI prints an actionable install message and exits non-zero without a Python traceback. When `--validate` is passed and the payload violates the schema, the CLI exits non-zero with a PII-safe stderr message naming the JSON Pointer path and expected/actual types — no cell content. The schema covers contact-field name+type, locked D-05 tail-key presence via `required`, and `question-N` / `answers-N` / `answers-tags-N` triple well-formedness via `patternProperties` — without constraining question text values.

This phase ALSO introduces minimal Python packaging metadata (`quizify-csv-to-json-webhook/pyproject.toml`) so `pip install '.[validate]'` resolves the optional `fastjsonschema>=2.21.2` extra. Stdlib-only at runtime is preserved (D-13): the runtime dependency surface is empty; `fastjsonschema` is only loaded inside the validation function when `--validate` is on.

**Independent of Phase 5 missing-trio behavior.** Phase 5's `logging.warning` for absent trio columns continues to fire as designed; the schema permits empty strings on those fields per D-03, so `--validate` does NOT upgrade the WARNING into a hard fail. The two gates are orthogonal.

**Zero JS changes.** Schema validates the Python emit only — Make.com side untouched.

</domain>

<decisions>
## Implementation Decisions

### Packaging Surface (NEW pyproject.toml)

- **D-06-01 (Add minimal pyproject.toml):** Create `quizify-csv-to-json-webhook/pyproject.toml` with `[project]` metadata + `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`. README documents the install path as `pip install '.[validate]'`. Honors the locked STATE.md decision verbatim. NOT published to PyPI — local-install metadata only. D-13 (stdlib-only at runtime) preserved: no entries under `[project.dependencies]`; the only declared dependency is the optional `validate` extra.
- **D-06-02 (Build backend = flit_core):** Use `flit_core >=3.2,<4` as the build backend, mirroring `confluence-to-markdown/pyproject.toml` sibling style. Avoids introducing a new backend (hatchling/setuptools) when an existing pattern is already in the repo.
- **D-06-03 (requires-python = ">=3.9"):** Honest floor accommodating PEP 585 generic syntax (`dict[str, int]`) used in `quizify_csv_ingest.py`. `from __future__ import annotations` is present (line 4), but the floor is set to 3.9 to reflect what we actually exercise.
- **D-06-04 (Single-module project shape):** Declare `quizify_csv_ingest` as a top-level py-module via flit's `module = "quizify_csv_ingest"` (or equivalent). DO NOT restructure into a package directory. Preserves the README's "single-file CLI by design" claim and avoids touching every test import.
- **D-06-05 (Project name + version):** `name = "quizify-csv-to-json-webhook"` (matches the directory and the existing repo identity); `version = "1.1.0"` (this is the v1.1 milestone deliverable).

### Schema Artifact

- **D-06-06 (Schema location):** `quizify-csv-to-json-webhook/docs/webhook-schema.json`. Colocated with the existing `docs/webhook-quizify-format-example.json` so contract artifacts (schema + example payload) share one directory. README points operators to one place for envelope reference.
- **D-06-07 (Schema dialect + identity):** `"$schema": "http://json-schema.org/draft-07/schema#"` (explicit Draft-07 per ROADMAP success criterion #4). `"$id"` set to a repo-relative path string (e.g., `"quizify-csv-to-json-webhook/docs/webhook-schema.json"`) — no GitHub URL embedding (avoids URL rot). Schema must self-validate against the Draft-07 metaschema (VALI-03 success criterion).
- **D-06-08 (Hand-written; auto-generation forbidden):** The schema is authored by hand. Auto-generating from the example payload is explicitly out of scope per REQUIREMENTS.md OUT OF SCOPE table — would couple us to Quizify's localization decisions.
- **D-06-09 (Top-level shape: array of rows):** Schema root is `{"type": "array", "items": <row schema>}`. Matches what `convert()` writes via `json.dump(rows, ...)`. No wrapper object.

### Schema Strictness

- **D-06-10 (additionalProperties: false at row level):** The row object accepts ONLY: known contact fields + `quiz_title` + locked D-05 tail keys + the question-N/answers-N/answers-tags-N triples (via patternProperties). Any unknown top-level key fails validation. Catches contract drift early. Future fields require an intentional schema edit.
- **D-06-11 (required fields — full set):** Schema requires: `email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags`, `quiz_title`, plus the locked D-05 tail (`result-logic`, `score-category`, `score-value`, `answer-tags`, `time-to-complete`, plus `product-recommendation` if it is a current emit key — verify against `build_row` during planning). Matches what `build_row()` always emits today; no field is conditionally absent.
- **D-06-12 (Allow empty strings — type-only constraints):** All string fields are `{"type": "string"}` with NO `minLength` constraint. Accepts `""` as valid. Aligned with D-03 (empty cells emit `""` verbatim) and Phase 5 TRAIL-02 (missing trio column emits `""`). Validation succeeds on real exports.
- **D-06-13 (Triple well-formedness via patternProperties, lenient values):** Three patternProperties entries: `^question-\\d+$` → `{"type": "string"}`; `^answers-\\d+$` → `oneOf` of (array of answer-objects, string) — matches the example payload's mixed shape; `^answers-tags-\\d+$` → `{"type": "string"}`. Validates KEY NAMING + VALUE TYPE only. Does NOT enforce triple completeness (no `dependentSchemas`) — overkill for v1.1.
- **D-06-14 (Permissive on nested answer objects):** Inside the `answers-N` array element schema, do not set `additionalProperties: false`. The Quizify-side answer object shape is asymmetric (some entries have `answer_img`/`answer_tag`, some don't). We own the envelope, Quizify owns the answer content.
- **D-06-15 (Question text values UNCONSTRAINED):** `^question-\\d+$` is type-only. NEVER add `enum`/`pattern` constraints on question text values — explicitly forbidden by REQUIREMENTS.md OUT OF SCOPE table.

### Validation Wiring

- **D-06-16 (Validation timing — post-build, pre-write):** After `convert()` finishes the row loop and before the JSON write, iterate the built `list[dict]` and run `validate(row)` per item. Exit non-zero on first failure. No partial output is written on failure. Validates the actual artifact, not an intermediate.
- **D-06-17 (Lazy import inside the validation function):** `import fastjsonschema` happens INSIDE the validation function, not at module top. When `--validate` is off, `fastjsonschema` is never imported — preserving D-13 stdlib-only behavior for the default path. When `--validate` is on AND `fastjsonschema` is missing, catch `ImportError` and print the actionable install hint (D-06-19) before exiting non-zero.
- **D-06-18 (Compile once per invocation):** Call `fastjsonschema.compile(schema_dict)` once after loading the schema JSON; reuse the compiled validator across all rows in the same invocation. Schema-loading happens once per CLI run (no per-row file I/O).

### Error Reporting

- **D-06-19 (Missing-extra error template — VALI-05):** When `import fastjsonschema` fails under `--validate`, stderr message is exactly:
    ```
    ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'
    ```
    No Python traceback. Exit non-zero. Categorical message — no PII concern.
- **D-06-20 (Validation failure template — VALI-02 / T-PII-01):** On `JsonSchemaValueException`, stderr message is exactly:
    ```
    ERROR schema validation failed at <pointer>: expected <type>, got <type>
    ```
    Where `<pointer>` is the JSON Pointer extracted from the exception (categorical — schema structure, locked); first `<type>` is the schema-declared type (categorical — locked); second `<type>` is the offending Python `type(value).__name__` (categorical — `str`/`int`/`NoneType`/`list`/etc.). NO cell content, NO row index in the pointer if avoidable, NO email/phone/name. T-PII-01 preserved. Do NOT forward `JsonSchemaValueException.message` raw — it can echo the offending value.
- **D-06-21 (Exit code = 1 across all failure modes):** Validation rejection, missing-extra error, and any other CLI error all exit `1`. Standard non-zero. No three-way exit-code scheme. Documented in README under the `--validate` flag row.
- **D-06-22 (--validate × Phase-5 missing-trio: independent gates):** Phase 5's `logging.warning` for absent trio columns fires as designed in `convert()` BEFORE the row loop. Schema validation fires AFTER the row loop. With D-06-12 (allow empty strings on the trio), schema check PASSES even when the trio column was missing — operator gets BOTH signals (WARNING + successful validate). NO upgrade to LayoutError. NO `minLength: 1` on the trio. Two orthogonal gates.

### README Integration (D-11 drift test)

- **D-06-23 (Extend existing sections, no new H2):** README updates land inside existing sections only — no new top-level heading. Specifically:
    - Add `--validate` row to the existing `## CLI reference` table (Default: `off`; Description: `Validate emitted JSON against docs/webhook-schema.json (requires '[validate]' extra)`).
    - Add `pip install '.[validate]'` line under `## Quickstart` as an OPTIONAL second install step.
    - Reference `docs/webhook-schema.json` inline where the example payload is referenced.
    Keeps the 10-section README lock intact; `tests/test_readme_help_alignment.py` (D-11 drift test) passes without allowlist edits.

### Testing Strategy

- **D-06-24 (Unit-level, not subprocess-driven — Pitfall 16 carry-forward):** New tests call the validation function directly with Python data structures and the compiled schema; do NOT shell out to the CLI for validation flows. Preserves the test budget per Phase 5's Pitfall 16 carry-forward.
- **D-06-25 (Required test coverage):** (a) **Schema self-validation** — schema file passes Draft-07 metaschema validation (VALI-03). (b) **Sample passes** — running validation against the 42-row sample's emitted output succeeds (VALI-01, VALI-04). (c) **Malformed payload fails with PII-safe pointer** — deliberately remove a required tail key, assert non-zero exit and that stderr matches the D-06-20 template AND contains zero cell-content fragments (VALI-02). (d) **Missing fastjsonschema** — monkeypatch `import fastjsonschema` to raise `ImportError`, run `--validate`, assert the D-06-19 actionable message and non-zero exit, no traceback (VALI-05). (e) **README drift test passes** — `tests/test_readme_help_alignment.py` green after the README edits (VALI-06 / D-11).

### Carry-forward (locked, not re-asked)

- **D-13 (stdlib-only at runtime):** Default code path imports nothing beyond stdlib. `fastjsonschema` is gated behind `--validate` AND a lazy import. The `[project.dependencies]` array is empty.
- **T-PII-01:** Stderr never echoes cell content. Schema-driven category names are safe; row data is not.
- **D-03:** Empty cells emit `""` verbatim with no warning. Schema accepts `""`.
- **D-05 (tail-key order):** Schema's `required` covers the locked tail; pattern is enforced positionally by the existing emit logic — schema verifies presence/type only.
- **D-11 (10-section README lock):** README edits stay inside existing sections.
- **D-15:** Already retired in Phase 5; Phase 6 does not revive any positional-trailer logic.
- **Phase 5 missing-trio WARNING:** Continues to fire on header absence; `--validate` does not interact with it.
- **Auto-generation forbidden:** Schema is hand-written.
- **Question text values unconstrained:** Schema validates triple shape, never values.

### Claude's Discretion

- Exact authorship style for the schema JSON (inline `additionalProperties` vs `$defs` extraction for the answer-object schema, per-field `description` strings) — planner's call. Prefer terse and grep-able.
- Whether the validation helper lives at module top or nested inside `convert()` — planner's call.
- Test file names and class organization (`test_schema_validation.py` vs adding to existing files) — planner's call. Reuse `conftest.py` fixtures where natural.
- Whether to emit a single-line stderr message vs multi-line on validation failure — planner's call as long as the D-06-20 template content is present and PII-safe.
- Whether to thread the compiled validator through `convert()`'s signature or build it ad-hoc inside the helper — planner's call.
- The schema's optional `description` strings on properties (helpful for tools, costless to omit) — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 6: JSON Schema Validation" — phase goal, dependencies, five success criteria.
- `.planning/REQUIREMENTS.md` §"Schema Validation (VALI-XX)" — REQ text for VALI-01 through VALI-06.
- `.planning/REQUIREMENTS.md` §"Out of Scope" — auto-generation forbidden; question-text-value constraints forbidden; default-on validation forbidden; production-grade diagnostics forbidden.

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (locked tail-key order), D-11 (10-section README lock), D-13 (stdlib-only at runtime), VALI-01 entry confirming opt-in / strict-when-enabled / `pip install '.[validate]'`.
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 (PII-safe stderr); D-03 (empty cells emit `""` verbatim).
- `.planning/STATE.md` §"v1.1 locked decisions" — confirms `fastjsonschema 2.21.2` choice, opt-in default, lazy import.

### Phase 5 carry-forwards
- `.planning/phases/05-python-trailer-hardening/05-CONTEXT.md` — D-05-07 through D-05-10 (missing-trio WARNING, no positional fallback). Phase 6 schema must permit `""` on the scoring trio per D-05-08 + D-03.
- `.planning/phases/05-python-trailer-hardening/05-CONTEXT.md` `<deferred>` — explicitly raises the `--validate` × missing-trio question, resolved here as D-06-22 (independent gates, no upgrade).

### Pitfalls and known landmines
- `.planning/research/PITFALLS.md` §"Pitfall 16" — keep new tests at unit level, not subprocess-driven, to preserve the test budget. Carries into D-06-24.

### Files being edited or created
- **NEW:** `quizify-csv-to-json-webhook/pyproject.toml` — minimal flit_core project metadata + `[validate]` extra.
- **NEW:** `quizify-csv-to-json-webhook/docs/webhook-schema.json` — Draft-07 schema artifact.
- **EDITED:** `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — add `--validate` to `argparse` setup; add validation helper with lazy `import fastjsonschema`; wire post-build pre-write call inside `convert()`.
- **EDITED:** `quizify-csv-to-json-webhook/README.md` — extend `## CLI reference` table; add optional install line under `## Quickstart`. NO new sections.
- **NEW or EDITED:** test file(s) for schema self-validation, sample-pass, malformed-fail, missing-extra, README drift — placement is planner's call (D-06-25).
- **EDITED:** `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` — green after README edits; the test itself does not require modification per D-06-23.
- **POSSIBLY EDITED:** `.planning/PROJECT.md` Key Decisions table — append a row for D-13 stdlib-only-at-runtime confirmation under v1.1 (validate extra is optional, not runtime).

### Sample / verification fixture
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row sample for the success-path test.
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — example payload; reference shape for hand-writing the schema.

### Sibling reference for packaging style
- `confluence-to-markdown/pyproject.toml` — flit_core build-backend example for the new pyproject.toml in this phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `convert()` in `quizify_csv_ingest.py` (line ~310) — already builds the full row list and writes JSON. The post-build pre-write insertion point sits between the row-loop close and the `json.dump` call.
- Existing `logging.warning` PII-safe pattern (e.g., the Phase 5 missing-trio warnings) — the new `--validate` stderr messages follow the same discipline.
- `argparse` setup block — `--validate` is added as a `store_true` flag with default `False`, alongside the existing `--dry-run`, `--verbose`, `--trailer-columns`, `-o`, `--emit-json`, `--quiz-title`.
- `tests/conftest.py` fixtures (including the Phase 5 `scoring_index_map_default` fixture) — reuse for schema validation tests where row construction is needed.
- The 42-row sample at `docs/quizify-submissions.csv` and example output at `docs/webhook-quizify-format-example.json` — reference inputs for sample-passes-validation tests.

### Established Patterns
- **Pure functions returning tuples** — `classify_headers` returns a 5-tuple. The new validation helper should follow the same purity discipline: take the rows + a compiled validator and return success/raise on failure.
- **First-only / once-only side effects** — schema compile happens once per invocation, never per row.
- **Lazy / conditional imports** — already used pattern-style with `_norm_for_match` reusing `unicodedata` (stdlib). The novel pattern here is `import fastjsonschema` inside a function body, not at module top.
- **`tuple[str, ...]` typing throughout for ordered name collections** — match style; `dict[str, Any]` for the loaded schema is fine.
- **Bounds-checked positional access with `""` default** — pattern from D-05-04. Schema accepts `""` per D-06-12; no minLength constraints.
- **Single-file CLI by design** — preserved by D-06-04 (single-module py-modules, no package directory restructure).

### Integration Points
- `argparse` setup: new `--validate` flag wired into the args namespace; `args.validate` consumed inside `convert()`.
- `convert()` signature: passes `validate: bool` (or args object) through; if `validate is True`, load schema, compile validator, iterate rows post-build, raise on first violation.
- Post-build pre-write insertion: keeps `--dry-run` and `--validate` mutually composable in trivial ways — `--dry-run` already short-circuits before writing JSON, so `--dry-run --validate` is effectively a no-op for validation (rows are not built in dry-run mode); planner should confirm and document.
- `pyproject.toml` placement (`quizify-csv-to-json-webhook/pyproject.toml`, NOT repo root) — repo root already hosts other projects; per-project pyproject is the established pattern (cf. `confluence-to-markdown/pyproject.toml`).

</code_context>

<specifics>
## Specific Ideas

- Stderr templates are LOCKED VERBATIM:
    - Missing extra (D-06-19): `ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'`
    - Validation failure (D-06-20): `ERROR schema validation failed at <pointer>: expected <type>, got <type>`
- Schema `$schema` value: `http://json-schema.org/draft-07/schema#` (canonical Draft-07 metaschema URL).
- `$id` value: a repo-relative path string (e.g., `"quizify-csv-to-json-webhook/docs/webhook-schema.json"`) — no `https://` URL.
- Schema root: `{"$schema": "...", "$id": "...", "type": "array", "items": {"type": "object", "additionalProperties": false, "required": [...], "properties": {...}, "patternProperties": {...}}}`.
- README's `--validate` row sits in the existing `| Flag | Default | Description | Env var |` CLI reference table. Default column = `off`. Env var column = `—`.
- The `[validate]` extra is named exactly `validate` (lowercase, singular) — the install command in docs and the tests rely on `pip install '.[validate]'`.

</specifics>

<deferred>
## Deferred Ideas

- **AUTO-01 (HTTP POST delivery)** — v1.2 candidate. Already deferred. Phase 6 unblocks AUTO-01 by making `--validate` available; AUTO-01 will gate POSTs on validation success.
- **Production-grade JSON Schema diagnostics** — explicitly out of scope per REQUIREMENTS.md OUT OF SCOPE table. v1.1 ships JSON Pointer + expected/actual type only. Promote in a later milestone if real operator need emerges.
- **Default-on schema validation** — explicitly out of scope. Would force a v2.0 semver bump. AUTO-01 may promote to default-on within the POST path only.
- **Validating Quizify question text values** — explicitly forbidden. Question text is the join key for Make.com Module 1's `QUESTION_CONFIG`; constraining it would couple our schema to Quizify's localization decisions.
- **`dependentSchemas` triple-completeness enforcement** — considered, rejected as overkill for v1.1 (D-06-13). Capture as a future tightening if real malformed-triple bugs surface.
- **Console_scripts entry (`quizify-csv` shim)** — considered during packaging discussion; rejected as outside Phase 6 scope. Capture for v1.2 if installed-script ergonomics become important.
- **Restructuring `quizify_csv_ingest.py` into a package directory** — considered during packaging discussion; rejected (D-06-04). Capture only if/when the CLI grows beyond single-file viability.
- **Three-way exit-code scheme (1/2/3 for layout/missing-extra/validation)** — considered, rejected (D-06-21). All errors exit 1 for v1.1 simplicity.
- **`additionalProperties: false` on nested answer objects** — considered, rejected (D-06-14). Quizify owns the answer-object shape; envelope ownership stops at the row level.
- **Promoting Phase 5 missing-trio WARNING to LayoutError under `--validate`** — considered (Phase 5 deferred), rejected (D-06-22). The two gates stay independent.

</deferred>

---

*Phase: 06-json-schema-validation*
*Context gathered: 2026-05-04*
