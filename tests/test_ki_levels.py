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


@pytest.mark.parametrize("year,expected", [(2009, 1), (2010, 9), (2021, 9), (2022, 8), (2033, 8), (2034, 7), (1986, 2)])
def test_great_year(year, expected):
    assert global_great_year(year) == expected


@pytest.mark.parametrize("year,expected", [(2021, 3), (2022, 2), (2165, 2), (2166, 1), (1878, 3), (1877, 4)])
def test_ki_age(year, expected):
    assert global_ki_age(year) == expected


@pytest.mark.parametrize("year,expected", [(2021, 6), (2022, 5), (3317, 5), (3318, 4), (726, 6)])
def test_great_age(year, expected):
    assert global_great_age(year) == expected


def test_gates_land_on_earth_children():
    for g in range(2022 - 144 * 20, 2022 + 144 * 20, 144):
        assert global_great_year(g) in (2, 5, 8) and global_year(g) == 5
    for g in range(2022 - 1296 * 3, 2022 + 1296 * 3, 1296):
        assert global_ki_age(g) == 2 and global_great_year(g) == 8
    assert (gate_start(2026, "great_year"), gate_start(2026, "ki_age"),
            gate_start(2165, "ki_age"), gate_start(2021, "great_age")) == (2022, 2022, 2022, 726)


def test_stacks():
    g = global_stack(2026, 2026 * 12 + 8)
    assert g == {"great_age": 5, "ki_age": 2, "great_year": 8, "year": 1, "month": 9}
    assert personal_stack(5, g) == {"great_age": 5, "ki_age": 8, "great_year": 2, "year": 9, "month": 1}
    assert "month" not in global_stack(2026)


def test_convergence_delegates():
    from convergence_ki import synodic_ki_for_year, synodic_gate_start
    assert synodic_ki_for_year(2022) == 8 and synodic_gate_start(2026) == 2022
