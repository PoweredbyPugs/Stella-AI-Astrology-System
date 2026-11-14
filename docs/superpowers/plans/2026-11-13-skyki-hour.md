# skyki_hour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One new Stella MCP tool, `skyki_hour(name, at, lat, lon)`, that returns every fact the hour reading needs for one Ki double-hour in one JSON reply, on the local ephemeris and chart store, matching `tests/fixtures/skyki_hour_chris.json`.

**Architecture:** Two new modules. `dignity.py` scores essential dignity for any planet at any longitude under a given sect (the one thing Stella lacks locally). `skyki.py` joins existing pure functions (`ki_solar`, `ki`, `sky`, `zr`, `ephemeris.planetary_hours`) at one instant into the reply, wraps each block so a failure lands in `absent`, and registers the tool with `register_skyki(mcp)` the way `sky.register_sky` does. No existing tool changes.

**Tech Stack:** Python 3.11+, pyswisseph via `sky.py` and `ephemeris.py`, FastMCP, pytest (`.venv/bin/python -m pytest tests`).

**Spec:** `docs/superpowers/specs/2026-11-13-skyki-hour.md` (local copy of the Claude Doc handoff). Fixture: `tests/fixtures/skyki_hour_chris.json`.

## Global Constraints

- Local only: no `call_sweph`, no HTTP. Everything from `sky.py`, `zr.py`, `ki_solar.py`, `ki.py`, `ephemeris.py`, `voc.py` and the chart file.
- Every time in the reply is ISO 8601 with an offset, in America/New_York (`sky.TZ`), seconds included, e.g. `2026-11-13T18:02:23-05:00`. Never a `Z` string and never naive.
- `at` is parsed with `sky.parse_instant` (offset honoured, naive = America/New_York); `None` means now.
- Houses are whole sign: `zr.house_from(sign, from_sign)`.
- No interpretive text, keywords, verdicts or scores beyond the dignity score. No position counter for the Ki hour.
- The call never raises for a block failure: the block is `None` (or `[]`) and its name is appended to `absent`.
- Existing tools and modules are not modified except the two registration lines in `stella_server.py` and the registry count. `zr.py`, `sky.py`, `ki*.py`, `ephemeris.py` stay as they are.
- Chart names are lowercased before `ephemeris._load_chart`. Numbers in chart files are strings: wrap in `float()`.
- Peak labels are lowercased first words: `"Major Peak"` → `"major"`, `"Moderate Peak"` → `"moderate"`, `"Minor Peak"` → `"minor"`, `None` → `None`.
- Commit messages follow the repo style `feat(skyki): ...`, `test(skyki): ...`, with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. **A time before sunrise** (e.g. 05:30): planetary hours for that NY date start at sunrise, so the overlapping hours come from the previous date's night. Sect must read night. Test in Task 2 (`test_hours_before_sunrise_come_from_the_previous_night`).
2. **An L5 boundary exactly at the window start**: `releasing.*.l5` must list only periods with `end > window.start and start < window.end`; a period ending at the start is excluded. Test in Task 2 (`test_l5_list_excludes_period_ending_at_window_start`).
3. **Rising sign with no change within ±4 hours**: `sky._ascendant_at` returns `entered_at`/`leaves_at` as `None`; the reply must carry `None`, not crash converting. Covered by `_iso` accepting `None` (Task 2 unit test `test_iso_passes_none_through`).
4. **A chart in the DMS format** (micheal, betsy, kelsea): natal joins cannot be read; `natal` and the per-L5 natal fields go absent rather than raising. Test in Task 2 (`test_dms_chart_marks_natal_absent`).
5. **Degree exactly on a term boundary** (e.g. 6.0 in Aries): terms are half-open `[lo, hi)`, so 6.0 belongs to the second term. Test in Task 1 (`test_term_boundary_is_half_open`).

---

### Task 1: Essential dignity scorer and sect helpers

**Files:**
- Create: `dignity.py`
- Test: `tests/test_dignity.py`

