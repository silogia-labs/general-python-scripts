# Phase 2: Core webhook mapping - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform each Quizify CSV row into one webhook-shaped JSON object matching `webhook-quizify-format-example.json`: contact fields (`firstName`, `lastName`, `email`, `phone`), subscription state (`status`, `statusDate`), the `tags` source marker, and per-question triples (`question-N`, `answers-N`, `answers-tags-N`) for every dynamic column classified by Phase 1. HTML entities in cells must appear decoded. Scoring fields (`Result logic` / `Score category` / `Score value`), `quiz_title`, `product-recommendation`, and operator README belong to Phase 3 and are out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Per-question tag distribution (Area 1)

- **D-01:** The single CSV `Answer tags` column (comma-separated, e.g. `no_red_flag, goal_athlete, consent_given`) is split per row, then each tag is matched to one of the dynamic question columns and emitted as `answers-tags-N` for that question. Unmatched tags are appended to the row-level `tags` array (with a stderr `WARNING` naming the tag) so no information is silently dropped.
- **D-02:** Matching uses a **configured tag→header-keyword map** shipped in code. Initial map (extend as needed):
  - `red_flag` → header substring `signos de alarma`
  - `goal_` → header substring `objetivo`
  - `consent` → header substring `consiento`
- **D-03:** Match algorithm: case-insensitive, NFC-normalized substring of the *raw* dynamic header text (consistent with Phase 1 D-09 — raw header retained, normalized only for comparison). First matching tag pattern wins; if multiple tags match the same question they join with `, ` in `answers-tags-N`.
- **D-04:** Questions with no matching tag emit `answers-tags-N: ""` (empty string, matching example shape for q-1, q-2, etc.).

### Answer shape (string vs object array) (Area 2)

- **D-05:** **Comma-in-cell heuristic**: if the decoded cell text contains `, ` (comma + space) it is treated as a free-text / multi-select answer and emitted as a **plain string** (matches example q-14 / q-15 / q-16). Otherwise the cell becomes a **single-element array of objects**.
- **D-06:** Object-array element shape: always `{"answer_name": "<decoded cell>", "answer_img": null, "answer_tag": null}`. Uniform across all single-answer questions, matches example q-2..q-20.
- **D-07:** **`id` key is omitted entirely** when unknown (CSV has no ID column) — per WEB-03 and PROJECT.md "omit fallback". Do **not** emit `id: null`. Document this in Phase 3's README.
- **D-08:** Empty cell ⇒ `answers-N` is the empty string `""` (not an empty array, not omitted). See D-09 for index policy.

### Empty / blank cells (Area 3)

- **D-09:** **Always emit all dynamic keys for every row.** For each dynamic column index `N` (1..K from Phase 1), emit `question-N` (verbatim header text), `answers-N` (string `""` if blank, otherwise per D-05/D-06), and `answers-tags-N` (string, possibly `""`). Stable index alignment across rows; downstream consumers can rely on `question-N` always being present.

### Contact, status, and top-level tags (Area 4)

- **D-10:** Contact mapping: `First name → firstName`, `Last name → lastName`, `Email → email` (preserved verbatim, no case normalization), `Phone → phone` (preserved verbatim including leading `+` and spaces).
- **D-11:** **`status`**: `Subscribed to newsletter` cell mapped — `Yes` → `"subscribed"`, `No` → `"unsubscribed"`. Any other non-empty value → `"unsubscribed"` plus a stderr `WARNING` naming the unexpected value. Empty cell → `"unsubscribed"` silently.
- **D-12:** **`statusDate`**: pass the CSV `Date` cell through verbatim (sample export already uses ISO `YYYY-MM-DD`). If a row's `Date` is non-ISO, emit as-is and log `WARNING` (no inventing timezones — defer richer parsing to a later phase if needed).
- **D-13:** **`tags`**: top-level array always starts with `"source: quizify"` (matches example exactly). Unmatched per-row `Answer tags` (D-01 fallback) are appended to this array. No other automatic enrichment.

### HTML entity decoding (Area 5 — derived from CONV-06)

- **D-14:** Decode HTML entities in **every string-typed value** emitted from the CSV (contact fields, `answers-N` strings, object `answer_name`, `Answer tags` values) using `html.unescape`. Decoding happens **after** reading and **before** assembling the JSON object. Headers used as `question-N` are also decoded (rare but possible — e.g. `&gt;` in a question text).

### CLI integration (Area 6)

- **D-15:** Phase 2 stays in the **same `quizify_csv_ingest.py` entrypoint** (Phase 1 D-11 — no subcommands). Default invocation now produces JSON; `--dry-run` keeps Phase 1's layout preview behavior.
- **D-16:** New flags introduced in Phase 2:
  - `-o, --output PATH` — write JSON array to file (UTF-8). Default: stdout (Phase 1 D-01: data on stdout).
  - `--emit-json` — accepted for explicit invocation; redundant with default but useful for self-documenting scripts. **Not** required.
- **D-17:** JSON formatting: pretty-printed with `indent=2`, `ensure_ascii=False` (preserves Spanish accents and decoded entities). Output is a single JSON array (matches example file shape).
- **D-18:** Exit codes: `0` on success, `1` on input/layout errors (existing Phase 1 convention), `2` on CLI usage errors. Per-row errors do not abort: log `WARNING` to stderr, skip the row, continue, and exit `1` at end if any row was skipped.

### Claude's Discretion

