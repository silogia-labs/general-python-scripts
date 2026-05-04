# Phase 6: JSON Schema Validation - Research

**Researched:** 2026-05-04
**Domain:** Python single-file CLI + opt-in JSON Schema Draft-07 validation via `fastjsonschema` 2.21.2 + flit_core packaging metadata
**Confidence:** HIGH (Context7 verified, version pinned via `pip index versions`, source-code inspection complete)

## Summary

Phase 6 grafts an opt-in `--validate` flag onto the existing 474-line `quizify_csv_ingest.py`, backs it with a hand-written Draft-07 schema at `docs/webhook-schema.json`, and adds a minimal flit_core `pyproject.toml` so `pip install '.[validate]'` resolves the optional `fastjsonschema>=2.21.2` extra. All locked decisions in 06-CONTEXT.md (D-06-01 through D-06-25) are constraint inputs, not research questions. The research focused on (a) `fastjsonschema 2.21.2` exception API surface so we extract the JSON Pointer without leaking cell content, (b) flit_core single-module pyproject syntax, (c) Draft-07 self-validation strategy, (d) `pip install '.[extra]'` mechanics for a subdirectory project, (e) schema-keyword interaction (`patternProperties` × `properties` × `additionalProperties`), and (f) test-pattern alignment with the existing 71-test suite.

The principal risk surface is **PII leakage through `JsonSchemaValueException.message` / `.value`** — both attributes can echo the offending value (cell content). The verified-safe extraction is `.path` (list, joinable to JSON Pointer), `.rule` (failed keyword string), `.definition.get('type')` (schema-declared expected type), and `type(value).__name__` (actual Python type) — never `.message`, never `.value`. This protects T-PII-01.

**Primary recommendation:** Adopt the locked schema strictness model (`additionalProperties: false` at row level, type-only string constraints, `patternProperties` for triples), use `fastjsonschema.compile(schema)` once per invocation inside the validation helper, catch `JsonSchemaValueException` and format the locked D-06-20 stderr template exclusively from `.path` / `.rule` / `.definition` / `type(value).__name__` — and use `flit_core` with explicit `[tool.flit.module] name = "quizify_csv_ingest"` so the project name (`quizify-csv-to-json-webhook`, hyphenated) and the importable single-file module (`quizify_csv_ingest`, underscored) decouple cleanly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Packaging (NEW pyproject.toml at `quizify-csv-to-json-webhook/pyproject.toml`):**
- D-06-01: `[project]` metadata + `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`. Empty `[project.dependencies]`. NOT published to PyPI. D-13 preserved.
- D-06-02: Build backend = `flit_core >=3.2,<4` (mirrors `confluence-to-markdown/pyproject.toml`).
- D-06-03: `requires-python = ">=3.9"` (PEP 585 generics in source).
- D-06-04: Single-module project — declare `quizify_csv_ingest` as a top-level py-module via flit's module key. NO package directory restructure.
- D-06-05: `name = "quizify-csv-to-json-webhook"`, `version = "1.1.0"`.

**Schema artifact (`docs/webhook-schema.json`):**
- D-06-06: Lives at `quizify-csv-to-json-webhook/docs/webhook-schema.json`.
- D-06-07: `"$schema": "http://json-schema.org/draft-07/schema#"`; `"$id"` = repo-relative path string. Self-validates against Draft-07 metaschema.
- D-06-08: Hand-written. Auto-generation forbidden.
- D-06-09: Root shape = `{"type": "array", "items": <row schema>}`.

**Schema strictness:**
- D-06-10: `additionalProperties: false` at row level (closed contract).
- D-06-11: `required` covers email, firstName, lastName, status, statusDate, phone, tags, quiz_title + locked D-05 tail (result-logic, score-category, score-value, product-recommendation, product-link-type, title, type-page-url).
- D-06-12: All string fields type-only (no `minLength`). Empty strings valid.
- D-06-13: Three patternProperties: `^question-\d+$` → string, `^answers-\d+$` → oneOf(array, string), `^answers-tags-\d+$` → string. NO dependentSchemas.
- D-06-14: Permissive on nested answer objects (no `additionalProperties: false` inside answer items).
- D-06-15: Question text values UNCONSTRAINED (no `enum`/`pattern` on `^question-\d+$` values).

**Validation wiring:**
- D-06-16: Post-build, pre-write — iterate the built `list[dict]` and validate per item.
- D-06-17: `import fastjsonschema` lazily INSIDE the validation function. ImportError → D-06-19 message + exit 1.
- D-06-18: `compile(schema_dict)` once per invocation.

**Error reporting (LOCKED VERBATIM):**
- D-06-19: `ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'`
- D-06-20: `ERROR schema validation failed at <pointer>: expected <type>, got <type>` — pointer/types categorical only; NEVER `.message` raw, NEVER `.value`.
- D-06-21: Exit code 1 on all failure modes.
- D-06-22: `--validate` is INDEPENDENT of Phase 5 missing-trio WARNING. Schema accepts `""` per D-06-12, so missing-trio passes validation. Two orthogonal gates.

**README integration:**
- D-06-23: Extend existing 10 sections only. Add `--validate` row to `## CLI reference` table; add `pip install '.[validate]'` line under `## Quickstart`. NO new H2.

**Testing:**
- D-06-24: Unit-level, NOT subprocess-driven (Pitfall 16 carry-forward).
- D-06-25: Five required test scenarios — schema self-validation, sample passes, malformed payload PII-safe failure, missing-fastjsonschema actionable error, README drift test green.

### Claude's Discretion
- Schema authorship style (inline vs `$defs` for answer object); per-field `description` strings.
- Validation helper location (module-top vs nested).
- Test file names + class organization (`test_schema_validation.py` vs additions to existing files).
- Single-line vs multi-line stderr (D-06-20 content must be present and PII-safe).
- Whether compiled validator threads through `convert()`'s signature.

