"""The sky window: events, the sky at an instant, releasing over a window, the whole reply.

Pure functions, no MCP, no network. The ephemeris files are not mounted here, so pyswisseph
runs Moshier: a minute on instants, a hundredth of a degree on longitudes.

Run: .venv/bin/python -m pytest tests/test_sky.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import swisseph as swe  # noqa: E402

import sky  # noqa: E402
from ephemeris import PLANET_IDS, _get_lon_speed, _load_chart  # noqa: E402

ORLANDO = (28.5383, -81.3792)
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
MINUTE = 1 / 1440


def jd(s):
    return sky.parse_instant(s)


def minutes_apart(a, b):
    return abs(jd(a) - jd(b)) * 1440


def instants(obj, out=None):
    """Every ISO instant string anywhere in a reply."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for v in obj.values():
            instants(v, out)
    elif isinstance(obj, list):
        for v in obj:
            instants(v, out)
    elif isinstance(obj, str) and ISO.match(obj):
        out.append(obj)
    return out


# ── Instants ──

def test_parse_instant_honors_offsets_and_reads_naive_as_new_york():
    assert sky.iso_utc(jd("2026-11-12T03:30:00Z")) == "2026-11-12T03:30:00Z"
    assert sky.iso_utc(jd("2026-11-11T22:30:00-05:00")) == "2026-11-12T03:30:00Z"
    assert sky.iso_utc(jd("2026-11-11T22:30:00")) == "2026-11-12T03:30:00Z"
    assert sky.iso_utc(jd("2026-11-12")) == "2026-11-12T05:00:00Z"        # a bare date is its midnight
    assert sky.iso_utc(jd("2026-07-01")) == "2026-07-01T04:00:00Z"        # in daylight time


# ── Events ──

def test_march_equinox_is_a_turning_and_the_suns_ingress_into_aries():
    ev = sky.sky_events(jd("2026-03-19"), jd("2026-03-22"), ["turnings", "ingresses"], ["Sun"])
    assert [t["kind"] for t in ev["turnings"]] == ["spring_equinox"]
    equinox = ev["turnings"][0]
    assert minutes_apart(equinox["at"], "2026-03-20T14:46:00Z") <= 2
    assert equinox["longitude"] < 0.01 or equinox["longitude"] > 359.99
    assert len(ev["ingresses"]) == 1
    ing = ev["ingresses"][0]
    assert (ing["planet"], ing["from_sign"], ing["to_sign"], ing["retrograde"]) == ("Sun", "Pisces", "Aries", False)
    assert minutes_apart(ing["at"], equinox["at"]) <= 1


def test_new_moon_of_november_2026():
    ev = sky.sky_events(jd("2026-11-08"), jd("2026-11-10"), ["lunations"])
    assert len(ev["lunations"]) == 1
    new = ev["lunations"][0]
    assert new["kind"] == "new"
    assert minutes_apart(new["at"], "2026-11-09T07:02:00Z") <= 3
    assert new["sign"] == "Scorpio" and abs(new["degree"] - 16.9) < 0.1


def test_full_moon_of_march_2026_is_the_lunar_eclipse():
    ev = sky.sky_events(jd("2026-03-01"), jd("2026-03-05"), ["lunations", "eclipses"])
    fulls = [l for l in ev["lunations"] if l["kind"] == "full"]
    assert len(fulls) == 1 and fulls[0]["sign"] == "Virgo"
    lunar = [e for e in ev["eclipses"] if e["type"] == "Lunar"]
    assert len(lunar) == 1 and lunar[0]["sign"] == "Virgo"
    assert lunar[0]["natal_contacts"] is None  # no chart
    assert minutes_apart(fulls[0]["at"], lunar[0]["at"]) <= 60


def test_moon_enters_capricorn_and_the_void_span_ends_there():
    ev = sky.sky_events(jd("2026-11-12"), jd("2026-11-13"), ["ingresses", "void"], ["Moon"])
    ing = [i for i in ev["ingresses"] if i["to_sign"] == "Capricorn"]
    assert len(ing) == 1 and ing[0]["from_sign"] == "Sagittarius"
    assert minutes_apart(ing[0]["at"], "2026-11-12T20:27:00Z") <= 2
    spans = [v for v in ev["void"] if v["to_sign"] == "Capricorn"]
    assert len(spans) == 1
    v = spans[0]
    assert minutes_apart(v["end"], ing[0]["at"]) <= 1
    assert v["from_sign"] == "Sagittarius"
    assert v["last_aspect"] == "Moon Trine Jupiter"
    assert v["start"] < v["end"]


def test_annular_solar_eclipse_of_february_2027():
    ev = sky.sky_events(jd("2027-02-01"), jd("2027-02-28"), ["eclipses"])
    solar = [e for e in ev["eclipses"] if e["type"] == "Solar"]
    assert len(solar) == 1
    e = solar[0]
    assert e["subtype"] == "Annular"
    assert e["at"].startswith("2027-02-06")
    assert e["sign"] == "Aquarius" and abs(e["degree"] - 17.6) < 0.1


