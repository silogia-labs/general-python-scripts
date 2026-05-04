# Feature Research

**Domain:** CSV-to-webhook JSON CLI + Make.com JS consumer modules (contract hardening milestone)
**Researched:** 2026-05-03
**Confidence:** HIGH (all findings derived from in-repo source code + in-repo CSV sample; no external ecosystem speculation needed for the JS bug analysis; jsonschema library status verified against known ecosystem state)

---

## Feature Landscape

### Table Stakes (Must Have for v1.1)

Features that are the stated v1.1 goal. Shipping without any of these means the milestone is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| TRAIL-01: Name-based scoring lookup | `--trailer-columns` reordering currently silently mis-binds `result-logic`/`score-category`/`score-value`; the README explicitly warns callers about this (Limitations section). Contract integrity requires removing that footgun. | SMALL | Isolated change in `build_row` signature + `convert` call site. No new CLI flags. Backwards compat preserved by falling back to `""` + WARNING when expected column name is absent. |
| CONTRACT-01: Remove `product_result` dead key from `quizify-mapping.js` | Line 103 emits `product_result: record.product_result \|\| null` into the Make.com module output. The Python CLI never emits a key named `product_result` (D-05 emits `product-recommendation`). The read always resolves to `undefined`/`null` and the key flows downstream to Airtable as a spurious null column. Single-line deletion. | SMALL | One line deleted from `quizify-mapping.js`. Zero Python changes. Verify no other JS file reads `product_result` off the module output object before deleting. |
| MAKE-FIX-01a: Fix peri-menu tag mismatch | `quizify-mapping.js:167` emits tag `"peri_menu"` (underscore); `score-calculations.js:213` checks `hasTag(tags, "peri-menu")` (hyphen). The check always returns false, so every perimenopausal submission is silently assigned `life_stage = "life_stage_unspecified"` instead of `"peri_menopause_menopause"`. | SMALL | One-character fix in `score-calculations.js:213`. See canonical spelling decision below. |
| MAKE-FIX-01b: Fix inverted activity_profile condition | `score-calculations.js:247-250`: `if (!data.is_athlete) activity_profile = "athlete"` is logically inverted. Every non-athlete is tagged `"athlete"` and every athlete is tagged `"non_athlete"`. Downstream email routing and Airtable tagging are wrong for all submissions. | SMALL | Change `!data.is_athlete` to `data.is_athlete`. One character. |
| VALI-01: Opt-in JSON Schema validation | CI/automation pipelines need a fast-fail path to detect contract drift between the Python CLI and downstream consumers. Default off preserves v1.0 permissive behavior; `--validate` / `--validate-schema PATH` enables strict mode. Prerequisite for AUTO-01 (HTTP POST with pre-flight validation) in v1.2. | MEDIUM | Requires adding `jsonschema` as a runtime dependency (first non-stdlib dep). Draft 7 recommended (see VALI-01 detail section). Schema lives at `docs/webhook-schema.json`. Validate pre-emit (block bad output). Error messages report JSON pointer path + expected type, never cell content (T-PII-01 preserved). |

### Differentiators (Nice to Have, Not v1.1 Blockers)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `--validate` also activates on `--dry-run` | Lets operators validate schema compliance against a live CSV before writing output. Useful for CI pre-checks. | SMALL | Extend `dry_run()` path in `main()` to also call the validator when flag is set. Dependency on VALI-01 landing first. |
| Structured validation error output (JSON) | Consumers running in automated pipelines may prefer machine-readable errors over human-readable stderr lines. Add `--validate-output json` sub-option. | SMALL | Post-VALI-01 addition. Defer to v1.2 unless trivial to add alongside VALI-01. |
| Warn (not error) mode for schema violations | `--validate-warn` flag: report violations to stderr but continue and emit JSON. Useful for soft enforcement during migration. | SMALL | Trivially added alongside VALI-01. Decision: skip for v1.1 to keep the flag surface minimal; schema validation is either on (strict) or off. |

