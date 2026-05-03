"""Phase 2 row-builder unit tests (Wave 1 — RED → GREEN).

Covers D-01..D-14 and CONV-03..06 / WEB-01..03.
"""

from __future__ import annotations

import json

import pytest

from quizify_csv_ingest import (
    build_row,
    decode_cell,
    map_status,
    match_tags_to_questions,
    shape_answer,
)


# --- decode_cell / HTML entity decoding ----------------------------------


def test_decode_cell_unescapes_entities() -> None:
    assert decode_cell("Postpartum &gt; 24 meses") == "Postpartum > 24 meses"
    assert decode_cell("&lt;tag&gt;") == "<tag>"
    assert decode_cell("") == ""
    assert decode_cell("plain") == "plain"


# --- map_status (D-11) ---------------------------------------------------


def test_status_mapping_yes_no_other_empty() -> None:
    assert map_status("Yes") == ("subscribed", None)
    assert map_status("No") == ("unsubscribed", None)
    assert map_status("") == ("unsubscribed", None)
    val, warn = map_status("Maybe")
    assert val == "unsubscribed"
    assert warn is not None
    assert "Maybe" in warn
    # PII safety: warning must not include any contact tokens
    assert "@" not in warn
    assert "+" not in warn


# --- shape_answer (D-05..D-08) ------------------------------------------


def test_answer_shape_heuristic() -> None:
    # Empty cell → empty string (D-08)
    assert shape_answer("") == ""

    # Single-token → single-element object array, no "id" key (D-06, D-07)
    out = shape_answer("Si")
    assert out == [{"answer_name": "Si", "answer_img": None, "answer_tag": None}]
    assert "id" not in out[0]

    # ", " present → plain string (D-05)
    assert shape_answer("A, B, C") == "A, B, C"
    assert shape_answer("Foo, Bar") == "Foo, Bar"


def test_id_key_never_present_in_object_array() -> None:
    out = shape_answer("Ninguno")
    assert isinstance(out, list)
    assert "id" not in out[0]
    # Also assert it round-trips through json without an id key
    assert '"id"' not in json.dumps(out)


# --- match_tags_to_questions (D-01..D-04) -------------------------------


def test_tag_distribution(dynamic_headers: list[str]) -> None:
    matched, unmatched = match_tags_to_questions(
        "no_red_flag, goal_athlete, consent_given", dynamic_headers
    )
    # q-3 (signos de alarma) → index 2; q-17 (objetivo) → index 16; q-20 (consiento) → index 19
    assert matched.get(2) == ["no_red_flag"]
    assert matched.get(16) == ["goal_athlete"]
    assert matched.get(19) == ["consent_given"]
    assert unmatched == []

    # Two tags hitting the same bucket
    matched2, unmatched2 = match_tags_to_questions(
        "has_red_flags, no_red_flag", dynamic_headers
    )
    assert matched2.get(2) == ["has_red_flags", "no_red_flag"]
    assert unmatched2 == []

    # Wholly unmatched tag (no pattern in TAG_HEADER_MAP fits)
    matched3, unmatched3 = match_tags_to_questions(
        "no_pelvic_symptom", dynamic_headers
    )
    assert matched3 == {}
    assert unmatched3 == ["no_pelvic_symptom"]

    # Empty input → empty buckets, no warnings
    assert match_tags_to_questions("", dynamic_headers) == ({}, [])


# --- build_row integration (D-09, D-10, D-13, D-14) ---------------------


