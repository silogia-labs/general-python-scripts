# Pitfalls Research

**Domain:** Python stdlib CLI + co-owned Make.com JS consumer — v1.1 contract hardening addition
**Researched:** 2026-05-03
**Confidence:** HIGH — all findings grounded in direct code inspection of `quizify_csv_ingest.py`, `quizify-mapping.js`, `score-calculations.js`, and the full v1.0 test suite

---

## Critical Pitfalls

### Pitfall 1: `additionalProperties: false` breaks dynamic-column tolerance (VALI-01)

**What goes wrong:**
The schema rejects any row that has more than the locked set of keys, which means adding a 21st Quizify question column causes every run in `--validate` mode to exit non-zero — silently, from the user's perspective — until they figure out why.

**Why it happens:**
JSON Schema `additionalProperties: false` is the standard way to enforce a closed contract, but `quizify_csv_ingest.py` intentionally emits `question-N` / `answers-N` / `answers-tags-N` triples for *all* dynamic columns discovered at runtime. There is no fixed N; the quiz may have 20 today and 22 after the operator adds a new question. The schema cannot enumerate all valid key names statically.

**How to avoid:**
Use `patternProperties` for the dynamic triples and `additionalProperties: false` only for the fixed keys outside that pattern. Specifically, the JSON Schema for `question-N`, `answers-N`, and `answers-tags-N` must use `"patternProperties": { "^(question|answers|answers-tags)-[0-9]+$": {} }` alongside the fixed key definitions, with `additionalProperties: false` scoped only to the contact/scoring tail. Alternatively, omit `additionalProperties: false` entirely and only use `required` to gate presence of mandatory fixed keys — this is the safer default for a growing contract.

**Warning signs:**
- `--validate` mode exits non-zero on a real export that works fine without it
- Schema test suite only covers the current 20-question fixture; no test verifies behaviour when K differs

**Phase to address:**
VALI-01 (validation phase) — must be enforced as an acceptance criterion before schema is considered shippable.

---

### Pitfall 2: `required` array covers only a subset of D-05 locked tail keys (VALI-01)

**What goes wrong:**
The schema `required` array lists, say, `email` and `result-logic` but omits `product-recommendation`. A row that silently drops that key passes validation. The D-05 lock in `test_key_order_locked` catches order but not absence at the schema level; these are separate guarantees.

**Why it happens:**
Developers copy-paste a subset of keys from the example payload when writing the schema and miss the four reserved-placeholder keys (`product-recommendation`, `product-link-type`, `title`, `type-page-url`) because those ship as `null` / `""` and feel like optional metadata.

**How to avoid:**
The `required` array in the schema MUST include all eight fixed-tail keys: `result-logic`, `score-category`, `score-value`, `product-recommendation`, `product-link-type`, `title`, `type-page-url`, plus the contact block (`email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags`, `quiz_title`). Cross-reference against `PHASE_3_REQUIRED_KEYS` in `test_structural_invariants.py` — that frozenset is the canonical list and the schema must require at least the same keys. Add a test that intentionally drops each required key one at a time and asserts the schema raises a `ValidationError`.

**Warning signs:**
- Schema `required` list is shorter than `PHASE_3_REQUIRED_KEYS | contact_keys`
- No parametric test that removes keys and expects failure

**Phase to address:**
VALI-01 — schema authoring step, before implementation code is written (TDD: schema test first).

---

### Pitfall 3: First runtime dependency breaks stdlib-only guarantee (VALI-01 + D-13)

**What goes wrong:**
Adding `import jsonschema` at the top of `quizify_csv_ingest.py` causes an `ImportError` on any machine that has not run `pip install jsonschema`, including all CI environments that test the v1.0 "no install required" contract. The `test_structural_invariants.py` module-scoped fixture invokes the CLI via `subprocess.run([sys.executable, str(SCRIPT), ...])`, so it will immediately fail on a clean virtualenv.

**Why it happens:**
It is the obvious import style. The constraint "stdlib-only at runtime" exists in `PROJECT.md` constraints but is easy to overlook when writing a new feature file.