### Anti-Features (Explicitly Excluded from v1.1)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| JS test harness (Jest/Vitest for `make-scripts/`) | Would make MAKE-FIX-01 bugs reproducible and regressions catchable | Adds Node.js toolchain, `package.json`, lockfile, and `node_modules` to a Python utility repo. Two short JS files (~500 LOC total) do not justify the overhead. Conflicts with the stdlib-only / minimal-dependency ethos. | Manual verification against `quizify-submissions.csv` sample (see MAKE-FIX-01 section). Revisit if `make-scripts/` grows beyond ~500 LOC or a third JS module is added. |
| `product_result` alias key emitted from Python | "Keep backwards compat for any Make.com module that reads `product_result`" | D-05 key order is locked. Adding an alias key from the Python side would silently override D-05 without an ADR-level decision and bloat every row. The correct fix is on the consumer side (one-line JS deletion). | Fix `quizify-mapping.js:103` (CONTRACT-01). |
| Automatic trailer-column order detection | Infer correct scoring columns by content heuristics (detect numeric strings, ISO dates, etc.) | Fragile: score values like "500", "6", "400" are also plausible in other columns; date detection would be wrong for empty cells. Creates a hidden "magic" behavior harder to debug than the current explicit positional contract. | TRAIL-01 name-based lookup: explicit, verifiable, warns on mismatch. |
| Streaming/NDJSON output | Reduce memory footprint for large exports | Out of scope until a real export exceeds ~50k rows (T-RESOURCE-01 threshold). Current 42-row sample is trivially small. | STREAM-01 deferred to v1.2. |
| HTTP POST delivery mode | Send converted rows directly to a webhook endpoint | Depends on VALI-01 being in place first (gate POST on validation success). Adding network I/O is a larger surface-area change requiring timeout/retry/auth design. | AUTO-01 deferred to v1.2. |

---

## Feature Detail: VALI-01

### JSON Schema draft recommendation: Draft 7

**Rationale:** The `jsonschema` PyPI library (4.x series) supports Draft 4, 6, 7, 2019-09, and 2020-12. Draft 7 is the last pre-restructured draft; it is simpler, has broader tooling support, and is sufficient for validating: object key presence, key types (string, array, null), required field lists, and `additionalProperties: false` on the contact/tail block. Draft 2020-12 adds `prefixItems` for array tuple validation (useful for locked key-order arrays) but that feature is not needed here — key order in JSON Schema cannot be enforced at the object level anyway (JSON objects are unordered by spec); the locked order constraint is an implementation concern, not a schema concern. Recommendation: Draft 7.

### Dependency: `jsonschema`

This is the first runtime dependency beyond stdlib. Justified because:
- No stdlib module validates JSON Schema.
- `jsonschema` is the de facto standard for Python JSON Schema validation with no serious alternatives at comparable maturity.
- Install footprint is small (`jsonschema` + `attrs`/`rpds-py` + `referencing`).
- Add to a new `requirements.txt` (not `requirements-dev.txt`); document explicitly in README.

### Schema scope

The schema validates the **envelope structure** only:
- Contact block: required keys `email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags`, `quiz_title` with correct types.
- Per-question triples: presence of `question-N`, `answers-N`, `answers-tags-N` for each N detected (since N is dynamic, the schema validates patterns using `patternProperties`).
- Tail keys: `result-logic`, `score-category`, `score-value` (strings), `product-recommendation` (string or null), `product-link-type` (string or null), `title` (string), `type-page-url` (string).

The schema does NOT validate:
- Question text values (free-text, quiz-specific).
- Answer values (free-text).
- `score-value` numeric range (intentionally string-typed per D-05).
- Tag content (open-ended list).

### Schema file location

`quizify-csv-to-json-webhook/docs/webhook-schema.json` — co-located with the example payload (`webhook-quizify-format-example.json`). This keeps all contract artifacts together and makes the schema discoverable without knowing the CLI internals.

### Validation timing: pre-emit

Validate each row dict **before** appending to `results` (or validate the full array before writing). Pre-emit is preferred because:
- Prevents writing a partially-valid output file that a downstream consumer might partially ingest.
- Consistent with `exit_code |= 1` pattern already used for row-length mismatches.
- Post-emit "warn after writing" creates a confusing state where a bad file exists on disk.

`--dry-run` should also validate when `--validate` is set (flag combination is useful for CI pre-checks without writing output).

### Error message surface (PII-safe)

