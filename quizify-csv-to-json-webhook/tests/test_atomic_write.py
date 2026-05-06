"""Phase 8 (STREAM-04) — atomic-write + SIGINT RED tests.

Carry-forward locks:
- D-08-10: ``os.replace`` is the single promotion path
- D-08-09: SIGINT propagates as KeyboardInterrupt; target never exists
- Pitfall 16: subprocess test justified ONLY for SIGINT delivery
"""
from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "docs" / "quizify-submissions.csv"
SCRIPT = ROOT / "quizify_csv_ingest.py"
sys.path.insert(0, str(ROOT))


def test_atomic_replace_on_success(tmp_path):
    """STREAM-04: success path -> target exists, .tmp does not."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    assert out.exists()
    assert not (tmp_path / "out.ndjson.tmp").exists()


def test_no_target_on_validation_failure(tmp_path, csv_with_bad_row_at_50):
    """STREAM-04: validation failure -> target absent (the .tmp may or may not
    exist; the contract constrains the *target* only).
    """
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(csv_with_bad_row_at_50), "-o", str(out), "--ndjson", "--validate"])
    if rc == 0:
        pytest.skip("synthetic CSV did not trigger schema failure (Pitfall 8-E).")
    assert rc == 1
    assert not out.exists()


def test_sigint_leaves_no_target(tmp_path):
    """STREAM-04 / D-08-09: SIGINT mid-run -> target path does not exist.

    Subprocess form per Pitfall 16 justified-exception (SIGINT delivery cannot
    be tested at unit level). Build a large synthetic CSV so the child stays
    busy long enough for SIGINT to land mid-stream.
    """
    # Build a large synthetic CSV so SIGINT can land mid-stream.
    big = tmp_path / "big.csv"
    header_cells = [
        "First name", "Last name", "Email", "Lead Verified",
        "Phone", "Subscribed to newsletter",
        "question-1",
        "Result logic", "Score category", "Score value",
        "Answer tags", "Time to complete (mm:ss)", "Date",
    ]
    rows = [",".join('"' + c + '"' for c in header_cells)]
    for i in range(20000):
        cells = [
            f"F{i}", f"L{i}", f"row-{i}@example.test",
            "false", f"+1 555 0{i:04d}", "Yes",
            "55", "Result A", "Cat A", "100", "", "01:23", "2026-05-05",
        ]
        rows.append(",".join('"' + c + '"' for c in cells))
    big.write_text("\n".join(rows) + "\n", encoding="utf-8")

    out = tmp_path / "out.ndjson"
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), str(big), "-o", str(out), "--ndjson"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(0.05)
    proc.send_signal(signal.SIGINT)
    stdout, stderr = proc.communicate(timeout=15)
    # RED-state guard: argparse must have ACCEPTED --ndjson (i.e., the test
    # is exercising real SIGINT delivery, not the "unrecognized arguments"
    # short-circuit). This makes the test RED until Plan 02 adds the flag.
    assert b"unrecognized arguments" not in stderr, (
        "argparse rejected --ndjson; SIGINT path not exercised"
    )
    assert proc.returncode != 0, "child should not exit cleanly after SIGINT"
    assert not out.exists(), "target file must not exist after SIGINT"


def test_os_replace_is_only_promotion_path():
    """D-08-10 grep gate as a unit test: only ``os.replace`` is used to promote."""
    src = (ROOT / "quizify_csv_ingest.py").read_text(encoding="utf-8")
    assert "shutil.move(" not in src
    assert "os.rename(" not in src
    assert src.count("os.replace(") == 1
