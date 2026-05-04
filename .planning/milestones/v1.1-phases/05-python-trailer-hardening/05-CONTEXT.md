# Phase 5: Python Trailer Hardening - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace positional `trailer_cells_decoded[0..2]` indexing in `quizify-csv-to-json-webhook/quizify_csv_ingest.py` with NFC+casefold name-based lookup of the scoring trio (`Result logic`, `Score category`, `Score value`). Any `--trailer-columns` ordering produces correctly-bound scoring fields. A canonical trio column missing from the CSV header / `--trailer-columns` produces an empty string for that field plus one PII-safe `logging.warning` at startup. No positional fallback. Default-order callers see no behavioral change. Existing 71-test suite stays green; new tests cover scrambled order, missing column, and the default-order regression.

**Scope is the scoring trio only.** Non-scoring trailer cells (`Answer tags` at index 3, `Date` at index 5, `Time to complete` at index 4) keep their existing positional access in `build_row`. Retire D-15 in favor of name-based binding.

**Zero JS changes.** Independent of Phase 4 (already shipped); blocks Phase 6 (schema validates the hardened payload shape).

</domain>

<decisions>
## Implementation Decisions

### Lookup Architecture

- **D-05-01 (Position-map placement):** `classify_headers` is the single source of truth — it already validates the trailer header row once at CSV open, so it also builds the trio index map and detects missing trio columns there. New return shape is a 5-tuple: `(prefix_raw, dynamic, trailer_raw, scoring_index_map, missing_trio_names)`, where `scoring_index_map: dict[str, int]` maps `{"Result logic": i, "Score category": j, "Score value": k}` for the canonical names actually present, and `missing_trio_names: list[str]` enumerates absent canonical names. The map keys are the canonical names *as written in `DEFAULT_TRAILER`* (display form), not the normalized form.
- **D-05-02 (Strict trailer check stays):** Existing positional check in `classify_headers` (each CSV trailer header position must match `--trailer-columns` / `DEFAULT_TRAILER` at that position) is preserved. `--trailer-columns` retains its meaning: "this is the order my CSV's trailer is in." TRAIL-01 only decouples the *scoring binding* from that order — it does not change the CSV-shape contract. Default-order CSVs hit zero new code paths beyond the new map build (TRAIL-03 trivially satisfied).
- **D-05-03 (Normalizer reuse):** Trio name comparisons reuse the existing `_norm_for_match` (NFC + casefold) at `quizify_csv_ingest.py:146`. Do NOT introduce a second normalizer; do NOT use `normalize_key` (NFC-only, no casefold) or bare `.lower()` (Pitfall 11). The position-map build does `_norm_for_match(header) == _norm_for_match(canonical)` for each trio canonical name against the trailer header slice.

### `build_row` API

- **D-05-04 (Signature change):** `build_row` gains one new positional-or-keyword arg `scoring_index_map: dict[str, int]`. Full new signature: `build_row(prefix_cells_decoded, dynamic_cells_decoded, trailer_cells_decoded, dynamic_headers_decoded, quiz_title, scoring_index_map)`. Inside, the existing `quizify_csv_ingest.py:263-265` block becomes:
    ```python
    row["result-logic"] = trailer_cells_decoded[scoring_index_map["Result logic"]] if "Result logic" in scoring_index_map else ""
    row["score-category"] = trailer_cells_decoded[scoring_index_map["Score category"]] if "Score category" in scoring_index_map else ""
    row["score-value"] = trailer_cells_decoded[scoring_index_map["Score value"]] if "Score value" in scoring_index_map else ""
    ```
- **D-05-05 (Trailer list still passed):** The full `trailer_cells_decoded: list[str]` argument is kept — `build_row` continues to use it positionally for `Answer tags` (`[3]` for `answer_tags_csv` at line 232) and `Date` (`[5]` for `status_date` at line 226). Out-of-scope cells stay positional.
- **D-05-06 (Test-fixture impact):** All 71 existing tests that call `build_row` directly (primarily `test_row_builder.py`) must add the default-order map `{"Result logic": 0, "Score category": 1, "Score value": 2}` as the new arg. A small `conftest.py` fixture (`scoring_index_map_default`) is the cleanest way to keep the churn mechanical.

### Missing-column Behavior

- **D-05-07 (Warning location):** `convert()` is the warning emitter — `classify_headers` returns `missing_trio_names` and remains pure (no logging side-effects from header inspection). `convert()` iterates `missing_trio_names` once before the row loop and emits one `logging.warning` per missing canonical name. This matches the existing PII-safe stderr discipline and v1.0's first-only "row length mismatch" precedent.
- **D-05-08 (Warning shape):** One warning per missing trio name, exact format:
    ```
    WARNING trailer column 'Result logic' absent from CSV header; emitting empty string for result-logic in all rows
    ```
    The string contains: canonical column name (categorical, locked), the corresponding output key (categorical, locked), and the word "all rows" (categorical). NO cell content, NO row counts, NO email/phone/name. T-PII-01 satisfied.
