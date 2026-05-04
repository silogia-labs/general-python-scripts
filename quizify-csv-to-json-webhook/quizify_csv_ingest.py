#!/usr/bin/env python3
"""Quizify CSV layout scanner — Phase 1 (classification + dry-run preview)."""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import os
import sys
import unicodedata
from pathlib import Path

CONTACT_PREFIX = (
    "First name",
    "Last name",
    "Email",
    "Lead Verified",
    "Phone",
    "Subscribed to newsletter",
)

DEFAULT_TRAILER = (
    "Result logic",
    "Score category",
    "Score value",
    "Answer tags",
    "Time to complete (mm:ss)",
    "Date",
)

# D-05-08: output-key mapping for the missing-column WARNING in convert().
# Compile-time constant — values come from D-05's locked output schema; these
# are NEVER user-controlled, so interpolating them in a log message is safe.
_OUTPUT_KEY_BY_CANONICAL: dict[str, str] = {
    "Result logic":   "result-logic",
    "Score category": "score-category",
    "Score value":    "score-value",
}


class LayoutError(ValueError):
    """Raised when header row does not match expected Quizify layout."""


def normalize_key(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def parse_trailer_arg(s: str) -> tuple[str, ...]:
    parts = [p.strip() for p in s.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        raise ValueError("empty trailer-columns")
    return tuple(parts)


def classify_headers(
    header_row: list[str],
    trailer: tuple[str, ...] | None = None,
) -> tuple[list[str], list[str], list[str], dict[str, int], tuple[str, ...]]:
    trailer = trailer if trailer is not None else DEFAULT_TRAILER
    p_len = len(CONTACT_PREFIX)
    t_len = len(trailer)
    n = len(header_row)
    if n < p_len + t_len + 1:
        raise LayoutError(
            f"Header too short ({n} columns); need contact ({p_len}), "
            f"at least one dynamic column, and trailer ({t_len})."
        )
    for i, expected in enumerate(CONTACT_PREFIX):
        if normalize_key(header_row[i]) != normalize_key(expected):
            raise LayoutError(
                f"Contact prefix mismatch at column {i}: expected {expected!r}, got {header_row[i]!r}"
            )
    for i, expected in enumerate(trailer):
        hi = n - t_len + i
        if normalize_key(header_row[hi]) != normalize_key(expected):
            raise LayoutError(
                f"Trailer mismatch at column {hi}: expected {expected!r}, got {header_row[hi]!r}"
            )
    prefix_raw = header_row[:p_len]
    dynamic = header_row[p_len : n - t_len]
    trailer_raw = header_row[n - t_len :]

    # D-05-01 / D-05-03 / Pitfall 9 / Pitfall 11:
    # Build a name-keyed scoring index map by exact NFC+casefold equality
    # against the canonical display-form names from DEFAULT_TRAILER[:3].
    # NEVER substring (`in`); NEVER `.lower()` or normalize_key for the trio
    # match (only `_norm_for_match`); NEVER log here (D-05-07).
    scoring_index_map: dict[str, int] = {}
    missing_trio_names: list[str] = []
    for canonical in DEFAULT_TRAILER[:3]:
        canonical_norm = _norm_for_match(canonical)
        idx = next(
            (i for i, h in enumerate(trailer_raw) if _norm_for_match(h) == canonical_norm),
            None,
        )
        if idx is not None:
            scoring_index_map[canonical] = idx
        else:
            missing_trio_names.append(canonical)
    return prefix_raw, dynamic, trailer_raw, scoring_index_map, tuple(missing_trio_names)


TAG_HEADER_MAP = {
    "red_flag": "signos de alarma",
    "goal_": "objetivo",
    "consent": "consiento",
}

# Phase 3 D-02: reserved placeholder keys with locked defaults; the CSV cannot
# supply these, so we emit hard-coded values that match the example payload's
# structural slots. Insertion order matches D-05's final-tail key order.
SCORING_PLACEHOLDERS = {
    "product-recommendation": None,
    "product-link-type": None,
    "title": "",
    "type-page-url": "",
}

SCHEMA_PATH = Path(__file__).resolve().parent / "docs" / "webhook-schema.json"


def decode_cell(s: str) -> str:
    """Decode HTML entities in a CSV cell (CONV-06, D-14). Identity on empty."""
    return html.unescape(s)


def shape_answer(decoded: str):
    """Return webhook-shaped answer per D-05/D-06/D-08.

    "" → "" ; ", " in cell → plain string ; else → single-element object array.
    Never emits an "id" key (D-07).
    """
    if decoded == "":
        return ""
    if ", " in decoded:
        return decoded
    return [{"answer_name": decoded, "answer_img": None, "answer_tag": None}]


def map_status(raw: str) -> tuple[str, str | None]:
    """D-11: Yes→subscribed; No/empty→unsubscribed silent; other→unsubscribed+warn.

    The warning message intentionally contains only the offending categorical
    value (no email/phone/name) so it is PII-safe (T-PII-01).
    """
    v = raw.strip()
    if v == "Yes":
        return ("subscribed", None)
    if v == "No" or v == "":
        return ("unsubscribed", None)
    return ("unsubscribed", f"unexpected status value {v!r}")


def _resolve_quiz_title(args: argparse.Namespace, environ) -> str:
    """D-07 precedence: CLI flag > env var > "" (future CSV column stub).

    Decodes via html.unescape at the boundary (D-09); whitespace preserved
    (D-09 forbids .strip()).
    """
    if args.quiz_title is not None:
        return html.unescape(args.quiz_title)
    env_val = environ.get("QUIZIFY_QUIZ_TITLE")
    if env_val is not None:
        return html.unescape(env_val)
    # Future: CSV "Quiz title" column lookup goes here (D-07 stub; do not
    # invent the header name without a real export proving it).
    return ""


def _norm_for_match(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()


def _looks_iso(s: str) -> bool:
    """Lightweight YYYY-MM-DD shape check; full date parsing deferred."""
    if len(s) != 10:
        return False
    return (
        s[4] == "-"
        and s[7] == "-"
        and s[:4].isdigit()
        and s[5:7].isdigit()
        and s[8:].isdigit()
    )


def match_tags_to_questions(
    tag_csv: str,
    dynamic_headers_decoded: list[str],
) -> tuple[dict[int, list[str]], list[str]]:
    """D-01..D-04: distribute Answer tags across dynamic question indices.

    Splits on ", "; for each tag, finds the first TAG_HEADER_MAP pattern that is
    a substring of the tag, then locates the first dynamic header whose
    NFC+casefold form contains the corresponding header keyword. Multiple tags
    matching the same question accumulate (caller joins with ", "). Tags that
    match no pattern (or whose pattern's keyword is missing from the headers)
    are returned as `unmatched`.
    """
    matched: dict[int, list[str]] = {}
    unmatched: list[str] = []
    if not tag_csv.strip():
        return matched, unmatched
    norm_headers = [_norm_for_match(h) for h in dynamic_headers_decoded]
    for tag in (t.strip() for t in tag_csv.split(", ") if t.strip()):
        tag_norm = _norm_for_match(tag)
        hit_idx: int | None = None
        for pattern, header_kw in TAG_HEADER_MAP.items():
            if _norm_for_match(pattern) in tag_norm:
                kw_norm = _norm_for_match(header_kw)
                hit_idx = next(
                    (i for i, h in enumerate(norm_headers) if kw_norm in h),
                    None,
                )
                if hit_idx is not None:
                    matched.setdefault(hit_idx, []).append(tag)
                    break
        if hit_idx is None:
            unmatched.append(tag)
    return matched, unmatched


def build_row(
    prefix_cells_decoded: list[str],
    dynamic_cells_decoded: list[str],
    trailer_cells_decoded: list[str],
    dynamic_headers_decoded: list[str],
    quiz_title: str,
    scoring_index_map: dict[str, int],
) -> tuple[dict, list[str]]:
    """Build a single webhook-shaped row dict from already-decoded cells.

    Caller MUST pass cells already through decode_cell (per RESEARCH per-row
    build sequence step 4). Returns (row_dict, warnings) where warnings is a
    list of stderr-safe strings (no email/phone/name/free-text).

    Key order: email, firstName, lastName, status, statusDate, phone, tags,
    then question-N / answers-N / answers-tags-N for N=1..K (D-09).
    """
    warnings_out: list[str] = []
    first_name = prefix_cells_decoded[0]
    last_name = prefix_cells_decoded[1]
    email = prefix_cells_decoded[2]
    phone = prefix_cells_decoded[4]
    status_raw = prefix_cells_decoded[5]

    status_value, status_warn = map_status(status_raw)
    if status_warn is not None:
        warnings_out.append(f"column 'Subscribed to newsletter' {status_warn}")

    status_date = trailer_cells_decoded[5]
    if status_date and not _looks_iso(status_date):
        warnings_out.append(
            f"column 'Date' value {status_date!r} is not ISO YYYY-MM-DD; emitted verbatim"
        )

    answer_tags_csv = trailer_cells_decoded[3]
    matched_buckets, unmatched_tags = match_tags_to_questions(
        answer_tags_csv, dynamic_headers_decoded
    )

    tags_list: list[str] = ["source: quizify"]
    for u in unmatched_tags:
        tags_list.append(u)
        warnings_out.append(
            f"tag {u!r} did not match any question; appended to row tags"
        )

    row: dict = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "status": status_value,
        "statusDate": status_date,
        "phone": phone,
        "tags": tags_list,
        "quiz_title": quiz_title,
    }
    for i, header in enumerate(dynamic_headers_decoded):
        n = i + 1
        cell = dynamic_cells_decoded[i] if i < len(dynamic_cells_decoded) else ""
        row[f"question-{n}"] = header
        row[f"answers-{n}"] = shape_answer(cell)
        row[f"answers-tags-{n}"] = ", ".join(matched_buckets.get(i, []))
    # TRAIL-01 / D-05-04 / D-05-10 / Pitfall 10:
    # Name-keyed scoring trio binding. The lookup index comes from
    # scoring_index_map (built once in classify_headers via NFC+casefold).
    # If a canonical trio column is absent from --trailer-columns, emit "".
    # NEVER add a positional fallback to indices 0/1/2 — the empty-string
    # branch is the ONLY behavior on a missing canonical name.
    # D-03 / D-05-09 carry-forward: empty cell in present column stays silent.
    row["result-logic"]   = trailer_cells_decoded[scoring_index_map["Result logic"]]   if "Result logic"   in scoring_index_map else ""
    row["score-category"] = trailer_cells_decoded[scoring_index_map["Score category"]] if "Score category" in scoring_index_map else ""
    row["score-value"]    = trailer_cells_decoded[scoring_index_map["Score value"]]    if "Score value"    in scoring_index_map else ""
    # Phase 3 D-02: 4 reserved placeholders, locked defaults. dict.update preserves
    # SCORING_PLACEHOLDERS' declared insertion order, which matches D-05's tail.
    row.update(SCORING_PLACEHOLDERS)
    return row, warnings_out


def configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", stream=sys.stderr, force=True)


def dry_run(path: Path, trailer: tuple[str, ...] | None) -> int:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            logging.error("CSV is empty")
            return 1
        try:
            _prefix, dynamic, _trailer_h, _scoring_map, _missing = classify_headers(header, trailer)
        except LayoutError as err:
            logging.error("%s", err)
            return 1
        k = len(dynamic)
        print(f"Questions (dynamic): {k}", file=sys.stderr)
        for h in dynamic:
            print(f"Dynamic: {h}", file=sys.stderr)
        row_warned = False
        data_rows = 0
        expected_len = len(header)
        for row in reader:
            data_rows += 1
            if len(row) != expected_len and not row_warned:
                logging.warning(
                    "row length mismatch: expected %s fields, got %s (further mismatches not logged)",
                    expected_len,
                    len(row),
                )
                row_warned = True
        print(f"Rows (data): {data_rows}", file=sys.stderr)
    return 0


def _format_validation_error(err) -> str:
    """Format a fastjsonschema.JsonSchemaValueException → D-06-20 PII-safe stderr.

    Uses ONLY categorical attributes — NEVER `err.message` / `err.value` / `str(err)`,
    which echo cell content (Pitfall 17, T-PII-01).

    Categorical inputs:
      err.path          : list[str], starts with literal 'data' (validator's own
                          variable name; not user data — RESEARCH Assumption A2).
      err.definition    : dict, the failing schema clause (categorical types).
      type(err.value)   : Python type — yields 'str'/'int'/'NoneType'/'list'/'dict'.
    """
    pointer = "/" + "/".join(err.path[1:]) if len(err.path) > 1 else "/"
    expected = (err.definition or {}).get("type", "<unknown>")
    if isinstance(expected, list):  # union type, e.g. ["string", "null"]
        expected = "|".join(expected)
    actual = type(err.value).__name__
    return f"ERROR schema validation failed at {pointer}: expected {expected}, got {actual}"


def _run_schema_validation(rows: list[dict], schema_path: Path) -> int:
    """Validate `rows` against the Draft-07 schema at `schema_path`.

    Returns 0 on success, 1 on any failure (D-06-21).

    Discipline (locked):
      - Lazy `import fastjsonschema` inside the body (D-06-17, Pitfall 18) so the
        default CLI path (no --validate) never loads the optional dependency,
        preserving D-13 stdlib-only-at-runtime.
      - `fastjsonschema.compile()` exactly once per invocation (D-06-18, Pitfall 19).
      - On schema violation, format stderr via `_format_validation_error` —
        categorical-only (T-PII-01, Pitfall 17). Never `.message`, never `.value`.
      - On missing extra, print exact D-06-19 template — no traceback.
      - On schema-authoring bug (JsonSchemaDefinitionException), print categorical
        message — schema dict is repo-controlled (no PII risk).
    """
    try:
        # Lazy import: only loaded under --validate (D-06-17, Pitfall 18)
        import fastjsonschema
    except ImportError:
        print(
            "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'",
            file=sys.stderr,
        )
        return 1

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        # Categorical: schema file is repo-controlled.
        print(f"ERROR could not load schema {schema_path.name}: {type(err).__name__}", file=sys.stderr)
        return 1

    try:
        validator = fastjsonschema.compile(schema)
    except fastjsonschema.JsonSchemaDefinitionException as err:
        # Categorical: schema dict is repo-controlled — no row data.
        print(f"ERROR schema definition invalid: {err}", file=sys.stderr)
        return 1

    try:
        validator(rows)  # root is `array` → single call validates all rows
    except fastjsonschema.JsonSchemaValueException as err:
        print(_format_validation_error(err), file=sys.stderr)
        return 1

    return 0


def convert(
    path: Path,
    trailer: tuple[str, ...] | None,
    output: Path | None,
    quiz_title: str,
    validate: bool = False,
) -> int:
    """Phase 2 main path: CSV → list[dict] → JSON array on stdout or to file.

    Per RESEARCH "Per-Row Build Sequence":
      1. Open with utf-8-sig + newline=""
      2. Read header, classify_headers; on LayoutError → log + return 1
      3. Decode dynamic headers (D-14)
      4. For each data row: length check, decode cells, build_row, log warnings
      5. Dump results once (D-17: indent=2, ensure_ascii=False)

    Note: results accumulate in memory. T-RESOURCE-01 (accept-with-threshold):
    streaming/NDJSON output deferred to v2 if row count exceeds ~50k or per-row
    payload > ~5KB (>250MB total).
    """
    exit_code = 0
    results: list[dict] = []
    try:
        fh = path.open(encoding="utf-8-sig", newline="")
    except OSError as err:
        logging.error("cannot open CSV: %s", err)
        return 1
    with fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            logging.error("CSV is empty")
            return 1
        try:
            _prefix_h, dynamic_h, _trailer_h, scoring_index_map, missing_trio_names = classify_headers(
                header, trailer
            )
        except LayoutError as err:
            logging.error("%s", err)
            return 1

        # D-05-08 (locked template) / T-PII-01 / TRAIL-02:
        # Emit one PII-safe WARNING per missing canonical trio column.
        # %r yields single-quoted form (e.g. 'Result logic'); the values are
        # compile-time constants — NEVER row indices, NEVER cell content.
        for name in missing_trio_names:
            logging.warning(
                "trailer column %r absent from CSV header; emitting empty string for %s in all rows",
                name,
                _OUTPUT_KEY_BY_CANONICAL[name],
            )

        dynamic_headers_decoded = [decode_cell(h) for h in dynamic_h]
        expected_len = len(header)
        p_len = len(CONTACT_PREFIX)
        t_len = len(trailer if trailer is not None else DEFAULT_TRAILER)

        for idx, row in enumerate(reader, start=1):
            if len(row) != expected_len:
                logging.warning(
                    "row %d row length mismatch: expected %d fields, got %d",
                    idx,
                    expected_len,
                    len(row),
                )
                exit_code |= 1
                continue
            decoded = [decode_cell(c) for c in row]
            prefix_d = decoded[:p_len]
            dynamic_d = decoded[p_len : expected_len - t_len]
            trailer_d = decoded[expected_len - t_len :]
            row_dict, warnings_out = build_row(
                prefix_d, dynamic_d, trailer_d, dynamic_headers_decoded, quiz_title,
                scoring_index_map,
            )
            for w in warnings_out:
                # `w` is constructed in build_row from column names + categorical
                # values only — never cell content (T-PII-01).
                logging.warning("row %d %s", idx, w)
            results.append(row_dict)

    if validate:
        rc = _run_schema_validation(results, SCHEMA_PATH)
        if rc != 0:
            return rc

    if output is None:
        json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        with output.open("w", encoding="utf-8") as out_fh:
            json.dump(results, out_fh, indent=2, ensure_ascii=False)
            out_fh.write("\n")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="quizify_csv_ingest")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trailer-columns", default=None)
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Write JSON array to PATH (UTF-8). Default: stdout.")
    parser.add_argument(
        "--emit-json",
        action="store_true",
        help="Explicit JSON emission flag (default behavior; accepted for self-documenting scripts).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate emitted JSON against docs/webhook-schema.json (requires '[validate]' extra).",
    )
    parser.add_argument(
        "--quiz-title",
        default=None,
        help='Quiz title; falls back to $QUIZIFY_QUIZ_TITLE env var, then "". Decoded via html.unescape.',
    )
    args = parser.parse_args(argv)

    quiz_title = _resolve_quiz_title(args, os.environ)

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

    return convert(args.csv_path, trailer_override, args.output, quiz_title, validate=args.validate)


if __name__ == "__main__":
    raise SystemExit(main())
