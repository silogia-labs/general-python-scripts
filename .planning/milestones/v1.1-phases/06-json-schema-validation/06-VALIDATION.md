---
phase: 6
slug: json-schema-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; version pinned implicitly by `quizify-csv-to-json-webhook/requirements-dev.txt`) |
| **Config file** | `quizify-csv-to-json-webhook/pytest.ini` (`pythonpath = .`) |
| **Quick run command** | `cd quizify-csv-to-json-webhook && pytest -q tests/test_schema_validation.py tests/test_readme_help_alignment.py` |
| **Full suite command** | `cd quizify-csv-to-json-webhook && pytest -q` |
| **Estimated runtime** | ~1.5 seconds (current 71 tests run in ~1.09s; +5 unit-level schema tests adds ~0.4s) |

---

## Sampling Rate

- **After every task commit:** Run `cd quizify-csv-to-json-webhook && pytest -q tests/test_schema_validation.py tests/test_readme_help_alignment.py`
- **After every plan wave:** Run `cd quizify-csv-to-json-webhook && pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green (76 tests projected)
- **Max feedback latency:** ~1.5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | — | — | Wave 0 fixture: schema artifact exists at locked path | unit | `test -f quizify-csv-to-json-webhook/docs/webhook-schema.json` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | VALI-03 | — | Schema self-validates against Draft-07 metaschema (fastjsonschema.compile raises JsonSchemaDefinitionException on invalid) | unit | `pytest -q tests/test_schema_validation.py::TestSchemaSelfValidation` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 0 | — | — | Wave 0 packaging: `quizify-csv-to-json-webhook/pyproject.toml` declares `[validate]` optional extra; flit_core build backend; py-modules `quizify_csv_ingest` | unit | `python -c "import tomllib,sys; d=tomllib.loads(open('quizify-csv-to-json-webhook/pyproject.toml').read()); assert 'fastjsonschema' in d['project']['optional-dependencies']['validate'][0]"` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 1 | VALI-01, VALI-04 | — | `--validate` argparse flag added; default off; lazy `import fastjsonschema` inside helper; default-path emits unchanged JSON | unit | `pytest -q tests/test_cli_emit.py::test_default_invocation_emits_json_to_stdout && pytest -q tests/test_schema_validation.py::TestSamplePasses` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 1 | VALI-02 | T-PII-01 | Validation failure emits exact D-06-20 stderr template; no cell content; pointer + expected/actual type only; exit 1 | unit | `pytest -q tests/test_schema_validation.py::TestValidationFailurePIIsafe` | ❌ W0 | ⬜ pending |
| 6-03-03 | 03 | 1 | VALI-05 | — | Missing fastjsonschema under `--validate` emits D-06-19 actionable stderr; exit 1; no traceback | unit | `pytest -q tests/test_schema_validation.py::TestMissingExtra` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 2 | VALI-06 | — | README adds `--validate` row to CLI reference table; `[validate]` install line under Quickstart; D-11 drift test green | unit | `pytest -q tests/test_readme_help_alignment.py` | ✅ existing | ⬜ pending |
| 6-04-02 | 04 | 2 | — | — | MILESTONES.md / PROJECT.md decisions table updated for v1.1 VALI-01 ship; no behavioral lock changes | manual + grep | `grep -q "VALI-01" .planning/PROJECT.md` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: task-id assignments are illustrative; planner may reorganize across plans 01–04 as long as every requirement keeps automated coverage and Wave 0 fixtures land before Wave 1 consumers.*

---

## Wave 0 Requirements

- [ ] `quizify-csv-to-json-webhook/docs/webhook-schema.json` — hand-written Draft-07 schema artifact. Must exist before any validation test can run.
- [ ] `quizify-csv-to-json-webhook/pyproject.toml` — flit_core project metadata + `[project.optional-dependencies] validate = ["fastjsonschema>=2.21.2"]`. Must exist before `pip install '.[validate]'` can resolve.
- [ ] `quizify-csv-to-json-webhook/tests/test_schema_validation.py` — new test file with 4 test classes per D-06-25:
  - `TestSchemaSelfValidation` — VALI-03 (compile-time Draft-07 self-validate via `fastjsonschema.compile`).
  - `TestSamplePasses` — VALI-01, VALI-04 (42-row sample emits and validates clean).
  - `TestValidationFailurePIIsafe` — VALI-02 + T-PII-01 (deliberate malformed payload → exact D-06-20 stderr template, no cell content).
  - `TestMissingExtra` — VALI-05 (monkeypatch `import fastjsonschema` to raise ImportError → exact D-06-19 stderr, exit 1, no traceback).
- [ ] `pip install '.[validate]'` for CI — install fastjsonschema so the new tests run. Locally, tests use `pytest.importorskip("fastjsonschema")` when not installed.
- [ ] No new `conftest.py` fixtures required — existing `sample_csv_path`, `dynamic_headers`, and Phase-5's `scoring_index_map_default` cover all test inputs.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-user install ergonomics for `pip install '.[validate]'` | VALI-05 | Real-world install behavior depends on the user's pip / Python combo and whether they cd into `quizify-csv-to-json-webhook/` first | (1) `cd quizify-csv-to-json-webhook && python -m venv /tmp/venv6 && /tmp/venv6/bin/pip install '.[validate]'`; (2) `/tmp/venv6/bin/python quizify_csv_ingest.py docs/quizify-submissions.csv --validate -o /tmp/out.json`; (3) verify exit 0; (4) `/tmp/venv6/bin/pip uninstall fastjsonschema -y`; (5) re-run with `--validate`; (6) verify exit 1 and the D-06-19 message printed without a traceback |
| README rendering of the `--validate` row in the existing 10-section structure | VALI-06 / D-11 | The drift test asserts section count and flag presence but not visual rendering | Open `quizify-csv-to-json-webhook/README.md` in a Markdown previewer (or GitHub's render), confirm the `--validate` row sits inside the existing CLI reference table and the install line under Quickstart reads naturally |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (schema artifact, pyproject.toml, new test file)
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter (planner's responsibility after task IDs are finalized)

**Approval:** pending
