# Stack Research

**Domain:** Python CLI utility — JSON Schema validation layer (v1.1 additions only)
**Researched:** 2026-05-03
**Confidence:** HIGH (library versions verified via PyPI; Python compat verified via package metadata)

---

## Scope

This file covers ONLY stack additions/changes needed for v1.1. The v1.0 baseline (Python 3.7+, stdlib runtime, pytest dev-only) is already validated and is not re-researched here. Three of the four v1.1 features require NO stack changes; one (VALI-01) requires a key decision on a first runtime dependency.

---

## Feature-by-Feature Stack Analysis

### VALI-01 — Opt-in JSON Schema validation (`--validate` flag)

This is the only feature that touches the dependency graph. All other v1.1 features are pure code changes.

#### Options compared

**Option A: `fastjsonschema` 2.21.2**

- Requires Python 3.3+ (no lower bound specified in package metadata; `requires_python` is `None`, meaning no constraint at all). Confirmed compatible with 3.7+.
- Zero transitive runtime dependencies. Single-file install.
- Compiles the schema to a Python function at import/startup time via `fastjsonschema.compile(schema)`. Subsequent calls are function calls, not schema walks.
- Supports JSON Schema Draft 04, 06, and 07. Draft-07 is sufficient for this schema (no `$defs`, no `unevaluatedProperties`, no 2020-12 features needed).
- The compiled validator raises `fastjsonschema.JsonSchemaValueException` on failure, which carries the path and value.
- Performance advantage is irrelevant at this scale (42 rows), but the zero-transitive-dep property directly serves the project constraint "add dependencies only when justified."

**Option B: `jsonschema` 4.17.3 (last Python 3.7-compatible release)**

- `requires_python: >=3.7` confirmed for 4.17.3. Version 4.18.0 raised floor to `>=3.8`.
- Runtime transitive deps at 4.17.3: `attrs>=17.4.0`, `pyrsistent>=0.14.0`, plus conditional backport shims (`importlib-metadata`, `importlib-resources`, `pkgutil-resolve-name`, `typing-extensions`) on Python < 3.8 or < 3.9.
- That is 2 mandatory non-stdlib packages (attrs, pyrsistent) plus up to 4 conditional ones. This turns a "add one dep" decision into "add 2-6 packages."
- `pyrsistent` is a C-extension with optional native acceleration — it has a pure-Python fallback but adds build complexity.
- The richer API (error iterators, `best_match`, format checking) offers no value for this use case: we validate the locked JSON envelope structure (key presence, types, pattern) — not human-readable diagnostics.
- Latest (4.26.0) requires `>=3.10` and adds `rpds-py` (Rust extension). Ruled out for Python 3.7 requirement.

**Option C: `python-jsonschema-objects`**

- A code-generation tool that creates Python classes from a JSON Schema. Not a validator. Wrong tool category. Ruled out.

**Option D: Hand-rolled validator**

- The schema is structurally simple: check key presence in a fixed ordered list, check type of a few fields (`string`, nullable, array), check `question-N`/`answers-N`/`answers-tags-N` triple existence for at least N=1.
- A hand-rolled check is ~50-80 lines of stdlib, zero deps, trivially testable, and will never require a version pin.
- Drawback: does not produce machine-readable JSON Schema that downstream tools (AUTO-01 HTTP POST gating, API docs) can consume. If VALI-01's intent is to establish a formal schema artifact as much as a runtime gate, hand-rolling defeats that goal.
- Appropriate only if the schema is never published or reused outside the script. Given AUTO-01 is a named v1.2 candidate that "depends on VALI-01 being in place," a formal schema file is more valuable than saving one dependency.

#### Recommendation: `fastjsonschema` 2.21.2

Use `fastjsonschema`. Rationale:

1. Zero transitive runtime deps — preserves the spirit of the stdlib-only ethos without requiring a hard zero-deps rule.
2. Python 3.3+ compat — no version pin gymnastics, no risk of accidental upgrade to a 3.8+-only release.
3. Schema compile model matches this use case: compile once at process start when `--validate` is passed, then call the validator per row. No repeated schema parsing overhead.
4. Draft-07 support covers everything needed for this schema without pulling in 2020-12 machinery.
5. A formal JSON Schema file (Draft-07 `.json`) produced alongside the script can be read directly by Make.com, AUTO-01, or CI without any Python tooling.

