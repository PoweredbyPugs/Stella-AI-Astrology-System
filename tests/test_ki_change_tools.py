"""The Ki change tools read resolved figures and step through 5 by inheritance.

Run: .venv/bin/python -m pytest tests/test_ki_change_tools.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stella_server  # noqa: E402

BIRTH = "1986-05-01"


def _pin(monkeypatch, day: str):
    import ki_changes
    real = ki_changes.get_ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: real(target_date=day, **kw))


def test_single_level_prints_inherited_tag(monkeypatch):
    _pin(monkeypatch, "2026-10-22")
    out = asyncio.run(stella_server.ki_change_day(birth_date=BIRTH))
    assert "Hexagram 29" in out or "Hex 29" in out
    assert "inherited from month" in out
    assert "Kun" not in out.split("── PERSONAL ──")[1]


def test_schedule_steps_through_five_with_inheritance(monkeypatch):
    _pin(monkeypatch, "2026-10-20")
    out = asyncio.run(stella_server.get_ki_change_schedule(birth_date=BIRTH, level="day", count=9))
    assert "Ki 5" in out and "inherits month" in out
    assert "☷" not in out.split("Ki 5")[1].split("\n")[0]


def test_schedule_steps_parents_as_they_turn(monkeypatch):
    _pin(monkeypatch, "2026-10-20")
    out = asyncio.run(stella_server.get_ki_change_schedule(level="year", count=15))
    row14 = [l for l in out.split("\n") if l.strip().startswith("14.")][0]
    assert "Ki 5 ☱ Dui (inherits great_year)" in row14, row14   # 2040: year 5 under great year 7
    out = asyncio.run(stella_server.get_ki_change_schedule(level="month", count=9))
    feb = [l for l in out.split("\n") if "Ki 5" in l and "→ Ki 5" in l][0]
    assert "Ki 5 ☲ Li (inherits year)" in feb, feb              # Feb 2027: month 5 under year 9


def test_tools_surface_hub_error(monkeypatch):
    import ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: {"error": "day is 5 and every parent above it is 5"})
    out = asyncio.run(stella_server.ki_change_day(birth_date=BIRTH))
    assert out.startswith("Ki stack unresolvable:")
    out2 = asyncio.run(stella_server.get_ki_change_schedule(birth_date=BIRTH, level="day"))
    assert out2.startswith("Ki stack unresolvable:")