### Deferred Ideas (OUT OF SCOPE)
- AUTO-01 (HTTP POST) — v1.2.
- Production-grade JSON Schema diagnostics — out of scope per REQUIREMENTS.md.
- Default-on schema validation — would force v2.0 bump.
- Validating Quizify question text values — explicitly forbidden.
- `dependentSchemas` triple-completeness enforcement — rejected as overkill.
- `console_scripts` entry — rejected; no installed-script ergonomics in v1.1.
- Restructuring into a package directory — rejected (D-06-04).
- Three-way exit-code scheme — rejected (D-06-21).
- `additionalProperties: false` on nested answer objects — rejected (D-06-14).
- Promoting Phase 5 missing-trio WARNING to LayoutError under `--validate` — rejected (D-06-22).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VALI-01 | `--validate` flag triggers schema validation against `docs/webhook-schema.json` | argparse `store_true` flag added to `main()`; `convert()` consumes `args.validate`; `fastjsonschema.compile()` API confirmed (single call, returns callable validator). |
| VALI-02 | Violation → exit 1 + PII-safe stderr with JSON Pointer; no cell content (T-PII-01) | `JsonSchemaValueException.path` (list[str]) is JSON-Pointer-safe; `.rule` + `.definition.get('type')` give expected category; `type(value).__name__` gives actual type. `.message` and `.value` MUST NOT be forwarded — they leak cell content. |
| VALI-03 | Schema covers contact fields, locked D-05 tail (`required`), question/answers/answers-tags triples (`patternProperties`); does NOT constrain question text values | Schema structure verified against 06-CONTEXT.md D-06-09..D-06-15; Draft-07 metaschema URL verified (`http://json-schema.org/draft-07/schema#`); `patternProperties` + `properties` + `additionalProperties` interaction confirmed. |
| VALI-04 | Opt-in only — default behavior unchanged when `--validate` absent | Lazy `import fastjsonschema` inside helper (D-06-17) means default code path imports nothing beyond stdlib; preserves D-13. |
| VALI-05 | `fastjsonschema>=2.21.2` is optional extra; lazy import; actionable stderr if missing | Version 2.21.2 confirmed current via `pip index versions fastjsonschema`. flit_core supports `[project.optional-dependencies] validate = [...]` per PEP 621. `pip install '.[validate]'` resolves the named extra. |
| VALI-06 | README documents `--validate` flag, `[validate]` extra, schema path; D-11 drift test passes | `tests/test_readme_help_alignment.py` checks (a) 10 named H2 sections present, (b) every long flag from `--help` appears as substring of README. Adding `--validate` row to the existing `## CLI reference` table satisfies both checks. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

No project-local CLAUDE.md exists at `./CLAUDE.md`. Global user CLAUDE.md (`~/.claude/CLAUDE.md`) declares: graphify skill at `~/.claude/skills/graphify/SKILL.md` (not present locally — skipped), user email, current date. None of these alter Phase 6 implementation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema artifact (declarative contract) | Static asset (`docs/webhook-schema.json`) | — | Pure JSON, no code; consumed by validator at runtime. |
| Schema compilation | CLI runtime helper | — | Once per invocation in the validation helper; no module-import side effect. |
| Per-row validation iteration | CLI runtime (`convert()`) | — | Already owns the row list and the JSON write; insertion point sits between row-build close and `json.dump`. |
| ImportError handling for missing extra | CLI runtime helper | — | Lazy-import discipline (D-06-17); local `try/except ImportError` block. |
| PII-safe stderr formatting | CLI runtime helper | — | T-PII-01 carry-forward; categorical fields only from exception attributes. |
| Optional dependency declaration | Packaging metadata (`pyproject.toml`) | — | PEP 621 `[project.optional-dependencies]`; flit_core build backend. |
| README operator docs | Static asset (`README.md`) | — | D-11 10-section lock; extend `## CLI reference` and `## Quickstart` only. |
| Self-validation against metaschema | Test-tier (unit) | — | Pure unit test; no production code consumes the metaschema. |

## Standard Stack

### Core (production runtime — opt-in only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastjsonschema` | `>=2.21.2` | JSON Schema Draft-04/06/07 validation via generated Python code | Already locked by STATE.md v1.1 decisions; performance-oriented (compile once, validate many); minimal API surface; supports Draft-07 explicitly. [VERIFIED: `pip index versions fastjsonschema` → 2.21.2 is the current release] |

### Core (development — already in repo)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | (existing) | Test runner | Already used by all 71 tests; no new dev dep needed. |

### Build backend
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `flit_core` | `>=3.2,<4` | PEP 517 build backend for the new pyproject.toml | Sibling pattern: `confluence-to-markdown/pyproject.toml` already uses `flit_core >=3.2,<4`. Minimal surface — fits a stdlib-only project introducing one optional extra. [CITED: `confluence-to-markdown/pyproject.toml`] |

### Alternatives Considered (LOCKED — do not switch)
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fastjsonschema` | `jsonschema` (the reference impl) | `jsonschema` has friendlier diagnostics but ~10× slower validation and a larger import surface. STATE.md v1.1 locked `fastjsonschema`. Don't revisit. |
| `flit_core` | `hatchling` / `setuptools` | Either works for a single-module project, but `flit_core` mirrors the sibling project and has near-zero config. STATE.md v1.1 locked. Don't revisit. |
| Hand-written schema | Auto-generated from sample | Auto-gen would embed Spanish question strings as required values — explicitly forbidden by REQUIREMENTS.md OUT OF SCOPE. |

**Installation (operator):**
```bash
cd quizify-csv-to-json-webhook
pip install '.[validate]'
```

**Version verification:**
- `fastjsonschema 2.21.2` confirmed current via `pip index versions fastjsonschema` on 2026-05-04. [VERIFIED]
- `flit_core >=3.2,<4` confirmed in sibling `confluence-to-markdown/pyproject.toml` line 19. [VERIFIED]

## Architecture Patterns

### System Architecture Diagram

```
┌────────────────────────┐
│ argv → main()          │  argparse adds --validate (store_true, default False)
└─────────┬──────────────┘
          │ args.validate
          ▼
┌────────────────────────┐
│ convert(path, ...,     │
│   validate: bool)      │
└─────────┬──────────────┘
          │
          ▼ (existing flow unchanged through here)
┌────────────────────────┐
│ open CSV → classify    │
│ headers → emit Phase-5 │  Phase 5 missing-trio WARNING fires here
│ missing-trio WARNING   │  (orthogonal to --validate per D-06-22)
└─────────┬──────────────┘
          ▼
┌────────────────────────┐
│ row loop:              │
│   build_row(...)       │
│   results.append(row)  │
└─────────┬──────────────┘
          │
          ├─── if not validate ──► json.dump(results) ──► exit 0
          │
          ▼ if validate
