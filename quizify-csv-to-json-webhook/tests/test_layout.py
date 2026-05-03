"""Tests for Quizify CSV header classification (Phase 1)."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from quizify_csv_ingest import CONTACT_PREFIX, DEFAULT_TRAILER, classify_headers

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
SCRIPT = ROOT / "quizify_csv_ingest.py"


def _read_header_row() -> list[str]:
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def test_sample_csv_header_classification() -> None:
    header = _read_header_row()
    prefix, dynamic, trailer = classify_headers(header)
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
    assert len(data_rows) == 42


def test_dry_run_stderr_row_count() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert "Rows (data): 42" in result.stderr
    assert "Questions (dynamic): 20" in result.stderr
    assert "Rango de edad" in result.stderr
    assert "@" not in result.stderr
