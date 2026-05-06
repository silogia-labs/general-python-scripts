"""Phase 10 D-10-16 — empty-deps gate for make-scripts/ + D-10-03 use-strict gate.

Asserts make-scripts/package.json ships private with empty dependencies and
devDependencies (D-13 extended to JS), and that both JS modules begin with
`"use strict";` as their first non-comment, non-blank line.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "make-scripts" / "package.json"


def test_make_scripts_zero_runtime_deps():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("dependencies", {}) == {}, \
        "D-13: no JS runtime deps allowed in make-scripts/"


def test_make_scripts_zero_dev_deps():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("devDependencies", {}) == {}, \
        "D-13: no JS dev deps — node:test stdlib only"


def test_make_scripts_private_package():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("private") is True, \
        "make-scripts/package.json must be marked private to prevent accidental publish"


def test_make_scripts_use_strict_directive():
    """D-10-03 — first non-comment, non-blank line is `"use strict";`."""
    for src in ("quizify-mapping.js", "score-calculations.js"):
        path = ROOT / "make-scripts" / src
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            assert stripped == '"use strict";', \
                f"{src}: first non-comment line is {stripped!r}, not \"use strict\";"
            break
