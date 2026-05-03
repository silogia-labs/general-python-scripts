"""Phase 02-02 Task 2 — Property-style structural invariants over every row
emitted by running the Phase 2 CLI against `docs/quizify-submissions.csv`.

The CLI is invoked exactly ONCE per test module (module-scoped fixture); all
tests share the parsed payload + raw stdout to keep total runtime well below
the VALIDATION.md sampling budget (T-RESOURCE-01 mitigation).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "quizify_csv_ingest.py"
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"

# Number of dynamic columns in the live sample CSV. Verified by Phase 1
# classification (Wave 1 SUMMARY: K = 20).
EXPECTED_K = 20

# Phase-3-only top-level keys; must NOT leak from Phase 2 output.
PHASE_3_KEYS = frozenset(
    {
        "quiz_title",
        "product-recommendation",
        "product-link-type",
        "title",
        "type-page-url",
    }
)


@pytest.fixture(scope="module")
def emitted_payload() -> tuple[list[dict], str]:
    """Run the CLI once against the live sample CSV; return (rows, raw_stdout).

    Module-scoped — every test in this file shares the same subprocess result.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"CLI failed (exit={result.returncode}); stderr={result.stderr}"
    )
    rows = json.loads(result.stdout)
    assert isinstance(rows, list), f"expected list, got {type(rows).__name__}"
    return rows, result.stdout


def test_row_count_matches_sample(emitted_payload):
    """Live sample CSV has 42 data rows; all should make it through."""
    rows, _ = emitted_payload
    assert len(rows) == 42, f"expected 42 rows, got {len(rows)}"


def test_every_row_has_required_top_level_keys(emitted_payload):
    """Contract from D-10..D-13: contact + status + statusDate + phone + tags."""
    rows, _ = emitted_payload
    required = {
        "email",
        "firstName",
        "lastName",
        "status",
        "statusDate",
        "phone",
        "tags",
    }
    for i, row in enumerate(rows):
        missing = required - row.keys()
        assert not missing, f"row {i} missing top-level keys: {missing}"


def test_every_row_has_all_question_triples_for_K_20(emitted_payload):
    """D-09: every row emits question-N / answers-N / answers-tags-N for N=1..K."""
    rows, _ = emitted_payload
    for i, row in enumerate(rows):
        for n in range(1, EXPECTED_K + 1):
            assert f"question-{n}" in row, f"row {i} missing question-{n}"
            assert f"answers-{n}" in row, f"row {i} missing answers-{n}"
            assert f"answers-tags-{n}" in row, f"row {i} missing answers-tags-{n}"


def test_tags_starts_with_source_quizify(emitted_payload):
    """D-13: tags[0] is always `source: quizify`."""
    rows, _ = emitted_payload
    for i, row in enumerate(rows):
        assert isinstance(row["tags"], list), (
            f"row {i} tags type={type(row['tags']).__name__}"
        )
        assert row["tags"], f"row {i} tags is empty"
        assert row["tags"][0] == "source: quizify", (
            f"row {i} tags[0]={row['tags'][0]!r}"
        )


def test_status_is_one_of_known_values(emitted_payload):
    """D-11: status enum is `subscribed` or `unsubscribed`."""
    rows, _ = emitted_payload
    allowed = {"subscribed", "unsubscribed"}
    for i, row in enumerate(rows):
        assert row["status"] in allowed, (
            f"row {i} status={row['status']!r} not in {allowed}"
        )


def test_question_and_answers_tags_keys_are_strings(emitted_payload):
    """question-N is the verbatim header (str); answers-tags-N is str (D-04/D-09)."""
    rows, _ = emitted_payload
    for i, row in enumerate(rows):
        for n in range(1, EXPECTED_K + 1):
            qv = row[f"question-{n}"]
            tv = row[f"answers-tags-{n}"]
            assert isinstance(qv, str), (
                f"row {i} question-{n} type={type(qv).__name__}"
            )
            assert isinstance(tv, str), (
                f"row {i} answers-tags-{n} type={type(tv).__name__}"
            )


