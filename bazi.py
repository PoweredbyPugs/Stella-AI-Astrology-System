"""bazi — traditional Zi Ping Four Pillars (八字) on Stella.

Settled mechanics (docs/superpowers/specs/2026-11-10-bazi-design.md):
    year   changes at the exact Lichun instant (Sun at 315°); 1984 is 甲子
    month  changes at the twelve jie (Sun at 15° of each sign); 寅 opens at Lichun
    day    sexagenary index (JDN + 49) mod 60, 甲子 = 0; 2000-01-01 is 戊午
    hour   twelve double-hours, 子 spanning 23:00–01:00
Month stems by the Five Tigers rule (五虎遁), hour stems by the Five Rats rule (五鼠遁).

Only the solar-term boundaries are shared with the Ki calendar. Nothing else is.
"""

from datetime import date, datetime, time, timezone

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


def pillars_from_civil(local: datetime, day_boundary: str = "23:00") -> dict:
    """Four pillars for a tz-aware local datetime read as clock time.

    ``day_boundary`` "23:00": the day pillar changes at the start of the Zi hour.
    "midnight": the day pillar keeps the civil date until 00:00, and the 23:00–00:00 hour
    stem is derived from the next day's stem (早子/晚子 convention).
    """
    if day_boundary not in DAY_BOUNDARIES:
        raise ValueError(f"day_boundary must be one of {DAY_BOUNDARIES}, not {day_boundary!r}")
    if local.tzinfo is None:
        raise ValueError("local datetime must be timezone-aware")

    jd = _jd_ut(local)
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
