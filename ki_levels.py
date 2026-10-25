"""ki_levels — Lo Shu arithmetic for the levels of the Ki stack counted in Ki years.

Every level is a count descending 1 per period, never resetting at a seam. Each
level is twelve of the one below (year → great year → Ki Age → great age). 12 mod 9 = 3,
so at every seam the child reads an Earth number (2, 5, 8). Nine of anything is one
cycle of its numbers; twelve of anything is its parent.

Anchors (global chain):
  year        2026 = 1                      (classical)
  month       Feb 2026 = 8                  (continuous count; years 1·4·7 open on 8, 9·6·3 on 5, 8·5·2 on 2)
  great year  Lichun 2010 opens 2           (12 years; gates on the Lichun before Jupiter's perihelion)
  Ki Age      Lichun 2010 opens 5           (144 years)
  great age   Lichun 2010 opens 8           (1,728 years = 12 Ki Ages = 24° of precession, 25,920 / 15)

The great age is anchored by precession: the vernal point reached 24° past the Lahiri
sidereal zero (285 CE) in 2010, and the gate is the Lichun before that crossing, as a
great year's gate is the Lichun before perihelion. Lichun 2010 therefore opened the great
age, the Ki Age and the great year together and the stack read 8 · 5 · 2 · 8 (year 8) —
each level three below the one above. The 2022 great year is 1: a level is Earth at its
seam only when its parent turns too.

Day and hour are not counted in Ki years; they live in ki_solar (degrees of the Sun).

Personal numbers at every level: personal(natal, global) = ki(natal - global + 5).
"""

from typing import Optional

GREAT_YEAR_ANCHOR_YEAR = 2010
GREAT_YEAR_ANCHOR_KI = 2
KI_AGE_ANCHOR_YEAR = 2010
KI_AGE_ANCHOR_KI = 5
GREAT_AGE_ANCHOR_YEAR = 2010
GREAT_AGE_ANCHOR_KI = 8
PERIOD_YEARS = {"great_age": 1728, "ki_age": 144, "great_year": 12, "year": 1}

_ANCHORS = {
    "great_year": (GREAT_YEAR_ANCHOR_YEAR, GREAT_YEAR_ANCHOR_KI),
    "ki_age": (KI_AGE_ANCHOR_YEAR, KI_AGE_ANCHOR_KI),
    "great_age": (GREAT_AGE_ANCHOR_YEAR, GREAT_AGE_ANCHOR_KI),
}

_MONTH_ANCHOR_ABS = 2026 * 12  # Feb 2026


def ki(n: int) -> int:
    """Reduce any integer to the Ki range 1–9."""
    return (n - 1) % 9 + 1


def personal(natal: int, g: int) -> int:
    """Where the natal number lands when the global number sits in the centre. Same at every level."""
    return ki(natal - g + 5)


def global_year(ki_year: int) -> int:
    """Global year Ki: 2026 → 1, descending 1 per Ki year."""
    return ki(2027 - ki_year)


def global_month(abs_month: int) -> int:
    """Global month Ki for abs_month = ki_year * 12 + index (0 = Feb). One continuous count."""
    return ki(8 - (abs_month - _MONTH_ANCHOR_ABS))


def _periods_since_anchor(ki_year: int, level: str) -> int:
    anchor_year, _ = _ANCHORS[level]
    return (ki_year - anchor_year) // PERIOD_YEARS[level]


def _global_level(ki_year: int, level: str) -> int:
    _, anchor_ki = _ANCHORS[level]
    return ki(anchor_ki - _periods_since_anchor(ki_year, level))


def global_great_year(ki_year: int) -> int:
    """Global great year: 2010–2021 = 2, 2022–2033 = 1, 2034–2045 = 9."""
    return _global_level(ki_year, "great_year")


def global_ki_age(ki_year: int) -> int:
    """Global Ki Age: 2010–2153 = 5, 2154–2297 = 4."""
    return _global_level(ki_year, "ki_age")


def global_great_age(ki_year: int) -> int:
    """Global great age: 2010–3737 = 8."""
    return _global_level(ki_year, "great_age")


def gate_start(ki_year: int, level: str) -> int:
    """The Ki year (a Lichun) that opens the great_year / ki_age / great_age period containing ki_year."""
    anchor_year, _ = _ANCHORS[level]
    return anchor_year + _periods_since_anchor(ki_year, level) * PERIOD_YEARS[level]


def global_stack(ki_year: int, abs_month: Optional[int] = None) -> dict[str, int]:
    """The global chain down to the year, and the month when abs_month is given."""
    stack = {
        "great_age": global_great_age(ki_year),
        "ki_age": global_ki_age(ki_year),
        "great_year": global_great_year(ki_year),
        "year": global_year(ki_year),
    }
    if abs_month is not None:
        stack["month"] = global_month(abs_month)
    return stack


def personal_stack(natal_year: int, stack: dict[str, int]) -> dict[str, int]:
    """The personal chain: the natal year read against every global level."""
    return {level: personal(natal_year, g) for level, g in stack.items()}
