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
    with pytest.raises(ValueError, match="outside the ephemeris") as ei:
        E.period("year", -3000, None)
    assert "year -3000" in str(ei.value)


def test_great_age_period_has_no_end_inside_the_ephemeris():
    p = E.period_at("great_age", AT, 5)
    assert p.number == 2 and p.start.year == 2010
    assert p.end is None and p.fig is None


def test_native_figure_and_ji_9_nov_2026():
    n = E.natal_of("1986-05-01")
    m = E.period_at("month", datetime(2026, 11, 9, 12), n["year"])
    nat = E.native_figure(m, n["month"])
    assert (m.fig.n, nat.n, E.ji_lines(m, n["month"])) == (36, 11, [2])
    d = E.period_at("day", datetime(2026, 11, 9, 12), n["year"])
    assert (d.fig.n, E.native_figure(d, n["month"]).n, E.ji_lines(d, n["month"])) == (20, 53, [3])


def test_native_figure_global_profile_has_no_ji():
    m = E.period_at("month", datetime(2026, 11, 9, 12), None)
    assert E.native_figure(m, 9) is None
    assert E.ji_lines(m, 9) == []


def test_shi_is_the_next_period():
    n = E.natal_of("1986-05-01")
    m = E.period_at("month", datetime(2026, 11, 9, 12), n["year"])
    nxt = E.period("month", m.idx + 1, n["year"])
    s = E.shi(m)
    assert s["to"] == nxt.number and s["fig"] == nxt.fig
    assert s["lines"] == E.moving(m.fig.lines, nxt.fig.lines)
    assert s["start"] == nxt.start and s["end"] == nxt.end


def test_palace_2026_global_1():
    pal = E.palace(1, 9)
    assert pal["five_yellow"] == 9 and pal["broken"] == 1
    assert pal["own"] == 9 and pal["opposite"] == 1 and pal["coincides"] is True
    assert [c["n"] for c in pal["cells"]] == [9, 5, 7, 8, 1, 3, 4, 6, 2]
    assert pal["cells"][4]["star"] == "White Water" and pal["cells"][4]["dir"] == "center"


def test_palace_month_global_8_and_center_five():
    pal = E.palace(8, 2)
    assert pal["five_yellow"] == 2 and pal["broken"] == 8 and pal["coincides"] is True
    assert all(c["n"] == E.ki(c["home"] + 3) for c in pal["cells"])
    assert E.palace(1, None)["own"] is None
    c = E.palace(5, None); assert c["five_yellow"] == 5 and c["broken"] is None


def test_shi_past_the_ephemeris_keeps_the_next_number():
    p = E.period_at("great_age", AT, 5)
    s = E.shi(p)
    assert s["to"] == 3 and s["fig"] is None and s["lines"] == [] and s["start"] == p.end and s["end"] is None