Do NOT use `jsonschema` 4.17.3 for this project. The 2-6 transitive dep tree is disproportionate for a validator that will only be called when the operator explicitly passes `--validate`. The version freeze at 4.17.3 also means perpetual debt: every security advisory against a newer `jsonschema` will require auditing whether the 4.17.3 line is affected.

### TRAIL-01 — Name-based scoring lookup (no new library)

Pure stdlib refactor. The fix is in `build_row()` at `quizify_csv_ingest.py` lines 263-265. Instead of indexing `trailer_cells_decoded[0]`, `[1]`, `[2]`, look up by the canonical column names (`"Result logic"`, `"Score category"`, `"Score value"`) using the `trailer_raw` headers that `classify_headers()` already returns. Caller already has both lists; it is a dict construction and key lookup, entirely in stdlib. No new dependency.

### CONTRACT-01 — Fix `quizify-mapping.js:102` (no stack change)

Single-line JS change: `record.product_result` → `record["product-recommendation"]`. No new library, no Node toolchain change, no Python dependency. The existing manual verification approach (per v1.1 decision log) is sufficient.

### MAKE-FIX-01 — Peri-menopause tag mismatch + inverted `is_athlete` (no stack change)

Two JS-only fixes:

1. `quizify-mapping.js:167` emits tag `"peri_menu"` (underscore); `score-calculations.js:213` checks `hasTag(tags, "peri-menu")` (hyphen). Fix: align `quizify-mapping.js:167` to emit `"peri-menu"` to match the consumer.
2. `score-calculations.js:247-250`: `activity_profile` is assigned `"athlete"` when `!data.is_athlete` — inverted condition. Fix: change `if (!data.is_athlete)` to `if (data.is_athlete)`.

No new library. No Node test runner added (deferred to v1.2 per decision log). Manual verification only.

---

## Recommended Stack

### Core Technologies (unchanged from v1.0)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.7+ | Runtime | Existing constraint; fastjsonschema 2.21.2 is compatible |
| stdlib (`json`, `csv`, `argparse`, `html`, `os`, `pathlib`, `logging`) | bundled | All runtime logic except validation | Zero install friction |

### New Runtime Dependency (VALI-01 only)

| Library | Version | Purpose | Dep footprint |
|---------|---------|---------|---------------|
| `fastjsonschema` | 2.21.2 | Compile-and-call JSON Schema Draft-07 validator for `--validate` mode | Zero transitive runtime deps |

### Development Tools (unchanged from v1.0)

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | >=7.0 | Test runner | `requirements-dev.txt` already pins this |

---

## Installation

```bash
# If adding as hard dep (not recommended — see below):
pip install fastjsonschema==2.21.2

# If adding as optional extra via pyproject.toml:
pip install '.[validate]'

# Dev (unchanged):
pip install -r quizify-csv-to-json-webhook/requirements-dev.txt
```

---

## Packaging Recommendation: Optional Extra, Not Hard Dep

**Use `pip install '.[validate]'` pattern via `pyproject.toml` (or `setup.cfg`).**

Rationale:

- `--validate` is default-off. An operator running the script without `--validate` never needs `fastjsonschema` installed. Making it a hard dep adds an install requirement that 100% of plain-conversion users never benefit from.
- The project pattern is "stdlib-only at runtime" (D-13). The least disruptive framing is: stdlib remains the runtime baseline; `[validate]` is an opt-in capability tier.
- If the script is later vendored or copied into an environment with a restricted package index, the `[validate]` extra can simply be omitted without breaking the core conversion path.
- Concretely: add a `pyproject.toml` with `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`. This does not require converting the single-file script into a package — `pyproject.toml` can declare extras for scripts in the same directory.
- In `quizify_csv_ingest.py`, gate the import with a try/except that raises a clear `SystemExit` when `--validate` is passed but `fastjsonschema` is not installed:

