# Quizify CSV → Webhook JSON

A single-file Python CLI that converts Quizify CSV exports (UTF-8) into
webhook-compatible JSON arrays matching
[`docs/webhook-quizify-format-example.json`](docs/webhook-quizify-format-example.json).
Offline-first, stdlib-only, no third-party dependencies at runtime.

## Purpose

`quizify_csv_ingest.py` reads a Quizify CSV submissions export and emits a JSON
array of per-row dictionaries shaped for downstream webhook receivers. It runs
locally, performs no network I/O, and depends only on the Python standard
library. The tool is a single-file CLI by design; there is no library import
surface to manage.

## Quickstart

```bash
python quizify_csv_ingest.py docs/quizify-submissions.csv --quiz-title "Autoevaluacion" -o out.json
```

Run from `quizify-csv-to-json-webhook/`. Sample input:
[`docs/quizify-submissions.csv`](docs/quizify-submissions.csv); target shape:
[`docs/webhook-quizify-format-example.json`](docs/webhook-quizify-format-example.json);
formal contract: [`docs/webhook-schema.json`](docs/webhook-schema.json).

Optional — enable schema validation:

```bash
cd quizify-csv-to-json-webhook
pip install '.[validate]'
```

The `[validate]` extra installs `fastjsonschema` so the `--validate` flag can check the emitted JSON against [`docs/webhook-schema.json`](docs/webhook-schema.json). Default invocations remain stdlib-only.

## CLI reference

`csv_path` is a positional argument: the path to a Quizify CSV export
(UTF-8). The flags below are all optional.

| Flag | Default | Description | Env var |
|------|---------|-------------|---------|
| `--dry-run` | off | Print layout summary to stderr; no JSON output. | — |
| `-v`, `--verbose` | WARNING | Raise log level to INFO with structural detail. | — |
| `--trailer-columns CSV` | `None` | Override default trailer columns (comma-separated, ordered). | — |
| `-o`, `--output PATH` | stdout | Write JSON array to PATH (UTF-8). | — |
| `--emit-json` | off | Explicit JSON emission; redundant with default behavior. | — |
| `--quiz-title VALUE` | `""` | Quiz title; decoded via `html.unescape`; whitespace preserved. | `QUIZIFY_QUIZ_TITLE` |
| `--validate` | off | Validate emitted JSON against `docs/webhook-schema.json` (requires `[validate]` extra). Validation runs only when JSON output is produced; `--dry-run` skips it. | — |
| `--post-url URL` | `—` | HTTPS-only single-shot POST of the JSON array body. Requires `--validate`. Mutually exclusive with `-o/--output` and `--ndjson`. Exit `3` on HTTP/network failure with categorical PII-safe stderr. | — |
| `--header "K: V"` | `[]` | Repeatable: add an HTTP header to the POST request (e.g., `--header "Authorization: Bearer ..."`). CRLF in values rejected at argparse. Applies only with `--post-url`. | — |
| `--timeout SECONDS` | `30.0` | HTTP request timeout in seconds (float). Applies only with `--post-url`. Values `<= 0` rejected at argparse. | — |
| `--ndjson` | off (array mode) | Emit line-delimited JSON; requires `-o/--output`; cannot combine with `--post-url`. With `--validate`, validates each row against `schema["items"]` and exits 1 on first failure with a categorical JSON Pointer (no cell content). | — |

## Configuration

Settings resolved at invocation time, in order of precedence.

| Setting    | CLI flag        | Env var               | Default | Notes                                |
|------------|-----------------|-----------------------|---------|--------------------------------------|
| Quiz title | `--quiz-title`  | `QUIZIFY_QUIZ_TITLE`  | `""`    | CLI > env > future CSV column > `""` |

Precedence resolution: the `--quiz-title` CLI flag wins when present; otherwise
the `QUIZIFY_QUIZ_TITLE` env var is used. A future per-CSV `Quiz title` column
is reserved as a stub in the precedence chain (not implemented in v1) — the
real export header has not been observed yet, so the lookup is intentionally
absent. When neither flag nor env is set, the value falls back to the empty
string. `html.unescape` is applied to the resolved value (so a CLI value like
`Salud &amp; Bienestar` becomes `Salud & Bienestar` in the output);
whitespace is preserved verbatim.

## Column assumptions

- **Contact prefix (first 6 columns):** `First name`, `Last name`, `Email`,
  `Lead Verified`, `Phone`, `Subscribed to newsletter`. A header mismatch
  aborts with exit code `1`.