**Interfaces:**
- Consumes: `ephemeris.SIGN_NAMES` (list of 12 sign names, Aries first).
- Produces:
  - `essential_dignities(planet: str, longitude: float, is_day: bool) -> dict` with keys `planet, sign, degree, score, condition, dignities, triplicity_ruler_type, term_ruler, face_ruler`.
    - `dignities` is the ordered list of the flags that hold, drawn from `["domicile", "exaltation", "triplicity", "term", "face", "detriment", "fall"]`.
    - `triplicity_ruler_type` is `"day"`, `"night"`, `"participating"` or `None`.
  - `condition_word(score: int) -> str`: `>= 5` → `"strong"`, `2..4` → `"moderate"`, `0..1` → `"neutral"`, `-4..-1` → `"weakened"`, `<= -5` → `"debilitated"`.
  - `sect_status(planet: str, is_day: bool) -> str`: Sun, Jupiter, Saturn are diurnal; Moon, Venus, Mars nocturnal; Mercury `"neutral"`. Returns `"in sect"`, `"contrary to sect"` or `"neutral"`.
  - `sect_block(is_day: bool) -> dict`: `{"label": "day", "light": "Sun", "benefic": "Jupiter", "malefic": "Saturn"}` or `{"label": "night", "light": "Moon", "benefic": "Venus", "malefic": "Mars"}`.
  - Tables as module constants: `DOMICILE`, `EXALTATION`, `DETRIMENT`, `FALL` (sign → planet or planets), `TRIPLICITY` (element → `{"day": p, "night": p, "participating": p}`), `TERMS` (sign → list of `(upper_bound, planet)`), `FACES` (sign → three planets), `POINTS = {"domicile": 5, "exaltation": 4, "triplicity": 3, "term": 2, "face": 1, "detriment": -5, "fall": -4}`.