- Internal helper module organization (e.g., split `mapping.py` from `cli.py`) — implementation detail.
- Exact log messages and wording.
- Whether `html.unescape` is wrapped in a memoized helper or called inline.
- Whether the tag-map dict lives at module top-level or inside a small `TagMap` dataclass.

### Folded Todos

*(none — no todos matched phase 2)*

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` — CONV-03..06, WEB-01..03 traceability
- `.planning/ROADMAP.md` — Phase 2 goal and success criteria

### Contracts & fixtures

- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — Representative export; rows demonstrate empty cells (red-flag short-circuit), comma-separated multi-select cells, HTML entities (`&gt;`), and consolidated `Answer tags` column shape
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — **Golden-file target** for shape: object-array with `answer_name`/`answer_img`/`answer_tag`, plain-string for multi-select (q-14/15/16), per-question `answers-tags-N`, top-level `tags: ["source: quizify"]`. Note: example contains `id` values absent from CSV — Phase 2 omits `id` entirely (D-07) and downstream consumers must tolerate absence.

### Prior phase context (binding)

- `.planning/phases/01-csv-ingestion-column-layout/01-CONTEXT.md` — Phase 1 decisions carried forward (stderr diagnostics, UTF-8 BOM handling, NFC normalization, raw-header retention, no subcommands, single argparse entrypoint, `--trailer-columns` override)

### Project constraints

- `.planning/PROJECT.md` — Stdlib-first Python (use `html`, `json`, `csv`, `argparse`, `unicodedata` only — no new deps in Phase 2), PII/privacy posture (no row content in default logs)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 1)

- `quizify_csv_ingest.py::classify_headers(header_row, trailer)` returns `(prefix_raw, dynamic, trailer_raw)` — Phase 2 calls this for every input and consumes the `dynamic` list to drive `question-N` indexing (1-based).
- `quizify_csv_ingest.py::normalize_key(s)` — NFC + strip; reuse for tag-map header matching (D-03).
- `quizify_csv_ingest.py::parse_trailer_arg`, `configure_logging`, `LayoutError` — reuse as-is.
- `CONTACT_PREFIX` and `DEFAULT_TRAILER` tuples — Phase 2 maps positions in `prefix_raw` (index 0 = First name, 1 = Last name, 2 = Email, 4 = Phone, 5 = Subscribed) and `trailer_raw` (index 3 = Answer tags, index 5 = Date).
- Existing UTF-8-sig reader pattern in `dry_run` — extract into a shared helper for both modes to avoid divergence.

### Established Patterns

- Stdlib-only (`csv`, `argparse`, `pathlib`, `unicodedata`, `logging`); add `html` and `json` in Phase 2 — both stdlib.
- `print(..., file=sys.stderr)` for diagnostics; `print(...)` (stdout) reserved for JSON output (D-16).
- Privacy: no cell content in default logs (PROJECT.md). Per-row `WARNING` may name the *column* and *unexpected value* but should avoid PII (e.g. log status mismatch as `unexpected status value <redacted>` or only the offending category, not the email).

### Integration Points

- Phase 2 outputs feed Phase 3 directly: Phase 3 will decorate the same per-row dict with `quiz_title`, `product-recommendation`, `product-link-type`, `title`, `type-page-url` and the trailer-derived score fields. Keep the per-row builder modular so Phase 3 can extend it without rewriting.

### Risks / Watchouts

- The example payload's `id` integers cannot be recovered from CSV — D-07 settles this but the README in Phase 3 must call it out so downstream consumers don't silently treat absence as a bug.
- `Subscribed to newsletter` only contains "Yes" in the sample export. The "No"→"unsubscribed" branch is unverified against real data; D-11's warning behavior protects against silent miscoding.
- Tag heuristic (D-02) has only 3 seed entries based on the single example quiz; Phase 2 tests must cover the unmatched-tag fallback path explicitly.

</code_context>

<specifics>
## Specific Ideas / Examples

- **Tag map dict** (D-02 seed):
  ```python
  TAG_HEADER_MAP = {
      "red_flag": "signos de alarma",
      "goal_": "objetivo",
      "consent": "consiento",
  }
  ```
- **Multi-select detection** (D-05): `", " in cell_text` after `html.unescape`. The example confirms: q-14 cell `"Escape de orina al toser/reír/saltar, Dolor en penetración..."` → string; q-2 cell `"Si"` → object array.
- **Empty-row example** (D-09): sample row 1 emits `question-1` through `question-K`, with `answers-N: ""` for blanks beyond q-3.
- **Golden-file test target** (success criterion 2): pick the first sample row that has all dynamic cells filled (row 3 in the export — SCARLETTE 2026-04-29 with full responses) and compare structure (key set, shape per key) against the example payload. Exact `id` values won't match — diff structurally with `id` keys excluded on both sides.

</specifics>

<deferred>
## Deferred Ideas

- HTTP POST / webhook send mode (**AUTO-01**, v2) — out of scope.
- JSON Schema validation (**VALI-01**) — out of scope.
- Subcommands (`convert`, `inspect`) — Phase 1 D-11 still holds; revisit in Phase 3 if scoring + quiz-title flag pressure makes a single parser unwieldy.
- Per-quiz tag-map config file (`--tag-map path.json`) — hold until a second quiz with different tag tokens appears.
- `--status-column` / `--status-map` operator overrides — defer until a real CSV variant breaks D-11.
- ID recovery from a Quizify question-bank export — would require an additional input file; not in v1 scope.

### Reviewed Todos (not folded)

*(none)*

---

*Phase: 2 — Core webhook mapping*
*Context gathered: 2026-05-03*
