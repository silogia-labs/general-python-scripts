"""Tests for Quizify CSV header classification (Phase 1)."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from quizify_csv_ingest import (
    CONTACT_PREFIX,
    DEFAULT_TRAILER,
    LayoutError,
    classify_headers,
    parse_trailer_arg,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
SCRIPT = ROOT / "quizify_csv_ingest.py"


def _read_header_row() -> list[str]:
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, skipinitialspace=True)
        return [h.rstrip() for h in next(reader)]


def test_sample_csv_header_classification() -> None:
    header = _read_header_row()
    prefix, dynamic, trailer, scoring_index_map, missing_trio_names = classify_headers(header)
    assert scoring_index_map == {"Result logic": 0, "Score category": 1, "Score value": 2}
    assert missing_trio_names == ()
    assert len(prefix) == len(CONTACT_PREFIX)
    assert prefix[0] == "First name"
    assert len(dynamic) == 20
    assert dynamic[0] == "Rango de edad"
    assert len(trailer) == len(DEFAULT_TRAILER)
    assert trailer[0] == "Result logic"


def test_data_row_count_matches_fixture() -> None:
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        data_rows = list(reader)
    assert len(data_rows) == 15


TRAILER_CLI = (
    "Result logic,Score category,Score value,Answer tags,"
    "Time to complete (mm:ss),Date"
)


def test_parse_trailer_arg_roundtrip() -> None:
    parts = parse_trailer_arg(TRAILER_CLI)
    assert parts == DEFAULT_TRAILER


def test_parse_trailer_arg_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_trailer_arg("")


def test_dry_run_with_trailer_columns_override() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            str(FIXTURE),
            "--trailer-columns",
            TRAILER_CLI,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert "Questions (dynamic): 20" in result.stderr


def test_invalid_trailer_columns_exit_code() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            str(FIXTURE),
            "--trailer-columns",
            "",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2
    assert "trailer-columns" in result.stderr.lower()


def test_dry_run_stderr_row_count() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert "Rows (data): 15" in result.stderr
    assert "Questions (dynamic): 20" in result.stderr
    assert "Rango de edad" in result.stderr
    assert "@" not in result.stderr


class TestScoringIndexMap:
    """TRAIL-01: classify_headers builds a name-keyed scoring index map.

    Verifies D-05-01 (5-tuple return), D-05-03 (NFC+casefold via _norm_for_match),
    D-05-02 (strict positional shape check still raises LayoutError).
    """

    def test_default_order_index_map(self) -> None:
        header = _read_header_row()
        _, _, _, scoring_index_map, missing_trio_names = classify_headers(header)
        assert scoring_index_map == {"Result logic": 0, "Score category": 1, "Score value": 2}
        assert missing_trio_names == ()

    def test_scrambled_order_maps_by_name(self) -> None:
        # Custom trailer reorders the trio: Score value first, then Result logic, then Score category
        custom_trailer = (
            "Score value", "Result logic", "Score category",
            "Answer tags", "Time to complete (mm:ss)", "Date",
        )
        header = list(CONTACT_PREFIX) + ["q1", "q2"] + list(custom_trailer)
        _, _, _, scoring_index_map, missing_trio_names = classify_headers(header, custom_trailer)
        # Named lookup, NOT positional: "Score value" is at trailer index 0, etc.
        assert scoring_index_map == {"Score value": 0, "Result logic": 1, "Score category": 2}
        assert missing_trio_names == ()

    def test_normalization_handles_case_and_diacritics(self) -> None:
        # Header has uppercase / case-variant trio names — should match canonical via NFC+casefold
        custom_trailer = (
            "RESULT LOGIC", "Score Category", "score value",
            "Answer tags", "Time to complete (mm:ss)", "Date",
        )
        header = list(CONTACT_PREFIX) + ["q1"] + list(custom_trailer)
        _, _, trailer_raw, scoring_index_map, missing_trio_names = classify_headers(
            header, custom_trailer
        )
        # All three trio canonicals matched (case-insensitively) — none missing
        assert missing_trio_names == ()
        assert set(scoring_index_map.keys()) == {"Result logic", "Score category", "Score value"}

    def test_missing_column_listed(self) -> None:
        # Trailer omits "Result logic"; replace it with non-trio columns
        custom_trailer = (
            "Score category", "Score value", "Answer tags",
            "Time to complete (mm:ss)", "Date",
        )
        header = list(CONTACT_PREFIX) + ["q1"] + list(custom_trailer)
        _, _, _, scoring_index_map, missing_trio_names = classify_headers(header, custom_trailer)
        # "Result logic" is in the missing list (canonical display form)
        assert "Result logic" in missing_trio_names
        # The other two trio canonicals ARE in the map at their correct positions
        assert scoring_index_map.get("Score category") == 0
        assert scoring_index_map.get("Score value") == 1
        # "Result logic" is NOT in the map
        assert "Result logic" not in scoring_index_map

    def test_strict_positional_still_raises_on_length_mismatch(self) -> None:
        # D-05-02 carry-forward: shape mismatch still raises LayoutError.
        short_header = list(CONTACT_PREFIX) + ["q1", "q2"] + ["Result logic", "Score category"]
        # Default trailer is 6 cols; header trailer slice would only be 2 → LayoutError
        with pytest.raises(LayoutError):
            classify_headers(short_header)
