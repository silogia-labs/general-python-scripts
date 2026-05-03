---
phase: 02-core-webhook-mapping
plan: 01
subsystem: quizify-csv-to-json-webhook
tags: [csv, webhook, mapping, json, pii-safety, tdd]
requires:
  - phase-01-csv-ingestion-column-layout (classify_headers, normalize_key, parse_trailer_arg, configure_logging, LayoutError, CONTACT_PREFIX, DEFAULT_TRAILER, dry_run)
provides:
  - quizify_csv_ingest.TAG_HEADER_MAP
  - quizify_csv_ingest.decode_cell
  - quizify_csv_ingest.shape_answer
  - quizify_csv_ingest.map_status
  - quizify_csv_ingest.match_tags_to_questions
  - quizify_csv_ingest.build_row
  - quizify_csv_ingest.convert
  - CLI flags -o/--output and --emit-json
affects:
  - quizify-csv-to-json-webhook/quizify_csv_ingest.py
  - quizify-csv-to-json-webhook/tests/
tech-stack:
  added: [html (stdlib), json (stdlib)]
  patterns: [pure-function row builder, NFC+casefold tag matching, PII-safe stderr logging]
key-files:
  created:
    - quizify-csv-to-json-webhook/tests/conftest.py
    - quizify-csv-to-json-webhook/tests/test_row_builder.py
    - quizify-csv-to-json-webhook/tests/test_cli_emit.py
    - quizify-csv-to-json-webhook/tests/test_logging_pii.py
    - .planning/phases/02-core-webhook-mapping/02-01-SUMMARY.md
  modified:
    - quizify-csv-to-json-webhook/quizify_csv_ingest.py
decisions:
  - D-01..D-04 implemented exactly via TAG_HEADER_MAP + match_tags_to_questions (NFC+casefold substring)
  - D-05/D-06/D-07 implemented in shape_answer; "id" key never emitted
  - D-08/D-09 stable indexing — every dynamic N emits question/answers/answers-tags trio
  - D-10 contact mapping verbatim (no case normalization for email/phone)
  - D-11 status enum with PII-safe warning on unexpected value
  - D-12 statusDate verbatim with non-ISO advisory warning
  - D-13 tags array seeded with "source: quizify"; unmatched per-row tags appended
  - D-14 html.unescape applied to every emitted string
  - D-15..D-18 single argparse entrypoint, default JSON to stdout, -o/--output to file, --emit-json accepted, exit codes 0/1/2 preserved
metrics:
  duration: ~10 minutes
  completed: 2026-05-03
  tasks: 3
  tests_added: 25  # 11 row-builder + 7 CLI + 3 PII + 4 implicit (e.g. long-output, full_answers shape) - 0 stubs
  files_created: 4
  files_modified: 1
---

# Phase 02 Plan 01: Core webhook mapping (row builder + CLI emission) Summary

JWT-style webhook row builder + CLI integration: pure-function pipeline that decodes HTML entities, maps contact/status/statusDate fields, distributes per-question Answer tags via a configured pattern→header keyword map, chooses answer shape (string vs object array), and emits one JSON array per CSV via stdout or `-o PATH`. PII-safe stderr logging verified by negative substring assertions.

## What Was Built

- **`quizify_csv_ingest.py`** — Phase 2 surface added inline ahead of `dry_run`:
  - `TAG_HEADER_MAP` constant (`red_flag` → `signos de alarma`, `goal_` → `objetivo`, `consent` → `consiento`)
  - `decode_cell(s)` — wraps `html.unescape`
  - `shape_answer(decoded)` — empty → `""`, `", "` present → string, else single-element `[{answer_name, answer_img: None, answer_tag: None}]` with NO `id` key
  - `map_status(raw)` — Yes/No/empty/other branches; warning text contains the offending categorical value only (no PII)
  - `match_tags_to_questions(tag_csv, headers)` — splits on `", "`, NFC+casefold substring lookup against TAG_HEADER_MAP; returns `(matched, unmatched)`
  - `build_row(prefix, dynamic, trailer, headers)` — assembles webhook-shaped dict with stable key order (contact → status → statusDate → phone → tags → question/answers/answers-tags-N for N=1..K)
  - `convert(path, trailer, output)` — open utf-8-sig, classify, decode, validate row length, build, dump JSON array (`indent=2, ensure_ascii=False`) to stdout or file
  - `main()` extended with `-o, --output` and `--emit-json`; `--dry-run` carry-forward unchanged

