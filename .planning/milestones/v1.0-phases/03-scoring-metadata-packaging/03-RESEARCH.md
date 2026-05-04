# Phase 3: Scoring metadata & packaging - Research

**Researched:** 2026-05-03
**Domain:** Python stdlib CLI extension (argparse + env precedence) and operator README authoring
**Confidence:** HIGH (everything is in-repo or stdlib idiom; no third-party dependencies introduced)

## Summary

Phase 3 closes the v1 milestone by extending the existing `quizify_csv_ingest.py` single-file CLI with three small, additive changes: (1) thread a `quiz_title` value (resolved from `--quiz-title` flag → `QUIZIFY_QUIZ_TITLE` env var → `""`) through `convert()` and `build_row()`; (2) emit three pass-through scoring keys (`result-logic`, `score-category`, `score-value`) plus four reserved placeholder keys at the end of each row dict; (3) author `quizify-csv-to-json-webhook/README.md` as the full operator doc per CONTEXT.md D-11. No new modules, no new third-party deps, no architectural reshuffle. The Phase 2 `build_row()` is structurally clean (returns a dict + warnings list) and accepts the new parameter cleanly.

The CONTEXT.md is exceptionally thorough — almost every implementation detail is locked. This research focuses on the seven concrete questions the planner asked: exact line ranges to edit, the test-extension pattern (extend Wave 2's `tests/test_golden_structure.py` and `tests/test_structural_invariants.py`), the canonical stdlib argparse-env idiom (resolve env *inside `main()`* after `parse_args`, not via `default=os.environ.get(...)` — the latter is a classic testability trap), README structure references that match how Python stdlib tools document themselves, trailer-override re-validation strategy (re-validate by canonical name, not by index, when `--trailer-columns` is set), the validation architecture extension (new golden-file assertions for key positions 8 and 22-25, plus `tests/test_quiz_title_precedence.py` as a new file), README-drift mitigation (a `tests/test_readme_help_alignment.py` smoke test that diffs CLI flags against the README CLI reference table), and the threat model (essentially nil — env-var read of a string the operator already controls).

**Primary recommendation:** Implement as **two small plans** matching the ROADMAP shape:

- **Plan 03-01** (TDD) — Code: extend `build_row()` + `convert()` signatures, add `--quiz-title` flag, resolve env in `main()`, emit 7 new keys (3 pass-through + 4 placeholders) at the end of the row dict in the locked positions. Extend `test_golden_structure.py` to drop the Phase-3 strip set and assert exact key positions; extend `test_structural_invariants.py` to assert the 7 new keys exist on every row; add `tests/test_quiz_title_precedence.py` for CLI-vs-env-vs-default precedence.
- **Plan 03-02** (DOC) — Author `quizify-csv-to-json-webhook/README.md` per the 10-section structure in D-11; add `tests/test_readme_help_alignment.py` smoke test that asserts every flag in `parser._actions` is named in the README CLI reference table.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `quiz_title` source resolution (CLI / env / default) | CLI / `main()` | — | Precedence logic is a CLI concern; never invoked in a library context |
| `quiz_title` decoding (`html.unescape`) | CLI / `main()` (or `convert()`) | — | Decode at the boundary so `build_row` consumes already-decoded values (matches Phase 2 D-14 boundary discipline) |
| Scoring pass-through (`result-logic`/`-category`/`-value`) | Pure-function row builder (`build_row`) | — | Trivial dict assignment from `trailer_cells_decoded[0..2]`; same tier as Phase 2 row construction |
| Reserved placeholder emission | Pure-function row builder (`build_row`) | Module-level constant (Claude's discretion) | Hard-coded defaults; no cross-row state |
| Operator README | Documentation artifact | — | External-facing markdown, not an implementation tier |
| README/`--help` drift detection | Test harness | — | A smoke test in `tests/` that introspects argparse |

[VERIFIED: in-repo code at `quizify-csv-to-json-webhook/quizify_csv_ingest.py` lines 172-231 (build_row), 272-345 (convert), 348-377 (main)]

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Pass-through `result-logic` / `score-category` / `score-value` from `trailer_cells_decoded[0]/[1]/[2]` verbatim. No invented Score-category→product-recommendation lookup.
- **D-02:** Emit 4 reserved keys with example defaults: `product-recommendation: null`, `product-link-type: null`, `title: ""`, `type-page-url: ""`. README documents them as "reserved — not derivable from CSV export".
- **D-03:** Empty/missing scoring cells emit `""` verbatim. No stderr WARNING for empty scoring.
- **D-04:** All scoring fields string verbatim, no numeric coercion. Decode via `html.unescape`.
- **D-05:** Per-row dict key order:
  1. `email`, `firstName`, `lastName`, `status`, `statusDate`, `phone`, `tags` (Phase 2)
  2. `quiz_title` (position 8)
  3. `question-N` / `answers-N` / `answers-tags-N` for N=1..K
  4. `result-logic`, `score-category`, `score-value`
  5. `product-recommendation`, `product-link-type`, `title`, `type-page-url`
- **D-06:** `quiz_title` optional, default `""`; key always present.
- **D-07:** Precedence high→low: CLI flag → env var → future per-CSV column (stub) → default `""`.
- **D-08:** CLI flag: `--quiz-title`; env var: `QUIZIFY_QUIZ_TITLE`.
- **D-09:** Decode `quiz_title` via `html.unescape`. Whitespace not stripped.
- **D-10:** README at `quizify-csv-to-json-webhook/README.md`.
- **D-11:** Full operator doc, 10 sections in fixed order (Purpose / Quickstart / CLI reference / Configuration table / Column assumptions / Output shape / Limitations / Privacy notes / Exit codes / Development).
- **D-12:** No worked example block in README (link to fixtures instead).
- **D-13:** No `requirements.txt`. Existing `requirements-dev.txt` stays.
- **D-14:** Configuration table in markdown (single source of truth for invocation knobs).
- **D-15:** Same `quizify_csv_ingest.py` entrypoint. Add `--quiz-title` to existing argparse parser. Resolve env inside `main()` after `parse_args`.
- **D-16:** `build_row()` gets one new parameter: `quiz_title: str`. Existing trailer indices (3 = Answer tags, 5 = Date) keep Phase 2 meanings.
- **D-17:** No new flags for the 4 reserved placeholder keys.

### Claude's Discretion

- `quiz_title` resolution inline in `main()` vs small `_resolve_quiz_title(args, env) -> str` helper.
- `SCORING_PLACEHOLDERS` constant dict vs inline four keys in `build_row`.
- Exact README prose, paragraph ordering inside sections, code-fence language tags.
- Hand-written README CLI reference vs auto-generated from `argparse --help` (CONTEXT prefers hand-written given small flag count).
- Whether to add `pyproject.toml` / `setup.cfg` (default: no).

### Deferred Ideas (OUT OF SCOPE)

- Future CSV `Quiz title` column lookup (D-07 stub).
- CLI flags for the 4 reserved placeholder keys.
- `Score value` numeric coercion.
- WARNING on empty scoring cells.
- README worked-example code block.
- HTTP POST mode (AUTO-01, v2).
- JSON Schema validation (VALI-01, v2).
- Subcommands.
- ID recovery from external Quizify export.
- Auto-generating the README CLI reference from `argparse --help`.
- `pyproject.toml` / packaging.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WEB-04 | Map `Result logic`/`Score category`/`Score value` into the webhook fields used for recommendations following the example and the script README | Pass-through to dedicated keys (D-01) plus 4 reserved placeholder keys (D-02) covers both the trailer-derived scoring fields and the example's recommendation slots; README Output Shape section documents the mapping (D-11.6) |
| WEB-05 | Support setting `quiz_title` via CLI flag or env when CSV does not include a dedicated column | `--quiz-title` flag + `QUIZIFY_QUIZ_TITLE` env var with explicit precedence (D-07/D-08); always-present `quiz_title` key with default `""` (D-06) |
| OPS-01 | Concise README beside the script describing usage, column assumptions, and limitations (missing IDs, encoding) | 10-section operator README (D-11) with explicit Limitations and Privacy sections |

## Standard Stack

### Core (already imported by existing code)

| Module | Source | Purpose | Why Standard |
|--------|--------|---------|--------------|
| `argparse` | Python stdlib | CLI parsing | [VERIFIED: line 6 of `quizify_csv_ingest.py`] Already used; just add one new argument |
| `html` | Python stdlib | `html.unescape` for `quiz_title` value | [VERIFIED: line 8] Phase 2 D-14 already uses this; keep boundary discipline |
| `json` | Python stdlib | Output serialization | [VERIFIED: line 9] Already used |
| `logging` | Python stdlib | Stderr diagnostics | [VERIFIED: line 10] Already used |
| `os` | Python stdlib | `os.environ.get("QUIZIFY_QUIZ_TITLE", "")` | [CITED: docs.python.org/3/library/os.html#os.environ] **NEW import in Phase 3** — only addition |

### Supporting

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `pytest` | Test harness | Already in `requirements-dev.txt` [VERIFIED: file exists at `quizify-csv-to-json-webhook/requirements-dev.txt`]; reuse subprocess + module-scoped fixture pattern from `test_structural_invariants.py` |
| `subprocess` | CLI integration tests | [VERIFIED: used in `tests/test_cli_emit.py` lines 16-23] Standard pattern for env-var precedence tests (pass `env=` to `subprocess.run`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `os.environ.get(...)` inside `main()` | `argparse` `default=os.environ.get("QUIZIFY_QUIZ_TITLE", "")` on the action | The `default=` form binds to env at module-import / parser-build time, which makes tests that mutate `os.environ` between calls fragile. Stdlib idiom for "CLI > env > default" in well-tested CLIs (e.g., `click` BoundedContext docs) is to resolve in the function body after `parse_args`. **Recommendation: resolve in `main()`** [ASSUMED — based on training; see "Open Questions" #1] |
| Inline 4 placeholder keys in `build_row` | `SCORING_PLACEHOLDERS = {...}` module constant | Constant is one symbol, testable independently, and self-documents intent. Inline keeps `build_row` self-contained. CONTEXT marks Claude's discretion. **Recommendation: module constant** for symmetry with `CONTACT_PREFIX`/`DEFAULT_TRAILER`/`TAG_HEADER_MAP` |

**No installation required.** Phase 3 adds **zero new third-party packages**. The only new stdlib import is `os`.

**Version verification:** Not applicable — stdlib only. Python 3.10+ assumed (PEP 604 `tuple[str, ...] | None` syntax already in use at line 53 of `quizify_csv_ingest.py`).

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────┐
                        │  CLI invocation      │
                        │  (argv[])            │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ argparse.parse_args  │
                        │  --quiz-title arg    │ ◄── NEW (Phase 3)
                        └──────────┬───────────┘
                                   │
                                   ▼
              ┌──────────────────────────────────────┐
              │   _resolve_quiz_title(args, environ) │ ◄── NEW (Phase 3)
              │   precedence: CLI > env > ""         │
              │   then html.unescape(...)            │
              └──────────────────┬───────────────────┘
                                 │
                                 │ str (always)
                                 ▼
                        ┌──────────────────────┐
                        │  convert(            │
                        │    csv_path,         │
                        │    trailer,          │
                        │    output,           │
                        │    quiz_title) ◄──── NEW PARAM
                        └──────────┬───────────┘
                                   │ per row
                                   ▼
                        ┌──────────────────────┐
                        │  build_row(          │
                        │    prefix_d,         │
                        │    dynamic_d,        │
                        │    trailer_d,        │
                        │    headers_d,        │
                        │    quiz_title) ◄──── NEW PARAM
                        └──────────┬───────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │  per-row dict (locked key order D-05)  │
              │  ── existing Phase 2 contact block ──  │
              │  email, firstName, lastName, status,   │
              │  statusDate, phone, tags               │
              │  ── NEW position 8 ──                  │
              │  quiz_title                            │
              │  ── existing question triples ──       │
              │  question-N, answers-N, answers-tags-N │
              │  ── NEW pass-through scoring ──        │
              │  result-logic, score-category,         │
              │  score-value                           │
              │  ── NEW reserved placeholders ──       │
              │  product-recommendation, product-link- │
              │  type, title, type-page-url            │
              └────────────────────────────────────────┘
                                   │
                                   ▼
                          json.dump(... indent=2,
                                    ensure_ascii=False)
                                   │
                          stdout / -o file
```

### Recommended Project Structure (no change)

```
quizify-csv-to-json-webhook/
├── README.md                  ← NEW (Phase 3, plan 03-02)
├── quizify_csv_ingest.py      ← extended (Phase 3, plan 03-01)
├── pytest.ini
├── requirements-dev.txt
├── docs/
│   ├── quizify-submissions.csv
│   └── webhook-quizify-format-example.json
└── tests/
    ├── conftest.py
    ├── test_layout.py
    ├── test_row_builder.py
    ├── test_cli_emit.py
    ├── test_logging_pii.py
    ├── test_golden_structure.py        ← extend (drop Phase-3 strip)
    ├── test_structural_invariants.py   ← extend (assert 7 new keys)
    ├── test_quiz_title_precedence.py   ← NEW (CLI > env > "")
    └── test_readme_help_alignment.py   ← NEW (drift smoke test)
```

### Pattern 1: argparse + env-var fallback (resolved in `main()`)

**What:** Define the flag with `default=None`. After `parse_args()`, read `os.environ.get(...)` only when the flag is `None`. Decode via `html.unescape` last.

**When to use:** Any CLI flag with documented precedence "CLI flag > env var > default". This is the canonical stdlib pattern for testable env fallback.

**Example:**
```python
# Source: docs.python.org/3/library/argparse.html (default=None semantics)
# and stdlib idiom; see also https://peps.python.org/pep-0008/

import os
import html
import argparse


def _resolve_quiz_title(args: argparse.Namespace, environ: dict[str, str]) -> str:
    """D-07 precedence: CLI flag > env var > "" (future CSV column stub).

    Decodes via html.unescape at the boundary (D-09); whitespace preserved.
    """
    if args.quiz_title is not None:
        return html.unescape(args.quiz_title)
    env_value = environ.get("QUIZIFY_QUIZ_TITLE")
    if env_value is not None:
        return html.unescape(env_value)
    # Future: CSV "Quiz title" column lookup goes here (D-07 stub).
    return ""


# in main():
parser.add_argument("--quiz-title", default=None,
                    help="Quiz title; falls back to $QUIZIFY_QUIZ_TITLE then \"\"")
args = parser.parse_args(argv)
quiz_title = _resolve_quiz_title(args, os.environ)
```

[VERIFIED: argparse `default=None` semantics — `args.quiz_title` is `None` when flag absent, regardless of env. Confirmed by Python stdlib argparse contract — `Namespace` attribute equals declared `default` when argument not present on command line.]

**Why not `default=os.environ.get(...)`:** That form is evaluated **once** at parser-construction time. Tests that monkeypatch `os.environ` between subprocess calls work fine (each `subprocess.run` gets a fresh process), but in-process tests (e.g., calling `main()` repeatedly with mutated env) silently use the parser's frozen default. Resolving inside `main()` reads `os.environ` *every* call, which is the testable, predictable contract. [ASSUMED — based on training; the canonical `argparse` HOWTO does not state this rule explicitly. The recommendation is best-practice consensus, not a documented rule.]

### Pattern 2: Module-scoped subprocess fixture for invariant tests

**What:** Run the CLI exactly once per test module; share parsed JSON across all tests in the module via `@pytest.fixture(scope="module")`.

**When to use:** Property-style tests that all consume the same emitted payload.

**Example (already in repo — extend, don't duplicate):**
```python
# Source: quizify-csv-to-json-webhook/tests/test_structural_invariants.py:38-56

@pytest.fixture(scope="module")
def emitted_payload() -> tuple[list[dict], str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, ...
    return json.loads(result.stdout), result.stdout
```

[VERIFIED: in-repo at `tests/test_structural_invariants.py` lines 38-56]

### Pattern 3: Subprocess env injection for precedence tests

**What:** `subprocess.run(..., env={...})` controls exactly what the child process sees, eliminating cross-test env leakage.

**Example:**
```python
# Source: docs.python.org/3/library/subprocess.html#subprocess.run env=
import os, subprocess, sys, json

def test_env_var_used_when_flag_absent(tmp_path):
    csv_path = _make_minimal_csv(tmp_path)
    env = {**os.environ, "QUIZIFY_QUIZ_TITLE": "FromEnv"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path)],
        capture_output=True, text=True, env=env, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload[0]["quiz_title"] == "FromEnv"

def test_cli_flag_overrides_env(tmp_path):
    csv_path = _make_minimal_csv(tmp_path)
    env = {**os.environ, "QUIZIFY_QUIZ_TITLE": "FromEnv"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path), "--quiz-title", "FromCli"],
        capture_output=True, text=True, env=env, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload[0]["quiz_title"] == "FromCli"

def test_default_empty_when_neither_set(tmp_path, monkeypatch):
    monkeypatch.delenv("QUIZIFY_QUIZ_TITLE", raising=False)
    csv_path = _make_minimal_csv(tmp_path)
    # Build env explicitly so QUIZIFY_QUIZ_TITLE is absent even if developer
    # has it set in their shell.
    env = {k: v for k, v in os.environ.items() if k != "QUIZIFY_QUIZ_TITLE"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path)],
        capture_output=True, text=True, env=env, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload[0]["quiz_title"] == ""
```

[CITED: docs.python.org/3/library/subprocess.html — `env` parameter controls child environment exactly]

### Anti-Patterns to Avoid

- **`default=os.environ.get(...)` on argparse `add_argument`:** Freezes env capture at parser construction. Use `default=None` + post-`parse_args` resolution. (See Pattern 1.)
- **Reading env inside `build_row` or `convert`:** Pushes side effects into pure functions. CONTEXT D-15 explicitly locates env resolution in `main()`; honor that boundary.
- **Stripping whitespace from `--quiz-title`:** D-09 says "operator chose the literal value, preserve it." Don't `.strip()`.
- **Re-reading `os.environ` after `parse_args` directly using string literal:** Use a named helper (`_resolve_quiz_title`) so the precedence rule is unit-testable without a subprocess.
- **Hand-coding the README CLI reference table without a drift check:** D-11.3 + D-14 lock README content; combine with `tests/test_readme_help_alignment.py` (Pattern below) so a flag added later cannot silently desynchronize.
- **Trusting `trailer_cells_decoded[0..2]` blindly when `--trailer-columns` is overridden:** see "Common Pitfalls" #3 below.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env-var read | Custom `_get_env_or_default` wrapper | `os.environ.get(name, default)` | Stdlib one-liner; CONTEXT.md D-07 default is `""` so `os.environ.get("QUIZIFY_QUIZ_TITLE", "")` could be inlined, but the named helper documents the precedence rule |
| HTML entity decode | Manual `&gt;` → `>` table | `html.unescape` (already in use line 8) | Phase 2 D-14 boundary; reuse exactly |
| Markdown table generation | Helper that prints argparse → table | Hand-write the table; verify with introspection test | Flag count is small (now ≤7); auto-gen adds machinery for no benefit |
| Numeric coercion of `score-value` | `int(value)` / `float(value)` | Pass-through string verbatim (D-04) | Receivers parse if they need to; coercion loses original encoding (e.g., `"500"` vs `"500.0"`) |
| README/`--help` drift detection | Manual diff in PR review | Test that introspects `parser._actions` and asserts each `option_strings[0]` appears in README | Drift is silent — only a code-side assertion catches it |

**Key insight:** Phase 3 is overwhelmingly about *not* introducing complexity. The locked decisions remove most architectural choices; the work is mechanical. Resist refactoring temptations (e.g., extracting a `RowBuilder` class) unless line-count pressure demands it. CONTEXT.md "Claude's Discretion" already lists the only legitimate refactor seams.

## Runtime State Inventory

This is **not** a rename / refactor / migration phase — it is purely additive code + new documentation. No runtime state of any kind is being renamed, moved, or migrated. **Section omitted intentionally.**

## Common Pitfalls

### Pitfall 1: argparse evaluates `default=` once at parser-build time
**What goes wrong:** A developer writes `default=os.environ.get("QUIZIFY_QUIZ_TITLE", "")` on the action, then writes a test that calls `main()` twice with different env values; the second call sees the first call's env value.
**Why it happens:** `add_argument` evaluates `default` immediately and stores the result on the action. `parse_args` only references that stored value when the flag is absent.
**How to avoid:** `default=None` on the action; resolve env inside `main()` via the `_resolve_quiz_title` helper.
**Warning signs:** Tests pass individually but fail when run together; in-process tests behave differently from subprocess tests.
[VERIFIED: argparse contract — `default` is bound at `add_argument` call time]

### Pitfall 2: Reserved placeholder keys mistaken for real Quizify output
**What goes wrong:** A downstream consumer reads `product-recommendation: null` and interprets it as "Quizify scored this user as having no product recommendation," when the real meaning is "this exporter cannot supply this field from the CSV."
**Why it happens:** The example payload (line 183) carries `"Basic"` for `product-recommendation`, but D-02 emits `null` because the CSV has no such column.
**How to avoid:** README "Output shape" section (D-11.6) MUST contain a paragraph explicitly listing the 4 reserved keys and stating "emitted with `null`/`""` because the CSV export does not contain these fields. Include a footnote referencing D-02.
**Warning signs:** Bug reports of the form "product recommendation is missing for user X" — the answer is always "the CSV doesn't have it; if you need it, fetch it from the source-of-truth API, not the exporter."
[VERIFIED: example file lines 183-186; CONTEXT.md D-02 / D-11.6]

### Pitfall 3: `--trailer-columns` override breaks scoring index assumptions
**What goes wrong:** Operator runs with `--trailer-columns "Date,Score value,Score category,Result logic,Answer tags,Time to complete (mm:ss)"`. Phase 3 reads `trailer_cells_decoded[0..2]` assuming the default order — now `result-logic` would carry the `Date` value, `score-category` would carry `Score value`, etc. Silent data corruption.
**Why it happens:** Phase 1 (D-05) provided `--trailer-columns` for forward compatibility, but Phase 3's pass-through (D-01) implicitly assumes the *default* order. CONTEXT.md does not lock a re-validation strategy.
**How to avoid:** Inside `build_row` (or one level up in `convert`), look up the scoring fields **by canonical name** rather than positional index when the trailer differs from `DEFAULT_TRAILER`. Concrete approach:
- In `convert()`, after `classify_headers` returns, compute `scoring_indices = {"result-logic": trailer.index("Result logic"), ...}` — using the *resolved trailer tuple*, not `DEFAULT_TRAILER`. If a canonical name is missing from the override, log a one-time WARNING and emit `""` for that field.
- Pass a small dict `{result_logic_idx, score_category_idx, score_value_idx}` into `build_row`, or pre-extract the three values in `convert` and pass them as parameters.
- Document in README "Column assumptions" that `--trailer-columns` must include the four canonical names `Result logic`, `Score category`, `Score value`, `Date` (in any order) for scoring + statusDate to populate.

**Warning signs:** Score values appear in wrong fields when operator passes `--trailer-columns`. Currently no test exercises this; Plan 03-01 should add one.
[VERIFIED: `quizify_csv_ingest.py` lines 50-77 — `classify_headers` returns `trailer_raw` slice in **the order specified by the trailer argument**, so positional reads against `[0..2]` only correspond to "Result logic / Score category / Score value" when the default order is used]

### Pitfall 4: README drifts from `--help` output silently
**What goes wrong:** A future plan adds `--foo` to the parser. README's CLI reference and configuration table still list only the old flags. Operators read the README, miss `--foo`.
**Why it happens:** README is plain markdown; nothing enforces it stays in sync with code.
**How to avoid:** Add `tests/test_readme_help_alignment.py`:
```python
def test_every_flag_named_in_readme():
    import quizify_csv_ingest as m
    parser = m._build_parser() if hasattr(m, "_build_parser") else None
    if parser is None:
        # Without a separate parser-builder, introspect via -h capture
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                                capture_output=True, text=True, check=True)
        help_text = result.stdout
    else:
        help_text = parser.format_help()
    flag_names = re.findall(r"--[a-z][a-z0-9-]+", help_text)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for flag in set(flag_names):
        if flag in {"--help"}:
            continue
        assert flag in readme, f"flag {flag} missing from README.md"
```
**Warning signs:** README claims a behavior the binary does not exhibit. Test fails on the first commit that adds a new flag without updating README.
[ASSUMED — pattern is widely used in well-maintained CLI projects but is not a stdlib-documented technique. Recommendation strength: medium; the planner should treat this as a "Claude's Discretion" implementation but the test contract itself is straightforward.]

### Pitfall 5: HTML-entity-bearing `--quiz-title` not decoded
**What goes wrong:** Operator passes `--quiz-title "Salud &amp; Bienestar"`. Without decode, `quiz_title: "Salud &amp; Bienestar"` ships to webhook, which a downstream consumer renders verbatim.
**Why it happens:** Forgetting D-09. The CLI input is just as much "string from outside" as a CSV cell.
**How to avoid:** Apply `html.unescape` once, in `_resolve_quiz_title`, immediately before returning. Same boundary discipline as Phase 2 D-14.
**Warning signs:** Webhook receiver shows literal `&amp;` / `&gt;` in quiz titles.
[VERIFIED: D-09]

## Code Examples

### Code-Extension Points (line ranges in current `quizify_csv_ingest.py`)

| Change | File / Function | Existing Lines | Edit Type |
|--------|-----------------|----------------|-----------|
| Add `import os` | top of file | line 11 (after `sys`) | INSERT one line |
| Add `SCORING_PLACEHOLDERS` constant (Claude's discretion) | module top-level | after line 84 (`TAG_HEADER_MAP`) | INSERT block |
| Extend `build_row` signature: add `quiz_title: str` parameter | `build_row` | line 172-177 | MODIFY signature; CONTEXT.md prefers kwarg-style for backward-compat-friendly diff |
| Insert `row["quiz_title"] = quiz_title` after tags | `build_row` | between line 224 (`"tags": tags_list,`) and line 225 (`for i, header...`) | INSERT |
| Append 3 pass-through scoring + 4 placeholder keys | `build_row` | after line 230 (loop end) | INSERT |
| Extend `convert` signature: add `quiz_title: str` parameter | `convert` | line 272-276 | MODIFY signature |
| Pass `quiz_title` into `build_row` call | `convert` | line 329-331 | MODIFY call site |
| Add `--quiz-title` argparse argument | `main` | after line 361 (`--emit-json` add_argument) | INSERT add_argument |
| Resolve env var precedence | `main` | after line 362 (`args = parser.parse_args(argv)`) and before line 374 (`if args.dry_run`) | INSERT helper call |
| Pass `quiz_title` into `convert(...)` | `main` | line 377 | MODIFY call site |

[VERIFIED: all line numbers from `quizify_csv_ingest.py` reading]

### Concrete Per-Row Build Sequence (after Phase 3)

```python
# Source: extension of existing quizify_csv_ingest.py:172-231

def build_row(
    prefix_cells_decoded: list[str],
    dynamic_cells_decoded: list[str],
    trailer_cells_decoded: list[str],
    dynamic_headers_decoded: list[str],
    quiz_title: str,                              # NEW (D-16)
) -> tuple[dict, list[str]]:
    warnings_out: list[str] = []
    # ... [Phase 2 contact + status + tags computation unchanged, lines 188-214] ...

    row: dict = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "status": status_value,
        "statusDate": status_date,
        "phone": phone,
        "tags": tags_list,
        "quiz_title": quiz_title,                 # NEW position 8 (D-05)
    }
    for i, header in enumerate(dynamic_headers_decoded):
        n = i + 1
        cell = dynamic_cells_decoded[i] if i < len(dynamic_cells_decoded) else ""
        row[f"question-{n}"] = header
        row[f"answers-{n}"] = shape_answer(cell)
        row[f"answers-tags-{n}"] = ", ".join(matched_buckets.get(i, []))

    # NEW (D-01): pass-through scoring keys, indices 0/1/2 of trailer_cells_decoded
    # under DEFAULT_TRAILER; see Pitfall 3 for --trailer-columns handling.
    row["result-logic"]   = trailer_cells_decoded[0] if len(trailer_cells_decoded) > 0 else ""
    row["score-category"] = trailer_cells_decoded[1] if len(trailer_cells_decoded) > 1 else ""
    row["score-value"]    = trailer_cells_decoded[2] if len(trailer_cells_decoded) > 2 else ""

    # NEW (D-02): reserved placeholder keys, hard-coded defaults
    row["product-recommendation"] = None
    row["product-link-type"]      = None
    row["title"]                  = ""
    row["type-page-url"]           = ""

    return row, warnings_out
```

(If `--trailer-columns` override changes ordering, replace the `[0]/[1]/[2]` indexing with a name→index lookup computed once in `convert()` and passed in. See Pitfall 3.)

### `main()` Precedence Resolution Sketch

```python
# Source: extension of existing quizify_csv_ingest.py:348-377

def _resolve_quiz_title(args, environ) -> str:
    if args.quiz_title is not None:
        return html.unescape(args.quiz_title)
    env_val = environ.get("QUIZIFY_QUIZ_TITLE")
    if env_val is not None:
        return html.unescape(env_val)
    # D-07 stub: future CSV "Quiz title" column lookup goes here.
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="quizify_csv_ingest")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trailer-columns", default=None)
    parser.add_argument("-o", "--output", type=Path, default=None, ...)
    parser.add_argument("--emit-json", action="store_true", ...)
    parser.add_argument(                                                    # NEW
        "--quiz-title",
        default=None,
        help="Quiz title; falls back to $QUIZIFY_QUIZ_TITLE env var, "
             "then default \"\". Decoded via html.unescape.",
    )
    args = parser.parse_args(argv)

    quiz_title = _resolve_quiz_title(args, os.environ)                      # NEW

    trailer_override: tuple[str, ...] | None = None
    if args.trailer_columns is not None:
        try:
            trailer_override = parse_trailer_arg(args.trailer_columns)
        except ValueError:
            print("ERROR invalid trailer-columns", file=sys.stderr)
            return 2

    configure_logging(args.verbose)
    if args.dry_run:
        return dry_run(args.csv_path, trailer_override)
    return convert(args.csv_path, trailer_override, args.output, quiz_title)  # MODIFIED