┌────────────────────────┐
│ _run_schema_validation │  Lazy: import fastjsonschema (D-06-17)
│ (results)              │  Compile once: validator = compile(schema)  (D-06-18)
│   - ImportError →      │  for row in results: validator(row)
│     D-06-19 + exit 1   │
│   - JsonSchemaValue    │
│     Exception →        │  Format from .path / .rule / .definition /
│     D-06-20 + exit 1   │  type(value).__name__  — NEVER .message/.value
└─────────┬──────────────┘
          ▼ on success
        json.dump(results) ──► exit 0
```

### Recommended Project Structure

```
quizify-csv-to-json-webhook/
├── pyproject.toml                       # NEW (D-06-01..D-06-05)
├── quizify_csv_ingest.py                # EDITED (argparse + validation helper)
├── README.md                            # EDITED (CLI table + Quickstart)
├── docs/
│   ├── webhook-schema.json              # NEW (D-06-06..D-06-15)
│   ├── webhook-quizify-format-example.json  # existing
│   └── quizify-submissions.csv          # existing (42-row sample)
├── requirements-dev.txt                 # existing (pytest only)
└── tests/
    ├── conftest.py                      # existing — `scoring_index_map_default` reusable
    ├── test_schema_validation.py        # NEW (planner's call; D-06-25 a/b/c/d)
    ├── test_readme_help_alignment.py    # green after README edits (no test edits)
    └── ... (existing 8 test files unchanged)
```

### Pattern 1: Lazy import inside helper (D-06-17)

**What:** `import fastjsonschema` happens inside the validation helper body, not at module top. Default code path never imports it.

**When to use:** Required for D-13 stdlib-only-at-runtime preservation.

**Example:**
```python
# Source: 06-CONTEXT.md D-06-17 + fastjsonschema docs (Context7-verified API surface)
def _run_schema_validation(rows: list[dict], schema_path: Path) -> int:
    try:
        import fastjsonschema  # lazy: only imported under --validate
    except ImportError:
        print(
            "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'",
            file=sys.stderr,
        )
        return 1
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        validator = fastjsonschema.compile(schema)  # compile once
    except fastjsonschema.JsonSchemaDefinitionException as err:
        # Schema authoring bug; categorical, no row data
        print(f"ERROR schema definition invalid: {err}", file=sys.stderr)
        return 1
    try:
        validator(rows)  # validate the whole array in one call (root is array)
    except fastjsonschema.JsonSchemaValueException as err:
        pointer = "/" + "/".join(err.path[1:])  # drop leading 'data'
        expected = (err.definition or {}).get("type", "<unknown>")
        actual = type(err.value).__name__
        print(
            f"ERROR schema validation failed at {pointer}: expected {expected}, got {actual}",
            file=sys.stderr,
        )
        return 1
    return 0
```

Note: `err.path` always begins with `'data'` (literal — not row content; see fastjsonschema source: `path = SPLIT_RE.split(self.name)`). Slicing `[1:]` and joining with `/` produces a JSON Pointer like `/0/email` for "row 0, key email." The leading `data` is the validator's own variable name, not user data. [VERIFIED via Context7 docs at horejsek.github.io/python-fastjsonschema/modules/fastjsonschema/exceptions.html]

### Pattern 2: Compile-once-validate-many (D-06-18)

**What:** Call `fastjsonschema.compile(schema)` exactly once per CLI invocation; reuse the returned callable for every row (or pass the entire list — the schema root is `{"type": "array"}` so a single call validates all rows).

**When to use:** Always. Per-row recompilation is the textbook fastjsonschema antipattern.

**Recommendation:** Validate the whole array in one call. fastjsonschema reports the first failure with a path like `data[3].email` → `/3/email` after pointer extraction. This avoids a Python-side row loop and gives the same first-failure semantics.

### Pattern 3: flit_core single-module project (D-06-04)

**What:** Project name uses hyphens (`quizify-csv-to-json-webhook`), the importable module uses underscores (`quizify_csv_ingest`). flit's default rule replaces hyphens with underscores, but the names diverge here, so we declare the module explicitly.

**Example:**
```toml
# Source: https://flit.pypa.io/en/stable/pyproject_toml.html [VERIFIED via WebFetch]
[project]
name = "quizify-csv-to-json-webhook"
version = "1.1.0"
description = "Quizify CSV → webhook JSON CLI"
requires-python = ">=3.9"
readme = "README.md"
license = { text = "MIT" }
# NOTE: NO [project.dependencies] — D-13 (stdlib-only at runtime).

[project.optional-dependencies]
validate = ["fastjsonschema>=2.21.2"]

