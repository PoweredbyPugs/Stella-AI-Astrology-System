"""SkyKi hour: one Ki hour read against the sky and a stored chart, in one call.

Joins, at one instant, the solar Ki hour that holds it (its window, the global and personal
Ki of the hour and the day), the moment chart (rising sign, sect, the Moon's phase and void
of course, the seven classical planets with essential dignity, sect and whole-sign houses
from the rising sign and from the natal rising sign, the planetary hours across the window),
the natal reading of the rising sign and its ruler, and zodiacal releasing at Levels 4 and 5
from Spirit and Fortune. Facts only, no interpretation.

Local only: pyswisseph (Moshier where the ephemeris files are missing) and the chart store
under charts/; no HTTP. Julian Days inside; every time in the reply is ISO 8601 in
America/New_York with its offset and whole seconds (never Z, never naive). A naive `at` is
America/New_York; no `at` is now.

Any block that cannot be computed is None and named in `absent`; the call never raises. An
error reply comes back only for a missing name, a chart that is not found or cannot be read,
an unreadable `at`, or a Ki hour window that cannot be computed.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import ki
import ki_solar
import sky
import zr
from dignity import essential_dignities, sect_block, sect_status
from ephemeris import SIGN_NAMES, _load_chart, planetary_hours

SEVEN = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
NATAL_PLANETS = tuple(sky.PLANETS) + sky.NATAL_EXTRA
LOT_LABELS = (("fortune", "Lot of Fortune"), ("spirit", "Lot of Spirit"))
ORB_CAP = 3.0
HOURS_FMT = "%Y-%m-%d %H:%M:%S"


# ── Times ──

def _iso(x, tz=sky.TZ) -> Optional[str]:
    """A Julian Day, an aware datetime or an ISO string (Z or offset) -> ISO in tz with its
    offset, whole seconds. None stays None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        dt = sky.jd_to_dt(float(x))
    elif isinstance(x, datetime):
        dt = x if x.tzinfo else x.replace(tzinfo=tz)
    else:
        dt = datetime.fromisoformat(str(x).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz).replace(microsecond=0).isoformat()


def _jd(s: str) -> float:
    return sky.parse_instant(str(s).replace("Z", "+00:00"))


def _ny_date(jd: float) -> date:
    return sky.jd_to_dt(jd).astimezone(sky.TZ).date()


def _hours_dt(s: str) -> datetime:
    """A planetary-hours string ("%Y-%m-%d %H:%M:%S %Z", New York) -> aware datetime."""
    return datetime.strptime(s[:19], HOURS_FMT).replace(tzinfo=sky.TZ)


def _block(absent: list, name: str, fn, *args):
    """Compute one block; a failure records its name in absent and gives None."""
    try:
        return fn(*args)
    except Exception:
        absent.append(name)
        return None


# ── Helpers ──

def _is_day(jd: float, lat: float, lon: float) -> bool:
    """True iff sunrise <= at < sunset on the New York date of at."""
    ph = planetary_hours(_ny_date(jd).isoformat(), lat, lon)
    at = sky.jd_to_dt(jd).astimezone(sky.TZ)
    return _hours_dt(ph["sunrise"]) <= at < _hours_dt(ph["sunset"])


def _planetary_hours_overlapping(jd0: float, jd1: float, lat: float, lon: float) -> list:
    """Every planetary hour overlapping [jd0, jd1), from the New York date of jd0 and the date
    before it (night hours run past midnight), deduplicated by start and sorted."""
    t0 = sky.jd_to_dt(jd0).astimezone(sky.TZ)
    t1 = sky.jd_to_dt(jd1).astimezone(sky.TZ)
    d = t0.date()
    seen = {}
    for day in (d - timedelta(days=1), d):
        for h in planetary_hours(day.isoformat(), lat, lon)["hours"]:
            start, end = _hours_dt(h["start"]), _hours_dt(h["end"])
            if end > t0 and start < t1 and start not in seen:
                seen[start] = {"ruler": h["ruler"], "start": _iso(start), "end": _iso(end)}
    return [seen[k] for k in sorted(seen)]


