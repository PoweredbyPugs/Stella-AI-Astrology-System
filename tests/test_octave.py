"""Octave tools, computed in Stella (no app required).

Run: .venv/bin/python -m pytest tests/test_octave.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import octave  # noqa: E402


def test_report():
    r = octave.octave_report("1986-05-01", target_date="2026-10-16")
    assert r["natal"]["triple"] == "5 · 9 · 1"
    assert (r["today"]["kiMonth"], r["today"]["personal"], r["today"]["greatYear"]) == ("Oct 2026", "9.1", 2)
    assert r["octave"]["greatYear"] == "great year 1 → 2 in 2022"
    assert [p["movingLines"] for p in r["echoPairs"]] == [[6], [2, 6], [4, 5]]
    assert sum("months" in y for y in r["years"]) == 1


def test_reading():
    t = octave.octave_reading(29, [6], full=False)
    assert t.startswith("# 29 ") and "## Line 6" in t
    assert octave.octave_reading(99).startswith("No reading for hexagram 99")


def test_no_http():
    assert not hasattr(octave, "OCTAVE_URL")
    assert "inherits the trigram" in octave.FRAMEWORK and "doubling it" not in octave.FRAMEWORK


def test_tool_rejects_other_tz():
    import stella_server
    res = asyncio.run(stella_server.mcp.call_tool("get_octave", {"birth_date": "1986-05-01", "tz": "Europe/London"}))
    assert "America/New_York" in str(res)
