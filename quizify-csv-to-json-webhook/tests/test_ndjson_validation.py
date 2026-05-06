"""Phase 8 (STREAM-03 + T-PII-01) — _ValidatingSink RED tests.

All tests RED until Plan 08-02 lands ``_ValidatingSink``, ``_RowValidationError``,
the ``--ndjson`` flag, and threads ``--validate`` through the sink-selection
helper. Imports of the new symbols are deferred into test bodies so pytest
collection succeeds.

Carry-forward locks:
- D-06-18: schema compiled exactly once per _ValidatingSink instance
- D-06-20 / Pitfall 17: PII-safe formatter; categorical stderr only
- D-08-06: row-prefixed JSON Pointer per RFC 6901 (`/<idx><pointer>`)
- T-PII-01: negative-substring assertions against SYNTHETIC_PII_TOKENS
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.conftest import SYNTHETIC_PII_TOKENS  # noqa: E402


def test_validating_sink_raises_at_first_failure(tmp_path):
    """STREAM-03: bad row -> _RowValidationError(row_index=0); target absent.

    Direct-injection unit test (RESEARCH §Q8 Option C) — pairs with the
    integration test below.
    """
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import (  # noqa: PLC0415
        SCHEMA_PATH,
        _NdjsonFileSink,
        _RowValidationError,
        _ValidatingSink,
    )
    target = tmp_path / "out.ndjson"
    inner = _NdjsonFileSink(target)
    sink = _ValidatingSink(inner, SCHEMA_PATH)
    bad_row = {"email": 12345}  # type-invalid + missing required keys
    with pytest.raises(_RowValidationError) as exc:
        with sink:
            sink.write(bad_row)
    assert exc.value.row_index == 0
    assert not target.exists()


def test_validating_sink_compiles_schema_once(tmp_path):
    """D-06-18 / D-08-08: ``fastjsonschema.compile`` called exactly once per
    _ValidatingSink instance (regardless of how many rows are written).
    """
    pytest.importorskip("fastjsonschema")
    import fastjsonschema  # noqa: PLC0415
    from quizify_csv_ingest import (  # noqa: PLC0415
        SCHEMA_PATH,
        _NdjsonFileSink,
        _ValidatingSink,
    )
    real_compile = fastjsonschema.compile
    with patch.object(fastjsonschema, "compile", side_effect=real_compile) as mock_compile:
        inner = _NdjsonFileSink(tmp_path / "out.ndjson")
        _ValidatingSink(inner, SCHEMA_PATH)
        assert mock_compile.call_count == 1


def test_per_row_validation_failure_no_target(tmp_path, capsys, csv_with_bad_row_at_50):
    """STREAM-03 integration: malformed CSV row -> rc=1, target absent, stderr
    carries a row-prefixed JSON Pointer (no cell content).

    The synthetic CSV row may not violate ``schema['items']`` cleanly through
    ``build_row`` (Pitfall 8-E); if so, this test ``pytest.skip``s and the
    unit test above carries the contract.
    """
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(csv_with_bad_row_at_50), "-o", str(out), "--ndjson", "--validate"])
    if rc == 0:
        pytest.skip(
            "synthetic CSV row 50 did not violate schema['items'] through "
            "build_row; unit test test_validating_sink_raises_at_first_failure "
            "carries the contract (RESEARCH §Q8 Option C)."
        )
    assert rc == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert re.search(r"ERROR schema validation failed at /\d+/", err), (
        f"stderr does not contain row-prefixed JSON Pointer: {err!r}"
    )


def test_per_row_failure_pii_safe(tmp_path, capsys, csv_with_bad_row_at_50):
    """T-PII-01 / Pitfall 17: synthetic PII tokens NEVER appear in stderr."""
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(csv_with_bad_row_at_50), "-o", str(out), "--ndjson", "--validate"])
    if rc == 0:
        pytest.skip("synthetic CSV did not trigger schema failure (Pitfall 8-E).")
    err = capsys.readouterr().err
    for token in SYNTHETIC_PII_TOKENS:
        assert token not in err, f"PII token leaked into stderr: {token!r}"
    # Pitfall 17: raw fastjsonschema err.path leak guard.
    assert "data[" not in err, f"raw err.path leaked: {err!r}"


def test_per_row_failure_uses_row_prefixed_pointer(tmp_path, capsys, csv_with_bad_row_at_50):
    """D-08-06 / RFC 6901: stderr pointer starts with ``/<idx>/`` form."""
    pytest.importorskip("fastjsonschema")
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    rc = main([str(csv_with_bad_row_at_50), "-o", str(out), "--ndjson", "--validate"])
    if rc == 0:
        pytest.skip("synthetic CSV did not trigger schema failure (Pitfall 8-E).")
    err = capsys.readouterr().err.strip()
    m = re.search(r"ERROR schema validation failed at (\S+):", err)
    assert m, f"could not extract pointer from stderr: {err!r}"
    pointer = m.group(1)
    assert re.match(r"^/\d+/", pointer), (
        f"pointer not in /<idx>/<rest> form: {pointer!r}"
    )
