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
from datetime import timezone as timezone_cls
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


def _hms_to_hours(text: str) -> float:
    h, m, sec = (float(x) for x in text.split(":"))
    return h + m / 60 + sec / 3600


def longitude_from_sidereal(greenwich: str, local: str) -> float:
    """Longitude in degrees from a chart's Greenwich and local sidereal times (hh:mm:ss)."""
    diff = _hms_to_hours(local) - _hms_to_hours(greenwich)
    if diff > 12:
        diff -= 24
    if diff < -12:
        diff += 24
    return round(diff * 15, 4)


def birth_from_chart(chart: dict, gender: Optional[str] = None, timezone: Optional[str] = None,
                     lat: Optional[float] = None, lon: Optional[float] = None) -> BirthData:
    """Birth data from either stored-chart shape (Helios ``birthInfo`` or legacy ``birthData``).

    ``timezone``, ``lat`` and ``lon`` override what the chart carries. A chart with no zone has
    its longitude recovered from its sidereal times and its zone inferred from that longitude
    (standard offset, no daylight saving), with a note saying so.
    """
    name = chart.get("name", "chart")
    notes = []
    if "birthInfo" in chart:
        info = chart["birthInfo"]
        naive = datetime.strptime(info["dateTime"], "%B %d, %Y %I:%M:%S %p")
        coords = info.get("coordinates") or {}
        lat = lat if lat is not None else coords.get("latitude")
        lon = lon if lon is not None else coords.get("longitude")
        tz = info.get("timezone")
        jd = info.get("julianDay")
    elif "birthData" in chart:
        info = chart["birthData"]
        naive = datetime.fromisoformat(f"{info['date']}T{info['time']}")
        loc = info.get("location") or {}
        lat = lat if lat is not None else loc.get("latitude")
        lon = lon if lon is not None else loc.get("longitude")
        tz = info.get("timezone")
        jd = float(info["julianDay"]) if info.get("julianDay") else None
    else:
        raise ValueError(f"Chart '{name}' has no birthInfo or birthData")

    if lon is None and chart.get("birthInfo", {}).get("siderealTime") and chart["birthInfo"].get("localSiderealTime") \
            and (chart["birthInfo"].get("coordinates") or {}).get("longitude") is None:
        lon = longitude_from_sidereal(chart["birthInfo"]["siderealTime"], chart["birthInfo"]["localSiderealTime"])
        notes.append(f"chart has no coordinates; longitude {lon} recovered from its sidereal times")

    if timezone:
        tz = timezone
    if tz:
        local = naive.replace(tzinfo=ZoneInfo(tz))
    elif lon is not None:
        hours = round(lon / 15)
        local = naive.replace(tzinfo=timezone_cls(timedelta(hours=hours)))
        notes.append(f"chart has no time zone; zone inferred from longitude as UTC{hours:+d} (standard time, "
                     "daylight saving unknown); pass timezone= to fix it")
    elif jd:
        offset = naive - _jd_to_utc(float(jd)).replace(tzinfo=None)
        offset = timedelta(minutes=round(offset.total_seconds() / 60))
        local = naive.replace(tzinfo=timezone_cls(offset))
        notes.append(f"chart has no time zone; birth time read with the chart's own UT offset ({offset})")
    else:
        local = naive.replace(tzinfo=timezone_cls.utc)
        notes.append("chart has no time zone or Julian Day; birth time read as UT")

    g = normalise_gender(gender) if gender is not None else normalise_gender(chart.get("gender"))
    return BirthData(local, lat, lon, tz, g, name, notes)


