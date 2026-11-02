"""get_ki_periods: dated octaves and the present at every level, for the Octave Calendar.

Fixtures are the live stack at 2026-11-02 17:48 New York for natal 1986-05-01 (personal
2.5.9.9.1.6.5), and the boundaries get_ki_changes / get_daily_ki report at that instant.

Run: .venv/bin/python -m pytest tests/test_ki_periods.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stella_server  # noqa: E402
from ki_solar import LEVELS, dt_to_jd, parse_target, period_index, period_start_jd, solar_stack  # noqa: E402

BIRTH = "1986-05-01"
AT = "2026-11-02T17:48"


def call(level, target=AT, birth=BIRTH):
    return json.loads(asyncio.run(stella_server.get_ki_periods(birth_date=birth, level=level, target_date=target)))


def test_present_matches_daily_ki_stack():
    out = call("all")["levels"]
    assert [out[l]["personal"] for l in LEVELS] == [2, 5, 9, 9, 1, 6, 5]
    assert [out[l]["global"] for l in LEVELS] == [8, 5, 1, 1, 9, 4, 5]
    assert all(0 <= out[l]["elapsed"] < 1 for l in LEVELS)


def test_present_spans_match_ki_changes():
    out = call("all")["levels"]
    assert out["day"]["start"].startswith("2026-11-02T05:08") and out["day"]["end"].startswith("2026-11-03T05:06")
    assert out["hour"]["start"].startswith("2026-11-02T17:07") and out["hour"]["end"].startswith("2026-11-02T19:07")
    assert out["month"]["end"].startswith("2026-11-07T04:52")
    assert out["year"]["end"].startswith("2027-02-03T20:46")
    assert out["great_year"]["end"].startswith("2034-02-03")


def test_spans_agree_with_solar_stack():
    jd = dt_to_jd(parse_target(AT))
    s = solar_stack(jd)
    for lvl in ("year", "month", "day", "hour"):
        idx = period_index(jd, lvl)
        assert abs(period_start_jd(lvl, idx) - s["spans"][lvl][0]) < 1 / 86400, lvl
        assert abs(period_start_jd(lvl, idx + 1) - s["spans"][lvl][1]) < 1 / 86400, lvl


def test_every_octave_runs_personal_1_to_9_and_holds_the_target():
    for lvl in LEVELS:
        ps = call(lvl)["periods"]
        assert [p["personal"] for p in ps] == list(range(1, 10)), lvl
        assert sum(p["contains_target"] for p in ps) == 1, lvl


def test_octave_periods_are_contiguous():
    for lvl in ("hour", "day", "month", "year", "great_year"):
        ps = call(lvl)["periods"]
        for a, b in zip(ps, ps[1:]):
            assert a["end"] == b["start"], lvl


def test_global_octave_without_birth_date_descends_from_1():
    ps = call("day", birth=None)["periods"]
    assert [p["global"] for p in ps] == [1, 9, 8, 7, 6, 5, 4, 3, 2]
    assert all(p["personal"] is None for p in ps)


def test_far_gates_give_the_ki_year_when_no_instant():
    out = call("all")["levels"]["great_age"]
    assert out["start_ki_year"] == 2010 and out["end"] is None and 0 < out["elapsed"] < 0.01
    ps = call("great_age")["periods"]
    assert ps[2]["start"] is None and ps[2]["start_ki_year"] == 3738


def test_unknown_level():
    assert "error" in call("week")
