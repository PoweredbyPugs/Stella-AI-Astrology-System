"""The Octave page's engine on Stella's clock: periods, resolve, figures, line figures, element relation.

Run: .venv/bin/python -m pytest tests/test_octave_engine.py
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import octave_engine as E  # noqa: E402

NATAL = "1986-05-01"
AT = datetime(2026, 11, 11, 12, 22)      # America/New_York


def test_stack_matches_the_page():
    p = E.period_at("hour", AT, E.natal_of(NATAL)["year"])
    assert [p.gstack[L] for L in E.LEVELS] == [8, 5, 1, 1, 8, 4, 8]
    assert [p.pstack[L] for L in E.LEVELS] == [2, 5, 9, 9, 2, 6, 2]


def test_natal_triple():
    n = E.natal_of(NATAL)
    assert (n["year"], n["month"], n["pm"]) == (5, 9, 1)   # 1986 → 5 (ki(2027 − 1986)); the spec's "1986 → 6" is a slip, the stack 2.5.9.9.2.6.2 only holds with 5


def test_resolve_five_inherits_and_all_five_is_no_figure():
    r = E.resolve({"great_age": 8, "ki_age": 5, "great_year": 5}, "great_year")
    assert (r.source, r.inherited, r.element) == (8, "great_age", "Earth")
    r5 = E.resolve({"great_age": 5, "ki_age": 5}, "ki_age")
    assert r5.lines is None and E.figure({"great_age": 5, "ki_age": 5}, "ki_age") is None


def test_month_figure_9_nov_2026():
    # natal 5 (the brief's 6 is the same "1986 → 6" slip; natal 6 gives Zhen over Kan = 40)
    p = E.period_at("month", datetime(2026, 11, 9, 12), E.natal_of(NATAL)["year"])
    assert p.fig.n == 36 and p.fig.name == "Darkening of the Light"


def test_line_figures_fixed_where_no_five():
    R = lambda k: E.resolve({"year": k}, "year")  # noqa: E731
    assert E.line_figure(R(1), R(4))["fig"].n == 59
    assert E.line_figure(R(4), R(2))["fig"].n == 46
    assert E.line_figure(R(2), R(8))["fig"].n == 23
    assert E.line_figure(R(7), R(1))["fig"].n == 60
    assert E.line_figure(R(8), R(1))["moving"] == [5, 6]       # Gen → Kan: 39 against 52


def test_triforce():
    assert (E.triforce(3).n, E.triforce(6).n, E.triforce(9).n, E.triforce(4)) == (51, 1, 30, None)


def test_relation_cycles():
    assert E.relation("Water", "Water") == "resonates"
    assert E.relation("Water", "Wood") == "feeds"
    assert E.relation("Water", "Metal") == "fed_by"
    assert E.relation("Water", "Fire") == "controls"
    assert E.relation("Water", "Earth") == "controlled_by"
    assert E.relation("Earth", "Fire") == "fed_by" and E.relation("Wood", "Earth") == "controls"
    assert E.relation(None, "Earth") is None


def test_period_outside_ephemeris_raises():
    with pytest.raises(ValueError):
        E.period("year", -3000, None)
