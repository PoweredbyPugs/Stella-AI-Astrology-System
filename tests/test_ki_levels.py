"""Lo Shu arithmetic for every level, with the Ki Age and great age anchored at Lichun 2022.

Run: .venv/bin/python -m pytest tests/test_ki_levels.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ki_levels import (  # noqa: E402
    gate_start, global_great_age, global_great_year, global_ki_age, global_month, global_stack,
    global_year, ki, personal, personal_stack,
)


def test_digits():
    assert [ki(n) for n in (0, 1, 9, 10, -1)] == [9, 1, 9, 1, 8]
    assert (personal(5, 1), personal(5, 9), personal(5, 8)) == (9, 1, 2)


def test_year_and_month():
    assert (global_year(2026), global_year(1986), global_year(2022)) == (1, 5, 5)
    assert global_month(2026 * 12) == 8 and global_month(2022 * 12) == 2
    assert global_month(2026 * 12 + 8) == 9  # Oct 2026


@pytest.mark.parametrize("year,expected", [(2009, 3), (2010, 2), (2021, 2), (2022, 1), (2033, 1), (2034, 9), (1986, 4)])
def test_great_year(year, expected):
    assert global_great_year(year) == expected


@pytest.mark.parametrize("year,expected", [(2009, 6), (2010, 5), (2153, 5), (2154, 4), (1866, 6), (1865, 7)])
def test_ki_age(year, expected):
    assert global_ki_age(year) == expected


@pytest.mark.parametrize("year,expected", [(2009, 9), (2010, 8), (3737, 8), (3738, 7), (282, 9), (281, 1)])
def test_great_age(year, expected):
    assert global_great_age(year) == expected


def test_gates_land_on_earth_children():
    for g in range(2010 - 144 * 20, 2010 + 144 * 20, 144):
        assert global_great_year(g) in (2, 5, 8) and global_year(g) in (2, 5, 8), g
    for g in range(2010 - 1728 * 2, 2010 + 1728 * 2, 1728):
        assert global_ki_age(g) in (2, 5, 8) and global_great_year(g) in (2, 5, 8), g
    # Lichun 2010: the staircase 8 · 5 · 2 · 8; Lichun 2022: only the great year turned, to 1
    assert (global_great_age(2010), global_ki_age(2010), global_great_year(2010), global_year(2010)) == (8, 5, 2, 8)
    assert (global_great_age(2022), global_ki_age(2022), global_great_year(2022), global_year(2022)) == (8, 5, 1, 5)
    assert (gate_start(2026, "great_year"), gate_start(2026, "ki_age"),
            gate_start(2153, "ki_age"), gate_start(2009, "great_age")) == (2022, 2010, 2010, 282)


def test_stacks():
    g = global_stack(2026, 2026 * 12 + 8)
    assert g == {"great_age": 8, "ki_age": 5, "great_year": 1, "year": 1, "month": 9}
    assert personal_stack(5, g) == {"great_age": 2, "ki_age": 5, "great_year": 9, "year": 9, "month": 1}
    assert "month" not in global_stack(2026)


def test_convergence_delegates():
    from convergence_ki import synodic_ki_for_year, synodic_gate_start
    assert synodic_ki_for_year(2022) == 1 and synodic_gate_start(2026) == 2022