```

## Test Strategy

Phase 2 verification harness (Plan 02-02) established two test layers we extend, plus one new file:

### Extend `tests/test_golden_structure.py`

Wave 2 currently strips Phase-3-only keys (`PHASE_3_KEYS` frozenset on line 28-36). After Phase 3:

- **Drop `PHASE_3_KEYS` strip:** the emitted row should now match the example top-level key set with `id` keys stripped (single difference). Update `test_aligned_row_top_level_keyset_matches_example` to assert exact equality of key sets.
- **Add positional ordering test:** assert `list(emitted.keys())` matches the locked D-05 order. Concretely, `list(emitted.keys())[7] == "quiz_title"` and the last 7 keys are `["result-logic", "score-category", "score-value", "product-recommendation", "product-link-type", "title", "type-page-url"]`.
- **Add placeholder defaults test:** `assert emitted["product-recommendation"] is None`, `emitted["title"] == ""`, etc. (D-02 verbatim).
- **Add scoring pass-through test:** synthesize a row whose trailer cells `[0..2]` are `("Score", "Signos de Alarma", "500")` and assert the emitted scoring keys carry exactly those strings.
- **Update `_build_aligned_csv` to set Result logic / Score category / Score value** so the golden test exercises live values (currently lines 116-123 set them all `""`). Set them to the example's `"Score" / "Signos de Alarma" / "500"` style values; assert pass-through.
- **Add `--quiz-title` to subprocess invocation in `run_aligned`** so the aligned row's `quiz_title` matches the example's `"Autoevaluacion"`.

### Extend `tests/test_structural_invariants.py`

- **Update `PHASE_3_KEYS` semantics:** rename to `PHASE_3_REQUIRED_KEYS` and assert each is **present** on every row.
- **Add `test_every_row_has_quiz_title`:** key always present, value is a `str`.
- **Add `test_every_row_has_scoring_keys`:** `result-logic`, `score-category`, `score-value` always present and string-typed.
- **Add `test_every_row_has_reserved_placeholders`:** all 4 keys present; placeholders match locked defaults exactly (`is None` for product fields; `""` for title/type-page-url).
- **Add `test_key_order_locked`:** materialize `list(row.keys())` for each row, assert position 7 = `"quiz_title"` (0-indexed) and final 7 keys exactly match the locked tail.
- **Add `test_quiz_title_default_empty`:** with no `--quiz-title` and no `QUIZIFY_QUIZ_TITLE` (subprocess env explicitly omits it), every row's `quiz_title == ""`.

### NEW `tests/test_quiz_title_precedence.py`

Three subprocess tests + one in-process unit test on `_resolve_quiz_title`:

```python
# Pseudo-outline; concrete implementation in Plan 03-01
def test_resolve_quiz_title_cli_wins(): ...
def test_resolve_quiz_title_env_used_when_flag_absent(): ...
def test_resolve_quiz_title_default_empty_when_neither(): ...
def test_resolve_quiz_title_html_unescape_applied(): ...
def test_resolve_quiz_title_whitespace_preserved():
    # D-09: don't .strip()
    ns = argparse.Namespace(quiz_title="  Padded  ")
    assert _resolve_quiz_title(ns, {}) == "  Padded  "

