# Plan 09-01 RED scaffolding — these tests fail until 09-02 ships impl.
"""Phase 9 (AUTO-01/02/03/05/06) — integration tests via mock_webhook.

Exercises _HttpPostSink against real loopback http.server with the 4 response
factories from conftest. RED until Plan 09-02 ships:
  - _HttpPostSink(url, headers, timeout) 3-arg signature
  - urllib.request-based single-shot POST + _NoRedirectHandler
  - _log_http_failure() categorical stderr
  - sys.exit(3) on HTTP/network failure

Key invariants (RESEARCH Q10 / Pitfall 7):
  - Happy / 502 / 4xx / 302 / timeout: len(received) == 1 (single-shot, no
    retry; 302 ALSO == 1 because the original POST IS received before the
    redirect comes back and is then refused client-side).
  - Validation-fails-pre-egress: len(received) == 0 (no socket touched).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.conftest import (  # noqa: E402
    _respond_200, _respond_302, _respond_502, _respond_hang,
)


def _respond_404(handler):
    body = b"server_response_marker"
    handler.send_response(404)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


# ----- AUTO-01: Happy path — exactly one POST, body decodes to JSON ----------

def test_happy_path_one_request(mock_webhook):
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    url, received, _ = mock_webhook(_respond_200)
    rows = [{"email": "a@example.test", "firstName": "A"}]
    with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
        for r in rows:
            sink.write(r)
    assert len(received) == 1
    import json
    method, body, _ = received[0]
    assert method == "POST"
    parsed = json.loads(body.decode("utf-8"))
    assert isinstance(parsed, list) and len(parsed) == 1
    assert parsed[0]["email"] == "a@example.test"


# ----- Pre-egress validation failure: NO socket touched -----------------------

def test_invalid_payload_zero_requests(mock_webhook, tmp_path, capsys):
    """Validation-fail short-circuits BEFORE any HTTP egress (exit 1, not 3)."""
    from quizify_csv_ingest import main  # noqa: PLC0415
    url, received, _ = mock_webhook(_respond_200)
    bad = tmp_path / "bad.csv"
    bad.write_text("not,a,valid,quizify,header\n1,2,3,4,5\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--post-url", url, "--validate", str(bad)])
    # Validation/layout failure exits 1; if argparse rejects the http:// URL
    # it would be 2; either way egress count must be zero.
    assert exc.value.code in (1, 2)
    assert len(received) == 0


# ----- AUTO-03: --header reaches the wire -------------------------------------

def test_header_added(mock_webhook):
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    url, received, _ = mock_webhook(_respond_200)
    with _HttpPostSink(url, headers=[("X-Test", "yes")], timeout=5.0) as sink:
        sink.write({"k": "v"})
    assert len(received) == 1
    headers_dict = received[0][2]
    # http.server normalizes header casing — accept any case.
    lower = {k.lower(): v for k, v in headers_dict.items()}
    assert lower.get("x-test") == "yes"


def test_user_content_type_wins(mock_webhook):
    """User-supplied Content-Type overrides default application/json (D-09)."""
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    url, received, _ = mock_webhook(_respond_200)
    with _HttpPostSink(
        url,
        headers=[("Content-Type", "application/vnd.api+json")],
        timeout=5.0,
    ) as sink:
        sink.write({"k": "v"})
    assert len(received) == 1
    headers_dict = received[0][2]
    lower = {k.lower(): v for k, v in headers_dict.items()}
    assert lower.get("content-type") == "application/vnd.api+json"
    # Single Content-Type only — not duplicated with default application/json.
    ct_keys = [k for k in headers_dict if k.lower() == "content-type"]
    assert len(ct_keys) == 1


# ----- AUTO-06: 5xx / 4xx -> exit 3 + categorical stderr ----------------------

def test_502_exit_3(mock_webhook, caplog):
    import logging
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    caplog.set_level(logging.ERROR)
    url, received, _ = mock_webhook(_respond_502)
    with pytest.raises(SystemExit) as exc:
        with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
            sink.write({"k": "v"})
    assert exc.value.code == 3
    assert len(received) == 1
    txt = caplog.text
    assert "http_failure" in txt
    assert "reason=http_server_error" in txt
    assert "status=502" in txt
    assert "reason_class=5xx" in txt
    assert "body_bytes=13" in txt


def test_4xx_exit_3(mock_webhook, caplog):
    import logging
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    caplog.set_level(logging.ERROR)
    url, received, _ = mock_webhook(_respond_404)
    with pytest.raises(SystemExit) as exc:
        with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
            sink.write({"k": "v"})
    assert exc.value.code == 3
    assert len(received) == 1
    txt = caplog.text
    assert "reason=http_client_error" in txt
    assert "status=404" in txt
    assert "reason_class=4xx" in txt


# ----- AUTO-02 / Pitfall 7 / RESEARCH Q10: 302 rejected, count == 1 -----------

def test_redirect_rejected(mock_webhook, caplog):
    import logging
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    caplog.set_level(logging.ERROR)
    url, received, _ = mock_webhook(_respond_302)
    with pytest.raises(SystemExit) as exc:
        with _HttpPostSink(url, headers=[], timeout=5.0) as sink:
            sink.write({"k": "v"})
    assert exc.value.code == 3
    # RESEARCH Q10: original POST IS received before _NoRedirectHandler refuses.
    assert len(received) == 1
    txt = caplog.text
    assert "reason=http_unexpected_redirect" in txt
    assert "status=302" in txt
    assert "reason_class=3xx" in txt
    # T-PII-01: redirect Location target must NEVER reach stderr/log.
    assert "other.example.test" not in txt


# ----- AUTO-06: timeout -> exit 3 + reason=network_timeout --------------------

def test_timeout_one_request(mock_webhook, caplog):
    import logging
    from quizify_csv_ingest import _HttpPostSink  # noqa: PLC0415
    caplog.set_level(logging.ERROR)
    url, received, _ = mock_webhook(_respond_hang)
    with pytest.raises(SystemExit) as exc:
        with _HttpPostSink(url, headers=[], timeout=0.5) as sink:
            sink.write({"k": "v"})
    assert exc.value.code == 3
    # Server received the headers/body before its sleep; count == 1.
    assert len(received) == 1
    txt = caplog.text
    assert "reason=network_timeout" in txt
    assert "status=-" in txt
    assert "reason_class=-" in txt
    assert "body_bytes=-" in txt
