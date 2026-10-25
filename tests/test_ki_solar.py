"""The solar-degree Ki stack: every level read from the Sun's longitude past Lichun.

Doctrine (2026-10-25):
- A day is 1° of the Sun past the Lichun gate (315°); a month is 30 of them; an hour is 5′.
- Every level opens on an Earth number and the count never resets: lock = flow.
- Month 2 opens day 8 (so every Lichun opens day 8, since 360 ≡ 0); day 8 opens hour 5.
- A great age is 24° of precession (1,728 years); the vernal point reached 24° past the
  Lahiri zero in 2010, so Lichun 2010 opened great age 8, Ki Age 5 and great year 2 together.

Run: .venv/bin/python -m pytest tests/test_ki_solar.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ki_solar import (  # noqa: E402
    DAY_OPENING_AT_LICHUN, dt_to_jd, hour_opening, jd_to_dt, lichun_instant, next_change_jd,
    solar_stack, solar_stack_at,
)

NY = ZoneInfo("America/New_York")


def numbers(jd):
    s = solar_stack(jd)
    return [s["numbers"][k] for k in ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")]


def test_lichun_2010_is_the_full_staircase():
    assert numbers(lichun_instant(2010) + 1 / 86400) == [8, 5, 2, 8, 2, 8, 5]


def test_lichun_2022_only_the_great_year_turns():
    assert numbers(lichun_instant(2022) + 1 / 86400) == [8, 5, 1, 5, 2, 8, 5]


def test_every_lichun_opens_day_8_and_hour_5():
    for y in (1986, 2010, 2022, 2026, 2027, 2058):
        s = solar_stack(lichun_instant(y) + 1 / 86400)
        assert (s["numbers"]["day"], s["numbers"]["hour"]) == (8, 5), y
        assert s["numbers"]["month"] in (2, 5, 8), y


def test_openings():
    assert DAY_OPENING_AT_LICHUN == 8
    assert [hour_opening(d) for d in range(1, 10)] == [2, 5, 8, 2, 5, 8, 2, 5, 8]


def test_now_reading_2026_10_25():
    s = solar_stack_at(datetime(2026, 10, 25, 14, 7, tzinfo=NY))
    assert numbers(s["jd"]) == [8, 5, 1, 1, 9, 3, 4]
    assert (s["month_index"], s["degree_day"], s["degree_hour"]) == (8, 18, 5)
    assert abs(s["sun_longitude"] - 212.343) < 0.002
    start, end = (jd_to_dt(j, NY) for j in s["spans"]["day"])
    assert (start.strftime("%m-%d %H:%M"), end.strftime("%m-%d %H:%M")) == ("10-25 05:50", "10-26 05:55")
    assert 1.9 < (s["spans"]["hour"][1] - s["spans"]["hour"][0]) * 24 < 2.1


def test_hours_descend_by_one_through_a_whole_degree_day():
    s = solar_stack_at(datetime(2026, 10, 25, 14, 7, tzinfo=NY))
    jd0, jd1 = s["spans"]["day"]
    seen = []
    jd = jd0 + 1 / 1440
    while jd < jd1:
        h = solar_stack(jd)["numbers"]["hour"]
        if not seen or seen[-1] != h:
            seen.append(h)
        jd += 1 / 1440
    assert len(seen) == 12
    assert all((a - 2) % 9 + 1 == b for a, b in zip(seen, seen[1:]))


def test_midnight_is_not_a_boundary():
    before = solar_stack_at(datetime(2026, 10, 25, 23, 59, tzinfo=NY))["numbers"]
    after = solar_stack_at(datetime(2026, 10, 26, 0, 1, tzinfo=NY))["numbers"]
    assert before == after


def test_day_count_flows_through_the_month_seam_and_opens_on_earth():
    # Oct 2026 (month 9) opens when the Sun reaches 225°, Oct 8 02:29 New York.
    seam = solar_stack_at(datetime(2026, 10, 8, 3, 0, tzinfo=NY))["spans"]["month"][0]
    before = solar_stack(seam - 1 / 86400)["numbers"]
    after = solar_stack(seam + 1 / 86400)["numbers"]
    assert (before["month"], after["month"]) == (1, 9)
    assert after["day"] in (2, 5, 8)
    assert (before["day"] - 2) % 9 + 1 == after["day"]


def test_day_count_flows_through_lichun():
    seam = lichun_instant(2027)
    before = solar_stack(seam - 1 / 86400)["numbers"]
    after = solar_stack(seam + 1 / 86400)["numbers"]
    assert (before["year"], after["year"], after["month"], after["day"], after["hour"]) == (1, 9, 5, 8, 5)
    assert (before["day"] - 2) % 9 + 1 == after["day"]
    assert (before["hour"] - 2) % 9 + 1 == after["hour"]


def test_next_change_instants():
    jd = dt_to_jd(datetime(2026, 10, 25, 14, 7, tzinfo=NY))
    s = solar_stack(jd)
    assert next_change_jd(jd, "hour", 1) == s["spans"]["hour"][1]
    assert next_change_jd(jd, "day", 1) == s["spans"]["day"][1]
    assert jd_to_dt(next_change_jd(jd, "day", 2), NY).strftime("%m-%d %H:%M") == "10-27 06:00"
    assert jd_to_dt(next_change_jd(jd, "month", 1), NY).strftime("%Y-%m-%d") == "2026-11-07"
    assert jd_to_dt(next_change_jd(jd, "year", 1), NY).strftime("%Y-%m-%d") == "2027-02-03"
    # the 12th hour change from now is the next degree-day's first hour, so the day turns with it
    assert solar_stack(next_change_jd(jd, "hour", 12 - s["degree_hour"] + 1) + 1 / 86400)["numbers"]["day"] == 2


def test_great_year_numbers_after_the_2010_seam():
    years = {2009: 3, 2010: 2, 2021: 2, 2022: 1, 2033: 1, 2034: 9, 1986: 4}
    for y, g in years.items():
        assert solar_stack(lichun_instant(y) + 30)["numbers"]["great_year"] == g, y


def test_great_age_is_twelve_ki_ages():
    from ki_levels import global_great_age, global_ki_age
    assert solar_stack(lichun_instant(2010) + 30)["numbers"]["ki_age"] == 5
    assert solar_stack(lichun_instant(2154) + 30)["numbers"]["ki_age"] == 4
    # 3738 is past the installed ephemeris files, so the far seam is checked on the arithmetic alone
    assert (global_great_age(3737), global_great_age(3738)) == (8, 7)
    assert global_ki_age(3738) in (2, 5, 8)


def test_dt_roundtrip():
    t = datetime(2026, 10, 25, 14, 7, tzinfo=NY)
    assert abs(jd_to_dt(dt_to_jd(t), NY) - t) < timedelta(seconds=1)
