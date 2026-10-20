"""Ki changes form every figure from the full stack with hub inheritance.

Run: .venv/bin/python -m pytest tests/test_ki_changes_hub.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ki_changes import KI_TO_TRIGRAM, get_ki_changes, next_stack  # noqa: E402

BIRTH = "1986-05-01"


def test_five_is_not_kun():
    assert 5 not in KI_TO_TRIGRAM


def test_personal_five_inherits_up_the_personal_chain():
    d = get_ki_changes("2022-06-15", birth_date=BIRTH)
    p = d["personal"]
    assert p["current"]["year"] == 5 and p["current"]["synodic"] == 2
    hx = p["hexagrams"]["year_month"]
    assert hx["lower"]["trigram"] == "☷ Kun (inherited from great_year)"
    assert hx["inherited"] == [{"level": "year", "from": "great_year"}]
    assert d["global"]["current"]["ki_age"] == 2 and d["global"]["current"]["great_age"] == 5
    assert p["current"]["ki_age"] == 8


def test_day_five_over_month_is_pure():
    # Oct 22 2026: Chris personal month 1, personal day 5 (spec example)
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    hx = d["personal"]["hexagrams"]["month_day"]
    assert d["personal"]["current"]["day"] == 5
    # Next day is 4 (Xun) over the same month: 59; the 5↔7 echo (47) is a pair, not a next figure.
    assert hx["hexagram"] == 29 and hx["transformed"]["hexagram"] == 59
    assert hx["changing"] == [{"line": 6, "direction": "yin→yang"}]


def test_next_stack_advances_parents_only_at_a_shared_gate():
    now = {"great_age": 5, "ki_age": 2, "great_year": 8, "year": 2, "month": 5, "day": 1, "hour": 9}
    times = {"year": "L2034", "synodic": "L2034", "ki_age": "L2166", "great_age": "L3318"}
    nxt = next_stack(now, "year", times)
    assert nxt["year"] == 1 and nxt["great_year"] == 7 and nxt["ki_age"] == 2
    assert next_stack(now, "day", times)["day"] == 9 and next_stack(now, "day", times)["month"] == 5


def test_year_change_at_a_gate_uses_the_new_great_year():
    d = get_ki_changes("2033-06-01")
    lc = d["level_changes"]["year"]
    assert d["global"]["current"]["synodic"] == 8 and d["global"]["next"]["synodic"] == 7
    assert lc["current"]["ki"] == 3 and lc["next"]["ki"] == 2


def test_level_change_lines_are_a_difference_of_resolved_trigrams():
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    lc = d["personal"]["level_changes"]["day"]  # 5 (Kan, inherited) → 4 (Xun)
    assert lc["current"]["inherited_from"] == "month" and lc["next"]["inherited_from"] is None
    assert lc["changing_lines"] == [{"line": 3, "direction": "yin→yang"}]
