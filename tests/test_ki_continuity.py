"""Ki continuity checks: month counts flow through every Lichun, great-year gates land on Earth.

Run: .venv/bin/python tests/test_ki_continuity.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convergence_ki import _flying_star, _year_ki, get_convergence_ki, synodic_ki_for_year  # noqa: E402
from ki import calculate_natal_ki  # noqa: E402

BIRTH = "1986-05-01"


def test_natal():
    n = calculate_natal_ki(date.fromisoformat(BIRTH))
    assert n["sequence"] == "5.9.1", n["sequence"]


def test_month_count_is_continuous():
    # Walk the 15th of every month from May 1986 to Oct 2026; the global month must
    # step down by exactly 1 per Ki month, with no jump at any Lichun.
    prev = None
    y, m = 1986, 5
    while (y, m) <= (2026, 10):
        g = get_convergence_ki(f"{y:04d}-{m:02d}-15")["month"]["ki"]
        if prev is not None:
            assert g == (prev - 2) % 9 + 1, f"{y}-{m:02d}: {prev} -> {g}"
        prev = g
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    assert prev == 9 and _flying_star(5, prev) == 1


def test_birth_and_now():
    assert get_convergence_ki("1986-05-01")["month"]["ki"] == 9
    k = get_convergence_ki("2026-10-16", birth_date=BIRTH)
    p = k["personal"]
    assert (k["synodic"]["ki"], k["year"]["ki"], k["month"]["ki"]) == (8, 1, 9)
    assert (p["synodic"]["ki"], p["year"]["ki"], p["month"]["ki"]) == (2, 9, 1)


def test_great_year_gates():
    assert [synodic_ki_for_year(y) for y in (1986, 1997, 1998, 2010, 2021, 2022, 2033, 2034)] == [2, 2, 1, 9, 9, 8, 8, 7]
    for start in range(1806, 2300, 12):
        assert _year_ki(start, 2, 4) in (2, 5, 8), start
    assert get_convergence_ki("2018-06-01")["synodic"]["ki"] == 9
    assert get_convergence_ki("2034-06-01")["synodic"]["ki"] == 7


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
