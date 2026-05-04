---
phase: 03-scoring-metadata-packaging
plan: 02
subsystem: operator-documentation
tags: [docs, readme, python, cli, drift-test]
requires:
  - quizify_csv_ingest argparse parser (Phase 3 final flag surface)
  - quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json (linked)
  - quizify-csv-to-json-webhook/docs/quizify-submissions.csv (linked)
provides:
  - quizify-csv-to-json-webhook/README.md (operator doc per D-11)
  - tests/test_readme_help_alignment.py (OPS-01 drift smoke test)
affects:
  - quizify-csv-to-json-webhook/README.md
  - quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py
tech-stack:
  added: []
  patterns: ["subprocess --help capture", "regex flag extraction", "substring drift assertion"]
key-files:
  created:
    - quizify-csv-to-json-webhook/README.md
    - quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py
  modified: []
decisions:
  - "Used subprocess --help capture (not in-process parser introspection) for the drift test — argparse parser is not exposed as a separate function; subprocess is the only stable contract."
  - "Regex `--[a-z][a-z0-9-]+` extracts long flags (excluding `--help`); short flags like `-v` and `-o` are documented in README but not asserted by the drift test (their presence is implicitly enforced by the long alias appearing in `--help`)."
  - "README CLI reference table written by hand (CONTEXT Claude's Discretion); flag count is small (6 long flags) and auto-generation would add machinery for no benefit. Drift test catches future divergence."
  - "Hand-wrote 169-line README; aimed at the 120-180 line band per the plan's authoring constraints."
metrics:
  duration: "~10 minutes"
  completed: 2026-05-03
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 2
  test_runtime_added: "~40ms"
  test_count_total: 71
---

# Phase 03 Plan 02: Operator README + drift smoke test Summary

OPS-01 closed: `quizify-csv-to-json-webhook/README.md` ships as the v1 operator
doc per D-11's locked 10-section structure (169 lines), and
`tests/test_readme_help_alignment.py` enforces ongoing parity between the
`argparse --help` output and the README — future flags cannot land without a
documentation update.

## What Was Built

**Documentation (`quizify-csv-to-json-webhook/README.md`, 169 lines):**

10 sections in D-11 order:

1. **Purpose** — single paragraph: stdlib-only Python CLI; CSV → webhook JSON
   array; offline; no network I/O.
2. **Quickstart** — fenced bash block with the locked invocation
   `python quizify_csv_ingest.py docs/quizify-submissions.csv --quiz-title "Autoevaluacion" -o out.json`
   plus pointers to the sample CSV and target shape.
3. **CLI reference** — markdown table covering every flag from
   `<post_phase3_cli_surface>`: `--dry-run`, `-v`/`--verbose`,
   `--trailer-columns CSV`, `-o`/`--output PATH`, `--emit-json`,
   `--quiz-title VALUE` plus the `csv_path` positional. Env var column
   reserved for `--quiz-title` only.
4. **Configuration** — D-14 markdown table (Setting / CLI flag / Env var /
   Default / Notes) with the single `Quiz title` row, plus a precedence
   paragraph documenting `html.unescape` decode and whitespace preservation.
5. **Column assumptions** — three bullets: contact prefix (6 columns),
   trailer block (6 columns) with the positional-scoring caveat from
   RESEARCH Pitfall 3, dynamic question block.
6. **Output shape** — numbered key-order list per D-05 plus three callout
   subsections: `### Omitted keys` (id absence per Phase 2 D-07),
   `### Reserved keys` (4 placeholders per D-02), `### Scoring pass-through`
   (verbatim D-01 / D-04).
7. **Limitations** — 9 bullets covering missing IDs, comma-in-cell heuristic,
   status mapping, ISO-date pass-through, always-emit-all-keys, Score value
   string typing, `--trailer-columns` positional risk, reserved placeholder
   semantics, and v2 deferrals.
8. **Privacy notes** — two paragraphs: stderr-WARNING posture (T-PII-01
   carry-forward), output-file ownership.
9. **Exit codes** — markdown table: `0` / `1` / `2`.
10. **Development** — pytest tooling in `requirements-dev.txt`; runtime is
    stdlib-only; no `requirements.txt` (D-13).

No worked CSV→JSON example block (D-12). All links relative.

**Tests (`tests/test_readme_help_alignment.py`, 63 lines):**

- `test_readme_has_all_required_sections` — asserts all 10 D-11 section
  headings are present as `## ` text in `README.md`.
- `test_every_flag_named_in_readme` — runs `python quizify_csv_ingest.py
  --help` via `subprocess.run(check=True, timeout=30)`, regex-extracts
  long-form flags (`--[a-z][a-z0-9-]+`), discards `--help`, and asserts every
  remaining flag appears as a substring of `README.md`.

Both tests use the established `ROOT = Path(__file__).resolve().parents[1]` /
`SCRIPT = ROOT / "quizify_csv_ingest.py"` constants from
`tests/test_structural_invariants.py` and `tests/test_cli_emit.py`.

## Sections Emitted (D-11 order verified)