def test_mercury_station_changes_the_sign_of_its_speed():
    ev = sky.sky_events(jd("2026-10-01"), jd("2026-12-31"), ["stations"], ["Mercury"])
    mercury = [s for s in ev["stations"] if s["planet"] == "Mercury"]
    assert mercury, "no Mercury station in the autumn of 2026"
    for s in mercury:
        at = jd(s["at"])
        before = _get_lon_speed(at - 1, PLANET_IDS["Mercury"])[1]
        after = _get_lon_speed(at + 1, PLANET_IDS["Mercury"])[1]
        assert (before < 0) != (after < 0)
        assert s["kind"] == ("retrograde" if after < 0 else "direct")
        assert s["sign"] in sky.SIGN_NAMES and 0 <= s["degree"] < 30


def test_unasked_kinds_are_empty_and_transits_null_without_a_chart():
    ev = sky.sky_events(jd("2026-11-12"), jd("2026-11-13"), ["moon_gates"])
    assert set(ev) == set(sky.KINDS)
    assert ev["transits"] is None
    assert ev["lunations"] == [] and ev["stations"] == []
    assert all(g["degree"] == 15 for g in ev["moon_gates"])


# ── The sky at an instant ──

def test_ascendant_at_orlando_is_leo_with_its_span():
    at = jd("2026-11-12T03:30:00Z")
    sk = sky.sky_at(at, *ORLANDO)
    asc = sk["ascendant"]
    assert asc["sign"] == "Leo" and asc["degree"] < 3
    assert asc["entered_at"] < sk["at"] < asc["leaves_at"]
    after = jd(asc["leaves_at"]) + 1 / 86400
    assert sky._sign_name(sky._asc_lon(after, *ORLANDO)) == "Virgo"
    before = jd(asc["entered_at"]) - 1 / 86400
    assert sky._sign_name(sky._asc_lon(before, *ORLANDO)) == "Cancer"
    assert sk["transits"] is None and sk["profection"] is None
    assert [p["planet"] for p in sk["planets"]] == sky.PLANETS
    moon = sk["moon"]
    assert moon["phase"] in sky.PHASES and 0 <= moon["illumination"] <= 1
    assert abs(moon["age_days"] - moon["phase_angle"] / 360 * sky.SYNODIC_MONTH) < 0.01


def test_transits_and_profection_for_chris():
    chart = _load_chart("chris")
    sk = sky.sky_at(jd("2026-11-12T03:30:00Z"), chart=chart)
    assert sk["ascendant"] is None
    transits = sk["transits"]
    assert transits and transits == sorted(transits, key=lambda t: t["orb"])
    saturn = [t for t in transits if t["transit_planet"] == "Saturn" and t["natal_point"] == "Saturn"
              and t["aspect"] == "Trine"]
    assert len(saturn) == 1
    assert saturn[0]["orb"] < 0.6 and saturn[0]["applying"] is True and saturn[0]["exact"] is True
    assert saturn[0]["exact_at"] is not None and saturn[0]["exact_at"] > sk["at"]
    for t in transits:
        assert 0 <= t["orb"] <= t["orb_max"]
        assert 0 <= t["strength"] <= 1
        assert t["aspect"] in sky.ASPECTS
    for t in transits:
        if t["transit_planet"] == "Moon":
            assert t["orb_max"] == (2.0 if t["aspect"] == "Sextile" else 3.0)
    assert sk["profection"] == {"age": 40, "house": 5, "sign": "Capricorn", "lord_of_year": "Saturn"}


def test_orb_cap_and_sextile_share():
    assert sky._orb_max("Moon", "Trine", 3.0) == 3.0
    assert sky._orb_max("Moon", "Sextile", 3.0) == 2.0
    assert sky._orb_max("Mercury", "Square", 3.0) == 2.0
    assert sky._orb_max("Saturn", "Conjunction", 1.0) == 1.0


# ── Releasing over a window ──

def test_zr_window_fortune_level_2_for_chris():
    chart = _load_chart("chris")
    z = sky.zr_window(chart, jd("2026-01-01"), jd("2027-01-01"), "fortune", [2])
    periods = z["periods"]
    assert periods and periods == z["levels"]["2"]
    for a, b in zip(periods, periods[1:]):
        assert a["end"] == b["start"]
    now = "2026-11-11T12:00:00Z"
    holding = [p for p in periods if p["start"] <= now < p["end"]]
    assert len(holding) == 1 and holding[0]["sign"] == "Aquarius" and holding[0]["level"] == 2
    assert holding[0]["ruler"] == "Saturn"
    assert z["frame"]["level"] == 1 and z["frame"]["start"] <= now < z["frame"]["end"]
    assert z["lot"] == "fortune" and z["lot_sign"] in sky.SIGN_NAMES and z["release_sign"] == z["lot_sign"]
    assert all(s.endswith("Z") for s in instants(z))