**How to avoid:**
Use a lazy/conditional import: move `import jsonschema` inside the function that performs validation, guarded by a `try/except ImportError` that raises a clear `SystemExit("--validate requires 'jsonschema': pip install jsonschema")`. This preserves v1.0 behaviour for non-`--validate` calls. Add a test that runs the CLI without `--validate` in a subprocess with `jsonschema` absent (monkeypatch `sys.modules`) and asserts exit code 0.

**Warning signs:**
- `import jsonschema` appears at module top-level
- No test covering the "jsonschema not installed" path

**Phase to address:**
VALI-01 — must be a design constraint stated in the plan before implementation begins.

---

### Pitfall 4: PII leakage through `jsonschema` ValidationError messages (T-PII-01 / VALI-01)

**What goes wrong:**
`jsonschema.ValidationError` instances carry a `.instance` attribute containing the failing value. If that value is an email address or phone number (e.g. the `email` field fails pattern validation), and the code logs `str(error)` or `error.message` to stderr, real PII exits to the terminal and potentially to log aggregation.

**Why it happens:**
The natural idiom is `logging.error("Schema validation failed: %s", error)`. `jsonschema`'s default `str(error)` representation includes the instance value in its output.

**How to avoid:**
Log only `error.json_path` (the failing key path) and `error.validator` / `error.validator_value` (what rule failed), never `error.instance` or the full `str(error)`. Add a PII-safety test modelled on the existing `test_logging_pii.py` pattern: construct a payload where the failing field is an email cell, run `--validate`, and assert the email string is absent from stderr.

**Warning signs:**
- `logging.error(..., error)` or `logging.error(..., str(error))` without stripping `.instance`
- No validation-specific entry in `test_logging_pii.py`

**Phase to address:**
VALI-01 — must be part of the error-reporting implementation step; reference T-PII-01 explicitly in the plan.

---

### Pitfall 5: `answers-N` empty-array vs missing-key schema ambiguity (VALI-01 + quizify-mapping.js)

**What goes wrong:**
`quizify-mapping.js` `extractAnswer()` handles both `Array.isArray(answers)` and `typeof answers === "string"` cases — the code tolerates empty arrays, empty strings, and single-item arrays. If the schema only accepts non-empty arrays for `answers-N`, it rejects the empty-string case (`shape_answer("")` returns `""`). If it only accepts strings, it rejects the object-array case. Either direction causes spurious validation failures.

**Why it happens:**
The answer shape heuristic in `shape_answer()` produces three distinct types: `""`, `"multi, select, string"`, or `[{...}]`. A naive schema writer sees the example payload, observes only object arrays, and writes `"type": "array"` — forgetting the string branch.

**How to avoid:**
The schema for `answers-N` must use `anyOf`: `[{"type": "string"}, {"type": "array", "items": {…}}]`. Test against all three branches from `test_answers_key_is_str_or_object_list` (which already validates these shapes at the Python level). The schema tests should import the same test CSV and verify all three shapes pass schema validation.

**Warning signs:**
- Schema `answers-N` definition uses `"type": "array"` without a `anyOf` string branch
- Schema test suite only covers the golden-file example (which happens to use arrays for all non-multi-select answers)

**Phase to address:**
VALI-01 — schema definition step.

---

### Pitfall 6: JSON Schema draft mismatch causes silent rule differences (VALI-01)

**What goes wrong:**
`jsonschema` 4.x defaults to Draft 2020-12. Draft 2019-09 and earlier treat `$schema`, `items` (for tuple validation), and `unevaluatedProperties` differently. If the schema is written against Draft 7 semantics (common copy-paste source) but executed under Draft 2020-12, tuple `items` definitions silently do nothing — validating arrays that should be rejected.

**Why it happens:**
Online JSON Schema examples and the `jsonschema` quickstart often omit `$schema` declarations, so the draft version is implicit and easy to misread.

**How to avoid:**
Declare `"$schema": "https://json-schema.org/draft/2020-12/schema"` explicitly in the schema file and pin `jsonschema>=4.18` in `requirements-dev.txt`. If Draft 7 semantics are needed for any reason, call `jsonschema.Draft7Validator` explicitly rather than `jsonschema.validate()`. Add a test that checks the schema file contains the expected `$schema` URI.

