"""Phase 03-02 — README ↔ argparse drift smoke test (OPS-01).

Asserts (a) every required D-11 section heading is present in README.md,
(b) every long flag printed by `python quizify_csv_ingest.py --help`
appears as a substring of README.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
README = ROOT / "README.md"

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Quickstart",
    "## CLI reference",
    "## Configuration",
    "## Column assumptions",
    "## Output shape",
    "## Limitations",
    "## Privacy notes",
    "## Exit codes",
    "## Development",
)


def _readme_text() -> str:
    return README.read_text(encoding="utf-8")


def _help_text() -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout


def test_readme_has_all_required_sections():
    text = _readme_text()
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    assert not missing, f"README.md missing required sections: {missing}"


def test_every_flag_named_in_readme():
    help_text = _help_text()
    # Match long flags like --dry-run, --quiz-title, --trailer-columns.
    flags = set(re.findall(r"--[a-z][a-z0-9-]+", help_text))
    flags.discard("--help")  # argparse builtin; intentionally not documented.
    readme = _readme_text()
    missing = sorted(f for f in flags if f not in readme)
    assert not missing, (
        f"flags present in --help but missing from README.md: {missing}\n"
        f"Help captured:\n{help_text}"
    )