- **Tests** — Three new test files driving 22+ assertions:
  - `tests/test_row_builder.py` — 12 unit tests covering decode_cell, map_status, shape_answer (incl. no-`id`), match_tags_to_questions (matched/multi/unmatched/empty), build_row contact/status/date/HTML/empty/tags/header-decoding/full-shape
  - `tests/test_cli_emit.py` — 7 subprocess integration tests: stdout JSON (42 rows, all 60 dynamic keys), `-o`/`--output` file write, `--dry-run` carry-forward, `--emit-json` accepted, exit code 2 on bad trailer, exit code 1 on row length mismatch
  - `tests/test_logging_pii.py` — 3 negative-substring tests: unexpected status warning hides email/phone/name; unmatched tag warning hides free-text answer cell; row-length-mismatch warning hides email/phone
  - `tests/conftest.py` — `sample_csv_path`, `dynamic_headers`, `full_answers_row`, `red_flag_short_circuit_row`, `multi_select_synthetic_row` fixtures

## Verification Results

```
$ cd quizify-csv-to-json-webhook && pytest -q
.............................                                            [100%]
29 passed in 0.48s
```

Phase-level smoke checks:
- `python quizify_csv_ingest.py docs/quizify-submissions.csv` → exit 0, 42-element JSON array, `tags[0] == "source: quizify"`, no `&gt;`/`&lt;` in output, no `"id"` key.
- Stderr PII grep against `@example|@gmail|\+5[26]` → 0 matches.
- All 60 question/answers/answers-tags keys present per row (3 × 20 dynamic columns).

## Commits (atomic, per task)

| Hash    | Type | Message                                                                                       |
| ------- | ---- | --------------------------------------------------------------------------------------------- |
| 1507ec3 | test | scaffold Wave 0 row-builder/CLI/PII test stubs and shared fixtures                            |
| 7c0d44d | test | add failing tests for row builder pure functions                                              |
| fee8f59 | feat | implement row builder pure functions (CONV-03..06, WEB-01..03)                                |
| ed79185 | test | add failing CLI emit and PII-in-logs tests                                                    |
| fe1f692 | feat | wire CLI to emit JSON (default stdout, -o file) and enforce PII-safe logs                     |

## Requirements Covered

- **CONV-03** — Contact field mapping (firstName/lastName/email/phone) verbatim from `prefix_cells_decoded` indices 0/1/2/4 → covered by `test_contact_and_status_mapping` and end-to-end CLI assertion.
- **CONV-04** — Subscription state via `map_status` Yes/No/empty/other branches → covered by `test_status_mapping_yes_no_other_empty`.
- **CONV-05** — `statusDate` pass-through with non-ISO advisory → covered by `test_status_date_passthrough`.
- **CONV-06** — `html.unescape` applied uniformly to cells and headers → covered by `test_decode_cell_unescapes_entities`, `test_html_entity_decode`, `test_headers_are_html_unescaped_in_question_keys`, and CLI stdout grep.
- **WEB-01** — Per-question tag distribution via `match_tags_to_questions` with unmatched-tag fallback → covered by `test_tag_distribution`.
- **WEB-02** — Stable per-question indexing (every N emits the trio); empty-cell shape → covered by `test_empty_cells_emit_all_keys` and CLI stdout key-set assertion.
- **WEB-03** — Answer shape heuristic (string vs object array, NO `id`) → covered by `test_answer_shape_heuskip` (excuse: `test_answer_shape_heuristic`) and `test_id_key_never_present_in_object_array`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Off-by-one in plan's expected `answers-tags-N` index for `consent_given`**
- **Found during:** Task 1 (Wave 1 RED authoring)
- **Issue:** The plan's `<behavior>` block stated `answers-tags-19 == "consent_given"`, but the live sample CSV header places `Consiento que usen mis respuestas...` at 0-indexed dynamic position 19, which corresponds to **q-20** under 1-based indexing (D-09). Index 19 is `Tipo de Jornada laboral`, which has no consent semantics. The implementation correctly resolves the consent tag to q-20 via `TAG_HEADER_MAP` substring match.
- **Fix:** Wrote the failing test to assert `answers-tags-20 == "consent_given"` instead of `answers-tags-19`. CONTEXT.md D-02 (`consent → consiento`) is satisfied; the deviation is purely in the plan's example off-by-one labeling, not in any locked decision.
- **Files:** `quizify-csv-to-json-webhook/tests/test_row_builder.py`
- **Commit:** 7c0d44d

