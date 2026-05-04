# Phase 1: CSV ingestion & column layout - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver reliable CSV parsing and **header classification**: distinguish fixed contact columns, ordered dynamic quiz-question columns (for later `question-N` indices), and the trailing analytic/score block — deterministically on the sample export, without manual column indexes. Emit a verifiable preview (question count, grouping) that satisfies roadmap success criteria without logging row-level PII by default.

</domain>

<decisions>
## Implementation Decisions

### Preview / debug UX (Area 1)

- **D-01:** Send **diagnostics and human-readable previews to stderr**; reserve **stdout** for primary machine-readable output when Phase 2 emits JSON (Unix convention: data on stdout, logs/diagnostics on stderr — aligns with common CSV CLI tools).
- **D-02:** **`--dry-run`** prints a **layout summary only**: row count, total columns, counts per group (contact / dynamic / trailer), **ordered list of dynamic header texts**, and derived **question count**. Do **not** print cell values in dry-run or default logging.
- **D-03:** Use **`logging` directed at stderr**; default log level **WARNING**. **`-v` / `--verbose`** raises to **INFO** and may include extra structural detail (e.g. column indices per group) — still **no bulk row content** unless explicitly overridden later with a separate dangerous flag (not in Phase 1 scope).

### Trailer block detection (Area 2)

- **D-04:** **Default trailer suffix** (ordered, contiguous at end of header row) matches the sample export: `Result logic`, `Score category`, `Score value`, `Answer tags`, `Time to complete (mm:ss)`, `Date`.
- **D-05:** Provide **`--trailer-columns`** as a **comma-separated ordered list** to override the default trailer set when Quizify adds/reorders trailing fields — keeps behavior forward-compatible without code changes.
- **D-06:** **Classification:** columns after the fixed contact prefix and **before** the detected trailer suffix form the **dynamic question block**, in header order; indices map to **`question-1` … `question-K`** in Phase 2 (`K` = dynamic count).

### Header matching strictness (Area 3)

- **D-07:** Read CSV as **UTF-8** using **`utf-8-sig`** so a leading BOM does not break header equality.
- **D-08:** For **classification keys** (matching known fixed and trailer names), normalize each header with **leading/trailing whitespace strip** and **Unicode NFC** (`unicodedata.normalize("NFC", ...)`) before comparison to canonical strings.
- **D-09:** **Retain the raw header string** from the parser for each column for later emission (`question-N` text must match export text); use normalization **only for equality checks**, not for overwriting stored labels.
- **D-10:** **No case-folding** by default for header matching (preserve Quizify’s casing); if future exports drift only by case, address via a later explicit flag — not Phase 1.

### CLI entry shape (Area 4)

- **D-11:** Phase 1 uses a **single argparse entrypoint** (one positional input path, global optional flags). **No subcommands** for this phase — keeps the tool minimal until Phase 2 adds JSON emission modes that may share the same parser.
- **D-12:** Flags for Phase 1 at minimum: **`--dry-run`**, **`-v` / `--verbose`**, **`--trailer-columns`**; script lives under **`quizify-csv-to-json-webhook/`** following repo “folder per helper” convention.

### Claude's Discretion

- Exact help strings and whether `-q`/`--quiet` is exposed — minor UX polish during implementation.

### Folded Todos

*(none — no todos matched phase 1)*

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/REQUIREMENTS.md` — CONV-01, CONV-02 traceability; phase mapping
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, requirement IDs

### Contracts & fixtures

- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — Representative export (headers, quoting, UTF-8, HTML entities in cells)
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — Target **`question-N`** numbering (**1-based**) and field naming for alignment with Phase 2

### Project constraints

- `.planning/PROJECT.md` — Stdlib-first Python, PII/privacy posture, out-of-scope boundaries

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- No Quizify-specific Python package yet — greenfield implementation beside existing docs.
- Other repo utilities (e.g. `github/repo_inventory.py`) demonstrate **`argparse`**, **`csv`**, **`pathlib`** — reasonable style peers for CLI layout.

### Established Patterns

- **Folder-per-helper** under repo root; minimal coupling between scripts.
- **Privacy:** avoid verbose logging of row contents by default (`PROJECT.md`) — informs stderr-only diagnostics and no cell dumps in `--dry-run`.

### Integration Points

- Phase 2 consumes classified headers + indices + reader helper from Phase 1 to build webhook-shaped JSON per row.

</code_context>

<specifics>
## Specific Ideas

- Research cues applied: stderr for diagnostics vs stdout for piped data; explicit `--check`/`--dry-run`-style validation patterns from common CSV CLI tools; explicit configurable column lists for evolving exports (ETL tools often allow override column names).

</specifics>

<deferred>
## Deferred Ideas

- HTTP POST / webhook send mode (**AUTO-01**, v2) — out of scope for ingestion phase.
- Optional JSON Schema validation (**VALI-01**) — later phase.
- Subcommands (`convert`, `validate`) — defer until Phase 2+ surfaces distinct verbs with incompatible flag sets.

### Reviewed Todos (not folded)

*(none)*

---

*Phase: 1-CSV ingestion & column layout*
*Context gathered: 2026-05-03*
