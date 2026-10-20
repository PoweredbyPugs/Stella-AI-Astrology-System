"""The octave math in Stella: the Nine-Year Spiral library ported, with hub inheritance.

Fixtures are the app's own vitest cases for 1986-05-01, plus the places where inheritance
changes the answer (a 5 year or month forms over the level above, never over a child).

Run: .venv/bin/python -m pytest tests/test_octave_math.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from octave_math import (  # noqa: E402
    build_report, change, great_year_label, month_figure, natal, natal_label, octave_label, octaves,
    year_figure,
)

N = 5


def test_natal_and_octaves():
    n = natal(date(1986, 5, 1))
    assert (n["year"], n["month"], n["third"], n["kiYear"]) == (5, 9, 1, 1986)
    assert natal_label(n) == "5 · 9 · 1"
    lst = octaves(N, 1986)
    assert [o["start"] for o in lst[:7]] == [1982, 1991, 2000, 2009, 2018, 2027, 2036]
    assert lst[0]["index"] == 0 and lst[0]["enteredAt"] == 5
    assert octave_label(lst[4]) == "Octave 4 · Feb 2018 → Jan 2027"
    assert great_year_label(lst[4]) == "great year 1 → 2 in 2022"
    assert great_year_label(lst[5]) == "great year 2 → 3 in 2034"


def test_year_figures_match_the_app():
    want = {2018: 29, 2019: 7, 2020: 40, 2021: 59, 2022: 2, 2023: 12, 2024: 45, 2025: 23, 2026: 35, 2027: 8}
    for y, n in want.items():
        assert year_figure(N, y)["number"] == n, y
    assert year_figure(N, 2022)["inherited"] == [{"level": "year", "from": "great_year"}]


def test_month_figures():
    assert month_figure(N, 2026, 8)["number"] == 63   # Oct 2026 = 9.1
    assert month_figure(N, 2026, 7)["number"] == 30   # Sep 2026 = 9.9
    assert month_figure(N, 2018, 0)["number"] == 29   # Feb 2018 = 1.5
    aug22 = month_figure(N, 2022, 6)                  # Aug 2022 = 5.5 → both inherit Kun
    assert aug22["number"] == 2
    assert aug22["inherited"] == [{"level": "year", "from": "great_year"}, {"level": "month", "from": "great_year"}]
    assert month_figure(N, 2022, 1)["number"] == 35   # Mar 2022 = 5.9 → Li over inherited Kun


def test_echo_pairs_of_octave_4():
    def pair(a, b):
        return change(year_figure(N, a), year_figure(N, b))
    assert (pair(2018, 2021)["moving"], pair(2018, 2021)["lowerMoved"], pair(2018, 2021)["transformed"]["number"]) == ([6], False, 59)
    assert (pair(2019, 2025)["moving"], pair(2019, 2025)["lowerMoved"]) == ([2, 6], True)
    assert (pair(2022, 2024)["moving"], pair(2022, 2024)["lowerMoved"]) == ([4, 5], False)


def test_report_matches_the_app_fixture():
    r = build_report(date(1986, 5, 1), None, date(2026, 10, 16), "Chris")
    assert r["natal"]["triple"] == "5 · 9 · 1"
    assert (r["today"]["kiMonth"], r["today"]["personal"], r["today"]["greatYear"]) == ("Oct 2026", "9.1", 2)
    assert r["today"]["monthFigure"]["number"] == 63 and r["today"]["yearFigure"]["number"] == 35
    assert r["today"]["monthPosition"] == "1 ↔ 4 · with Apr 2026, Jan 2027"
    assert r["today"]["nextGreatYearShift"] == {"kiYear": 2034, "from": 2, "to": 3}
    assert r["octave"] == {"index": 4, "label": "Octave 4 · Feb 2018 → Jan 2027",
                           "greatYear": "great year 1 → 2 in 2022", "enteredAt": None, "containsToday": True}
    assert len(r["years"]) == 9 and r["years"][0]["kiYear"] == 2018
    assert [p["movingLines"] for p in r["echoPairs"]] == [[6], [2, 6], [4, 5]]
    assert [(p["years"], p["primary"]["number"], p["transformed"]["number"]) for p in r["echoPairs"]] == [
        ([2018, 2021], 29, 59), ([2019, 2025], 7, 23), ([2022, 2024], 2, 45)]
    assert r["nextCycle"]["label"] == "Feb 2027" and r["nextCycle"]["personal"] == "1.5"
    assert r["nextCycle"]["yearFigure"]["number"] == 8
    months = {m["label"]: m for y in r["years"] for m in y["months"]}
    assert months["Sep 2026"]["position"] == "Source and arrival · 9"
    assert months["Oct 2026"]["now"] is True
    assert all("no figure" not in m["figure"] for m in months.values())
    assert months["Aug 2022"]["figure"].startswith("2 ")


def test_birth_octave_marks_months_before_birth():
    r = build_report(date(1986, 5, 1), 0, date(2026, 10, 16), None)
    assert r["octave"]["index"] == 0 and r["octave"]["enteredAt"] == 5
    months = {m["label"]: m for y in r["years"] for m in y["months"]}
    assert months["Mar 1986"].get("beforeBirth") is True and not months["Apr 1986"].get("beforeBirth")