- **Trailer block (last 6 columns by default):** `Result logic`,
  `Score category`, `Score value`, `Answer tags`,
  `Time to complete (mm:ss)`, `Date`. Override with
  `--trailer-columns "name1,name2,..."`. The scoring trio
  (`Result logic`, `Score category`, `Score value`) is bound to the
  output keys `result-logic`, `score-category`, `score-value` by
  canonical column name (NFC + casefold equality), so reordering those
  three names within `--trailer-columns` is safe. If a canonical trio
  column is omitted from `--trailer-columns` entirely, the
  corresponding output key is emitted as `""` and a PII-safe stderr
  `WARNING` names the absent column at startup. `Answer tags` and
  `Date` continue to be read positionally (trailer indices 3 and 5);
  keep those two in their default positions if you reorder the trailer.
- **Dynamic question block (everything between):** mapped in header order to
  `question-1` … `question-K`. See
  [`docs/quizify-submissions.csv`](docs/quizify-submissions.csv) for the
  reference layout.

## Output shape

See
[`docs/webhook-quizify-format-example.json`](docs/webhook-quizify-format-example.json)
for the canonical target shape. Per-row dict key order is fixed:

1. Contact + tags block: `email`, `firstName`, `lastName`, `status`,
   `statusDate`, `phone`, `tags`
2. `quiz_title` (resolved per Configuration)
3. Per-question triples: `question-N`, `answers-N`, `answers-tags-N` for
   N=1..K
4. Pass-through scoring keys: `result-logic`, `score-category`, `score-value`
5. Reserved placeholder keys: `product-recommendation`, `product-link-type`,
   `title`, `type-page-url`

### Omitted keys

`id` keys are omitted entirely when unknown — the CSV export does not contain
answer IDs. The exporter never emits `id: null`; consumers should treat the
absence of `id` as "not derivable from this source."

### Reserved keys

`product-recommendation`, `product-link-type`, `title`, and `type-page-url`
are emitted with locked defaults (`null`, `null`, `""`, `""`) because the CSV
export does not contain these fields. Downstream consumers must NOT interpret
`product-recommendation: null` as "Quizify said no recommendation" — it means
"this exporter cannot supply this field." Fetch from the source-of-truth API
if the real value is required.

### Scoring pass-through

`result-logic`, `score-category`, and `score-value` carry the verbatim decoded
strings from the CSV trailer columns `Result logic`, `Score category`, and
`Score value` respectively. `Score value` is string-typed; receivers parse
the value if numeric semantics are required.

## Limitations

- Answer IDs are not present in the CSV export; the JSON omits the `id` key
  rather than emitting `id: null`.
- Multi-select answers are detected by a comma-space heuristic (`, ` in the
  cell): cells matching are emitted as plain strings; otherwise as a
  single-element array of `{answer_name, answer_img, answer_tag}` objects.
- Subscription status mapping: `Yes` → `subscribed`, `No` or empty →
  `unsubscribed`. Any other value emits `unsubscribed` plus a stderr
  `WARNING` naming the unexpected categorical value.
- `statusDate` is the CSV `Date` cell verbatim; ISO `YYYY-MM-DD` shape is
  verified loosely; non-ISO values pass through with a `WARNING` (no
  timezone invention).
- Every row emits every key (including empty `answers-N: ""`) for stable
  downstream indexing.
- `Score value` is string-typed (e.g., `"500"`, `"6"`); no numeric coercion
  is performed.
- Reserved placeholder keys (`product-recommendation`, `product-link-type`,
  `title`, `type-page-url`) emit `null` / `""` because the CSV cannot
  supply them.
- HTTP POST / webhook-send mode (`--post-url`) lands in v1.2 Phase 9 as
  HTTPS-only single-shot delivery; see the CLI reference for the contract.

## Privacy notes

CSV exports contain PII (names, emails, phone numbers). The default log level
is `WARNING`; emitted warnings name only column names and categorical values
(e.g., `unexpected status value 'Maybe'`), never row content like email
addresses or phone numbers. `-v`/`--verbose` raises the log level to `INFO`
with structural detail only — column counts, indices, and layout hints — and
still does not emit cell content.

Output JSON is the operator's responsibility. Treat output files written via
`-o PATH` as PII-bearing artifacts. The tool does no network I/O — output
goes to stdout or to the operator-named file path, and nowhere else.

## Exit codes

| Code | Meaning                                        |
|------|------------------------------------------------|
| 0    | Success                                        |
| 1    | Input/layout error or one or more rows skipped |
| 2    | CLI usage error (invalid flag value)           |

## Development

Runtime is stdlib-only — there is no `requirements.txt`. Tooling (pytest)
lives in `requirements-dev.txt`: `pip install -r requirements-dev.txt`. Run
the test suite with `cd quizify-csv-to-json-webhook && pytest -q`.

Tests live under `tests/`. Layout classification, the row builder, CLI
emission, structural invariants over the live sample CSV, golden-file diff
against the example payload, `quiz_title` precedence, and README/`--help`
drift are all exercised under `pytest`.