| # | Heading | Lines |
|---|---------|-------|
| 1 | `## Purpose` | 1 paragraph |
| 2 | `## Quickstart` | 1 fenced block + pointer sentence |
| 3 | `## CLI reference` | 1 paragraph + 6-row table |
| 4 | `## Configuration` | 1 sentence + 1-row table + precedence paragraph |
| 5 | `## Column assumptions` | 3 bullets |
| 6 | `## Output shape` | numbered list + 3 callout subsections |
| 7 | `## Limitations` | 9 bullets |
| 8 | `## Privacy notes` | 2 paragraphs |
| 9 | `## Exit codes` | 3-row table |
| 10 | `## Development` | 2 paragraphs |

Verified by the structural grep gate in Task 1's `<verify>` block (all 10
section headings + all 6 long flags + `QUIZIFY_QUIZ_TITLE` + 2 fixture
links).

## Flags Documented (parity with `<post_phase3_cli_surface>`)

| Flag | In README? | In `--help`? |
|------|-----------|--------------|
| `csv_path` (positional) | yes | yes |
| `--dry-run` | yes | yes |
| `-v` / `--verbose` | yes | yes |
| `--trailer-columns` | yes | yes |
| `-o` / `--output` | yes | yes |
| `--emit-json` | yes | yes |
| `--quiz-title` | yes | yes |

Drift test (`test_every_flag_named_in_readme`) confirms every long flag from
the live `--help` output appears in `README.md`.

## Tests Added

| File | New Tests | Topic |
|------|-----------|-------|
| `tests/test_readme_help_alignment.py` | 2 | OPS-01 drift detection (sections + flag parity) |

**Test runtime added:** ~40ms (single subprocess `--help` call, ~30ms; two
file reads, <10ms).

**Full suite:** `cd quizify-csv-to-json-webhook && pytest -q` →
`71 passed in 1.09s` (69 from Phase 1+2+3-01, +2 from this plan).

## Deviations from Plan

None — plan executed exactly as written. The `<verify>` automated grep gate
in Task 1 surfaced an environment quirk (the system's `grep` is `ugrep`,
which interprets `--dry-run` as an option) but the verification semantics
were satisfied via the equivalent `grep -F --` invocation; no plan-content
deviation. The drift test itself implements the exact code given in the plan
verbatim.

## Manual Smoke Verification

Ran the README's Quickstart command from `quizify-csv-to-json-webhook/`:

```
$ python quizify_csv_ingest.py docs/quizify-submissions.csv --quiz-title "Autoevaluacion" -o /tmp/qz_smoke.json
[8 stderr WARNING lines about row tags — expected behavior, T-PII-01-compliant]

rows: 42
quiz_title: Autoevaluacion
result-logic: Score
```

Clean exit (`returncode == 0`), 42 rows emitted, `quiz_title` and
`result-logic` populated as expected. The Configuration table accurately
reflects the CLI > env > default precedence demonstrated in plan 03-01's
manual smoke. Limitations cover missing IDs, comma-in-cell heuristic,
reserved placeholders, and Score value string typing. Privacy Notes match
the Phase 2 stderr-warning posture (warnings name the categorical tag value
`'no_pelvic_symptom'`, never row content).

## Confirmation: D-13 honored

No `requirements.txt` was created. The Development section explicitly states
"there is no `requirements.txt`" and points operators to
`requirements-dev.txt` for pytest tooling.

```
$ ls quizify-csv-to-json-webhook/requirements*.txt
quizify-csv-to-json-webhook/requirements-dev.txt
```

## Auth Gates

None — README is read-only documentation; the drift test invokes the local
script with no external services or credentials.

## Threat Model Coverage

| Threat ID | Mitigation Verified |
|-----------|--------------------|
| T-V8-01 (Information Disclosure / README PII posture) | README `## Privacy notes` documents default `WARNING` log level; warnings name columns + categorical values, never cell content. |
| T-REPUDIATION-01 ("I followed the README") | `test_every_flag_named_in_readme` asserts flag-name parity between `--help` output and README text. |
| T-DOCDRIFT-01 (silent flag/section drift) | `test_every_flag_named_in_readme` catches additions; `test_readme_has_all_required_sections` catches structural deletions. |
| T-PII-01 (carry-forward) | No new log surfaces in Phase 3; documentation reaffirms posture. |

## Hand-off

**Phase 3 milestone scope is complete.** All 11 v1 requirements (CONV-01..06,
WEB-01..05, OPS-01) are now satisfied or — for the Phase 1/2 requirements —
inherit from prior phases. Ready for `/gsd-verify-work` then
`/gsd-complete-milestone`.

## Self-Check: PASSED

Verified files exist and commits are present:

```
FOUND: quizify-csv-to-json-webhook/README.md (169 lines)
FOUND: quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py
FOUND: commit 093093c (Task 1 — README authoring)
FOUND: commit 4769bfb (Task 2 — drift smoke test)
PASSED: full pytest suite (71/71 in 1.09s)
PASSED: structural grep gate (all 10 sections + 6 long flags + env var + 2 fixture links present)
PASSED: Quickstart smoke (42 rows emitted, exit 0, quiz_title and scoring populated)
```
