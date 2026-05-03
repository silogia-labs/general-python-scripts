# Phase 3: Scoring metadata & packaging - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Finish the per-row webhook dict by adding scoring fields, `quiz_title`, and the example payload's reserved product/result keys; then ship the operator README that documents the whole tool. Concretely: extend `build_row()` (Phase 2) to emit `quiz_title`, `result-logic`, `score-category`, `score-value`, and the four reserved keys (`product-recommendation`, `product-link-type`, `title`, `type-page-url`). Add `--quiz-title` flag plus `QUIZIFY_QUIZ_TITLE` env var. Author `quizify-csv-to-json-webhook/README.md`. No new helper modules unless implementation pressure demands it. Out of scope: HTTP POST mode (AUTO-01 v2), JSON Schema validation (VALI-01 v2), interactive CLI, multi-quiz config files, ID recovery from external sources.

</domain>

<decisions>
## Implementation Decisions

### Scoring field mapping (Area 1)

- **D-01:** **Pass-through to dedicated keys.** Emit `result-logic`, `score-category`, `score-value` carrying the verbatim decoded values from `trailer_cells_decoded[0]`, `[1]`, `[2]` respectively. No invented Score-category→product-recommendation lookup table. Aligns with PROJECT.md "omit fallback" / Phase 2 D-07 "don't invent values".
- **D-02:** **Emit all 4 example reserved keys with example defaults**, since the CSV cannot supply them: `product-recommendation: null`, `product-link-type: null`, `title: ""`, `type-page-url: ""`. Preserves example shape exactly so downstream consumers expecting these keys do not break. README documents them as "reserved — not derivable from CSV export".
- **D-03:** **Empty/missing scoring cells emit `""` verbatim** (consistent with Phase 2 D-08/D-09: empty cell → `""`, key always present). No stderr WARNING for empty scoring — empty trailer cells are a tolerated state, not anomalous. (If a future quiz produces all-empty score columns and that's surprising, surface via dedicated flag in a later phase.)
- **D-04:** **Result logic / Score category / Score value typing: string verbatim.** No int/float coercion of `Score value` (sample shows `"500"`, `"6"` — values may be ordinal tiers, ratios, or measurements; receivers parse if needed). Empty → `""`. Decoded via `html.unescape` like every other CSV-sourced string (Phase 2 D-14).
- **D-05:** **Key ordering: match example payload exactly.** Per-row dict key order:
  1. `email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags` *(Phase 2 D-10..D-13)*
  2. `quiz_title` *(new in Phase 3, position 8)*
  3. `question-N`, `answers-N`, `answers-tags-N` for N=1..K *(Phase 2 D-09)*
  4. `result-logic`, `score-category`, `score-value` *(new pass-through, slotted before placeholders so example shape is a strict superset)*
  5. `product-recommendation`, `product-link-type`, `title`, `type-page-url` *(new placeholders, end-of-dict, matches example positions 183-186)*

### `quiz_title` source & precedence (Area 2)

- **D-06:** **Optional, default `""`.** When neither `--quiz-title` nor `QUIZIFY_QUIZ_TITLE` is set, emit `quiz_title: ""`. Key is always present (consistent with Phase 2 always-emit policy and example shape). No invocation-time error for missing title.
- **D-07:** **Precedence (high → low): CLI flag → env var → future per-CSV column → default `""`.**
  - `--quiz-title FOO` always wins.
  - If flag is absent, read `QUIZIFY_QUIZ_TITLE` env var.
  - If both absent, future-proof for a CSV `Quiz title` column (not present in current sample export — implementation may stub the lookup with a TODO; downstream agents must not invent the column name without a real export proving it).
  - Fall back to `""`.
- **D-08:** **Naming.** CLI flag: `--quiz-title` (matches roadmap). Env var: `QUIZIFY_QUIZ_TITLE` (`QUIZIFY_` prefix avoids collision in shared shells). README documents both side-by-side in the configuration table.
- **D-09:** Decode `quiz_title` value through `html.unescape` like every other string (Phase 2 D-14) so `&amp;` in a flag value comes through correctly. Whitespace is **not** stripped — operator chose the literal value, preserve it.

### Score value typing & emptiness (Area 3)

*(Locked alongside Area 1 — see D-03 and D-04. No additional decisions.)*

### README scope & content (Area 4)

- **D-10:** **README location:** `quizify-csv-to-json-webhook/README.md` (per-helper folder convention from PROJECT.md).
- **D-11:** **README scope: full operator doc** with the following sections (in order):
  1. **Purpose** — one paragraph on what it does and why.
  2. **Quickstart** — one-line invocation example producing JSON to stdout.
  3. **CLI reference** — every flag (`--dry-run`, `-v`/`--verbose`, `--trailer-columns`, `-o`/`--output`, `--emit-json`, `--quiz-title`) with description, default, env-var equivalent if any.
  4. **Configuration table** (markdown) — columns: Setting / CLI flag / Env var / Default / Notes. Documents `quiz_title` precedence rule explicitly (D-07).
  5. **Column assumptions** — fixed contact prefix (`First name` … `Subscribed to newsletter`), trailer block (`Result logic` … `Date`), dynamic question block in between. Reference Phase 1's `--trailer-columns` override for forward-compat.
  6. **Output shape** — link to `docs/webhook-quizify-format-example.json`. Document key ordering (D-05) and call out: (a) `id` is omitted when unknown (Phase 2 D-07); (b) `product-recommendation`, `product-link-type`, `title`, `type-page-url` are reserved — emitted with `null`/`""` because CSV cannot supply them; (c) scoring keys are pass-through (D-01).
  7. **Limitations** — missing IDs, comma-in-cell answer heuristic (Phase 2 D-05), status mapping `Yes/No → subscribed/unsubscribed` plus warn on other (Phase 2 D-11), ISO date pass-through (Phase 2 D-12), empty rows always emit all keys (Phase 2 D-09).
  8. **Privacy notes** — exports are PII; default log level is WARNING; warnings name columns and categorical values, never cell content (Phase 2 PII posture). `-v`/`--verbose` adds INFO-level structural detail only.
  9. **Exit codes** — `0` success, `1` input/layout error or any per-row skip, `2` CLI usage error (Phase 2 D-18).
  10. **Development** — note that `requirements-dev.txt` provides pytest et al.; runtime is stdlib-only (no `requirements.txt`).
- **D-12:** **No worked example block in README** (rejected the "Full doc + worked example" option implicitly — `Full operator doc` was selected). Rationale: a worked CSV→JSON example would drift from code as fixtures or mappings evolve. Instead, README links to `docs/quizify-submissions.csv` (input) and `docs/webhook-quizify-format-example.json` (target shape) and says "run the Quickstart against the sample CSV to see live output."
- **D-13:** **Dependencies file policy: no `requirements.txt`.** Stdlib-only runtime per PROJECT.md; an empty file is misleading. Existing `requirements-dev.txt` (pytest tooling) stays. README "Development" section names this explicitly.
- **D-14:** **README precedence/config rendering: markdown table** (D-11.4). Single source of truth for invocation knobs; renders on GitHub.

### CLI integration

- **D-15:** **Same `quizify_csv_ingest.py` entrypoint** (Phase 1 D-11, Phase 2 D-15 still hold). Add `--quiz-title PATH-LIKE-VALUE` to the existing argparse parser. Resolve env var inside `main()` after `parse_args` (CLI > env logic). Pass resolved title down into `convert()` → `build_row()` as a parameter.
- **D-16:** **`build_row()` signature gets one new parameter:** `quiz_title: str`. Phase 3 also threads `trailer_cells_decoded[0..2]` into the row dict; existing trailer indices (3 = Answer tags, 5 = Date) keep their Phase 2 meanings. No new helper module unless line count / readability forces it (Claude's discretion).
- **D-17:** **No new flags for the 4 reserved placeholder keys.** D-02 emits hard-coded defaults. CLI-overridable defaults (e.g., `--product-recommendation`) were considered and rejected — adds surface area without a concrete v1 use case. Revisit only if a real downstream consumer requires non-null placeholders.

### Claude's Discretion

- Whether `quiz_title` resolution lives inline in `main()` or in a small helper (`_resolve_quiz_title(args, env) -> str`).
- Whether to factor a `SCORING_PLACEHOLDERS` constant dict or inline the four keys in `build_row`.
- Exact wording of README prose, ordering of paragraphs within sections, code-fence language tags.
- Whether the README's CLI reference is auto-generated from `argparse` `--help` output or hand-written (hand-written likely simpler given the small flag count).
- Whether to add `pyproject.toml` / `setup.cfg` for the helper folder (default: no, until packaging becomes a real need).

### Folded Todos

*(none — no todos matched phase 3)*

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` — WEB-04, WEB-05, OPS-01 traceability and acceptance criteria
- `.planning/ROADMAP.md` — Phase 3 goal ("Finish scoring-related fields, quiz title handling, and operator docs") and three success criteria

### Contracts & fixtures

- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — **Authoritative target shape.** Lines 12 (`quiz_title`) and 183-186 (the 4 reserved placeholder keys) are the structural references for D-02 / D-05. Pay attention to per-row key order.
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — Source of truth for trailer column meanings (`Result logic`, `Score category`, `Score value` at indices 26/27/28 of the header). Sample rows demonstrate `Score`/`Signos de Alarma`/`500` and `Score`/`Perfil moderado`/`6`.

### Prior phase context (binding — DO NOT re-decide)

- `.planning/phases/01-csv-ingestion-column-layout/01-CONTEXT.md` — Stdlib-first, single argparse entrypoint, stderr/stdout split, NFC normalization for matching, raw-header retention, `--trailer-columns` override.
- `.planning/phases/02-core-webhook-mapping/02-CONTEXT.md` — `build_row()` signature and structure, `decode_cell` (`html.unescape`), per-row key ordering for q-N triples, omit-on-unknown for `id`, status/statusDate mapping, top-level `tags` policy, exit code semantics, PII-safe warnings.

### Implementation under modification

- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — Phase 3 extends `build_row()` (currently lines 172-231), `convert()` (lines 272-345), and `main()` (lines 348-377). Constants `CONTACT_PREFIX` (line 15) and `DEFAULT_TRAILER` (line 24) define the trailer indices Phase 3 reads.

### Project constraints

- `.planning/PROJECT.md` — Stdlib-only Python (Phase 3 adds `os` for env var read; no new third-party deps), PII/privacy posture (no row content in default logs), per-helper folder convention.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 1 + Phase 2)

- `quizify_csv_ingest.py::build_row(prefix_cells_decoded, dynamic_cells_decoded, trailer_cells_decoded, dynamic_headers_decoded)` — extend signature to accept `quiz_title: str`. Insert `row["quiz_title"] = quiz_title` after `row["tags"]` (D-05 position 8). Read `trailer_cells_decoded[0..2]` for scoring pass-through; append the 3 scoring keys + 4 placeholder keys after the loop that emits `question-N`/`answers-N`/`answers-tags-N`.
- `quizify_csv_ingest.py::decode_cell(s)` — reuse for the resolved `quiz_title` value (D-09).
- `quizify_csv_ingest.py::convert(path, trailer, output)` — extend signature to accept `quiz_title`; thread into `build_row`.
- `quizify_csv_ingest.py::main(argv)` — add `--quiz-title` argparse argument; resolve precedence (CLI > env > `""`) before calling `convert`.
- Existing argparse parser already has `prog="quizify_csv_ingest"`; just add one new argument.

### Established Patterns

- Stdlib only: Phase 3 needs `os.environ.get("QUIZIFY_QUIZ_TITLE", "")` — no new imports beyond what's already used (`os` is the one new module).
- `print(..., file=sys.stderr)` for diagnostics; stdout reserved for JSON. Phase 3 has no new diagnostic surfaces (no warnings for empty scoring per D-03).
- Privacy: README's quickstart should not show real PII output; use sanitized snippets or link to the example file.

### Integration Points

- **No downstream phases.** Phase 3 closes the milestone; the next workflow step after Phase 3 is `/gsd-complete-milestone`.
- README is the externally visible artifact — it must align with the actual CLI surface after Phase 3 lands. Plan should include a "verify README matches `--help`" step.

### Risks / Watchouts

- **Reserved placeholder keys (D-02) emit hard-coded values that have NO source in the CSV.** A future consumer reading `product-recommendation: null` may misinterpret it as "Quizify said null" rather than "this exporter cannot supply this field." README's Output Shape section (D-11.6) MUST call this out explicitly to avoid downstream confusion.
- **`Score value` is string-typed (D-04).** Receivers expecting a number (e.g., for arithmetic) must parse. README's Limitations section flags this.
- **Future CSV `Quiz title` column (D-07)** is a stub in the precedence chain; do NOT invent the header name (`Quiz title` vs `quiz_title` vs `Title`). When a real export shows up, that's a Phase 4 question — for now, the lookup just isn't implemented and the precedence falls through to default `""`.
- **README test/CI coverage:** unlike code, README drift is silent. Plan should consider a smoke test that asserts `--help` text + flag list match what's documented (or a manual "diff before commit" step).

</code_context>

<specifics>
## Specific Ideas / Examples

- **Example payload anchors** (line numbers in `webhook-quizify-format-example.json`):
  - Line 12: `"quiz_title": "Autoevaluacion"` — Phase 3 emits at this position with operator-supplied or `""` value.
  - Lines 183-186: the 4 reserved keys with `"Basic"` / `null` / `""` / `""` — Phase 3 emits these as `null` / `null` / `""` / `""` (D-02 deviates from example's "Basic" because we can't derive it).
- **CSV trailer indices** (header row):
  - Index 26: `Result logic` → `result-logic` key (verbatim, e.g., `"Score"`).
  - Index 27: `Score category` → `score-category` key (verbatim, e.g., `"Signos de Alarma"`, `"Perfil moderado"`).
  - Index 28: `Score value` → `score-value` key (verbatim string, e.g., `"500"`, `"6"`).
- **Configuration table example** (D-14):
  ```
  | Setting    | CLI flag        | Env var               | Default | Notes                              |
  |------------|-----------------|-----------------------|---------|------------------------------------|
  | quiz_title | `--quiz-title`  | `QUIZIFY_QUIZ_TITLE`  | `""`    | CLI > env > future CSV column > "" |
  ```
- **Quickstart line** for README (D-11.2):
  ```
  python quizify_csv_ingest.py docs/quizify-submissions.csv --quiz-title "Autoevaluacion" -o out.json
  ```

</specifics>

<deferred>
## Deferred Ideas

- Future CSV `Quiz title` column lookup (D-07) — stub today; implement when a real export proves the column name and casing.
- CLI flags for the 4 reserved placeholder keys (`--product-recommendation`, `--title`, …) — defer until a downstream consumer requires non-null placeholders (D-17).
- `Score value` numeric coercion — revisit when a consumer actually breaks on string typing.
- WARNING on empty scoring cells — defer until empty-scoring is observed as a real anomaly (currently tolerated silently per D-03).
- README worked-example code block (the kind that drifts) — link to fixtures instead (D-12). Reconsider only if onboarding feedback shows operators struggle.
- HTTP POST / webhook send mode (**AUTO-01**, v2) — out of scope.
- JSON Schema validation (**VALI-01**, v2) — out of scope.
- Subcommands (`convert`, `inspect`) — Phase 1 D-11 and Phase 2 D-15 still hold; Phase 3 stays single-entrypoint.
- ID recovery from a Quizify question-bank export — would require an additional input file; not in v1 scope.
- Auto-generating the README CLI reference from `argparse --help` — Claude's-discretion item; defer unless flag count grows.
- `pyproject.toml` / packaging — defer until distribution becomes a real need.

### Reviewed Todos (not folded)

*(none)*

---

*Phase: 3 — Scoring metadata & packaging*
*Context gathered: 2026-05-03*
</deferred>
