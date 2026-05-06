**Success Criteria** (what must be TRUE):
  1. `python quizify_csv_ingest.py csv -o out.ndjson --ndjson` emits exactly N lines for N rows, each terminated by a single `\n`, no `\r` bytes anywhere; `jq -s . out.ndjson` reproduces the v1.1 golden array structurally.
  2. `--ndjson --validate` against a CSV with a malformed row at position 50 of 100 exits non-zero with a JSON-Pointer-only stderr (no cell content); the final output path does not exist (only the `.tmp` sibling).
  3. Argparse rejects `--ndjson` combined with `--post-url` and rejects `--ndjson` writing to stdout (file-mode target only); error messages are categorical and PII-safe.
  4. SIGINT mid-stream leaves no partial file at the target path (verified by SIGINT test); `os.replace()` is the only path that promotes `.tmp` to final.
  5. Default array-mode invocation remains byte-identical to v1.1 (TRAIL-03 golden-fixture regression test green); D-05 top-level key order unchanged; D-13 stdlib-only-at-runtime preserved.
**Plans:** 2 plans
  - [x] 08-01-PLAN.md — RED scaffolding: test stubs for STREAM-01..04 + Pitfall 8-D regression + argparse rejections + synthetic 100-row CSV fixture + README `--ndjson` row (D-11 pre-stage).
  - [ ] 08-02-PLAN.md — GREEN implementation: `_NdjsonFileSink` (CM) + `_ValidatingSink` decorator + `_RowValidationError` + `__enter__/__exit__` shims + `--ndjson` argparse flag + 2 post-parse `parser.error` checks + `_select_sink` extension + `convert()` rewrite.