def test_zr_window_spirit_level_2_for_chris_holds_virgo():
    chart = _load_chart("chris")
    z = sky.zr_window(chart, jd("2026-01-01"), jd("2027-01-01"), "spirit", [2])
    now = "2026-11-11T12:00:00Z"
    holding = [p for p in z["periods"] if p["start"] <= now < p["end"]]
    assert len(holding) == 1 and holding[0]["sign"] == "Virgo"
    assert all(s.endswith("Z") for s in instants(z))


def test_zr_window_several_levels_keeps_the_finest_as_periods():
    chart = _load_chart("chris")
    z = sky.zr_window(chart, jd("2026-11-11T00:00:00Z"), jd("2026-11-13T00:00:00Z"), "spirit", [4, 5])
    assert set(z["levels"]) == {"4", "5"}
    assert z["periods"] == z["levels"]["5"]
    assert z["frame"]["level"] == 4
    assert len(z["levels"]["5"]) > len(z["levels"]["4"])


# ── The whole reply ──

def test_two_hour_window_for_chris_has_no_absent_parts():
    r = sky.sky_window("2026-11-11T22:19:00-05:00", "2026-11-12T00:18:00-05:00", name="chris",
                       lat=ORLANDO[0], lon=ORLANDO[1], zr_levels=[4, 5])
    assert "error" not in r
    assert r["tz"] == "UTC" and r["chart"] == "chris"
    assert r["start"] == "2026-11-12T03:19:00Z" and r["end"] == "2026-11-12T05:18:00Z"
    assert r["absent"] == []
    assert set(r) == {"tz", "start", "end", "chart", "at_start", "events", "releasing", "absent"}
    assert set(r["at_start"]) == {"at", "planets", "moon", "void", "ascendant", "transits", "profection"}
    assert set(r["events"]) == set(sky.KINDS)
    assert set(r["releasing"]) == {"spirit", "fortune"}
    assert set(r["releasing"]["spirit"]["levels"]) == {"4", "5"}
    assert r["at_start"]["ascendant"]["sign"] in sky.SIGN_NAMES
    assert isinstance(r["at_start"]["void"], bool)
    assert r["events"]["transits"] is not None
    assert all(s.endswith("Z") for s in instants(r))


def test_releasing_defaults_to_the_level_the_window_is_read_at():
    assert sky.default_zr_levels(2 / 24) == [5]
    assert sky.default_zr_levels(1.0) == [4]
    assert sky.default_zr_levels(30.5) == [3]
    assert sky.default_zr_levels(365.25) == [2]
    assert sky.default_zr_levels(12 * 365.25) == [1]
    r = sky.sky_window("2026-11-09T05:00:00Z", "2026-12-09T05:00:00Z", name="chris", kinds="lunations")
    assert "error" not in r and r["absent"] == []
    assert set(r["releasing"]) == {"spirit", "fortune"}
    assert set(r["releasing"]["spirit"]["levels"]) == {"3"}
    assert r["releasing"]["spirit"]["frame"]["level"] == 2
    assert r["releasing"]["fortune"]["periods"][0]["sign"] in sky.SIGN_NAMES
    r = sky.sky_window("2026-11-09T05:00:00Z", "2026-12-09T05:00:00Z", name="chris", kinds="lunations",
                       zr_levels=[4, 5])
    assert set(r["releasing"]["spirit"]["levels"]) == {"4", "5"}


def test_window_errors():
    assert "max 13 years" in sky.sky_window("2026-01-01", "2040-01-01")["error"]
    assert sky.sky_window("2026-01-02", "2026-01-01")["error"]
    assert sky.sky_window("2026-01-01", "2026-01-02", name="Nobody")["error"] == "Chart not found: nobody"
    assert "unknown kind" in sky.sky_window("2026-01-01", "2026-01-02", kinds=["weather"])["error"]
    assert "unknown planet" in sky.sky_window("2026-01-01", "2026-01-02", planets="Ceres")["error"]


def test_bare_date_window_is_read_as_new_york_and_lists_are_accepted_as_strings():
    r = sky.sky_window("2026-11-12", "2026-11-13", kinds="ingresses,void", planets="moon")
    assert r["start"] == "2026-11-12T05:00:00Z" and r["end"] == "2026-11-13T05:00:00Z"
    assert r["chart"] is None and r["releasing"] is None
    assert r["at_start"]["transits"] is None and r["at_start"]["ascendant"] is None
    assert r["events"]["transits"] is None and r["events"]["lunations"] == []
    assert [i["planet"] for i in r["events"]["ingresses"]] == ["Moon"]
    assert any(v["to_sign"] == "Capricorn" for v in r["events"]["void"])
    assert r["at_start"]["void"] is False
