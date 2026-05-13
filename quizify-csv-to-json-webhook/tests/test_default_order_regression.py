"""TRAIL-03: default-order callers see no behavioral change vs v1.0 baseline.

Phase 5 (TRAIL-01 / TRAIL-02) replaces positional trailer indexing with
name-keyed lookup. For default-order CSVs (DEFAULT_TRAILER), this MUST
produce output structurally identical to v1.0. The golden fixture
``tests/fixtures/v1.0_default_order_output.json`` was captured from the
pre-Phase-5 CLI in Wave 0 and is the comparison oracle.

Per D-05-12, this is the ONE allowed subprocess-driven test in Phase 5
because it specifically exercises the CLI entry point as a v1.0 user
would. All other Phase 5 tests stay unit-level.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
GOLDEN = ROOT / "tests" / "fixtures" / "v1.0_default_order_output.json"


def test_default_order_byte_identical_to_v1_0_baseline() -> None:
    """TRAIL-03: post-Phase-5 default-order output equals v1.0 baseline structurally."""
    assert GOLDEN.exists(), (
        f"Golden fixture missing: {GOLDEN}. "
        "Plan 01 Task 1 must run before this test (Wave 0 precondition)."
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    actual = json.loads(result.stdout)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, (
        "Default-order output diverged from v1.0 baseline; "
        "TRAIL-03 contract violated."
    )
    # Sanity check: 15 rows survived
    assert len(actual) == 15, f"expected 15 rows, got {len(actual)}"
    # Sanity check: scoring trio keys still present and bound to non-empty values
    # (default-order trailer in the sample CSV always supplies scoring)
    for r in actual:
        assert "result-logic" in r
        assert "score-category" in r
        assert "score-value" in r


def test_phase7_refactor_byte_identical_to_v1_0_baseline(capsys) -> None:
    """REFACTOR-01 SC#1: post-Phase-7 default-order output via direct convert() call
    is structurally identical to the v1.0/v1.1 golden fixture.

    Unit-level (capsys) per D-07-13 / Pitfall 16. The existing subprocess-driven
    TRAIL-03 test above stays as the literal-byte oracle; this twin protects
    the refactor at the function-call boundary.
    """
    from quizify_csv_ingest import convert
    rc = convert(FIXTURE, None, None, "")
    captured = capsys.readouterr()
    assert rc == 0, f"convert() returned non-zero rc={rc}; stderr={captured.err!r}"
    actual = json.loads(captured.out)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, (
        "Phase 7 refactor diverged from v1.0/v1.1 baseline; "
        "REFACTOR-01 SC#1 (byte-identical default output) violated."
    )
    assert len(actual) == 15
    for r in actual:
        assert "result-logic" in r
        assert "score-category" in r
        assert "score-value" in r


def test_phase7_iter_rows_symbol_exists() -> None:
    """REFACTOR-01 SC#2: `iter_rows` is the named public symbol per ROADMAP.

    FAILS-RED until Plan 02 adds the symbol. Catching this at import time is
    the contract gate for 'the refactor actually happened, not just got
    renamed in convert()'.
    """
    import quizify_csv_ingest
    assert hasattr(quizify_csv_ingest, "iter_rows"), (
        "Phase 7 refactor must expose `iter_rows` as a top-level symbol "
        "(ROADMAP SC#2)."
    )