**Warning signs:**
- Schema file has no `$schema` declaration
- `jsonschema.validate()` called without a `cls=` argument

**Phase to address:**
VALI-01 — plan authoring step; state the draft version as a first-class decision.

---

### Pitfall 7: Schema validates serialized JSON differently than Make.com deserializes it (VALI-01)

**What goes wrong:**
Python's `json.dump(..., ensure_ascii=False)` emits literal Unicode (e.g. `"¿Fuiste asignada..."`) while an older `ensure_ascii=True` call (e.g. in tests, or if the flag is inadvertently toggled) emits `¿`. The schema validates the Python-serialized form, not the wire form. If Make.com deserialises the escaped form differently (it shouldn't, but), or if tests compare the escaped string to the unescaped schema, assertions fail for non-obvious reasons.

**Why it happens:**
`ensure_ascii` defaults to `True` in `json.dumps()` but the CLI explicitly passes `ensure_ascii=False`. A future test helper that calls `json.dumps()` without that flag produces a different byte stream, which could trigger a schema assertion that passes in production but fails in test, or vice versa.

**How to avoid:**
All test helpers that construct JSON for schema-validation tests must use the same `json.dumps(obj, indent=2, ensure_ascii=False)` call as the production `convert()` function. Extract a `_serialize(results)` helper in the module that tests can import, so the serialization path is single-source.

**Warning signs:**
- Test helpers using bare `json.dumps(obj)` or `json.dumps(obj, ensure_ascii=True)`
- Schema test failures involving non-ASCII question texts (Spanish characters)

**Phase to address:**
VALI-01 — serialization helper extraction step.

---

### Pitfall 8: `--dry-run` skips validation; schema drift goes undetected until real run (VALI-01)

**What goes wrong:**
`--dry-run` is the operator's preview path. If `--validate` only activates in `convert()` (not `dry_run()`), then operators who always preview before running never hit the schema check. Schema violations accumulate silently and only surface when the operator removes `--dry-run`.

**Why it happens:**
`dry_run()` does not build row dicts; it just classifies headers. Schema validation requires a fully-built row. Naively, validation is placed only in `convert()`.

**How to avoid:**
Document explicitly in the README and plan that `--dry-run` does NOT validate payload shape (it cannot — no rows are built). The canonical preview-with-schema path is `--validate` without `--dry-run`, using a sample CSV. The `--dry-run --validate` combination should either be explicitly prohibited with a clear error, or silently ignored with a WARNING log entry. Either choice must be tested. Do not silently drop the `--validate` flag when `--dry-run` is set.

**Warning signs:**
- No test covering `--dry-run --validate` interaction
- README does not describe which flag combinations are valid

**Phase to address:**
VALI-01 — CLI argument interaction design, documented before implementation.

---

### Pitfall 9: Substring match collision for trailer scoring lookup (TRAIL-01)

**What goes wrong:**
The v1.0 positional lookup (`trailer_cells_decoded[0..2]`) is being replaced with name-based lookup. The name-based lookup searches the trailer header list for substrings like `"score"`. If a future dynamic question column header contains "score" (e.g. "Escala de dolor (score percibido)") and somehow leaks into the trailer list, or if the substring check is too broad, the wrong cell is mapped to `score-value`.

**Why it happens:**
The current `DEFAULT_TRAILER` tuple is `("Result logic", "Score category", "Score value", "Answer tags", "Time to complete (mm:ss)", "Date")`. A substring match for `"score"` hits both "Score category" (index 1) and "Score value" (index 2). If the match iterates in order, the first hit wins — miscategorising both. The match must be for the *full canonical name* (NFC+casefold), not a substring.

**How to avoid:**
Name-based lookup for TRAIL-01 must use exact NFC+casefold equality (`normalize_key(header) == normalize_key(canonical_name)`), not substring containment. The three scoring trailer keys to locate are `"Result logic"`, `"Score category"`, and `"Score value"` — match these exactly, not by partial string. The lookup should build a position map `{canonical_name: index}` once per CSV and assert all three are found or raise a `LayoutError`.

