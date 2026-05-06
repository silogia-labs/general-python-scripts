# Plan 09-01 RED scaffolding — these tests fail until 09-02 ships impl.
"""Phase 9 (AUTO-02..05) — pure-unit argparse rejection tests for --post-url
HTTPS gate, --validate dependency, --header validation, --timeout validation.

No socket touched. Mirrors test_argparse_ndjson.py shape.
Locked reason vocabulary (D-09-08): post_url_https_required,
post_url_requires_validate, header_crlf_rejected, header_missing_colon,
header_empty_name, header_invalid_name, timeout_invalid.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLE_CSV = str(ROOT / "docs" / "quizify-submissions.csv")


# ---- Phase 7 carry-forward: existing mutex stays in place ------------------

def test_post_url_output_mutex(capsys):
    """Phase 7 carry-forward: --post-url and -o are mutually exclusive."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--post-url", "https://x.test", "-o", "out.json", SAMPLE_CSV])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not allowed with" in err or "mutually exclusive" in err.lower()


# ---- AUTO-02 / AUTO-05: HTTPS-only + --validate dependency ------------------

def test_post_url_requires_validate(capsys):
    """AUTO-05: --post-url without --validate -> SystemExit(2), categorical."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--post-url", "https://x.test", SAMPLE_CSV])
    assert exc.value.code == 2
    assert "post_url_requires_validate" in capsys.readouterr().err


def test_http_rejected(capsys):
    """AUTO-02: http:// scheme rejected by argparse type=_https_url."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--post-url", "http://x.test", "--validate", SAMPLE_CSV])
    assert exc.value.code == 2
    assert "post_url_https_required" in capsys.readouterr().err


def test_https_no_netloc_rejected(capsys):
    """AUTO-02: https:// with empty netloc rejected."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--post-url", "https://", "--validate", SAMPLE_CSV])
    assert exc.value.code == 2
    assert "post_url_https_required" in capsys.readouterr().err


# ---- AUTO-03: --header parsing -------------------------------------------------

def test_header_crlf_rejected(capsys):
    """AUTO-03: CRLF in header value rejected (header injection mitigation)."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--header", "X-Foo: bar\r\nX-Inject: bad",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "header_crlf_rejected" in capsys.readouterr().err


def test_header_missing_colon(capsys):
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--header", "X-Foo bar",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "header_missing_colon" in capsys.readouterr().err


def test_header_empty_name(capsys):
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--header", ": value",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "header_empty_name" in capsys.readouterr().err


def test_header_invalid_name(capsys):
    """RFC 7230 token charset: space in field name is invalid."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--header", "X Foo: bar",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "header_invalid_name" in capsys.readouterr().err


# ---- AUTO-04: --timeout validation -------------------------------------------

def test_timeout_invalid_zero(capsys):
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--timeout", "0",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "timeout_invalid" in capsys.readouterr().err


def test_timeout_invalid_negative(capsys):
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main([
            "--post-url", "https://x.test", "--validate",
            "--timeout", "-1",
            SAMPLE_CSV,
        ])
    assert exc.value.code == 2
    assert "timeout_invalid" in capsys.readouterr().err


def test_timeout_default_30():
    """Default --timeout is 30.0 seconds (parsed namespace, no socket)."""
    from quizify_csv_ingest import _build_parser  # noqa: PLC0415
    parser = _build_parser()
    args = parser.parse_args([
        "--post-url", "https://x.test", "--validate", SAMPLE_CSV,
    ])
    assert args.timeout == 30.0
