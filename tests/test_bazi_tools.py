"""The three BaZi MCP tools: natal, luck pillars, time pillars.

Run: .venv/bin/python -m pytest tests/test_bazi_tools.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stella_server  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def test_get_bazi_betsy_markdown():
    out = run(stella_server.get_bazi(name="betsy"))
    for s in ("戊午", "癸亥", "丙戌", "己亥", "Day Master", "true solar time", "七殺格", "天乙貴人", "壬戌"):
        assert s in out, s
    assert "Luck Pillars" in out and "backward" in out


def test_get_bazi_json():
    d = json.loads(run(stella_server.get_bazi(name="betsy", format="json")))
    assert d["pillars"]["day"]["cn"] == "丙戌"
    assert d["analysis"]["structure"]["name"] == "七殺格"
    assert d["luck"]["direction"] == "backward"
    assert d["settings"] == {"true_solar_time": True, "day_boundary": "23:00"}


def test_get_bazi_raw_birth_data():
    out = run(stella_server.get_bazi(birth_datetime="1986-05-01T14:35", lat=28.5383, lon=-81.3792,
                                     timezone="America/New_York", gender="male"))
    assert "丙寅" in out and "乙巳" in out and "癸巳" in out


def test_get_bazi_no_gender_omits_luck_with_reason():
    out = run(stella_server.get_bazi(name="kate"))      # older shape, no gender
    assert "luck pillars omitted" in out.lower() and "gender" in out.lower()
    assert "Luck Pillars" not in out or "omitted" in out


def test_get_bazi_gender_override_restores_luck():
    out = run(stella_server.get_bazi(name="kate", gender="female"))
    assert "omitted" not in out.lower() and "Luck Pillars" in out


def test_get_bazi_no_coordinates_warns_first():
    out = run(stella_server.get_bazi(name="kelsea"))
    first = out.strip().splitlines()[0].lower()
    assert first.startswith("> warning") and "clock time" in first


def test_get_bazi_clock_time_option():
    out = run(stella_server.get_bazi(name="betsy", true_solar_time=False))
    assert "clock time" in out and "true solar time: off" in out.lower()


def test_get_bazi_unknown_chart():
    out = run(stella_server.get_bazi(name="nobody-here"))
    assert "not found" in out.lower()


def test_luck_pillars_tool():
    out = run(stella_server.get_bazi_luck_pillars(name="chris"))
    assert "forward" in out and "癸巳" in out and "丙申" in out


def test_time_pillars_tool_default_now():
    out = run(stella_server.get_bazi_time_pillars())
    assert "Year" in out and "Hour" in out


def test_time_pillars_tool_against_natal():
    out = run(stella_server.get_bazi_time_pillars(target="2026-11-11T12:00", name="betsy"))
    assert "丙午" in out and "比肩" in out and "自刑" in out
    d = json.loads(run(stella_server.get_bazi_time_pillars(target="2026-11-11T12:00", name="betsy", format="json")))
    assert d["pillars"]["day"]["cn"] == "己丑" and d["luck"]["cn"]
