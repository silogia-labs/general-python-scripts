# Phase 2: Core webhook mapping - Research

**Researched:** 2026-05-03
**Domain:** stdlib Python CSV→JSON row mapping
**Confidence:** HIGH

## Phase Summary

Phase 2 turns each Quizify CSV row into one webhook JSON object that matches `webhook-quizify-format-example.json`: contact fields, `status`/`statusDate`, a `tags` array seeded with `"source: quizify"`, and per-dynamic-column triples (`question-N`, `answers-N`, `answers-tags-N`) for `N=1..K` where `K` comes from Phase 1's `classify_headers`. All locked decisions (D-01..D-18) remain frozen in CONTEXT.md — comma-in-cell heuristic for answer shape, configured tag→header-keyword map for per-question tag distribution, `html.unescape` on every emitted string, `id` key omitted entirely, and the same `quizify_csv_ingest.py` argparse entrypoint extended with `-o/--output PATH`. Stdlib only: `csv`, `json`, `html`, `argparse`, `pathlib`, `unicodedata`, `logging`.

## Project Constraints (from CLAUDE.md / PROJECT.md)

- Stdlib-first Python — no new dependencies in Phase 2 (`html` and `json` are stdlib). [VERIFIED: PROJECT.md]
- PII posture: exports are PII; default logs MUST NOT contain row content. [VERIFIED: PROJECT.md]
- `graphify` skill enabled but not relevant to this phase. [VERIFIED: .planning/config.json]
- `nyquist_validation: true`, `security_enforcement: true` (ASVS L1, block on high). [VERIFIED: .planning/config.json]

## User Constraints (from CONTEXT.md)

### Locked Decisions
Verbatim from `02-CONTEXT.md` `<decisions>`:
- **D-01..D-04** Tag distribution: split `Answer tags` on `, `, match each tag to a dynamic question via `TAG_HEADER_MAP` (case-insensitive NFC substring match against raw header), unmatched tags appended to top-level `tags` with stderr WARNING. Multiple tags matching same question join with `, `. No match → `answers-tags-N: ""`.
- **D-05..D-08** Answer shape: comma-in-cell heuristic on decoded text (`", " in cell`) → plain string; otherwise single-element list `[{"answer_name": "<decoded>", "answer_img": null, "answer_tag": null}]`. **`id` key omitted entirely**. Empty cell → `answers-N: ""`.
- **D-09** Always emit all dynamic keys per row (`question-N`, `answers-N`, `answers-tags-N`).
- **D-10** Contact: First name → firstName, Last name → lastName, Email → email (verbatim, no case-fold), Phone → phone (verbatim).
- **D-11** status: `Yes` → `"subscribed"`, `No` → `"unsubscribed"`, other → `"unsubscribed"` + WARNING, empty → `"unsubscribed"` silent.
- **D-12** statusDate: pass `Date` cell verbatim; non-ISO → emit + WARNING.
- **D-13** tags array always starts `["source: quizify"]`; unmatched per-row Answer tags appended.
- **D-14** `html.unescape` on every emitted string (contact, headers used as `question-N`, answers, tag values).
- **D-15..D-18** Same `quizify_csv_ingest.py` entrypoint, `--dry-run` keeps Phase 1 preview, `-o/--output PATH` writes file (default stdout), `--emit-json` accepted (redundant), `indent=2`, `ensure_ascii=False`. Exit 0/1/2 conventions.

### Claude's Discretion
Internal helper module organization (split `mapping.py` from `cli.py` or keep monolithic), exact log wording, whether `html.unescape` is wrapped vs inline, whether tag-map is plain dict or `TagMap` dataclass.

### Deferred Ideas (OUT OF SCOPE)
- HTTP POST send mode (AUTO-01).
- JSON Schema validation (VALI-01).
- Subcommands.
- Per-quiz `--tag-map` config file.
- `--status-column` / `--status-map` overrides.
- ID recovery from Quizify question-bank export.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONV-03 | Map First name/Last name/Email/Phone | D-10; CONTACT_PREFIX positions 0,1,2,4 |
| CONV-04 | Map subscription → status | D-11; CONTACT_PREFIX position 5 (`Subscribed to newsletter`) |
| CONV-05 | Map Date → statusDate | D-12; trailer index 5 |
| CONV-06 | Decode HTML entities | D-14; sample contains `&gt;`, `&lt;` only — `html.unescape` covers both |
| WEB-01 | Build `tags` with source marker + parsed Answer tags | D-13; trailer index 3 |
| WEB-02 | Emit `question-N` / `answers-N` / `answers-tags-N` for each dynamic | D-09; uses Phase 1 `dynamic` list |
| WEB-03 | Choose answer shape (string vs object array, omit unknown id) | D-05..D-07 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSV reading + header classification | CLI / data layer | — | Phase 1 owns; Phase 2 reuses |
| Row → dict transformation | Pure function (mapping) | — | TDD-friendly, no I/O |
| HTML entity decode | Pure function | — | `html.unescape` is pure |
| Tag matching | Pure function | — | data-driven, no I/O |
| JSON serialization | CLI / output layer | — | `json.dump` to stdout or file |
| Logging | CLI / observability layer | — | stderr only |