Schema violations report:
- JSON Pointer path to the violating key (e.g., `/0/email` — key name only, not value).
- Expected type/constraint (e.g., `expected string, got null`).
- Row index (integer, not cell content).

Never log the violating value itself (T-PII-01). `jsonschema.ValidationError.path` gives the deque of path components; `.message` gives the schema-level description without the instance value if formatted carefully. Wrap with a PII-safe formatter that strips `.instance` from the error output.

---

## Feature Detail: TRAIL-01

### Current behavior (v1.0)

`build_row` receives `trailer_cells_decoded: list[str]` and binds positionally:
- `result-logic` ← `trailer_cells_decoded[0]`
- `score-category` ← `trailer_cells_decoded[1]`
- `score-value` ← `trailer_cells_decoded[2]`
- `statusDate` ← `trailer_cells_decoded[5]`

The default trailer tuple is `("Result logic", "Score category", "Score value", "Answer tags", "Time to complete (mm:ss)", "Date")`. Positions 0-2 and 5 are correct for the default order. But if `--trailer-columns` is used with a different order, the bindings silently mis-assign.

### TRAIL-01 implementation approach

Change the `build_row` signature to accept a `trailer_map: dict[str, str]` (column name → decoded cell value) instead of (or in addition to) the positional list. The `convert` function builds the map via `zip(trailer_raw_headers, trailer_cells_decoded)` before calling `build_row`. Lookups inside `build_row`:

```python
result_logic = trailer_map.get("Result logic", "")
score_category = trailer_map.get("Score category", "")
score_value = trailer_map.get("Score value", "")
status_date = trailer_map.get("Date", "")
answer_tags_csv = trailer_map.get("Answer tags", "")
```

When a key is absent (non-default `--trailer-columns` that omits the column), emit `""` and log a WARNING naming the missing column — not its value (PII-safe). The warning text: `"trailer column 'Result logic' not found in --trailer-columns; emitting empty string"`.

### Backwards compatibility

Callers using default behavior (no `--trailer-columns`) are unaffected — the default tuple produces the same name→value mapping as before. The positional indices are now implicit in the map rather than explicit in the code, but the output is identical. No semver bump needed.

Callers using `--trailer-columns` in non-default order: they were getting silently wrong values before (a bug). The new behavior gives them correct name-based values — this is a fix, not a breaking change.

---

## Feature Detail: CONTRACT-01

### What the bug is

`quizify-mapping.js` lines 101-103:

```javascript
product_recommendation: record["product-recommendation"] || null,
product_result: record.product_result || null,
```

Line 101 (`product_recommendation`) is correct — it reads the Python CLI's `product-recommendation` key.
Line 102 (`product_result`) is a typo/duplicate — `record.product_result` does not exist in the Python output. It always resolves to `undefined`, producing `product_result: null` in the Make.com module output.

### Verification before fix

Search both JS files for any reference to `product_result` as a reader (i.e., does `score-calculations.js` or any other module read `data.product_result`?). If yes, the fix is to also remove/rename that reader. If no, the key is entirely dead and should be deleted from the output object in `quizify-mapping.js`.

From reading `score-calculations.js` in full: there is no reference to `product_result` anywhere. The key is dead. Safe to delete line 103 from `quizify-mapping.js`.

### Was `product_result` intentional?

No. Evidence: (1) the Python CLI's locked D-05 key order documents `product-recommendation` (hyphen) as the canonical key; (2) line 101 already correctly maps `product-recommendation`; (3) `score-calculations.js` never reads `product_result`; (4) PROJECT.md decision log explicitly states "CONTRACT-01 fixes the Make.com side rather than emitting an alias key from Python." The underscore key is a copy-paste artifact from JS dot-notation habit (JS cannot use `record.product-recommendation` due to the hyphen, so the author used bracket notation on line 101 but apparently also tried a dot-notation variant on line 102 without noticing the name was wrong).

---

## Feature Detail: MAKE-FIX-01

### Bug A: Peri-menopause tag mismatch

**Emitter** (`quizify-mapping.js:167`):
```javascript
process_filter_tag(output.menopause_status, "peri", "peri_menu")
```
This calls `add("peri_menu")` (underscore) and sets `output.is_peri_menu = true`.

