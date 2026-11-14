# tests/test_skyki.py
import json, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skyki, sky
from zr import house_from
from ephemeris import _load_chart

FIX = json.load(open(Path(__file__).parent / "fixtures" / "skyki_hour_chris.json"))
MAITLAND = (28.6278, -81.3631)

def iso(s):
    return datetime.fromisoformat(s)

def within_minute(a, b):
    return abs((iso(a) - iso(b)).total_seconds()) <= 60

def fixture_call():
    return skyki.skyki_hour("chris", FIX["at"], *MAITLAND)

def test_fixture_window_and_ki():
    r = fixture_call()
    assert within_minute(r["window"]["start"], FIX["window"]["start"])
    assert within_minute(r["window"]["end"], FIX["window"]["end"])
    assert r["ki"] == FIX["ki"]

def test_fixture_moment_rising_sect_moon():
    r = fixture_call()["moment"]
    f = FIX["moment"]
    assert (r["rising"]["sign"], r["rising"]["ruler"]) == ("Gemini", "Mercury")
    assert within_minute(r["rising"]["entered_at"], f["rising"]["entered_at"])
    assert within_minute(r["rising"]["leaves_at"], f["rising"]["leaves_at"])
    assert r["sect"] == f["sect"]
    assert r["moon"] == f["moon"]

def test_fixture_planets():
    r = fixture_call()["moment"]["planets"]
    for got, want in zip(r, FIX["moment"]["planets"], strict=True):
        assert abs(got.pop("degree") - want["degree"]) <= 0.05, want["planet"]
        want = {k: v for k, v in want.items() if k != "degree"}
        assert got == want, want["planet"]

def test_fixture_planetary_hours():
    r = fixture_call()["moment"]["planetary_hours"]
    assert [h["ruler"] for h in r] == ["Mars", "Sun", "Venus"]
    for got, want in zip(r, FIX["moment"]["planetary_hours"]):
        assert within_minute(got["start"], want["start"]) and within_minute(got["end"], want["end"])

def test_fixture_natal_joins():
    r = fixture_call()["natal"]
    f = FIX["natal"]
    assert r["rising_sign_house"] == 10
    assert r["in_rising_sign"] == f["in_rising_sign"]
    ru, fu = r["ruler"], f["ruler"]
    assert (ru["planet"], ru["is_chart_ruler"], ru["natal"], ru["transit"]) == ("Mercury", True, fu["natal"], fu["transit"])
    assert [(c["natal_point"], c["aspect"], c["applying"]) for c in ru["contacts"]] == \
        [(c["natal_point"], c["aspect"], c["applying"]) for c in fu["contacts"]]
    for got, want in zip(ru["contacts"], fu["contacts"]):
        assert abs(got["orb"] - want["orb"]) <= 0.05
        assert within_minute(got["exact_at"], want["exact_at"])

def test_fixture_releasing():
    r = fixture_call()["releasing"]
    f = FIX["releasing"]
    assert r["fortune_sign"] == "Gemini"
    for lot in ("spirit", "fortune"):
        for key in ("sign", "ruler", "peak", "house_from_fortune", "angularity", "loosing_of_bond"):
            assert r[lot]["l4"][key] == f[lot]["l4"][key], (lot, key)
        assert within_minute(r[lot]["l4"]["start"], f[lot]["l4"]["start"])
        assert within_minute(r[lot]["l4"]["end"], f[lot]["l4"]["end"])
        assert len(r[lot]["l5"]) == len(f[lot]["l5"])
        for got, want in zip(r[lot]["l5"], f[lot]["l5"]):
            for key in ("sign", "ruler", "peak", "house_from_fortune", "angularity", "loosing_of_bond",
                        "natal_house", "natal_planets", "ruler_natal", "ruler_transit"):
                assert got[key] == want[key], (lot, got["sign"], key)
            assert within_minute(got["start"], want["start"]) and within_minute(got["end"], want["end"])
    assert within_minute(r["fortune"]["l4"]["loosing_at"], f["fortune"]["l4"]["loosing_at"])

def test_fixture_changes_in_order_and_nothing_absent():
    r = fixture_call()
    assert [(c["what"], c["from"], c["to"]) for c in r["changes"]] == \
        [(c["what"], c["from"], c["to"]) for c in FIX["changes"]]
    for got, want in zip(r["changes"], FIX["changes"]):
        assert within_minute(got["at"], want["at"])
    assert r["absent"] == []
    assert r["chart"] == "chris"

