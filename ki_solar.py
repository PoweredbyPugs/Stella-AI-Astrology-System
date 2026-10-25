"""ki_solar — the Ki timekeeping stack read from the Sun's longitude past Lichun.

One hand on the clock: the Sun. Every level is a count of how far it has moved past the
Lichun gate (315°, 15° Aquarius), and every count descends 1 per period without resetting.

    year   = 360° of Sun (Lichun to Lichun)
    month  = 30°  (the Sun at 15° of each sign: the twelve jie)
    day    = 1°   (a "degree-day": 23.5 h near perihelion, 25.2 h near aphelion)
    hour   = 5′   (one twelfth of a degree-day, about two hours)

Twelve of anything is its parent; nine of anything is one cycle of its numbers. 12 mod 9 = 3
and 30 mod 9 = 3, so each level opens on an Earth number (2, 5, 8) and the lock at a seam is
the running count itself. The old clock day never fit (365 leaves 5); the degree-day does.

Anchors (doctrine 2026-10-25, see tests/test_ki_solar.py):
    year        2026 = 1                          (classical)
    month       Feb 2026 = 8                      (classical, continuous)
    day         every Lichun opens day 8          (month 2 opened day 8; 360 ≡ 0 mod 9)
    hour        opening = ki(3·day + 8)           (day 8 opens hour 5)
    great year / Ki Age / great age: ki_levels (Lichun 2010 opened 2 · 5 · 8 together)

Above the year, periods are counted in Ki years (Lichun to Lichun), so the great year,
Ki Age and great age are delegated to ki_levels and share its anchors.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import swisseph as swe

from ki_calendar import LICHUN_LON, TZ, lichun_jd, sun_at
from ki_levels import (
    PERIOD_YEARS, gate_start, global_great_age, global_great_year, global_ki_age, global_month,
    global_year, ki,
)

MEAN_MOTION = 0.9856  # mean solar motion, degrees per day
MONTH_DEGREES = 30
HOURS_PER_DAY = 12
MINUTES_PER_HOUR = 5
DAY_OPENING_AT_LICHUN = 8
HOUR_OPENING_CONSTANT = 8
LEVELS = ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")
EARTH = (2, 5, 8)


# ── Instants ──

def dt_to_jd(dt: datetime) -> float:
    """Aware (or naive = ``TZ``) datetime → Julian Day (UT)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + (u.second + u.microsecond / 1e6) / 3600)


def jd_to_dt(jd: float, tz: ZoneInfo = TZ) -> datetime:
    """Julian Day (UT) → aware datetime in ``tz`` (whole seconds)."""
    y, m, d, h = swe.revjul(jd)
    base = datetime(y, m, d, tzinfo=timezone.utc).timestamp() + round(h * 3600)
    return datetime.fromtimestamp(base, tz=timezone.utc).astimezone(tz)


def parse_target(target: Optional[str]) -> datetime:
    """A tool's target string → aware datetime. None = now; a bare date = local noon of that day;
    an ISO datetime is taken as given (naive = ``TZ``)."""
    if not target:
        return datetime.now(TZ)
    dt = datetime.fromisoformat(target)
    if len(target) == 10:
        dt = dt.replace(hour=12)
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


# ── The Sun ──

def sun_longitude(jd: float) -> float:
    return swe.calc_ut(jd, swe.SUN)[0][0] % 360


def lichun_instant(ki_year: int) -> float:
    """Julian Day of the Lichun that opens ``ki_year``."""
    return lichun_jd(ki_year)


def ki_year_at(jd: float) -> int:
    """The Ki year containing an instant (opens at the exact Lichun, not the calendar date)."""
    y = swe.revjul(jd)[0]
    return y if jd >= lichun_jd(y) else y - 1


def degrees_past_lichun(jd: float) -> float:
    return (sun_longitude(jd) - LICHUN_LON) % 360


def boundary_jd(ki_year: int, degrees: float) -> float:
    """The instant the Sun reaches ``degrees`` past the Lichun that opens ``ki_year``.
    Degrees of 360 and beyond roll into the following Ki year so a run of boundaries is one chain."""
    while degrees >= 360:
        ki_year, degrees = ki_year + 1, degrees - 360
    if degrees == 0:
        return lichun_jd(ki_year)
    return sun_at((LICHUN_LON + degrees) % 360, lichun_jd(ki_year) + degrees / MEAN_MOTION)


