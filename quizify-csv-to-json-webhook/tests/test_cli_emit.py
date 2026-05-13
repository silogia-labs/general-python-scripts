"""Phase 2 CLI emission integration tests (Wave 2 — subprocess-based)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"


def test_default_invocation_emits_json_to_stdout() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 15
    first = payload[0]
    for k in (
        "firstName",
        "lastName",
        "email",
        "phone",
        "status",
        "statusDate",
        "tags",
    ):
        assert k in first
    for n in range(1, 21):
        assert f"question-{n}" in first
        assert f"answers-{n}" in first
        assert f"answers-tags-{n}" in first
    assert first["tags"][0] == "source: quizify"
    # HTML entities decoded uniformly
    assert "&gt;" not in result.stdout
    assert "&lt;" not in result.stdout
    # No "id" key anywhere in output
    assert '"id":' not in result.stdout


def test_output_flag_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "-o", str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 15
    # No JSON on stdout when writing to file
    assert result.stdout.strip() == ""


def test_long_output_flag_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "out2.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "--output", str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()


def test_dry_run_still_works() -> None:
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


def test_emit_json_flag_accepted() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "--emit-json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    json.loads(result.stdout)


def test_exit_code_2_on_invalid_trailer_columns() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "--trailer-columns", ""],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2


def test_exit_code_1_when_row_length_mismatch_skipped(tmp_path: Path) -> None:
    # Synthesize a CSV with one bad row.
    with FIXTURE.open(encoding="utf-8-sig") as f:
        good_header = f.readline().rstrip("\n")
    bad = tmp_path / "bad.csv"
    bad.write_text(good_header + "\n" + "only,three,fields\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "row length mismatch" in result.stderr.lower()
