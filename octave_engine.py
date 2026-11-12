"""octave_engine — the Octave Calendar page's engine on Stella's clock.

A port of the page's ``src/engine.js`` (trigrams, hub inheritance, King Wen figure, moving lines,
element relation, period and octave) onto Stella's own modules: periods, their bounds and their
numbers come from ``ki_solar`` (the solar-degree stack), personal numbers from ``ki_levels`` and
trigrams from ``hub_inheritance``. Nothing here re-derives the clock.

A period's figure is its level's trigram over its container's (the level above). A 5 takes the
trigram of the nearest level above it that is not 5; a stack that is 5 all the way up has no figure.

Task 2 adds the native figure (field, shi, ji) and the Lo Shu palace to this module.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import ki_solar
from hub_inheritance import (
    TRIGRAM_ELEMENT, TRIGRAM_LINES, TRIGRAM_PINYIN, HubUnresolvable, king_wen,  # noqa: F401
    moving_lines, resolve as _hub_resolve,
)
from ki_levels import ki, personal, personal_stack  # noqa: F401  (ki re-exported for the packet)

LEVELS = ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")  # container → finer
LABEL = {"great_age": "great age", "ki_age": "Ki Age", "great_year": "great year", "year": "year",
         "month": "month", "day": "day", "hour": "hour"}

# The star's element by number: 1 water; 3, 4 wood; 9 fire; 2, 5, 8 earth; 6, 7 metal.
# A 5 period takes the element of the trigram it inherits (Resolved.element); a 5 native is Earth.
ELEMENT: dict[int, str] = {1: "Water", 2: "Earth", 3: "Wood", 4: "Wood", 5: "Earth",
                           6: "Metal", 7: "Metal", 8: "Earth", 9: "Fire"}

# Wilhelm titles, index = King Wen number.
HEX_NAME: list[str] = [
    "", "The Creative", "The Receptive", "Difficulty at the Beginning", "Youthful Folly", "Waiting", "Conflict",
    "The Army", "Holding Together", "Small Taming", "Treading", "Peace", "Standstill", "Fellowship", "Great Possession",
    "Modesty", "Enthusiasm", "Following", "Work on the Decayed", "Approach", "Contemplation", "Biting Through", "Grace",
    "Splitting Apart", "Return", "Innocence", "Great Taming", "Nourishment", "Great Exceeding", "The Abysmal",
    "The Clinging", "Influence", "Duration", "Retreat", "Great Power", "Progress", "Darkening of the Light", "The Family",
    "Opposition", "Obstruction", "Deliverance", "Decrease", "Increase", "Breakthrough", "Coming to Meet", "Gathering",
    "Pushing Upward", "Oppression", "The Well", "Revolution", "The Cauldron", "The Arousing", "Keeping Still",
    "Development", "Marrying Maiden", "Abundance", "The Wanderer", "The Gentle", "The Joyous", "Dispersion", "Limitation",
    "Inner Truth", "Small Exceeding", "After Completion", "Before Completion",
]
# Gnostic Book of Changes titles where they differ (the page's GNOSTIC map).
GNOSTIC_TITLE: dict[int, str] = {
    1: "The Dynamic", 2: "The Magnetic", 6: "Stress", 7: "Discipline", 4: "Inexperience", 15: "Temperance",
    23: "Disintegration", 12: "Stagnation", 29: "Danger", 30: "Clarity", 46: "Pushing Upward",
    20: "Contemplation", 51: "Shock", 53: "Gradual Progress", 59: "Dispersion", 48: "The Well",
    64: "Unfinished Business",
}

# Wu Xing: generating and controlling cycles.
_GEN = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
_CTL = {"Wood": "Earth", "Fire": "Metal", "Earth": "Water", "Metal": "Wood", "Water": "Fire"}

def upper(level: str) -> Optional[str]:
    """The container of ``level`` (one level up), or None at the top."""
    i = LEVELS.index(level)
    return LEVELS[i - 1] if i > 0 else None


def lower(level: str) -> Optional[str]:
    """The finer level below ``level``, or None at the bottom."""
    i = LEVELS.index(level)
    return LEVELS[i + 1] if i + 1 < len(LEVELS) else None


# ── Trigrams ──

@dataclass(frozen=True)
class Resolved:
    ki: int                          # the number at this level (may be 5)
    source: Optional[int]            # the Ki whose trigram is used (own, or inherited); None if unresolved
    lines: Optional[tuple]           # trigram lines bottom→top, 1 = yang
    element: Optional[str]           # TRIGRAM_ELEMENT[source]
    inherited: Optional[str]         # level the trigram came from, None if own


def _own(k: int) -> Resolved:
    return Resolved(k, k, TRIGRAM_LINES[k], TRIGRAM_ELEMENT[k], None)


def resolve(stack: dict[str, int], level: str) -> Resolved:
    """The trigram for ``level``; a 5 inherits from the nearest level above that is not 5.
    Never raises: a stack that is 5 all the way up resolves to nothing."""
    try:
        r = _hub_resolve(stack, level)
    except HubUnresolvable:
        return Resolved(5, None, None, None, None)
    src = r.source_ki
    return Resolved(r.ki, src, r.lines, TRIGRAM_ELEMENT[src], r.inherited_from)


# ── Figures ──

@dataclass(frozen=True)
class Figure:
    n: int                           # King Wen number
    name: str                        # Wilhelm title
    gnostic: Optional[str]           # Gnostic Book of Changes title where it differs
    lines: tuple[int, ...]           # six lines bottom→top: lower trigram then upper
    up: Resolved
    lo: Resolved


def _figure(up: Resolved, lo: Resolved) -> Figure:
    lines = tuple(lo.lines) + tuple(up.lines)
    n = king_wen(lines)
    return Figure(n, HEX_NAME[n], GNOSTIC_TITLE.get(n), lines, up, lo)


def hex_of(up_ki: int, lo_ki: int) -> Figure:
    """The hexagram of two trigram numbers (neither 5): ``up_ki`` over ``lo_ki``."""
    return _figure(_own(up_ki), _own(lo_ki))


def figure(stack: dict[str, int], level: str) -> Optional[Figure]:
    """The level's trigram over its container's; None at the top level or when either side is unresolved."""
    container = upper(level)
    if container is None:
        return None
    up, lo = resolve(stack, level), resolve(stack, container)
    if up.lines is None or lo.lines is None:
        return None
    return _figure(up, lo)


def moving(a: tuple, b: tuple) -> list[int]:
    """The lines (1 = bottom) where two figures differ."""
    return [m["line"] for m in moving_lines(tuple(a), tuple(b))]


def relation(actor: Optional[str], field: Optional[str]) -> Optional[str]:
    """The actor's element against the field's: resonates | fed_by | feeds | controls | controlled_by."""
    if not actor or not field:
        return None
    if actor == field:
        return "resonates"
    if _GEN[field] == actor:
        return "fed_by"
    if _GEN[actor] == field:
        return "feeds"
    if _CTL[actor] == field:
        return "controls"
    if _CTL[field] == actor:
        return "controlled_by"
    return None


def line_figure(from_res: Resolved, to_res: Resolved) -> Optional[dict]:
    """The figure of a hexad line: destination over origin, both resolved (a 5 inherits). Moving lines are
    the figure against the origin doubled (Gen → Kan gives 39 with lines 5 and 6)."""
    if from_res.source is None or to_res.source is None:
        return None
    fig = _figure(to_res, from_res)
    base = _figure(from_res, from_res)
    return {"fig": fig, "base": base, "moving": moving(base.lines, fig.lines),
            "inherited_from": to_res.inherited, "inherited_origin": from_res.inherited}


def triforce(n: int) -> Optional[Figure]:
    """The doubled trigram of a shock or clarity point: 3 → 51, 6 → 1, 9 → 30; None otherwise."""
    return hex_of(n, n) if n in (3, 6, 9) else None


# ── Natal ──

def natal_of(birth_date: str) -> dict:
    """Natal year and month numbers and the personal month, read at local noon of the birth day."""
    y, m, d = (int(x) for x in birth_date.split("-"))
    dt = datetime(y, m, d, 12)
    nums = ki_solar.solar_stack_at(dt)["numbers"]
    year, month = nums["year"], nums["month"]
    return {"year": year, "month": month, "pm": personal(year, month),
            "ki_year": ki_solar.ki_year_at(ki_solar.dt_to_jd(dt))}


# ── Periods and the octave ──

def _role(k: int) -> str:
    return "shock-given" if k == 3 else "shock-made" if k == 6 else "clarity" if k == 9 else "hexad"


@dataclass
class Period:
    level: str
    idx: int
    start: datetime
    end: datetime
    gstack: dict                     # global numbers, top of stack down to ``level``
    pstack: Optional[dict]           # personal numbers (natal given), else None
    stack: dict                      # pstack when natal is given, else gstack
    number: int
    global_number: int
    personal_number: Optional[int]
    own: Resolved                    # the level's own resolved trigram
    fig: Optional[Figure]
    role: str


def period(level: str, idx: int, natal: Optional[int]) -> Period:
    """One period at ``level`` by Stella's continuous index; personal when ``natal`` is given."""
    s, e = ki_solar.period_start_jd(level, idx), ki_solar.period_start_jd(level, idx + 1)
    if s is None or e is None:
        raise ValueError("outside the ephemeris")
    gstack = ki_solar.period_stack(level, idx)
    pstack = personal_stack(natal, gstack) if natal else None
    stack = pstack if natal else gstack
    return Period(
        level=level, idx=idx, start=ki_solar.jd_to_dt(s), end=ki_solar.jd_to_dt(e),
        gstack=gstack, pstack=pstack, stack=stack, number=stack[level],
        global_number=gstack[level], personal_number=pstack[level] if pstack else None,
        own=resolve(stack, level), fig=figure(stack, level), role=_role(stack[level]),
    )


def period_at(level: str, dt: datetime, natal: Optional[int]) -> Period:
    """The period at ``level`` containing ``dt`` (naive = America/New_York)."""
    return period(level, ki_solar.period_index(ki_solar.dt_to_jd(dt), level), natal)


def octave(level: str, idx: int, natal: Optional[int]) -> list[Period]:
    """The nine periods of the octave containing ``idx``, from its 1 (personal when ``natal`` is given)."""
    s0 = ki_solar.octave_start_index(level, idx, natal)
    return [period(level, s0 + i, natal) for i in range(9)]
