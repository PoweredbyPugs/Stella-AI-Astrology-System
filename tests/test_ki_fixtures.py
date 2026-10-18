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
    # Boundary days, New York local: the day a 15° crossing falls on belongs to the period it opens.
    ("2026-02-02", 2, 9, 1),  # Jan of Ki 2025; Lichun 2026 is Feb 3, 3:01 pm
    ("2026-02-03", 1, 8, 2),  # Feb 2026 opens
    ("2026-10-07", 1, 1, 9),  # Sep 2026; Oct opens Oct 8, 2:29 am
    ("2026-10-08", 1, 9, 1),
    ("2026-11-06", 1, 9, 1),  # Nov opens Nov 7, 4:52 am
    ("2026-11-07", 1, 8, 2),
    ("2026-12-06", 1, 7, 3),  # Dec opens Dec 6, 8:52 pm: the fixed table said Dec 7
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


@pytest.mark.parametrize("day,gy,gm,pm", MONTH_ROWS)
def test_daily_cascade_agrees(day, gy, gm, pm):
    from ki import calculate_daily_ki

    r = calculate_daily_ki(date.fromisoformat(BIRTH), date.fromisoformat(day))
    assert r["global"]["year"]["ki"] == gy, f"{day} global year"
    assert r["global"]["month"]["ki"] == gm, f"{day} global month"
    assert r["personal"]["month"]["ki"] == pm, f"{day} personal month"


def test_calendar_matches_published_lichun():
    """Lichun instants against masterseanchan.com (UTC+8): 2022 Feb 4 04:50, 2025 Feb 3 22:10, 2026 Feb 4 04:02."""
    from zoneinfo import ZoneInfo
    from ki_calendar import boundary_instants_local

    hk = ZoneInfo("Asia/Hong_Kong")
    got = {y: boundary_instants_local(y)[0].astimezone(hk).strftime("%Y-%m-%d %H:%M") for y in (2022, 2025, 2026)}
    assert got == {2022: "2022-02-04 04:50", 2025: "2025-02-03 22:10", 2026: "2026-02-04 04:02"}, got


def test_octave_app_agrees_on_every_row():
    """The octave app (port 3333) must open each period on the same day as Stella."""
    import httpx
    import octave

    for day, gy, gm, pm in MONTH_ROWS:
        try:
            r = octave.octave_report(BIRTH, target_date=day)
        except httpx.HTTPError:
            pytest.skip("octave app not running")
        py, pm_app = (int(x) for x in r["today"]["personal"].split("."))
        assert pm_app == pm, f"{day} personal month: octave {pm_app}, spec {pm}"
        assert py == get_convergence_ki(day, birth_date=BIRTH)["personal"]["year"]["ki"], f"{day} personal year"


def test_convergence_reports_build_identity():
    """Every convergence payload names the code copy that produced it."""
    k = get_convergence_ki("2026-10-17")
    assert "build" in k, list(k)
    assert k["build"]["code_path"].endswith("convergence_ki.py")
    assert k["build"]["git"]  # short sha, or 'nogit' inside containers
