#!/usr/bin/env python3
"""Quizify CSV layout scanner — Phase 1 (classification + dry-run preview)."""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
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
) -> tuple[list[str], list[str], list[str]]:
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
    return prefix_raw, dynamic, trailer_raw


TAG_HEADER_MAP = {
    "red_flag": "signos de alarma",
    "goal_": "objetivo",
    "consent": "consiento",
}


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
    }
    for i, header in enumerate(dynamic_headers_decoded):
        n = i + 1
        cell = dynamic_cells_decoded[i] if i < len(dynamic_cells_decoded) else ""
        row[f"question-{n}"] = header
        row[f"answers-{n}"] = shape_answer(cell)
        row[f"answers-tags-{n}"] = ", ".join(matched_buckets.get(i, []))
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
            _prefix, dynamic, _trailer_h = classify_headers(header, trailer)
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


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="quizify_csv_ingest")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trailer-columns", default=None)
    args = parser.parse_args(argv)

    trailer_override: tuple[str, ...] | None = None
    if args.trailer_columns is not None:
        try:
            trailer_override = parse_trailer_arg(args.trailer_columns)
        except ValueError:
            print("ERROR invalid trailer-columns", file=sys.stderr)
            return 2

    configure_logging(args.verbose)

    if not args.dry_run:
        print(
            "Phase 1: use --dry-run to classify headers (JSON conversion is Phase 2).",
            file=sys.stderr,
        )
        return 2

    return dry_run(args.csv_path, trailer_override)


if __name__ == "__main__":
    raise SystemExit(main())
