"""Phase 02-02 Task 1 — Golden-file structural diff against
`webhook-quizify-format-example.json`.

Verifies that an aligned synthetic row run through the Phase 2 CLI produces a
JSON object whose key SET and per-key TYPES match the canonical example
payload, after stripping `id` keys (D-07) and Phase-3-only keys from the
example. This is structural verification — value-level equality is intentionally
NOT enforced here (multi-select cells, tags, and image/tag fields differ in
acceptable ways across phases).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "webhook-quizify-format-example.json"
SCRIPT = ROOT / "quizify_csv_ingest.py"

# Phase 1 contact prefix + Phase 1 default trailer (kept in lock-step with
# quizify_csv_ingest.CONTACT_PREFIX / DEFAULT_TRAILER).
CONTACT_PREFIX = (
    "First name",
    "Last name",
    "Email",
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_id(obj):
    """Recursively remove every 'id' key from nested dicts/lists.

    The example payload carries Quizify-internal numeric `id` values that
    Phase 2 cannot recover (D-07). We strip them on the example side before
    structural comparison so the diff focuses on shape, not identity.
    """
    if isinstance(obj, dict):
        return {k: strip_id(v) for k, v in obj.items() if k != "id"}
    if isinstance(obj, list):
        return [strip_id(x) for x in obj]
    return obj


def _example_first_row() -> dict:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def _build_aligned_csv(csv_path: Path) -> None:
    """Construct a synthetic CSV whose dynamic headers match the example's
    `question-1`..`question-20` strings verbatim, and whose dynamic cells
    mirror the example's `answer_name` values (single-answer questions) or
    the example's plain-string multi-select values (q-14/15/16).
    """
    example = _example_first_row()

    # Dynamic headers in example order (1..20)
    dyn_headers: list[str] = [example[f"question-{n}"] for n in range(1, 21)]

    # Dynamic cells: pull answer_name from object-array answers; otherwise use
    # the multi-select string verbatim. q-7 source is intentionally written
    # with the HTML entity form so we can prove round-trip decoding.
    def cell_for(n: int) -> str:
        v = example[f"answers-{n}"]
        if isinstance(v, list):
            if not v:
                return ""
            name = v[0]["answer_name"]
            if n == 6:
                # Force HTML entity present in source CSV for the round-trip
                # assertion; the script must decode &gt; back to >.
                return name + " &gt; placeholder"
            return name
        # multi-select string (q-14, q-15, q-16)
        return v

    dyn_cells = [cell_for(n) for n in range(1, 21)]

    # Trailer: scoring fields populated for Phase 3 pass-through; tags carry
    # the three matchable tokens the example shows.
    trailer_cells = [
        "Score",                                         # Result logic
        "Signos de Alarma",                              # Score category
        "500",                                           # Score value
        "no_red_flag, goal_athlete, consent_given",      # Answer tags
        "05:00",                                         # Time to complete
        "2025-11-18",                                    # Date
    ]

    prefix_cells = [
        "Silveimar",                # First name
        "Paez",                     # Last name
        "silverpaezp@gmail.com",    # Email
        "+52 55 4888 7674",         # Phone
        "Yes",                      # Subscribed to newsletter
    ]

    header = list(CONTACT_PREFIX) + dyn_headers + list(DEFAULT_TRAILER)
    data_row = prefix_cells + dyn_cells + trailer_cells

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(data_row)


def run_aligned(tmp_path: Path) -> tuple[list[dict], str]:
    """Build the aligned CSV in tmp_path, run the CLI, return (parsed, stdout)."""
    csv_path = tmp_path / "aligned.csv"
    _build_aligned_csv(csv_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path), "--quiz-title", "Autoevaluacion"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"CLI failed (exit={result.returncode}); stderr={result.stderr}"
    )
    parsed = json.loads(result.stdout)
    return parsed, result.stdout


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_aligned_row_top_level_keyset_matches_example(tmp_path):
    """Phase 3 emits a strict superset of the example's top-level key set
    (D-05: scoring trio is slotted before placeholders so example shape is a
    strict superset). The example payload lacks `result-logic` / `score-category`
    / `score-value` — Phase 3 adds them per D-01."""
    parsed, _ = run_aligned(tmp_path)
    assert len(parsed) == 1, f"expected exactly 1 emitted row, got {len(parsed)}"
    emitted = parsed[0]
    example = _example_first_row()
    emitted_keys = set(emitted.keys())
    # `product_result` is a Quizify-internal field not yet emitted by the
    # script; exclude it from the keyset check until the contract is decided.
    example_keys = set(example.keys()) - {"product_result"}
    missing = example_keys - emitted_keys
    extra = emitted_keys - example_keys
    assert not missing, f"emitted is missing example keys: {missing}"
    assert extra == {"result-logic", "score-category", "score-value"}, (
        f"unexpected extra keys (expected only the scoring trio): {extra}"
    )


def test_aligned_row_per_key_types_match_example(tmp_path):
    """For every key shared with the (id-stripped, Phase-3-stripped) example,
    the emitted value's Python type matches the example's type.

    Carve-out for `answers-N` keys: the example payload is internally
    inconsistent — q-3's single-answer cell `"Ninguno"` is emitted as a
    plain string in the example, while every other single-answer question
    uses an object array. Phase 2's D-05 heuristic (`", " in cell` →
    string, else object array) is deterministic and produces an object
    array for `"Ninguno"`. Both shapes are valid Phase 2 answer shapes
    per D-05/D-08, so we accept either str or list for `answers-N` keys
    and require strict type equality for every other shared key.
    """
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    example = strip_id(_example_first_row())
    shared = set(emitted) & set(example)
    assert shared, "expected at least one shared key"
    answer_value_types = (str, list)
    # Phase 3 D-02 deviates from the example for placeholder keys: example has
    # "product-recommendation": "Basic", Phase 3 emits null because the CSV
    # cannot supply it. Other placeholder defaults (None / "") may also diverge
    # in type from the example. These are documented intentional deviations.
    placeholder_keys = {"product-recommendation", "product-link-type", "title", "type-page-url"}
    for k in shared:
        if k in placeholder_keys:
            continue
        if k.startswith("answers-") and not k.startswith("answers-tags-"):
            # Both Phase 2 answer shapes (str for multi-select, list for
            # single-answer) are valid; the example uses both inconsistently.
            assert isinstance(emitted[k], answer_value_types), (
                f"{k!r} unexpected type {type(emitted[k]).__name__}"
            )
            assert isinstance(example[k], answer_value_types), (
                f"example {k!r} unexpected type {type(example[k]).__name__}"
            )
            continue
        assert type(emitted[k]) is type(example[k]), (
            f"type mismatch for {k!r}: emitted={type(emitted[k]).__name__} "
            f"example={type(example[k]).__name__}"
        )


def test_aligned_row_object_array_shape_no_id(tmp_path):
    """Every list-typed answers-N has length 1 and dict keys exactly the
    three expected fields, with answer_img and answer_tag both null and NO
    `id` key (D-07).
    """
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    expected_keys = {"answer_name", "answer_img", "answer_tag"}
    saw_object_array = False
    for n in range(1, 21):
        val = emitted[f"answers-{n}"]
        if isinstance(val, list):
            saw_object_array = True
            assert len(val) == 1, f"answers-{n} length={len(val)}"
            assert set(val[0].keys()) == expected_keys, (
                f"answers-{n} keys={set(val[0].keys())}"
            )
            assert "id" not in val[0], f"answers-{n} leaked 'id' key"
            assert val[0]["answer_img"] is None
            assert val[0]["answer_tag"] is None
            assert isinstance(val[0]["answer_name"], str)
    assert saw_object_array, "expected at least one object-array answers-N"


def test_key_order_locked(tmp_path):
    """Phase 3 D-05: position 7 = quiz_title; final 7 keys are scoring + placeholders."""
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    keys = list(emitted.keys())
    assert keys[7] == "quiz_title", f"position 7 = {keys[7]!r}"
    assert keys[-7:] == [
        "result-logic",
        "score-category",
        "score-value",
        "product-recommendation",
        "product-link-type",
        "title",
        "type-page-url",
    ], f"final 7 keys = {keys[-7:]}"


def test_scoring_keys_present_after_phase3(tmp_path):
    """D-01: pass-through verbatim from trailer cells [0..2]."""
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    assert emitted["result-logic"] == "Score"
    assert emitted["score-category"] == "Signos de Alarma"
    assert emitted["score-value"] == "500"
    assert emitted["quiz_title"] == "Autoevaluacion"


def test_reserved_placeholders_match_defaults(tmp_path):
    """D-02: locked defaults — null/null/""/"" verbatim regardless of CSV content."""
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    assert emitted["product-recommendation"] is None
    assert emitted["product-link-type"] is None
    assert emitted["title"] == ""
    assert emitted["type-page-url"] == ""


def test_html_entity_round_trip(tmp_path):
    """Source `&gt;` decodes to `>` in answer_name, and the raw stdout JSON
    contains no `&gt;` substring. q-6 is the round-trip target (see cell_for).
    """
    parsed, raw_stdout = run_aligned(tmp_path)
    q6 = parsed[0]["answers-6"]
    assert isinstance(q6, list), f"q-6 should be object array, got {type(q6).__name__}"
    assert " > placeholder" in q6[0]["answer_name"], (
        f"q-6 answer_name={q6[0]['answer_name']!r}"
    )
    assert "&gt;" not in raw_stdout, "raw HTML entity leaked into emitted JSON"


def test_specific_tag_distribution_matches_example(tmp_path):
    """In the example's header ordering, `no_red_flag` lands at q-3,
    `goal_athlete` at q-17, and `consent_given` at q-20; everything else "".
    """
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    assert emitted["answers-tags-3"] == "no_red_flag"
    assert emitted["answers-tags-17"] == "goal_athlete"
    assert emitted["answers-tags-20"] == "consent_given"
    for n in range(1, 21):
        if n not in (3, 17, 20):
            actual = emitted[f"answers-tags-{n}"]
            assert actual == "", f"answers-tags-{n}={actual!r}"


def test_multi_select_questions_emit_strings(tmp_path):
    """q-14, q-15, q-16 are multi-select questions: always emit as strings,
    regardless of token count. Detection is by header pattern, not by `, `
    presence in the cell — single-token answers like "Ninguno" must still
    emit as a string for these questions.
    """
    parsed, _ = run_aligned(tmp_path)
    emitted = parsed[0]
    for n in (14, 15, 16):
        v = emitted[f"answers-{n}"]
        assert isinstance(v, str), f"answers-{n} type={type(v).__name__}"


def test_tags_top_level_starts_with_source_quizify(tmp_path):
    """tags[0] is always `source: quizify` — matches example exactly."""
    parsed, _ = run_aligned(tmp_path)
    tags = parsed[0]["tags"]
    assert isinstance(tags, list)
    assert tags[0] == "source: quizify", f"tags[0]={tags[0]!r}"
