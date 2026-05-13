"""Phase 6 schema validation tests.

Plan 01 (this file's first commit) covers VALI-03 only.
Plan 03 will append: TestSamplePasses (VALI-01/04), TestValidationFailurePIIsafe
(VALI-02 + T-PII-01), TestMissingExtra (VALI-05).
"""
from __future__ import annotations

import builtins
import json
import re
import sys
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


class TestSamplePasses:
    """VALI-01 / VALI-04 / D-06-25(b): 15-row sample emits and validates clean."""

    def test_sample_csv_payload_validates(self, tmp_path: Path) -> None:
        fastjsonschema = pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import convert  # noqa: PLC0415 — late import OK in tests

        out = tmp_path / "out.json"
        rc = convert(FIXTURE, None, out, "Autoevaluacion")
        assert rc == 0, "convert() must succeed on the 15-row sample"
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(payload, list) and len(payload) > 0

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = fastjsonschema.compile(schema)
        validator(payload)  # raises JsonSchemaValueException on failure → test fails

    def test_sample_with_validate_flag_exits_zero(self, tmp_path: Path) -> None:
        pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
            convert,
        )

        out = tmp_path / "out.json"
        rc = convert(FIXTURE, None, out, "Autoevaluacion")
        assert rc == 0
        payload = json.loads(out.read_text(encoding="utf-8"))

        rc2 = _run_schema_validation(payload, PROD_SCHEMA_PATH)
        assert rc2 == 0, "_run_schema_validation must accept the sample payload"


class TestValidationFailurePIIsafe:
    """VALI-02 + T-PII-01 / D-06-20 / D-06-25(c) / Pitfall 17.

    Deliberately malformed payload → exact D-06-20 stderr template, NO cell content.
    """

    def _build_payload_with_pii(self, leak_email: str, leak_phone: str, leak_name: str) -> list[dict]:
        # Build a structurally-valid row carrying KNOWN-PII tokens, then drop a
        # required key to trigger a 'required' violation on a DIFFERENT field —
        # this stresses Pitfall 17 (the offending-value attribute would otherwise
        # echo the email/phone/name).
        row = {
            "email": leak_email,
            "firstName": leak_name,
            "lastName": "Doe",
            "status": "completed",
            "statusDate": "2026-05-04",
            "phone": leak_phone,
            "tags": ["source: quizify"],
            "quiz_title": "Autoevaluacion",
            "result-logic": "",
            "score-category": "",
            "score-value": "",
            "product-recommendation": None,
            "product-link-type": None,
            "title": "",
            "type-page-url": "",
        }
        # Drop a required key — triggers 'required' violation. The offending
        # value attribute would be the row dict itself; if forwarded raw, it
        # leaks every PII token above.
        del row["email"]
        return [row]

    def test_missing_required_key_exits_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        payload = self._build_payload_with_pii("leak@example.com", "+52 55 9999 9999", "LeakageName")
        rc = _run_schema_validation(payload, PROD_SCHEMA_PATH)
        assert rc == 1, "_run_schema_validation must return 1 on schema violation"

    def test_failure_stderr_matches_d_06_20_template(self, capsys: pytest.CaptureFixture[str]) -> None:
        pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        payload = self._build_payload_with_pii("leak@example.com", "+52 55 9999 9999", "LeakageName")
        rc = _run_schema_validation(payload, PROD_SCHEMA_PATH)
        assert rc == 1
        err = capsys.readouterr().err.strip()
        # D-06-20 template, categorical only.
        assert err.startswith("ERROR schema validation failed at "), err
        assert re.match(
            r"^ERROR schema validation failed at \S+: expected \S+, got \w+$",
            err,
        ), f"stderr does not match D-06-20 template: {err!r}"

    def test_failure_stderr_does_not_leak_cell_content(self, capsys: pytest.CaptureFixture[str]) -> None:
        pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        leak_email = "leak@example.com"
        leak_phone = "+52 55 9999 9999"
        leak_name = "LeakageName"
        payload = self._build_payload_with_pii(leak_email, leak_phone, leak_name)
        _run_schema_validation(payload, PROD_SCHEMA_PATH)
        err = capsys.readouterr().err
        # Pitfall 17 / T-PII-01: NO cell content in stderr.
        assert leak_email not in err, f"email leaked into stderr: {err!r}"
        assert leak_phone not in err, f"phone leaked into stderr: {err!r}"
        assert leak_name not in err, f"name leaked into stderr: {err!r}"
        # Sanity: also ensure JsonSchemaValueException's free-form .message
        # phrasing did not slip through (e.g. 'must be string', 'data[0]').
        assert "data[" not in err, f"raw err.path leaked: {err!r}"

    def test_failure_pointer_uses_json_pointer_form(self, capsys: pytest.CaptureFixture[str]) -> None:
        pytest.importorskip("fastjsonschema")
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        payload = self._build_payload_with_pii("leak@example.com", "+52 55 9999 9999", "LeakageName")
        _run_schema_validation(payload, PROD_SCHEMA_PATH)
        err = capsys.readouterr().err.strip()
        # D-06-20: pointer is JSON Pointer form starting with '/'.
        m = re.match(r"^ERROR schema validation failed at (\S+):", err)
        assert m, f"could not extract pointer from stderr: {err!r}"
        pointer = m.group(1)
        assert pointer.startswith("/"), f"pointer not in JSON Pointer form: {pointer!r}"


class TestMissingExtra:
    """VALI-05 / D-06-19 / D-06-25(d) / Pitfall 18.

    Monkeypatch `import fastjsonschema` to raise ImportError → exact D-06-19
    stderr, exit 1, no traceback.
    """

    def _patch_import_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
            if name == "fastjsonschema":
                raise ImportError("No module named 'fastjsonschema'")
            return real_import(name, globals, locals, fromlist, level)

        # Also clear any cached import so the helper actually re-imports.
        sys.modules.pop("fastjsonschema", None)
        monkeypatch.setattr(builtins, "__import__", fake_import)

    def test_missing_fastjsonschema_emits_d_06_19_template(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        self._patch_import_fail(monkeypatch)
        rc = _run_schema_validation([], PROD_SCHEMA_PATH)
        assert rc == 1

    def test_missing_fastjsonschema_stderr_matches_locked_template(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        self._patch_import_fail(monkeypatch)
        _run_schema_validation([], PROD_SCHEMA_PATH)
        err = capsys.readouterr().err.strip()
        assert err == (
            "ERROR --validate requires fastjsonschema; install with: pip install '.[validate]'"
        ), f"D-06-19 verbatim mismatch: {err!r}"

    def test_missing_fastjsonschema_emits_no_traceback(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quizify_csv_ingest import (  # noqa: PLC0415
            SCHEMA_PATH as PROD_SCHEMA_PATH,
            _run_schema_validation,
        )

        self._patch_import_fail(monkeypatch)
        _run_schema_validation([], PROD_SCHEMA_PATH)
        err = capsys.readouterr().err
        assert "Traceback" not in err, f"unexpected traceback in stderr: {err!r}"
        assert 'File "' not in err, f"unexpected file frame in stderr: {err!r}"