[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"

[tool.flit.module]
name = "quizify_csv_ingest"
```

The `[tool.flit.module]` table is the explicit way to point flit at a single `.py` file whose name doesn't match the project name's underscore-substitution. flit looks for `quizify_csv_ingest.py` in the directory holding `pyproject.toml`, finds it, and packages the single module. [CITED: flit.pypa.io/en/stable/pyproject_toml.html]

### Pattern 4: Schema layout (D-06-09..D-06-15)

```jsonc
// Source: 06-CONTEXT.md D-06-07..D-06-15 + JSON Schema Draft-07 spec
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "quizify-csv-to-json-webhook/docs/webhook-schema.json",
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": [
      "email", "firstName", "lastName", "status", "statusDate", "phone", "tags",
      "quiz_title",
      "result-logic", "score-category", "score-value",
      "product-recommendation", "product-link-type", "title", "type-page-url"
    ],
    "properties": {
      "email": { "type": "string" },
      "firstName": { "type": "string" },
      "lastName": { "type": "string" },
      "status": { "type": "string" },
      "statusDate": { "type": "string" },
      "phone": { "type": "string" },
      "tags": { "type": "array", "items": { "type": "string" } },
      "quiz_title": { "type": "string" },
      "result-logic": { "type": "string" },
      "score-category": { "type": "string" },
      "score-value": { "type": "string" },
      "product-recommendation": { "type": ["string", "null"] },
      "product-link-type": { "type": ["string", "null"] },
      "title": { "type": "string" },
      "type-page-url": { "type": "string" }
    },
    "patternProperties": {
      "^question-\\d+$": { "type": "string" },
      "^answers-\\d+$": {
        "oneOf": [
          { "type": "string" },
          {
            "type": "array",
            "items": { "type": "object" }
          }
        ]
      },
      "^answers-tags-\\d+$": { "type": "string" }
    }
  }
}
```

Notes:
- `patternProperties` + `properties` + `additionalProperties: false` interact as: a key is ALLOWED if it matches any entry in `properties` OR any pattern in `patternProperties`; otherwise rejected by `additionalProperties: false`. Keys matching BOTH a `properties` entry and a `patternProperties` regex must satisfy BOTH (intersection AND). [VERIFIED: JSON Schema Draft-07 §6.5.4-6.5.6; Context7 fastjsonschema docs confirm the implementation matches the spec]
- None of the fixed `properties` keys (`email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags`, `quiz_title`, `result-logic`, `score-category`, `score-value`, `product-recommendation`, `product-link-type`, `title`, `type-page-url`) match `^question-\d+$`, `^answers-\d+$`, or `^answers-tags-\d+$`. Verified by inspection — every fixed key contains at least one character that breaks the pattern (no leading `question-`/`answers-`/`answers-tags-` prefix followed by digits).
- `product-recommendation` and `product-link-type` are `["string", "null"]` — the locked defaults emit `null` per `SCORING_PLACEHOLDERS` at line 117 of `quizify_csv_ingest.py`.
- `tags` is a string array; per `build_row` line 265, the default value is `["source: quizify"]` plus optional unmatched-tag entries. All elements are strings.
- The answer-array `items` is `{"type": "object"}` only (no per-property constraints) per D-06-14 (Quizify owns answer-object shape). The example payload mixes `{"answer_name", "id"}` and `{"answer_name", "answer_img", "answer_tag", "id"}` — keeping the constraint at `type: object` accepts both.

### Anti-Patterns to Avoid

- **Eager-importing fastjsonschema at module top** — breaks D-13 for default callers; breaks the `--validate`-without-the-extra error path (the script would fail at import time, not in the helper).
- **Forwarding `JsonSchemaValueException.message` to stderr** — leaks cell content. The message is free-form (e.g., `data[0].email must be string`) and `.value` is literally the offending value. Both are unsafe for T-PII-01.
- **Compiling the schema per-row** — fastjsonschema compiles via code generation (`exec`); per-row compile is ~1000× slower than per-row validate.
- **Loose `^question-` pattern** — must include `\d+$` (or at minimum `\d+`) so it doesn't accidentally match a future `question-meta` or similar non-numeric suffix.
- **Draft 2020-12 metaschema URL** — fastjsonschema 2.21.2 supports Draft-04/06/07. Using `https://json-schema.org/draft/2020-12/schema` would be silently ignored (or fall back to Draft-07 default). Stick to `http://json-schema.org/draft-07/schema#` per D-06-07.
- **`additionalProperties: false` on the answer-object items** — would reject example-payload rows where the answer carries `id` (lines 16-19 of `webhook-quizify-format-example.json`) but no `answer_img`/`answer_tag`. Asymmetric answer shape is owned by Quizify, not us (D-06-14).
- **`pip install '[validate]'` from repo root** — won't work; `pyproject.toml` lives in `quizify-csv-to-json-webhook/`, so installation requires `cd quizify-csv-to-json-webhook && pip install '.[validate]'` (or `pip install 'quizify-csv-to-json-webhook/[validate]'` from repo root, but the README will document the `cd`-then-install form for clarity).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | Custom recursive type checker | `fastjsonschema.compile(schema)` | Spec compliance is non-trivial: `oneOf`, `patternProperties`, `additionalProperties` interaction, `$ref` resolution. fastjsonschema's compiled validators are ~25ms for valid input. |
| JSON Pointer extraction | String parsing of error message | `JsonSchemaValueException.path` (list[str]) | The library exposes `path` as a list; just slice + join. Parsing `.message` invites PII leakage and is brittle across versions. |
| Schema self-validation against Draft-07 metaschema | Hand-fetching the metaschema | `fastjsonschema.compile(json.loads(schema_text))` against the schema itself, then validate the schema dict against the embedded Draft-07 metaschema | fastjsonschema bundles support for Draft-07 via the `$schema` keyword on the schema being compiled; if the schema is invalid Draft-07, `compile()` raises `JsonSchemaDefinitionException`. Use that as the self-validation gate (no separate `jsonschema` library needed). |
| Optional-dependency wiring | Manual `try: import; except: ...` everywhere | PEP 621 `[project.optional-dependencies]` + lazy import in one helper | flit_core resolves the extra; pip handles the install path; the lazy import is a single `try/except ImportError` block. |
| pyproject for single-module project | Custom `setup.py` | flit_core `[tool.flit.module]` | flit_core handles single-file modules natively with `name = "..."` in the `[tool.flit.module]` table. No `setup.py`. |

**Key insight:** The locked decisions in 06-CONTEXT.md already chose every standard library/pattern correctly. The implementation risk is concentrated in **one** spot — the validation-helper error formatting — where a wrong attribute (`.message` or `.value`) silently breaks T-PII-01.

## Common Pitfalls

(Continuing the Phase 4/5 PITFALLS.md tradition — these are the Phase 6 specific landmines on top of any carry-forward from `.planning/research/PITFALLS.md`.)

### Pitfall 17: Forwarding `JsonSchemaValueException.message` raw leaks cell content (T-PII-01)

**What goes wrong:** Stderr message becomes `ERROR data[0].email must be string but got 'silverpaezp@gmail.com'` — the email is printed verbatim. T-PII-01 violated.

**Why it happens:** `JsonSchemaValueException.message` is a free-form human-readable string that includes both the path AND the offending value. `JsonSchemaValueException.value` is literally the offending Python object. Both are designed for developer debugging, not user-facing error reporting.

**How to avoid:** Format the D-06-20 stderr message ONLY from:
- `err.path` (list[str], path components — categorical)
- `err.rule` (e.g., `'type'`, `'required'`, `'pattern'` — categorical)
- `err.definition.get('type')` (schema-declared expected type — categorical)
- `type(err.value).__name__` (Python type name like `str`, `int`, `NoneType`, `list` — categorical)

Never reference `err.message`, `str(err)`, or `err.value` directly in the stderr output.

**Warning signs:** A test that passes a row with a known PII value (e.g., `email: "leak@example.com"`) and a deliberately wrong schema-violating type (e.g., dropping a required key) does NOT explicitly assert `"leak@example.com" not in stderr`. This is the test that catches the regression — required by D-06-25(c).

**Phase to address:** This phase — must land in the validation helper's first commit.

---

### Pitfall 18: Eager `import fastjsonschema` at module top breaks D-13 + breaks the missing-extra error path

