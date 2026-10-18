"""The Ki calendar: when a Ki year and a Ki month open, astronomically.

One rule, shared by every Stella Ki stack and by the octave app (lib/ki/kimonths.ts):

- A Ki year opens at Lichun, the instant the Sun reaches 315° (15° Aquarius).
- A Ki month opens when the Sun reaches 15° of each sign: 315°, 345°, 15°, … 285°.
  These are the twelve "jie" solar terms (Lichun, Jingzhe, Qingming, Lixia, …).
- Boundaries are read as calendar dates in ``TZ`` (America/New_York). The boundary
  day belongs to the period it opens: when Lichun falls at 3 pm on Feb 3, the whole
  of Feb 3 is the new Ki year. Nothing is hard-coded to Feb 4.

Month index 0 is Feb (opens at Lichun) … 11 is Jan.
"""

from datetime import date, datetime, timezone
from functools import lru_cache
from typing import List, Tuple
from zoneinfo import ZoneInfo

import swisseph as swe

TZ = ZoneInfo("America/New_York")
LICHUN_LON = 315.0
MONTH_NAMES = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan"]


def jd_to_local(jd: float) -> datetime:
    """A Julian Day (UT) as an aware datetime in ``TZ``."""
    y, m, d, h = swe.revjul(jd)
    ts = datetime(y, m, d, tzinfo=timezone.utc).timestamp() + round(h * 3600)
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(TZ)


def sun_at(lon: float, from_jd: float) -> float:
    """Julian Day (UT) when the Sun next reaches ``lon`` degrees, searching forward from ``from_jd``."""
    jd = from_jd
    for _ in range(60):
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        diff = (lon - sun_lon) % 360
        if diff > 180:
            diff -= 360
        if abs(diff) < 1e-5:
            return jd
        jd += diff / 0.9856  # mean solar motion, degrees per day
    return jd


@lru_cache(maxsize=None)
def lichun_jd(year: int) -> float:
    """Julian Day (UT) of the Lichun that opens Ki year ``year``."""
    return sun_at(LICHUN_LON, swe.julday(year, 1, 25, 0.0))


@lru_cache(maxsize=None)
def boundaries_jd(ki_year: int) -> Tuple[float, ...]:
    """The 13 boundary instants of a Ki year: Lichun, the 11 month openings, the next Lichun."""
    out = [lichun_jd(ki_year)]
    for k in range(1, 12):
        out.append(sun_at((LICHUN_LON + 30 * k) % 360, out[0] + 30.44 * k - 8))
    out.append(lichun_jd(ki_year + 1))
    return tuple(out)


@lru_cache(maxsize=None)
def boundary_dates(ki_year: int) -> Tuple[date, ...]:
    """Local calendar date on which each boundary of a Ki year opens."""
    return tuple(jd_to_local(jd).date() for jd in boundaries_jd(ki_year))


def lichun_date(year: int) -> date:
    """Local calendar date of the Lichun that opens Ki year ``year``."""
    return jd_to_local(lichun_jd(year)).date()


def ki_year_of(d: date) -> int:
    """Ki year containing calendar date ``d``."""
    return d.year if d >= lichun_date(d.year) else d.year - 1


def ki_month_of(d: date) -> Tuple[int, int]:
    """(Ki year, month index 0 = Feb … 11 = Jan) containing calendar date ``d``."""
    ky = ki_year_of(d)
    dates = boundary_dates(ky)
    for i in range(11, -1, -1):
        if d >= dates[i]:
            return ky, i
    raise ValueError(f"No Ki month for {d}")


def ki_month_span(ki_year: int, index: int) -> Tuple[date, date]:
    """First and last calendar day of a Ki month."""
    dates = boundary_dates(ki_year)
    return dates[index], date.fromordinal(dates[index + 1].toordinal() - 1)


def ki_year_span(ki_year: int) -> Tuple[date, date]:
    """First and last calendar day of a Ki year."""
    return lichun_date(ki_year), date.fromordinal(lichun_date(ki_year + 1).toordinal() - 1)


def ki_month_label(ki_year: int, index: int) -> str:
    """'Oct 2026', 'Jan 2027' (Jan carries the following calendar year)."""
    return f"{MONTH_NAMES[index]} {ki_year + 1 if index == 11 else ki_year}"


def boundary_instants_local(ki_year: int) -> List[datetime]:
    """Boundary instants of a Ki year as aware datetimes in ``TZ`` (for display)."""
    return [jd_to_local(jd) for jd in boundaries_jd(ki_year)]
