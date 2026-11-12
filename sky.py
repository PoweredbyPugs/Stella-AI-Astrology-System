"""Sky: the sky over a window of time, in one call.

What stands at the start (the planets, the Moon and her phase, void of course, the rising
sign, transits to a stored chart with their orbs, the annual profection), what moves inside
the window (lunations, ingresses, the Moon's gates at 15 degrees of a sign, stations,
eclipses, void of course spans, exact transits, the four turnings of the year), and the
zodiacal releasing periods that overlap it. Built for Octave: one call per period.

Pure pyswisseph (Moshier where the ephemeris files are missing) and the local chart store
under charts/; no Helios. Julian Days inside; ISO 8601 at the edges: inputs take an offset
or Z (naive = America/New_York; a bare date is its midnight), every instant returned is UTC
with Z, whole seconds. Longitudes rounded to 4, degrees in sign to 2, speeds to 4.

Register in stella_server.py beside register_octave:
    from sky import register_sky  # noqa: E402
    register_sky(mcp)

CLI: python sky.py START END [--name chris] [--lat 28.5383 --lon -81.3792] [--kinds a,b]
     [--planets a,b] [--aspects a,b] [--zr-levels 4,5] [--lots spirit,fortune] [--orb 3]
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo

import swisseph as swe

from ephemeris import (
    ASPECTS, FLAGS, PLANET_IDS, SIGN_NAMES, _angular_sep, _degree_in_sign, _get_lon,
    _get_lon_speed, _load_chart, _sign_name,
)
import voc
import zr

TZ = ZoneInfo("America/New_York")
UTC = timezone.utc
SECOND = 1 / 86400
MINUTE = 1 / 1440
HOUR = 1 / 24
MAX_YEARS = 13
SYNODIC_MONTH = 29.530589

KINDS = ("lunations", "ingresses", "moon_gates", "stations", "eclipses", "void", "transits", "turnings")
LOTS = ("spirit", "fortune")
PLANETS = list(PLANET_IDS)  # Sun .. Pluto, in that order
NATAL_EXTRA = ("North Node", "Chiron")
PHASES = ("new", "waxing crescent", "first quarter", "waxing gibbous",
          "full", "waning gibbous", "last quarter", "waning crescent")
LUNATIONS = ("new", "first_quarter", "full", "last_quarter")
TURNINGS = ("spring_equinox", "summer_solstice", "autumn_equinox", "winter_solstice")

# Per transiting body: the orb a transit is listed within (sextiles two thirds), the span
# searched for its perfection, and the scan steps, all in days.
ORB = {"Moon": 3.0, "Sun": 3.0, "Mercury": 2.0, "Venus": 2.0, "Mars": 2.5,
       "Jupiter": 3.0, "Saturn": 3.0, "Uranus": 2.5, "Neptune": 2.5, "Pluto": 2.5}
EXACT_SPAN = {"Moon": 3.0, "Sun": 45.0, "Mercury": 45.0, "Venus": 45.0, "Mars": 120.0,
              "Jupiter": 365.25, "Saturn": 730.5, "Uranus": 730.5, "Neptune": 730.5, "Pluto": 730.5}
TRANSIT_STEP = {"Moon": HOUR, "Sun": 0.25, "Mercury": 0.25, "Venus": 0.25, "Mars": 0.5,
                "Jupiter": 1.0, "Saturn": 2.0, "Uranus": 2.0, "Neptune": 2.0, "Pluto": 2.0}
APPLY_STEP = {"Moon": HOUR}  # every other body: one day
INGRESS_STEP = {"Moon": 2 * HOUR, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 1.0,
                "Jupiter": 5.0, "Saturn": 5.0, "Uranus": 5.0, "Neptune": 5.0, "Pluto": 5.0}
STATION_STEP = {"Mercury": 1.0, "Venus": 1.0, "Mars": 1.0,
                "Jupiter": 3.0, "Saturn": 3.0, "Uranus": 3.0, "Neptune": 3.0, "Pluto": 3.0}
EXACT_ORB = {"Moon": 1.0}  # every other body: half a degree
ASC_SCAN = 4 * HOUR
ASC_STEP = 5 * MINUTE
VOID_CHUNK = 100.0  # days per calculate_voc call (it stops after sixty ingresses)


# ── Instants ──

def _dt_to_jd(dt: datetime) -> float:
    u = dt.astimezone(UTC)
    return swe.julday(u.year, u.month, u.day,
                      u.hour + u.minute / 60 + (u.second + u.microsecond / 1e6) / 3600)


def parse_instant(s: str) -> float:
    """ISO 8601 -> Julian Day (UT). An offset or Z is honored; naive is America/New_York;
    a bare date is its midnight."""
    dt = datetime.fromisoformat(str(s).strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return _dt_to_jd(dt)


def jd_to_dt(jd: float) -> datetime:
    """Julian Day (UT) -> aware UTC datetime, whole seconds."""
    y, m, d, h = swe.revjul(jd)
    return datetime(y, m, d, tzinfo=UTC) + timedelta(seconds=round(h * 3600))


def iso_utc(jd: float) -> str:
    return jd_to_dt(jd).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_of(dt: datetime, tz: ZoneInfo) -> str:
    """A wall-clock datetime in tz (naive) -> UTC ISO, whole seconds."""
    aware = dt.replace(tzinfo=tz) if dt.tzinfo is None else dt
    u = datetime.fromtimestamp(round(aware.timestamp()), tz=UTC)
    return u.strftime("%Y-%m-%dT%H:%M:%SZ")


def _naive_in(jd: float, tz: ZoneInfo) -> datetime:
    return jd_to_dt(jd).astimezone(tz).replace(tzinfo=None)


# ── Scanning ──

def _bisect(pred, lo: float, hi: float, tol: float = SECOND / 4) -> float:
    """The instant between lo and hi where pred changes; pred(lo) != pred(hi)."""
    at_lo = pred(lo)
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if pred(mid) == at_lo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _changes(key, jd0: float, jd1: float, step: float) -> list:
    """Where an integer-valued key of the instant changes inside [jd0, jd1): (jd, before, after)."""
    out = []
    prev_jd, prev = jd0, key(jd0)
    jd = jd0
    while jd < jd1:
        jd = min(jd + step, jd1)
        cur = key(jd)
        if cur != prev:
            x = _bisect(lambda j, p=prev: key(j) == p, prev_jd, jd)
            if jd0 <= x < jd1:
                out.append((x, prev, cur))
        prev_jd, prev = jd, cur
    return out


def _wrap(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def _samples(pid: int, jd_from: float, jd_to: float, step: float) -> list:
    """The body's longitude at every step from jd_from to jd_to: [(jd, lon)]."""
    out, jd = [], jd_from
    while True:
        out.append((jd, _get_lon(jd, pid)))
        if jd >= jd_to:
            return out
        jd = min(jd + step, jd_to)