def apply_lmt_fallback(birth: BirthData) -> BirthData:
    """Before a zone's recorded history, zoneinfo gives its reference city's LMT. Rebuild the
    offset from the birth longitude and say so."""
    if birth.local.tzname() == "LMT" and birth.lon is not None:
        minutes = round(birth.lon * 4)
        local = birth.local.replace(tzinfo=timezone_cls(timedelta(minutes=minutes)))
        notes = birth.notes + [f"birth predates the zone's recorded history; read as local mean time of "
                               f"longitude {birth.lon} (UTC{minutes // 60:+03d}:{abs(minutes) % 60:02d})"]
        return BirthData(local, birth.lat, birth.lon, birth.tz, birth.gender, birth.source, notes)
    return birth


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
    birth = apply_lmt_fallback(birth)
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
    from bazi_tables import LUSHEN, YANGREN
    month_hidden = HIDDEN_STEMS[month_branch]
    other_stems = {pillars[k]["stem"]["index"] for k in ("year", "month", "hour")}
    storage = month_branch in (1, 4, 7, 10)
    primary_god = ten_god(dm, month_hidden[0])
    prefix = ""
    if month_branch == LUSHEN[dm]:
        chosen, revealed, name = month_hidden[0], month_hidden[0] in other_stems, "建祿格"
    elif STEMS[dm]["polarity"] == "yang" and YANGREN.get(dm) == month_branch:
        chosen, revealed, name = month_hidden[0], month_hidden[0] in other_stems, "月刃格"
    elif primary_god == "劫財" and not storage:
        chosen, revealed, name = month_hidden[0], month_hidden[0] in other_stems, "月劫格"
    else:
        candidates = [c for c in month_hidden if ten_god(dm, c) not in ("比肩", "劫財")]
        chosen, revealed = candidates[0], False
        for cand in candidates:
            if cand in other_stems:
                chosen, revealed = cand, True
                break
        prefix = "雜氣" if storage else ""
        name = f"{prefix}{ten_god(dm, chosen)}格"
    god = ten_god(dm, chosen)
    special = []
    positions = [pillars[k]["stem"]["index"] for k in PILLAR_ORDER] + [s["index"] for k in PILLAR_ORDER for s in hidden[k]]
    others = positions[:2] + positions[3:]           # every character except the Day Master's own slot
    if not any(element_relation(dm_el, STEMS[i]["element"]) in (0, 4) for i in others):
        special.append("從格 (follow structure) candidate: no same-element or resource character anywhere")
    same_or_resource = sum(1 for i in others if element_relation(dm_el, STEMS[i]["element"]) in (0, 4))
    if same_or_resource >= len(others) - 1:
        special.append("專旺/從強 (dominant structure) candidate: nearly every character supports the Day Master")
    structure = {
        "name": name, "qi_used": STEMS[chosen]["cn"], "ten_god": god, "revealed": revealed,
        "basis": "Ziping Zhenquan: 建祿格 when the month is the Day Master's 祿 branch, 月刃格 when it is a yang "
                 "stem's 刃 branch, 月劫格 when a yin stem's month primary qi is 劫財; otherwise the first of the "
                 "month branch's non-比劫 hidden stems revealed in a stem (primary, then middle, then residual), "
                 "else the primary unrevealed; in the storage months 辰戌丑未 the result is a 雜氣 structure",
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


# ── Interactions and stars ──────────────────────────────────────────────────

from itertools import combinations  # noqa: E402

from bazi_tables import (CLASHES, DESTRUCTIONS, DIRECTIONAL, GUCHEN_GUASU, HARMS, LUSHEN,  # noqa: E402
                         PUNISHMENT_PAIR, PUNISHMENT_TRIADS, SELF_PUNISHMENT, SIX_COMBOS, STAR_EN,
                         STEM_COMBOS, TAOHUA, TIANYI, TIANYI_VARIANT_NOTE, TRINES, WENCHANG,
                         YANGREN, YIMA)


def _entry(kind, cn, members, pillars, **extra):
    return {"type": kind, "cn": cn, "members": [(k, pillars[k]["branch"]["cn"] if kind != "stem_combination"
                                                 else pillars[k]["stem"]["cn"]) for k in members], **extra}


def interactions(pillars: dict) -> list:
    """Every named interaction among the pillars given (any keys; natal keys plus transit keys work)."""
    out = []
    keys = list(pillars)
    stems = {k: pillars[k]["stem"]["index"] for k in keys}
    branches = {k: pillars[k]["branch"]["index"] for k in keys}
    season = SEASON_OF_BRANCH[branches["month"]]

    for a, b in combinations(keys, 2):
        pair = frozenset((stems[a], stems[b]))
        if pair in STEM_COMBOS:
            el = STEM_COMBOS[pair]
            out.append(_entry("stem_combination", "天干五合", (a, b), pillars, element=el, transforms=el == season))

    # Triples first so a full trine or directional is not also reported as its halves.
    trine_members = set()
    for a, b, c in combinations(keys, 3):
        trio = {branches[a], branches[b], branches[c]}
        for key, el in TRINES.items():
            if trio == set(key):
                out.append(_entry("trine", "三合", (a, b, c), pillars, element=el))
                trine_members.update({frozenset((a, b)), frozenset((b, c)), frozenset((a, c))})
        for key, el in DIRECTIONAL.items():
            if trio == set(key):
                out.append(_entry("directional", "三會", (a, b, c), pillars, element=el))
        for key, note in PUNISHMENT_TRIADS:
            if trio == set(key):
                out.append(_entry("punishment", "三刑", (a, b, c), pillars, note=note))

    for a, b in combinations(keys, 2):
        x, y = branches[a], branches[b]
        pair = frozenset((x, y))
        if pair in SIX_COMBOS:
            out.append(_entry("six_combination", "六合", (a, b), pillars, element=SIX_COMBOS[pair]))
        if frozenset((a, b)) not in trine_members and x != y:
            for key, el in TRINES.items():
                if pair <= set(key) and key[1] in pair:
                    out.append(_entry("half_trine", "半合", (a, b), pillars, element=el))
        if tuple(sorted(pair)) in [tuple(sorted(p)) for p in CLASHES]:
            out.append(_entry("clash", "六沖", (a, b), pillars))
        if tuple(sorted(pair)) in [tuple(sorted(p)) for p in HARMS]:
            out.append(_entry("harm", "六害", (a, b), pillars))
        if tuple(sorted(pair)) in [tuple(sorted(p)) for p in DESTRUCTIONS]:
            out.append(_entry("destruction", "六破", (a, b), pillars))
        if x == y and x in SELF_PUNISHMENT:
            out.append(_entry("self_punishment", "自刑", (a, b), pillars))
        elif x != y:
            for key, note in PUNISHMENT_TRIADS:
                if pair <= set(key):
                    out.append(_entry("punishment", "刑", (a, b), pillars, note=note))
            if pair == frozenset(PUNISHMENT_PAIR[0]):
                out.append(_entry("punishment", "刑", (a, b), pillars, note=PUNISHMENT_PAIR[1]))
    return out


def _group(table: dict, branch: int):
    return next(v for k, v in table.items() if branch in k)


def stars(pillars: dict) -> dict:
    hits, footnotes = [], []
    stems = {k: pillars[k]["stem"]["index"] for k in PILLAR_ORDER}
    branches = {k: pillars[k]["branch"]["index"] for k in PILLAR_ORDER}

    def hit(star, found_in, cast_from):
        hits.append({"star_cn": star, "star_en": STAR_EN[star], "found_in": found_in, "cast_from": cast_from,
                     "branch": pillars[found_in]["branch"]["cn"]})

    def scan(star, targets, cast_from, skip_self=True):
        for k in PILLAR_ORDER:
            if skip_self and k == cast_from and star in ("桃花", "驛馬", "孤辰", "寡宿"):
                continue
            if branches[k] in targets:
                hit(star, k, cast_from)

    for cast in ("day", "year"):
        scan("天乙貴人", TIANYI[stems[cast]], cast)
        if stems[cast] == 6:
            footnotes.append(TIANYI_VARIANT_NOTE)
    scan("文昌", (WENCHANG[stems["day"]],), "day")
    scan("祿神", (LUSHEN[stems["day"]],), "day")
    if stems["day"] in YANGREN:
        scan("羊刃", (YANGREN[stems["day"]],), "day")
    for cast in ("year", "day"):
        b = branches[cast]
        scan("桃花", (_group(TAOHUA, b),), cast)
        scan("驛馬", (_group(YIMA, b),), cast)
        gu, gua = _group(GUCHEN_GUASU, b)
        scan("孤辰", (gu,), cast)
        scan("寡宿", (gua,), cast)
    return {"hits": hits, "footnotes": list(dict.fromkeys(footnotes))}


# ── Luck pillars (大運) and time pillars ────────────────────────────────────

def luck_direction(gender: str, year_polarity: str) -> str:
    return "forward" if (gender == "male") == (year_polarity == "yang") else "backward"


def _jie_instants(jd: float) -> list:
    """All jie instants (UT JD) in the BaZi year around ``jd`` and its neighbours, sorted."""
    y = bazi_year_at(jd)
    out = []
    for yy in (y - 1, y, y + 1):
        out.extend(boundaries_jd(yy)[:12])
    return sorted(set(out))


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    from calendar import monthrange
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def luck_pillars(birth: BirthData, natal: dict, count: int = 10, at: Optional[datetime] = None) -> dict:
    """Ten-year luck pillars from the natal month pillar, forward or backward by gender and year polarity.

    Start age: days from birth to the next (forward) or previous (backward) jie, at three days per
    year, one day per four months, one double-hour per ten days. ``natal`` is the ``natal_pillars``
    result so the same solar-time reading is used.
    """
    if birth.gender not in ("male", "female"):
        raise ValueError("gender required for luck pillars (male or female)")
    pillars = natal["pillars"]
    direction = luck_direction(birth.gender, pillars["year"]["stem"]["polarity"])
    birth_jd = _jd_ut(birth.local)
    jies = _jie_instants(birth_jd)
    if direction == "forward":
        target = next(j for j in jies if j > birth_jd)
        days = target - birth_jd
    else:
        target = next(j for j in reversed(jies) if j <= birth_jd)
        days = birth_jd - target
    years = int(days // 3)
    rem_days = days - 3 * years
    months = int(rem_days * 4)
    rem_frac = rem_days * 4 - months            # fraction of a 4-month block → days
    extra_days = int(round(rem_frac * 30))
    start_age = {"years": years, "months": months, "days": extra_days, "days_to_jie": round(days, 2)}

    birth_date = birth.local.date()
    start = _add_months(birth_date, years * 12 + months)
    start = date.fromordinal(start.toordinal() + extra_days)

    step = 1 if direction == "forward" else -1
    dm = pillars["day"]["stem"]["index"]
    out = []
    for n in range(1, count + 1):
        sx = sexagenary(pillars["month"]["index"] + step * n)
        p_start = _add_months(start, 120 * (n - 1))
        p_end = _add_months(start, 120 * n)
        entry = {
            **sx,
            "index_in_sequence": n,
            "start_date": p_start.isoformat(),
            "end_date": p_end.isoformat(),
            "age_from": years + 10 * (n - 1),
            "ten_god_stem": ten_god(dm, sx["stem"]["index"]),
            "ten_god_branch": ten_god(dm, HIDDEN_STEMS[sx["branch"]["index"]][0]),
            "life_stage": life_stage(dm, sx["branch"]["index"]),
        }
        entry["interactions_with_natal"] = [i for i in interactions({**pillars, "luck": sx})
                                            if any(m[0] == "luck" for m in i["members"])]
        out.append(entry)

    now = (at or datetime.now(tz=birth.local.tzinfo)).date()
    current = next((p for p in out if p["start_date"] <= now.isoformat() < p["end_date"]), None)
    return {"direction": direction, "start_age": start_age, "start_date": start.isoformat(),
            "pillars": out, "current": current, "as_of": now.isoformat()}


def time_pillars(at: datetime, day_boundary: str = "23:00") -> dict:
    return pillars_from_civil(at, day_boundary)


def time_against_natal(at: datetime, natal: dict, luck: Optional[dict] = None,
                       day_boundary: str = "23:00") -> dict:
    pillars = natal["pillars"]
    dm = pillars["day"]["stem"]["index"]
    now = time_pillars(at, day_boundary)
    gods = {k: {"stem": ten_god(dm, now[k]["stem"]["index"]),
                "branch": ten_god(dm, HIDDEN_STEMS[now[k]["branch"]["index"]][0]),
                "life_stage": life_stage(dm, now[k]["branch"]["index"])} for k in PILLAR_ORDER}
    current_luck = (luck or {}).get("current")
    combined = {**pillars}
    if current_luck:
        combined["luck"] = current_luck
    combined.update({f"{k}_now": now[k] for k in PILLAR_ORDER})
    transit_keys = {"luck", *(f"{k}_now" for k in PILLAR_ORDER)}
    natal_side = set(PILLAR_ORDER) | {"luck"}
    inter = [i for i in interactions(combined)
             if any(m[0] in transit_keys for m in i["members"]) and any(m[0] in natal_side for m in i["members"])]
    return {"at": at.isoformat(), "pillars": now, "ten_gods": gods, "luck": current_luck, "interactions": inter}
