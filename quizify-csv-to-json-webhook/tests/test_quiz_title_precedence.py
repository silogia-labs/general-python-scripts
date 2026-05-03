"""Phase 03-01 Task 1 — Tests for `quiz_title` resolution precedence (WEB-05).

Covers D-06..D-09, D-15: CLI flag > env var > "" default; html.unescape applied
at the boundary; whitespace preserved verbatim. Two tiers: in-process unit tests
on `_resolve_quiz_title` and subprocess tests that exercise the full CLI path.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"

# Make the script importable for unit tests on _resolve_quiz_title.
sys.path.insert(0, str(ROOT))
from quizify_csv_ingest import _resolve_quiz_title  # noqa: E402


CONTACT_PREFIX = (
    "First name",
    "Last name",
    "Email",
    "Lead Verified",
    "Phone",
    "Subscribed to newsletter",
)
DEFAULT_TRAILER = (
    "Result logic",
    "Score category",
    "Score value",
    "Answer tags",
    "Time to complete (mm:ss)",
    "Date",
)


def _make_minimal_csv(tmp_path: Path) -> Path:
    """Write a 1-row CSV with the canonical header + 1 dynamic question."""
    csv_path = tmp_path / "minimal.csv"
    header = list(CONTACT_PREFIX) + ["Q1?"] + list(DEFAULT_TRAILER)
    data_row = [
        "First",
        "Last",
        "user@example.com",
        "false",
        "+52 55 0000 0000",
        "Yes",
        "Si",
        "Score",
        "Test",
        "100",
        "",
        "00:30",
        "2024-01-15",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(data_row)
    return csv_path


# --- Unit tests on _resolve_quiz_title -------------------------------------


def test_resolve_quiz_title_cli_wins() -> None:
    ns = argparse.Namespace(quiz_title="FromCli")
    assert _resolve_quiz_title(ns, {"QUIZIFY_QUIZ_TITLE": "FromEnv"}) == "FromCli"


def test_resolve_quiz_title_env_used_when_flag_absent() -> None:
    ns = argparse.Namespace(quiz_title=None)
    assert _resolve_quiz_title(ns, {"QUIZIFY_QUIZ_TITLE": "FromEnv"}) == "FromEnv"


def test_resolve_quiz_title_default_empty_when_neither() -> None:
    ns = argparse.Namespace(quiz_title=None)
    assert _resolve_quiz_title(ns, {}) == ""


def test_resolve_quiz_title_html_unescape_applied() -> None:
    # CLI path
    ns = argparse.Namespace(quiz_title="Salud &amp; Bienestar")
    assert _resolve_quiz_title(ns, {}) == "Salud & Bienestar"
    # Env path
    ns2 = argparse.Namespace(quiz_title=None)
    assert _resolve_quiz_title(ns2, {"QUIZIFY_QUIZ_TITLE": "&lt;tag&gt;"}) == "<tag>"


def test_resolve_quiz_title_whitespace_preserved() -> None:
    # D-09: do NOT .strip()
    ns = argparse.Namespace(quiz_title="  Padded  ")
    assert _resolve_quiz_title(ns, {}) == "  Padded  "


# --- Subprocess tests (full CLI path) --------------------------------------


def _run_cli(csv_path: Path, env: dict, *extra_argv: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path), *extra_argv],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"CLI failed (exit={result.returncode}); stderr={result.stderr}"
    )
    return json.loads(result.stdout)


def test_subprocess_cli_overrides_env(tmp_path: Path) -> None:
    csv_path = _make_minimal_csv(tmp_path)
    env = {**os.environ, "QUIZIFY_QUIZ_TITLE": "FromEnv"}
    payload = _run_cli(csv_path, env, "--quiz-title", "FromCli")
    assert payload[0]["quiz_title"] == "FromCli"


def test_subprocess_env_used_when_no_cli(tmp_path: Path) -> None:
    csv_path = _make_minimal_csv(tmp_path)
    env = {**os.environ, "QUIZIFY_QUIZ_TITLE": "FromEnv"}
    payload = _run_cli(csv_path, env)
    assert payload[0]["quiz_title"] == "FromEnv"


def test_subprocess_default_empty(tmp_path: Path) -> None:
    csv_path = _make_minimal_csv(tmp_path)
    # Build env explicitly so a developer's exported QUIZIFY_QUIZ_TITLE
    # does not leak into this test.
    env = {k: v for k, v in os.environ.items() if k != "QUIZIFY_QUIZ_TITLE"}
    payload = _run_cli(csv_path, env)
    assert payload[0]["quiz_title"] == ""