**Warning signs:**
- Lookup code uses `.contains()` or `in` operator against trailer header strings
- No unit test covering a trailer list that contains "score" in two different headers

**Phase to address:**
TRAIL-01 — implementation and unit test authoring.

---

### Pitfall 10: Silent fallback to positional behaviour preserves the v1.0 mis-bind bug (TRAIL-01)

**What goes wrong:**
The temptation is: "if name lookup fails, fall back to `trailer_cells_decoded[0..2]`." This is the exact bug TRAIL-01 is meant to fix. A fallback silently re-introduces positional mis-binding for any `--trailer-columns` invocation where the names don't match.

**Why it happens:**
Defensive programming instinct. The developer doesn't want the CLI to crash if the CSV has an unexpected trailer, so they add a fallback. The fallback is indistinguishable from the broken v1.0 behaviour.

**How to avoid:**
In `--validate` mode: name lookup failure is a hard `LayoutError`. Without `--validate`: emit a WARNING to stderr that names the missing canonical header and populate the field with `""` (same as a missing optional cell), not by falling back to positional index. Document this change explicitly in the MILESTONES.md entry as a user-facing behaviour change (bugfix). Add a test: pass a custom `--trailer-columns` list with scrambled order, assert the scored fields map to the correct values regardless of position.

**Warning signs:**
- Lookup code has an `except`/`or` branch that falls back to an integer index
- MILESTONES.md does not note the behaviour change for `--trailer-columns` users

**Phase to address:**
TRAIL-01 — plan authoring; flag as backwards-compat note from the start.

---

### Pitfall 11: Case/diacritic normalization mismatch between `TAG_HEADER_MAP` and trailer lookup (TRAIL-01)

**What goes wrong:**
`TAG_HEADER_MAP` keyword matching uses `_norm_for_match()` = `unicodedata.normalize("NFC", s).casefold()`. If the new name-based trailer lookup uses a different normalization (e.g. `.lower()` instead of `.casefold()`, or NFC vs NFD), headers with accented characters (Spanish) silently fail to match.

**Why it happens:**
It is easy to write `header.lower() == canonical.lower()` when the existing `normalize_key()` and `_norm_for_match()` functions are slightly different and the developer uses the wrong one for the trailer lookup.

**How to avoid:**
TRAIL-01 implementation MUST reuse `_norm_for_match()` (NFC + casefold) for all name comparisons — not `normalize_key()` (which only does NFC without casefold) and not bare `.lower()`. Add a unit test where the trailer header contains a capital letter or an accented character variant (e.g. `"Score Category"` vs `"score category"`) and assert the lookup succeeds.

**Warning signs:**
- Trailer lookup code uses `.lower()` rather than `.casefold()`
- Trailer lookup uses `normalize_key()` rather than `_norm_for_match()`

**Phase to address:**
TRAIL-01 — implementation step.

---

### Pitfall 12: `product_result` ghost key in `quizify-mapping.js:103` (CONTRACT-01)

**What goes wrong:**
Line 103 of `quizify-mapping.js` reads `record.product_result || null`. The Python CLI never emits a `product_result` key — D-05's locked tail uses `product-recommendation` (hyphenated). This line always evaluates to `null` and was presumably intended to read `record["product-recommendation"]`. Line 102 already reads `record["product-recommendation"]` correctly, so line 103 is a silent dead-code duplicate with a wrong key name. If line 102 is removed during a future refactor (confusing it with the duplicate), the `product_recommendation` output field silently becomes null for all records.

**Why it happens:**
The key was renamed at some point during v1.0 development (from underscore to hyphen convention) and the JS was not updated. Both keys look plausible; the bug is invisible at runtime because JavaScript returns `undefined` for missing object keys, which `|| null` coerces to `null`.

