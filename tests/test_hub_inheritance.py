"""Hub inheritance: Ki 5 has no trigram and takes the nearest non-5 parent's.

Run: .venv/bin/python -m pytest tests/test_hub_inheritance.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub_inheritance import (  # noqa: E402
    TRIGRAM_LINES, HubUnresolvable, hexagram, hexagram_lines, king_wen, moving_lines, resolve,
)

PURE = {1: 29, 2: 2, 3: 51, 4: 57, 6: 1, 7: 58, 8: 52, 9: 30}


@pytest.mark.parametrize("month,expected", PURE.items())
def test_day_five_over_month_is_pure_hexagram(month, expected):
    stack = {"great_year": 2, "year": 9, "month": month, "day": 5}
    assert king_wen(hexagram_lines(stack, upper="day", lower="month")) == expected
    assert resolve(stack, "day").inherited_from == "month"


def test_chain_of_fives_resolves_to_first_non_five_parent():
    chain = {"great_year": 2, "year": 9, "month": 5, "day": 5}
    assert resolve(chain, "day").inherited_from == "year"
    assert resolve(chain, "month").inherited_from == "year"
    assert king_wen(hexagram_lines(chain, "day", "month")) == 30


def test_all_five_raises_and_ki_age_resolves_great_year():
    with pytest.raises(HubUnresolvable):
        resolve({"great_age": 5, "ki_age": 5, "great_year": 5, "year": 5}, "year")
    deep = {"ki_age": 8, "great_year": 5, "year": 5, "month": 5, "day": 5}
    assert resolve(deep, "great_year").inherited_from == "ki_age"
    assert king_wen(hexagram_lines(deep, "day", "month")) == 52


def test_five_seven_under_kun_parent_matches_old_table():
    dep = hexagram_lines({"great_year": 2, "year": 5}, "year", "great_year")
    chg = hexagram_lines({"great_year": 2, "year": 7}, "year", "great_year")
    assert king_wen(dep) == 2 and king_wen(chg) == 45
    assert moving_lines(dep, chg) == [
        {"line": 4, "from": "yin", "to": "yang"}, {"line": 5, "from": "yin", "to": "yang"}]


def test_five_seven_under_dui_parent_has_no_moving_lines():
    dep = hexagram_lines({"great_year": 7, "year": 5}, "year", "great_year")
    chg = hexagram_lines({"great_year": 7, "year": 7}, "year", "great_year")
    assert moving_lines(dep, chg) == []


def test_one_four_and_two_eight_stay_line_six_under_any_parent():
    for parent in TRIGRAM_LINES:
        for a, b in ((1, 4), (2, 8)):
            dep = hexagram_lines({"great_year": parent, "year": a}, "year", "great_year")
            chg = hexagram_lines({"great_year": parent, "year": b}, "year", "great_year")
            assert moving_lines(dep, chg) == [{"line": 6, "from": "yin", "to": "yang"}]


def test_spec_example_oct_22_2026():
    stack = {"great_year": 2, "year": 9, "month": 1, "day": 5}
    h = hexagram(stack, upper="day", lower="month")
    assert h["hexagram"] == 29
    assert h["upper"]["trigram"] == "☵ Kan (inherited from month)"
    assert h["inherited"] == [{"level": "day", "from": "month"}]
    assert hexagram({**stack, "day": 7}, "day", "month")["inherited"] == []


def test_king_wen_covers_all_64():
    assert sorted(king_wen(tuple((n >> i) & 1 for i in range(6))) for n in range(64)) == list(range(1, 65))
