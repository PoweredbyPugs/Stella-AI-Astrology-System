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
    assert (r["today"]["kiMonth"], r["today"]["personal"], r["today"]["greatYear"]) == ("Oct 2026", "9.1", 9)
    assert r["octave"]["greatYear"] == "great year 8 → 9 in 2022"
    assert [p["movingLines"] for p in r["echoPairs"]] == [[6], [1, 6], [5, 6]]
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


def test_framework_v2_carries_the_lenses_and_rules():
    f = octave.FRAMEWORK
    for s in ("Ba (場)", "Shi (勢)", "Ji (機)", "resonates", "fed by", "Five Yellow", "What's under the surface?", "nourish", "tends everything", "Tri-force", "Jev decides and grades; Jev never writes", "get_octave_period", "write_octave_statement"):
        assert s in f, s
    assert "version: 2.0.0" in octave.hermes_skill()


def test_ledger_resource_registered():
    import stella_server
    names = {str(r.uri) for r in asyncio.run(stella_server.mcp.list_resources())}
    assert "octave://ledger" in names