Single-tier project (offline CLI). No cross-tier confusion possible.

## Reusable Code from Phase 1

**Import as-is** from `quizify_csv_ingest.py`:
- `classify_headers(header_row, trailer)` — returns `(prefix_raw, dynamic, trailer_raw)`. Phase 2 uses `dynamic` length to drive `question-N` indexing (1-based) and uses `trailer_raw` indices to find Date / Answer tags positions.
- `normalize_key(s)` — NFC + strip. Reuse for tag→header substring matching.
- `parse_trailer_arg(s)` — unchanged.
- `LayoutError` — re-raised on invalid header.
- `configure_logging(verbose)` — unchanged.
- `CONTACT_PREFIX`, `DEFAULT_TRAILER` — referenced (positions: contact[0]=First name, [1]=Last name, [2]=Email, [4]=Phone, [5]=Subscribed; trailer[3]=Answer tags, trailer[5]=Date).

**Refactor recommended (planner choice):**
- The CSV-open + reader + header read + classify pattern in `dry_run` SHOULD be extracted into a small helper (e.g., `_open_and_classify(path, trailer) -> (file_handle, reader, header, prefix, dynamic, trailer_h)` or a generator `iter_rows(path, trailer)` yielding `(prefix_cells, dynamic_cells, trailer_cells)` per row). Reason: both `dry_run` and the new `convert` path need exactly this preamble. Duplicating it risks divergent behavior on UTF-8-sig handling, length-mismatch warnings, and exception handling.
- Either keep `dry_run` calling the new helper, or have the helper yield rows and let `dry_run` short-circuit after the header. Pick whichever keeps the diff smallest.

[VERIFIED: read of `quizify_csv_ingest.py` lines 13-113]

## HTML Entity Coverage

**Sample CSV audit** — entities present:
- `&gt;` — appears 38+ times (e.g., `Postpartum &gt; 24 meses`, `&gt; 24 meses`, `&gt; 12 semanas`).
- `&lt;` — appears in `&lt; 6 semanas` (row 30, q-19 column).
- No `&amp;`, `&#xNNNN;`, `&quot;`, `&apos;` found in current sample.

