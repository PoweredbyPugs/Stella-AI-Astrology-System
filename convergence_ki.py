"""Convergence Ki — Astronomical Ki calculation using the 15° grid.

Three bodies cross the same 12 mid-sign gates (15° of each sign) at three speeds:
  Sun:       12 gates in 1 year        → each gate = 1 month (~30 days)
  Moon:      12 gates in 1 sid. month  → each gate = 1 lunar gate (~2.3 days)
  Ascendant: 12 gates in 1 sid. day   → each gate = 1 mid-sign hour (~2 hrs)

Same grid. Same 12. Same 15°. Same 9 Ki numbers. Same remainder 3.
One relationship, three octaves.

Convergence sockets (15° Aquarius, Gemini, Libra) are a subset of the 12 mid-sign gates
— the air trine, where the 9-fold and 15-fold grids converge (LCM=120°). The Moon
crosses these every ~9.09 days, giving the traditional day Ki rhythm.

Research: stella/research/convergence-sockets.md
"""

import swisseph as swe
from datetime import date, datetime, timezone
from typing import Optional
from pathlib import Path
from zoneinfo import ZoneInfo

from ki_calendar import ki_month_of, ki_year_of, ki_year_span, lichun_jd as _lichun_jd

# ── Config ──
EPHE_PATH = "/mnt/baratie/baratie/sweph-service/ephemeris"
swe.set_ephe_path(EPHE_PATH)
TZ = ZoneInfo("America/New_York")


