"""Phase 2 row-builder unit tests (Wave 1 — RED → GREEN).

Covers D-01..D-14 and CONV-03..06 / WEB-01..03.
"""

from __future__ import annotations

import json
import logging

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

    # New mappings: no_pelvic_symptom → q-14 (piso pélvico); no_triggers → q-15 (disparadores)
    matched_pelv, unmatched_pelv = match_tags_to_questions(
        "no_pelvic_symptom, no_triggers", dynamic_headers
    )
    assert matched_pelv.get(13) == ["no_pelvic_symptom"]
    assert matched_pelv.get(14) == ["no_triggers"]
    assert unmatched_pelv == []

    # Wholly unmatched tag (no pattern in TAG_HEADER_MAP fits)
    matched3, unmatched3 = match_tags_to_questions(
        "unknown_xyz_tag", dynamic_headers
    )
    assert matched3 == {}
    assert unmatched3 == ["unknown_xyz_tag"]

    # Empty input → empty buckets, no warnings
    assert match_tags_to_questions("", dynamic_headers) == ({}, [])


# --- build_row integration (D-09, D-10, D-13, D-14) ---------------------


def test_contact_and_status_mapping(
    full_answers_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )

    assert row["firstName"] == "Scarlette"
    assert row["lastName"] == "Tester"
    assert row["email"] == "scarlette@example.com"
    assert row["phone"] == "+52 55 0000 0000"
    assert row["status"] == "subscribed"
    assert row["statusDate"] == "2026-04-29"