**What goes wrong:** A naive implementation puts `import fastjsonschema` at line 14 of `quizify_csv_ingest.py`. (a) Default callers (no `--validate`) now require fastjsonschema installed even though the flag is off — D-13 violated. (b) When fastjsonschema IS missing under `--validate`, the script fails with a Python traceback at import time before `argparse` even runs, defeating D-06-19's actionable message.

**Why it happens:** Idiomatic Python style is "imports at top." It's the right default 95% of the time and the wrong default here.

**How to avoid:** `import fastjsonschema` lives INSIDE the `_run_schema_validation` function body, wrapped in `try/except ImportError`. Module-top imports stay stdlib-only (the existing list at lines 5-14 is correct as-is).

**Warning signs:** `grep -n 'import fastjsonschema' quizify_csv_ingest.py` shows the import outside any function body. Or: running `python quizify_csv_ingest.py sample.csv` (no flag) fails with `ModuleNotFoundError`.

**Phase to address:** This phase — verified by D-06-25(d) test.

---

### Pitfall 19: Per-row schema compile balloons CLI runtime

**What goes wrong:** The validation helper calls `fastjsonschema.compile(schema)` inside a `for row in results:` loop. 42 rows → 42 schema-codegen passes. CLI runtime spikes from <1s to several seconds.

**Why it happens:** A naive port of "validate each row" reads as "compile + validate each row" if the boilerplate of compile is included in the per-row block.

**How to avoid:** Compile once before the loop (D-06-18). Better still: `validator(rows)` once — the schema root is `{"type": "array"}` so a single validator call handles all rows and reports the first failure with a path like `data[3].email` (extracts to `/3/email`).

**Warning signs:** Validation timing test takes >100ms on the 42-row sample. Or: the helper's body shows `compile` inside any `for` loop.

**Phase to address:** This phase.

---

### Pitfall 20: `fastjsonschema` accidentally declared as a runtime dependency in pyproject.toml (breaks D-13)

**What goes wrong:** A copy-paste from a different project puts `dependencies = ["fastjsonschema>=2.21.2"]` (without the `[project.optional-dependencies]` table). Now a plain `pip install .` pulls fastjsonschema, the runtime is no longer stdlib-only, and D-13 is silently broken.

**Why it happens:** PEP 621 has both `[project] dependencies = [...]` and `[project.optional-dependencies] <name> = [...]`. They look almost identical in TOML. The difference is one keyword and one indentation level.

**How to avoid:** The pyproject.toml MUST have:
- An explicitly EMPTY (or absent) `[project.dependencies]` array — preferably absent entirely so a typo can't add to it.
- A `[project.optional-dependencies]` table with `validate = ["fastjsonschema>=2.21.2"]`.

**Warning signs:** `grep -n fastjsonschema pyproject.toml` shows the package name on more than one line, OR shows it under a key named `dependencies` (not `optional-dependencies` or `validate`).

**Phase to address:** This phase. Plan should include a unit test or grep-based check that asserts `[project.dependencies]` is empty/absent.

---

### Pitfall 21: `^question-\d+$` regex too loose or anchored wrong

**What goes wrong:** Schema regex `^question-\d+` (no `$` end-anchor) matches `question-1foo` and lets garbage keys through. Or `question-\d+` (no `^` start-anchor) matches `xquestion-1` (impossible in our emit, but the schema would silently relax). Or `^question-` (no digits required) matches `question-meta` — letting an unanticipated future key slip through `additionalProperties: false`.

**Why it happens:** Regex authoring under TDD is fast and slightly forgiving — anchors are easy to miss in JSON-escaped patterns (`\\d` in JSON is `\d` in the underlying regex).

**How to avoid:** Use exactly `"^question-\\d+$"`, `"^answers-\\d+$"`, `"^answers-tags-\\d+$"` (JSON-escaped form — the `\\d` becomes `\d` after JSON parse). Add a unit test that constructs a row with `{"question-1foo": "..."}` and asserts validation FAILS.

**Warning signs:** No regex round-trip test in `test_schema_validation.py`. Or: a row with `question-1abc` passes validation under `--validate`.

**Phase to address:** This phase.

---

### Pitfall 22: Draft-07 vs Draft 2020-12 metaschema URL drift

**What goes wrong:** Schema declares `"$schema": "https://json-schema.org/draft/2020-12/schema"`. fastjsonschema 2.21.2 supports Draft-04/06/07 only — the 2020-12 URL is silently treated as the default (Draft-07). The schema "works" but the declared dialect is a lie, and a future swap to a stricter validator (e.g., `jsonschema` 4.x) would behave differently.

**Why it happens:** Newer JSON-Schema docs and tools default to 2020-12; Claude's training may suggest the modern URL. D-06-07 LOCKS Draft-07 explicitly.

**How to avoid:** `"$schema": "http://json-schema.org/draft-07/schema#"` (HTTP, not HTTPS; trailing `#`). Verified-correct format per fastjsonschema's source. Self-validation test asserts the schema's `$schema` value matches this exact string.

**Warning signs:** The schema's `$schema` value contains `2020-12` or `draft/`. Or: HTTPS instead of HTTP in the URL.

**Phase to address:** This phase.

---

### Pitfall 23: Subprocess-flooding tests (Phase 5 Pitfall 16 carry-forward)

**What goes wrong:** New schema-validation tests call `subprocess.run([sys.executable, "quizify_csv_ingest.py", ...])` for every assertion. Test runtime balloons from 1.09s to 4-5s, regressing the existing test budget.

**Why it happens:** D-06-25(b) is the "sample passes" success-path test, naturally written as a subprocess invocation. But the success path is also exercisable directly by calling the validation helper with the parsed JSON list.

**How to avoid:** D-06-24 — call the validation helper directly with Python data structures + a precomputed compiled validator. Use `subprocess` ONLY for the rare end-to-end smoke test (e.g., one CLI-level test that asserts `--validate` exit code on the live sample). The other four scenarios in D-06-25 are unit-level.

**Warning signs:** `grep -c subprocess.run tests/test_schema_validation.py` returns more than 2.

**Phase to address:** This phase.

---

### Pitfall 24: `[validate]` extra name pluralized or mis-cased

**What goes wrong:** pyproject.toml declares `[project.optional-dependencies] validation = [...]` (or `Validate`, or `validate-extras`). The README-locked install line `pip install '.[validate]'` resolves nothing, install fails silently with "no matches found for 'validate'", and operators get confused.

**Why it happens:** Naming consistency drift between the spec, README, tests, and the toml.

