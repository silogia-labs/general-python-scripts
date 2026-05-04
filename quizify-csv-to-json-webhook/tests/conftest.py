"""Shared pytest fixtures for Phase 2 row-builder + CLI tests."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "quizify-submissions.csv"


@pytest.fixture
def sample_csv_path() -> Path:
    return FIXTURE


@pytest.fixture
def dynamic_headers() -> list[str]:
    """20 dynamic headers from the live sample CSV (raw, not yet decoded)."""
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    return header[6:-6]


@pytest.fixture
def full_answers_row() -> dict:
    """Synthetic SCARLETTE-style row with all dynamic cells populated.

    Mirrors the example payload's answer_name values; HTML entities (&gt;)
    embedded in two cells to exercise CONV-06 decoding through build_row.
    """
    prefix = [
        "Scarlette",
        "Tester",
        "scarlette@example.com",
        "false",
        "+52 55 0000 0000",
        "Yes",
    ]
    dynamic = [
        "55",
        "Si",
        "Ninguno",
        "Regular",
        "4 - 6",
        "7 - 10",
        "Postpartum &gt; 24 meses",
        "Vaginal",
        "13 - 24 meses",
        "Irregular",
        "No aplica",
        "Sacro/Cola",
        "&gt; 12 semanas",
        "Escape de orina al toser/reír/saltar, Dolor en penetración o examen, Sensación de peso pélvico/prolapso",
        "Fase premenstrual/menstrual, Tos/estornudos/risas, Cargas/saltos/correr, Sentado prolongado/teletrabajo",
        "No puedo entrenar, Dificulta tareas domésticas, Dificulta cuidado de hijos, Afecta vida sexual",
        "Volver al deporte",
        "Recreacional 2-3x/sem",
        "Si",
        "Otro valor aqui",
    ]
    trailer = [
        "",
        "",
        "",
        "no_red_flag, goal_athlete, consent_given",
        "05:00",
        "2026-04-29",
    ]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def red_flag_short_circuit_row() -> dict:
    """Maria-style: only first 3 dynamic cells filled; tag = has_red_flags."""
    prefix = [
        "Maria",
        "Test",
        "maria@example.com",
        "false",
        "+52 55 0000 0001",
        "",
    ]
    dynamic = ["55", "Si", "Debilidad progresiva en piernas"] + [""] * 17
    trailer = ["", "", "", "has_red_flags", "01:30", "2026-04-15"]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def multi_select_synthetic_row() -> dict:
    """Forces ', ' multi-select heuristic to fire at q-1 and No-status branch."""
    prefix = [
        "Multi",
        "Sel",
        "multi@example.com",
        "false",
        "+52 55 0000 0002",
        "No",
    ]
    dynamic = ["A, B, C"] + [""] * 19
    trailer = ["", "", "", "", "00:30", "2026-05-01"]
    return {"prefix": prefix, "dynamic": dynamic, "trailer": trailer}


@pytest.fixture
def scoring_index_map_default() -> dict[str, int]:
    """Default-order scoring index map matching DEFAULT_TRAILER[:3] positions.

    Used by every test_row_builder.py call site that previously omitted the
    scoring map (post-Phase-5, build_row requires it as the 6th arg).

    Per D-05-06: keys are display-form canonical names from DEFAULT_TRAILER;
    values are positional indices into a default-order trailer.
    """
    return {"Result logic": 0, "Score category": 1, "Score value": 2}