def _crossings(samples: list, pid: int, target: float) -> list:
    """Instants the body's longitude equals target between the samples, to the second."""
    out = []
    pj, pg = samples[0][0], _wrap(samples[0][1] - target)
    for jd, lon in samples[1:]:
        g = _wrap(lon - target)
        if (pg < 0) != (g < 0) and abs(g - pg) < 180:
            out.append(_bisect(lambda j: _wrap(_get_lon(j, pid) - target) < 0, pj, jd))
        pj, pg = jd, g
    return out


def _place(lon: float) -> dict:
    return {"longitude": round(lon % 360, 4), "sign": _sign_name(lon), "degree": round(_degree_in_sign(lon), 2)}


# ── Charts ──

def _natal_points(chart: dict) -> list:
    """The chart's planets (Sun..Pluto, North Node, Chiron where present), Ascendant, Midheaven."""
    pts = []
    for p in chart.get("planets", []):
        name = p.get("name")
        if (name in PLANETS or name in NATAL_EXTRA) and p.get("longitude") is not None:
            pts.append((name, float(p["longitude"]) % 360))
    for key, label in (("ascendant", "Ascendant"), ("midheaven", "Midheaven")):
        a = (chart.get("angles") or {}).get(key) or {}
        if a.get("longitude") is not None:
            pts.append((label, float(a["longitude"]) % 360))
    return pts