- **D-05-09 (Empty cell ≠ missing column):** Per existing D-03, when the canonical column IS present in `--trailer-columns` but the cell is empty for a given row, emit `""` silently (no warning). The TRAIL-02 warning fires only on header *absence*, never on cell emptiness. The conditional in D-05-04 distinguishes these cases naturally (`"Result logic" in scoring_index_map` is True when the column exists, regardless of any row's cell content).
- **D-05-10 (No positional fallback — explicit):** When a trio canonical name is absent from `scoring_index_map`, `build_row` emits `""`. It MUST NOT fall back to `trailer_cells_decoded[0]`, `[1]`, `[2]`, or any other positional default. This is Pitfall 10 ("the v1.0 bug wearing a different costume") — the planner must inspect the implementation to confirm no `or trailer_cells_decoded[N]` slipped in. Document this corrected behavior in `MILESTONES.md` under v1.1 as a user-facing bugfix per TRAIL-03.

### Test Strategy

- **D-05-11 (Three new test classes):** (a) **Scrambled-order test** — pass `--trailer-columns "Score value, Result logic, Score category, Answer tags, Time to complete (mm:ss), Date"` (or via `classify_headers` directly with a custom trailer tuple), construct a header matching that order, and assert `row["result-logic"]`, `row["score-category"]`, `row["score-value"]` map to the named-cell values, not the positional [0]/[1]/[2] cells. Verifies TRAIL-01. (b) **Missing-column test** — pass a `--trailer-columns` that omits "Result logic"; assert `row["result-logic"] == ""`, the other two trio fields are bound correctly, and exactly one PII-safe `logging.warning` was captured for `'Result logic'` (no cell content in the message). Verifies TRAIL-02. (c) **Default-order regression** — run the existing 42-row sample with default `--trailer-columns`; output JSON byte-for-byte (or structurally) matches v1.0 output. Verifies TRAIL-03.
- **D-05-12 (Test placement):** Unit-level tests on `classify_headers` and `build_row` directly, not subprocess-driven (per Pitfall 16: "schema-test subprocess flood balloons test time"). Reuse the existing `test_row_builder.py` patterns and `conftest.py` fixtures.

### Carry-forward (locked, not re-asked)

- NFC+casefold equality via `_norm_for_match` — never substring, never `.lower()`, never `normalize_key()` (Pitfalls 9 & 11).
- NO positional fallback — Pitfall 10's "v1.0 bug wearing a different costume" rule.
- T-PII-01 — warnings name canonical column + output key only; no cell content.
- D-03 retained for empty-cell-in-present-column behavior.
- D-05 hyphen-key output convention (`result-logic`, `score-category`, `score-value`) unchanged.
- 71 existing tests must remain green; new tests added on top.
- D-15 (positional trailer indexing rationale) is retired with this phase; update PROJECT.md decisions log accordingly.

### Claude's Discretion

- Exact location of the new `_build_scoring_index_map` helper inside `quizify_csv_ingest.py` (top-level vs nested in `classify_headers`) — planner's call.
- Whether `missing_trio_names` is a `list[str]` or a `tuple[str, ...]` in the return type — planner's call (consistent with existing `tuple[str, ...]` style is fine).
- Test-fixture naming for the default scoring index map — planner's call.
- Commit grouping (single commit for production change + tests, vs. split) — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 5: Python Trailer Hardening" — phase goal, dependencies, four success criteria.
- `.planning/REQUIREMENTS.md` §"Trailer Hardening (TRAIL-XX)" — REQ text for TRAIL-01, TRAIL-02, TRAIL-03 (search for `TRAIL-01`).

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (locked tail-key order), D-15 (positional trailer indexing — being retired this phase), v1.1 entry confirming TRAIL-01 lookup is NFC+casefold equality (NOT substring) with NO positional fallback.
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 (PII-safe stderr); D-03 (empty cells emit "" verbatim, no WARNING).
- `.planning/STATE.md` §"v1.1 locked decisions" — confirms TRAIL-01 normalization choice and forbids positional fallback.

### Pitfalls and known landmines (high-priority read for planner)
- `.planning/research/PITFALLS.md` §"Pitfall 9: Substring match collision" — name match must be exact NFC+casefold equality, never substring; "Score" is a substring of both "Score category" and "Score value".
- `.planning/research/PITFALLS.md` §"Pitfall 10: Silent fallback to positional" — the trap this phase exists to avoid; `or trailer_cells_decoded[N]` is forbidden.
- `.planning/research/PITFALLS.md` §"Pitfall 11: Normalization mismatch" — must reuse `_norm_for_match` (NFC + casefold), not `normalize_key` (NFC-only) or `.lower()`.
- `.planning/research/PITFALLS.md` §"Pitfall 16" — keep new tests at unit level, not subprocess-driven, to preserve the 1.09s test budget.

### Files being edited
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — `classify_headers` (line 51) gains map+missing return; `build_row` (line 199) gains `scoring_index_map` arg; lines 263–265 rewritten; `convert()` (line 310) emits the missing-column warning(s) before the row loop. `_norm_for_match` (line 146) reused as-is.
- `quizify-csv-to-json-webhook/tests/conftest.py` — add `scoring_index_map_default` fixture; existing trailer fixtures remain.
- `quizify-csv-to-json-webhook/tests/test_row_builder.py` — every `build_row(...)` call gets the new arg; new scrambled-order and missing-column tests added.
- `quizify-csv-to-json-webhook/tests/test_layout.py` — `classify_headers` return-arity expectations updated.
- `.planning/MILESTONES.md` (or v1.1 milestone notes file) — TRAIL-03 user-facing-bugfix note for non-default `--trailer-columns` callers.

### Sample / verification fixture
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row sample for the TRAIL-03 default-order regression.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_norm_for_match(s)` at `quizify_csv_ingest.py:146` — `unicodedata.normalize("NFC", s).casefold()`. Use this for every trio name comparison. Already battle-tested via `match_tags_to_questions` (Pitfall 11 alignment).
- `DEFAULT_TRAILER` tuple at `quizify_csv_ingest.py:25-32` — canonical trio names live at indices 0, 1, 2 (`"Result logic"`, `"Score category"`, `"Score value"`). The trio's canonical-name list can be derived as `DEFAULT_TRAILER[:3]` rather than redeclared.
- `LayoutError` at `quizify_csv_ingest.py:35` — keep raising it for the strict positional check (D-05-02). Do NOT raise it for missing trio names; that's a `logging.warning` per D-05-07.
- `logging.warning` pattern in `convert()` (e.g., line 374) — already PII-safe and the right home for the new missing-column warnings.

### Established Patterns
- Pure functions returning tuples — `classify_headers` returning a 5-tuple is consistent with the codebase's "pure header parsing, side-effects in `convert`" split.
- Bounds-checked positional access with `""` default — current line 263–265 pattern (`if len(...) > N else ""`) generalizes cleanly to `if name in scoring_index_map else ""`.
- First-only / once-only logging discipline — see `row_warned` in `dry_run` at lines 294–305. The new missing-column warnings are once-per-CSV by construction (emitted before the row loop), no rate-limit state needed.
- `tuple[str, ...]` typing throughout for ordered name collections — match style.

### Integration Points
- `classify_headers` is called from `dry_run` (line 286) and `convert` (line 344). Both call sites must absorb the new 5-tuple return. `dry_run` discards the new fields with `_`; `convert` keeps them and forwards `scoring_index_map` into `build_row` and iterates `missing_trio_names` for warnings.
- The scoring index map and missing-trio list are computed once at CSV open and passed through `convert`'s row loop unchanged — O(1) per row.

</code_context>

<specifics>
## Specific Ideas

- Default `scoring_index_map` for tests is exactly `{"Result logic": 0, "Score category": 1, "Score value": 2}` — matches `DEFAULT_TRAILER[:3]` positions.
- Missing-column warning string template is locked verbatim (D-05-08); preserve canonical-name capitalization and the `'all rows'` phrasing for grep-ability and downstream operator scripts.
- The TRAIL-03 regression test compares against the existing v1.0 sample output — if a golden-file fixture for the 42-row output already exists in the test suite, reuse it; otherwise generate once and check in alongside this phase's diff.

</specifics>

<deferred>
## Deferred Ideas

- **Name-based lookup for non-scoring trailer cells** (`Answer tags` at index 3, `Date` at index 5, `Time to complete` at index 4) — out of TRAIL-01 scope. If a future Quizify export reorders the back half of the trailer, capture as a follow-on `TRAIL-04` for v1.2.
- **Promoting missing-trio columns to a hard `LayoutError` under `--validate`** — natural Phase 6 extension once the schema declares trio presence as required. Note for the Phase 6 planner: `--validate` may want to upgrade `missing_trio_names` from a warn to a fail.
- **Set-equality trailer validation** (drop `--trailer-columns` ordering as a CSV-shape contract) — explicitly rejected this phase (D-05-02). Capture as a v2.0 candidate if `--trailer-columns` ergonomics ever come up for revisit.
- **MILESTONES.md re-styling** — only the TRAIL-03 user-facing bugfix note is required this phase. Any broader milestone-doc cleanup belongs in a docs phase.

</deferred>

---

*Phase: 05-python-trailer-hardening*
*Context gathered: 2026-05-03*
