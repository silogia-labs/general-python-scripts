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
from typing import Iterator, Protocol

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


class _Sink(Protocol):
    def write(self, row: dict) -> None: ...
    def close(self) -> None: ...


class _StdoutSink:
    """Buffers rows; emits the JSON array on close() to preserve byte identity (D-07-02)."""
    def __init__(self) -> None:
        self._rows: list[dict] = []

    def write(self, row: dict) -> None:
        self._rows.append(row)

    def close(self) -> None:
        json.dump(self._rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class _FileSink:
    """Buffers rows; emits the JSON array on close() (D-07-03).
    Atomic os.replace deferred to Phase 8 STREAM-04 — Phase 7 keeps direct-open."""
    def __init__(self, output: Path) -> None:
        self._output = output
        self._rows: list[dict] = []

    def write(self, row: dict) -> None:
        self._rows.append(row)

    def close(self) -> None:
        with self._output.open("w", encoding="utf-8") as out_fh:
            json.dump(self._rows, out_fh, indent=2, ensure_ascii=False)
            out_fh.write("\n")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class _HttpPostSink:
    """Phase 7 STUB. Real HTTP POST lands in Phase 9 (AUTO-01..06).
    __init__ accepts the URL silently — NO validation in Phase 7 (D-07-04, D-07-12)."""
    def __init__(self, url: str) -> None:
        self.url = url

    def write(self, row: dict) -> None:
        raise NotImplementedError("HTTP POST delivery lands in Phase 9")

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class _NdjsonFileSink:
    """Phase 8 (STREAM-01..04 / D-08-02): atomic NDJSON file sink.

    Writes one ``json.dump(row) + '\\n'`` per row to a ``.tmp`` sibling; on
    successful exit ``os.replace`` promotes to the target (atomic on POSIX
    and Win32). On any exception (incl. KeyboardInterrupt), best-effort
    unlinks the .tmp and never promotes — STREAM-04 invariant.
    """
    def __init__(self, output: Path):
        self._target = output
        self._tmp = output.with_suffix(output.suffix + ".tmp")  # Pitfall 8-D — multi-suffix preserve
        self._fp = None

    def __enter__(self):
        self._fp = self._tmp.open("w", encoding="utf-8", newline="\n")
        return self

    def write(self, row: dict) -> None:
        json.dump(row, self._fp, ensure_ascii=False)
        self._fp.write("\n")

    def __exit__(self, exc_type, exc, tb):
        self._fp.close()
        if exc_type is None:
            os.replace(self._tmp, self._target)   # ONLY promotion path
        else:
            try:
                os.unlink(self._tmp)
            except OSError:
                pass
        return False  # never suppress

    def close(self) -> None:
        pass  # Protocol compliance; no-op when CM is used


class _RowValidationError(Exception):
    """D-08-06 sentinel: per-row validation failure carrying row index + PII-safe stderr line."""
    def __init__(self, row_index: int, pointer_message: str) -> None:
        self.row_index = row_index
        self.pointer_message = pointer_message
        super().__init__(pointer_message)


class _ValidatingSink:
    """D-08-05 decorator: per-row schema validation wrapping any inner _Sink.

    Lazy-imports fastjsonschema (D-13 / D-06-17 / Pitfall 18); compiles
    ``schema['items']`` exactly once (D-06-18 / D-08-08). On the first
    failure raises ``_RowValidationError`` — which propagates through the
    inner sink's ``__exit__`` (cleaning up its .tmp).
    """
    def __init__(self, inner: "_Sink", schema_path: Path):
        import fastjsonschema  # lazy, D-13 / D-06-17 / Pitfall 18
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self._validate_one = fastjsonschema.compile(schema["items"])  # D-06-18 / D-08-08
        self._inner = inner
        self._idx = 0

    def __enter__(self):
        self._inner.__enter__()
        return self

    def write(self, row: dict) -> None:
        try:
            self._validate_one(row)
        except Exception as exc:  # JsonSchemaValueException — Pitfall 17 categorical catch
            raise _RowValidationError(
                self._idx,
                _format_validation_error(exc, row_idx=self._idx),
            ) from None
        self._inner.write(row)
        self._idx += 1

    def __exit__(self, exc_type, exc, tb):
        return self._inner.__exit__(exc_type, exc, tb)

    def close(self) -> None:
        self._inner.close()


def _select_sink(output: Path | None, post_url: str | None) -> _Sink:
    """D-07-11: Argparse mutex guarantees output and post_url are not both set."""
    if post_url is not None:
        return _HttpPostSink(post_url)
    if output is not None:
        return _FileSink(output)
    return _StdoutSink()


# Module-private sentinel for empty-CSV signaling (RESEARCH Q5):
class _EmptyCsvError(Exception):
    """Raised by _RowStream.__iter__ when the CSV has no header row."""


class _RowStream:
    """Phase 7: streaming wrapper around the per-row build loop (D-07-05).

    Single-iteration only — re-iterating reopens the file and resets state.
    Caller materializes via list(stream); convert() reads stream.exit_code AFTER.
    """
    def __init__(
        self,
        path: Path,
        trailer: tuple[str, ...] | None,
        quiz_title: str,
    ) -> None:
        self.path = path
        self.trailer = trailer
        self.quiz_title = quiz_title
        self.exit_code = 0

    def __iter__(self) -> Iterator[dict]:
        # single-iteration; re-iterating reopens the file and resets state.
        # File-open OSError surfaces here — convert() catches it together
        # with LayoutError and _EmptyCsvError at the list(self) call site.
        with self.path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                raise _EmptyCsvError() from None

            # classify_headers raises LayoutError on bad header; let it propagate.
            _prefix_h, dynamic_h, _trailer_h, scoring_index_map, missing_trio_names = (
                classify_headers(header, self.trailer)
            )

            # D-05-08 (locked WARNING template, Phase 5 carry-forward):
            for name in missing_trio_names:
                logging.warning(
                    "trailer column %r absent from CSV header; emitting empty string for %s in all rows",
                    name,
                    _OUTPUT_KEY_BY_CANONICAL[name],
                )

            dynamic_headers_decoded = [decode_cell(h) for h in dynamic_h]
            expected_len = len(header)
            p_len = len(CONTACT_PREFIX)
            t_len = len(self.trailer if self.trailer is not None else DEFAULT_TRAILER)

            for idx, row in enumerate(reader, start=1):
                if len(row) != expected_len:
                    logging.warning(
                        "row %d row length mismatch: expected %d fields, got %d",
                        idx,
                        expected_len,
                        len(row),
                    )
                    self.exit_code |= 1
                    continue
                decoded = [decode_cell(c) for c in row]
                prefix_d = decoded[:p_len]
                dynamic_d = decoded[p_len : expected_len - t_len]
                trailer_d = decoded[expected_len - t_len :]
                row_dict, warnings_out = build_row(
                    prefix_d, dynamic_d, trailer_d, dynamic_headers_decoded,
                    self.quiz_title, scoring_index_map,
                )
                for w in warnings_out:
                    logging.warning("row %d %s", idx, w)
                yield row_dict


def iter_rows(
    path: Path,
    trailer: tuple[str, ...] | None,
    quiz_title: str,
) -> _RowStream:
    """ROADMAP SC#2 / D-07-06: public factory for the row-stream."""
    return _RowStream(path, trailer, quiz_title)


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


def _format_validation_error(err, row_idx: int | None = None) -> str:
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
    if row_idx is not None:
        # D-08-06 / RFC 6901: row-prefixed JSON Pointer for per-row mode.
        # Root-level error -> "/<idx>"; nested -> "/<idx>/<rest>".
        pointer = f"/{row_idx}" if pointer == "/" else f"/{row_idx}{pointer}"
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
    post_url: str | None = None,
) -> int:
    """Phase 7 refactor: iter_rows + sink dispatch. Default behavior unchanged."""
    stream = iter_rows(path, trailer, quiz_title)
    try:
        results = list(stream)
    except _EmptyCsvError:
        logging.error("CSV is empty")
        return 1
    except LayoutError as err:
        logging.error("%s", err)
        return 1
    except OSError as err:
        logging.error("cannot open CSV: %s", err)
        return 1
    exit_code = stream.exit_code

    if validate:
        rc = _run_schema_validation(results, SCHEMA_PATH)
        if rc != 0:
            return rc

    sink = _select_sink(output, post_url)
    try:
        for row in results:
            sink.write(row)
    finally:
        sink.close()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="quizify_csv_ingest")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trailer-columns", default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-o", "--output", type=Path, default=None,
                       help="Write JSON array to PATH (UTF-8). Default: stdout.")
    group.add_argument("--post-url", default=None,
                       help="(Phase 9) HTTP POST delivery target. Stub in Phase 7.")
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

    return convert(
        args.csv_path, trailer_override, args.output, quiz_title,
        validate=args.validate, post_url=args.post_url,
    )


if __name__ == "__main__":
    raise SystemExit(main())
