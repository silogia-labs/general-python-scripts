"""Shared pytest fixtures for Phase 2 row-builder + CLI tests."""

from __future__ import annotations

import csv
import http.server
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"


@pytest.fixture
def sample_csv_path() -> Path:
    return FIXTURE


@pytest.fixture
def dynamic_headers() -> list[str]:
    """20 dynamic headers from the live sample CSV (raw, not yet decoded)."""
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f, skipinitialspace=True))
    header = [h.rstrip() for h in header]
    return header[5:-6]


@pytest.fixture
def full_answers_row() -> dict:
    """Synthetic SCARLETTE-style row with all dynamic cells populated.

    Mirrors the example payload's answer_name values; HTML entities (&gt;)
    embedded in two cells to exercise CONV-06 decoding through build_row.
    """
    prefix = [
        "Scarlette",
        "Tester",
        "scarlette@example.com",
        "+52 55 0000 0000",
        "Yes",
    ]
    dynamic = [
        "55",
        "Si",
        "Ninguno",
        "Regular",
        "4 - 6",
        "7 - 10",
        "Postpartum &gt; 24 meses",
        "Vaginal",
        "13 - 24 meses",
        "Irregular",
        "No aplica",
        "Sacro/Cola",
        "&gt; 12 semanas",
        "Escape de orina al toser/reír/saltar, Dolor en penetración o examen, Sensación de peso pélvico/prolapso",
        "Fase premenstrual/menstrual, Tos/estornudos/risas, Cargas/saltos/correr, Sentado prolongado/teletrabajo",
        "No puedo entrenar, Dificulta tareas domésticas, Dificulta cuidado de hijos, Afecta vida sexual",
        "Volver al deporte",
        "Recreacional 2-3x/sem",
        "Si",
        "Otro valor aqui",
    ]
    trailer = [
        "",
        "",
        "",
        "no_red_flag, goal_athlete, consent_given",
        "05:00",
        "2026-04-29",
    ]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def red_flag_short_circuit_row() -> dict:
    """Maria-style: only first 3 dynamic cells filled; tag = has_red_flags."""
    prefix = [
        "Maria",
        "Test",
        "maria@example.com",
        "+52 55 0000 0001",
        "",
    ]
    dynamic = ["55", "Si", "Debilidad progresiva en piernas"] + [""] * 17
    trailer = ["", "", "", "has_red_flags", "01:30", "2026-04-15"]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def multi_select_synthetic_row() -> dict:
    """Forces ', ' multi-select heuristic to fire at q-1 and No-status branch."""
    prefix = [
        "Multi",
        "Sel",
        "multi@example.com",
        "+52 55 0000 0002",
        "No",
    ]
    dynamic = ["A, B, C"] + [""] * 19
    trailer = ["", "", "", "", "00:30", "2026-05-01"]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def scoring_index_map_default() -> dict[str, int]:
    """Default-order scoring index map matching DEFAULT_TRAILER[:3] positions.

    Used by every test_row_builder.py call site that previously omitted the
    scoring map (post-Phase-5, build_row requires it as the 6th arg).

    Per D-05-06: keys are display-form canonical names from DEFAULT_TRAILER;
    values are positional indices into a default-order trailer.
    """
    return {"Result logic": 0, "Score category": 1, "Score value": 2}


# ---------------------------------------------------------------------------
# Phase 8 (Plan 08-01) — synthetic 100-row CSV factory + PII-token list.
# T-PII-01-safe: tokens are obviously synthetic; they appear ONLY in the
# CSV cells of row index 50 so negative-substring assertions on stderr are
# meaningful. Append-only; no existing fixture is mutated.
# ---------------------------------------------------------------------------

SYNTHETIC_PII_TOKENS: tuple[str, ...] = (
    "synth-name-50",
    "synth-50@example.test",
    "+99 555 0100",
    "synth-tag-50",
)


