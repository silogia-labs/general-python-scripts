"""Phase 8 (STREAM-01 + T-PII-01) — argparse rejection RED tests for --ndjson.

D-08-11: ``--ndjson`` lives outside the existing -o/--post-url mutex group;
two post-parse ``parser.error()`` checks reject:
  1. ``--ndjson`` + ``--post-url`` (categorical message, exit 2)
  2. ``--ndjson`` without ``-o`` (categorical message, exit 2)

D-08-13: ``--ndjson --validate -o ...`` is an accepted combination.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "docs" / "quizify-submissions.csv"
sys.path.insert(0, str(ROOT))

from tests.conftest import SYNTHETIC_PII_TOKENS  # noqa: E402


def test_ndjson_rejects_post_url(capsys):
    """D-08-11(a): ``--ndjson`` + ``--post-url`` -> SystemExit(2), categorical msg."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--ndjson", "--post-url", "https://x", "in.csv"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--ndjson cannot be combined with --post-url" in err


def test_ndjson_requires_output(capsys):
    """D-08-11(b): ``--ndjson`` without ``-o`` -> SystemExit(2), categorical msg."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--ndjson", "in.csv"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--ndjson requires -o/--output" in err


def test_argparse_rejection_pii_safe(capsys):
    """T-PII-01: argparse rejection messages never echo synthetic PII tokens.

    Categorical messages structurally satisfy this; the assertion locks the
    contract against future verbose-error drift.
    """
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit):
        main(["--ndjson", "--post-url", "https://x", "in.csv"])
    err = capsys.readouterr().err
    # Lock the categorical message contract (RED until Plan 02 adds it).
    assert "--ndjson cannot be combined with --post-url" in err
    for token in SYNTHETIC_PII_TOKENS:
        assert token not in err

    with pytest.raises(SystemExit):
        main(["--ndjson", "in.csv"])
    err = capsys.readouterr().err
    assert "--ndjson requires -o/--output" in err
    for token in SYNTHETIC_PII_TOKENS:
        assert token not in err


def test_ndjson_validate_combination_accepted(tmp_path):
    """D-08-13: ``--ndjson --validate -o out.ndjson`` does not exit at argparse.

    Will currently FAIL because Plan 02 has not added the flag — that is the
    intended RED signal for this scaffolding plan.
    """
    from quizify_csv_ingest import main  # noqa: PLC0415
    out = tmp_path / "out.ndjson"
    # Should not raise SystemExit at argparse layer (rc may be 0 or 1 depending
    # on whether the sample CSV passes schema; the contract here is "argparse
    # accepts the combination").
    try:
        rc = main([str(SAMPLE_CSV), "-o", str(out), "--ndjson", "--validate"])
    except SystemExit as e:
        # argparse rejection codes are 2; anything else is acceptable here.
        assert e.code != 2, f"argparse rejected --ndjson --validate combo: {e.code}"
        rc = e.code
    assert rc in (0, 1)