**How to avoid:**
CONTRACT-01 removes line 103 entirely (or renames it to something intentional if there was a reason to have both). Add a manual verification note to the CONTRACT-01 plan: run the JS against `quizify-submissions.csv` sample and assert `product_recommendation` is non-null for rows where the Python emits a non-null `product-recommendation`. The `docs/quizify-submissions.csv` sample currently has `product-recommendation: null` for all rows (per `test_every_row_has_reserved_placeholders`), so you need a synthetic fixture with a non-null value to verify the fix.

**Warning signs:**
- `product_recommendation` is `null` in Make.com output even after fix
- No test fixture with a non-null `product-recommendation` value

**Phase to address:**
CONTRACT-01 — implementation and manual-verification plan.

---

### Pitfall 13: `peri_menu` vs `peri-menu` tag mismatch breaks `is_peri_meno` life-stage (MAKE-FIX-01)

**What goes wrong:**
`quizify-mapping.js:167` calls `process_filter_tag(output.menopause_status, "peri", "peri_menu")`, which pushes the tag `"peri_menu"` (underscore). `score-calculations.js:213` checks `hasTag(tags, "peri-menu")` (hyphen). These never match. Every peri-menopausal respondent gets `life_stage = "life_stage_unspecified"` instead of `"peri_menopause_menopause"`. The fix must pick one spelling and apply it to both files.

**Why it happens:**
The two files were written independently. JS object-property naming conventions in `quizify-mapping.js` favour underscores for emitted tag names (see `"has_red_flags"`, `"is_athlete"`, etc.). Someone used a hyphen in the `hasTag` check in `score-calculations.js` without checking the emitting side.

**How to avoid:**
The canonical spelling is `peri_menu` (underscore) to match all other tag names in `quizify-mapping.js`. Fix `score-calculations.js:213` to use `hasTag(tags, "peri_menu")`. Do NOT change `quizify-mapping.js:167` — that is the emitting side and the canonical source. After the fix, confirm with the user whether any Airtable formula or email-template condition currently checks for `"peri-menu"` (hyphen); if so, that consumer also needs updating. Add this to the manual verification checklist.

**Warning signs:**
- `life_stage` is always `"life_stage_unspecified"` for peri-menopausal respondents in Make.com output
- No peri-menopausal respondent in `quizify-submissions.csv` sample to catch the bug in manual testing

**Phase to address:**
MAKE-FIX-01 — implementation; requires sample-coverage check before closing the plan.

---

### Pitfall 14: `is_athlete` inverted condition — fixing it changes customer-facing email routing (MAKE-FIX-01)

**What goes wrong:**
`score-calculations.js:247-250`:
```js
let activity_profile = "non_athlete";
if (!data.is_athlete) {
    activity_profile = "athlete";
}
```
This is logically inverted: `!is_athlete` sets `"athlete"`. All non-athlete respondents have received `activity_profile = "athlete"` since the module was deployed. `email_template_id` is NOT gated on `activity_profile`, so email routing is unaffected — but `activity_profile` is pushed into `out.tags` and flows to Airtable. Any Airtable view or automation that filters by `activity_profile == "athlete"` is currently selecting non-athletes.

**Why it happens:**
A copy-paste inversion. The variable initialized to `"non_athlete"` suggests the intent was `if (data.is_athlete) { activity_profile = "athlete"; }`.

**How to avoid:**
Before merging this fix, confirm with the user: (a) Is `activity_profile` used in any active Airtable formula, automation, or view? (b) Has any email campaign been segmented by `activity_profile`? If yes, the fix changes which real users are in which segment — this is a customer-facing semantic change, not just a code fix. Document the decision in `PROJECT.md` Key Decisions. Only after user confirmation, fix the condition to `if (data.is_athlete)`. The MAKE-FIX-01 plan must include a "user confirmation gate" before merging.

**Warning signs:**
- No user sign-off before the fix is merged
- No note in MILESTONES.md about the semantic behaviour change
- `is_athlete` in `data` is `false` for all rows in the sample (peri-only quiz respondents), so the test cannot distinguish correct from incorrect behaviour without an athlete respondent in the fixture

**Phase to address:**
MAKE-FIX-01 — requires explicit user confirmation step before implementation.

---