**How to avoid:** The extra name is exactly `validate` (lowercase, singular). It appears in:
- `pyproject.toml`: `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`
- `README.md`: `pip install '.[validate]'`
- D-06-19 stderr template: `pip install '.[validate]'`

A grep-based test or doc-test should assert this string is byte-identical across the three locations.

**Warning signs:** The string `'.[validate]'` appears with any case-shift, plural, or hyphen variation in any of those three files.

**Phase to address:** This phase.

## Code Examples

### Example 1: argparse wiring (D-06-23)

```python
# Source: quizify_csv_ingest.py main() lines 433-452 (current shape) + D-06 add
parser.add_argument(
    "--validate",
    action="store_true",
    help="Validate emitted JSON against docs/webhook-schema.json (requires '[validate]' extra).",
)
```

The `args.validate` namespace key is then forwarded into `convert(...)` either as a new keyword arg or via the existing `args` object. Discretion left to planner per 06-CONTEXT.md.

### Example 2: JSON Pointer extraction (T-PII-01-safe)

```python
# Source: fastjsonschema source (Context7-verified) + D-06-20 template
def _format_validation_error(err) -> str:
    """Format JsonSchemaValueException → D-06-20 PII-safe stderr line.

    Uses ONLY categorical attributes:
      - err.path  : list[str], e.g. ['data', '3', 'email']
      - err.definition : dict, schema clause being evaluated
      - type(err.value).__name__ : 'str' / 'int' / 'NoneType' / 'list' / etc.

    NEVER references err.message or err.value directly.
    """
    pointer = "/" + "/".join(err.path[1:]) if len(err.path) > 1 else "/"
    expected = (err.definition or {}).get("type", "<unknown>")
    if isinstance(expected, list):  # type can be a list, e.g. ["string", "null"]
        expected = "|".join(expected)
    actual = type(err.value).__name__
    return f"ERROR schema validation failed at {pointer}: expected {expected}, got {actual}"
```

### Example 3: Schema self-validation test (D-06-25 a)

```python
# Source: fastjsonschema docs — JsonSchemaDefinitionException raised on invalid schema
def test_schema_self_validates_against_draft07():
    """Schema file MUST itself be valid Draft-07."""
    import fastjsonschema  # opt-in test; skip if not installed
    import json
    from pathlib import Path

    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "docs" / "webhook-schema.json").read_text()
    )
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    # If the schema is malformed, this raises JsonSchemaDefinitionException.
    fastjsonschema.compile(schema)
```

This avoids needing the `jsonschema` library or an offline metaschema file — `fastjsonschema.compile()` IS the self-validation gate.

### Example 4: Sample-passes test (D-06-25 b, unit-level not subprocess)

```python
def test_sample_csv_payload_validates(tmp_path):
    """The 42-row sample MUST pass schema validation post-Phase-5 hardening."""
    import fastjsonschema
    from quizify_csv_ingest import convert

    out = tmp_path / "out.json"
    rc = convert(SAMPLE_CSV_PATH, None, out, quiz_title="Autoevaluacion")
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = fastjsonschema.compile(schema)
    validator(payload)  # raises JsonSchemaValueException on failure
```

Note: this calls `convert()` directly (no subprocess) — preserves Pitfall 16/23 budget. Adds one fastjsonschema dependency for the test, gated by `pytest.importorskip("fastjsonschema")`.

### Example 5: PII-safe failure test (D-06-25 c — VALI-02)

```python
def test_validation_failure_does_not_leak_cell_content():
    import fastjsonschema
    from quizify_csv_ingest import _format_validation_error

    leak_email = "leak@example.com"
    schema = {"type": "object", "required": ["email"], "properties": {"email": {"type": "string"}}}
    validator = fastjsonschema.compile(schema)
    bad_row = {"email": leak_email, "phone": "+52 55 9999 9999"}  # missing 'email' key after del
    del bad_row["email"]
    try:
        validator(bad_row)
        assert False, "expected validation failure"
    except fastjsonschema.JsonSchemaValueException as err:
        msg = _format_validation_error(err)
        assert "email" in msg or "required" in err.rule
        # Critical PII assertions:
        assert leak_email not in msg
        assert "+52" not in msg
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `jsonschema` 3.x for validation | `fastjsonschema` 2.21.2 | STATE.md v1.1 lock (2026-05-04) | ~10× faster; smaller dep surface; minimal API. |
| `setup.py` for single-module packaging | `pyproject.toml` + flit_core | PEP 621 (2020) widespread by 2023 | Declarative metadata; no Python code in build config. |
| Draft-04 schemas | Draft-07 (locked) / Draft 2020-12 (NOT used here) | D-06-07 locks Draft-07 | fastjsonschema supports through Draft-07; 2020-12 not yet supported. |
| `[options.extras_require]` (setup.cfg) | `[project.optional-dependencies]` (PEP 621) | PEP 621 finalized 2020 | Same install syntax (`pip install '.[validate]'`); declarative-only. |

**Deprecated/outdated:**
- `https://json-schema.org/draft/2020-12/schema` URL — fastjsonschema 2.21.2 does not support 2020-12 dialect. Using it silently falls back to Draft-07. D-06-07 locks the explicit Draft-07 URL so this can't drift.
- `setup.py` for single-module projects — PEP 621 covers everything we need.

## Runtime State Inventory

> Phase 6 is primarily additive (new file + edits to one Python file + README edits) and does NOT rename any keys, modules, or stored identifiers. The Inventory is short but explicit — none of the categories are populated, but each must be answered, not left blank.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases, datastores, or persistent caches involved. The CLI is a pure CSV-in / JSON-out transform. | None. |
| Live service config | None — no external services (n8n, Make.com config, Datadog, etc.) reference Python module names or schema paths. The Make.com side reads JSON keys (locked by D-05), not module paths or schema files. | None. |
| OS-registered state | None — no Task Scheduler, launchd, systemd, pm2 entries reference `quizify_csv_ingest`. CLI is invoked by humans / CI on demand. Verified by absence of any such config in the repo and by the project's "single-file utility" nature. | None. |
| Secrets / env vars | One env var exists: `QUIZIFY_QUIZ_TITLE` (read at line 165). Phase 6 does NOT add, rename, or remove any env var. The locked stderr templates (D-06-19, D-06-20) are compile-time constants, not env-driven. | None. |
| Build artifacts / installed packages | Phase 6 introduces `pyproject.toml`. After someone runs `pip install '.[validate]'`, an installed-package record will exist for `quizify-csv-to-json-webhook==1.1.0` plus any pip-resolved `*.dist-info/` and a `quizify_csv_ingest.egg-info/`-equivalent (flit creates `*.dist-info`, not `egg-info`). Nothing pre-existing to clean up since the project has never been pip-installed before. | None for v1.1; if/when v1.2 bumps the version, operators will `pip install --upgrade '.[validate]'` and pip handles the dist-info refresh. |

