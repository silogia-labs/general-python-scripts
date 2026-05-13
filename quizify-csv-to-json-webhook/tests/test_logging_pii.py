"""Phase 2 stderr WARNING content asserts no PII leakage (T-PII-01)."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"


def _read_header() -> list[str]:
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        return [h.rstrip() for h in next(csv.reader(f, skipinitialspace=True))]


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _good_dynamic(k: int) -> list[str]:
    return [""] * k


def test_warning_for_unexpected_status_does_not_contain_email(tmp_path: Path) -> None:
    header = _read_header()
    k = len(header) - 11  # contact(5) + trailer(6)
    leak_email = "leak@example.com"
    leak_phone = "+52 55 9999 9999"
    bad_status = "Maybe"
    row = (
        ["Leakage", "Person", leak_email, leak_phone, bad_status]
        + _good_dynamic(k)
        + ["", "", "", "", "00:10", "2026-01-01"]
    )
    csv_path = tmp_path / "status.csv"
    _write_csv(csv_path, header, [row])

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    # Diagnostic was emitted
    assert "unexpected status value" in result.stderr.lower()
    # PII tokens absent from stderr
    assert leak_email not in result.stderr
    assert leak_phone not in result.stderr
    assert "Leakage" not in result.stderr


def test_warning_for_unmatched_tag_does_not_contain_free_text_answer(
    tmp_path: Path,
) -> None:
    header = _read_header()
    k = len(header) - 11
    secret_answer = "SECRET_FREE_TEXT_ANSWER_PII"
    leak_email = "tagleak@example.com"
    dyn = _good_dynamic(k)
    # Place secret in a free-text-shaped cell; tag must miss all patterns
    if k > 6:
        dyn[6] = secret_answer
    row = (
        ["TagTest", "User", leak_email, "+52 55 0000 7777", "Yes"]
        + dyn
        + ["", "", "", "totally_unknown_tag", "00:10", "2026-01-01"]
    )
    csv_path = tmp_path / "tag.csv"
    _write_csv(csv_path, header, [row])

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    # Tag token (categorical) IS allowed in stderr
    assert "totally_unknown_tag" in result.stderr
    # Free-text answer cell and contact PII are NOT in stderr
    assert secret_answer not in result.stderr
    assert leak_email not in result.stderr


def test_warning_for_row_length_mismatch_does_not_contain_cell_values(
    tmp_path: Path,
) -> None:
    header = _read_header()
    leak_email = "ohno@example.com"
    bad = tmp_path / "bad.csv"
    # Bad row has only 4 fields; one of them is a contact email
    with bad.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["Bad", "Row", leak_email, "+52 55 0000 0000"])

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "row length mismatch" in result.stderr.lower()
    assert leak_email not in result.stderr
    assert "+52 55 0000 0000" not in result.stderr