def _chart_tz(chart: dict) -> ZoneInfo:
    return ZoneInfo((chart.get("birthData") or {}).get("timezone") or "America/New_York")


def _birth_dt(chart: dict) -> datetime:
    """The birth instant, aware, in the chart's zone: julianDay if present, else the wall clock."""
    bd = chart.get("birthData") or {}
    tz = _chart_tz(chart)
    if bd.get("julianDay") not in (None, ""):
        return jd_to_dt(float(bd["julianDay"])).astimezone(tz)
    return datetime.fromisoformat(f"{bd['date']}T{bd.get('time', '12:00:00')}").replace(tzinfo=tz)


def _orb_max(planet: str, aspect: str, cap: float) -> float:
    o = min(ORB[planet], cap)
    if aspect == "Sextile":
        o = o * 2 / 3
    return round(o, 2)


def _targets(n_lon: float, angle: float) -> list:
    if angle in (0, 180):
        return [(n_lon + angle) % 360]
    return [(n_lon + angle) % 360, (n_lon - angle) % 360]


# ── The sky at an instant ──

def _part(absent: list, name: str, fn, *args):
    """Compute one part; a failure records its name in absent instead of raising."""
    try:
        return fn(*args)
    except Exception:
        absent.append(name)
        return None


def _planets_at(jd: float) -> list:
    out = []
    for name in PLANETS:
        lon, speed = _get_lon_speed(jd, PLANET_IDS[name])
        out.append({"planet": name, **_place(lon), "speed": round(speed, 4), "retrograde": speed < 0})
    return out