def test_every_time_carries_an_offset():
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): yield from walk(v)
        elif isinstance(x, list):
            for v in x: yield from walk(v)
        elif isinstance(x, str) and len(x) >= 19 and x[4] == "-" and x[10] == "T":
            yield x
    times = list(walk(fixture_call()))
    assert times and all(iso(t).utcoffset() is not None and not t.endswith("Z") for t in times)

# ── Further checks from the handoff ─────────────────────────────────────────

def test_daytime_hour_reads_day_sect():
    r = skyki.skyki_hour("chris", "2026-11-13T12:00:00-05:00", *MAITLAND)
    assert r["moment"]["sect"] == {"label": "day", "light": "Sun", "benefic": "Jupiter", "malefic": "Saturn"}
    assert r["moment"]["planets"][0]["sect"] == "in sect"   # the Sun by day

def test_void_moon_hour_reports_the_span_and_the_change():
    # Find a void span near the fixture week and stand two minutes inside it.
    jd0 = sky.parse_instant("2026-11-10T00:00:00-05:00")
    spans = sky._void_spans(jd0, jd0 + 10)
    assert spans
    for span in spans:
        at = sky.jd_to_dt(span["start_jd"] + 2 / 1440).astimezone(sky.TZ).isoformat()
        r = skyki.skyki_hour("chris", at, *MAITLAND)
        if iso(r["window"]["start"]) < iso(skyki._iso(span["start_jd"])):
            break
    else:
        raise AssertionError("no void span whose start falls inside its Ki hour")
    assert r["moment"]["moon"]["void"] is True
    assert within_minute(r["moment"]["moon"]["void_start"], skyki._iso(span["start_jd"]))
    assert within_minute(r["moment"]["moon"]["void_end"], skyki._iso(span["end_jd"]))
    assert any(c["what"] == "moon_void" and c["to"] == "void" for c in r["changes"])

def test_rising_change_mid_hour_is_listed_and_rising_is_the_sign_at_at():
    r = fixture_call()
    assert r["moment"]["rising"]["sign"] == "Gemini"
    assert [(c["from"], c["to"]) for c in r["changes"] if c["what"] == "rising_sign"] == [("Gemini", "Cancer")]

def test_one_minute_either_side_of_the_boundary_gives_different_windows():
    a = skyki.skyki_hour("chris", "2026-11-13T20:00:30-05:00", *MAITLAND)["window"]
    b = skyki.skyki_hour("chris", "2026-11-13T20:02:30-05:00", *MAITLAND)["window"]
    assert a != b and within_minute(a["end"], b["start"])

def test_second_chart_follows_its_own_natal():
    chart = _load_chart("bradley")
    asc = chart["angles"]["ascendant"]["sign"]
    r = skyki.skyki_hour("bradley", FIX["at"], *MAITLAND)
    assert r["absent"] == []
    assert r["natal"]["rising_sign_house"] == house_from("Gemini", asc)
    for p in r["moment"]["planets"]:
        assert p["natal_house"] == house_from(p["sign"], asc)
    assert r["natal"]["in_rising_sign"] == [pl["name"] for pl in chart["planets"] if pl["sign"] == "Gemini"] + \
        [f"Lot of {k.title()}" for k, v in chart["lots"].items() if v["sign"] == "Gemini"]

# ── Review focus ────────────────────────────────────────────────────────────

def test_hours_before_sunrise_come_from_the_previous_night():
    r = skyki.skyki_hour("chris", "2026-11-13T05:30:00-05:00", *MAITLAND)
    assert r["moment"]["sect"]["label"] == "night"
    hours = r["moment"]["planetary_hours"]
    assert hours and all(iso(h["start"]) < iso(r["window"]["end"]) and iso(h["end"]) > iso(r["window"]["start"]) for h in hours)

def test_l5_list_excludes_period_ending_at_window_start():
    r = fixture_call()
    w0 = iso(r["window"]["start"])
    for lot in ("spirit", "fortune"):
        for p in r["releasing"][lot]["l5"]:
            assert iso(p["end"]) > w0

def test_iso_passes_none_through():
    assert skyki._iso(None) is None
    assert skyki._iso("2026-11-13T22:58:14Z") == "2026-11-13T17:58:14-05:00"

def test_dms_chart_marks_natal_absent():
    r = skyki.skyki_hour("betsy", FIX["at"], *MAITLAND)
    assert "natal" in r["absent"]
    assert r["window"] and r["moment"]["planets"]

def test_missing_chart_is_an_error_not_a_raise():
    assert "error" in skyki.skyki_hour("no-such-chart", FIX["at"], *MAITLAND)
