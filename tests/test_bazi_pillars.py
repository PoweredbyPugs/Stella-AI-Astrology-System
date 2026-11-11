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


# ── Task 2: true solar time, birth data, chart loading ──────────────────────

import json  # noqa: E402

from bazi import BirthData, apparent_solar_time, birth_from_chart, natal_pillars  # noqa: E402


def test_apparent_solar_time_betsy():
    # EST, lon -77.0269 → -8.1 min; EoT 1978-11-20 ≈ +14.3 min; result ≈ 22:37
    t, parts = apparent_solar_time(datetime(1978, 11, 20, 22, 31, tzinfo=NY), -77.0269)
    assert abs(parts["longitude_minutes"] - (-8.1)) < 0.2
    assert 13.5 < parts["equation_minutes"] < 15.0
    assert t.hour == 22 and 36 <= t.minute <= 38


def test_dst_uses_standard_meridian():
    # Chris 14:35 EDT: standard offset -5 → meridian -75°, not -60°
    _, parts = apparent_solar_time(datetime(1986, 5, 1, 14, 35, tzinfo=NY), -81.3792)
    assert parts["standard_offset_hours"] == -5
    assert abs(parts["longitude_minutes"] - (-25.5)) < 0.2


def test_solar_time_crosses_day_boundary():
    # 1986-11-20 22:50 EST at lon -70.0: +20 min longitude, EoT ≈ +14 → ~23:24 apparent
    b = BirthData(datetime(1986, 11, 20, 22, 50, tzinfo=NY), 42.0, -70.0, "America/New_York", "male", "test")
    solar = natal_pillars(b)
    clock = natal_pillars(b, true_solar_time=False)
    assert solar["pillars"]["day"]["cn"] != clock["pillars"]["day"]["cn"]
    assert solar["settings"]["true_solar_time"] is True and not solar["warnings"]


def test_birth_from_chart_two_shapes():
    betsy = birth_from_chart(json.load(open("charts/betsy.json")))
    assert betsy.gender == "female" and betsy.lon == -77.0269 and betsy.local.hour == 22
    assert betsy.local.minute == 31 and betsy.tz == "America/New_York"
    chris = birth_from_chart(json.load(open("charts/chris.json")))
    assert chris.gender == "male" and chris.local.minute == 35 and chris.tz == "America/New_York"
    assert chris.lat == 28.5383


def test_birth_from_chart_gender_override_and_absence():
    kate = birth_from_chart(json.load(open("charts/kate.json")))
    assert kate.gender is None
    assert birth_from_chart(json.load(open("charts/kate.json")), gender="F").gender == "female"


def test_no_coordinates_warns_and_uses_clock_time():
    b = BirthData(datetime(1995, 8, 25, 21, 3, tzinfo=NY), None, None, "America/New_York", None, "test")
    r = natal_pillars(b)
    assert r["warnings"] and "clock time" in r["warnings"][0]
    assert r["pillars"]["day"]["cn"] == pillars_from_civil(b.local)["day"]["cn"]


# ── Review fixes: LMT fallback, charts without a zone, overrides ────────────

from bazi import longitude_from_sidereal  # noqa: E402


def test_lmt_fallback_rebuilds_offset_from_longitude():
    # Buffalo 1850: zoneinfo gives New York LMT (-4:56); the birth place's LMT at lon -78.75 is -5:15
    b = BirthData(datetime(1850, 6, 1, 12, 0, tzinfo=NY), 42.9, -78.75, "America/New_York", "male", "test")
    r = natal_pillars(b)
    assert any("local mean time" in w for w in r["warnings"])
    assert r["clock_time"].endswith("-05:15")


def test_longitude_from_sidereal_times():
    assert abs(longitude_from_sidereal("07:30:08", "02:22:02") - (-77.0269)) < 0.01   # Betsy


def test_chart_without_zone_recovers_longitude_and_infers_zone():
    k = birth_from_chart(json.load(open("charts/kelsea.json")))
    assert abs(k.lon - (-122.25)) < 0.1 and k.tz is None
    assert k.local.utcoffset().total_seconds() == -8 * 3600         # zone inferred from longitude
    assert any("inferred" in n for n in k.notes)


def test_chart_overrides_for_zone_and_place():
    k = birth_from_chart(json.load(open("charts/kelsea.json")), timezone="America/Los_Angeles", lat=37.8, lon=-122.4)
    assert k.tz == "America/Los_Angeles" and k.lon == -122.4 and k.local.utcoffset().total_seconds() == -7 * 3600
    assert not any("inferred" in n for n in k.notes)


# ── More reference charts (buyiju.com, 2026-11-11, clock time) ───────────────

def test_sydney_southern_hemisphere_clock_pillars():
    p = pillars_from_civil(datetime(1990, 1, 15, 10, 0, tzinfo=ZoneInfo("Australia/Sydney")))
    assert cns(p) == ["己巳", "丁丑", "庚辰", "辛巳"]


def test_1960_clock_pillars():
    p = pillars_from_civil(datetime(1960, 8, 8, 3, 0, tzinfo=SH))
    assert cns(p) == ["庚子", "甲申", "戊辰", "甲寅"]


# ── Second source: china95.net (2026-11-11) ──────────────────────────────────

def test_china95_true_solar_time_moves_hour():
    # 2000-06-01 09:05 Beijing time at 105°E: china95 gives the 巳 hour on clock time and the 辰 hour with 真太阳时
    b = BirthData(datetime(2000, 6, 1, 9, 5, tzinfo=SH), 30.0, 105.0, "Asia/Shanghai", "male", "test")
    assert natal_pillars(b, true_solar_time=False)["pillars"]["hour"]["cn"] == "辛巳"
    assert natal_pillars(b)["pillars"]["hour"]["cn"] == "庚辰"
    assert cns(natal_pillars(b)["pillars"])[:3] == ["庚辰", "辛巳", "庚寅"]


def test_lixia_2000_instant_from_ephemeris():
    # Swiss Ephemeris: 立夏 2000 (Sun at 45°) is 2000-05-05 12:50 Beijing. china95 shows 13:19, its own approximation.
    from ki_calendar import boundaries_jd, jd_to_local
    lixia = jd_to_local(boundaries_jd(2000)[3]).astimezone(SH)
    assert lixia.strftime("%Y-%m-%d %H:%M") == "2000-05-05 12:50"