def _moon_at(jd: float) -> dict:
    lon = _get_lon(jd, swe.MOON)
    angle = (lon - _get_lon(jd, swe.SUN)) % 360
    return {
        **_place(lon),
        "phase_angle": round(angle, 2),
        "phase": PHASES[int(((angle + 22.5) % 360) // 45)],
        "age_days": round(angle / 360 * SYNODIC_MONTH, 2),
        "illumination": round(swe.pheno_ut(jd, swe.MOON, FLAGS)[1], 3),
    }


def _asc_lon(jd: float, lat: float, lon: float) -> float:
    return swe.houses(jd, lat, lon, b'P')[1][0]


def _ascendant_at(jd: float, lat: float, lon: float) -> dict:
    asc = _asc_lon(jd, lat, lon)
    idx = int((asc % 360) // 30)

    def same(j):
        return int((_asc_lon(j, lat, lon) % 360) // 30) == idx

    entered = leaves = None
    j = jd
    for _ in range(int(ASC_SCAN / ASC_STEP)):
        if not same(j - ASC_STEP):
            entered = _bisect(same, j - ASC_STEP, j)
            break
        j -= ASC_STEP
    j = jd
    for _ in range(int(ASC_SCAN / ASC_STEP)):
        if not same(j + ASC_STEP):
            leaves = _bisect(same, j, j + ASC_STEP)
            break
        j += ASC_STEP
    return {**_place(asc),
            "entered_at": iso_utc(entered) if entered is not None else None,
            "leaves_at": iso_utc(leaves) if leaves is not None else None}


def _transits_at(jd: float, chart: dict, cap: float, planets: list, aspects: list) -> list:
    points = _natal_points(chart)
    out = []
    for tp in planets:
        pid = PLANET_IDS[tp]
        t_lon = _get_lon(jd, pid)
        t_next = _get_lon(jd + APPLY_STEP.get(tp, 1.0), pid)
        span, step = EXACT_SPAN[tp], TRANSIT_STEP[tp]
        samples = None
        for point, n_lon in points:
            delta = _wrap(t_lon - n_lon)
            for asp in aspects:
                angle = ASPECTS[asp]
                orb_max = _orb_max(tp, asp, cap)
                orb = abs(abs(delta) - angle)
                if orb > orb_max:
                    continue
                orb_next = abs(_angular_sep(t_next, n_lon) - angle)
                target = (n_lon + angle) % 360 if delta >= 0 else (n_lon - angle) % 360
                if samples is None:
                    samples = _samples(pid, jd - span, jd + span, step)
                hits = _crossings(samples, pid, target)
                exact_at = min(hits, key=lambda x: abs(x - jd)) if hits else None
                out.append({
                    "transit_planet": tp,
                    "natal_point": point,
                    "aspect": asp,
                    "orb": round(orb, 2),
                    "orb_max": orb_max,
                    "applying": (exact_at > jd) if exact_at is not None else (orb_next < orb),
                    "exact": orb <= EXACT_ORB.get(tp, 0.5),
                    "exact_at": iso_utc(exact_at) if exact_at is not None else None,
                    "strength": round(1 - orb / orb_max, 2) if orb_max else 0.0,
                })
    out.sort(key=lambda t: (t["orb"], t["transit_planet"], t["natal_point"]))
    return out


def _profection_at(jd: float, chart: dict) -> dict:
    birth = _birth_dt(chart)
    now = jd_to_dt(jd).astimezone(birth.tzinfo)
    age = now.year - birth.year
    if (now.month, now.day, now.hour, now.minute, now.second) < \
       (birth.month, birth.day, birth.hour, birth.minute, birth.second):
        age -= 1
    asc = chart["angles"]["ascendant"]
    asc_idx = SIGN_NAMES.index(asc["sign"]) if asc.get("sign") in SIGN_NAMES \
        else int((float(asc["longitude"]) % 360) // 30)
    sign = SIGN_NAMES[(asc_idx + age % 12) % 12]
    return {"age": age, "house": age % 12 + 1, "sign": sign, "lord_of_year": zr.get_ruler(sign)}


def sky_at(jd: float, lat: Optional[float] = None, lon: Optional[float] = None,
           chart: Optional[dict] = None, orb: float = 3.0, planets: Optional[list] = None,
           aspects: Optional[list] = None, void_spans: Optional[list] = None,
           absent: Optional[list] = None) -> dict:
    """The sky at one instant: the at_start object of the reply."""
    absent = absent if absent is not None else []
    planets = planets or PLANETS
    aspects = aspects or list(ASPECTS)
    if void_spans is None:
        void_spans = _part(absent, "void", _void_spans, jd - 1, jd + 1) or []
    has_place = lat is not None and lon is not None
    return {
        "at": iso_utc(jd),
        "planets": _part(absent, "planets", _planets_at, jd),
        "moon": _part(absent, "moon", _moon_at, jd),
        "void": any(s["start_jd"] <= jd < s["end_jd"] for s in void_spans),
        "ascendant": _part(absent, "ascendant", _ascendant_at, jd, float(lat), float(lon)) if has_place else None,
        "transits": _part(absent, "transits", _transits_at, jd, chart, orb, planets, aspects) if chart else None,
        "profection": _part(absent, "profection", _profection_at, jd, chart) if chart else None,
    }


# ── Events inside a window ──

def _lunations(jd0: float, jd1: float) -> list:
    def key(j):
        return int(((_get_lon(j, swe.MOON) - _get_lon(j, swe.SUN)) % 360) // 90)
    out = []
    for x, _before, after in _changes(key, jd0, jd1, 0.25):
        out.append({"kind": LUNATIONS[after], "at": iso_utc(x), **_place(_get_lon(x, swe.MOON))})
    return out


def _ingresses(jd0: float, jd1: float, planets: list) -> list:
    out = []
    for name in planets:
        pid = PLANET_IDS[name]

        def key(j, pid=pid):
            return int((_get_lon(j, pid) % 360) // 30)
        for x, before, after in _changes(key, jd0, jd1, INGRESS_STEP[name]):
            out.append({"planet": name, "from_sign": SIGN_NAMES[before], "to_sign": SIGN_NAMES[after],
                        "at": iso_utc(x), "retrograde": _get_lon_speed(x, pid)[1] < 0})
    out.sort(key=lambda e: e["at"])
    return out


def _moon_gates(jd0: float, jd1: float) -> list:
    def key(j):
        return int(((_get_lon(j, swe.MOON) - 15) % 360) // 30)
    return [{"at": iso_utc(x), "sign": SIGN_NAMES[after], "degree": 15}
            for x, _before, after in _changes(key, jd0, jd1, 2 * HOUR)]


def _stations(jd0: float, jd1: float, planets: list) -> list:
    out = []
    for name in planets:
        if name not in STATION_STEP:
            continue
        pid = PLANET_IDS[name]

        def key(j, pid=pid):
            return int(_get_lon_speed(j, pid)[1] < 0)
        for x, _before, after in _changes(key, jd0, jd1, STATION_STEP[name]):
            out.append({"planet": name, "kind": "retrograde" if after else "direct",
                        "at": iso_utc(x), **{k: v for k, v in _place(_get_lon(x, pid)).items() if k != "longitude"}})
    out.sort(key=lambda e: e["at"])
    return out


def _eclipses(jd0: float, jd1: float, points: Optional[list]) -> list:
    """After ephemeris.eclipses, on Julian Days, clipped to [jd0, jd1)."""
    out = []
    runs = (
        ("Solar", swe.sol_eclipse_when_glob, swe.SUN,
         ((swe.ECL_TOTAL, "Total"), (swe.ECL_ANNULAR, "Annular"), (swe.ECL_PARTIAL, "Partial"),
          (swe.ECL_ANNULAR_TOTAL, "Hybrid"))),
        ("Lunar", swe.lun_eclipse_when, swe.MOON,
         ((swe.ECL_TOTAL, "Total"), (swe.ECL_PARTIAL, "Partial"), (swe.ECL_PENUMBRAL, "Penumbral"))),
    )
    for kind, when, body, subtypes in runs:
        jd = jd0 - 1
        for _ in range(400):
            try:
                res, tret = when(jd, FLAGS, 0)
            except Exception:
                break
            ecl_jd = tret[0]
            if ecl_jd >= jd1:
                break
            if ecl_jd >= jd0:
                lon = _get_lon(ecl_jd, body)
                names = [label for flag, label in subtypes if res & flag]
                ecl = {"type": kind, "subtype": " / ".join(names) if names else "Unknown",
                       "at": iso_utc(ecl_jd), **_place(lon), "natal_contacts": None}
                if points is not None:
                    ecl["natal_contacts"] = [
                        {"point": p, "orb": round(_angular_sep(lon, plon), 2)}
                        for p, plon in points if _angular_sep(lon, plon) <= 3.0]
                out.append(ecl)
            jd = ecl_jd + 1
    out.sort(key=lambda e: e["at"])
    return out


def _void_spans(jd0: float, jd1: float) -> list:
    """Void of course spans from voc.calculate_voc over the New York dates around [jd0, jd1],
    as Julian Days: [{start_jd, end_jd, from_sign, to_sign, last_aspect}]."""
    out, seen = [], set()
    chunk_from = jd0 - 1
    while chunk_from < jd1 + 1:
        chunk_to = min(chunk_from + VOID_CHUNK, jd1 + 1)
        d0 = jd_to_dt(chunk_from).astimezone(TZ).strftime("%Y-%m-%d")
        d1 = jd_to_dt(chunk_to).astimezone(TZ).strftime("%Y-%m-%d")
        for v in voc.calculate_voc(d0, d1, "America/New_York"):
            key = (v["start"], v["end"])
            if key in seen:
                continue
            seen.add(key)
            s = _dt_to_jd(datetime.strptime(v["start"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ))
            e = _dt_to_jd(datetime.strptime(v["end"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ))
            out.append({"start_jd": s, "end_jd": e, "from_sign": v["previousSign"],
                        "to_sign": v["newSign"], "last_aspect": v["lastAspect"]})
        chunk_from = chunk_to + 1
    out.sort(key=lambda s: s["start_jd"])
    return out


def _void_events(spans: list, jd0: float, jd1: float) -> list:
    """The spans overlapping [jd0, jd1), clipped to it."""
    return [{"start": iso_utc(max(s["start_jd"], jd0)), "end": iso_utc(min(s["end_jd"], jd1)),
             "from_sign": s["from_sign"], "to_sign": s["to_sign"], "last_aspect": s["last_aspect"]}
            for s in spans if s["start_jd"] < jd1 and s["end_jd"] > jd0]


def _exact_transits(jd0: float, jd1: float, chart: dict, planets: list, aspects: list, cap: float) -> list:
    points = _natal_points(chart)
    out = []
    for tp in planets:
        pid = PLANET_IDS[tp]
        samples = _samples(pid, jd0, jd1, TRANSIT_STEP[tp])
        for point, n_lon in points:
            for asp in aspects:
                for target in _targets(n_lon, ASPECTS[asp]):
                    for x in _crossings(samples, pid, target):
                        if jd0 <= x < jd1:
                            out.append({"transit_planet": tp, "natal_point": point, "aspect": asp,
                                        "at": iso_utc(x), "orb_max": _orb_max(tp, asp, cap)})
    out.sort(key=lambda e: (e["at"], e["transit_planet"], e["natal_point"]))
    return out


def _turnings(jd0: float, jd1: float) -> list:
    def key(j):
        return int((_get_lon(j, swe.SUN) % 360) // 90)
    return [{"kind": TURNINGS[after], "at": iso_utc(x), "longitude": round(_get_lon(x, swe.SUN) % 360, 4)}
            for x, _before, after in _changes(key, jd0, jd1, 1.0)]


def sky_events(jd0: float, jd1: float, kinds: Optional[list] = None, planets: Optional[list] = None,
               aspects: Optional[list] = None, chart: Optional[dict] = None, orb: float = 3.0,
               void_spans: Optional[list] = None, absent: Optional[list] = None) -> dict:
    """Everything that happens inside [jd0, jd1): the events object of the reply. A kind not
    asked for is an empty list; transits are null without a chart."""
    absent = absent if absent is not None else []
    kinds = list(kinds) if kinds else list(KINDS)
    planets = planets or PLANETS
    aspects = aspects or list(ASPECTS)
    points = _natal_points(chart) if chart else None
    out = {k: [] for k in KINDS}
    if "lunations" in kinds:
        out["lunations"] = _part(absent, "lunations", _lunations, jd0, jd1)
    if "ingresses" in kinds:
        out["ingresses"] = _part(absent, "ingresses", _ingresses, jd0, jd1, planets)
    if "moon_gates" in kinds:
        out["moon_gates"] = _part(absent, "moon_gates", _moon_gates, jd0, jd1)
    if "stations" in kinds:
        out["stations"] = _part(absent, "stations", _stations, jd0, jd1, planets)
    if "eclipses" in kinds:
        out["eclipses"] = _part(absent, "eclipses", _eclipses, jd0, jd1, points)
    if "void" in kinds:
        if void_spans is None:
            void_spans = _part(absent, "void", _void_spans, jd0, jd1)
        out["void"] = _void_events(void_spans, jd0, jd1) if void_spans is not None else None
    if "turnings" in kinds:
        out["turnings"] = _part(absent, "turnings", _turnings, jd0, jd1)
    if not chart:
        out["transits"] = None
    elif "transits" in kinds:
        out["transits"] = _part(absent, "transits", _exact_transits, jd0, jd1, chart, planets, aspects, orb)
    return out


# ── Zodiacal releasing over a window ──

def _period_dict(p, tz: ZoneInfo) -> dict:
    d = p.to_dict()
    d["start"] = _iso_of(p.start, tz)
    d["end"] = _iso_of(p.end, tz)
    d["loosing_at"] = _iso_of(p.loosing_at, tz) if p.loosing_at else None
    return d


def zr_window(chart: dict, jd0: float, jd1: float, lot: str = "spirit", levels=(2,)) -> dict:
    """The releasing periods of one lot overlapping [jd0, jd1): the releasing[lot] object.
    periods is the finest level's list, levels every requested level, frame the period one
    level above the finest at jd0 (None at L1 or before the birth)."""
    tz = _chart_tz(chart)
    wanted = sorted(set(int(x) for x in levels))
    start_naive, end_naive = _naive_in(jd0, tz), _naive_in(jd1, tz)
    found = zr.zr_periods_for_chart(chart, start_naive, end_naive, lot, wanted)
    by_level = {str(n): [_period_dict(p, tz) for p in found.get(f"L{n}", [])] for n in wanted}
    finest = wanted[-1]
    frame = None
    if finest > 1:
        try:
            above = getattr(zr.zr_for_chart(chart, start_naive, lot), f"L{finest - 1}")
            frame = {"level": above.level, "sign": above.sign, "ruler": above.ruler,
                     "start": _iso_of(above.start, tz), "end": _iso_of(above.end, tz),
                     "is_peak": above.is_peak, "peak_type": above.peak_type}
        except ValueError:
            frame = None
    lot_sign, _degree, _birth, fortune_sign = zr._chart_lot_inputs(chart, lot)
    return {
        "lot": lot,
        "lot_sign": lot_sign,
        "release_sign": zr.release_sign_for(lot_sign, lot, fortune_sign),
        "frame": frame,
        "periods": by_level[str(finest)],
        "levels": by_level,
    }


# ── The whole reply ──

def _as_list(v) -> Optional[list]:
    if v is None:
        return None
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return list(v)


def _pick(values, allowed, what: str) -> Optional[list]:
    """Case-insensitive selection from allowed, in allowed's order; None when nothing is asked."""
    values = _as_list(values)
    if not values:
        return None
    by_lower = {a.lower(): a for a in allowed}
    chosen = []
    for v in values:
        key = str(v).strip().lower().replace(" ", "_") if what == "kind" else str(v).strip().lower()
        if key not in by_lower:
            raise ValueError(f"unknown {what}: {v}")
        chosen.append(by_lower[key])
    return [a for a in allowed if a in chosen]


def sky_window(start: str, end: str, name: Optional[str] = None, lat: Optional[float] = None,
               lon: Optional[float] = None, kinds=None, planets=None, aspects=None,
               zr_levels=None, lots=None, orb: Optional[float] = None) -> dict:
    """The sky over [start, end): at_start, events, releasing and absent, every instant UTC."""
    try:
        jd0, jd1 = parse_instant(start), parse_instant(end)
    except ValueError as ex:
        return {"error": f"bad instant: {ex}"}
    if jd1 <= jd0:
        return {"error": "end must be after start"}
    years = (jd1 - jd0) / 365.25
    if years > MAX_YEARS:
        return {"error": f"window too long: {years:.1f} years (max {MAX_YEARS} years)"}
    try:
        kinds = _pick(kinds, KINDS, "kind") or list(KINDS)
        planets = _pick(planets, PLANETS, "planet") or PLANETS
        aspects = _pick(aspects, list(ASPECTS), "aspect") or list(ASPECTS)
        lots = _pick(lots, LOTS, "lot") or list(LOTS)
        levels = sorted(set(int(x) for x in (_as_list(zr_levels) or [])))
        if levels and (levels[0] < 1 or levels[-1] > zr.MAX_LEVEL):
            raise ValueError(f"zr_levels must be within 1..{zr.MAX_LEVEL}")
        cap = 3.0 if orb is None else float(orb)
        if (lat is None) != (lon is None):
            raise ValueError("lat and lon go together")
    except (TypeError, ValueError) as ex:
        return {"error": str(ex)}

    chart = None
    if name:
        name = str(name).strip().lower()
        try:
            chart = _load_chart(name)
        except FileNotFoundError:
            return {"error": f"Chart not found: {name}"}

    absent: list = []
    # The void scan costs about a tenth of a second per Moon sign, so the whole window is
    # scanned only when void is asked for; the start alone needs the day around it.
    void_spans = _part(absent, "void", _void_spans, jd0, jd1) if "void" in kinds else None
    at_spans = void_spans if void_spans is not None else _part(absent, "void", _void_spans, jd0, jd0)
    at_start = sky_at(jd0, lat, lon, chart, cap, planets, aspects, at_spans or [], absent)
    events = sky_events(jd0, jd1, kinds, planets, aspects, chart, cap, void_spans, absent)
    releasing = None
    if chart and levels:
        releasing = {}
        for lot in lots:
            releasing[lot] = _part(absent, f"releasing.{lot}", zr_window, chart, jd0, jd1, lot, levels)
    seen = set()
    absent = [a for a in absent if not (a in seen or seen.add(a))]
    return {
        "tz": "UTC",
        "start": iso_utc(jd0),
        "end": iso_utc(jd1),
        "chart": name or None,
        "at_start": at_start,
        "events": events,
        "releasing": releasing,
        "absent": absent,
    }


# ── MCP ──

def register_sky(mcp) -> None:
    """Add the sky window tool to Stella's FastMCP server."""

    @mcp.tool()
    async def get_sky_window(
        start: str,
        end: str,
        name: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        kinds: Optional[Union[list[str], str]] = None,
        planets: Optional[Union[list[str], str]] = None,
        aspects: Optional[Union[list[str], str]] = None,
        zr_levels: Optional[Union[list[int], str]] = None,
        lots: Optional[Union[list[str], str]] = None,
        orb: Optional[float] = None,
    ) -> str:
        """The sky over a window of time in one call: what stands at the start (planets, the
        Moon and her phase, void of course, the rising sign, transits to a stored chart with
        their orbs, the annual profection), what moves inside it (lunations, ingresses, the
        Moon crossing 15 degrees of a sign, stations, eclipses, void of course spans, exact
        transits, equinoxes and solstices) and the zodiacal releasing periods overlapping it.

        Local ephemeris and chart store only, no Helios. Every instant in the reply is UTC
        ISO 8601 with Z; the window is half open [start, end). Parts that fail are named in
        "absent" rather than raising; a window over 13 years is an error.

        Args:
            start: Window start, ISO 8601 (offset or Z honored; naive = America/New_York)
            end: Window end, exclusive, same form
            name: Stored chart name for transits, profection and releasing (default none)
            lat: Latitude in degrees, with lon, for the rising sign
            lon: Longitude in degrees, east positive
            kinds: Event kinds to compute, list or comma separated: lunations, ingresses,
                moon_gates, stations, eclipses, void, transits, turnings (default all)
            planets: Bodies for ingresses, stations and transits, e.g. "Moon,Sun" (default all)
            aspects: Aspects for transits: Conjunction, Sextile, Square, Trine, Opposition (default all)
            zr_levels: Releasing levels 1-5, e.g. [4,5] or "4,5" (default none)
            lots: "spirit", "fortune" or both (default both)
            orb: Cap in degrees for transits in orb at the start (default 3.0)
        """
        try:
            result = await asyncio.to_thread(
                sky_window, start, end, name, lat, lon, kinds, planets, aspects, zr_levels, lots, orb)
            return json.dumps(result, default=str)
        except Exception as ex:
            return json.dumps({"error": str(ex)})


# ── CLI ──

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="The sky over a window of time, as JSON.")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--name")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--kinds")
    ap.add_argument("--planets")
    ap.add_argument("--aspects")
    ap.add_argument("--zr-levels", dest="zr_levels")
    ap.add_argument("--lots")
    ap.add_argument("--orb", type=float)
    a = ap.parse_args()
    print(json.dumps(sky_window(a.start, a.end, a.name, a.lat, a.lon, a.kinds, a.planets, a.aspects,
                                a.zr_levels, a.lots, a.orb), indent=1, default=str))
