"""Doubling rule for Ki 5 in hexagram formation (get_ki_transition path).

Spec: if one digit is 5 it takes the other digit's trigram; only 5 over 5
has no figure. Li over Li = 30, Zhen over Zhen = 51.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ki_reading import get_hexagram_lines, ki_to_hexagram  # noqa: E402


def test_five_lower_takes_upper_trigram():
    assert ki_to_hexagram(5, 3) == ki_to_hexagram(3, 3) == 51  # Zhen doubled


def test_five_upper_takes_lower_trigram():
    assert ki_to_hexagram(9, 5) == ki_to_hexagram(9, 9) == 30  # Li doubled


def test_five_over_five_has_no_figure():
    assert ki_to_hexagram(5, 5) is None


def test_hexagram_lines_follow_doubling_rule():
    # The lines must agree with the figure ki_to_hexagram produces.
    assert get_hexagram_lines(5, 3) == get_hexagram_lines(3, 3)
    assert get_hexagram_lines(9, 5) == get_hexagram_lines(9, 9)
    assert get_hexagram_lines(5, 5) is None


def test_five_over_five_renders_no_figure_not_none():
    import stella_server

    # birth 1986-05-01 at 2022-08-15: personal year 5, personal month 5
    out = asyncio.run(stella_server.get_ki_transition(
        birth_date="1986-05-01", target_date="2022-08-15"))
    assert "Hexagram None" not in out, out
    assert "no figure (5 over 5)" in out, out


def test_transition_tool_renders_hexagram_for_five():
    import stella_server

    out1 = asyncio.run(stella_server.get_ki_transition(
        birth_date="1986-05-01", target_date="2022-06-15"))
    assert "Hexagram 51" in out1, out1  # personal year 5, month 3 → Zhen doubled
    assert "Hexagram None" not in out1, out1

    out2 = asyncio.run(stella_server.get_ki_transition(
        birth_date="1986-05-01", target_date="2026-05-15"))
    assert "Hexagram 30" in out2, out2  # personal year 9, month 5 → Li doubled
    assert "Hexagram None" not in out2, out2