### Pitfall 15: CLI surface drift — `--validate` flag addition breaks D-11 drift test (Cross-cutting)

**What goes wrong:**
`test_readme_help_alignment.py:test_every_flag_named_in_readme` asserts that every long flag produced by `--help` appears in `README.md`. Adding `--validate` to `argparse` without updating the README causes this test to fail. This is the safety net working as designed — but if the developer sees the test failure and "fixes" it by disabling the test or adding the flag text without updating the README structure, the protection breaks.

**Why it happens:**
The developer adds the argument to `argparse`, runs the tests, sees a failure in a "doc test", and treats it as noise. The correct interpretation is: the README must be updated before the test can pass.

**How to avoid:**
State in the VALI-01 plan that README.md must be updated in the same commit that adds `--validate` to `argparse`. The D-11 drift test failure is expected and correct — it is the gate, not the bug. Add a note to the README `## Development` section explaining that the drift test is intentionally strict. Do not add `--help` to the `flags.discard()` set to hide new flags.

**Warning signs:**
- `test_every_flag_named_in_readme` fails after adding `--validate`
- Developer removes the flag from `REQUIRED_SECTIONS` or disables the test

**Phase to address:**
VALI-01 — documentation update is part of the implementation plan checklist, not a separate task.

---

### Pitfall 16: Test count regression or slow-test budget violation (Cross-cutting)

**What goes wrong:**
v1.0 has 71 tests passing in 1.09s using a module-scoped fixture for the 12 structural invariants (single subprocess call). VALI-01 schema tests + TRAIL-01 lookup tests + manual-verification scaffolds add new tests. If each schema test spins up a fresh subprocess, test time balloons past the implicit "fast feedback" budget.

**Why it happens:**
Schema validation tests are easiest to write as end-to-end subprocess tests (mirrors the existing pattern). Adding 10 such tests, each with a 50ms subprocess startup, adds 500ms — already doubling test time.

**How to avoid:**
Unit-test schema validation at the function level: call the Python validation function directly (not via subprocess) from test. Reserve subprocess-based tests for CLI integration scenarios (e.g. exit-code checks for `--validate` flag). Extend the existing module-scoped `emitted_payload` fixture to include schema validation checks, rather than adding a new subprocess per check. The 71-test suite runs in 1.09s; target no more than 2.5s after v1.1 additions.

**Warning signs:**
- New test file has its own `subprocess.run(SCRIPT, ...)` for each parametric schema test
- Total test time exceeds 3s after adding v1.1 tests

**Phase to address:**
All v1.1 phases — each plan should specify whether new tests are unit tests (fast) or integration tests (subprocess); unit tests are preferred for validation logic.

---

### Pitfall 17: `score-calculations.js` recomputes scoring independently from Python `score-value` (Cross-cutting latent risk)

**What goes wrong:**
Python emits `score-value` as a pass-through string from the CSV (`trailer_cells_decoded[2]`). `score-calculations.js` computes `score_total` from scratch using its own `SCORE_RULES` applied to mapped answer fields. These two values are computed independently and may diverge if Quizify's scoring algorithm changes or if the CSV `score-value` column uses different rules. Currently both are emitted (`out.score_total` vs the pass-through `score-value`), so a consumer might use either, not knowing which is authoritative.

**Why it happens:**
The JS scoring was written to recompute scores for Make.com's internal routing. The Python pass-through was written to preserve what Quizify itself computed. These are different pipelines that happen to co-exist.

**How to avoid:**
This is a latent risk — MAKE-FIX-01 scope does not need to fix it, but MUST document it. Add a note to the MAKE-FIX-01 plan or MILESTONES.md: "score_total (JS-computed) vs score-value (Quizify CSV pass-through) are independent values. A post-v1.1 audit should verify whether these agree on the live sample and which is used downstream." Do not silently remove either field.

**Warning signs:**
- `score_total` and `score-value` disagree for rows in `quizify-submissions.csv`
- No documentation of which scoring field is authoritative for email template selection