def _synthetic_row(idx: int, malformed: bool = False) -> str:
    """Build one synthetic CSV line for the 100-row fixture.

    Header layout (13 columns total): 6-column CONTACT_PREFIX + 1 dynamic
    question column + 6-column DEFAULT_TRAILER.

    For ``idx == 50`` and ``malformed=True`` the cells deliberately embed the
    SYNTHETIC_PII_TOKENS so any leak into stderr is detectable. The row stays
    structurally well-formed at the CSV layer (correct column count, valid
    Subscribed value, ISO-shaped Date) so ``_RowStream`` does not flag it
    with a length-mismatch / categorical warning — that would conflate with
    ``_RowValidationError``'s exit-1 path (Pitfall 8-E in 08-RESEARCH.md).

    The schema-side malformation is reserved for a hand-built bad dict in the
    unit test (RESEARCH §Q8 Option C); the CSV-level fixture pairs with that
    integration test, which may ``pytest.skip`` if a clean CSV→build_row→
    schema-violation path cannot be produced. Implementer's discretion per
    D-08 carry-forward.
    """
    if malformed and idx == 50:
        first, last = "synth-name-50", "Tester"
        email = "synth-50@example.test"
        phone = "+99 555 0100"
        tags = "synth-tag-50"
    else:
        first, last = f"First{idx}", f"Last{idx}"
        email = f"row-{idx}@example.test"
        phone = f"+1 555 01{idx:02d}"
        tags = ""
    prefix = [first, last, email, phone, "Yes"]
    dynamic = ["55"]  # one neutral cell; satisfies build_row
    trailer = ["Result A", "Cat A", "100", tags, "01:23", "2026-05-05"]
    cells = prefix + dynamic + trailer

    def _q(c: str) -> str:
        return '"' + c.replace('"', '""') + '"'

    return ",".join(_q(c) for c in cells)


@pytest.fixture
def csv_with_bad_row_at_50(tmp_path: Path) -> Path:
    """Synthetic 100-row CSV with malformed cells at row index 50.

    UTF-8, ``\\n`` line endings (no CRLF — STREAM-02 must not be exercised
    by the fixture itself). Header matches CONTACT_PREFIX + ["question-1"]
    + DEFAULT_TRAILER. 100 data rows; row 50 carries SYNTHETIC_PII_TOKENS.

    See ``_synthetic_row`` docstring re: schema malformation strategy.
    """
    header_cells = [
        "First name", "Last name", "Email",
        "Phone", "Subscribed to newsletter",
        "question-1",
        "Result logic", "Score category", "Score value",
        "Answer tags", "Time to complete (mm:ss)", "Date",
    ]
    header_line = ",".join('"' + c + '"' for c in header_cells)
    lines = [header_line]
    for i in range(100):
        lines.append(_synthetic_row(i, malformed=(i == 50)))
    out = tmp_path / "synthetic.csv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Phase 9 (Plan 09-01) — mock_webhook fixture for AUTO-01..06 RED scaffolding.
# Loopback http.server listening on 127.0.0.1:<ephemeral>, with 4 response
# handler factories. Synthetic PII markers ONLY (T-PII-01-safe).
# Pitfalls mitigated: (2) finite hang sleep + thread.join; (9) silenced
# log_message; (10) allow_reuse_address. See 09-RESEARCH.md "Mock-server
# fixture (refined)".
# ---------------------------------------------------------------------------


class _ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True


class _BaseHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        self.server.received.append(("POST", body, dict(self.headers)))
        self._respond()

    def log_message(self, *a, **kw):  # silence default stderr noise (Pitfall 9)
        pass


def _respond_200(handler):
    body = b"server_response_marker"
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _respond_502(handler):
    body = b"Bad Gateway!!"  # exactly 13 bytes
    handler.send_response(502)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", "13")
    handler.end_headers()
    handler.wfile.write(body)


def _respond_302(handler):
    handler.send_response(302)
    handler.send_header("Location", "http://other.example.test/x")
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def _respond_hang(handler):
    time.sleep(2.0)  # finite — NOT infinite (Pitfall 2)
    body = b"server_response_marker"
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


@pytest.fixture
def mock_webhook():
    """Factory fixture: call with respond_fn -> (url, received, server)."""
    servers: list[tuple[_ReusableHTTPServer, threading.Thread]] = []

    def factory(respond_fn):
        klass = type("H", (_BaseHandler,), {"_respond": respond_fn})
        server = _ReusableHTTPServer(("127.0.0.1", 0), klass)
        server.received = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        url = f"http://127.0.0.1:{server.server_address[1]}"
        return url, server.received, server

    yield factory
    for server, thread in servers:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
