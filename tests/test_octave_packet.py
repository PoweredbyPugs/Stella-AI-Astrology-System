"""The packet: one period, its figures, condition, flow, house, point and sources.

Run: .venv/bin/python -m pytest tests/test_octave_packet.py
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import octave_ledger as L  # noqa: E402
import octave_packet as P  # noqa: E402


def test_packet_month_9_nov_2026_natal_1986():
    pk = P.packet_at("month", datetime(2026, 11, 9, 12), "1986-05-01")
    assert pk["ba"]["n"] == 36 and pk["native"]["n"] == 11 and pk["ji"] == [2]
    assert pk["point"]["question"] == L.brief(pk["number"])["q"]
    assert pk["condition"]["native"] == "Earth"             # 1986 → 5, Earth
    assert pk["flow"]["containerLevel"] == "year"
    assert pk["sources"]["ji"]["label"].startswith("what the person meets: 36 at line 2")
    assert "## Line 2" in pk["sources"]["ji"]["short"]
    assert pk["sources"]["shi"]["full"].endswith(P.book_text(pk["shi"]["ba"]["n"], [], False))
    assert pk["span"]["start"] < pk["span"]["end"]


def test_packet_top_level_has_no_flow_and_no_figure():
    pk = P.packet_at("great_age", datetime(2026, 11, 9, 12), "1986-05-01")
    assert pk["ba"] is None and pk["flow"] is None and pk["sources"]["ba"] is None
    assert pk["shi"]["to"] in range(1, 10)
    assert pk["span"]["end"] is None


def test_packet_rejects_bad_level():
    with pytest.raises(ValueError):
        P.packet("week", 0, "1986-05-01")
