# Plan 09-01 RED scaffolding — these tests fail until 09-02 ships impl.
"""Phase 9 (T-PII-01) — TestHTTPErrorPIIsafe negative-substring suite.

For every locked HTTP-failure reason in D-09-08, assert that NEITHER
caplog.text NOR captured stderr contain ANY of the synthetic PII markers
(row tokens) NOR the mock-server response markers (server body, redirect
target, loopback IP). Locks the categorical-only stderr contract from
multiple angles.

Reasons under test:
  network-side (mock-injected URLError): tls_error, dns_error,
    connection_refused, network_error
  server-side (real loopback): http_unexpected_redirect, http_client_error,
    http_server_error, network_timeout
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.conftest import (  # noqa: E402
    _respond_302, _respond_502, _respond_hang,
)


# Synthetic PII markers — placed in row payload that gets POSTed.
_MARKER_EMAIL = "marker_email_50@example.test"
_MARKER_PHONE = "+15555550042"
_MARKER_FREETEXT = "marker_freetext_xyzzy"

# Server-side response markers — must NEVER appear in stderr/log.
_FORBIDDEN_TOKENS = (
    _MARKER_EMAIL,
    _MARKER_PHONE,
    _MARKER_FREETEXT,
    "server_response_marker",
    "Bad Gateway",
    "other.example.test",
    "127.0.0.1",
)


def _respond_404_with_marker(handler):
    body = b"server_response_marker"
    handler.send_response(404)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _row_with_pii():
    return {
        "email": _MARKER_EMAIL,
        "phone": _MARKER_PHONE,
        "freetext": _MARKER_FREETEXT,
    }


def _assert_pii_safe(caplog_text: str, stderr: str):
    combined = caplog_text + "\n" + stderr
    leaked = [t for t in _FORBIDDEN_TOKENS if t in combined]
    assert not leaked, f"PII / response markers leaked into stderr/log: {leaked}"


class TestHTTPErrorPIIsafe:
    """Server-side failures via real loopback http.server (4 high-risk reasons)."""

    def test_redirect_pii_safe(self, mock_webhook, caplog, capsys):
        from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
        caplog.set_level(logging.ERROR)
        url, _received, _ = mock_webhook(_respond_302)
        with pytest.raises(SystemExit):
            with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
                sink.write(_row_with_pii())
        _assert_pii_safe(caplog.text, capsys.readouterr().err)

    def test_client_error_pii_safe(self, mock_webhook, caplog, capsys):
        from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
        caplog.set_level(logging.ERROR)
        url, _received, _ = mock_webhook(_respond_404_with_marker)
        with pytest.raises(SystemExit):
            with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
                sink.write(_row_with_pii())
        _assert_pii_safe(caplog.text, capsys.readouterr().err)

    def test_server_error_pii_safe(self, mock_webhook, caplog, capsys):
        from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
        caplog.set_level(logging.ERROR)
        url, _received, _ = mock_webhook(_respond_502)
        with pytest.raises(SystemExit):
            with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
                sink.write(_row_with_pii())
        _assert_pii_safe(caplog.text, capsys.readouterr().err)

    def test_timeout_pii_safe(self, mock_webhook, caplog, capsys):
        from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
        caplog.set_level(logging.ERROR)
        url, _received, _ = mock_webhook(_respond_hang)
        with pytest.raises(SystemExit):
            with _HttpPostSink(url, headers=[], timeout=0.5) as sink:
                sink.write(_row_with_pii())
        _assert_pii_safe(caplog.text, capsys.readouterr().err)


# ----- Network-side failures via injected URLError --------------------------
# Parametrized over the remaining 4 reasons. Mocks self._opener.open to raise
# the canonical exception that should map to each reason.

import socket
import ssl
import urllib.error


@pytest.mark.parametrize("reason_label,exc_factory", [
    ("tls_error", lambda: urllib.error.URLError(ssl.SSLError("synthetic_tls"))),
    ("dns_error", lambda: urllib.error.URLError(socket.gaierror(-2, "synthetic_dns"))),
    ("connection_refused", lambda: urllib.error.URLError(
        ConnectionRefusedError("synthetic_refused")
    )),
    ("network_error", lambda: urllib.error.URLError("synthetic_generic")),
])
def test_network_side_failure_pii_safe(reason_label, exc_factory, caplog, capsys):
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    caplog.set_level(logging.ERROR)
    with mock.patch.object(
        _HttpPostSink, "_post_once", side_effect=exc_factory()
    ):
        with pytest.raises(SystemExit):
            with _HttpPostSink(
                "https://x.test", headers=[], timeout=5.0
            ) as sink:
                sink.write(_row_with_pii())
    _assert_pii_safe(caplog.text, capsys.readouterr().err)