**Checker** (`score-calculations.js:213`):
```javascript
const is_peri_meno = hasTag(tags, "peri-menu");
```
Checks for `"peri-menu"` (hyphen). Never matches `"peri_menu"`. Result: `is_peri_meno` is always `false`; `life_stage` is always `"life_stage_unspecified"` for perimenopausal submissions.

**Canonical spelling decision: `peri_menu` (underscore)**

Rationale — tag naming convention in the entire codebase uses underscores for compound tag names:
- `has_red_flags` (underscore)
- `goal_athlete` (underscore)
- `consent_given` (underscore)
- `no_red_flag` (underscore)
- `no_pelvic_symptom` (underscore, seen in CSV sample)
- `goal_sleep`, `goal_sex_life` (underscore)
- `has_red_flags`, `has_triggers`, `has_limitations`, `has_pelvic_symptoms` (underscore)

No hyphenated compound tag exists anywhere in the emitter, the CSV sample, or `score-calculations.js` except for the single `"peri-menu"` in the checker. The emitter side (`peri_menu`) aligns with the convention. Fix is in the checker.

**Fix:** `score-calculations.js:213` — change `"peri-menu"` to `"peri_menu"`.

Also check: `score-calculations.js` uses `life_stage` value `"peri_menopause_menopause"` as a string pushed to `tags` (line 279). This is the life-stage profile string, not the diagnostic tag — it is distinct from `peri_menu` and is not broken.

### Bug B: Inverted activity_profile condition

**Current code** (`score-calculations.js:247-250`):
```javascript
let activity_profile = "non_athlete";
if (!data.is_athlete) {
    activity_profile = "athlete";
}
```

`data.is_athlete` is set to `true` by `process_filter_tag(output.sport_level, "alto", "athlete")` in `quizify-mapping.js:163` when `sport_level` contains "alto". It is `false`/`undefined` otherwise.

Current behavior: every submission where `data.is_athlete` is falsy (the non-athlete majority) gets `activity_profile = "athlete"`. Every submission where `data.is_athlete === true` (an actual athlete) gets `activity_profile = "non_athlete"`. All submissions are mis-tagged.

**Fix:** change `!data.is_athlete` to `data.is_athlete` at line 248.

### Manual verification approach (no JS test harness)

Steps to verify all four JS fixes against the live CSV sample before closing v1.1:

1. Identify representative rows from `quizify-submissions.csv` for each fix:
   - **Perimenopausal row:** row 10 (Karen Retamal) — `Perimenopausia/Menopausia` = `"Perimenopausia"`. After fix, `is_peri_meno` must be `true` and `life_stage` must be `"peri_menopause_menopause"`.
   - **Non-perimenopausal row:** row 4 (SCARLETTE MONROY, 3rd submission) — `Perimenopausia/Menopausia` = `"No aplica"`. After fix, `is_peri_meno` must remain `false`.
   - **Athlete row:** row 1 (Silveimar Paez in example payload) — `Nivel de deporte` = `"Recreacional 2-3x/sem"` (does not contain "alto"). Expected: `is_athlete = false`, `activity_profile = "non_athlete"`. (No "alto" row is present in the 10-row sample; document that "alto" sport level triggers athlete profile.)
   - **Non-athlete row (majority):** any row without "alto" in `sport_level`. After fix, `activity_profile = "non_athlete"`.
   - **product_result key:** run `quizify_csv_ingest.py docs/quizify-submissions.csv` and verify `jq '.[0] | has("product_result")'` returns `false` (already true from Python side). Then verify `quizify-mapping.js` output object no longer has `product_result` key after fix.

2. For the JS verification, manually paste a representative JSON row (from `python quizify_csv_ingest.py docs/quizify-submissions.csv -o /tmp/out.json`) into the Make.com Code module test console and inspect the output object. Check `life_stage_profile`, `activity_profile`, `is_peri_meno`, and absence of `product_result`.

3. Document expected vs actual shape in the phase VERIFICATION file.

---

## Feature Dependencies