def _build_identity() -> dict:
    """Name the code copy answering: short git sha (or 'nogit') and file path.

    Computed once at import so a long-lived server reports the code it loaded,
    not whatever is on disk now. Lets a caller tell stale processes apart.
    """
    import subprocess
    here = Path(__file__).resolve()
    try:
        sha = subprocess.run(
            ["git", "-C", str(here.parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip() or "nogit"
    except Exception:
        sha = "nogit"
    return {
        "git": sha,
        "code_path": str(here),
        "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


BUILD = _build_identity()

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

CONVERGENCE_SOCKETS = {
    315.0: {"name": "S1", "sign": "15° Aquarius", "role": "Lichun / Year Start"},
    75.0:  {"name": "S2", "sign": "15° Gemini",   "role": "Center / Pivot"},
    195.0: {"name": "S3", "sign": "15° Libra",    "role": "Completion"},
}

# Mid-sign gates: 15° of each sign (the 12 gates shared by all three bodies)
MID_SIGN_GATES = {
    15.0:  {"sign": "15° Aries",       "sign_idx": 0},
    45.0:  {"sign": "15° Taurus",      "sign_idx": 1},
    75.0:  {"sign": "15° Gemini",      "sign_idx": 2,  "socket": "S2"},
    105.0: {"sign": "15° Cancer",      "sign_idx": 3},
    135.0: {"sign": "15° Leo",         "sign_idx": 4},
    165.0: {"sign": "15° Virgo",       "sign_idx": 5},
    195.0: {"sign": "15° Libra",       "sign_idx": 6,  "socket": "S3"},
    225.0: {"sign": "15° Scorpio",     "sign_idx": 7},
    255.0: {"sign": "15° Sagittarius", "sign_idx": 8},
    285.0: {"sign": "15° Capricorn",   "sign_idx": 9},
    315.0: {"sign": "15° Aquarius",    "sign_idx": 10, "socket": "S1"},
    345.0: {"sign": "15° Pisces",      "sign_idx": 11},
}


# ── Helpers ──

def _dt_to_jd(dt: datetime) -> float:
    utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0 + utc.second / 3600.0)


def _jd_to_dt(jd: float, tz: ZoneInfo = TZ) -> datetime:
    y, m, d, h = swe.revjul(jd)
    hr = int(h)
    mn = int((h - hr) * 60)
    sec = int(((h - hr) * 60 - mn) * 60)
    return datetime(y, m, d, hr, mn, sec, tzinfo=timezone.utc).astimezone(tz)


def _year_ki(year: int, month: int, day: int) -> int:
    """Calculate year Ki for a given date. The Ki year opens on the local date of Lichun."""
    ki_year = ki_year_of(date(year, month, day))
    digit_sum = sum(int(d) for d in str(ki_year))
    while digit_sum > 9:
        digit_sum = sum(int(d) for d in str(digit_sum))
    ki = (11 - digit_sum) % 9
    return ki if ki != 0 else 9


def _find_moon_socket_crossings(start_jd: float, end_jd: float) -> list:
    """Find all Moon crossings of convergence sockets in a JD range."""
    crossings = []
    jd = start_jd
    prev_lon = None
    step = 1.0 / 24.0  # hourly steps

    while jd < end_jd:
        moon = swe.calc_ut(jd, swe.MOON)[0]
        lon = moon[0]

        if prev_lon is not None:
            for target_deg, info in CONVERGENCE_SOCKETS.items():
                prev_dist = (target_deg - prev_lon) % 360
                curr_dist = (target_deg - lon) % 360
                if 0 < prev_dist < 15 and curr_dist > 345:
                    # Refine with binary search
                    lo, hi = jd - step, jd
                    for _ in range(20):
                        mid = (lo + hi) / 2
                        mid_lon = swe.calc_ut(mid, swe.MOON)[0][0]
                        mid_dist = (target_deg - mid_lon) % 360
                        if mid_dist > 180:
                            lo = mid
                        else:
                            hi = mid
                    crossings.append({
                        "jd": (lo + hi) / 2,
                        "socket": info["name"],
                        "degree": target_deg,
                        "sign": info["sign"],
                        "role": info["role"],
                    })

        prev_lon = lon
        jd += step

    crossings.sort(key=lambda c: c["jd"])
    return crossings


def _find_moon_midsign_crossings(start_jd: float, end_jd: float) -> list:
    """Find all Moon crossings of mid-sign gates (15° of each sign) in a JD range."""
    crossings = []
    jd = start_jd
    prev_lon = None
    step = 1.0 / 24.0  # hourly steps

    while jd < end_jd:
        moon = swe.calc_ut(jd, swe.MOON)[0]
        lon = moon[0]

        if prev_lon is not None:
            for target_deg, info in MID_SIGN_GATES.items():
                prev_dist = (target_deg - prev_lon) % 360
                curr_dist = (target_deg - lon) % 360
                if 0 < prev_dist < 15 and curr_dist > 345:
                    # Refine with binary search
                    lo, hi = jd - step, jd
                    for _ in range(20):
                        mid = (lo + hi) / 2
                        mid_lon = swe.calc_ut(mid, swe.MOON)[0][0]
                        mid_dist = (target_deg - mid_lon) % 360
                        if mid_dist > 180:
                            lo = mid
                        else:
                            hi = mid
                    crossings.append({
                        "jd": (lo + hi) / 2,
                        "gate": target_deg,
                        "sign": info["sign"],
                        "sign_idx": info["sign_idx"],
                        "is_socket": "socket" in info,
                        "socket": info.get("socket"),
                    })

        prev_lon = lon
        jd += step

    crossings.sort(key=lambda c: c["jd"])
    return crossings


def _find_moon_sidereal_month_start(target_jd: float) -> float:
    """Find the most recent Moon crossing of S1 (15° Aquarius) before target_jd.

    This marks the start of the current sidereal month for lunar gate counting.
    """
    # Search backward up to 30 days
    crossings = _find_moon_socket_crossings(target_jd - 30, target_jd)
    s1_crossings = [c for c in crossings if c["socket"] == "S1" and c["jd"] <= target_jd]
    if s1_crossings:
        return s1_crossings[-1]["jd"]
    # Fallback: search further back
    crossings = _find_moon_socket_crossings(target_jd - 60, target_jd - 30)
    s1_crossings = [c for c in crossings if c["socket"] == "S1"]
    return s1_crossings[-1]["jd"] if s1_crossings else target_jd


def _find_lichun(year: int) -> float:
    """Julian Day of Lichun (Sun at 315°) opening Ki year ``year`` (shared with ki_calendar)."""
    return _lichun_jd(year)


def gate_label(ecliptic_lon: float) -> str:
    """Human-readable gate label for an ecliptic longitude."""
    gate = int(ecliptic_lon / 15) * 15
    sign_idx = gate // 30
    deg = gate % 30
    return f"{deg}° {SIGN_NAMES[sign_idx]}"


# ── Public API ──

def _find_jupiter_perihelion(near_year: float) -> float:
    """Find exact Julian Day of Jupiter's perihelion nearest to a given year.

    Jupiter's perihelion (~14-16° Aries) occurs every ~11.86 years.
    Uses heliocentric distance minimization.
    """
    # Start search 6 years before target
    jd = swe.julday(int(near_year) - 6, 1, 1, 0.0)
    end_jd = swe.julday(int(near_year) + 7, 1, 1, 0.0)

    # Sample every 10 days, find distance minimum
    distances = []
    while jd < end_jd:
        dist = swe.calc_ut(jd, swe.JUPITER, swe.FLG_HELCTR)[0][2]
        distances.append((jd, dist))
        jd += 10

    # Find local minimum closest to target year
    target_jd = swe.julday(int(near_year), 6, 1, 0.0)
    best = None
    for i in range(1, len(distances) - 1):
        if distances[i][1] < distances[i-1][1] and distances[i][1] < distances[i+1][1]:
            if best is None or abs(distances[i][0] - target_jd) < abs(best[0] - target_jd):
                best = distances[i]

    if best is None:
        return swe.julday(int(near_year), 1, 1, 0.0)

    # Refine with golden section search
    lo, hi = best[0] - 10, best[0] + 10
    for _ in range(50):
        m1 = lo + (hi - lo) / 3
        m2 = lo + 2 * (hi - lo) / 3
        d1 = swe.calc_ut(m1, swe.JUPITER, swe.FLG_HELCTR)[0][2]
        d2 = swe.calc_ut(m2, swe.JUPITER, swe.FLG_HELCTR)[0][2]
        if d1 < d2:
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2


# Great year (synodic gate): arithmetic 12-year gates. Lichun 2022 opens gate 8 and the
# great year descends 1 per gate. 12 mod 9 = 3 keeps every gate on an Earth year (2, 5, 8),
# as 12 months keep every Lichun on an Earth month. 9 gates = 108 years.
# Jupiter's ~11.86-year perihelion cycle lands near these gates but is not the clock.
from ki_levels import (
    GREAT_YEAR_ANCHOR_KI as SYNODIC_ANCHOR_KI,
    GREAT_YEAR_ANCHOR_YEAR as SYNODIC_ANCHOR_YEAR,
    gate_start as _gate_start,
    global_great_year as _global_great_year,
)

SYNODIC_GATE_YEARS = 12


def synodic_gate_start(ki_year: int) -> int:
    """Ki year (Lichun) that opens the synodic gate containing ki_year."""
    return _gate_start(ki_year, "great_year")


def synodic_ki_for_year(ki_year: int) -> int:
    """Global great-year Ki for a Ki year: 2010-2021 = 9, 2022-2033 = 8, 2034-2045 = 7."""
    return _global_great_year(ki_year)


def get_synodic_gate(target_date: str = None, birth_date: str = None) -> dict:
    """Calculate the Synodic Gate Ki — the 12-year great-year level.

    Pure arithmetic: 12 Ki years per gate, descending 9 → 1, gates on Lichun,
    anchored at Lichun 2022 = gate 8. Jupiter's ~11.86-yr orbital cycle is the
    natural period behind the count, not the anchor; perihelia are reported as
    an informational layer only.

    12 years per synodic gate, 9 Ki count → remainder 3.
    At each synodic gate boundary, the year Ki is always Earth (2, 5, 8).
    This mirrors month/day/hour always being Earth at Lichun.

    9 synodic gates = one full cycle = 108 years.

    Args:
        target_date: ISO date YYYY-MM-DD (default: today)
        birth_date: Birth date YYYY-MM-DD for personal synodic Ki
    """
    if target_date:
        td = datetime.fromisoformat(target_date)
        if td.tzinfo is None:
            td = td.replace(tzinfo=TZ)
    else:
        td = datetime.now(TZ)

    # Surrounding Jupiter perihelia — informational layer only, never the gate.
    current_year = td.year + td.month / 12
    peri_jd = _find_jupiter_perihelion(current_year)
    peri_dt = _jd_to_dt(peri_jd)
    next_peri_jd = _find_jupiter_perihelion(current_year + 12)
    next_peri_dt = _jd_to_dt(next_peri_jd)

    now_jd = _dt_to_jd(td)

    # Synodic gate Ki: arithmetic 12-year gates (see synodic_ki_for_year).
    td_ki_year = ki_year_of(td.date())
    synodic_ki = synodic_ki_for_year(td_ki_year)
    gate_start_year = synodic_gate_start(td_ki_year)
    current_gate_lichun = _find_lichun(gate_start_year)
    gate_lichun_dt = _jd_to_dt(current_gate_lichun)
    gate_year_ki = _year_ki(gate_start_year, 2, 4)
    next_gate_lichun_dt = _jd_to_dt(_find_lichun(gate_start_year + SYNODIC_GATE_YEARS))

    perihelia_chain = []
    for offset in range(-9, 3):
        pjd = _find_jupiter_perihelion(current_year + offset * 11.86)
        pdt = _jd_to_dt(pjd)
        ly = ki_year_of(pdt.date())
        perihelia_chain.append({
            "perihelion": pdt.strftime("%Y-%m-%d"),
            "lichun_year": ly,
            "year_ki": _year_ki(ly, 2, 4),
            "synodic_ki": synodic_ki_for_year(ly),
        })

    # Progress through current synodic gate
    orbital_period = (next_peri_jd - peri_jd) / 365.25
    years_into_gate = (now_jd - current_gate_lichun) / 365.25
    gate_length_years = SYNODIC_GATE_YEARS

    # Personal synodic Ki
    personal_synodic = None
    if birth_date:
        bd = datetime.fromisoformat(birth_date)
        natal_yki = _year_ki(bd.year, bd.month, bd.day)
        personal_synodic = _flying_star(natal_yki, synodic_ki)

    result = {
        "synodic_gate": {
            "ki": synodic_ki,
            "element": "Earth" if synodic_ki in [2, 5, 8] else ("Man" if synodic_ki in [1, 4, 7] else "Heaven"),
        },
        "current_perihelion": {
            "date": peri_dt.strftime("%Y-%m-%d"),
            "distance_au": round(swe.calc_ut(peri_jd, swe.JUPITER, swe.FLG_HELCTR)[0][2], 4),
        },
        "gate_boundary": {
            "lichun_date": gate_lichun_dt.strftime("%Y-%m-%d"),
            "year_ki_at_boundary": gate_year_ki,
        },
        "progress": {
            "years_into_gate": round(years_into_gate, 2),
            "gate_length_years": round(gate_length_years, 2),
            "percent": round(years_into_gate / gate_length_years * 100, 1),
        },
        "next_perihelion": {
            "date": next_peri_dt.strftime("%Y-%m-%d"),
        },
        "next_gate": {
            "lichun_date": next_gate_lichun_dt.strftime("%Y-%m-%d"),
            "ki": synodic_ki_for_year(gate_start_year + SYNODIC_GATE_YEARS),
        },
        "orbital_period_years": round(orbital_period, 3),
        "cycle_108": {
            "gates_per_cycle": 9,
            "years_per_cycle": "~108",
            "current_gate_position": f"{synodic_ki}/9",
        },
        "perihelia_chain": perihelia_chain,
    }

    if personal_synodic is not None:
        result["personal_synodic"] = {
            "ki": personal_synodic,
            "natal_year_ki": natal_yki,
        }

    return result


def _flying_star(natal_ki: int, global_ki: int) -> int:
    """Apply Flying Star transformation to convert global Ki to personal Ki.

    Uses the Lo Shu Flying Star sequence [5,6,7,8,9,1,2,3,4].
    Personal Ki = natal Ki's position when global Ki occupies the center.
    Applied independently to each level (year, month, day, hour).
    """
    FLYING_SEQUENCE = [5, 6, 7, 8, 9, 1, 2, 3, 4]
    NUM_TO_IDX = {n: i for i, n in enumerate(FLYING_SEQUENCE)}
    shift = -NUM_TO_IDX[global_ki]
    new_idx = (NUM_TO_IDX[natal_ki] + shift) % 9
    return FLYING_SEQUENCE[new_idx]


def get_convergence_ki(target_date: str = None, lat: float = 28.5383,
                        lon: float = -81.3792,
                        birth_date: str = None) -> dict:
    """Calculate full convergence Ki state for a given date and location.

    **EXPERIMENTAL ASTRONOMICAL MODEL** — This day Ki calculation uses Moon
    socket crossings (every ~9 days) instead of the traditional daily cascade.
    The convergence socket theory is a modern astronomical interpretation,
    not classical 9 Star Ki practice.

    For traditional personal daily Ki, use `get_daily_ki` instead.

    Returns year, month, day, and hour Ki with astronomical positions,
    socket crossings, gates, and timing. If birth_date is provided,
    also returns personal Ki (year/day/hour offset by natal year Ki).

    Args:
        target_date: ISO date string YYYY-MM-DD (default: today)
        lat: Latitude for hour Ki / ascendant (default: Orlando)
        lon: Longitude for hour Ki / ascendant (default: Orlando)
        birth_date: Birth date YYYY-MM-DD for personal Ki calculation
    """
    if target_date:
        td = datetime.fromisoformat(target_date)
        if td.tzinfo is None:
            td = td.replace(tzinfo=TZ)
    else:
        td = datetime.now(TZ)

    now_jd = _dt_to_jd(td)

    # ── Year Ki ──
    yki = _year_ki(td.year, td.month, td.day)
    lichun_year, months_from_lichun = ki_month_of(td.date())

    # ── Month Ki ──
    # Sun position determines month
    sun = swe.calc_ut(now_jd, swe.SUN)[0]
    sun_lon = sun[0]
    sun_sign = SIGN_NAMES[int(sun_lon / 30)]
    sun_deg = sun_lon % 30

    # Month Ki: one continuous count, descending 1 per Ki month across every Lichun.
    # 12 mod 9 = 3, so each Feb starts 3 lower than the last:
    # year Ki 1/4/7 start month at 8; 9/6/3 start at 5; 8/5/2 start at 2.
    month_starts = {1: 8, 4: 8, 7: 8, 3: 5, 6: 5, 9: 5, 2: 2, 5: 2, 8: 2}
    month_start_ki = month_starts[yki]

    # Which month are we in? months_from_lichun counts the Sun's 15°-of-sign crossings
    # since Lichun, by local date (ki_calendar): 0 = Feb … 11 = Jan.
    mki = (month_start_ki - months_from_lichun) % 9
    if mki <= 0:
        mki += 9

    # ── Day Ki ──
    # Day Ki uses the -3 cascade: day_start = month_start - 3 (mod 9).
    # Counts down by 1 per solar day from Lichun.
    # 365 mod 9 = 5 → all 9 starting values appear over 9 years.
    # Month always starts Earth (8, 5, 2). Day start values over 9 years:
    # 5, 9, 4, 8, 3, 7, 2, 6, 1 (for global years 1, 9, 8, 7, 6, 5, 4, 3, 2).
    # Moon is NOT structural for day Ki — kept as parallel observation layer only.
    lichun_jd = _find_lichun(lichun_year)

    # Day start from -3 cascade: month_start - 3
    day_starts = {1: 5, 9: 9, 8: 4, 7: 8, 6: 3, 5: 7, 4: 2, 3: 6, 2: 1}
    day_start_ki = day_starts[yki]

    # Count solar days since Lichun using calendar dates (not JD fractional math).
    # Lichun day itself = offset 0 = day_start_ki, regardless of what time Lichun falls.
    # JD subtraction gives wrong results when Lichun is mid-afternoon.
    lichun_dt = _jd_to_dt(lichun_jd)
    lichun_date = lichun_dt.date()
    today_date = td.date()
    days_since_lichun = (today_date - lichun_date).days

    # Day Ki counts down by 1 per day
    dki = (day_start_ki - (days_since_lichun % 9)) % 9
    if dki <= 0:
        dki += 9

    # ── Hour Ki ──
    # Hour Ki uses the -3 cascade: hour_start = day_ki - 3 (mod 9).
    # 12 double-hours per day (Chinese shíchén), descending by 1 each.
    # Rat hour (23:00-01:00) = hour 1, Ox (01-03) = 2, ... Pig (21-23) = 12.
    # Hour shifts by 3 per day (12 mod 9 = 3).
    # Hour always starts Earth at Lichun (2, 5, 8).
    hour_start_ki = (dki - 3) % 9
    if hour_start_ki <= 0:
        hour_start_ki += 9

    # Determine current double-hour (1-12, starting at 23:00)
    local_hour = td.hour
    if local_hour >= 23:
        double_hour = 1
    elif local_hour < 1:
        double_hour = 1
    else:
        double_hour = (local_hour + 1) // 2 + 1

    hki = (hour_start_ki - (double_hour - 1)) % 9
    if hki <= 0:
        hki += 9

    DOUBLE_HOUR_NAMES = ['Rat','Ox','Tiger','Rabbit','Dragon','Snake',
                         'Horse','Goat','Monkey','Rooster','Dog','Pig']
    current_dh_name = DOUBLE_HOUR_NAMES[double_hour - 1]
    # Double hour number (1-12) is the primary identifier; animal names kept as reference only

    # ── Minute Ki ──
    # 5th level: minute_start = hour_ki - 3 (mod 9).
    # 9 segments per double-hour (~13.3 min each), descending by 1.
    # 9/9 = remainder 0 → all 9 numbers appear once per double-hour.
    minute_start_ki = (hki - 3) % 9
    if minute_start_ki <= 0:
        minute_start_ki += 9

    # Which minute segment are we in? (1-9)
    # Each double-hour = 120 minutes, each segment = 120/9 = 13.333 min
    dh_start_hour = (23 + (double_hour - 1) * 2) % 24
    minutes_into_dh = ((local_hour - dh_start_hour) % 24) * 60 + td.minute
    minute_segment = min(int(minutes_into_dh / (120 / 9)) + 1, 9)

    min_ki = (minute_start_ki - (minute_segment - 1)) % 9
    if min_ki <= 0:
        min_ki += 9

    # Also compute ascendant for observation (parallel layer, not structural)
    houses = swe.houses(now_jd, lat, lon, b'P')
    asc = houses[1][0]
    asc_sign = SIGN_NAMES[int(asc / 30)]
    asc_deg = asc % 30
    current_gate = int(asc / 15) * 15

    # ── Moon position ──
    moon = swe.calc_ut(now_jd, swe.MOON)[0]
    moon_lon = moon[0]
    moon_sign = SIGN_NAMES[int(moon_lon / 30)]
    moon_deg = moon_lon % 30

    # ── Lunar Gate Ki (Moon crossing 12 mid-sign gates per sidereal month) ──
    # Find start of current sidereal month (last S1 crossing)
    sid_month_start_jd = _find_moon_sidereal_month_start(now_jd)
    # Find all mid-sign crossings since sidereal month start
    lunar_gate_crossings = _find_moon_midsign_crossings(sid_month_start_jd, now_jd + 5)
    lunar_gates_passed = [c for c in lunar_gate_crossings if c["jd"] <= now_jd]
    lunar_gate_count = len(lunar_gates_passed)

    # Lunar gate Ki: count down from the day Ki at the sidereal month start.
    # Use the solar day cascade to find what day Ki was at the S1 crossing.
    days_to_s1 = int(sid_month_start_jd - lichun_jd)
    sid_month_start_ki = (day_start_ki - (days_to_s1 % 9)) % 9
    if sid_month_start_ki <= 0:
        sid_month_start_ki += 9

    # The S1 crossing IS the first lunar gate (15° Aquarius is a mid-sign gate)
    # So lunar_gate_count includes the S1 itself as gate #1
    # Subsequent gates count down from there
    lunar_gate_ki = (sid_month_start_ki - (lunar_gate_count - 1)) % 9
    if lunar_gate_ki <= 0:
        lunar_gate_ki += 9

    # Current and next lunar gate
    last_lunar_gate = lunar_gates_passed[-1] if lunar_gates_passed else None
    future_lunar_gates = [c for c in lunar_gate_crossings if c["jd"] > now_jd]
    next_lunar_gate = future_lunar_gates[0] if future_lunar_gates else None

    # ── Apsidal info ──
    apogee = swe.calc_ut(now_jd, swe.MEAN_APOG)[0]
    apogee_lon = apogee[0]
    apogee_sign = SIGN_NAMES[int(apogee_lon / 30)]
    apogee_deg = apogee_lon % 30

    # Which arc has the long leg?
    if apogee_lon >= 315 or apogee_lon < 75:
        long_leg = "S1→S2 (Aquarius→Gemini)"
    elif 75 <= apogee_lon < 195:
        long_leg = "S2→S3 (Gemini→Libra)"
    else:
        long_leg = "S3→S1 (Libra→Aquarius)"

    # ── Synodic Ki (Great Year / Jupiter orbit) ──
    synodic_data = get_synodic_gate(
        target_date=td.strftime("%Y-%m-%d") if target_date else None,
        birth_date=birth_date,
    )
    synodic_ki = synodic_data.get("synodic_gate", {}).get("ki", None)

    # ── Build result ──
    result = {
        "timestamp": td.isoformat(),
        "build": BUILD,
        "location": {"lat": lat, "lon": lon},

        "synodic": {
            "ki": synodic_ki,
            "gate": synodic_data.get("current_gate", {}),
            "anchor": "12 Ki years per great year, gates at Lichun on Earth years; Jupiter's ~11.86-yr cycle is the natural period, not the anchor.",
        },

        "year": {
            "ki": yki,
            "period": " → ".join(d.strftime("%b %-d, %Y") for d in ki_year_span(lichun_year)),
            "anchor": "Sun at Lichun (15° Aquarius). Apsidal precession (~8.85yr) drives socket asymmetry.",
        },

        "month": {
            "ki": mki,
            "sun": f"{sun_deg:.1f}° {sun_sign}",
            "sun_ecliptic": round(sun_lon, 2),
            "anchor": "Sun crossing 15° of each sign",
        },

        "lunar_gate": {
            "ki": lunar_gate_ki,
            "gates_since_sid_month": lunar_gate_count,
            "sid_month_start": _jd_to_dt(sid_month_start_jd).strftime("%Y-%m-%d %I:%M %p"),
            "last_gate": {
                "sign": last_lunar_gate["sign"] if last_lunar_gate else None,
                "date": _jd_to_dt(last_lunar_gate["jd"]).strftime("%Y-%m-%d %I:%M %p") if last_lunar_gate else None,
                "is_socket": last_lunar_gate["is_socket"] if last_lunar_gate else None,
            },
            "next_gate": {
                "sign": next_lunar_gate["sign"] if next_lunar_gate else None,
                "date": _jd_to_dt(next_lunar_gate["jd"]).strftime("%Y-%m-%d %I:%M %p") if next_lunar_gate else None,
                "is_socket": next_lunar_gate["is_socket"] if next_lunar_gate else None,
            },
            "math": "12 gates per sidereal month, 12/9 = remainder 3",
            "anchor": "Moon crossing 15° of each sign (~2.3 days per gate)",
        },

        "day": {
            "ki": dki,
            "day_start_ki": day_start_ki,
            "days_since_lichun": days_since_lichun,
            "lichun": _jd_to_dt(lichun_jd).strftime("%Y-%m-%d %I:%M %p"),
            "anchor": "Solar day cascade: day_start = month_start - 3. Counts down 1/day from Lichun. 365 mod 9 = 5 ensures full 9-year continuity.",
        },

        "hour": {
            "ki": hki,
            "double_hour": double_hour,
            "double_hour_name": current_dh_name,
            "hour_start_ki": hour_start_ki,
            "ascendant": f"{asc_deg:.1f}° {asc_sign} (observation layer)",
            "anchor": "Hour cascade: hour_start = day_ki - 3. 12 double-hours/day, descend 1 each. Shift 3/day.",
        },



        "apsidal": {
            "apogee": f"{apogee_deg:.1f}° {apogee_sign}",
            "apogee_ecliptic": round(apogee_lon, 2),
            "long_leg": long_leg,
            "note": "Apogee determines which day Ki leg is longest",
        },

        "summary": f"Synodic {synodic_ki} · Year {yki} · Month {mki} · Day {dki} · Hour {hki}",

        "framework": {
            "note": "Three bodies, same 12 mid-sign gates, same 15°, same 9 Ki, same remainder 3. One relationship, three octaves.",
            "solar":      {"body": "Sun",       "cycle": "Tropical year",    "gates_per_cycle": 12, "gate_duration": "~30 days",  "repeats_after": "9 years"},
            "lunar":      {"body": "Moon",      "cycle": "Sidereal month",   "gates_per_cycle": 12, "gate_duration": "~2.3 days", "repeats_after": "9 sidereal months"},
            "terrestrial":{"body": "Ascendant", "cycle": "Sidereal day",     "gates_per_cycle": 12, "gate_duration": "~2 hours",  "repeats_after": "9 sidereal days"},
        },
    }

    # ── Personal Ki (if birth_date provided) ──
    if birth_date:
        from ki import calculate_ki, get_full_profile
        from datetime import date as date_type

        bd = date_type.fromisoformat(birth_date)
        natal_yki = _year_ki(bd.year, bd.month, bd.day)

        # Personal Ki = Flying Star applied independently to each global level.
        # The natal year Ki transforms every level the same way.
        # Global 1 with natal 5 → personal 9 at ALL levels where global=1.
        profile = get_full_profile(bd, td.date() if hasattr(td, 'date') else td)
        personal_synodic = _flying_star(natal_yki, synodic_ki) if synodic_ki else None
        personal_year = _flying_star(natal_yki, yki)
        personal_month = _flying_star(natal_yki, mki)
        personal_dki = _flying_star(natal_yki, dki)
        personal_hki = _flying_star(natal_yki, hki)

        result["personal"] = {
            "natal_ki": profile['natal']['sequence'],
            "natal_year_ki": natal_yki,
            "synodic": {"ki": personal_synodic} if personal_synodic else None,
            "year": {"ki": personal_year},
            "month": {"ki": personal_month},
            "day": {"ki": personal_dki},
            "hour": {"ki": personal_hki},
            "summary": f"Personal: Synodic {personal_synodic} · Year {personal_year} · Month {personal_month} · Day {personal_dki} · Hour {personal_hki}",
        }

    return result


# The 24 gates (0° and 15° of each sign) carry one number family each, in rotation from 0° Aries.
GATE_FAMILIES = ([1, 4, 7], [3, 6, 9], [2, 5, 8])


def gate_family(ecliptic_lon: float) -> list:
    """The three Ki numbers a 15° gate can carry. Which one is live depends on the cycle."""
    return GATE_FAMILIES[(int(ecliptic_lon / 15) % 24) % 3]


def _family_label(nums: list) -> str:
    from hub_inheritance import TRIGRAM_NAME
    return " · ".join(f"{n} {TRIGRAM_NAME[n]}" if n != 5 else "5 ☯" for n in nums)


def natal_gates_from_chart(name: str, chart: dict) -> dict:
    """Map a chart's planets and angles to their 15° gates, each gate's number family (with
    trigrams), and the convergence sockets. Structural: it does not change with time or place."""
    planets_raw = chart.get("planets", [])
    angles_raw = chart.get("angles", {})

    results = []
    family_counts = {" · ".join(map(str, f)): 0 for f in GATE_FAMILIES}

    def _process_body(body_name, lon):
        lon = float(lon)
        gate = int(lon / 15) * 15
        family = gate_family(lon)
        is_socket = gate in [315, 75, 195]
        socket_name = CONVERGENCE_SOCKETS[float(gate)]["name"] if is_socket else None
        sign_idx = int(lon / 30)
        deg = lon % 30
        results.append({
            "planet": body_name,
            "position": f"{deg:.1f}° {SIGN_NAMES[sign_idx]}",
            "ecliptic": round(lon, 2),
            "gate": gate_label(gate),
            "ki": _family_label(family),
            "ki_numbers": family,
            "convergence_socket": socket_name,
        })
        family_counts[" · ".join(map(str, family))] += 1

    if isinstance(planets_raw, list):
        for p in planets_raw:
            if isinstance(p, dict) and "longitude" in p:
                _process_body(p.get("name", "?"), p["longitude"])
    elif isinstance(planets_raw, dict):
        for body_name, data in planets_raw.items():
            if isinstance(data, dict) and "longitude" in data:
                _process_body(body_name, data["longitude"])
            elif isinstance(data, (int, float)):
                _process_body(body_name, data)

    if isinstance(angles_raw, dict):
        for angle_name, data in angles_raw.items():
            if isinstance(data, dict) and "longitude" in data:
                _process_body(angle_name, data["longitude"])
            elif isinstance(data, (int, float)):
                _process_body(angle_name, data)
    elif isinstance(angles_raw, list):
        for a in angles_raw:
            if isinstance(a, dict) and "longitude" in a:
                _process_body(a.get("name", "?"), a["longitude"])

    return {
        "chart": name,
        "planets": results,
        "family_balance": family_counts,
        "socket_planets": [p for p in results if p["convergence_socket"]],
    }


def get_natal_gates(name: str) -> dict:
    """Map a stored chart's planets to their 15° gates and number families.

    Args:
        name: Chart name (e.g., 'chris', 'lisa')
    """
    import json

    charts_dir = Path(__file__).parent / "charts"
    chart_path = charts_dir / f"{name}.json"
    if not chart_path.exists():
        return {"error": f"Chart '{name}' not found. Available: {[f.stem for f in charts_dir.glob('*.json')]}"}
    return natal_gates_from_chart(name, json.loads(chart_path.read_text()))