**Tables (exact):**
- Domicile: Aries Mars, Taurus Venus, Gemini Mercury, Cancer Moon, Leo Sun, Virgo Mercury, Libra Venus, Scorpio Mars, Sagittarius Jupiter, Capricorn Saturn, Aquarius Saturn, Pisces Jupiter. Detriment is the opposite sign's domicile ruler.
- Exaltation: Aries Sun, Taurus Moon, Cancer Jupiter, Virgo Mercury, Libra Saturn, Capricorn Mars, Pisces Venus. Fall is the opposite sign's exalted planet (Libra Sun, Scorpio Moon, Capricorn Jupiter, Pisces Mercury, Aries Saturn, Cancer Mars, Virgo Venus).
- Triplicity (Dorothean; the participating ruler counts in both sects): Fire Sun/Jupiter/Saturn; Earth Venus/Moon/Mars; Air Saturn/Mercury/Jupiter; Water Venus/Mars/Moon (day/night/participating).
- Terms (Egyptian), as upper bounds: Aries 6 Jupiter, 12 Venus, 20 Mercury, 25 Mars, 30 Saturn. Taurus 8 Venus, 14 Mercury, 22 Jupiter, 27 Saturn, 30 Mars. Gemini 6 Mercury, 12 Jupiter, 17 Venus, 24 Mars, 30 Saturn. Cancer 7 Mars, 13 Venus, 19 Mercury, 26 Jupiter, 30 Saturn. Leo 6 Jupiter, 11 Venus, 18 Saturn, 24 Mercury, 30 Mars. Virgo 7 Mercury, 17 Venus, 21 Jupiter, 28 Mars, 30 Saturn. Libra 6 Saturn, 14 Mercury, 21 Jupiter, 28 Venus, 30 Mars. Scorpio 7 Mars, 11 Venus, 19 Mercury, 24 Jupiter, 30 Saturn. Sagittarius 12 Jupiter, 17 Venus, 21 Mercury, 26 Saturn, 30 Mars. Capricorn 7 Mercury, 14 Jupiter, 22 Venus, 26 Saturn, 30 Mars. Aquarius 7 Mercury, 13 Venus, 20 Jupiter, 25 Mars, 30 Saturn. Pisces 12 Venus, 16 Jupiter, 19 Mercury, 28 Mars, 30 Saturn. A degree `d` is in the first term whose upper bound is `> d`.
- Faces (Chaldean order Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter, repeating from Aries 0°): Aries Mars/Sun/Venus, Taurus Mercury/Moon/Saturn, Gemini Jupiter/Mars/Sun, Cancer Venus/Mercury/Moon, Leo Saturn/Jupiter/Mars, Virgo Sun/Venus/Mercury, Libra Moon/Saturn/Jupiter, Scorpio Mars/Sun/Venus, Sagittarius Mercury/Moon/Saturn, Capricorn Jupiter/Mars/Sun, Aquarius Venus/Mercury/Moon, Pisces Saturn/Jupiter/Mars. Face index is `int(degree // 10)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dignity.py
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dignity import essential_dignities, condition_word, sect_status, sect_block

FIX = json.load(open(Path(__file__).parent / "fixtures" / "skyki_hour_chris.json"))
SIGN_START = {"Aries": 0, "Taurus": 30, "Gemini": 60, "Cancer": 90, "Leo": 120, "Virgo": 150,
              "Libra": 180, "Scorpio": 210, "Sagittarius": 240, "Capricorn": 270, "Aquarius": 300, "Pisces": 330}

def test_fixture_planets_score_as_the_handoff_says():
    for p in FIX["moment"]["planets"]:
        d = essential_dignities(p["planet"], SIGN_START[p["sign"]] + p["degree"], is_day=False)
        assert (d["score"], d["condition"], d["dignities"]) == (p["score"], p["condition"], p["dignities"]), p["planet"]

def test_fixture_sect_status_at_night():
    for p in FIX["moment"]["planets"]:
        assert sect_status(p["planet"], is_day=False) == p["sect"], p["planet"]

def test_chris_natal_matches_the_stored_api_dignities():
    chart = json.load(open(Path(__file__).parent.parent / "charts" / "chris.json"))
    for pl in chart["planets"]:
        if pl["name"] not in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            continue
        d = essential_dignities(pl["name"], float(pl["longitude"]), is_day=chart["sect"]["isDaySect"])
        s = pl["dignities"]
        assert d["score"] == s["score"], pl["name"]
        assert d["condition"] == s["condition"], pl["name"]
        assert ("domicile" in d["dignities"]) == s["domicile"], pl["name"]
        assert ("exaltation" in d["dignities"]) == s["exaltation"], pl["name"]
        assert ("triplicity" in d["dignities"]) == s["triplicity"]["isTriplicityRuler"], pl["name"]
        assert ("term" in d["dignities"]) == s["term"]["isInOwnTerm"], pl["name"]
        assert ("face" in d["dignities"]) == s["face"]["isInOwnFace"], pl["name"]
        assert ("detriment" in d["dignities"]) == s["detriment"], pl["name"]
        assert ("fall" in d["dignities"]) == s["fall"], pl["name"]

def test_condition_words():
    assert [condition_word(s) for s in (7, 5, 4, 2, 1, 0, -1, -4, -5, -9)] == \
        ["strong", "strong", "moderate", "moderate", "neutral", "neutral", "weakened", "weakened", "debilitated", "debilitated"]

def test_term_boundary_is_half_open():
    assert essential_dignities("Venus", 6.0, True)["term_ruler"] == "Venus"      # Aries 6°00' opens Venus's term
    assert essential_dignities("Jupiter", 5.999, True)["term_ruler"] == "Jupiter"

def test_participating_triplicity_counts_in_both_sects():
    assert "triplicity" in essential_dignities("Saturn", 8.57, True)["dignities"]
    assert essential_dignities("Saturn", 8.57, False)["triplicity_ruler_type"] == "participating"

def test_sect_blocks():
    assert sect_block(True) == {"label": "day", "light": "Sun", "benefic": "Jupiter", "malefic": "Saturn"}
    assert sect_block(False) == {"label": "night", "light": "Moon", "benefic": "Venus", "malefic": "Mars"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dignity.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'dignity'`.

- [ ] **Step 3: Implement `dignity.py`**

Signatures and tables as in Interfaces. `essential_dignities` computes sign and degree from the longitude (`longitude % 360`), collects flags in the fixed order, sums `POINTS`, and reports `degree` rounded to 2 places. Module docstring: one paragraph naming the sources (Lilly points, Dorothean triplicities, Egyptian terms, Chaldean faces) and that the scores and condition words reproduce the chart store's API fields.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dignity.py -q`
Expected: 7 passed. If `test_chris_natal_matches_the_stored_api_dignities` fails on one planet, report which planet and which flag in your report and stop: the API's table differs there and the controller rules on it. Do not loosen the test.

- [ ] **Step 5: Run the suite and commit**

Run: `.venv/bin/python -m pytest tests -q` → all pass.

```bash
git add dignity.py tests/test_dignity.py
git commit -m "feat(dignity): essential dignity scoring at any longitude and sect; sect helpers"
```

