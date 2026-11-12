"""The ZR MCP tools: snapshot, report and periods over a window.

Run: .venv/bin/python -m pytest tests/test_zr_tools.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stella_server  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def test_get_zr_periods_lists_every_period_in_the_window():
    out = json.loads(run(stella_server.get_zr_periods(
        name="lisa", lot="fortune", start="2020-01-01", end="2030-01-01", levels="1,2")))
    assert out["lot"] == "fortune" and set(out["periods"]) == {"L1", "L2"}
    l2 = out["periods"]["L2"]
    assert l2, "no L2 periods in a ten-year window"
    for a, b in zip(l2, l2[1:]):
        assert a["end"] == b["start"]
    for key in ("sign", "start", "end", "ruler", "phase", "peak_type", "is_loosing_of_bond", "is_pre_loosing"):
        assert key in l2[0], key
    assert l2[0]["start"] <= "2020-01-01" and l2[-1]["end"] >= "2030-01-01"


def test_get_zr_periods_rejects_a_backwards_window():
    out = json.loads(run(stella_server.get_zr_periods(name="lisa", start="2030-01-01", end="2020-01-01")))
    assert "error" in out


def test_get_zr_report_takes_lot_and_format():
    md = run(stella_server.get_zr_report(name="lisa", lot="fortune", date="2026-11-11"))
    assert "Releasing from: **Fortune**" in md
    data = json.loads(run(stella_server.get_zr_report(name="lisa", lot="spirit", date="2026-11-11", format="json")))
    assert data["lot"] == "spirit" and "L1" in data["periods"]


def test_get_zodiacal_releasing_exposes_loosing_fields():
    out = json.loads(run(stella_server.get_zodiacal_releasing(name="lisa", lot="spirit", date="2026-11-11")))
    l1 = out[0]["data"]["L1"]
    for key in ("loosing_at", "is_loosing_of_bond", "is_pre_loosing", "phase", "house_from_fortune"):
        assert key in l1, key