**Phase to address:**
MAKE-FIX-01 — documentation note only; do not fix in v1.1.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Positional trailer indexing (`trailer_cells_decoded[0..2]`) | Simple, no config | Silently mis-binds if `--trailer-columns` order changes; was TRAIL-01's root cause | Never — already accepted as debt in v1.0; fix in TRAIL-01 |
| Schema `required` listing only "obvious" keys | Faster to write | Silent acceptance of structurally incomplete payloads | Never |
| Module-top `import jsonschema` | Cleaner code | Breaks stdlib-only guarantee for non-validation users | Never — lazy import is required |
| Fallback-to-positional on name-lookup miss | Avoids crash | Re-introduces the exact bug being fixed | Never |
| Using `json.dumps()` defaults in tests | Less typing | `ensure_ascii=True` default diverges from production serialization | Never in schema/roundtrip tests |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Python CLI → Make.com Module 1 | Validate Python output only; forget JS reads it | Run manual verification of `quizify-mapping.js` output after any Python key-name change |
| `quizify-mapping.js` → `score-calculations.js` | Edit Module 1 without checking Module 2 consumers | `process_filter_tag(..., "peri_menu")` output feeds `hasTag(tags, ...)` in Module 2; any tag-name change in Module 1 must update Module 2 |
| `score-calculations.js` → Airtable | Fix inverted condition without checking Airtable segments | `activity_profile` flows to `out.tags`; confirm with user before merging `is_athlete` fix |
| `--validate` flag → README drift test | Add argparse flag, run tests, see "doc test" fail, disable it | README update is part of the same commit; drift test is the gating mechanism |
| `jsonschema` error output → stderr | Log full `str(error)` which includes `.instance` (the cell value) | Log only `error.json_path` + `error.validator`; never `error.instance` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging `jsonschema` `ValidationError` verbatim | PII leakage: failing field value (email, phone) appears in stderr / log aggregator | Filter to `json_path` + `validator` only; add T-PII-01 test for validation errors |
| Emitting PII in `--validate` summary report | Email/name in validation failure summary output | Apply same T-PII-01 pattern: name the key path, not the cell value |
| Schema stored with example payload data | Real user email in schema fixtures | Schema tests must use synthetic fixtures with fake PII; never copy rows from `quizify-submissions.csv` |

---

## "Looks Done But Isn't" Checklist