---

### Task 2: `skyki.py` core and the fixture test

**Files:**
- Create: `skyki.py`
- Test: `tests/test_skyki.py`

**Interfaces:**
- Consumes (Task 1): `dignity.essential_dignities`, `dignity.sect_status`, `dignity.sect_block`.
- Consumes (existing): `sky.parse_instant(s) -> jd`, `sky.jd_to_dt(jd)` (aware UTC), `sky.TZ`, `sky._planets_at(jd)`, `sky._moon_at(jd)`, `sky._ascendant_at(jd, lat, lon)` (ISO `Z` strings or `None` for `entered_at`/`leaves_at`), `sky._transits_at(jd, chart, cap, planets, aspects)` with `aspects=list(sky.ASPECTS)` and `cap=3.0`, `sky._void_spans(jd0, jd1)` (`start_jd, end_jd`), `sky.zr_window(chart, jd0, jd1, lot, levels=(4, 5))` (`levels["4"]`, `levels["5"]`, times as `Z` strings), `ki_solar.solar_stack(jd)["spans"]["hour"]` (`(start_jd, end_jd)`), `ki.calculate_daily_ki(birth_date: date, target_dt_naive_ny)` (`natal_year_ki`, `global[level]["ki"]`, `global[level]["info"]["name"|"element"]`, same for `personal`), `ephemeris._load_chart(name)`, `ephemeris.planetary_hours(date_str, lat, lon)` (`hours[{ruler, start, end}]`, NY strings `"%Y-%m-%d %H:%M:%S %Z"`, `sunrise`, `sunset`), `zr.house_from`, `zr.get_ruler`.
- Produces:
  - `skyki_hour(name: str, at: Optional[str] = None, lat: float = None, lon: float = None) -> dict` with the fixture's top-level keys `chart, at, window, ki, moment, natal, releasing, changes, absent`.
  - Helpers (module level, tested): `_iso(jd_or_iso_z, tz=sky.TZ) -> Optional[str]` (a Julian Day, an aware datetime, or a `Z` string → NY ISO with offset; `None` → `None`), `_is_day(jd, lat, lon) -> bool`, `_planetary_hours_overlapping(jd0, jd1, lat, lon) -> list[dict]`, `_natal_rising_sign(chart) -> str`, `_natal_points(chart) -> list[tuple[name, sign]]` (planets, North Node, Chiron, then `"Lot of Fortune"`, `"Lot of Spirit"`), `_peak(label) -> Optional[str]`.