# ── Openings ──

def hour_opening(day_ki: int) -> int:
    """The first hour of a degree-day: slope 3 keeps it continuous (12 ≡ 3), the constant is the
    doctrine's anchor (day 8 opens hour 5). Days 1·4·7 open 2, 2·5·8 open 5, 3·6·9 open 8."""
    return ki(3 * day_ki + HOUR_OPENING_CONSTANT)


def day_ki_at(degrees_past: float) -> int:
    """Global day Ki from degrees past Lichun: one continuous count, 8 at every Lichun."""
    return ki(DAY_OPENING_AT_LICHUN - int(degrees_past))


# ── The stack ──

def solar_stack(jd: float) -> dict:
    """Every level at an instant, with where the Sun is and when the current periods began and end."""
    Y = ki_year_at(jd)
    lon = sun_longitude(jd)
    deg = (lon - LICHUN_LON) % 360
    d_abs = int(deg)
    m_idx = d_abs // MONTH_DEGREES
    frac = deg - d_abs
    h_idx = min(int(frac * HOURS_PER_DAY), HOURS_PER_DAY - 1)
    min_idx = min(int((frac * HOURS_PER_DAY - h_idx) * MINUTES_PER_HOUR), MINUTES_PER_HOUR - 1)

    day = day_ki_at(deg)
    numbers = {
        "great_age": global_great_age(Y),
        "ki_age": global_ki_age(Y),
        "great_year": global_great_year(Y),
        "year": global_year(Y),
        "month": global_month(Y * 12 + m_idx),
        "day": day,
        "hour": ki(hour_opening(day) - h_idx),
    }
    spans = {
        "year": (lichun_jd(Y), lichun_jd(Y + 1)),
        "month": (boundary_jd(Y, MONTH_DEGREES * m_idx), boundary_jd(Y, MONTH_DEGREES * (m_idx + 1))),
        "day": (boundary_jd(Y, d_abs), boundary_jd(Y, d_abs + 1)),
        "hour": (boundary_jd(Y, d_abs + h_idx / HOURS_PER_DAY), boundary_jd(Y, d_abs + (h_idx + 1) / HOURS_PER_DAY)),
    }
    return {
        "jd": jd,
        "ki_year": Y,
        "sun_longitude": lon,
        "degrees_past_lichun": deg,
        "month_index": m_idx,              # 0 = Feb (opens at Lichun) … 11 = Jan
        "degree_day": d_abs % MONTH_DEGREES + 1,   # 1–30 within the month
        "degree_day_of_year": d_abs + 1,           # 1–360
        "degree_hour": h_idx + 1,                  # 1–12 within the day
        "arcminute": min_idx + 1,                  # 1–5 within the hour
        "day_opening": DAY_OPENING_AT_LICHUN if m_idx == 0 and d_abs == 0 else ki(DAY_OPENING_AT_LICHUN - MONTH_DEGREES * m_idx),
        "hour_opening": hour_opening(day),
        "numbers": numbers,
        "spans": spans,
    }


def solar_stack_at(dt: datetime) -> dict:
    return solar_stack(dt_to_jd(dt))


def next_change_jd(jd: float, level: str, n: int = 1) -> float:
    """The instant of the n-th next change of ``level`` after ``jd`` (n = 1 is the next one)."""
    s = solar_stack(jd)
    Y = s["ki_year"]
    d_abs = s["degree_day_of_year"] - 1
    if level == "hour":
        return boundary_jd(Y, d_abs + (s["degree_hour"] - 1 + n) / HOURS_PER_DAY)
    if level == "day":
        return boundary_jd(Y, d_abs + n)
    if level == "month":
        return boundary_jd(Y, MONTH_DEGREES * (s["month_index"] + n))
    if level == "year":
        return lichun_jd(Y + n)
    if level in PERIOD_YEARS:
        return lichun_jd(gate_start(Y, level) + n * PERIOD_YEARS[level])
    raise ValueError(f"unknown level {level!r}")


def stack_after(jd: float, level: str, n: int = 1) -> dict:
    """The global numbers just after the n-th next change of ``level``."""
    return solar_stack(next_change_jd(jd, level, n) + 1 / 86400)["numbers"]
