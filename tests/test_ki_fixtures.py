"""Spec fixture tables for Ki month seeds and great-year gates.

Source of truth: Ki fix plan 2026-10-17. Both the get_ki stack (ki.py) and the
convergence stack (convergence_ki.py) must return identical year/month values
for every row.

Run: .venv/bin/python -m pytest tests/test_ki_fixtures.py
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convergence_ki import get_convergence_ki  # noqa: E402
from ki import calculate_ki  # noqa: E402

BIRTH = "1986-05-01"  # natal year digit n=5

# date, global year, global month, personal month (n=5)
MONTH_ROWS = [
    ("2026-02-15", 1, 8, 2),
    ("2024-02-15", 3, 5, 5),
    ("2025-02-15", 2, 2, 8),
    ("2019-05-15", 8, 8, 2),
    ("2019-12-01", 8, 2, 8),  # Nov Ki month
    ("2022-06-15", 5, 7, 3),
    ("2021-11-15", 6, 5, 5),
    ("2026-10-09", 1, 9, 1),
    ("2027-03-15", 9, 4, 6),
]


@pytest.mark.parametrize("day,gy,gm,pm", MONTH_ROWS)
def test_convergence_month_seed(day, gy, gm, pm):
    k = get_convergence_ki(day, birth_date=BIRTH)
    assert k["year"]["ki"] == gy, f"{day} global year"
    assert k["month"]["ki"] == gm, f"{day} global month"
    assert k["personal"]["month"]["ki"] == pm, f"{day} personal month"


@pytest.mark.parametrize("day,gy,gm,pm", MONTH_ROWS)
def test_get_ki_stack_agrees(day, gy, gm, pm):
    r = calculate_ki(date.fromisoformat(day))
    assert r["ki_year"] == gy, f"{day} global year"
    assert r["ki_month"] == gm, f"{day} global month"


def test_convergence_reports_build_identity():
    """Every convergence payload names the code copy that produced it."""
    k = get_convergence_ki("2026-10-17")
    assert "build" in k, list(k)
    assert k["build"]["code_path"].endswith("convergence_ki.py")
    assert k["build"]["git"]  # short sha, or 'nogit' inside containers