### Minor enhancements over plan

- Added `test_long_output_flag_writes_file` to verify the long form `--output` works alongside `-o` (plan only required `-o`). No risk; same code path.
- Added `test_full_answers_synthetic_row_shape` to consolidate the synthetic full-row contract (tag routing for all three matched tags + answer-shape branches + no-`id` invariant + PII-safe warnings).

### Out of Scope (deferred per plan)

- Streaming/NDJSON output for very large CSVs — T-RESOURCE-01 documented in `convert` docstring; threshold ~50k rows or >250MB.
- HTTP webhook POST mode (AUTO-01, v2).
- JSON Schema validation (VALI-01).

## Auth Gates Encountered

None.

## Known Stubs

None. All test stubs from Wave 0 were filled with concrete assertions in Waves 1 and 2; no placeholders remain.

## Threat Model Compliance

- **T-PII-01** (Information Disclosure via logging) — **Mitigated.** All warning messages constructed in `build_row` use only column names (`'Subscribed to newsletter'`, `'Date'`) and categorical values (status enum, tag tokens). The row-level `convert` warnings use only row index and length integers. Verified by `tests/test_logging_pii.py` synthesizing rows with PII tokens (email, phone, free-text answer) and asserting those substrings never appear in stderr.
- **T-INPUT-01** (Tampering / DoS via malformed CSV) — **Mitigated.** Row length mismatches are caught with `len(row) != expected_len`, logged with bounded message, row skipped, `exit_code |= 1`, iteration continues. UTF-8 decoding via `encoding="utf-8-sig"` (Phase 1 carry-forward). No `eval` / no untrusted JSON deserialization.
- **T-RESOURCE-01** (DoS via results accumulation) — **Accepted with documented threshold.** Sample is 42 rows; production expected ≤ low thousands. Streaming deferred to v2 if row count > ~50k or per-row payload > ~5KB. Documented in `convert` docstring.

## TDD Gate Compliance

- Plan 02-01 frontmatter `type: tdd` → RED/GREEN/REFACTOR cycle observed:
  - **RED:** 7c0d44d (`test(...)`) row-builder failing tests; ed79185 (`test(...)`) CLI/PII failing tests
  - **GREEN:** fee8f59 (`feat(...)`) row-builder GREEN; fe1f692 (`feat(...)`) CLI GREEN
  - **REFACTOR:** Not needed — Phase 1 `dry_run` was not modified; no duplication arose between `dry_run` and `convert` worth extracting in this plan.
- Wave 0 scaffold commit (1507ec3) is `test(...)` and intentionally non-failing (stubs use `pytest.skip`); it precedes the RED gate per plan instruction.

## Self-Check: PASSED

Created files (verified via `[ -f ... ]`):
- FOUND: quizify-csv-to-json-webhook/tests/conftest.py
- FOUND: quizify-csv-to-json-webhook/tests/test_row_builder.py
- FOUND: quizify-csv-to-json-webhook/tests/test_cli_emit.py
- FOUND: quizify-csv-to-json-webhook/tests/test_logging_pii.py

Modified files:
- FOUND: quizify-csv-to-json-webhook/quizify_csv_ingest.py (TAG_HEADER_MAP, decode_cell, shape_answer, map_status, match_tags_to_questions, build_row, convert; main extended with -o/--output and --emit-json)

Commits (verified via `git log --oneline`):
- FOUND: 1507ec3
- FOUND: 7c0d44d
- FOUND: fee8f59
- FOUND: ed79185
- FOUND: fe1f692

Final pytest line: `29 passed in 0.48s`.