def test_answers_key_is_str_or_object_list(emitted_payload):
    """D-05/D-06/D-07/D-08: answers-N is str (incl. "") or single-element
    object array with exactly the three expected keys and no `id`.
    """
    rows, _ = emitted_payload
    expected_keys = {"answer_name", "answer_img", "answer_tag"}
    for i, row in enumerate(rows):
        for n in range(1, EXPECTED_K + 1):
            v = row[f"answers-{n}"]
            assert isinstance(v, (str, list)), (
                f"row {i} answers-{n} type={type(v).__name__}"
            )
            if isinstance(v, list):
                assert len(v) == 1, f"row {i} answers-{n} length={len(v)}"
                obj = v[0]
                assert isinstance(obj, dict), (
                    f"row {i} answers-{n}[0] type={type(obj).__name__}"
                )
                assert set(obj.keys()) == expected_keys, (
                    f"row {i} answers-{n} keys={set(obj.keys())}"
                )
                assert "id" not in obj, f"row {i} answers-{n} leaked 'id' key"
                assert obj["answer_img"] is None
                assert obj["answer_tag"] is None
                assert isinstance(obj["answer_name"], str)


def test_no_html_entities_remain_in_output(emitted_payload):
    """D-14: the live sample CSV contains `&gt;` (q-7, q-13 source); the
    serialized output must not contain `&gt;`, `&lt;`, or `&amp;`.
    """
    _, raw_stdout = emitted_payload
    assert "&gt;" not in raw_stdout, "raw &gt; entity leaked into emitted JSON"
    assert "&lt;" not in raw_stdout, "raw &lt; entity leaked into emitted JSON"
    assert "&amp;" not in raw_stdout, "raw &amp; entity leaked into emitted JSON"


def test_no_phase_3_keys_present(emitted_payload):
    """Phase 2 must not emit any Phase-3-only top-level keys."""
    rows, _ = emitted_payload
    for i, row in enumerate(rows):
        leaked = PHASE_3_KEYS & row.keys()
        assert not leaked, f"row {i} leaked Phase 3 keys {leaked}"


def test_no_id_key_anywhere_in_serialized_output(emitted_payload):
    """D-07: `"id":` substring must not appear anywhere in the JSON output."""
    _, raw_stdout = emitted_payload
    assert '"id":' not in raw_stdout, '`"id":` substring leaked into emitted JSON'


def test_every_row_emits_every_dynamic_question_header(emitted_payload):
    """Verifies WEB-02 dynamic-header binding: question-N values are non-empty
    strings and every row sees the same 20 question texts (stable across rows).
    """
    rows, _ = emitted_payload
    first_questions = [rows[0][f"question-{n}"] for n in range(1, EXPECTED_K + 1)]
    for q in first_questions:
        assert isinstance(q, str) and q.strip(), "question header empty/blank"
    for i, row in enumerate(rows[1:], start=1):
        for n in range(1, EXPECTED_K + 1):
            assert row[f"question-{n}"] == first_questions[n - 1], (
                f"row {i} question-{n} drifted from row 0"
            )


def test_consent_tag_lands_on_consiento_question(emitted_payload):
    """D-02 (consent → consiento): for every row whose Answer tags include
    `consent_given`, the emitted answers-tags-N for the dynamic question
    whose header contains "consiento" (case-insensitive) must contain
    `consent_given`. Iterates over the live header order rather than
    hardcoding N=19 vs N=20 (the live CSV places `Consiento` at q-20,
    while the example payload places it at q-19; both are valid).
    """
    rows, _ = emitted_payload
    # Locate the consent question index from row 0's headers.
    consent_idx: int | None = None
    for n in range(1, EXPECTED_K + 1):
        if "consiento" in rows[0][f"question-{n}"].casefold():
            consent_idx = n
            break
    assert consent_idx is not None, "no `Consiento` header found in dynamic columns"

    # At least one row in the sample carries `consent_given` per Wave 1 SUMMARY.
    saw_consent = False
    for i, row in enumerate(rows):
        # Only assert when we know the row carried consent_given. We can't
        # see the original CSV tags column from the emitted payload, but
        # if the consent column emits `consent_given`, that's the correct
        # binding. If a row's consent slot is non-empty, it must contain
        # `consent_given` (no other tag matches the consent pattern).
        slot = row[f"answers-tags-{consent_idx}"]
        if slot:
            saw_consent = True
            assert "consent_given" in slot, (
                f"row {i} answers-tags-{consent_idx}={slot!r} does not contain "
                f"`consent_given`"
            )
    assert saw_consent, (
        "expected at least one row to carry `consent_given` on the consent question"
    )
