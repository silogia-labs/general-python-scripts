"""Quick task 260512-uzh — coverage for the new INFO logs and the
``--dry-run`` HTTP overload (no network I/O when combined with ``--post-url``).

Three behavioural truths from the plan's must_haves are exercised here:

  A. ``--dry-run`` + ``--post-url`` performs zero HTTP egress and exits 0.
  B. The same invocation emits the new ``http_request ... dry_run=true``
     INFO line on stderr (visible because ``-v`` is passed).
  C. A normal ``-v`` conversion emits at least one ``row_built row=`` INFO
     line per yielded row.

Test A intentionally targets a syntactically-valid HTTPS URL pointing at the
``mock_webhook`` loopback port. The ``_https_url`` argparse type accepts it
(scheme is ``https``); the dry-run short-circuit then prevents any actual
``urlopen`` call, so the mock server records zero requests. This proves the
short-circuit is upstream of the socket layer (the TLS handshake against a
plain-HTTP server would otherwise raise — its absence IS the assertion).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.conftest import _respond_200  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_logging():
    """Reset root logger after each test.

    main() -> configure_logging() calls logging.basicConfig(force=True,
    stream=sys.stderr), which captures pytest's per-test capsys buffer. When
    the test ends and that buffer is torn down, subsequent tests in this
    session inherit a stale stream handle and emit '--- Logging error ---'
    tracebacks (which can re-include captured response bodies and trip the
    PII gate in test_http_post_pii.py). Tearing the handlers down here keeps
    each test isolated.
    """
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    root.setLevel(logging.WARNING)


def _https_url_for(server) -> str:
    """Wrap a mock_webhook server's port in an https:// URL string.

    The URL passes ``_https_url`` validation but is never actually contacted
    when ``--dry-run`` is in effect (that's the invariant under test).
    """
    port = server.server_address[1]
    return f"https://127.0.0.1:{port}"


def test_dry_run_post_url_zero_network(mock_webhook, sample_csv_path, capsys):
    """Test A: --dry-run + --post-url performs zero HTTP egress and exits 0."""
    from quizify_csv_ingest import main  # noqa: PLC0415

    _url, received, server = mock_webhook(_respond_200)
    https_url = _https_url_for(server)

    rc = main([
        "--post-url", https_url,
        "--validate",
        "--dry-run",
        "-v",
        str(sample_csv_path),
    ])
    capsys.readouterr()  # drain
    assert rc == 0, f"expected exit 0 from dry-run, got {rc}"
    assert len(received) == 0, (
        f"expected zero network requests in dry-run, got {len(received)}"
    )


def test_dry_run_post_url_emits_http_request_log(
    mock_webhook, sample_csv_path, capsys,
):
    """Test B: dry-run + post-url emits the http_request INFO line on stderr.

    configure_logging() uses ``logging.basicConfig(..., force=True, stream=sys.stderr)``
    which detaches pytest's caplog handler — capturing the real stderr stream
    via capsys is the right tool here (mirrors how the existing dry_run()
    layout-summary tests assert on stderr text).
    """
    from quizify_csv_ingest import main  # noqa: PLC0415

    _url, received, server = mock_webhook(_respond_200)
    https_url = _https_url_for(server)

    rc = main([
        "--post-url", https_url,
        "--validate",
        "--dry-run",
        "-v",
        str(sample_csv_path),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert len(received) == 0

    err = captured.err
    # Match: "http_request method=POST url=https://... rows=N bytes=N dry_run=true"
    assert "http_request method=POST" in err, (
        f"missing http_request INFO line in stderr:\n{err[-1000:]}"
    )
    assert "url=https://" in err
    assert "dry_run=true" in err


def test_row_built_log_emitted_under_verbose(
    sample_csv_path, tmp_path, capsys,
):
    """Test C: a normal -v conversion emits row_built INFO lines per row."""
    from quizify_csv_ingest import main  # noqa: PLC0415

    out = tmp_path / "out.json"
    rc = main([
        "-v",
        "-o", str(out),
        str(sample_csv_path),
    ])
    captured = capsys.readouterr()
    assert rc == 0, f"expected exit 0 from normal conversion, got {rc}"
    assert out.exists() and out.stat().st_size > 0

    err = captured.err
    assert "row_built row=" in err, (
        f"missing row_built INFO line in stderr:\n{err[:400]}"
    )
    # At least the first row is indexed 1.
    assert "row_built row=1" in err