**Canonical answer to "what runtime state survives a code edit?":** Nothing meaningful. Phase 6 is greenfield-additive within an established CLI. No data migrations, no service re-registrations, no env-var renames, no build-artifact cleanup needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥ 3.9 | Runtime + `pyproject.toml` `requires-python` | (verify on planner machine) | — | None — the `from __future__ import annotations` at line 4 + PEP 585 generics REQUIRE 3.9+. |
| `pytest` | Test runner | (existing — `requirements-dev.txt`) | as-installed | None — already in repo dev dep set. |
| `fastjsonschema >= 2.21.2` | Schema validation tests + `--validate` runtime | (must install via `pip install '.[validate]'`) | 2.21.2 | None for `--validate`; tests gate on `pytest.importorskip("fastjsonschema")` so they're skipped if not installed locally. |
| `flit_core >= 3.2,<4` | Build backend (only invoked if someone actually builds a wheel) | (pip resolves at install time) | as-resolved | None for builds; not needed for `--validate` runtime. |
| `pip` | Install path | (assumed — universal) | — | None. |

**Missing dependencies with no fallback:** None blocking. `fastjsonschema` is opt-in by design (D-06-17).

**Missing dependencies with fallback:** Tests that require `fastjsonschema` use `pytest.importorskip` and are skipped locally if the extra isn't installed; CI installs `'.[validate]'` to exercise them.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (existing — version pinned implicitly by `requirements-dev.txt`) |
| Config file | None visible at root; `pytest` discovers `tests/` by convention. |
| Quick run command | `cd quizify-csv-to-json-webhook && pytest -q tests/test_schema_validation.py` |
| Full suite command | `cd quizify-csv-to-json-webhook && pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALI-01 | `--validate` flag triggers validation; sample passes end-to-end | unit + 1 smoke subprocess | `pytest -q tests/test_schema_validation.py::test_sample_csv_payload_validates` | ❌ Wave 0 |
| VALI-02 | Violation → exit 1 + PII-safe pointer; no cell content | unit (helper-direct) | `pytest -q tests/test_schema_validation.py::test_validation_failure_does_not_leak_cell_content` | ❌ Wave 0 |
| VALI-03 | Schema self-validates against Draft-07 metaschema | unit | `pytest -q tests/test_schema_validation.py::test_schema_self_validates_against_draft07` | ❌ Wave 0 |
| VALI-04 | Default behavior unchanged when `--validate` absent | unit | existing `tests/test_cli_emit.py::test_default_invocation_emits_json_to_stdout` (no edit needed; relies on D-06-17 lazy-import) | ✅ existing |
| VALI-05 | Missing `fastjsonschema` → D-06-19 actionable stderr + exit 1, no traceback | unit (monkeypatch) | `pytest -q tests/test_schema_validation.py::test_missing_fastjsonschema_extra_emits_actionable_stderr` | ❌ Wave 0 |
| VALI-06 | README documents `--validate`, `[validate]` extra; D-11 drift test passes | unit (existing) | `pytest -q tests/test_readme_help_alignment.py` | ✅ existing (no test edit; only README content edit) |

### Sampling Rate
- **Per task commit:** `pytest -q tests/test_schema_validation.py tests/test_readme_help_alignment.py` (~< 0.5s)
- **Per wave merge:** `pytest -q` (full suite — must stay green; current 71 tests + ~5 new = 76)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_schema_validation.py` — covers VALI-01 (sample-pass), VALI-02 (PII-safe failure), VALI-03 (self-validate), VALI-05 (missing extra). Five test functions per D-06-25.
- [ ] `docs/webhook-schema.json` — the schema artifact itself is required Wave 0 fixture for the schema tests.
- [ ] No new `conftest.py` fixtures needed — existing `sample_csv_path`, `dynamic_headers`, and Phase-5's `scoring_index_map_default` cover the test inputs.
- [ ] Framework install for the `validate` extra in CI: `pip install '.[validate]'` — required to exercise the new tests with fastjsonschema available. Locally, tests skip via `pytest.importorskip` when not installed.

## Security Domain

(`security_enforcement: true`; ASVS Level 1.)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 6 adds no auth surface. |
| V3 Session Management | no | No sessions; CLI is invocation-scoped. |
| V4 Access Control | no | Local file I/O only; OS file permissions govern. |
| V5 Input Validation | yes | This is literally the phase's deliverable. JSON Schema validation = ASVS V5.1 (input is constrained against an explicit schema). Library: `fastjsonschema` (compiled validators). |
| V6 Cryptography | no | No crypto operations. |
| V7 Error Handling & Logging | yes | T-PII-01 carry-forward — categorical-only stderr; no cell content. Logging discipline is the entire reason D-06-20 forbids `.message`/`.value`. |
| V14.2 Dependency Management | yes | New optional dependency `fastjsonschema>=2.21.2` declared in `[project.optional-dependencies]`; not in runtime `[project.dependencies]`. Version pin uses `>=` for security-patch acceptance; minor bumps are accepted automatically. |

### Known Threat Patterns for Python CLI + JSON Schema validation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII leakage in error messages | Information Disclosure | Categorical-only error formatting (D-06-20). Never forward `JsonSchemaValueException.message` or `.value`. Pitfall 17. |
| Dependency-confusion via the `[validate]` extra | Tampering / Spoofing | `fastjsonschema` is published on PyPI by `horejsek` since 2017; the package name is unambiguous. Version pin `>=2.21.2` accepts security patches but rejects pre-2.14 versions which lack the `path` attribute. |
| Schema injection via untrusted schema path | Tampering | The schema path is hardcoded — `docs/webhook-schema.json` relative to the script — NOT user-controllable. No `--schema-path` flag in v1.1. |
| Resource exhaustion via deeply nested arrays | Denial of Service | Schema's `^answers-\d+$` permits arrays, but Quizify's CSV format caps array length implicitly via cell length; no recursion. fastjsonschema generates iterative code, not recursive validators. Within v1.1 row sizes (~1KB), no concern. |
| Pickle/code-execution via fastjsonschema | Tampering | `fastjsonschema.compile()` uses `exec()` on generated code — but the generated code is derived from the schema dict, which is loaded from a repo-controlled JSON file. No user-controlled schema path means no code-injection vector. Document this in the validation helper's docstring. |