```
TRAIL-01 (name-based trailer lookup)
    └── independent of VALI-01 (can ship in either order)
    └── depends on: v1.0 trailer classification (classify_headers) — already shipped

CONTRACT-01 (remove product_result key)
    └── independent of all other v1.1 features
    └── depends on: confirming score-calculations.js does not read product_result

MAKE-FIX-01a (peri_menu tag fix)
    └── depends on: CONTRACT-01 being understood (same JS file review)
    └── independent of VALI-01 and TRAIL-01

MAKE-FIX-01b (activity_profile inversion)
    └── independent of all other v1.1 features

VALI-01 (JSON Schema validation)
    └── depends on: TRAIL-01 (if TRAIL-01 changes output shape, schema must reflect final shape)
    └── enables: AUTO-01 in v1.2 (HTTP POST gated on validation success)
    └── requires: jsonschema PyPI dependency (first runtime dep)
```

### Dependency Notes

- **VALI-01 should land after TRAIL-01:** If TRAIL-01 changes how scoring keys are populated (they should not change value, only reliability), the schema should be written against the final stable output shape. In practice TRAIL-01 does not change output shape, only internal lookup strategy, so the order is flexible — but TRAIL-01 first is lower risk.
- **CONTRACT-01 and MAKE-FIX-01 are JS-only:** they have no Python changes and do not interact with VALI-01 or TRAIL-01. They can be planned and shipped in the same phase or a dedicated JS-fix phase.
- **MAKE-FIX-01a and MAKE-FIX-01b are independent** of each other and can be fixed in a single commit.

---

## MVP Definition

### v1.1 Launch With

- [x] TRAIL-01: Name-based scoring lookup — eliminates silent mis-bind risk documented in README; required for contract integrity
- [x] CONTRACT-01: Remove `product_result` dead key — eliminates spurious null column in downstream Airtable; one-line deletion
- [x] MAKE-FIX-01a: Fix `peri_menu` tag check — correctness bug affecting all perimenopausal submissions' life-stage routing
- [x] MAKE-FIX-01b: Fix inverted `activity_profile` — correctness bug affecting all submissions' activity routing and email template selection
- [x] VALI-01: Opt-in JSON Schema validation — required to enable AUTO-01 in v1.2; provides CI fast-fail path

### Add After v1.1 (v1.2 candidates)

- [ ] AUTO-01: HTTP POST delivery mode — depends on VALI-01; deferred per PROJECT.md
- [ ] STREAM-01: Streaming/NDJSON output — deferred pending evidence of >50k-row exports

### Future Consideration (v2+)

- [ ] Local JS test harness (Jest/Vitest) — justified only if `make-scripts/` grows beyond ~500 LOC or a third module is added
- [ ] Multi-quiz configuration (dynamic `TAG_HEADER_MAP` per quiz) — deferred; single-quiz mapping sufficient through v1.x

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| MAKE-FIX-01b (activity_profile inversion) | HIGH — all submissions mis-routed | LOW (1-char fix) | P1 |
| MAKE-FIX-01a (peri_menu tag) | HIGH — perimenopausal submissions mis-routed | LOW (1-char fix) | P1 |
| CONTRACT-01 (product_result dead key) | MEDIUM — spurious null in Airtable | LOW (1-line deletion) | P1 |
| TRAIL-01 (name-based trailer lookup) | MEDIUM — prevents future mis-bind; current default is fine | LOW (isolated build_row change) | P1 |
| VALI-01 (JSON Schema validation) | MEDIUM — CI safety net; unlocks v1.2 AUTO-01 | MEDIUM (new dep, schema authoring, formatter) | P1 |

All five features are P1 for v1.1. The JS fixes (MAKE-FIX-01a/b, CONTRACT-01) are the highest-leverage items: two single-character fixes and one line deletion that correct live correctness bugs. TRAIL-01 and VALI-01 are the Python-side hardening items.

---

## Sources

- In-repo source code: `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (v1.0 final, 427 lines)
- In-repo JS modules: `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js`, `score-calculations.js`
- In-repo sample data: `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` (rows 1-12 reviewed)
- In-repo contract: `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`
- Project context: `.planning/PROJECT.md` (key decisions D-05, D-07, D-13, D-15; constraints; deferred items)
- Milestone history: `.planning/MILESTONES.md`
- Operator README: `quizify-csv-to-json-webhook/README.md` (Limitations section documents known positional binding risk)

---
*Feature research for: Quizify CSV → Webhook JSON CLI, v1.1 Contract Hardening & Make.com Alignment*
*Researched: 2026-05-03*
