# Plan 09-01 RED scaffolding — these tests fail until 09-02 ships impl.
"""Phase 9 (D-09-18 + bonus) — CI grep gates locking _HttpPostSink shape.

Asserts source-level structural invariants on quizify_csv_ingest.py:

  1. No certificate-disabling APIs ever land.
  2. Exactly one ssl.create_default_context() call (single TLS context).
  3. Exactly one self._opener.open( call (single-shot POST, no retry).
  4. No third-party `requests` library import (D-13 stdlib-only-at-runtime).
  5. (Bonus, RESEARCH Open Q1) Exactly one Request(...method="POST"...) call.

All counts are taken on a comment-stripped copy of the source so a comment
mentioning the very pattern under test can NEVER self-invalidate the gate
(Nyquist hygiene).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "quizify_csv_ingest.py"
SRC = SRC_PATH.read_text(encoding="utf-8")
# Strip line-leading comments so a comment cannot self-invalidate the gate.
SRC_NOCOMMENTS = re.sub(r"^\s*#.*$", "", SRC, flags=re.MULTILINE)


def test_no_cert_disabling():
    assert not re.search(
        r"CERT_NONE|_create_unverified_context|verify=False",
        SRC_NOCOMMENTS,
    ), "TLS verification must never be disabled"


def test_one_default_ssl_context():
    n = SRC_NOCOMMENTS.count("ssl.create_default_context()")
    assert n == 1, f"expected exactly 1 ssl.create_default_context(); got {n}"


def test_one_opener_open_callsite():
    n = SRC_NOCOMMENTS.count("self._opener.open(")
    assert n == 1, (
        f"expected exactly 1 self._opener.open(...) call (single-shot, no retry); "
        f"got {n}"
    )


def test_no_requests_lib():
    assert not re.search(
        r"^(import requests|from requests )",
        SRC_NOCOMMENTS,
        re.MULTILINE,
    ), "third-party `requests` library is forbidden (D-13 stdlib-only)"


def test_one_post_method_callsite():
    """Bonus gate (RESEARCH Open Q1): exactly one Request(method="POST") call.

    Allows up to ~80 chars between Request( and method="POST" so the kw can be
    on a continuation line or after url/data.
    """
    matches = re.findall(r"Request\([^)]{0,160}method=[\"']POST[\"']", SRC_NOCOMMENTS)
    assert len(matches) == 1, (
        f"expected exactly 1 Request(...method=\"POST\") call; got {len(matches)}"
    )