- [ ] **VALI-01 schema:** `additionalProperties: false` is present AND `patternProperties` covers `question-N`/`answers-N`/`answers-tags-N` — verify schema rejects extra fixed keys but accepts new question columns
- [ ] **VALI-01 schema:** `required` array matches `PHASE_3_REQUIRED_KEYS` union contact keys — verify by parametric drop-key test
- [ ] **VALI-01 import:** `import jsonschema` is inside the validation function, not at module top — verify by running CLI without `--validate` in a venv where `jsonschema` is not installed
- [ ] **VALI-01 PII:** validation error logging omits `.instance` — verify by T-PII-01 pattern test
- [ ] **TRAIL-01 lookup:** name lookup uses exact NFC+casefold equality, not substring — verify with scrambled `--trailer-columns` fixture
- [ ] **TRAIL-01 fallback:** no positional fallback branch — grep for `trailer_cells_decoded[0]` outside the legacy path
- [ ] **CONTRACT-01:** `product_result` dead-key line removed from `quizify-mapping.js` — verify manually that `product_recommendation` is non-null when Python emits non-null `product-recommendation`
- [ ] **MAKE-FIX-01 peri tag:** `score-calculations.js` uses `peri_menu` (underscore) — grep for `peri-menu` (hyphen) and confirm absence
- [ ] **MAKE-FIX-01 athlete:** user has confirmed `activity_profile` behaviour change before merge
- [ ] **Cross-cutting README:** `--validate` appears in README.md `## CLI reference` section before any test run
- [ ] **Cross-cutting sample coverage:** manual verification fixture includes at least one peri-menopausal respondent and one athlete respondent

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `additionalProperties: false` rejects new columns | LOW — schema-only change | Add pattern to `patternProperties`; re-run `--validate` |
| `jsonschema` top-level import breaks CI | LOW | Move import inside function; all other tests unaffected |
| PII in validation error logs | MEDIUM | Audit log aggregator for leaked values; patch logging immediately; rotate any exposed tokens |
| `is_athlete` inverted condition merged without user sign-off | HIGH — customer-facing | Revert commit; audit which Make.com runs used the wrong profile; notify affected Airtable automations |
| `peri_menu` / `peri-menu` mismatch persists post-fix | LOW | Fix one-character change in `score-calculations.js:213`; no Python changes needed |
| D-11 drift test permanently disabled | MEDIUM — loss of safety net | Restore test; update README; add CI note to never disable this test |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `additionalProperties` breaks dynamic columns | VALI-01 — schema design step | Parametric test: K+1 question columns passes `--validate` |
| `required` subset drift | VALI-01 — schema authoring | Parametric drop-key test: each required key missing → `ValidationError` |
| Runtime dependency breaks stdlib guarantee | VALI-01 — plan constraint | Test: CLI without `--validate` works with `jsonschema` absent |
| PII in ValidationError logs | VALI-01 — error-reporting impl | T-PII-01 test: email in failing field → absent from stderr |
| `answers-N` empty/string/array ambiguity | VALI-01 — schema definition | Schema test: all three shapes from `test_answers_key_is_str_or_object_list` pass |
| JSON Schema draft mismatch | VALI-01 — plan authoring | Test: schema file contains expected `$schema` URI |
| `ensure_ascii` serialization divergence | VALI-01 — serialization helper | Test: Spanish-character question text passes roundtrip without entity escapes |
| `--dry-run` + `--validate` interaction | VALI-01 — CLI design | Test: `--dry-run --validate` produces documented behaviour |
| Substring match collision | TRAIL-01 — implementation | Unit test: trailer with two "score" headers; correct cell mapped |
| Silent positional fallback | TRAIL-01 — plan authoring | Test: scrambled `--trailer-columns` → correct field mapping; no fallback |
| Normalization mismatch in lookup | TRAIL-01 — implementation | Unit test: mixed-case + accented trailer header still resolves |
| `product_result` ghost key | CONTRACT-01 — implementation | Manual verification: non-null `product-recommendation` → non-null JS output |
| `peri_menu` vs `peri-menu` | MAKE-FIX-01 — implementation | Manual check: `grep "peri-menu" score-calculations.js` returns nothing after fix |
| `is_athlete` inversion | MAKE-FIX-01 — user confirmation gate | User sign-off recorded in MILESTONES.md before merge |
| CLI surface drift (D-11) | VALI-01 — README update in same commit | `test_every_flag_named_in_readme` passes |
| Test time budget | All phases — unit-test preference | `pytest --tb=short -q` completes in ≤ 2.5s after v1.1 |
| `score_total` vs `score-value` divergence | MAKE-FIX-01 — doc note only | Documented in MILESTONES.md; audit deferred to post-v1.1 |

---

## Sources

- Direct code inspection: `quizify_csv_ingest.py` lines 261-268 (positional trailer indexing), `quizify-mapping.js` lines 102-103 (ghost key), `score-calculations.js` lines 213 and 247-250 (tag mismatch and inverted condition)
- `tests/test_structural_invariants.py` — `PHASE_3_REQUIRED_KEYS` frozenset and `test_key_order_locked` as canonical contract references
- `tests/test_logging_pii.py` — T-PII-01 contract pattern (negative substring assertions)
- `tests/test_readme_help_alignment.py` — D-11 drift test mechanics
- `PROJECT.md` constraints section: "Stdlib-only at runtime; no `requirements.txt` (D-13)"
- `PROJECT.md` key decisions: positional indexing flagged as `⚠️ Revisit` with explicit TRAIL-01 note
- `jsonschema` library behaviour: ValidationError `.instance` attribute carries failing value; confirmed by library design
- `MILESTONES.md` v1.0 stats: 71 tests / 1.09s as the performance baseline

---
*Pitfalls research for: Quizify CSV → Webhook JSON v1.1 Contract Hardening & Make.com Alignment*
*Researched: 2026-05-03*
