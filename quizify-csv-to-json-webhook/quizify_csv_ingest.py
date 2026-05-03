#!/usr/bin/env python3
"""Quizify CSV layout scanner — Phase 1 (classification + dry-run preview)."""

from __future__ import annotations

import argparse
import csv
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
