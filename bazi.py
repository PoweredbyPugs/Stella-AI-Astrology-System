"""bazi — traditional Zi Ping Four Pillars (八字) on Stella.

Settled mechanics (docs/superpowers/specs/2026-11-10-bazi-design.md):
    year   changes at the exact Lichun instant (Sun at 315°); 1984 is 甲子
    month  changes at the twelve jie (Sun at 15° of each sign); 寅 opens at Lichun
    day    sexagenary index (JDN + 49) mod 60, 甲子 = 0; 2000-01-01 is 戊午
    hour   twelve double-hours, 子 spanning 23:00–01:00
Month stems by the Five Tigers rule (五虎遁), hour stems by the Five Rats rule (五鼠遁).

Only the solar-term boundaries are shared with the Ki calendar. Nothing else is.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import swisseph as swe

from bazi_tables import BRANCHES, NAYIN, NAYIN_ELEMENT, STEMS
from ki_calendar import boundaries_jd, lichun_jd

DAY_BOUNDARIES = ("23:00", "midnight")


# ── Sexagenary arithmetic ───────────────────────────────────────────────────

def sexagenary_index(stem: int, branch: int) -> int:
    """The index 0–59 whose stem is ``stem`` and branch is ``branch``."""
    return (6 * stem - 5 * branch) % 60


def sexagenary(index: int) -> dict:
    index %= 60
    s, b = STEMS[index % 10], BRANCHES[index % 12]
    return {
        "index": index,
        "stem": {"index": index % 10, **s},
        "branch": {"index": index % 12, **b},
        "cn": s["cn"] + b["cn"],
        "pinyin": f"{s['pinyin']} {b['pinyin']}",
        "nayin": NAYIN[index],
        "nayin_element": NAYIN_ELEMENT[index],
    }


def day_index_from_jdn(jdn: int) -> int:
    return (jdn + 49) % 60


def jdn_of(d: date) -> int:
    """Julian Day Number of a proleptic Gregorian civil date (2000-01-01 → 2451545)."""
    return d.toordinal() + 1721425


# ── Year and month from the Sun ─────────────────────────────────────────────

def _jd_ut(dt: datetime) -> float:
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def bazi_year_at(jd_ut: float) -> int:
    """The calendar year whose Lichun opened the BaZi year containing ``jd_ut``."""
    y = swe.revjul(jd_ut)[0]
    return y if jd_ut >= lichun_jd(y) else y - 1


def year_index(jd_ut: float) -> int:
    return (bazi_year_at(jd_ut) - 1984) % 60


def month_number(jd_ut: float) -> int:
    """0 for the 寅 month (opens at Lichun) … 11 for the 丑 month."""
    y = bazi_year_at(jd_ut)
    bounds = boundaries_jd(y)
    return sum(1 for b in bounds[1:12] if jd_ut >= b)


def month_index(jd_ut: float, year_idx: int) -> int:
    m = month_number(jd_ut)
    tiger_stem = ((year_idx % 10) % 5) * 2 + 2       # 五虎遁: 甲己→丙, 乙庚→戊, 丙辛→庚, 丁壬→壬, 戊癸→甲
    return sexagenary_index((tiger_stem + m) % 10, (2 + m) % 12)


# ── Day and hour ────────────────────────────────────────────────────────────

def hour_branch_of(t: time) -> int:
    return ((t.hour + 1) // 2) % 12


def hour_index(day_idx: int, hour_branch: int) -> int:
    rat_stem = ((day_idx % 10) % 5) * 2            # 五鼠遁: 甲己→甲, 乙庚→丙, 丙辛→戊, 丁壬→庚, 戊癸→壬
    return sexagenary_index((rat_stem + hour_branch) % 10, hour_branch)


def pillars_from_civil(local: datetime, day_boundary: str = "23:00",
                       instant: Optional[datetime] = None) -> dict:
    """Four pillars for a tz-aware local datetime read as clock time.

    ``day_boundary`` "23:00": the day pillar changes at the start of the Zi hour.
    "midnight": the day pillar keeps the civil date until 00:00, and the 23:00–00:00 hour
    stem is derived from the next day's stem (早子/晚子 convention).
    ``instant``: the true instant for the year and month pillars when ``local`` is an
    apparent-solar-time reading rather than the clock (default: ``local`` itself).
    """
    if day_boundary not in DAY_BOUNDARIES:
        raise ValueError(f"day_boundary must be one of {DAY_BOUNDARIES}, not {day_boundary!r}")
    if local.tzinfo is None:
        raise ValueError("local datetime must be timezone-aware")

    jd = _jd_ut(instant or local)
    y_idx = year_index(jd)
    m_idx = month_index(jd, y_idx)

    civil = local.date()
    late_zi = local.hour == 23
    next_day = date.fromordinal(civil.toordinal() + 1)
    stem_day = next_day if late_zi else civil
    pillar_day = civil if (day_boundary == "midnight" or not late_zi) else next_day

    d_idx = day_index_from_jdn(jdn_of(pillar_day))
    h_idx = hour_index(day_index_from_jdn(jdn_of(stem_day)), hour_branch_of(local.time()))

    return {
        "year": sexagenary(y_idx),
        "month": sexagenary(m_idx),
        "day": sexagenary(d_idx),
        "hour": sexagenary(h_idx),
    }


# ── Birth data ──────────────────────────────────────────────────────────────

GENDERS = {"m": "male", "male": "male", "man": "male", "男": "male",
           "f": "female", "female": "female", "woman": "female", "女": "female"}


def normalise_gender(value) -> Optional[str]:
    if value is None:
        return None
    return GENDERS.get(str(value).strip().lower())


@dataclass
class BirthData:
    local: datetime                 # tz-aware clock time of birth
    lat: Optional[float]
    lon: Optional[float]
    tz: Optional[str]               # IANA zone name, or None when the chart carried none
    gender: Optional[str]           # "male" / "female" / None
    source: str
    notes: list = field(default_factory=list)


def _jd_to_utc(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd)
    return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(seconds=round(h * 3600))


def birth_from_chart(chart: dict, gender: Optional[str] = None) -> BirthData:
    """Birth data from either stored-chart shape (Helios ``birthInfo`` or legacy ``birthData``)."""
    name = chart.get("name", "chart")
    notes = []
    if "birthInfo" in chart:
        info = chart["birthInfo"]
        naive = datetime.strptime(info["dateTime"], "%B %d, %Y %I:%M:%S %p")
        coords = info.get("coordinates") or {}
        lat, lon = coords.get("latitude"), coords.get("longitude")
        tz = info.get("timezone")
        jd = info.get("julianDay")
    elif "birthData" in chart:
        info = chart["birthData"]
        naive = datetime.fromisoformat(f"{info['date']}T{info['time']}")
        loc = info.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        tz = info.get("timezone")
        jd = float(info["julianDay"]) if info.get("julianDay") else None
    else:
        raise ValueError(f"Chart '{name}' has no birthInfo or birthData")

    if tz:
        local = naive.replace(tzinfo=ZoneInfo(tz))
    elif jd:
        offset = naive - _jd_to_utc(float(jd)).replace(tzinfo=None)
        offset = timedelta(minutes=round(offset.total_seconds() / 60))
        local = naive.replace(tzinfo=timezone(offset))
        notes.append(f"chart has no time zone; birth time read with the chart's own UT offset ({offset})")
    else:
        local = naive.replace(tzinfo=timezone.utc)
        notes.append("chart has no time zone or Julian Day; birth time read as UT")

    g = normalise_gender(gender) if gender is not None else normalise_gender(chart.get("gender"))
    return BirthData(local, lat, lon, tz, g, name, notes)


# ── True solar time ─────────────────────────────────────────────────────────

def apparent_solar_time(local: datetime, lon: float) -> tuple:
    """Apparent (true) solar time for a tz-aware clock reading at longitude ``lon``.

    Standard time (DST removed) + 4 min per degree east of the zone's standard meridian
    + the equation of time. Returns (apparent datetime, parts dict).
    """
    off = local.utcoffset() or timedelta()
    dst = local.dst() or timedelta()
    std = off - dst
    std_hours = std.total_seconds() / 3600
    longitude_minutes = 4 * (lon - 15 * std_hours)
    equation_minutes = swe.time_equ(_jd_ut(local)) * 1440
    standard = local - dst
    apparent = standard + timedelta(minutes=longitude_minutes + equation_minutes)
    return apparent, {
        "standard_offset_hours": std_hours,
        "dst_minutes": dst.total_seconds() / 60,
        "longitude_minutes": round(longitude_minutes, 2),
        "equation_minutes": round(equation_minutes, 2),
    }


def natal_pillars(birth: BirthData, true_solar_time: bool = True, day_boundary: str = "23:00") -> dict:
    warnings = list(birth.notes)
    solar = None
    if true_solar_time and birth.lon is None:
        warnings.insert(0, "no coordinates: hour and day pillars computed on clock time, not true solar time")
        true_solar_time = False
    if true_solar_time:
        reading, solar = apparent_solar_time(birth.local, birth.lon)
    else:
        reading = birth.local
    pillars = pillars_from_civil(reading, day_boundary, instant=birth.local)
    return {
        "pillars": pillars,
        "instant_used": reading.isoformat(),
        "clock_time": birth.local.isoformat(),
        "solar": solar,
        "warnings": warnings,
        "settings": {"true_solar_time": true_solar_time, "day_boundary": day_boundary},
    }


# ── Analysis ────────────────────────────────────────────────────────────────

from bazi_tables import (ELEMENTS, HIDDEN_STEMS, LIFE_STAGE_START, LIFE_STAGES,  # noqa: E402
                         SEASON_NAME_OF_BRANCH, SEASON_OF_BRANCH, SEASON_STATES,
                         TEN_GOD_BY_RELATION, TEN_GODS, void_branches)

PILLAR_ORDER = ("year", "month", "day", "hour")


def element_relation(a: str, b: str) -> int:
    """0 same, 1 a produces b, 2 a controls b, 3 b controls a, 4 b produces a."""
    i, j = ELEMENTS.index(a), ELEMENTS.index(b)
    return (j - i) % 5 if (j - i) % 5 in (0, 1, 2) else (3 if (j - i) % 5 == 3 else 4)


def ten_god(day_stem: int, other: int) -> str:
    dm, o = STEMS[day_stem], STEMS[other]
    rel = element_relation(dm["element"], o["element"])
    return TEN_GOD_BY_RELATION[(rel, dm["polarity"] == o["polarity"])]


def ten_god_detail(name: str) -> dict:
    return {"cn": name, **TEN_GODS[name]}


def life_stage(stem: int, branch: int) -> str:
    start = LIFE_STAGE_START[stem]
    step = (branch - start) % 12 if STEMS[stem]["polarity"] == "yang" else (start - branch) % 12
    return LIFE_STAGES[step]


def season_state(element: str, month_branch: int) -> str:
    return SEASON_STATES[element_relation(SEASON_OF_BRANCH[month_branch], element)]


def _stem_dict(i: int) -> dict:
    return {"index": i, **STEMS[i]}


def analyze(pillars: dict) -> dict:
    dm = pillars["day"]["stem"]["index"]
    dm_el = STEMS[dm]["element"]
    hidden = {k: [_stem_dict(i) for i in HIDDEN_STEMS[pillars[k]["branch"]["index"]]] for k in PILLAR_ORDER}

    tg_stems = {k: ("日主" if k == "day" else ten_god(dm, pillars[k]["stem"]["index"])) for k in PILLAR_ORDER}
    tg_detail = {k: ({"cn": "日主", "pinyin": "ri zhu", "en": "Day Master"} if k == "day" else ten_god_detail(tg_stems[k]))
                 for k in PILLAR_ORDER}
    tg_hidden = {k: [ten_god(dm, s["index"]) for s in hidden[k]] for k in PILLAR_ORDER}

    tally_visible = {e: 0 for e in ELEMENTS}
    for k in PILLAR_ORDER:
        tally_visible[pillars[k]["stem"]["element"]] += 1
        tally_visible[pillars[k]["branch"]["element"]] += 1
    tally_all = {e: 0 for e in ELEMENTS}
    for k in PILLAR_ORDER:
        tally_all[pillars[k]["stem"]["element"]] += 1
        for s in hidden[k]:
            tally_all[s["element"]] += 1

    stages = {k: life_stage(dm, pillars[k]["branch"]["index"]) for k in PILLAR_ORDER}

    voids = void_branches(pillars["day"]["index"])
    void = {"branches": [{"index": b, **BRANCHES[b]} for b in voids],
            "pillars": [k for k in PILLAR_ORDER if k != "day" and pillars[k]["branch"]["index"] in voids]}

    # Strength: season command, roots, support.
    month_branch = pillars["month"]["branch"]["index"]
    state = season_state(dm_el, month_branch)
    rooted = any(s["element"] == dm_el for k in PILLAR_ORDER for s in hidden[k])
    support = sum(1 for k in ("year", "month", "hour")
                  if element_relation(dm_el, pillars[k]["stem"]["element"]) in (0, 4))
    if state in ("旺", "相") and (rooted or support):
        verdict = "strong"
    elif state in ("休", "囚", "死") and not (rooted and support):
        verdict = "weak"
    else:
        verdict = "middling"
    strength = {
        "season_state": state, "rooted": rooted, "support": support, "verdict": verdict,
        "method": "season (旺相休囚死 of the Day Master's element in the month) + roots in any branch "
                  "+ same-element or resource stems; strong = in season with a root or support, "
                  "weak = out of season without both",
    }

    # Structure (格局), Ziping Zhenquan rules.
    month_hidden = HIDDEN_STEMS[month_branch]
    other_stems = {pillars[k]["stem"]["index"] for k in ("year", "month", "hour")}
    primary_god = ten_god(dm, month_hidden[0])
    if primary_god in ("比肩", "劫財"):
        # 建祿 / 月刃: the month branch itself is the structure, whatever is revealed.
        chosen, revealed = month_hidden[0], month_hidden[0] in other_stems
    else:
        chosen, revealed = month_hidden[0], False
        for cand in month_hidden:
            if cand in other_stems:
                chosen, revealed = cand, True
                break
    god = ten_god(dm, chosen)
    name = {"比肩": "建祿格", "劫財": "月刃格"}.get(god, f"{god}格")
    special = []
    all_eight = [pillars[k]["stem"]["index"] for k in PILLAR_ORDER] + [s["index"] for k in PILLAR_ORDER for s in hidden[k]]
    if not any(element_relation(dm_el, STEMS[i]["element"]) in (0, 4) for i in all_eight if i != dm):
        special.append("從格 (follow structure) candidate: no same-element or resource character anywhere")
    same_or_resource = sum(1 for i in all_eight if element_relation(dm_el, STEMS[i]["element"]) in (0, 4))
    if same_or_resource >= len(all_eight) - 1:
        special.append("專旺/從強 (dominant structure) candidate: nearly every character supports the Day Master")
    structure = {
        "name": name, "qi_used": STEMS[chosen]["cn"], "ten_god": god, "revealed": revealed,
        "basis": "Ziping Zhenquan: the month branch's primary qi if revealed in a stem, else a revealed "
                 "middle qi, else a revealed residual qi, else the primary qi unrevealed; 比肩 → 建祿格, 劫財 → 月刃格",
        "special_candidates": special,
    }

    # Climate.
    season = SEASON_NAME_OF_BRANCH[month_branch]
    fire, water = tally_all["fire"], tally_all["water"]
    if season == "winter" or (season != "summer" and water >= fire + 2):
        temperature = "cold"
    elif season == "summer" or fire >= water + 2:
        temperature = "hot"
    else:
        temperature = "temperate"
    moisture = "damp" if water >= 3 else ("dry" if water == 0 else "balanced")
    tempering = []
    if temperature == "cold":
        tempering.append("fire")
    if temperature == "hot":
        tempering.append("water")
    if moisture == "damp":
        tempering.append("earth")
    if moisture == "dry":
        tempering.append("water")
    climate = {"season": season, "temperature": temperature, "moisture": moisture,
               "tempering": sorted(set(tempering), key=ELEMENTS.index)}

    return {
        "day_master": _stem_dict(dm),
        "hidden": hidden,
        "ten_gods_stems": tg_stems,
        "ten_gods_detail": tg_detail,
        "ten_gods_hidden": tg_hidden,
        "tally_visible": tally_visible,
        "tally_all": tally_all,
        "life_stages": stages,
        "void": void,
        "strength": strength,
        "structure": structure,
        "climate": climate,
    }
