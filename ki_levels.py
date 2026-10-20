"""ki_levels — Lo Shu arithmetic for every level of the Ki timekeeping stack.

Every level is a count descending 1 per period, never resetting at a seam. Each
level is twelve of the one below (month → year → great year → Ki Age), and the
great age is nine Ki Ages. 12 mod 9 = 3, so at every seam the child reads an
Earth number (2, 5, 8).

Anchors (global chain):
  year        2026 = 1                      (classical)
  month       Feb 2026 = 8                  (continuous count; years 1·4·7 open on 8, 9·6·3 on 5, 8·5·2 on 2)
  great year  Lichun 2022 opens 8           (12 years; the year there is 5, the month 2)
  Ki Age      Lichun 2022 opens 2           (144 years)
  great age   Lichun 2022 opens 5           (1,296 years)

Read upward at Lichun 2022 the stack is 5 · 2 · 8 · 5 · 2: each level the next Earth
number in the cycle 2 → 5 → 8 → 2. That is the whole justification for the Ki Age
and great age anchors; no doctrinal date is known. The arithmetic alone would also
allow a Ki Age opening in 1914 (next 2058) or 1950 (next 2094). Change the two
constants if a fact turns up.

Personal numbers at every level: personal(natal, global) = ki(natal - global + 5).
"""

from typing import Optional

GREAT_YEAR_ANCHOR_YEAR = 2022
GREAT_YEAR_ANCHOR_KI = 8
KI_AGE_ANCHOR_YEAR = 2022
KI_AGE_ANCHOR_KI = 2
GREAT_AGE_ANCHOR_YEAR = 2022
GREAT_AGE_ANCHOR_KI = 5
PERIOD_YEARS = {"great_age": 1296, "ki_age": 144, "great_year": 12, "year": 1}

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
    """Global great year: 2022–2033 = 8, 2034–2045 = 7."""
    return _global_level(ki_year, "great_year")


def global_ki_age(ki_year: int) -> int:
    """Global Ki Age: 2022–2165 = 2, 2166–2309 = 1."""
    return _global_level(ki_year, "ki_age")


def global_great_age(ki_year: int) -> int:
    """Global great age: 2022–3317 = 5."""
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
