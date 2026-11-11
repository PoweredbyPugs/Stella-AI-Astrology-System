"""BaZi four pillars from a civil instant, and true solar time.

Reference pillars from buyiju.com (2026-11-11, clock time, no solar correction):
  Betsy 1978-11-20 22:31 New York: 戊午 癸亥 丙戌 己亥
  Chris 1986-05-01 14:35 New York: 丙寅 壬辰 乙巳 癸未
  2000-01-01 00:30 Shanghai:        己卯 丙子 戊午 壬子
Day anchors: 1900-01-01 甲戌; Mao Zedong 1893-12-26 辰時: 癸巳 甲子 丁酉 甲辰.

Run: .venv/bin/python -m pytest tests/test_bazi_pillars.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bazi import day_index_from_jdn, pillars_from_civil, sexagenary  # noqa: E402

NY = ZoneInfo("America/New_York")
SH = ZoneInfo("Asia/Shanghai")


def cns(p):
    return [p[k]["cn"] for k in ("year", "month", "day", "hour")]


def test_day_anchors():
    assert sexagenary(day_index_from_jdn(2415021))["cn"] == "甲戌"
    assert sexagenary(day_index_from_jdn(2451545))["cn"] == "戊午"


def test_sexagenary_carries_pinyin_and_nayin():
    s = sexagenary(0)
    assert s["cn"] == "甲子" and s["pinyin"] == "jia zi" and s["nayin"] == "海中金"
    assert s["stem"]["element"] == "wood" and s["branch"]["animal"] == "Rat"


def test_betsy_clock_pillars():
    p = pillars_from_civil(datetime(1978, 11, 20, 22, 31, tzinfo=NY))
    assert cns(p) == ["戊午", "癸亥", "丙戌", "己亥"]


def test_chris_clock_pillars():
    p = pillars_from_civil(datetime(1986, 5, 1, 14, 35, tzinfo=NY))
    assert cns(p) == ["丙寅", "壬辰", "乙巳", "癸未"]


def test_y2k_pillars():
    p = pillars_from_civil(datetime(2000, 1, 1, 0, 30, tzinfo=SH))
    assert cns(p) == ["己卯", "丙子", "戊午", "壬子"]


def test_mao_pillars():
    p = pillars_from_civil(datetime(1893, 12, 26, 8, 0, tzinfo=SH))
    assert cns(p) == ["癸巳", "甲子", "丁酉", "甲辰"]


def test_nayin_rows():
    betsy = pillars_from_civil(datetime(1978, 11, 20, 22, 31, tzinfo=NY))
    assert [betsy[k]["nayin"] for k in ("year", "month", "day", "hour")] == ["天上火", "大海水", "屋上土", "平地木"]
    chris = pillars_from_civil(datetime(1986, 5, 1, 14, 35, tzinfo=NY))
    assert [chris[k]["nayin"] for k in ("year", "month", "day", "hour")] == ["爐中火", "長流水", "佛燈火", "楊柳木"]


def test_year_turns_at_exact_lichun():
    from ki_calendar import jd_to_local, lichun_jd
    lichun = jd_to_local(lichun_jd(2024))
    assert lichun.date().isoformat() == "2024-02-04"
    before = pillars_from_civil(lichun - timedelta(minutes=1))
    after = pillars_from_civil(lichun + timedelta(minutes=1))
    assert before["year"]["cn"] == "癸卯" and after["year"]["cn"] == "甲辰"


def test_month_turns_at_exact_jie():
    from ki_calendar import boundaries_jd, jd_to_local
    lidong = jd_to_local(boundaries_jd(2026)[9])  # 立冬 opens the 亥 month (index 9 from 寅)
    assert lidong.date().isoformat() in ("2026-11-06", "2026-11-07")
    before = pillars_from_civil(lidong - timedelta(minutes=1))
    after = pillars_from_civil(lidong + timedelta(minutes=1))
    assert before["month"]["cn"] == "戊戌" and after["month"]["cn"] == "己亥"


def test_day_boundary_2300_moves_day():
    p = pillars_from_civil(datetime(1986, 5, 1, 23, 30, tzinfo=NY))
    assert p["day"]["cn"] == "丙午" and p["hour"]["cn"] == "戊子"


def test_day_boundary_midnight_keeps_day_but_next_stem():
    p = pillars_from_civil(datetime(1986, 5, 1, 23, 30, tzinfo=NY), day_boundary="midnight")
    assert p["day"]["cn"] == "乙巳" and p["hour"]["cn"] == "戊子"


def test_early_zi_after_midnight_is_same_day_under_both_rules():
    for rule in ("23:00", "midnight"):
        p = pillars_from_civil(datetime(1986, 5, 2, 0, 30, tzinfo=NY), day_boundary=rule)
        assert p["day"]["cn"] == "丙午" and p["hour"]["cn"] == "戊子", rule


def test_unknown_day_boundary_rejected():
    with pytest.raises(ValueError):
        pillars_from_civil(datetime(1986, 5, 1, 12, 0, tzinfo=NY), day_boundary="noon")
