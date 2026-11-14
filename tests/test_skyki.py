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

def test_l5_list_excludes_period_ending_at_window_start(monkeypatch):
    # Spirit's L5 list gets a period ending exactly at the window start, and the next one
    # starting there; the first must be left out and no change listed at window.start.
    real = sky.zr_window
    def fake(chart, jd0, jd1, lot, levels):
        z = real(chart, jd0, jd1, lot, levels=levels)
        if lot == "spirit":
            w = sky.iso_utc(jd0)
            nxt = dict(z["levels"]["5"][-1], start=w)
            prev = dict(nxt, sign="Leo", ruler="Sun", start=sky.iso_utc(jd0 - 5 * sky.HOUR), end=w)
            z["levels"]["5"] = [prev, nxt]
        return z
    monkeypatch.setattr(skyki.sky, "zr_window", fake)
    r = fixture_call()
    w0 = iso(r["window"]["start"])
    assert [p["sign"] for p in r["releasing"]["spirit"]["l5"]] == ["Virgo"]
    for lot in ("spirit", "fortune"):
        for p in r["releasing"][lot]["l5"]:
            assert iso(p["end"]) > w0
    assert not [c for c in r["changes"] if c["what"].endswith("_l5") and iso(c["at"]) == w0]

def test_iso_passes_none_through():
    assert skyki._iso(None) is None
    assert skyki._iso("2026-11-13T22:58:14Z") == "2026-11-13T17:58:14-05:00"

def test_dms_chart_marks_natal_absent():
    r = skyki.skyki_hour("betsy", FIX["at"], *MAITLAND)
    assert "natal" in r["absent"]
    assert r["window"] and r["moment"]["planets"]

def test_missing_chart_is_an_error_not_a_raise():
    assert "error" in skyki.skyki_hour("no-such-chart", FIX["at"], *MAITLAND)

# ── Fix round 1 ─────────────────────────────────────────────────────────────

def test_window_failure_is_an_error_not_a_raise(monkeypatch):
    def boom(jd):
        raise RuntimeError("no sun today")
    monkeypatch.setattr(skyki.ki_solar, "solar_stack", boom)
    r = skyki.skyki_hour("chris", FIX["at"], *MAITLAND)
    assert "error" in r and "no sun today" in r["error"]