**Block rules (what each key holds):**
- `window`: `{"start", "end"}` from `solar_stack(jd)["spans"]["hour"]`.
- `ki`: `natal_year` = `calculate_daily_ki(...)["natal_year_ki"]`; `global`/`personal` each `{"hour": {"number", "trigram", "element"}, "day": {...}}` where `trigram` is `info["name"]` (e.g. `"Lake"`) and `element` is `info["element"]`. Birth date is `date.fromisoformat(chart["birthData"]["date"])`; the target is `jd_to_dt(jd).astimezone(sky.TZ).replace(tzinfo=None)`.
- `moment.rising`: `{"sign", "ruler": zr.get_ruler(sign), "entered_at", "leaves_at"}` from `_ascendant_at`.
- `moment.sect`: `sect_block(_is_day(...))`. `_is_day` is true iff the planetary-hours `sunrise <= at < sunset` for the NY date of `at` (parse the NY strings with `datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")` and attach `sky.TZ`).
- `moment.moon`: `{"phase": _moon_at(jd)["phase"], "void": bool}`; when void also `"void_start"`, `"void_end"` from the span in `_void_spans(jd - 1, jd + 1)` containing `jd`.
- `moment.planets`: the first seven of `_planets_at(jd)` in order Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn; per planet `{"planet", "sign", "degree" (round 2), "retrograde", "score", "condition", "dignities", "sect", "house_from_rising", "natal_house"}` where `score/condition/dignities` come from `essential_dignities(planet, longitude, is_day)`, `sect` from `sect_status`, `house_from_rising = house_from(sign, rising)`, `natal_house = house_from(sign, natal_rising)`.
- `moment.planetary_hours`: every planetary hour with `end > window.start and start < window.end`, taken from the NY date of `window.start` and the NY date before it, deduplicated by start, sorted; `{"ruler", "start", "end"}`.
- `natal`: `rising_sign_house = house_from(rising, natal_rising)`; `in_rising_sign` = names from `_natal_points` whose sign is the rising sign, in that order; `ruler` = `{"planet", "is_chart_ruler": ruler == get_ruler(natal_rising), "natal": {"sign", "house"}, "transit": {"sign", "house": house_from(transit sign, natal_rising)}, "contacts": [...]}` where contacts are `_transits_at(jd, chart, 3.0, [ruler], list(sky.ASPECTS))` mapped to `{"natal_point", "aspect": lowercased, "orb", "applying", "exact_at": _iso}`. Natal sign and house of the ruler come from the chart's planet entry (`sign`, and `house_from(sign, natal_rising)`, never the stored Placidus `house`).
- `releasing`: `fortune_sign = chart["lots"]["fortune"]["sign"]`; for each lot in `("spirit", "fortune")`: `zr_window(chart, w0, w1, lot, levels=(4, 5))`; `l4` = the single period in `levels["4"]` containing `jd` (there is exactly one, since the window lies inside one Ki hour and L4 periods are ≥ 25 h; if more than one overlaps, the one containing `at`), mapped to `{"sign", "ruler", "start", "end", "peak": _peak(peak_type), "house_from_fortune", "angularity", "loosing_of_bond": is_loosing_of_bond, "loosing_at": _iso or None}`; `l5` = every period in `levels["5"]`, same mapping plus `"natal_house": house_from(sign, natal_rising)`, `"natal_planets"`: planet names (planets only: Sun..Pluto, North Node, Chiron; not lots) in that sign, `"ruler_natal": {"sign", "house"}` from the natal entry, `"ruler_transit": {"sign", "house"}` from `_planets_at` with the natal whole-sign house.
- `changes`: entries `{"at", "what", "from", "to"}` for: `rising_sign` when `leaves_at` is inside `(window.start, window.end)` (`to` = next sign; also `entered_at` inside the window, with `from` = previous sign); `planetary_hour` at each boundary between consecutive overlapping hours inside the window; `spirit_l5` / `fortune_l5` at each boundary between consecutive L5 periods inside the window; `moon_void` for a void start (`from: "aspecting", to: "void"`) or end (`from: "void", to: "aspecting"`) inside the window. Sorted by `at`, then by `what`.
- `absent`: names of blocks that raised: `"ki"`, `"rising"`, `"sect"`, `"moon"`, `"planets"`, `"planetary_hours"`, `"natal"`, `"releasing"`, `"changes"`. A failed block's value is `None`. Missing `name` or a chart that is not found returns `{"error": "..."}` (the only error case).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_skyki.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'skyki'`.

- [ ] **Step 3: Implement `skyki.py`**

Module docstring: what the tool is for (one Ki hour, facts only, local ephemeris), and the time rule. Implement the helpers and `skyki_hour` per the Block rules. Each block runs inside a small `_part(name, fn)` that catches `Exception`, appends `name` to `absent` and returns `None` (same idea as `sky._part`). Compute shared inputs once: `jd`, `w0, w1`, chart, natal rising, `is_day`, the seven planets, the ascendant, the planetary hours, both lots' windows; then assemble `changes` from the blocks that succeeded.