def test_status_date_passthrough(
    full_answers_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    assert row["statusDate"] == "2026-04-29"
    # ISO date should not warn
    assert not any("ISO" in w or "Date" in w for w in warnings)

    # Non-ISO triggers warning, value still emitted verbatim
    trailer_nonisodate = trailer[:5] + ["29-04-2026"]
    row2, warnings2 = build_row(
        prefix, dyn, trailer_nonisodate, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    assert row2["statusDate"] == "29-04-2026"
    assert any("Date" in w for w in warnings2)


def test_html_entity_decode(
    full_answers_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, _ = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )

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
    red_flag_short_circuit_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in red_flag_short_circuit_row["prefix"]]
    dyn = [decode_cell(c) for c in red_flag_short_circuit_row["dynamic"]]
    trailer = [decode_cell(c) for c in red_flag_short_circuit_row["trailer"]]
    row, _ = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )

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
    full_answers_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, _ = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    assert isinstance(row["tags"], list)
    assert row["tags"][0] == "source: quizify"

    # Unmatched tag falls into top-level tags + warning
    bad_trailer = trailer[:3] + ["totally_unknown_tag"] + trailer[4:]
    row2, warnings2 = build_row(
        prefix, dyn, bad_trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    assert "totally_unknown_tag" in row2["tags"]
    assert any("totally_unknown_tag" in w for w in warnings2)


def test_headers_are_html_unescaped_in_question_keys(scoring_index_map_default) -> None:
    # Synthetic header with HTML entity to confirm question-N values are decoded
    headers = ["Tamaño &gt; promedio?"]
    prefix = ["F", "L", "e@x.com", "false", "+1", "Yes"]
    dyn = ["Si"]
    trailer = ["", "", "", "", "00:10", "2026-01-01"]
    decoded_headers = [decode_cell(h) for h in headers]
    decoded_dyn = [decode_cell(c) for c in dyn]
    row, _ = build_row(
        prefix, decoded_dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    assert row["question-1"] == "Tamaño > promedio?"


def test_full_answers_synthetic_row_shape(
    full_answers_row: dict, dynamic_headers: list[str], scoring_index_map_default
) -> None:
    """Synthetic SCARLETTE-style row exercises the full mapping contract."""
    decoded_headers = [decode_cell(h) for h in dynamic_headers]
    prefix = [decode_cell(c) for c in full_answers_row["prefix"]]
    dyn = [decode_cell(c) for c in full_answers_row["dynamic"]]
    trailer = [decode_cell(c) for c in full_answers_row["trailer"]]
    row, warnings = build_row(
        prefix, dyn, trailer, decoded_headers,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )

    # Tag routing for matched tags
    assert row["answers-tags-3"] == "no_red_flag"
    assert row["answers-tags-17"] == "goal_athlete"
    assert row["answers-tags-20"] == "consent_given"
    # All other answers-tags-N empty
    for n in range(1, 21):
        if n not in (3, 17, 20):
            assert row[f"answers-tags-{n}"] == "", f"expected empty for n={n}"

    # answers-3 is a multi-select question (signos de alarma) — always string
    assert row["answers-3"] == "Ninguno"

    # answers-14 is a multi-select question (piso pélvico) — always string
    assert isinstance(row["answers-14"], str)

    # No "id" key anywhere
    assert '"id"' not in json.dumps(row, ensure_ascii=False)

    # No PII in warnings
    for w in warnings:
        assert "@" not in w
        assert "+52" not in w


# --- Phase 3: scoring + placeholders + quiz_title (D-01..D-05, D-16) -----


def _minimal_decoded_inputs(
    trailer: list[str] | None = None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Tiny single-question synthetic input. Caller may supply a custom trailer."""
    prefix = ["F", "L", "e@x.com", "false", "+1", "Yes"]
    dynamic = ["Si"]
    headers = ["Q1?"]
    if trailer is None:
        trailer = ["Score", "Test", "100", "", "00:30", "2024-01-15"]
    return prefix, dynamic, trailer, headers


def test_quiz_title_threaded_through_build_row(scoring_index_map_default) -> None:
    prefix_d, dyn_d, trailer_d, headers_d = _minimal_decoded_inputs()
    row, _ = build_row(
        prefix_d, dyn_d, trailer_d, headers_d,
        quiz_title="Autoevaluacion", scoring_index_map=scoring_index_map_default,
    )
    assert row["quiz_title"] == "Autoevaluacion"
    # D-05: quiz_title is the 8th key (0-indexed position 7)
    assert list(row.keys())[7] == "quiz_title"


def test_scoring_pass_through(scoring_index_map_default) -> None:
    prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
    trailer_d = ["Score", "Signos de Alarma", "500", "", "00:30", "2024-01-15"]
    row, _ = build_row(
        prefix_d, dyn_d, trailer_d, headers_d,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    # D-01 / D-04: pass-through verbatim, string-typed
    assert row["result-logic"] == "Score"
    assert row["score-category"] == "Signos de Alarma"
    assert row["score-value"] == "500"
    assert isinstance(row["score-value"], str)


def test_empty_scoring_emits_empty_strings(scoring_index_map_default) -> None:
    prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
    trailer_d = ["", "", "", "", "", "2024-01-15"]
    row, warnings_out = build_row(
        prefix_d, dyn_d, trailer_d, headers_d,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    # D-03: empty scoring cells emit "" verbatim, no WARNING
    assert row["result-logic"] == ""
    assert row["score-category"] == ""
    assert row["score-value"] == ""
    for w in warnings_out:
        assert "result-logic" not in w
        assert "score-category" not in w
        assert "score-value" not in w
        assert "Result logic" not in w
        assert "Score category" not in w
        assert "Score value" not in w


def test_reserved_placeholders_match_locked_defaults(scoring_index_map_default) -> None:
    prefix_d, dyn_d, trailer_d, headers_d = _minimal_decoded_inputs()
    row, _ = build_row(
        prefix_d, dyn_d, trailer_d, headers_d,
        quiz_title="", scoring_index_map=scoring_index_map_default,
    )
    # D-02: locked defaults verbatim
    assert row["product-recommendation"] is None
    assert row["product-link-type"] is None
    assert row["title"] == ""
    assert row["type-page-url"] == ""


def test_key_order_matches_d05(scoring_index_map_default) -> None:
    prefix_d, dyn_d, trailer_d, headers_d = _minimal_decoded_inputs()
    row, _ = build_row(
        prefix_d, dyn_d, trailer_d, headers_d,
        quiz_title="My Quiz", scoring_index_map=scoring_index_map_default,
    )
    keys = list(row.keys())
    # Contact block (positions 0..6) + quiz_title at position 7
    assert keys[:8] == [
        "email",
        "firstName",
        "lastName",
        "status",
        "statusDate",
        "phone",
        "tags",
        "quiz_title",
    ]
    # Final 7 keys: scoring trio + 4 placeholders in declared D-05 order
    assert keys[-7:] == [
        "result-logic",
        "score-category",
        "score-value",
        "product-recommendation",
        "product-link-type",
        "title",
        "type-page-url",
    ]


class TestScrambledTrailer:
    """TRAIL-01: build_row binds scoring trio by named index, not positional.

    A reversed scoring_index_map proves the binding is name-keyed: if the
    implementation regressed to positional reads, the values would swap.
    """

    def test_scrambled_order_binds_correctly(
        self, scoring_index_map_default
    ) -> None:
        # Reversed index map: "Result logic" reads cell 2, "Score value" reads cell 0
        reversed_map = {"Result logic": 2, "Score category": 1, "Score value": 0}
        prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
        # trailer cells: [VAL, CAT, LOG, "", "00:30", "2024-01-15"] — note positions 0/1/2
        trailer_d = ["VAL", "CAT", "LOG", "", "00:30", "2024-01-15"]
        row, _ = build_row(
            prefix_d, dyn_d, trailer_d, headers_d,
            quiz_title="", scoring_index_map=reversed_map,
        )
        # Named lookup → "Result logic" reads cell 2 == "LOG", not cell 0 == "VAL"
        assert row["result-logic"] == "LOG"
        assert row["score-category"] == "CAT"
        assert row["score-value"] == "VAL"


class TestMissingColumnWarning:
    """TRAIL-02 + T-PII-01: missing canonical trio column → empty string + PII-safe WARNING.

    Verifies D-05-08 (locked warning template), D-05-09 (no positional fallback),
    D-05-10 (Pitfall 10), and T-PII-01 (no cell content / no PII tokens).
    """

    def test_missing_column_emits_empty_string(self) -> None:
        # "Result logic" deliberately omitted from the index map
        partial_map = {"Score category": 1, "Score value": 2}
        prefix_d, dyn_d, _trailer_default, headers_d = _minimal_decoded_inputs()
        trailer_d = ["IGNORED_AT_0", "CAT", "VAL", "", "00:30", "2024-01-15"]
        row, _ = build_row(
            prefix_d, dyn_d, trailer_d, headers_d,
            quiz_title="", scoring_index_map=partial_map,
        )
        # NO positional fallback to trailer_d[0] — must be "" (D-05-10 / Pitfall 10)
        assert row["result-logic"] == ""
        assert row["score-category"] == "CAT"
        assert row["score-value"] == "VAL"

    def test_warning_message_matches_locked_template(self, tmp_path, caplog) -> None:
        # Build a 1-row CSV whose --trailer-columns omits "Result logic".
        # Use a 6-column custom trailer: replace "Result logic" with a non-trio
        # placeholder column "Notes" while keeping Answer tags at index 3 and
        # Date at index 5 (D-05-05: positional reads for those two are out of scope).
        import csv as _csv
        from quizify_csv_ingest import CONTACT_PREFIX, convert
        csv_path = tmp_path / "missing_result_logic.csv"
        custom_trailer = (
            "Notes", "Score category", "Score value",
            "Answer tags", "Time to complete (mm:ss)", "Date",
        )
        header = list(CONTACT_PREFIX) + ["q1"] + list(custom_trailer)
        row = [
            "First", "Last", "x@example.com", "555-0100", "Yes",
            "Q1 cell",
            "note text", "cat", "100", "tag1", "00:30", "2024-01-15",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = _csv.writer(f)
            w.writerow(header)
            w.writerow(row)
        with caplog.at_level(logging.WARNING):
            rc = convert(csv_path, custom_trailer, output=tmp_path / "out.json", quiz_title="")
        assert rc == 0
        matches = [
            r for r in caplog.records
            if "absent from CSV header" in r.getMessage()
            and "'Result logic'" in r.getMessage()
            and "result-logic in all rows" in r.getMessage()
        ]
        assert len(matches) == 1, [r.getMessage() for r in caplog.records]

    def test_warning_pii_safe(self, tmp_path, caplog) -> None:
        # Same fixture shape as above — 6-col trailer, "Result logic" omitted.
        import csv as _csv
        from quizify_csv_ingest import CONTACT_PREFIX, convert
        csv_path = tmp_path / "pii_check.csv"
        custom_trailer = (
            "Notes", "Score category", "Score value",
            "Answer tags", "Time to complete (mm:ss)", "Date",
        )
        header = list(CONTACT_PREFIX) + ["q1"] + list(custom_trailer)
        row = [
            "PIINAME", "LASTPII", "leak@example.com", "Yes", "+15550100", "Yes",
            "PIIANSWER",
            "note text", "cat", "100", "tag1", "00:30", "2024-01-15",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = _csv.writer(f)
            w.writerow(header)
            w.writerow(row)
        with caplog.at_level(logging.WARNING):
            convert(csv_path, custom_trailer, output=tmp_path / "out.json", quiz_title="")
        matches = [r for r in caplog.records if "absent from CSV header" in r.getMessage()]
        assert len(matches) >= 1
        msg = matches[0].getMessage()
        assert "@" not in msg
        assert "+" not in msg
        assert "leak" not in msg
        assert "PIINAME" not in msg
        assert "LASTPII" not in msg
        assert "PIIANSWER" not in msg