# subprocess tier: env injection (Pattern 3)
def test_subprocess_cli_overrides_env(tmp_path): ...
def test_subprocess_env_used_when_no_cli(tmp_path): ...
def test_subprocess_default_empty(tmp_path): ...
```

### NEW `tests/test_readme_help_alignment.py`

Single test; introspects argparse via subprocess `--help` and asserts every long flag appears in `README.md`. See Pitfall 4 for shape.

### Sample-vs-aggregate measurement (Nyquist)

| Layer | Cardinality | Subprocess invocations | Cost |
|-------|-------------|------------------------|------|
| `test_quiz_title_precedence.py` (subprocess) | 3 | 3 (each runs against a 1-row tmp CSV) | ~0.3s |
| `test_quiz_title_precedence.py` (unit) | 5+ | 0 (direct `_resolve_quiz_title` calls) | <0.01s |
| `test_golden_structure.py` extensions | unchanged (8 → 12) | unchanged (1 per test, 1-row CSV) | ~0.4s |
| `test_structural_invariants.py` extensions | 12 → 18 | unchanged (module-scoped, 1 invocation) | ~0.06s |
| `test_readme_help_alignment.py` | 1 | 1 (`--help` only) | <0.05s |

Total Phase 3 added test runtime budget: **< 1 second**, comfortable under the 60s subprocess timeout.

## State of the Art

This phase is intentionally additive within a stdlib-only Python file. There is no "modern alternative" to consider for the locked design — the alternatives space (Click/Typer for CLI, pydantic for env config, dotenv for secret loading) is explicitly out of scope per `PROJECT.md` "stdlib-first" and CONTEXT.md D-13. **No state-of-the-art shifts apply.**

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| (none — phase is greenfield extension) | — | — | — |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Resolve env inside `main()`, not via argparse `default=os.environ.get(...)`" — recommendation strength | Architecture Patterns / Pattern 1 | Low — both approaches produce identical behavior for the subprocess test pattern Phase 3 uses. The recommended approach is more testable in-process, and CONTEXT D-15 explicitly requires it. **Assumption is safe; flagged for transparency.** |
| A2 | README/`--help` drift smoke test pattern | Common Pitfalls #4 | Low — pattern is well-known but not a documented stdlib idiom. Worst case: test is brittle (false negative if README uses code-fenced flag forms differently). Recommend simple `flag in readme_text` substring check. |
| A3 | "`Score value` may be ordinal tier, ratio, or measurement" rationale | (CONTEXT D-04) | None — this rationale is from CONTEXT.md D-04, not asserted independently |

**If you reduce the assumption list to high-stakes items: A1 is the only assumption with any test-design impact, and CONTEXT D-15 already locks the conclusion.**

## Open Questions

1. **Should `convert()` extract scoring values by canonical name (Pitfall 3) or pass through `[0..2]` blindly?**
   - What we know: CONTEXT D-15 says "thread `trailer_cells_decoded[0..2]` into the row dict." That implies positional. CONTEXT also says (D-15 text in canonical_refs) "existing trailer indices (3 = Answer tags, 5 = Date) keep their Phase 2 meanings" — also positional.
   - What's unclear: does the planner accept that `--trailer-columns` override breaks scoring silently? Or should Plan 03-01 include a name-based lookup as a small enhancement?
   - Recommendation: implement positional `[0..2]` to honor D-15 verbatim, **but** add an INFO-level log message in `convert()` when `args.trailer_columns is not None` to alert the operator that scoring/statusDate assumptions depend on the default order. Document in README "Column assumptions" and Limitations. Actual name-based lookup deferred to a future phase if a real export needs it (matches "Future CSV `Quiz title` column" deferral pattern).

2. **Where exactly should `html.unescape(quiz_title)` happen — `_resolve_quiz_title` or inside `build_row`?**
   - What we know: D-09 says decode the resolved value. D-15 says resolve in `main()`.
   - What's unclear: is `build_row` allowed to assume its `quiz_title` parameter is already decoded?
   - Recommendation: decode in `_resolve_quiz_title` so `build_row` continues to receive already-decoded strings (matching every other Phase 2 contract — `decoded` is the noun in `build_row`'s parameter names line 173-176). This keeps the boundary discipline clean.

3. **Should `_resolve_quiz_title` be public or `_` private?**
   - What we know: CONTEXT marks helper-extraction as Claude's Discretion; doesn't lock visibility.
   - What's unclear: future tests may want to import it.
   - Recommendation: leading underscore (private) — Phase 3 unit tests can still import it; the underscore signals "not part of the script's public interface."

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥ 3.10 | argparse, PEP 604 type unions, `os.environ` | ✓ (assumed — Phase 1/2 already use 3.10+ syntax) | n/a | — |
| `pytest` | tests | ✓ | listed in `requirements-dev.txt` [VERIFIED: file exists] | — |
| `os` (stdlib) | env-var read | ✓ | stdlib | — |

**No external/network dependencies. No services. No databases. No CLI tools beyond `python` and `pytest`.** Phase 3 has the smallest possible environment surface.

## Validation Architecture

`workflow.nyquist_validation: true` per `.planning/config.json`. Section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (version pinned in `requirements-dev.txt`) |
| Config file | `quizify-csv-to-json-webhook/pytest.ini` (sets `pythonpath = .`) |
| Quick run command | `cd quizify-csv-to-json-webhook && pytest -q tests/test_quiz_title_precedence.py tests/test_readme_help_alignment.py` |
| Full suite command | `cd quizify-csv-to-json-webhook && pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-04 | `result-logic`/`-category`/`-value` pass-through verbatim | unit + golden | `pytest tests/test_row_builder.py::test_scoring_pass_through tests/test_golden_structure.py::test_scoring_keys_present_after_phase3` | ❌ Wave 0 (extend) |
| WEB-04 | Empty scoring cells → `""` | unit | `pytest tests/test_row_builder.py::test_empty_scoring_emits_empty_strings` | ❌ Wave 0 |
| WEB-04 | 4 reserved placeholders with locked defaults | golden + invariant | `pytest tests/test_golden_structure.py::test_reserved_placeholders_match_defaults tests/test_structural_invariants.py::test_every_row_has_reserved_placeholders` | ❌ Wave 0 (extend existing files) |
| WEB-04 | Key order matches D-05 | golden + invariant | `pytest tests/test_golden_structure.py::test_key_order_locked tests/test_structural_invariants.py::test_key_order_locked` | ❌ Wave 0 |
| WEB-05 | `--quiz-title` flag wins over env | subprocess | `pytest tests/test_quiz_title_precedence.py::test_subprocess_cli_overrides_env` | ❌ Wave 0 (NEW file) |
| WEB-05 | Env var used when flag absent | subprocess | `pytest tests/test_quiz_title_precedence.py::test_subprocess_env_used_when_no_cli` | ❌ Wave 0 |
| WEB-05 | Default `""` when neither set | subprocess | `pytest tests/test_quiz_title_precedence.py::test_subprocess_default_empty` | ❌ Wave 0 |
| WEB-05 | `html.unescape` applied to resolved `quiz_title` | unit | `pytest tests/test_quiz_title_precedence.py::test_resolve_quiz_title_html_unescape_applied` | ❌ Wave 0 |
| WEB-05 | Whitespace not stripped | unit | `pytest tests/test_quiz_title_precedence.py::test_resolve_quiz_title_whitespace_preserved` | ❌ Wave 0 |
| OPS-01 | README exists with all 10 sections | smoke (manual review) | `pytest tests/test_readme_help_alignment.py::test_readme_has_all_required_sections` | ❌ Wave 0 (NEW file) |
| OPS-01 | README CLI flags match `--help` | smoke | `pytest tests/test_readme_help_alignment.py::test_every_flag_named_in_readme` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q tests/test_quiz_title_precedence.py tests/test_readme_help_alignment.py tests/test_row_builder.py` (~0.4s)
- **Per wave merge:** `pytest -q` (full suite — Phase 2 + Phase 3 = ~1.0s expected)
- **Phase gate:** Full suite green before `/gsd-verify-work` and `/gsd-complete-milestone`

### Wave 0 Gaps
- [ ] `tests/test_quiz_title_precedence.py` — covers WEB-05 precedence + decode + whitespace contract (NEW file)
- [ ] `tests/test_readme_help_alignment.py` — covers OPS-01 drift detection (NEW file)
- [ ] Extend `tests/test_row_builder.py` — add 3 tests for scoring pass-through, empty-scoring `""`, and `quiz_title` parameter wiring through `build_row`
- [ ] Extend `tests/test_golden_structure.py` — drop `PHASE_3_KEYS` strip, add positional-order test, add scoring + placeholder + `quiz_title` value tests, update `_build_aligned_csv` and `run_aligned` to populate scoring trailer cells and pass `--quiz-title "Autoevaluacion"`
- [ ] Extend `tests/test_structural_invariants.py` — invert `PHASE_3_KEYS` semantics from "must NOT leak" to "must be present"; add 6 invariant tests (quiz_title, scoring trio, placeholders, key order, default-empty)
- [ ] Framework install: none — `pytest` already available

## Security Domain

`workflow.security_enforcement: true`, ASVS Level 1. Section included; threat surface is essentially nil.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — no auth surface |
| V3 Session Management | no | n/a — single-shot CLI |
| V4 Access Control | no | n/a — local file CLI |
| V5 Input Validation | yes (low) | `--quiz-title` is a string; `html.unescape` is the only transformation; no SQL/HTML/JS injection sinks (we're emitting JSON) |
| V6 Cryptography | no | n/a |
| V7 Error Handling & Logging | yes (carry-forward) | Phase 2 PII posture (T-PII-01) preserved; no new logging surfaces in Phase 3 (D-03 says no warning for empty scoring) |
| V8 Data Protection | yes (carry-forward) | PII in CSV; default WARNING log level; README Privacy Notes section (D-11.8) explicitly documents posture |
| V12 Files & Resources | yes (low) | New env-var read (`os.environ.get`) — no file system or network operations introduced |

### Known Threat Patterns for Stdlib Python CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Env-var injection (operator-controlled) | n/a — operator owns the shell | None needed; `quiz_title` is a string copied verbatim into JSON. JSON serialization (`json.dump`, `ensure_ascii=False`) handles escaping. |
| Log injection via `quiz_title` | Tampering | None — Phase 3 does not log `quiz_title` value. README Privacy section reaffirms: warnings name columns + categorical values, never operator-supplied content. |
| Untrusted CSV cell injection into `result-logic` etc. | Tampering | Already mitigated in Phase 2 (`html.unescape` boundary, `json.dump` output escaping). Pass-through is just a dict assignment; no eval, no template injection sink. |
| README drift causing operator misconfiguration | Repudiation (operator claims they followed docs) | `tests/test_readme_help_alignment.py` smoke test (Pitfall 4) |

### Phase-Specific Threat Notes

- **No new untrusted parsing.** Phase 3 reads from `os.environ` (operator-controlled), `argv` (operator-controlled), and the same CSV that Phase 2 already validates. No new external input source.
- **No new file I/O.** Output path / dry-run / trailer-columns flags are unchanged.
- **No new network surface.** AUTO-01 (HTTP POST) is explicitly v2 / out of scope.
- **Privacy carry-forward.** Phase 2's stderr WARNING messages remain the only log surfaces; Phase 3 adds zero new log sites (D-03 forbids warning on empty scoring). PII posture per `PROJECT.md` is unchanged.

**Verdict: no high-severity threats. ASVS Level 1 controls inherited from Phase 1+2 remain sufficient. README Privacy Notes section satisfies the documentation control for V8.**

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` exists at the repository root [VERIFIED: `ls /Users/silveimar/Documents/silogia-repos/general-python-scripts/CLAUDE.md` not present]. The user's global `~/.claude/CLAUDE.md` contains only a `graphify` skill pointer, an email address, and the current date. No actionable directives constrain Phase 3 implementation beyond what `PROJECT.md` and the phase CONTEXT.md already lock.

