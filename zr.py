"""
Zodiacal Releasing Calculator
Native implementation for Stella MCP server.

Based on Vettius Valens' technique (Anthology IV) as explained by Chris Brennan,
Hellenistic Astrology ch. 18. Uses the Egyptian year (360 days) and month (30 days).

Construction of the sub-periods, at every level:
  - the sub-periods of a period run through the twelve signs in zodiacal order,
    starting from the period's own sign, each lasting its sign-number of units
    (months under a general period, 2.5 days under a month, and so on);
  - the twelve signs add up to 211 units. A period longer than that completes a
    full cycle, and the bond is loosed: the sub-periods jump to the sign OPPOSITE
    the starting sign and continue in order from there (they do not restart);
  - the last sub-period is cut at the parent's end.
Peak periods and angular triads are always counted from the Lot of Fortune.
When Spirit falls in the same sign as Fortune, Spirit releases from the next sign.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Iterator, Sequence
from dataclasses import dataclass, field

# Sign periods - minor years of planetary rulers
SIGN_YEARS = {
    "Aries": 15,       # Mars
    "Taurus": 8,       # Venus
    "Gemini": 20,      # Mercury
    "Cancer": 25,      # Moon
    "Leo": 19,         # Sun
    "Virgo": 20,       # Mercury
    "Libra": 8,        # Venus
    "Scorpio": 15,     # Mars
    "Sagittarius": 12, # Jupiter
    "Capricorn": 27,   # Saturn
    "Aquarius": 30,    # Saturn
    "Pisces": 12,      # Jupiter
}

SIGN_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# One full cycle of twelve sub-periods, in the sub-level's unit
CYCLE_YEARS = sum(SIGN_YEARS.values())  # 211

# Egyptian calendar
EGYPTIAN_YEAR = 360  # days
EGYPTIAN_MONTH = 30  # days

# Level multipliers (days per "year" at each level)
LEVEL_MULTIPLIERS = {
    1: EGYPTIAN_YEAR,           # L1: years → 360 days per year
    2: EGYPTIAN_MONTH,          # L2: months → 30 days per "year"
    3: EGYPTIAN_MONTH / 12,     # L3: ~2.5 days per "year"
    4: EGYPTIAN_MONTH / 144,    # L4: ~0.208 days per "year" (~5 hours)
    5: EGYPTIAN_MONTH / 1728,   # L5: ~0.017 days per "year" (~25 min)
    6: EGYPTIAN_MONTH / 20736,  # L6: ~0.0014 days per "year" (~2 min 5 s)
}
MAX_LEVEL = max(LEVEL_MULTIPLIERS)

RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


@dataclass
class ZRPeriod:
    """A single Zodiacal Releasing period."""
    sign: str
    start: datetime
    end: datetime
    level: int
    is_angular: bool          # angular from the lot being released (NOT the peak test)
    is_peak: bool             # angular from Fortune (peak periods are ALWAYS from Fortune)
    peak_type: Optional[str]  # "Major Peak", "Moderate Peak", "Minor Peak", or None
    ruler: str
    house_from_fortune: int = 0           # 1..12, whole-sign from Fortune
    angularity: str = ""                  # "angular" | "succedent" | "cadent", from Fortune
    phase: str = ""                       # angular triad: "preparatory" | "peak" | "completion"
    loosing_at: Optional[datetime] = None # when THIS period's sub-periods loose the bond
    is_loosing_of_bond: bool = False      # this period lies in the loosed portion of its parent
    is_pre_loosing: bool = False          # last sub-period of the parent's first cycle

    @property
    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt < self.end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sign": self.sign,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "level": self.level,
            "ruler": self.ruler,
            "duration_days": round(self.duration_days, 2),
            "is_angular": self.is_angular,
            "is_peak": self.is_peak,
            "peak_type": self.peak_type,
            "house_from_fortune": self.house_from_fortune,
            "angularity": self.angularity,
            "phase": self.phase,
            "loosing_at": self.loosing_at.isoformat() if self.loosing_at else None,
            "is_loosing_of_bond": self.is_loosing_of_bond,
            "is_pre_loosing": self.is_pre_loosing,
        }


@dataclass
class ZRSnapshot:
    """Complete ZR state at a specific moment."""
    target_date: datetime
    lot: str
    lot_sign: str
    lot_degree: float
    L1: ZRPeriod
    L2: ZRPeriod
    L3: ZRPeriod
    L4: ZRPeriod
    L5: ZRPeriod
    L6: ZRPeriod
    is_loosing_of_bond: bool          # the L2 period is in the loosed portion of L1
    loosing_details: Optional[str]
    release_sign: str = ""            # sign the releasing starts from (differs from lot_sign
                                      # only when Spirit shares Fortune's sign)
    fortune_sign: str = ""

    def __post_init__(self):
        if not self.release_sign:
            self.release_sign = self.lot_sign

    @property
    def levels(self) -> List[ZRPeriod]:
        return [self.L1, self.L2, self.L3, self.L4, self.L5, self.L6]

    def to_dict(self) -> Dict[str, Any]:
        loosed = [f"L{p.level}" for p in self.levels if p.is_loosing_of_bond]
        return {
            "target_date": self.target_date.isoformat(),
            "lot": self.lot,
            "lot_sign": self.lot_sign,
            "lot_degree": round(self.lot_degree, 2),
            "release_sign": self.release_sign,
            "fortune_sign": self.fortune_sign,
            "L1": self.L1.to_dict(),
            "L2": self.L2.to_dict(),
            "L3": self.L3.to_dict(),
            "L4": self.L4.to_dict(),
            "L5": self.L5.to_dict(),
            "L6": self.L6.to_dict(),
            "is_loosing_of_bond": self.is_loosing_of_bond,
            "loosing_details": self.loosing_details,
            "loosed_levels": loosed,
        }


# ── Sign arithmetic ──────────────────────────────────────────────────────────

def get_sign_index(sign: str) -> int:
    return SIGN_ORDER.index(sign)


def get_sign_at_offset(start_sign: str, offset: int) -> str:
    start_idx = get_sign_index(start_sign)
    return SIGN_ORDER[(start_idx + offset) % 12]


def opposite_sign(sign: str) -> str:
    return get_sign_at_offset(sign, 6)


def get_ruler(sign: str) -> str:
    return RULERS[sign]


def house_from(sign: str, from_sign: str) -> int:
    """Whole-sign house of `sign` counted from `from_sign` (1..12)."""
    return (get_sign_index(sign) - get_sign_index(from_sign)) % 12 + 1


def is_angular_from(sign: str, lot_sign: str) -> bool:
    """Check if sign is angular (1st, 4th, 7th, 10th) from lot sign."""
    return house_from(sign, lot_sign) in (1, 4, 7, 10)


def get_angularity_from_fortune(sign: str, fortune_sign: str) -> str:
    """angular (1, 4, 7, 10), succedent (2, 5, 8, 11) or cadent (3, 6, 9, 12) from Fortune."""
    h = house_from(sign, fortune_sign)
    if h in (1, 4, 7, 10):
        return "angular"
    if h in (2, 5, 8, 11):
        return "succedent"
    return "cadent"


def get_triad_phase(sign: str, fortune_sign: str) -> str:
    """
    Angular triad phase from Fortune (Brennan, ch. 18, fig. 18.5).
    Each Fortune angle has a beginning, a middle and an end:
      preparatory = the cadent sign before the angle (12th, 3rd, 6th, 9th)
      peak        = the angle itself (1st, 4th, 7th, 10th)
      completion  = the succedent sign after it (2nd, 5th, 8th, 11th)
    """
    return {
        "cadent": "preparatory",
        "angular": "peak",
        "succedent": "completion",
    }[get_angularity_from_fortune(sign, fortune_sign)]


def get_peak_type_from_fortune(sign: str, fortune_sign: str) -> Optional[str]:
    """
    Determine peak type based on angularity from Lot of Fortune.
    Peak periods are ALWAYS calculated from Fortune, regardless of which lot is released.

    Per Brennan's worksheet:
    - 1st from Fortune (Fortune itself) = Major Peak
    - 10th from Fortune = Major Peak
    - 7th from Fortune = Moderate Peak
    - 4th from Fortune = Minor Peak
    """
    h = house_from(sign, fortune_sign)
    if h in (1, 10):
        return "Major Peak"
    if h == 7:
        return "Moderate Peak"
    if h == 4:
        return "Minor Peak"
    return None


# ── Period lengths ───────────────────────────────────────────────────────────

def get_period_days(sign: str, level: int) -> float:
    """Get duration in days for a sign at a given level."""
    return SIGN_YEARS[sign] * LEVEL_MULTIPLIERS[level]


def get_cycle_days(level: int) -> float:
    """Length of one full cycle of twelve sub-periods at `level` (211 units)."""
    return CYCLE_YEARS * LEVEL_MULTIPLIERS[level]


def loosing_time(period_start: datetime, period_end: Optional[datetime], level: int) -> Optional[datetime]:
    """When the sub-periods (at level + 1) of a period starting at `period_start`
    loose the bond, or None if the period ends before they complete a cycle."""
    if level >= MAX_LEVEL:
        return None
    at = period_start + timedelta(days=get_cycle_days(level + 1))
    if period_end is not None and at >= period_end:
        return None
    return at


def _make_period(sign: str, start: datetime, end: datetime, level: int,
                 lot_sign: str, fortune_sign: str,
                 parent_end: Optional[datetime],
                 loosed: bool, pre_loosing: bool) -> ZRPeriod:
    peak_type = get_peak_type_from_fortune(sign, fortune_sign)
    return ZRPeriod(
        sign=sign,
        start=start,
        end=end,
        level=level,
        is_angular=is_angular_from(sign, lot_sign),
        is_peak=peak_type is not None,
        peak_type=peak_type,
        ruler=get_ruler(sign),
        house_from_fortune=house_from(sign, fortune_sign),
        angularity=get_angularity_from_fortune(sign, fortune_sign),
        phase=get_triad_phase(sign, fortune_sign),
        loosing_at=loosing_time(start, end, level),
        is_loosing_of_bond=loosed,
        is_pre_loosing=pre_loosing,
    )


def iter_subperiods(
    start_sign: str,
    parent_start: datetime,
    parent_end: Optional[datetime],
    level: int,
    lot_sign: str,
    fortune_sign: str,
) -> Iterator[ZRPeriod]:
    """
    Yield the periods at `level` filling [parent_start, parent_end) in order.

    Starts from `start_sign` (the parent's sign) and runs through the twelve signs.
    After each full cycle the bond is loosed: the next sign is the one opposite the
    sign that opened the cycle. The final period is cut at parent_end. With
    parent_end None (level 1) the sequence is unbounded.
    """
    current_dt = parent_start
    cycle_start_sign = start_sign
    current_sign = start_sign
    position = 0          # index within the current cycle, 0..11
    loosed = False

    while parent_end is None or current_dt < parent_end:
        period_end = current_dt + timedelta(days=get_period_days(current_sign, level))
        cut = parent_end is not None and period_end >= parent_end
        if cut:
            period_end = parent_end
        # the 12th sub-period of the first cycle is pre-loosing only if the loosing happens
        pre_loosing = (not loosed and position == 11 and not cut)
        yield _make_period(current_sign, current_dt, period_end, level, lot_sign, fortune_sign,
                           parent_end, loosed, pre_loosing)
        if cut:
            return
        current_dt = period_end
        position += 1
        if position == 12:
            # Loosing of the bond: jump to the opposite sign and continue from there
            cycle_start_sign = opposite_sign(cycle_start_sign)
            current_sign = cycle_start_sign
            position = 0
            loosed = True
        else:
            current_sign = get_sign_at_offset(current_sign, 1)


def find_period_at_level(
    start_sign: str,
    level_start: datetime,
    target_dt: datetime,
    level: int,
    lot_sign: str,
    fortune_sign: str,
    level_end: Optional[datetime] = None,
) -> ZRPeriod:
    """
    Find which period contains target_dt at given level.

    lot_sign: the lot being released (for is_angular)
    fortune_sign: Lot of Fortune sign (for peaks, triads and classification)
    level_end: end of the parent period; the last sub-period is cut there
    """
    if target_dt < level_start or (level_end is not None and target_dt >= level_end):
        raise ValueError(f"{target_dt} is outside the parent period at level {level}")
    for period in iter_subperiods(start_sign, level_start, level_end, level, lot_sign, fortune_sign):
        if period.contains(target_dt):
            return period
    raise ValueError(f"Could not find period at level {level} for {target_dt}")


def release_sign_for(lot_sign: str, lot_name: str, fortune_sign: str) -> str:
    """Sign the releasing starts from. Spirit in Fortune's sign releases from the next sign
    (Valens, Anthology IV; Brennan ch. 18)."""
    if lot_name.lower() == "spirit" and lot_sign == fortune_sign:
        return get_sign_at_offset(lot_sign, 1)
    return lot_sign


def calculate_zr(
    lot_sign: str,
    lot_degree: float,
    birth_dt: datetime,
    target_dt: datetime,
    lot_name: str = "spirit",
    fortune_sign: Optional[str] = None,
) -> ZRSnapshot:
    """
    Calculate complete Zodiacal Releasing snapshot.

    Each level has fixed period lengths (years/months/days). L2 starts from the L1
    sign at the L1 start, L3 from the L2 sign at the L2 start, and so on, with the
    loosing of the bond applied at every level.

    Peak periods are ALWAYS calculated from Fortune, per Brennan/Valens.
    fortune_sign must be provided for accurate peak marking.
    If not provided, falls back to lot_sign (only correct when releasing from Fortune).
    """
    f_sign = fortune_sign if fortune_sign else lot_sign
    start_sign = release_sign_for(lot_sign, lot_name, f_sign)

    periods: List[ZRPeriod] = []
    parent_sign, parent_start, parent_end = start_sign, birth_dt, None
    for level in range(1, MAX_LEVEL + 1):
        p = find_period_at_level(parent_sign, parent_start, target_dt, level, lot_sign, f_sign, parent_end)
        periods.append(p)
        parent_sign, parent_start, parent_end = p.sign, p.start, p.end

    l1, l2, l3, l4, l5, l6 = periods

    loosing_details = None
    if l2.is_loosing_of_bond:
        loosing_details = (f"L1 {l1.sign} loosed the bond on {l1.loosing_at:%Y-%m-%d}: "
                           f"L2 jumped to {opposite_sign(l1.sign)}, now {l2.sign} ({l2.ruler})")
    elif l2.is_pre_loosing:
        loosing_details = (f"L2 {l2.sign} is the last period before the loosing of the bond "
                           f"on {l1.loosing_at:%Y-%m-%d} (to {opposite_sign(l1.sign)})")

    return ZRSnapshot(
        target_date=target_dt,
        lot=lot_name,
        lot_sign=lot_sign,
        lot_degree=lot_degree,
        L1=l1,
        L2=l2,
        L3=l3,
        L4=l4,
        L5=l5,
        L6=l6,
        is_loosing_of_bond=l2.is_loosing_of_bond,
        loosing_details=loosing_details,
        release_sign=start_sign,
        fortune_sign=f_sign,
    )


def zr_periods(
    lot_sign: str,
    birth_dt: datetime,
    start: datetime,
    end: datetime,
    levels: Sequence[int] = (1, 2),
    lot_name: str = "spirit",
    fortune_sign: Optional[str] = None,
) -> Dict[str, List[ZRPeriod]]:
    """
    Every period at each requested level that overlaps [start, end).

    Returns {"L1": [...], "L2": [...]} with periods in time order. Deeper levels are
    built by descending through every parent that overlaps the window.
    """
    if end <= start:
        raise ValueError("end must be after start")
    if start < birth_dt:
        start = birth_dt
    f_sign = fortune_sign if fortune_sign else lot_sign
    wanted = sorted(set(int(l) for l in levels))
    if not wanted or wanted[0] < 1 or wanted[-1] > MAX_LEVEL:
        raise ValueError(f"levels must be within 1..{MAX_LEVEL}")

    result: Dict[str, List[ZRPeriod]] = {}
    # parents at the level above: (sign, start, end or None)
    parents = [(release_sign_for(lot_sign, lot_name, f_sign), birth_dt, None)]
    for level in range(1, wanted[-1] + 1):
        found: List[ZRPeriod] = []
        for sign, p_start, p_end in parents:
            for period in iter_subperiods(sign, p_start, p_end, level, lot_sign, f_sign):
                if period.start >= end:
                    break
                if period.end > start:
                    found.append(period)
        if level in wanted:
            result[f"L{level}"] = found
        parents = [(p.sign, p.start, p.end) for p in found]
    return result


# ── Formatting ───────────────────────────────────────────────────────────────

def format_zr_summary(snapshot: ZRSnapshot) -> str:
    """Format ZR snapshot as human-readable summary."""
    head = f"## Zodiacal Releasing from {snapshot.lot.title()} ({snapshot.lot_sign} {snapshot.lot_degree:.0f}°)"
    if snapshot.release_sign != snapshot.lot_sign:
        head += f" — releasing from {snapshot.release_sign} (Spirit shares Fortune's sign)"
    lines = [head, f"**Target:** {snapshot.target_date.strftime('%Y-%m-%d %H:%M')} ", ""]

    for period in snapshot.levels:
        peak = f" ⭐ {period.peak_type}" if period.is_peak else ""
        marks = ""
        if period.is_loosing_of_bond:
            marks += " ⚡ LB"
        if period.is_pre_loosing:
            marks += " ⏳ pre-LB"
        lines.append(
            f"**L{period.level}:** {period.sign} ({period.ruler}){peak}{marks} — "
            f"{period.phase}, {ordinal(period.house_from_fortune)} from Fortune\n"
            f"    {period.start.strftime('%Y-%m-%d %H:%M')} → "
            f"{period.end.strftime('%Y-%m-%d %H:%M')} ({format_duration(period.duration_days)})"
        )

    if snapshot.loosing_details:
        lines.append(f"\n⚡ **Loosing of the Bond:** {snapshot.loosing_details}")

    return "\n".join(lines)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_duration(days: float) -> str:
    """Format duration in human-readable form."""
    if days >= 365:
        return f"{days / 365.25:.1f} years"
    elif days >= 30:
        return f"{days / 30.44:.1f} months"
    elif days >= 1:
        return f"{days:.1f} days"
    else:
        hours = days * 24
        if hours >= 1:
            return f"{hours:.1f} hours"
        else:
            return f"{hours * 60:.1f} minutes"


# ── Chart adapters ───────────────────────────────────────────────────────────

def _chart_lot_inputs(chart_data: Dict[str, Any], lot: str):
    lots = chart_data.get("lots", {})
    birth_data = chart_data.get("birthData", {})

    lot_data = lots.get(lot, {})
    lot_sign = lot_data.get("sign")
    if not lot_sign:
        raise ValueError(f"Chart has no lot '{lot}'")
    lot_degree = float(lot_data.get("degreeInSign", 0))
    fortune_sign = lots.get("fortune", {}).get("sign") or lot_sign

    birth_date = birth_data.get("date")
    birth_time = birth_data.get("time", "12:00:00")
    birth_dt = datetime.fromisoformat(f"{birth_date}T{birth_time}")
    return lot_sign, lot_degree, birth_dt, fortune_sign


def zr_for_chart(
    chart_data: Dict[str, Any],
    target_dt: datetime,
    lot: str = "spirit",
) -> ZRSnapshot:
    """Calculate ZR from a Stella chart.

    Peak periods are always calculated from Lot of Fortune,
    regardless of which lot is being released (per Brennan/Valens).
    """
    lot_sign, lot_degree, birth_dt, fortune_sign = _chart_lot_inputs(chart_data, lot)
    return calculate_zr(lot_sign, lot_degree, birth_dt, target_dt, lot, fortune_sign=fortune_sign)


def zr_periods_for_chart(
    chart_data: Dict[str, Any],
    start: datetime,
    end: datetime,
    lot: str = "spirit",
    levels: Sequence[int] = (1, 2),
) -> Dict[str, List[ZRPeriod]]:
    """Every period overlapping [start, end) for a Stella chart."""
    lot_sign, _degree, birth_dt, fortune_sign = _chart_lot_inputs(chart_data, lot)
    return zr_periods(lot_sign, birth_dt, start, end, levels, lot, fortune_sign)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("usage: python zr.py charts/<name>.json [YYYY-MM-DD]")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        chart = json.load(f)
    target = datetime.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now()
    for lot in ("spirit", "fortune"):
        print(format_zr_summary(zr_for_chart(chart, target, lot)))
        print()