def _asc_boundaries(jd0, jd1, lat, lon):
    idx = lambda j: int((sky._asc_lon(j, lat, lon) % 360) // 30)
    out, j, prev = [], jd0, idx(jd0)
    while j < jd1:
        j2 = min(j + sky.MINUTE, jd1)
        cur = idx(j2)
        if cur != prev:
            out.append((sky._bisect(lambda x: idx(x) == prev, j, j2), sky.SIGN_NAMES[prev], sky.SIGN_NAMES[cur]))
            prev = cur
        j = j2
    return out

def test_two_rising_changes_inside_one_ki_hour_are_both_listed():
    # Aries rises in under ninety minutes at Maitland; this Ki hour holds Aries->Taurus and Taurus->Gemini.
    r = skyki.skyki_hour("chris", "2026-11-13T16:10:00-05:00", *MAITLAND)
    assert r["moment"]["rising"]["sign"] == "Aries"
    got = [c for c in r["changes"] if c["what"] == "rising_sign"]
    w0, w1 = sky.parse_instant(r["window"]["start"]), sky.parse_instant(r["window"]["end"])
    want = _asc_boundaries(w0, w1, *MAITLAND)
    assert len(want) == 2
    assert [(c["from"], c["to"]) for c in got] == [(f, t) for _, f, t in want]
    for c, (jd, _, _) in zip(got, want):
        assert within_minute(c["at"], skyki._iso(jd))
    assert [iso(c["at"]) for c in r["changes"]] == sorted(iso(c["at"]) for c in r["changes"])

def test_void_failure_keeps_the_moon_phase(monkeypatch):
    def boom(jd0, jd1):
        raise RuntimeError("voc down")
    monkeypatch.setattr(skyki.sky, "_void_spans", boom)
    r = skyki.skyki_hour("chris", FIX["at"], *MAITLAND)
    assert r["moment"]["moon"] == {"phase": FIX["moment"]["moon"]["phase"], "void": None}
    assert "moon_void" in r["absent"] and "moon" not in r["absent"]

def test_corrupt_chart_is_an_error_not_a_raise(monkeypatch, tmp_path):
    import ephemeris
    (tmp_path / "broken.json").write_text("{ not json")
    monkeypatch.setattr(ephemeris, "CHARTS_DIR", tmp_path)
    assert "error" in skyki.skyki_hour("broken", FIX["at"], *MAITLAND)

def test_iso_from_julian_day():
    assert skyki._iso(sky.parse_instant("2026-11-13T22:58:14Z")) == "2026-11-13T17:58:14-05:00"

def test_iso_from_aware_utc_datetime():
    from datetime import timezone
    assert skyki._iso(datetime(2026, 11, 13, 22, 58, 14, tzinfo=timezone.utc)) == "2026-11-13T17:58:14-05:00"


def test_register_skyki_adds_both_tools():
    import asyncio
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("t")
    skyki.register_skyki(mcp)
    tools = asyncio.run(mcp.list_tools())
    assert sorted(t.name for t in tools) == ["skyki_hour", "skyki_inner_hour"]
    assert "Ki" in tools[0].description and "lat" in tools[0].description


# ── Final review fix ────────────────────────────────────────────────────────

def test_chart_name_is_lowercased_before_loading(monkeypatch):
    seen = []
    real = skyki._load_chart
    def spy(n):
        seen.append(n)
        return real(n)
    monkeypatch.setattr(skyki, "_load_chart", spy)
    r = skyki.skyki_hour(" Chris ", FIX["at"], *MAITLAND)
    assert seen == ["chris"]
    assert r["chart"] == "chris"

def test_boundary_a_fraction_after_the_true_start_is_not_a_change_at_window_start(monkeypatch):
    jd = sky.parse_instant(FIX["at"])
    w0 = skyki.ki_solar.solar_stack(jd)["spans"]["hour"][0]
    shown = sky.parse_instant(skyki._iso(w0))
    edge = shown + 0.5 * sky.SECOND if shown < w0 else shown
    b = (w0 + edge) / 2  # after the true start, yet shown as the window start
    assert b > w0 and skyki._iso(b) == skyki._iso(w0)
    monkeypatch.setattr(skyki.sky, "_void_spans", lambda a, z: [
        {"start_jd": b, "end_jd": b + sky.HOUR, "from_sign": "Capricorn", "to_sign": "Aquarius", "last_aspect": None}])
    r = fixture_call()
    assert not [c for c in r["changes"] if c["at"] == r["window"]["start"]]

def test_missing_transit_blanks_only_ruler_transit_in_l5(monkeypatch):
    def boom(jd):
        raise RuntimeError("no planets")
    monkeypatch.setattr(skyki.sky, "_planets_at", boom)
    r = fixture_call()
    assert "releasing_natal" in r["absent"]
    rows = r["releasing"]["fortune"]["l5"]
    want = FIX["releasing"]["fortune"]["l5"]
    for got, w in zip(rows, want, strict=True):
        assert got["ruler_transit"] is None
        assert (got["natal_house"], got["natal_planets"], got["ruler_natal"]) == \
            (w["natal_house"], w["natal_planets"], w["ruler_natal"])


# ── Inner hour: the personal side read from the second (month) Ki number ───────────────────

def inner_fixture_call():
    return skyki.skyki_inner_hour("chris", FIX["at"], *MAITLAND)

def test_inner_hour_personal_side_comes_from_the_month_number():
    k = inner_fixture_call()["ki"]
    # chris is 5.9.1: the inner hour reads from the 9, not the 5
    assert k["natal_month"] == 9
    assert "natal_year" not in k
    assert k["global"] == FIX["ki"]["global"]
    assert k["personal"]["hour"] == {"number": 7, "trigram": "Lake", "element": "Metal"}
    assert k["personal"]["day"] == {"number": 3, "trigram": "Thunder", "element": "Wood"}

def test_inner_hour_matches_the_principal_hour_everywhere_but_ki():
    a = fixture_call()
    b = inner_fixture_call()
    assert set(a) == set(b)
    for key in a:
        if key != "ki":
            assert a[key] == b[key], key

def test_inner_hour_keeps_ki_absent_without_birth_data():
    r = skyki.skyki_inner_hour("betsy", FIX["at"], *MAITLAND)
    assert r["ki"] is None and "ki" in r["absent"]

def test_inner_hour_registers_as_a_second_tool():
    import asyncio
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("t")
    skyki.register_skyki(mcp)
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(tools) == {"skyki_hour", "skyki_inner_hour"}
    assert "second" in tools["skyki_inner_hour"].description
    assert "lat" in tools["skyki_inner_hour"].description