## Sources

### Primary (HIGH confidence)
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (lines 1-381) — current implementation surface; all line-range pointers verified
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` (line 12 = `quiz_title`, lines 183-186 = 4 reserved placeholders) — authoritative target shape
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — header row at columns 28/29/30 = `Result logic`/`Score category`/`Score value` (= trailer indices 0/1/2)
- `quizify-csv-to-json-webhook/tests/conftest.py`, `test_golden_structure.py`, `test_structural_invariants.py`, `test_cli_emit.py` — Phase 2 test patterns directly extended in Phase 3
- `.planning/phases/03-scoring-metadata-packaging/03-CONTEXT.md` — locked decisions D-01..D-17
- `.planning/phases/02-core-webhook-mapping/02-01-SUMMARY.md` and `02-02-SUMMARY.md` — what Phase 2 actually built
- `.planning/REQUIREMENTS.md` — WEB-04, WEB-05, OPS-01 acceptance language
- `.planning/ROADMAP.md` — Phase 3 success criteria (3 items)
- `.planning/PROJECT.md` — stdlib-first / PII posture / per-helper folder convention
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`, ASVS Level 1

### Secondary (MEDIUM confidence)
- Python stdlib documentation knowledge for `argparse` (`default` evaluation timing), `os.environ` (live-read), `subprocess.run` (`env=` parameter), `html.unescape` semantics. Not freshly fetched; well-stable APIs.

### Tertiary (LOW confidence)
- README/`--help` drift smoke-test pattern (Pitfall 4) — community idiom, not a documented stdlib technique. Marked `[ASSUMED]`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only, all imports verified in repo
- Architecture: HIGH — every code-extension point has a verified line range
- Pitfalls: HIGH — Pitfall 3 (`--trailer-columns` override) is verified by reading `classify_headers`; Pitfalls 1, 2, 5 are verified by CONTEXT.md and code inspection. Pitfall 4 (README drift) is medium-confidence community pattern.
- Test strategy: HIGH — extends existing patterns from `tests/test_structural_invariants.py` (module-scoped subprocess fixture) and `tests/test_cli_emit.py` (subprocess CLI), both already proven on this codebase.
- Security: HIGH — threat surface inventoried; verdict (no high-severity threats) is consistent with phase scope (additive code, no new I/O / network / parsing).

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (30 days — stable stdlib + locked CONTEXT.md, low risk of drift)