def _natal_rising_sign(chart: dict) -> str:
    asc = chart["angles"]["ascendant"]
    if asc.get("sign") in SIGN_NAMES:
        return asc["sign"]
    return SIGN_NAMES[int((float(asc["longitude"]) % 360) // 30)]


def _natal_points(chart: dict) -> list:
    """(name, sign) for the chart's planets (Sun..Pluto, North Node, Chiron where present),
    then "Lot of Fortune" and "Lot of Spirit" where the chart has them."""
    planets = chart.get("planets")
    if not isinstance(planets, list):
        raise ValueError("chart planets are not in the list format")
    pts = [(p["name"], p["sign"]) for p in planets if p.get("name") in NATAL_PLANETS and p.get("sign")]
    lots = chart.get("lots") or {}
    for key, label in LOT_LABELS:
        if (lots.get(key) or {}).get("sign"):
            pts.append((label, lots[key]["sign"]))
    return pts


def _peak(label) -> Optional[str]:
    """"Major Peak" -> "major", "Minor Peak" -> "minor", None -> None."""
    return label.split()[0].lower() if label else None


# ── Blocks ──

def _window(jd: float) -> dict:
    w0, w1 = ki_solar.solar_stack(jd)["spans"]["hour"]
    return {"start": _iso(w0), "end": _iso(w1), "start_jd": w0, "end_jd": w1}


def _ki(jd: float, chart: dict) -> dict:
    birth = date.fromisoformat(chart["birthData"]["date"])
    target = sky.jd_to_dt(jd).astimezone(sky.TZ).replace(tzinfo=None)
    k = ki.calculate_daily_ki(birth, target)

    def side(s):
        return {lvl: {"number": k[s][lvl]["ki"], "trigram": k[s][lvl]["info"]["name"],
                      "element": k[s][lvl]["info"]["element"]} for lvl in ("hour", "day")}
    return {"natal_year": k["natal_year_ki"], "global": side("global"), "personal": side("personal")}


def _rising(jd: float, lat: float, lon: float) -> dict:
    a = sky._ascendant_at(jd, float(lat), float(lon))
    return {"sign": a["sign"], "ruler": zr.get_ruler(a["sign"]),
            "entered_at": _iso(a["entered_at"]), "leaves_at": _iso(a["leaves_at"])}


def _moon(jd: float, spans: Optional[list]) -> dict:
    """Phase always; void None when the void spans could not be computed."""
    out = {"phase": sky._moon_at(jd)["phase"], "void": None if spans is None else False}
    for s in spans or []:
        if s["start_jd"] <= jd < s["end_jd"]:
            out.update(void=True, void_start=_iso(s["start_jd"]), void_end=_iso(s["end_jd"]))
            break
    return out


def _planets(transit: list, is_day: bool, rising: str, natal_rising: str) -> list:
    out = []
    for p in transit[:len(SEVEN)]:
        lon = p["longitude"]
        d = essential_dignities(p["planet"], lon, is_day)
        out.append({
            "planet": p["planet"], "sign": p["sign"], "degree": round(p["degree"], 2),
            "retrograde": p["retrograde"], "score": d["score"], "condition": d["condition"],
            "dignities": d["dignities"], "sect": sect_status(p["planet"], is_day),
            "house_from_rising": zr.house_from(p["sign"], rising),
            "natal_house": zr.house_from(p["sign"], natal_rising),
        })
    return out


def _natal(jd: float, chart: dict, rising: str, natal_rising: str, transit_sign: dict) -> dict:
    points = _natal_points(chart)
    natal_sign = dict(points)
    ruler = zr.get_ruler(rising)
    contacts = sky._transits_at(jd, chart, ORB_CAP, [ruler], list(sky.ASPECTS))
    return {
        "rising_sign_house": zr.house_from(rising, natal_rising),
        "in_rising_sign": [n for n, s in points if s == rising],
        "ruler": {
            "planet": ruler,
            "is_chart_ruler": ruler == zr.get_ruler(natal_rising),
            "natal": {"sign": natal_sign[ruler], "house": zr.house_from(natal_sign[ruler], natal_rising)},
            "transit": {"sign": transit_sign[ruler],
                        "house": zr.house_from(transit_sign[ruler], natal_rising)},
            "contacts": [{"natal_point": c["natal_point"], "aspect": c["aspect"].lower(),
                          "orb": c["orb"], "applying": c["applying"], "exact_at": _iso(c["exact_at"])}
                         for c in contacts],
        },
    }


def _period(p: dict) -> dict:
    return {"sign": p["sign"], "ruler": p["ruler"], "start": _iso(p["start"]), "end": _iso(p["end"]),
            "peak": _peak(p["peak_type"]), "house_from_fortune": p["house_from_fortune"],
            "angularity": p["angularity"], "loosing_of_bond": p["is_loosing_of_bond"],
            "loosing_at": _iso(p["loosing_at"])}


def _l5_natal(sign: str, ruler: str, natal_rising: str, natal_sign: dict, transit_sign: dict) -> dict:
    return {
        "natal_house": zr.house_from(sign, natal_rising),
        "natal_planets": [n for n, s in natal_sign.items() if s == sign and n in NATAL_PLANETS],
        "ruler_natal": {"sign": natal_sign[ruler], "house": zr.house_from(natal_sign[ruler], natal_rising)},
        "ruler_transit": {"sign": transit_sign[ruler],
                          "house": zr.house_from(transit_sign[ruler], natal_rising)},
    }


def _releasing(jd: float, w0: float, w1: float, chart: dict, natal_rising: str,
               transit_sign: dict, absent: list) -> dict:
    try:
        natal_sign = dict(_natal_points(chart))
    except Exception:
        natal_sign = None
    natal_missing = False
    out = {"fortune_sign": chart["lots"]["fortune"]["sign"]}
    for lot in ("spirit", "fortune"):
        z = sky.zr_window(chart, w0, w1, lot, levels=(4, 5))
        l4s = [p for p in z["levels"]["4"] if _jd(p["end"]) > w0 and _jd(p["start"]) < w1]
        l4 = next((p for p in l4s if _jd(p["start"]) <= jd < _jd(p["end"])), l4s[0])
        l5 = []
        for p in z["levels"]["5"]:
            if not (_jd(p["end"]) > w0 and _jd(p["start"]) < w1):
                continue
            row = _period(p)
            try:
                row.update(_l5_natal(p["sign"], p["ruler"], natal_rising, natal_sign, transit_sign))
            except Exception:
                natal_missing = True
                row.update(natal_house=None, natal_planets=None, ruler_natal=None, ruler_transit=None)
            l5.append(row)
        out[lot] = {"l4": _period(l4), "l5": l5}
    if natal_missing:
        absent.append("releasing_natal")
    return out


def _rising_boundaries(jd: float, w0: float, w1: float, lat: float, lon: float) -> list:
    """Every ascendant sign change strictly inside (w0, w1): (jd, from_sign, to_sign), walked
    forward through leaves_at and backward through entered_at from the sign at jd."""
    step = 30 * sky.SECOND
    out = []
    here = sky._ascendant_at(jd, float(lat), float(lon))
    cur = here
    while cur["leaves_at"] is not None and w0 < _jd(cur["leaves_at"]) < w1:
        t = _jd(cur["leaves_at"])
        nxt = sky._ascendant_at(t + step, float(lat), float(lon))
        out.append((t, cur["sign"], nxt["sign"]))
        cur = nxt
    cur = here
    while cur["entered_at"] is not None and w0 < _jd(cur["entered_at"]) < w1:
        t = _jd(cur["entered_at"])
        prev = sky._ascendant_at(t - step, float(lat), float(lon))
        out.append((t, prev["sign"], cur["sign"]))
        cur = prev
    return sorted(out)


def _changes(jd: float, w0: float, w1: float, lat: float, lon: float, rising: Optional[dict],
             hours: Optional[list], releasing: Optional[dict], spans: Optional[list]) -> list:
    out = []

    def inside(t):
        return t is not None and w0 < _jd(t) < w1

    def add(at, what, frm, to):
        out.append({"at": _iso(at), "what": what, "from": frm, "to": to})

    if rising:
        for t, frm, to in _rising_boundaries(jd, w0, w1, lat, lon):
            add(t, "rising_sign", frm, to)
    if hours:
        for a, b in zip(hours, hours[1:]):
            if inside(b["start"]):
                add(b["start"], "planetary_hour", a["ruler"], b["ruler"])
    if releasing:
        for lot in ("spirit", "fortune"):
            l5 = releasing[lot]["l5"]
            for a, b in zip(l5, l5[1:]):
                if inside(b["start"]):
                    add(b["start"], f"{lot}_l5", a["sign"], b["sign"])
    for s in spans or []:
        if w0 < s["start_jd"] < w1:
            add(s["start_jd"], "moon_void", "aspecting", "void")
        if w0 < s["end_jd"] < w1:
            add(s["end_jd"], "moon_void", "void", "aspecting")
    out.sort(key=lambda c: (_jd(c["at"]), c["what"]))
    return out


# ── The whole reply ──

def skyki_hour(name: str, at: Optional[str] = None, lat: float = None, lon: float = None) -> dict:
    """One Ki hour, read at `at` for the stored chart `name` at (lat, lon)."""
    if not name:
        return {"error": "name is required"}
    try:
        chart = _load_chart(name)
    except FileNotFoundError:
        return {"error": f"chart '{name}' not found"}
    except ValueError as e:  # json.JSONDecodeError is a ValueError
        return {"error": f"chart '{name}' cannot be read: {e}"}
    try:
        jd = sky.parse_instant(at) if at else sky._dt_to_jd(datetime.now(timezone.utc))
    except Exception:
        return {"error": f"cannot read at: {at!r}"}

    try:
        window = _window(jd)
    except Exception as e:
        return {"error": f"cannot compute the Ki hour window: {e}"}

    absent: list = []
    w0, w1 = window.pop("start_jd"), window.pop("end_jd")

    natal_rising = _block(absent, "natal", _natal_rising_sign, chart)
    transit = _block(absent, "planets", sky._planets_at, jd)
    transit_sign = {p["planet"]: p["sign"] for p in transit} if transit else {}
    spans = _block(absent, "moon_void", sky._void_spans, jd - 1, jd + 1)

    rising = _block(absent, "rising", _rising, jd, lat, lon)
    is_day = _block(absent, "sect", _is_day, jd, lat, lon)
    moon = _block(absent, "moon", _moon, jd, spans)
    planets = _block(absent, "planets", _planets, transit, is_day, rising["sign"], natal_rising) \
        if transit and rising and is_day is not None and natal_rising else None
    if planets is None and "planets" not in absent:
        absent.append("planets")
    hours = _block(absent, "planetary_hours", _planetary_hours_overlapping, w0, w1, lat, lon)

    natal = _block(absent, "natal", _natal, jd, chart, rising["sign"], natal_rising, transit_sign) \
        if rising and natal_rising else None
    if natal is None and "natal" not in absent:
        absent.append("natal")
    releasing = _block(absent, "releasing", _releasing, jd, w0, w1, chart, natal_rising, transit_sign, absent)
    changes = _block(absent, "changes", _changes, jd, w0, w1, lat, lon, rising, hours,
                     releasing, spans)

    return {
        "chart": name,
        "at": _iso(jd),
        "window": window,
        "ki": _block(absent, "ki", _ki, jd, chart),
        "moment": {
            "rising": rising,
            "sect": sect_block(is_day) if is_day is not None else None,
            "moon": moon,
            "planets": planets,
            "planetary_hours": hours,
        },
        "natal": natal,
        "releasing": releasing,
        "changes": changes,
        "absent": sorted(set(absent), key=absent.index),
    }
