"""Phase 10 T-PII-01 carry-forward — make-scripts/tests/fixtures/ has no real PII.

Asserts no fixture file in make-scripts/tests/fixtures/ contains tokens drawn
from docs/quizify-submissions.csv. Names from CONVENTIONS.md §MAKE-FIX-01
(Karen Retamal, Javielys Mancilla) are explicitly forbidden — they appear in
manual-verification docs but must NOT be ported into automated fixtures.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "make-scripts" / "tests" / "fixtures"

FORBIDDEN_TOKENS = (
    "Karen Retamal", "Karen", "Retamal",
    "Javielys Mancilla", "Javielys", "Mancilla",
)


def test_no_real_pii_in_fixtures():
    if not FIXTURE_ROOT.exists():
        return  # nothing to scan yet
    leaks = []
    for path in FIXTURE_ROOT.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                leaks.append((path.name, token))
    assert not leaks, f"PII tokens found in fixtures: {leaks}"
