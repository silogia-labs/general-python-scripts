# Phase 5: Python Trailer Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 05-python-trailer-hardening
**Areas discussed:** Position-map placement, Strict trailer check, build_row signature, Missing-column warning

---

## Position-map placement

| Option | Description | Selected |
|--------|-------------|----------|
| Extend classify_headers (Recommended) | classify_headers builds and returns the trio index map alongside its existing header validation; single source of truth for trailer parsing. 4-tuple return (later expanded to 5-tuple in CONTEXT to also surface missing_trio_names). | ✓ |
| New resolver helper called from convert() | resolve_scoring_indices(trailer_headers) → dict, called from convert() right after classify_headers. Keeps classify_headers signature intact but splits parsing from validation. | |
| Per-row inside build_row | build_row receives trailer_headers_decoded and looks up the trio every row. O(rows) lookups; duplicates work; violates Pitfall 9 guidance to build the map once. | |

**User's choice:** Extend classify_headers (Recommended)
**Notes:** Locks classify_headers as the single source of truth for header parsing AND map building. CONTEXT.md expands the return to a 5-tuple to also pass missing_trio_names through to convert() for the warning emit (D-05-07).

---

## Strict trailer check

| Option | Description | Selected |
|--------|-------------|----------|
| Keep strict positional check; add trio map alongside (Recommended) | Existing strict positional validation against --trailer-columns / DEFAULT_TRAILER stays. Trio index map built additionally by name. --trailer-columns retains its meaning as "this is the order in my CSV"; TRAIL-01 just decouples scoring binding from that order. Smallest semantic change; default-order CSVs hit zero new code paths beyond the map build. | ✓ |
| Relax to set-equality (any order, any --trailer-columns) | Drop --trailer-columns ordering as a CSV-shape contract; require only that the trailer SET equals the canonical 6 names. Most permissive; reduces --trailer-columns to a no-op; risks hiding genuine schema drift. | |
| Name-based for trio, positional for the other 3 (split) | Mixed model: trio validated/bound by name in any order; the other 3 cells stay positional. Expressive but harder to reason about; surfaces a 'half-named, half-positional' contract. | |

**User's choice:** Keep strict positional check; add trio map alongside (Recommended)
**Notes:** TRAIL-03 (default-order callers see no behavioral change) is trivially satisfied by this option.

---

## build_row signature

| Option | Description | Selected |
|--------|-------------|----------|
| Add scoring_index_map arg; keep trailer list (Recommended) | build_row(prefix, dynamic, trailer_cells_decoded, dyn_headers, quiz_title, scoring_index_map). Trailer list still passed (used by Answer tags [3] and Date [5]); map dictates which cell maps to result-logic / score-category / score-value. Tests update fixtures to pass {"Result logic": 0, "Score category": 1, "Score value": 2} for default ordering. | ✓ |
| Resolve trio in convert(); pass 3 explicit strings | build_row gets result_logic / score_category / score_value as 3 explicit kwargs. Trio resolution happens upstream in convert(). build_row trailer responsibility halved but every test passes 3 new kwargs. | |
| Switch trailer to dict trailer_by_name | Full conversion: trailer becomes a {canonical_name: cell_value} dict. Most uniform; largest test churn — every existing trailer-list fixture rewritten. | |

**User's choice:** Add scoring_index_map arg; keep trailer list (Recommended)
**Notes:** Minimum churn across the 71-test suite. A single conftest.py fixture (scoring_index_map_default) keeps the test diff mechanical (D-05-06).

---

## Missing-column warning

| Option | Description | Selected |
|--------|-------------|----------|
| Once at startup, named per missing trio column (Recommended) | classify_headers returns missing_trio_names; convert() emits one logging.warning per missing canonical name before the row loop. Format: WARNING trailer column 'Result logic' absent from CSV header; emitting empty string for result-logic in all rows. Clean signal, no per-row noise; matches v1.0 first-only "row length mismatch" precedent. | ✓ |
| Once at startup, single combined warning | One warning listing all missing trio names. Same single-shot ergonomics; less verbose; harder to grep by canonical column name. | |
| Per-row warning with first-only rate-limit | build_row checks scoring_index_map per row and uses a sentinel to fire once per missing column per CSV. Co-locates detection with the empty emit; adds rate-limit state. classify_headers stays oblivious. | |

**User's choice:** Once at startup, named per missing trio column (Recommended)
**Notes:** Emit happens before the row loop, so no rate-limit state-keeping is needed. T-PII-01 satisfied — message contains canonical column name and output key only, no cell content (D-05-08). Empty cells in present columns continue to emit "" silently per D-03 (D-05-09).

---

## Claude's Discretion

- Exact location of the new helper inside `quizify_csv_ingest.py` (top-level function vs. nested inside `classify_headers`).
- Whether `missing_trio_names` is typed as `list[str]` or `tuple[str, ...]`.
- Test-fixture naming for the default scoring index map.
- Commit grouping (single commit for production change + tests, vs. split).

## Deferred Ideas

- **Name-based lookup for non-scoring trailer cells** (Answer tags, Date, Time to complete) — out of TRAIL-01 scope; capture as TRAIL-04 candidate for v1.2 if Quizify reorders the back half of the trailer.
- **Promoting missing-trio columns to a hard LayoutError under `--validate`** — natural Phase 6 extension once the schema declares trio presence as required.
- **Set-equality trailer validation** (drop `--trailer-columns` ordering) — explicitly rejected this phase; capture as v2.0 candidate.
- **Broader MILESTONES.md restyling** — only the TRAIL-03 bugfix note is required here.
