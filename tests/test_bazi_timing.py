"""BaZi luck pillars (大運) and time pillars (流年 / 流月 / 流日 / 流時).

Run: .venv/bin/python -m pytest tests/test_bazi_timing.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bazi import (BirthData, birth_from_chart, luck_direction, luck_pillars, natal_pillars,  # noqa: E402
                  time_against_natal, time_pillars)

NY = ZoneInfo("America/New_York")
BETSY = birth_from_chart(json.load(open("charts/betsy.json")))
CHRIS = birth_from_chart(json.load(open("charts/chris.json")))


def test_direction_rule():
    assert luck_direction("male", "yang") == "forward"
    assert luck_direction("female", "yang") == "backward"
    assert luck_direction("male", "yin") == "backward"
    assert luck_direction("female", "yin") == "forward"


def test_betsy_luck_start():
    # female, 戊 yang → backward; 立冬 1978-11-07 13:34 EST, birth 11-20 22:31 → 13.4 days → 4 years 5 months
    natal = natal_pillars(BETSY)
    l = luck_pillars(BETSY, natal)
    assert l["direction"] == "backward"
    assert l["start_age"]["years"] == 4 and 4 <= l["start_age"]["months"] <= 6
    assert [p["cn"] for p in l["pillars"][:3]] == ["壬戌", "辛酉", "庚申"]
    assert l["pillars"][0]["start_date"].startswith("1983-0")
    assert l["pillars"][1]["start_date"].startswith("1993-0")
    assert l["pillars"][0]["ten_god_stem"] == "七殺"              # 壬 against 丙
    assert len(l["pillars"]) == 10


def test_chris_luck_forward():
    # male, 丙 yang → forward; 立夏 1986-05-05 15:30 EDT, birth 05-01 14:35 → 4.04 days → 1 year 4 months
    natal = natal_pillars(CHRIS)
    l = luck_pillars(CHRIS, natal)
    assert l["direction"] == "forward"
    assert l["start_age"]["years"] == 1 and 3 <= l["start_age"]["months"] <= 5
    assert [p["cn"] for p in l["pillars"][:3]] == ["癸巳", "甲午", "乙未"]


def test_current_luck_pillar():
    natal = natal_pillars(CHRIS)
    l = luck_pillars(CHRIS, natal, at=datetime(2026, 11, 11, 12, 0, tzinfo=NY))
    # start ≈ 1987-09; pillars every 10 years: 2017-09 → 2027-09 is the fourth pillar 丙申
    assert l["current"]["cn"] == "丙申" and l["current"]["index_in_sequence"] == 4


def test_missing_gender_raises():
    b = BirthData(datetime(2012, 7, 12, 0, 35, tzinfo=NY), 39.8, -77.2, "America/New_York", None, "kate")
    with pytest.raises(ValueError, match="gender"):
        luck_pillars(b, natal_pillars(b))


def test_time_pillars_2026_11_11():
    p = time_pillars(datetime(2026, 11, 11, 12, 0, tzinfo=NY))
    assert [p[k]["cn"] for k in ("year", "month", "day", "hour")] == ["丙午", "己亥", "己丑", "庚午"]


def test_time_against_natal_reports_ten_gods_and_interactions():
    natal = natal_pillars(BETSY)
    luck = luck_pillars(BETSY, natal, at=datetime(2026, 11, 11, 12, 0, tzinfo=NY))
    t = time_against_natal(datetime(2026, 11, 11, 12, 0, tzinfo=NY), natal, luck)
    assert t["pillars"]["year"]["cn"] == "丙午"
    assert t["ten_gods"]["year"]["stem"] == "比肩"                 # 丙 against 丙
    assert t["ten_gods"]["month"]["stem"] == "傷官"                # 己 against 丙
    assert t["luck"]["cn"] == luck["current"]["cn"]
    # 2026 is 午; Betsy's natal year is 午: 午午 self punishment between the annual pillar and natal year
    assert any(i["type"] == "self_punishment" and {m[0] for m in i["members"]} == {"year", "year_now"}
               for i in t["interactions"])
    assert all(any(m[0].endswith("_now") or m[0] == "luck" for m in i["members"]) for i in t["interactions"])
