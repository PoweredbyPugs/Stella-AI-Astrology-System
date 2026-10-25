"""The daily cascade carries the great year, Ki Age and great age, and names what a 5 inherits.

Run: .venv/bin/python -m pytest tests/test_daily_ki_hub.py
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ki import calculate_daily_ki  # noqa: E402
import stella_server  # noqa: E402


def test_stack_has_upper_levels_and_hub_tags():
    # Oct 23 2026 (noon): global day 5 under month 9, so the personal day is 5 under personal month 1
    r = calculate_daily_ki(date(1986, 5, 1), date(2026, 10, 23))
    g, p = r["global"], r["personal"]
    assert (g["great_age"]["ki"], g["ki_age"]["ki"], g["great_year"]["ki"], g["year"]["ki"]) == (8, 5, 1, 1)
    assert (p["great_year"]["ki"], p["year"]["ki"], p["month"]["ki"], p["day"]["ki"]) == (9, 9, 1, 5)
    assert p["day"]["hub"] == {"trigram": "☵ Kan (inherited from month)", "inherited_from": "month"}
    assert p["month"]["hub"]["inherited_from"] is None
    assert g["great_age"]["hub"] == {"trigram": "☶ Gen", "inherited_from": None}
    assert p["great_age"]["hub"] == {"trigram": "☷ Kun", "inherited_from": None}
    assert r["sequences"]["personal"].count(".") == 6


def test_tool_prints_inheritance():
    out = asyncio.run(stella_server.get_daily_ki("1986-05-01", "2026-10-23"))
    assert "**Ki Age:**" in out and "**Great Age:**" in out
    assert "inherits ☵ Kan from month" in out