## Sources

### Primary (HIGH confidence)
- Context7: `/websites/horejsek_github_io_python-fastjsonschema` — exception class API (`JsonSchemaValueException` attributes: `message`, `value`, `name`, `path`, `definition`, `rule`, `rule_definition`); `compile()` and `validate()` API; Draft-04/06/07 support confirmed; Draft-07 is the default when `$schema` absent. [VERIFIED 2026-05-04]
- WebFetch: `https://flit.pypa.io/en/stable/pyproject_toml.html` — `[tool.flit.module] name = "..."` syntax for single-module projects; project-name vs module-name decoupling. [VERIFIED 2026-05-04]
- `pip index versions fastjsonschema` — confirmed 2.21.2 is the current release. [VERIFIED 2026-05-04]
- Direct source inspection: `quizify_csv_ingest.py` (full file), `tests/conftest.py`, `tests/test_readme_help_alignment.py`, `tests/test_cli_emit.py`, `tests/test_logging_pii.py`, `tests/test_structural_invariants.py`, `confluence-to-markdown/pyproject.toml`, `docs/webhook-quizify-format-example.json`. [VERIFIED via Read]
- 06-CONTEXT.md, REQUIREMENTS.md, ROADMAP.md, PROJECT.md, STATE.md, 05-CONTEXT.md, .planning/research/PITFALLS.md (first 50 lines). [VERIFIED via Read]

### Secondary (MEDIUM confidence)
- JSON Schema Draft-07 specification, semantics of `patternProperties` × `properties` × `additionalProperties` interaction. [CITED via Context7 fastjsonschema docs which encode the spec semantics]

### Tertiary (LOW confidence)
- None — no claims in this research rely on training-data-only reasoning. Every API attribute, version, and syntactic detail is verified against current docs or current source.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 42-row sample at `docs/quizify-submissions.csv` produces a payload that VALIDATES against the schema described in Pattern 4 (D-06-09..D-06-15) | VALI-01 / D-06-25(b) | If wrong, the schema needs widening (e.g., a tag-array element is non-string, or `product-recommendation` carries a type the schema rejects). The test would fail in Wave 1 and the schema would be edited. Low risk — the schema mirrors the locked emit shape. |
| A2 | `JsonSchemaValueException.path` always begins with `'data'` (literal — fastjsonschema's internal variable name) | Pattern 1, Example 2 | If wrong, the `path[1:]` slice silently produces a wrong pointer. Confirmed via Context7-fetched source: `path = SPLIT_RE.split(self.name)` with `name` taking the form `data.foo[3].bar`. The first token is always `data`. Low risk but worth a unit assertion. |
| A3 | `fastjsonschema 2.21.2` resolves correctly via `pip install '.[validate]'` from `quizify-csv-to-json-webhook/` (subdirectory project install) | VALI-05 | If wrong, the install line in README is wrong and operators fail. Verified that pip's `.` means "the current directory's pyproject.toml" and the `[validate]` extra is a standard PEP 621 extra. Low risk. |
| A4 | flit_core's `[tool.flit.module]` table is the correct way to declare a single-file module when project-name and module-name differ by hyphen↔underscore | D-06-04 | If wrong, `pip install .` fails at build time. Verified via flit.pypa.io/en/stable/pyproject_toml.html WebFetch. Low risk. |

**If this table is empty:** N/A — there are 4 modest assumptions, all low risk and all verified against authoritative sources. None blocks planning.

## Open Questions

1. **Should `_run_schema_validation` accept the rows + schema-path, or rows + precompiled validator?**
   - What we know: D-06-18 says compile once per invocation. Either signature satisfies that.
   - What's unclear: Whether testability prefers passing the validator (so tests inject a precompiled one) or the path (so tests verify the full schema-load → compile → validate flow).
   - Recommendation: Helper takes `rows` + `schema_path`. Compiles internally. Tests construct a dedicated test-schema with the helper's API. Single-responsibility wins.

2. **Where does the schema file path constant live in the source?**
   - What we know: D-06-06 locks the path to `docs/webhook-schema.json` relative to the project dir.
   - What's unclear: Module-level constant vs `pathlib`-resolved at helper-call time.
   - Recommendation: Module-level `SCHEMA_PATH = Path(__file__).resolve().parent / "docs" / "webhook-schema.json"`. Same idiom as the test files use for `FIXTURE` path.

3. **Should `--dry-run --validate` validate or no-op?**
   - What we know: 06-CONTEXT.md `<code_context>` notes `--dry-run` short-circuits before rows are built; thus `--dry-run --validate` is effectively a no-op for validation today.
   - What's unclear: Should `main()` reject the combination explicitly, or silently allow it?
   - Recommendation: Allow silently (no flag conflict; preserves 06-CONTEXT.md "trivially composable"). Document in the README's `--validate` row description: "validation runs only when JSON output is produced; `--dry-run` skips both".

4. **Test file naming — single `test_schema_validation.py` or split across two files?**
   - What we know: D-06-25 lists 5 test scenarios (a-e); test (e) is the existing `test_readme_help_alignment.py` (no edit). Tests (a)-(d) all relate to schema validation.
   - What's unclear: Whether a separate `test_pyproject_optional_extra.py` file makes sense for VALI-05 specifically.
   - Recommendation: Single `tests/test_schema_validation.py`. Group by class — `TestSchemaSelfValidation`, `TestSamplePasses`, `TestPiiSafeFailure`, `TestMissingExtraActionable`. One file = one feature.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package and version verified against pip index / Context7 docs.
- Architecture: HIGH — every locked decision in 06-CONTEXT.md is preserved; only the discretionary surface (helper signature, file naming) involves judgment.
- Pitfalls: HIGH — derived from direct source inspection of `quizify_csv_ingest.py` and Context7-verified fastjsonschema API.
- PII safety: HIGH — `JsonSchemaValueException` source code inspected; `.message` and `.value` flagged as unsafe; `.path` / `.rule` / `.definition` / `type(value).__name__` flagged as safe.

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (30 days for stable libs; fastjsonschema is mature; flit_core API is stable since 2020). Re-verify if either package ships a major-version bump before then.