`html.unescape` handles all named HTML entities and numeric character references (`&#NN;`, `&#xNN;`) per Python stdlib. [CITED: docs.python.org/3/library/html.html#html.unescape] HIGH confidence that `&gt;` → `>` and `&lt;` → `<` produce JSON output matching example payload (`"> 12 semanas"`).

**Verification fixture for Phase 2 tests:** assert `"Postpartum &gt; 24 meses"` (raw) → `"Postpartum > 24 meses"` (decoded) and that this string appears in emitted `answer_name`.

## Multi-Select Heuristic Validation

**Heuristic (D-05):** `", " in decoded_cell` → plain string answer; else single-element object array.

**Sample audit — single-answer cells (heuristic must NOT fire):**
- `"55"`, `"35 - 44"`, `"45 - 54"`, `"25 - 34"` (age ranges use ` - `, no comma) ✓
- `"Si"`, `"No"` ✓
- `"Vaginal"`, `"Cesárea"`, `"Postpartum > 24 meses"` (decoded) ✓
- `"7 - 10"`, `"4 - 6"`, `"0 - 3"` (numeric ranges use ` - `) ✓
- `"> 12 semanas"`, `"< 6 semanas"` (decoded) ✓

**Sample audit — multi-select cells (heuristic SHOULD fire):**
None of the sample CSV rows actually contain `", "` inside a quiz answer cell. The sample's multi-select cells use **single space** as separator: e.g. row 11 q-7 = `"Pérdida de control de esfínteres Dolor nocturno que no cede Antecedente de cáncer Debilidad progresiva en piernas"` — Quizify space-joins multi-selects in the CSV, while the example JSON shows `, ` joins.

**CRITICAL FINDING:** The example JSON (q-14, q-15, q-16) shows `"Escape de orina al toser/reír/saltar, Dolor en penetración o examen, Sensación de peso pélvico/prolapso"` — comma-separated. But the **CSV export uses space-joined** multi-selects. This means: against the actual sample CSV, the comma heuristic will essentially never fire — every cell becomes an object-array. The example payload's `", "`-joined strings appear to come from a different export format than the current sample.

**Implication for the planner:**
1. The heuristic as locked (D-05) is correct for inputs that look like the example JSON, but on the current sample CSV it produces object-arrays for every cell — including multi-selects.
2. This is **not a contradiction with locked decisions** — D-05 says "if the cell text contains `, ` it's a string". Sample cells don't contain `, `, so they get object-arrays. The heuristic is permissive: it does the right thing when Quizify exports `", "`-joined cells (matches example) and falls back to object-array when Quizify exports space-joined cells (current sample).
3. Tests MUST cover BOTH: (a) a fixture cell containing `", "` → string; (b) a fixture cell with no `, ` → object array. Don't rely solely on the sample CSV to exercise the string branch.
4. **Watchout to flag in plan:** the space-joined behavior in the actual sample is a Quizify export quirk. Phase 2 emits object-arrays for those cells; downstream consumers expecting comma-joined strings (per the example) may be surprised. This is acceptable for v1 because the locked spec is shape-fidelity to example, not lossless multi-select detection. Document in Phase 3 README. [ASSUMED — based on sample inspection; user has not explicitly acknowledged the space-join quirk, but D-05 was locked with awareness of the example]

**Edge case — false positives:** Could a single-answer cell legitimately contain `", "`? Reviewed all 42 sample rows: no single-answer dynamic cell contains `", "`. Age/numeric ranges all use ` - `. HIGH confidence the heuristic does not produce false positives on this export format.

## Tag Distribution Mechanics

**Algorithm (D-01..D-04):**
1. Read `Answer tags` cell from `trailer_raw[3]` (post-classify).
2. After `html.unescape`, split on `", "` (comma+space). Strip each part. Drop empties.
3. For each tag, scan `dynamic` headers in order. For each header, NFC-normalize + casefold and test if any seeded keyword (also normalized) is a substring. First-matching tag→question pair wins per-tag (D-03).
4. Bucket per question index: if multiple tags match same question, join with `", "` for `answers-tags-N`.
5. Tags with no match → append to top-level `tags` array; emit stderr `WARNING tag '<name>' did not match any question`.
6. Questions with no tag → `answers-tags-N: ""`.

**Seed map (D-02):**
```python
TAG_HEADER_MAP = {
    "red_flag": "signos de alarma",
    "goal_":    "objetivo",
    "consent":  "consiento",
}
```

**Sample audit — tag matches:**
- Row 4 (SCARLETTE full): tags = `no_red_flag, goal_athlete, consent_given`. Matches:
  - `no_red_flag` contains `red_flag` → matches q-3 header `"Reflexiona, ¿has presentado alguno de estos signos de alarma?"` ✓
  - `goal_athlete` starts with `goal_` → matches q-17 `"Mi objetivo principal es..."` (note: header has "objetivo" substring) ✓
  - `consent_given` contains `consent` → matches q-19 `"Consiento que usen mis respuestas..."` ✓
- Row 12 (Claudia): tags = `has_red_flags, no_red_flag` — both contain `red_flag` → both match q-3 → joined `"has_red_flags, no_red_flag"` for `answers-tags-3`.
- Row 17 (Carolina): tags = `no_red_flag, no_pelvic_symptom, goal_athlete, consent_given`. `no_pelvic_symptom` doesn't match any seeded pattern → falls to top-level `tags` + WARNING.
- Rows 6, 21, 28: include `no_pelvic_symptom`, `no_triggers`, `goal_sleep`, `goal_sex_life` — `goal_*` all match `goal_` pattern; `no_pelvic_symptom` and `no_triggers` are unmatched.

**Edge case — tag matched to empty-answer question (research question 4):**
Row 2 (Maria): only first 3 dynamic cells filled (`55`, `Si`, `Debilidad progresiva en piernas`); columns 4..20 are blank. `Answer tags` = `has_red_flags`. Matches q-3 (signos de alarma) — q-3 IS filled in this row, so the tag attaches naturally.

**Recommendation:** **Attach tag regardless of whether the matched question's answer is empty.** Reasons:
1. The tag describes the row, not the cell — a `has_red_flags` tag on a short-circuit submission is meaningful even if subsequent cells are blank.
2. Adding an emptiness predicate would require special-casing and would silently drop information. Locked D-09 already commits to "emit all dynamic keys per row, blank → `""`" — symmetric treatment for tags is consistent.
3. No locked decision says otherwise; fits within Claude's Discretion.

**Substring matching — false-positive check:** Could `red_flag` accidentally match a header that mentions "flag" elsewhere? Sample headers reviewed: only q-3 mentions "alarma" / "signos". No other header contains the seeded keywords. HIGH confidence on current sample.

## Per-Row Build Sequence

Canonical order (decode BEFORE structural decisions):

```
1. Read row from csv.reader.
2. If len(row) != expected_len: log WARNING "row length mismatch", skip row, set exit_code |= 1.
3. Slice row by Phase 1 boundaries: prefix_cells = row[:6], dynamic_cells = row[6:6+K], trailer_cells = row[-6:].
4. Decode every cell via html.unescape (single pass, list comprehension).
5. Build contact fields: firstName/lastName/email/phone from prefix_cells positions 0,1,2,4.
6. Compute status from prefix_cells[5] (D-11 logic).
7. Compute statusDate from trailer_cells[5] (verbatim, optional ISO sanity check).
8. Initialize tags = ["source: quizify"].
9. Split trailer_cells[3] (Answer tags) on ", "; strip; drop empties → tag_list.
10. Match each tag against dynamic headers via TAG_HEADER_MAP; bucket matched tags by question index; collect unmatched.
11. Append unmatched tags to tags[] + WARNING for each.
12. Build per-question keys: for i in range(K):
       N = i + 1
       row_dict[f"question-{N}"] = decoded_dynamic_headers[i]
       cell = decoded_dynamic_cells[i]
       if cell == "":            row_dict[f"answers-{N}"] = ""
       elif ", " in cell:        row_dict[f"answers-{N}"] = cell
       else:                     row_dict[f"answers-{N}"] = [{"answer_name": cell, "answer_img": None, "answer_tag": None}]
       row_dict[f"answers-tags-{N}"] = matched_buckets.get(i, "")
13. Assemble final dict in stable key order (contact → status → statusDate → phone → tags → questions×K).
14. Append to results list.
```

**Critical pitfall — decode ordering:** Decode MUST happen before the comma test. Counter-example: cell `Foo &amp; Bar, Baz`. If you test `, ` on the raw text, it fires (correct here). If you test on already-decoded text `Foo & Bar, Baz`, it also fires (correct). But a cell like `Some &#x2C; thing` (unicode comma char ref) — if decoded, it becomes `Some , thing` and would fire the heuristic. If not decoded, would not. **Decoding first matches the example payload's plain-text expectations** and is consistent with D-14 ("decoding happens before assembling JSON object"). Decode first.

**Header decoding:** Apply `html.unescape` to dynamic headers used as `question-N` values too — D-14 covers headers ("rare but possible"). No matches in current sample but trivial cost.

## JSON Output Mechanics

**Standard call:**
```python
json.dump(results, fh, indent=2, ensure_ascii=False)
fh.write("\n")  # trailing newline for POSIX compatibility
```

[CITED: docs.python.org/3/library/json.html#json.dump]
- `indent=2` — pretty-prints (matches example file).
- `ensure_ascii=False` — preserves Spanish accents (`á`, `é`, `ñ`) and decoded entities natively. Required because example payload has `"¿Fuiste asignada mujer al nacer?"` literal.
- File mode: open with `encoding="utf-8"` (text mode is fine for json).
- For stdout: `json.dump(results, sys.stdout, ...)` then `sys.stdout.write("\n")`. No `print` to avoid double newline.

**Streaming vs accumulation:** Sample is 42 rows, projected production ≤ low thousands. Accumulate into a `list[dict]` and `json.dump` once. Memory cost is trivial (a few MB at 1000 rows). [ASSUMED]

**Threshold for streaming:** If row count exceeds ~50,000 OR per-row payload exceeds ~5KB (yielding >250MB total), revisit with line-delimited JSON (`{...}\n{...}\n`) or `json.dump` per-element with manual array brackets. Document this threshold in code comment; defer actual streaming work to v2 (out of scope per CONTEXT). [ASSUMED]

## Golden-File Comparison Strategy (Plan 02-02)

**Problem:** `webhook-quizify-format-example.json` was hand-crafted for a Silveimar/Paez submission that does not appear in the sample CSV. It also includes `id` integers (e.g., `"id": 100455`) and Phase 3 fields (`quiz_title`, `product-recommendation`, `product-link-type`, `title`, `type-page-url`) that Phase 2 does not produce. Direct equality diff will fail by design.

**Recommended approach: structural assertions, not value equality.**

For each emitted row, assert:
1. **Required keys present:** `firstName`, `lastName`, `email`, `phone`, `status`, `statusDate`, `tags`.
2. **Types:** `tags` is `list[str]` and `tags[0] == "source: quizify"`.
3. **Per question N in 1..K:** keys `question-N`, `answers-N`, `answers-tags-N` all present.
4. **`question-N`** is `str`.
5. **`answers-N`** is `str` (empty or multi-select) OR `list[dict]`. If list: length 1, dict has keys exactly `{"answer_name", "answer_img", "answer_tag"}`, `answer_name` is `str`, `answer_img is None`, `answer_tag is None`. **NO `id` key.**
6. **`answers-tags-N`** is `str`.
7. **No Phase 3 keys present:** `quiz_title`, `product-recommendation`, `product-link-type`, `title`, `type-page-url` are absent.
8. **HTML decode round-trip:** for a row with `Postpartum &gt; 24 meses` source, the emitted answer object's `answer_name` is `"Postpartum > 24 meses"` (no `&gt;` substring anywhere in dumped JSON).

**Golden-file shape diff:** Load example payload, strip `id` keys recursively, strip Phase 3 keys, and assert the SET of keys per object equals what Phase 2 emits for a row with all 20 dynamic cells filled (sample row 4 — SCARLETTE 2026-04-29). This catches accidental key drops or renames without tying tests to specific values.

**Recommended fixture (also separate test):** Construct a minimal in-test CSV string with one row whose dynamic cells exactly mirror the example payload's `answer_name` values. Run the converter, parse output JSON, and assert object-array shape per question. Bypasses the `id` and Phase 3 mismatches because we control the fixture and assert only what Phase 2 owns.

## Test Architecture

**Existing layout** (`quizify-csv-to-json-webhook/tests/`):
- `test_layout.py` — Phase 1 tests; uses `pytest`, imports from `quizify_csv_ingest`, mixes pure-function tests with `subprocess.run` end-to-end tests.

**Phase 2 additions (proposed file split):**

| File | Purpose | Style |
|------|---------|-------|
| `tests/test_mapping.py` | Pure-function unit tests for the row builder (no I/O). TDD-friendly. | `pytest`, direct imports |
| `tests/test_tags.py` | Tag-matching algorithm: seeded matches, multi-tag-same-question join, unmatched-tag fallback, empty-answer-question attachment | `pytest`, direct imports |
| `tests/test_decode.py` | `html.unescape` coverage: `&gt;`, `&lt;`, `&amp;`, no-entity passthrough, decoded-then-comma-detected | `pytest`, direct imports |
| `tests/test_answer_shape.py` | Multi-select heuristic: comma-string fires, no-comma → object array, empty → `""` | `pytest`, direct imports |
| `tests/test_cli_convert.py` | End-to-end: `subprocess.run` against sample CSV, parse stdout JSON, structural assertions, exit codes, `-o/--output` flag, `--dry-run` still works | `pytest` + `subprocess` |
| `tests/test_golden_shape.py` | Golden structural diff against `webhook-quizify-format-example.json` (id-stripped, Phase-3-stripped) | `pytest` + json |

**TDD-first targets:** `test_mapping.py`, `test_tags.py`, `test_decode.py`, `test_answer_shape.py` — pure functions, write tests first.

**Integration-style (write after row builder works):** `test_cli_convert.py`, `test_golden_shape.py`.

**Fixture rows (minimum 3 for Nyquist):**
1. **Full-answers row** (sample row 4 / SCARLETTE 2026-04-29) — exercises every dynamic key, all three tag patterns, HTML entity decoding, status=subscribed.
2. **Red-flag short-circuit row** (sample row 2 / Maria) — only first 3 dynamic cells filled, blank-cell handling, single tag matching first-3-cell question.
3. **Multi-select-string row** (synthesized fixture) — cell containing `", "` to force string-answer branch (sample CSV does not exercise this branch — see Multi-Select Heuristic Validation).

Plus optional fixtures:
4. **Unsubscribed row** — `Subscribed to newsletter = "No"`, asserts `status: "unsubscribed"`.
5. **Unexpected status row** — `Subscribed = "Maybe"`, asserts `status: "unsubscribed"` + WARNING.
6. **Unmatched-tag row** (sample row 17 / Carolina) — `no_pelvic_symptom` falls through to top-level tags + WARNING.

## PII / Logging Constraints

**Safe to log at WARNING (no PII):**
- Column names (e.g., `"Subscribed to newsletter"`).
- Header strings.
- Unexpected categorical values that are NOT free-text PII: e.g., `"unexpected status value 'Maybe'"`, `"unmatched tag 'no_pelvic_symptom'"`, `"row length mismatch: expected 32 fields, got 31"`.
- Row indices (e.g., `"row 17"`).
- Tag tokens (`no_pelvic_symptom`, `goal_athlete`) — these are categorical labels, not PII.
- Date strings if non-ISO (assume operator wants to know about format breaks; not strongly identifying alone).

**MUST NOT appear in default logs:**
- Email addresses, phone numbers, names — never log these.
- Free-text answer cells — could contain quotations of dictated symptoms.
- Combined fields that could re-identify a row (e.g., row index + name).

**Pattern:** When logging a per-row issue, name the *column* and the *category of issue*, never the cell value when the column may contain PII. For cells in tag/status columns (categorical, low-cardinality, non-PII), the value itself is loggable.

**Example messages:**
- `WARNING row 7 column 'Subscribed to newsletter' unexpected value 'Maybe', defaulting to unsubscribed`
- `WARNING row 17 tag 'no_pelvic_symptom' did not match any question; appended to row tags`
- `WARNING row 12 column 'Date' value '04/29/2026' is not ISO YYYY-MM-DD; emitted verbatim`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in use, see `tests/test_layout.py`) |
| Config file | None — pytest discovers `tests/test_*.py` automatically |
| Quick run command | `cd quizify-csv-to-json-webhook && pytest tests/test_mapping.py tests/test_tags.py tests/test_decode.py tests/test_answer_shape.py -x` |
| Full suite command | `cd quizify-csv-to-json-webhook && pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CONV-03 | Contact field mapping | unit | `pytest tests/test_mapping.py::test_contact_fields_mapped -x` | ❌ Wave 0 |
| CONV-04 | Subscribed→status mapping (Yes/No/other/empty) | unit | `pytest tests/test_mapping.py::test_status_mapping -x` | ❌ Wave 0 |
| CONV-05 | Date→statusDate verbatim | unit | `pytest tests/test_mapping.py::test_status_date -x` | ❌ Wave 0 |
| CONV-06 | HTML entity decoding | unit | `pytest tests/test_decode.py -x` | ❌ Wave 0 |
| WEB-01 | tags array shape + unmatched tag fallback | unit | `pytest tests/test_tags.py -x` | ❌ Wave 0 |
| WEB-02 | All N produce 3 keys, in order | integration | `pytest tests/test_cli_convert.py::test_all_question_keys_present -x` | ❌ Wave 0 |
| WEB-03 | Answer shape (string vs object array, no id) | unit | `pytest tests/test_answer_shape.py -x` | ❌ Wave 0 |
| Phase-1 carry-forward | Header layout still rejects bad input | unit | `pytest tests/test_layout.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** quick run command (4 unit-test files, < 5 seconds).
- **Per wave merge:** full suite command (adds CLI + golden, < 30 seconds).
- **Phase gate:** full suite green before `/gsd-verify-work`.

### Signal Classes (Nyquist) and Sample Sizes
| Signal class | Min fixtures | Rationale |
|--------------|-------------|-----------|
| Header layout invariants (Phase 1 carry-forward) | reuse existing | already covered by `test_layout.py` |
| Row-builder pure-function correctness | 3 rows (full / short-circuit / synthesized multi-select) | covers full path, blank-cell path, multi-select branch |
| Tag-mapping correctness | 4 cases (each seeded pattern + unmatched + multi-tag-same-question join) | enumerates the only deterministic branches |
| HTML entity decoding | 3 cases (`&gt;`, `&lt;`, no-entity passthrough; optional `&amp;`) | covers entities present in sample + identity case |
| Multi-select detection | 2 cases (comma-string fires, no-comma → object array) + 1 boundary (cell that is exactly `","`) | binary branch with one boundary |
| End-to-end CLI golden | 1 sample row (row 4 SCARLETTE full) + structural diff | proves integration; structural-only diff per Plan 02-02 |

### Wave 0 Gaps
- [ ] `tests/test_mapping.py` — covers CONV-03, CONV-04, CONV-05
- [ ] `tests/test_tags.py` — covers WEB-01 (incl. unmatched fallback)
- [ ] `tests/test_decode.py` — covers CONV-06
- [ ] `tests/test_answer_shape.py` — covers WEB-03
- [ ] `tests/test_cli_convert.py` — covers WEB-02 + CLI flags + exit codes
- [ ] `tests/test_golden_shape.py` — Plan 02-02 structural diff
- No framework install needed (pytest already used in Phase 1).

## Security Domain

### Applicable ASVS Categories (L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | offline CLI, no auth |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | filesystem perms only |
| V5 Input Validation | yes | strict header layout match (Phase 1), length-mismatch row skip, status enum validation, ISO date pass-through warning |
| V6 Cryptography | no | no secrets, no crypto operations |
| V7 Error Handling & Logging | yes | PII-safe stderr logging (see PII section); exit codes 0/1/2 |
| V14 Configuration | yes | stdlib-only, no untrusted deserialization (csv reader is safe; json.dump only writes — never loads attacker-controlled JSON) |

### Known Threat Patterns for stdlib Python CSV→JSON CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSV injection (formula prefixes `=`, `+`, `-`, `@` in cells) | Tampering | Out of scope for v1 — output is JSON, not Excel-bound. Document in Phase 3 README that downstream consumers re-importing into spreadsheets are responsible for CSV-injection sanitization. |
| HTML/script injection via decoded entities | Tampering | `html.unescape` decodes named entities ONLY — does not execute. Output is JSON strings; downstream consumers responsible for HTML escaping if rendering to web. |
| Path traversal via `-o/--output PATH` | Tampering | Use `pathlib.Path` and `Path.open("w")`; do not interpolate path into shell. argparse already gives a Path object. |
| Resource exhaustion (huge CSV) | DoS | csv.reader streams rows; only the result list accumulates. ≤ low-thousands rows is safe. Document threshold (Phase 2 JSON Output Mechanics section). |
| Information disclosure via logs | Info Disclosure | PII / Logging Constraints section above. |
| Untrusted JSON deserialization | Tampering | N/A — Phase 2 only writes JSON, never reads. |

No HIGH-severity threats applicable to this phase. ASVS L1 satisfied by stdlib defaults + the PII logging discipline.

## Risks / Watchouts

1. **Sample CSV does not exercise the multi-select string branch.** Quizify export uses space-joined multi-selects in the current sample, while the example JSON shows comma-joined strings. Tests MUST construct synthetic fixtures with `", "` cells to exercise that branch. (See Multi-Select Heuristic Validation.)
2. **`No`-status branch is unverified against real data** — sample only contains `Yes`. CONTEXT acknowledges this (D-11 watchout); test with synthesized fixtures.
3. **Tag seeding is minimal (3 patterns).** Real exports already include `no_pelvic_symptom`, `no_triggers`, `goal_*` variants. Unmatched-tag fallback path WILL fire in production; ensure the WARNING is visible but not noisy.
4. **`id` key omission** — must be enforced explicitly in code AND test (`assert "id" not in answer_obj`). Easy to accidentally include if copy-pasting from example.
5. **Header decoding** — applied to `question-N` per D-14. No sample headers contain entities, but apply unconditionally. Test asserts no `&` characters in any emitted `question-N` when source headers have entities.
6. **`Lead Verified` column** is at CONTACT_PREFIX[3] but Phase 2 does NOT emit it (D-10 mapping skips it). Confirm this is intentional silent drop. [VERIFIED: D-10 names only firstName/lastName/email/phone — Lead Verified is intentionally not emitted; matches example which has no such field]
7. **`status: "unsubscribed"` lower-casing** — example uses lowercase `"subscribed"`. Don't accidentally emit `"Subscribed"` from `Yes`. Hardcode the constants.
8. **Plan 02-02 golden file** has Phase 3 fields (`product-recommendation`, etc.) — strip these before comparison; do not let them leak into Phase 2 expectations.
9. **`Lead Verified` value is `"false"` (string)**, not boolean — irrelevant to Phase 2 since not emitted, but worth noting to avoid confusion.

## Code Examples

```python
# Source: PROJECT.md + Python stdlib docs (verified)
import html
import json
import sys
from pathlib import Path

TAG_HEADER_MAP = {
    "red_flag": "signos de alarma",
    "goal_":    "objetivo",
    "consent":  "consiento",
}

def decode_cell(s: str) -> str:
    return html.unescape(s)

def shape_answer(decoded: str):
    if decoded == "":
        return ""
    if ", " in decoded:
        return decoded
    return [{"answer_name": decoded, "answer_img": None, "answer_tag": None}]

def map_status(raw: str) -> tuple[str, str | None]:
    """Returns (status_value, optional_warning_message)."""
    v = raw.strip()
    if v == "Yes":   return ("subscribed", None)
    if v == "No":    return ("unsubscribed", None)
    if v == "":      return ("unsubscribed", None)
    return ("unsubscribed", f"unexpected status value {v!r}")

def match_tags_to_questions(
    tag_csv: str,
    dynamic_headers: list[str],
) -> tuple[dict[int, list[str]], list[str]]:
    """Returns (per_question_tags, unmatched_tags)."""
    matched: dict[int, list[str]] = {}
    unmatched: list[str] = []
    if not tag_csv.strip():
        return matched, unmatched
    norm_headers = [h.lower() for h in dynamic_headers]  # NFC via Phase 1 conventions
    for tag in (t.strip() for t in tag_csv.split(", ") if t.strip()):
        for pattern, header_kw in TAG_HEADER_MAP.items():
            if pattern in tag:
                hit_idx = next(
                    (i for i, h in enumerate(norm_headers) if header_kw in h),
                    None,
                )
                if hit_idx is not None:
                    matched.setdefault(hit_idx, []).append(tag)
                    break
        else:
            unmatched.append(tag)
    return matched, unmatched
```

[VERIFIED: html.unescape, json.dump signatures from docs.python.org]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Streaming threshold ~50k rows / 250MB | JSON Output Mechanics | Low — accumulation works fine for any plausible Quizify export volume |
| A2 | Quizify space-joined multi-selects in sample CSV are an export quirk acceptable for v1 | Multi-Select Heuristic Validation | Medium — if user expects comma-joined output for these cells, the heuristic produces object-arrays instead. Worth confirming in Phase 3 README rather than re-opening D-05 |
| A3 | `Lead Verified` intentionally not emitted (matches example, matches D-10) | Risks #6 | Low — D-10 explicitly enumerates emitted contact keys |

If user wants to revisit A2, that is a CONTEXT-level decision change, not a research correction.

## Required Reading for Planner

Absolute paths the planner MUST load before writing PLAN.md:

- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/.planning/phases/02-core-webhook-mapping/02-CONTEXT.md` — locked decisions
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/.planning/REQUIREMENTS.md` — CONV-03..06, WEB-01..03 traceability
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/.planning/ROADMAP.md` — Phase 2 success criteria
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/.planning/PROJECT.md` — stdlib-first / PII posture
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/.planning/phases/01-csv-ingestion-column-layout/01-CONTEXT.md` — Phase 1 binding decisions
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/quizify-csv-to-json-webhook/quizify_csv_ingest.py` — Phase 1 implementation (reuse surface)
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — fixture
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — golden shape (id-stripped, Phase-3-stripped for Phase 2 comparison)
- `/Users/silveimar/Documents/silogia-repos/general-python-scripts/quizify-csv-to-json-webhook/tests/test_layout.py` — Phase 1 test pattern (pytest + subprocess; mirror this style)

## Sources

### Primary (HIGH confidence)
- Python stdlib docs: `html.unescape`, `json.dump`, `csv.reader` — docs.python.org/3/library/html.html, docs.python.org/3/library/json.html
- In-repo files: `quizify_csv_ingest.py`, `docs/quizify-submissions.csv` (42 rows audited), `docs/webhook-quizify-format-example.json` (20 questions audited), `02-CONTEXT.md`, `01-CONTEXT.md`, `tests/test_layout.py`, `.planning/config.json`, `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`

### Secondary (MEDIUM confidence)
- Sample-based reasoning about Quizify export format quirks (space-joined multi-selects) — observation from current sample only; Quizify could change this format

### Tertiary (LOW confidence)
- Streaming threshold projections (~50k rows / 250MB) — heuristic, not benchmarked

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, all functions verified against Python 3 docs
- Architecture: HIGH — Phase 1 surface is small and read directly from source
- Pitfalls: MEDIUM — sample CSV does not exercise every locked-decision branch (multi-select string, status=No, unmatched tags partially) — mitigated by synthetic fixtures
- Tag matching: HIGH — all sample tags categorized; algorithm deterministic
- Multi-select heuristic: HIGH for false-positive analysis on current sample; MEDIUM on real-world coverage (depends on whether Quizify ever exports `, `-joined cells)

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days; stable stdlib targets, frozen contract files)

## RESEARCH COMPLETE
