"""Phase 8 (STREAM-01..02 + Pitfall 8-D) — NDJSON file output RED tests.

All tests in this module are RED until Plan 08-02 lands ``_NdjsonFileSink``
and the ``--ndjson`` argparse flag in ``quizify_csv_ingest.py``. Imports of
``_NdjsonFileSink`` are deferred into test bodies so pytest collection
succeeds and per-test RED is reported (rather than a collection-time error).

Carry-forward locks exercised here:
- D-05 tail-key order (jq-array structural equivalence to v1.1 golden)
- STREAM-01 line count == row count
- STREAM-02 ``\\n``-only output, no ``\\r``
- Pitfall 8-D ``.tmp`` naming preserves the multi-suffix form
- D-08-02 ``__exit__`` cleanup on exception (incl. KeyboardInterrupt)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "docs" / "quizify-submissions.csv"
GOLDEN = ROOT / "tests" / "fixtures" / "v1.0_default_order_output.json"
SCRIPT = ROOT / "quizify_csv_ingest.py"
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# STREAM-01 happy path + STREAM-02 byte-level invariants
# ---------------------------------------------------------------------------

def test_ndjson_happy_path(tmp_path):
    """STREAM-01: --ndjson produces N JSON-Lines for N CSV rows; each line
    round-trips via ``json.loads``.
    """
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 15, f"expected 15 NDJSON lines, got {len(lines)}"
    for line in lines:
        d = json.loads(line)
        assert isinstance(d, dict)


def test_no_carriage_returns(tmp_path):
    """STREAM-02: produced bytes contain no ``\\r`` (CRLF translation defeated)."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    assert b"\r" not in out.read_bytes()


def test_line_count_and_separator(tmp_path):
    """STREAM-01: exactly N ``\\n`` bytes for N rows; no extra trailing newline."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    raw = out.read_bytes()
    nl = raw.count(b"\n")
    assert nl == 15, f"expected 15 newline bytes, got {nl}"
    # Last byte should be a newline; no double-trailing-newline.
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_jq_equivalent_to_array(tmp_path):
    """STREAM-01: NDJSON lines reassemble structurally to the v1.1 golden array
    (D-05 tail-key order preserved by build_row across both modes).
    """
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson"])
    assert rc == 0
    actual = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, "NDJSON reassembled array diverges from v1.1 golden"


# ---------------------------------------------------------------------------
# Pitfall 8-D regression + __exit__ cleanup (D-08-02)
# ---------------------------------------------------------------------------

def test_tmp_path_preserves_suffix():
    """Pitfall 8-D: ``out.ndjson`` -> ``out.ndjson.tmp`` (NOT ``out.tmp``).

    The literal expectation locks the ``with_suffix(suffix + '.tmp')`` form
    against future drift to ``with_suffix('.tmp')``.
    """
    from quizify_csv_ingest import _NdjsonFileSink  # noqa: PLC0415
    sink = _NdjsonFileSink(Path("out.ndjson"))
    assert sink._tmp.name == "out.ndjson.tmp"


def test_exit_unlinks_tmp_on_exception(tmp_path):
    """D-08-02: ``__exit__`` on generic exception unlinks the .tmp and never
    promotes to target.
    """
    from quizify_csv_ingest import _NdjsonFileSink  # noqa: PLC0415
    target = tmp_path / "out.ndjson"
    sink = _NdjsonFileSink(target)
    with pytest.raises(RuntimeError):
        with sink:
            sink.write({"a": 1})
            raise RuntimeError("boom")
    assert not target.exists()
    assert not (tmp_path / "out.ndjson.tmp").exists()


def test_keyboard_interrupt_cleanup(tmp_path):
    """D-08-09: KeyboardInterrupt propagates through __exit__; target absent,
    .tmp cleaned. Unit-level proxy for the SIGINT subprocess test (Pitfall 16).
    """
    from quizify_csv_ingest import _NdjsonFileSink  # noqa: PLC0415
    target = tmp_path / "out.ndjson"
    sink = _NdjsonFileSink(target)
    with pytest.raises(KeyboardInterrupt):
        with sink:
            sink.write({"a": 1})
            raise KeyboardInterrupt()
    assert not target.exists()
    assert not (tmp_path / "out.ndjson.tmp").exists()
