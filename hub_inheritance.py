"""hub_inheritance — resolve trigrams for a Ki stack where 5 inherits its parent.

Ki 5 is the hub of the Lo Shu and has no trigram. At any level of the timekeeping
stack (great age → Ki Age → great year → year → month → day → hour) a 5 takes the
trigram of the nearest parent level that is not 5, walking up as far as needed. If
every level up to the top is 5 or missing, nothing can be inherited and
HubUnresolvable is raised rather than guessed.

Moving lines are always the line-by-line difference between two six-line figures;
there is no fixed table.

This is the rule for timekeeping only. The three-number natal reading (ki_reading.py)
keeps its own convention for 5.
"""

from dataclasses import dataclass
from typing import Optional

# Later Heaven / Lo Shu trigram for each Ki. Lines bottom→top, 1 = yang.
TRIGRAM_LINES: dict[int, tuple[int, int, int]] = {
    1: (0, 1, 0),  # ☵ Kan
    2: (0, 0, 0),  # ☷ Kun
    3: (1, 0, 0),  # ☳ Zhen
    4: (0, 1, 1),  # ☴ Xun
    6: (1, 1, 1),  # ☰ Qian
    7: (1, 1, 0),  # ☱ Dui
    8: (0, 0, 1),  # ☶ Gen
    9: (1, 0, 1),  # ☲ Li
}
TRIGRAM_SYMBOL = {1: "☵", 2: "☷", 3: "☳", 4: "☴", 6: "☰", 7: "☱", 8: "☶", 9: "☲"}
TRIGRAM_PINYIN = {1: "Kan", 2: "Kun", 3: "Zhen", 4: "Xun", 6: "Qian", 7: "Dui", 8: "Gen", 9: "Li"}
TRIGRAM_IMAGE = {1: "Water", 2: "Earth", 3: "Thunder", 4: "Wind", 6: "Heaven", 7: "Lake", 8: "Mountain", 9: "Fire"}
# Wu Xing phase of each trigram (3 Thunder and 4 Wind are Wood).
TRIGRAM_ELEMENT = {1: "Water", 2: "Earth", 3: "Wood", 4: "Wood", 6: "Metal", 7: "Metal", 8: "Earth", 9: "Fire"}
TRIGRAM_NAME = {k: f"{TRIGRAM_SYMBOL[k]} {TRIGRAM_PINYIN[k]}" for k in TRIGRAM_LINES}

_LINES_TO_KI = {v: k for k, v in TRIGRAM_LINES.items()}

LEVELS = ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")  # parent → child


class HubUnresolvable(ValueError):
    """Every level up to the top is 5 or missing; nothing to inherit."""


@dataclass(frozen=True)
class ResolvedTrigram:
    ki: int                        # the Ki at this level (may be 5)
    lines: tuple[int, int, int]
    inherited_from: Optional[str]  # level name the trigram came from, None if own

    @property
    def source_ki(self) -> int:
        return _LINES_TO_KI[self.lines]

    @property
    def name(self) -> str:
        n = TRIGRAM_NAME[self.source_ki]
        return f"{n} (inherited from {self.inherited_from})" if self.inherited_from else n


def resolve(stack: dict[str, int], level: str) -> ResolvedTrigram:
    """Trigram for ``level`` in ``stack`` ({'great_year': 2, 'year': 9, 'month': 1, 'day': 5, ...})."""
    ki = stack[level]
    if ki != 5:
        return ResolvedTrigram(ki, TRIGRAM_LINES[ki], None)
    i = LEVELS.index(level)
    for parent in reversed(LEVELS[:i]):
        if stack.get(parent, 5) != 5:
            return ResolvedTrigram(ki, TRIGRAM_LINES[stack[parent]], parent)
    raise HubUnresolvable(f"{level} is 5 and every parent above it is 5 or missing: {stack}")


def hexagram_lines(stack: dict[str, int], upper: str, lower: str) -> tuple[int, ...]:
    """Six lines bottom→top: the lower level's trigram under the upper level's (day over month, etc.)."""
    return resolve(stack, lower).lines + resolve(stack, upper).lines


def moving_lines(deposit: tuple[int, ...], charge: tuple[int, ...]) -> list[dict]:
    """Line-by-line difference, 1-indexed from the bottom. Reports direction only."""
    return [
        {"line": i + 1, "from": "yang" if a else "yin", "to": "yang" if b else "yin"}
        for i, (a, b) in enumerate(zip(deposit, charge)) if a != b
    ]


# King Wen number from six lines (bottom→top). Index = lines as binary, bit 0 = line 1.
KING_WEN = {
    0b000000: 2, 0b000001: 24, 0b000010: 7, 0b000011: 19, 0b000100: 15, 0b000101: 36, 0b000110: 46, 0b000111: 11,
    0b001000: 16, 0b001001: 51, 0b001010: 40, 0b001011: 54, 0b001100: 62, 0b001101: 55, 0b001110: 32, 0b001111: 34,
    0b010000: 8, 0b010001: 3, 0b010010: 29, 0b010011: 60, 0b010100: 39, 0b010101: 63, 0b010110: 48, 0b010111: 5,
    0b011000: 45, 0b011001: 17, 0b011010: 47, 0b011011: 58, 0b011100: 31, 0b011101: 49, 0b011110: 28, 0b011111: 43,
    0b100000: 23, 0b100001: 27, 0b100010: 4, 0b100011: 41, 0b100100: 52, 0b100101: 22, 0b100110: 18, 0b100111: 26,
    0b101000: 35, 0b101001: 21, 0b101010: 64, 0b101011: 38, 0b101100: 56, 0b101101: 30, 0b101110: 50, 0b101111: 14,
    0b110000: 20, 0b110001: 42, 0b110010: 59, 0b110011: 61, 0b110100: 53, 0b110101: 37, 0b110110: 57, 0b110111: 9,
    0b111000: 12, 0b111001: 25, 0b111010: 6, 0b111011: 10, 0b111100: 33, 0b111101: 13, 0b111110: 44, 0b111111: 1,
}


def king_wen(lines: tuple[int, ...]) -> int:
    return KING_WEN[sum(bit << i for i, bit in enumerate(lines))]


def _side(level: str, r: ResolvedTrigram) -> dict:
    k = r.source_ki
    return {
        "level": level, "ki": r.ki, "trigram": r.name, "symbol": TRIGRAM_SYMBOL[k],
        "pinyin": TRIGRAM_PINYIN[k], "image": TRIGRAM_IMAGE[k], "element": TRIGRAM_ELEMENT[k],
        "inherited_from": r.inherited_from,
    }


def hexagram(stack: dict[str, int], upper: str, lower: str) -> dict:
    """The figure of ``upper`` over ``lower`` with both trigrams resolved and any inheritance named."""
    lo, up = resolve(stack, lower), resolve(stack, upper)
    lines = lo.lines + up.lines
    inherited = [{"level": lvl, "from": r.inherited_from}
                 for lvl, r in ((lower, lo), (upper, up)) if r.inherited_from]
    return {
        "hexagram": king_wen(lines),
        "lines": list(lines),
        "lower": _side(lower, lo),
        "upper": _side(upper, up),
        "inherited": inherited,
    }
