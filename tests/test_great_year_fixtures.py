"""Spec fixture table for the great-year (synodic) level: 12-year arithmetic gates.

Source of truth: Ki fix plan 2026-10-17, re-anchored 2026-10-25: Lichun 2010 opens global
great year 2 (with Ki Age 5 and great age 8), so 2022 opens 1; 12 Ki years per gate,
descending; gates always land on Earth years. The synodic digit must come from arithmetic,
never from Jupiter perihelion.

Run: .venv/bin/python -m pytest tests/test_great_year_fixtures.py
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convergence_ki import get_convergence_ki, get_synodic_gate  # noqa: E402

BIRTH = "1986-05-01"  # natal year digit n=5

# date, global great year, personal great year (n=5), next gate (Lichun year)
# Gates are the Lichuns of 2010 + 12k; Lichun 2010 opened great year 2 (with Ki Age 5 and
# great age 8), so 2022 opened 1 and 2034 opens 9. Personal = ((n − g + 4) mod 9) + 1 with n = 5.
GY_ROWS = [
    ("1986-05-01", 4, 6, 1998),
    ("2009-06-01", 3, 7, 2010),
    ("2018-09-01", 2, 8, 2022),
    ("2022-02-02", 2, 8, 2022),
    # Lichun 2022 fell Feb 3, 3:50 pm New York; the stack turns at the instant, so a bare date
    # (read at noon) is still the old gate and an afternoon time is the new one.
    ("2022-02-03T15:00", 2, 8, 2022),
    ("2022-02-03T16:00", 1, 9, 2034),
    ("2022-02-05", 1, 9, 2034),
    ("2026-10-18", 1, 9, 2034),
    # Lichun 2034 falls Feb 3, 1:40 pm New York.
    ("2034-02-02", 1, 9, 2034),
    ("2034-02-03T14:00", 9, 1, 2046),
    ("2034-02-05", 9, 1, 2046),
]


@pytest.mark.parametrize("day,ggy,pgy,gate", GY_ROWS)
def test_convergence_great_year(day, ggy, pgy, gate):
    k = get_convergence_ki(day, birth_date=BIRTH)
    assert k["synodic"]["ki"] == ggy, f"{day} global great year"
    assert k["personal"]["synodic"]["ki"] == pgy, f"{day} personal great year"


@pytest.mark.parametrize("day,ggy,pgy,gate", GY_ROWS)
def test_synodic_gate_next_gate(day, ggy, pgy, gate):
    g = get_synodic_gate(target_date=day, birth_date=BIRTH)
    assert g["synodic_gate"]["ki"] == ggy, f"{day} gate ki"
    assert g["personal_synodic"]["ki"] == pgy, f"{day} personal gate ki"
    assert g["next_gate"]["lichun_date"][:4] == str(gate), f"{day} next gate"


@pytest.mark.parametrize("day,ggy,pgy,gate", GY_ROWS)
def test_stacks_agree_on_year_and_month(day, ggy, pgy, gate):
    from datetime import date
    from ki import calculate_ki

    if "T" in day:
        pytest.skip("boundary instant: the three-number reading is date-based")
    r = calculate_ki(date.fromisoformat(day))
    k = get_convergence_ki(day)
    assert r["ki_year"] == k["year"]["ki"], f"{day} year digit disagreement"
    assert r["ki_month"] == k["month"]["ki"], f"{day} month digit disagreement"


def test_ki_change_global_reports_exact_gate():
    import stella_server

    out = asyncio.run(stella_server.ki_change_global(birth_date=BIRTH))
    assert "Current: 1" in out, out
    assert "Lichun 2034" in out, out
    assert "perihelion" not in out.lower(), out
    assert "~2034" not in out, out
