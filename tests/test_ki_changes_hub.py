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
    # Global day 5 → 4, so the personal day rises 5 → 6: Qian over Kan = 6, lines 4 and 6 move.
    assert hx["hexagram"] == 29 and hx["transformed"]["hexagram"] == 6
    assert hx["changing"] == [{"line": 4, "direction": "yin→yang"}, {"line": 6, "direction": "yin→yang"}]


def test_next_stack_advances_every_parent_that_turns_first():
    from datetime import datetime
    now = {"great_age": 5, "ki_age": 2, "great_year": 8, "year": 2, "month": 5, "day": 1, "hour": 9}
    lichun = datetime(2034, 2, 3, 13, 40)
    times = {"hour": datetime(2033, 7, 1, 13), "day": datetime(2033, 7, 2), "month": datetime(2033, 7, 7, 4),
             "year": lichun, "synodic": lichun, "ki_age": datetime.max, "great_age": datetime.max}
    nxt = next_stack(now, "year", times)
    assert nxt["year"] == 1 and nxt["great_year"] == 7 and nxt["ki_age"] == 2
    day = next_stack(now, "day", times)
    assert day["day"] == 9 and day["month"] == 5 and day["year"] == 2
    # the month turns on Jul 7, before the day's next change on Jul 8
    times2 = {**times, "day": datetime(2033, 7, 8)}
    assert next_stack(now, "day", times2)["month"] == 4
    # sub-second disagreement between two solar-term searches still counts as the same instant
    times3 = {**times, "month": lichun.replace(microsecond=400)}
    assert next_stack(now, "month", times3)["year"] == 1


def test_year_change_at_a_gate_uses_the_new_great_year():
    d = get_ki_changes("2033-06-01")
    lc = d["level_changes"]["year"]
    assert d["global"]["current"]["synodic"] == 8 and d["global"]["next"]["synodic"] == 7
    assert lc["current"]["ki"] == 3 and lc["next"]["ki"] == 2


def test_level_change_lines_are_a_difference_of_resolved_trigrams():
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    lc = d["personal"]["level_changes"]["day"]  # 5 (Kan, inherited) → 6 (Qian)
    assert lc["current"]["inherited_from"] == "month" and lc["next"]["inherited_from"] is None
    assert lc["next"]["ki"] == 6
    assert lc["changing_lines"] == [{"line": 1, "direction": "yin→yang"}, {"line": 3, "direction": "yin→yang"}]


def test_personal_next_figures_agree_with_personal_next_numbers():
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    p = d["personal"]
    for level, nxt in p["next"].items():
        if level in p["level_changes"]:
            assert p["level_changes"][level]["next"]["ki"] == nxt, level
    g = d["global"]
    for level, nxt in g["next"].items():
        if level in d["level_changes"]:
            assert d["level_changes"][level]["next"]["ki"] == nxt, level


def test_month_turning_at_lichun_sees_the_new_year():
    # Jan 2027 → Feb 2027: the month and the year turn at the same Lichun. Year 1 → 9, month 2 → 5,
    # so the opening 5 month inherits Li from the new year, not Kan from the old one.
    d = get_ki_changes("2027-01-20")
    lc = d["level_changes"]["month"]
    assert lc["next"]["ki"] == 5 and lc["next"]["inherited_from"] == "year"
    assert lc["next"]["trigram"] == "Li (inherited from year)"
    assert d["hexagrams"]["year_month"]["transformed"]["hexagram"] == 30


def test_hour_turning_after_midnight_sees_the_new_day():
    # 23:30: the hour next turns at 01:00, the day at 00:00 before it.
    d = get_ki_changes("2026-10-22T23:30:00")
    assert d["global"]["current"]["day"] == 5
    assert next_stack(_hub(d["global"]["current"]), "hour", _instants(d))["day"] == 4


def _hub(cur):
    from ki_changes import hub_level
    return {hub_level(k): v for k, v in cur.items()}


def _instants(d):
    return d["global"]["change_instants"]