```python
# Near top of file, only imported when needed:
def _import_validator():
    try:
        import fastjsonschema
        return fastjsonschema
    except ImportError:
        raise SystemExit(
            "ERROR: --validate requires fastjsonschema. "
            "Install with: pip install 'quizify[validate]'"
        )
```

This keeps the import lazy (no startup cost when `--validate` is not passed) and gives the operator an actionable error message.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `fastjsonschema` 2.21.2 | `jsonschema` 4.17.3 | Only if richer error reporting (error iterators, `best_match`) is needed for human-facing diagnostics — not this use case |
| `fastjsonschema` 2.21.2 | Hand-rolled validator | Only if the schema will never be published, reused by AUTO-01, or consumed by external tooling |
| Optional extra `[validate]` | Hard runtime dep | Only if ALL callers are guaranteed to want validation (e.g., if `--validate` becomes default-on in a future version) |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `jsonschema` >= 4.18.0 | Requires Python >= 3.8; breaks stated Python 3.7+ compat constraint | `fastjsonschema` 2.21.2 |
| `jsonschema` 4.26.0 | Requires Python >= 3.10 and adds `rpds-py` (Rust extension); 4 transitive deps | `fastjsonschema` 2.21.2 |
| `python-jsonschema-objects` | Code-generation tool, not a validator | `fastjsonschema` or `jsonschema` |
| Any Node test runner for MAKE-FIX-01 / CONTRACT-01 | Deferred by explicit v1.1 decision; adds toolchain complexity disproportionate to two small files | Manual verification against `quizify-submissions.csv` sample |

---

## Version Compatibility

| Package | Python constraint | Notes |
|---------|-------------------|-------|
| `fastjsonschema` 2.21.2 | None declared (`requires_python` absent) | Tested from 3.3+; docs confirm 3.3+; safe for 3.7+ |
| `jsonschema` 4.17.3 | `>=3.7` | Last 3.7-compatible release; frozen at this version means no upstream security patches |
| `jsonschema` 4.18.0+ | `>=3.8` | Dropped 3.7 in this release |
| `jsonschema` 4.26.0 | `>=3.10` | Current latest; incompatible with project constraint |

---

## Schema Design Note (VALI-01 integration point)

The schema file should live at `quizify-csv-to-json-webhook/schema/quizify-webhook.schema.json` (Draft-07). Validation hooks into `convert()` in `quizify_csv_ingest.py` after `build_row()` returns and before `results.append(row_dict)`. The compiled validator object is created once before the row loop when `args.validate` is True, and called per-row. Schema violations exit non-zero (consistent with existing `exit_code |= 1` pattern for row-length mismatches).

Key schema constraints to encode:
- Required top-level keys: contact block (`email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`), `tags` (array), `quiz_title` (string), at least one `question-1`/`answers-1`/`answers-tags-1` triple, scoring trio (`result-logic`, `score-category`, `score-value`), four reserved placeholders (`product-recommendation`, `product-link-type`, `title`, `type-page-url`).
- `patternProperties` for the `question-N`/`answers-N`/`answers-tags-N` triples using `^question-\d+$` etc.
- Do NOT validate question text values or answer content — only structural envelope.

---

## Sources

- `/python-jsonschema/jsonschema` (Context7) — version history, Python compat, transitive deps (HIGH confidence)
- `/websites/horejsek_github_io_python-fastjsonschema` (Context7) — version, Python compat, draft support (HIGH confidence)
- PyPI API `https://pypi.org/pypi/jsonschema/4.17.3/json` — `requires_python` and `requires_dist` verified directly (HIGH confidence)
- PyPI API `https://pypi.org/pypi/fastjsonschema/2.21.2/json` — `requires_python` (absent) and `requires_dist` (devel-only extras) verified directly (HIGH confidence)
- `pip index versions jsonschema` / `pip index versions fastjsonschema` — current latest versions confirmed locally (HIGH confidence)

---
*Stack research for: Quizify CSV → Webhook JSON CLI, v1.1 Contract Hardening additions*
*Researched: 2026-05-03*
