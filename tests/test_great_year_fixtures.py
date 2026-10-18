"""Spec fixture table for the great-year (synodic) level: 12-year arithmetic gates.

Source of truth: Ki fix plan 2026-10-17. Anchor: Lichun 2022 opens global great
year 8; 12 Ki years per gate, descending; gates always land on Earth years.
The synodic digit must come from arithmetic, never from Jupiter perihelion.

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
GY_ROWS = [
    ("1986-05-01", 2, 8, 1998),
    # Personal 9 per the spec's own formula ((n−g+4) mod 9)+1 with n=5, g=1;
    # the plan table's "5" contradicts the formula and the other 7 rows.
    ("2009-06-01", 1, 9, 2010),
    ("2018-09-01", 9, 1, 2022),
    ("2022-02-03", 9, 1, 2022),  # before Lichun 2022
    ("2022-02-05", 8, 2, 2034),
    ("2026-10-18", 8, 2, 2034),
    ("2034-02-03", 8, 2, 2034),
    ("2034-02-05", 7, 3, 2046),
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

    r = calculate_ki(date.fromisoformat(day))
    k = get_convergence_ki(day)
    assert r["ki_year"] == k["year"]["ki"], f"{day} year digit disagreement"
    assert r["ki_month"] == k["month"]["ki"], f"{day} month digit disagreement"


def test_ki_change_global_reports_exact_gate():
    import stella_server

    out = asyncio.run(stella_server.ki_change_global(birth_date=BIRTH))
    assert "Current: 8" in out, out
    assert "Lichun 2034" in out, out
    assert "perihelion" not in out.lower(), out
    assert "~2034" not in out, out
