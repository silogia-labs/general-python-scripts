"""Phase 6 schema validation tests.

Plan 01 (this file's first commit) covers VALI-03 only.
Plan 03 will append: TestSamplePasses (VALI-01/04), TestValidationFailurePIIsafe
(VALI-02 + T-PII-01), TestMissingExtra (VALI-05).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"
SCHEMA_PATH = ROOT / "docs" / "webhook-schema.json"


class TestSchemaSelfValidation:
    """VALI-03 / D-06-07 / D-06-25(a): schema is itself valid Draft-07."""

    def test_schema_file_exists(self) -> None:
        assert SCHEMA_PATH.is_file(), f"missing schema artifact: {SCHEMA_PATH}"

    def test_schema_declares_draft07_dialect(self) -> None:
        # Pitfall 22: HTTP (not HTTPS), trailing '#', Draft-07 (not 2020-12).
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"

    def test_schema_declares_repo_relative_id(self) -> None:
        # D-06-07: `$id` is a repo-relative path string, no GitHub URL.
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["$id"] == "quizify-csv-to-json-webhook/docs/webhook-schema.json"

    def test_schema_compiles_under_fastjsonschema(self) -> None:
        # D-06-25(a): fastjsonschema.compile() raises JsonSchemaDefinitionException
        # if the schema is malformed Draft-07. Use that as the self-validation gate.
        fastjsonschema = pytest.importorskip("fastjsonschema")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = fastjsonschema.compile(schema)  # raises if invalid
        assert callable(validator)