For the DMS-format charts (`planets` is a dict; betsy, micheal, kelsea), `_natal_rising_sign` still works (it reads `angles.ascendant.sign`, present in both formats), so the planets block keeps its natal houses; `_natal_points` raises `ValueError("chart planets are not in the list format")`, which sends `natal` to `absent`. Such charts also lack `birthData` and `lots`, so `ki` and `releasing` go absent too; that is correct behaviour, not a failure. Keep `releasing` itself computing when `natal` is absent by filling the natal fields with `None` in that case rather than failing the whole block; add `"releasing_natal"` to `absent` then. (Adjust `test_dms_chart_marks_natal_absent` only if this reading requires it: assert `"natal" in absent`, which stays true.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_skyki.py -q`
Expected: 17 passed. Tests run on Moshier (no ephemeris files), so times may differ from the fixture by up to a minute; the tolerances allow that. If a value differs by more, report it rather than widening a tolerance.

- [ ] **Step 5: Run the suite and commit**

Run: `.venv/bin/python -m pytest tests -q` → all pass.

```bash
git add skyki.py tests/test_skyki.py
git commit -m "feat(skyki): skyki_hour joins the Ki hour, moment chart, dignities, hours, natal reading and releasing for one instant"
```

---

### Task 3: Register the tool, docs and changelog

**Files:**
- Modify: `skyki.py` (add `register_skyki`)
- Modify: `stella_server.py` (two lines next to `from sky import register_sky` / `register_sky(mcp)`)
- Modify: `tests/test_tool_registry.py` (count 104 → 105)
- Modify: `TOOLS.md` (title count "104 Tools" → "105 Tools"; one new row 105 after the `get_sky_window` row's numbering scheme, in the same table as `get_sky_window`)
- Modify: `CHANGELOG.md` (new dated section at the top)
- Test: `tests/test_skyki.py` (one registration test), `tests/test_tool_registry.py`

**Interfaces:**
- Consumes: `skyki.skyki_hour` (Task 2); `sky.register_sky` as the pattern (nested `@mcp.tool() async def ...`, `await asyncio.to_thread(...)`, `json.dumps(result, default=str)`, exceptions → `{"error": str(e)}`).
- Produces: `register_skyki(mcp) -> None` registering one tool `skyki_hour(name: str, at: Optional[str] = None, lat: float = None, lon: float = None) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skyki.py`:

```python
def test_register_skyki_adds_one_tool():
    import asyncio
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("t")
    skyki.register_skyki(mcp)
    tools = asyncio.run(mcp.list_tools())
    assert [t.name for t in tools] == ["skyki_hour"]
    assert "Ki" in tools[0].description and "lat" in tools[0].description
```

Change `tests/test_tool_registry.py`'s expected count from 104 to 105.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_skyki.py::test_register_skyki_adds_one_tool tests/test_tool_registry.py -q`
Expected: `AttributeError: module 'skyki' has no attribute 'register_skyki'` and `assert 104 == 105`.

- [ ] **Step 3: Implement `register_skyki` and wire it in**

Docstring for the tool (this is the description Jev and the client see). First line: `Every fact the hour reading needs for one Ki double-hour, in one call: facts only, no grading.` Then a short paragraph: the Ki hour containing `at` (start, end, global and personal hour and day with trigram and element), the chart of the moment (rising sign and when it changes, sect, the seven planets with dignity score, condition, flags, sect status and both whole-sign houses, the Moon's phase and void state, the planetary hours overlapping the Ki hour), the rising sign read against the natal chart (its natal house, natal points in it, its ruler natally and in transit with contacts), releasing L4 and L5 for Spirit and Fortune with natal joins, and the time-ordered `changes` inside the hour. Args section: `name` (stored chart), `at` (ISO 8601, default now, naive = America/New_York), `lat`, `lon` (required; rising sign, sect, planetary hours). Note: "Runs on the local ephemeris and chart store. Parts that cannot be computed are named in `absent`." No em-dashes anywhere in the docstring.

In `stella_server.py`, directly after `register_sky(mcp)`: `from skyki import register_skyki` and `register_skyki(mcp)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_skyki.py tests/test_tool_registry.py -q`
Expected: all pass, registry count 105, no "already exists" log line.

- [ ] **Step 5: Docs**

`TOOLS.md`: bump the heading count to 105 and add a row for `skyki_hour` next to `get_sky_window`, one line, same voice as the other rows: "One Ki double-hour in one call for the hour reading: Ki hour and numbers, rising sign and sect, the seven planets with dignity and houses, the Moon, planetary hours, the rising sign read natally, releasing L4/L5 with natal joins, and the changes inside the hour; facts only".

`CHANGELOG.md`: new section `## 2026.11.13 — skyki_hour and local dignity scoring` above the Octave section, two bullets: `dignity.py` (what it scores, the tables by name, that it reproduces the chart store's API scores and condition words, checked against chris's natal planets) and `skyki.py` (the tool, what it joins, the fixture it matches, that nothing existing changed). Mention the open points decided: Ceres out, the Moon's contacts out, numbers/trigrams/elements only.

- [ ] **Step 6: Run the suite and commit**

Run: `.venv/bin/python -m pytest tests -q` → all pass.

```bash
git add skyki.py stella_server.py tests/test_skyki.py tests/test_tool_registry.py TOOLS.md CHANGELOG.md
git commit -m "feat(skyki): register skyki_hour (105 tools); docs and changelog"
```