def test_contact_and_status_mapping(
    full_answers_row: dict, dynamic_headers: list[str]
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(prefix, dyn, trailer, decoded_headers)

    assert row["firstName"] == "Scarlette"
    assert row["lastName"] == "Tester"
    assert row["email"] == "scarlette@example.com"
    assert row["phone"] == "+52 55 0000 0000"
    assert row["status"] == "subscribed"
    assert row["statusDate"] == "2026-04-29"


def test_status_date_passthrough(
    full_answers_row: dict, dynamic_headers: list[str]
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(prefix, dyn, trailer, decoded_headers)
    assert row["statusDate"] == "2026-04-29"
    # ISO date should not warn
    assert not any("ISO" in w or "Date" in w for w in warnings)

    # Non-ISO triggers warning, value still emitted verbatim
    trailer_nonisodate = trailer[:5] + ["29-04-2026"]
    row2, warnings2 = build_row(prefix, dyn, trailer_nonisodate, decoded_headers)
    assert row2["statusDate"] == "29-04-2026"
    assert any("Date" in w for w in warnings2)


def test_html_entity_decode(
    full_answers_row: dict, dynamic_headers: list[str]
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, _ = build_row(prefix, dyn, trailer, decoded_headers)

    # q-7 cell had &gt; → must be decoded in the object-array shape
    a7 = row["answers-7"]
    assert isinstance(a7, list)
    assert a7[0]["answer_name"] == "Postpartum > 24 meses"

    # q-13 cell had &gt; → "> 12 semanas"
    a13 = row["answers-13"]
    assert isinstance(a13, list)
    assert a13[0]["answer_name"] == "> 12 semanas"

    # JSON dump must not contain raw entities
    serialized = json.dumps(row, ensure_ascii=False)
    assert "&gt;" not in serialized
    assert "&lt;" not in serialized


def test_empty_cells_emit_all_keys(
    red_flag_short_circuit_row: dict, dynamic_headers: list[str]
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in red_flag_short_circuit_row["prefix"]]
    dyn = [decode_cell(c) for c in red_flag_short_circuit_row["dynamic"]]
    trailer = [decode_cell(c) for c in red_flag_short_circuit_row["trailer"]]
    row, _ = build_row(prefix, dyn, trailer, decoded_headers)

    # All 60 dynamic keys must exist
    for n in range(1, 21):
        assert f"question-{n}" in row
        assert f"answers-{n}" in row
        assert f"answers-tags-{n}" in row

    # Blanks beyond q-3 emit ""
    for n in range(4, 21):
        assert row[f"answers-{n}"] == ""
        assert row[f"answers-tags-{n}"] == ""

    # has_red_flags lands on q-3 (index 2)
    assert row["answers-tags-3"] == "has_red_flags"

    # Status: empty cell → unsubscribed silent
    assert row["status"] == "unsubscribed"


def test_top_level_tags_starts_with_source_quizify(
    full_answers_row: dict, dynamic_headers: list[str]
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, _ = build_row(prefix, dyn, trailer, decoded_headers)
    assert isinstance(row["tags"], list)
    assert row["tags"][0] == "source: quizify"

    # Unmatched tag falls into top-level tags + warning
    bad_trailer = trailer[:3] + ["totally_unknown_tag"] + trailer[4:]
    row2, warnings2 = build_row(prefix, dyn, bad_trailer, decoded_headers)
    assert "totally_unknown_tag" in row2["tags"]
    assert any("totally_unknown_tag" in w for w in warnings2)


def test_headers_are_html_unescaped_in_question_keys() -> None:
    # Synthetic header with HTML entity to confirm question-N values are decoded
    headers = ["Tamaño &gt; promedio?"]
    prefix = ["F", "L", "e@x.com", "false", "+1", "Yes"]
    dyn = ["Si"]
    trailer = ["", "", "", "", "00:10", "2026-01-01"]
    decoded_headers = [decode_cell(h) for h in headers]
    decoded_dyn = [decode_cell(c) for c in dyn]
    row, _ = build_row(prefix, decoded_dyn, trailer, decoded_headers)
    assert row["question-1"] == "Tamaño > promedio?"


def test_full_answers_synthetic_row_shape(
    full_answers_row: dict, dynamic_headers: list[str]
) -> None:
    """Synthetic SCARLETTE-style row exercises the full mapping contract."""
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(prefix, dyn, trailer, decoded_headers)

    # Tag routing for matched tags
    assert row["answers-tags-3"] == "no_red_flag"
    assert row["answers-tags-17"] == "goal_athlete"
    assert row["answers-tags-20"] == "consent_given"
    # All other answers-tags-N empty
    for n in range(1, 21):
        if n not in (3, 17, 20):
            assert row[f"answers-tags-{n}"] == "", f"expected empty for n={n}"

    # answers-3 single-token → object array
    assert row["answers-3"] == [
        {"answer_name": "Ninguno", "answer_img": None, "answer_tag": None}
    ]

    # answers-14 multi-comma → string
    assert isinstance(row["answers-14"], str)
    assert ", " in row["answers-14"]

    # No "id" key anywhere
    assert '"id"' not in json.dumps(row, ensure_ascii=False)

    # No PII in warnings
    for w in warnings:
        assert "@" not in w
        assert "+52" not in w
