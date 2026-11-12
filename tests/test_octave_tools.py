"""The seven deterministic Octave tools.

Run: .venv/bin/python -m pytest tests/test_octave_tools.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stella_server  # noqa: E402

run = asyncio.run


def test_get_octave_period_natal():
    d = json.loads(run(stella_server.get_octave_period(level="month", datetime="2026-11-09T12:00", natal="1986-05-01")))
    assert d["ba"]["n"] == 36 and d["ji"] == [2] and "sources" in d
    assert d["palace"]["global"] == d["global"]


def test_get_octave_period_global_has_palace_and_no_ji():
    d = json.loads(run(stella_server.get_octave_period(level="year", datetime="2026-06-01T12:00")))
    assert d["global"] == 1 and d["palace"]["five_yellow"] == 9 and "ji" not in d
    for k in ("number", "span", "ba", "shi", "house", "point"):
        assert k in d


def test_get_octave_condition_names_whose_element():
    d = json.loads(run(stella_server.get_octave_condition(natal="1986-05-01", level="hour", datetime="2026-11-11T12:22")))
    assert d["trad"].startswith("Your earth in ") and d["trad_key"].endswith(".")
    assert d["statement"].endswith("?")
    assert d["condition"]["relation"] in ("resonates", "fed_by", "feeds", "controls", "controlled_by")


def test_get_octave_point_and_line():
    p = json.loads(run(stella_server.get_octave_point(number=3)))
    assert p["name"] == "Power" and p["force"]["n"] == 51
    l = json.loads(run(stella_server.get_octave_line(from_number=7, to_number=1)))
    assert l["verb"] == "shape" and l["figure"]["n"] == 60 and l["kind"] == "octave trace"


def test_get_palace_month_8():
    d = json.loads(run(stella_server.get_palace(level="month", datetime="2026-02-10T12:00", natal="1986-05-01")))
    assert d["five_yellow"] == 2 and d["star"]
    assert d["house"]["number"]


def test_native_figure_and_shi():
    n = json.loads(run(stella_server.get_native_figure(natal="1986-05-01", level="month", datetime="2026-11-09T12:00")))
    assert n["ba"]["n"] == 36 and n["ji"] == [2] and n["native"] and n["text"]
    s = json.loads(run(stella_server.get_octave_shi(level="month", datetime="2026-11-09T12:00", natal="1986-05-01")))
    assert s["ba"]["n"] == 36 and "to" in s["shi"] and "next" in s


def test_line_with_a_five_needs_a_datetime():
    assert "error" in json.loads(run(stella_server.get_octave_line(from_number=5, to_number=7)))
    assert "error" in json.loads(run(stella_server.get_octave_line(from_number=1, to_number=2)))
    d = json.loads(run(stella_server.get_octave_line(from_number=5, to_number=7, datetime="2026-11-09T12:00")))
    assert d["figure"]


def test_tools_report_bad_input_as_error():
    assert "error" in json.loads(run(stella_server.get_octave_period(level="week")))
    assert "error" in json.loads(run(stella_server.get_octave_period(level="year", idx=-3000)))


def _no_key_call(monkeypatch, tool, **kw):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    raw = run(tool(natal="1986-05-01", level="month", datetime="2026-11-09T12:00", **kw))
    return json.loads(raw)


def test_write_octave_statement_without_keys_says_so(monkeypatch):
    d = _no_key_call(monkeypatch, stella_server.write_octave_statement)
    assert d["ok"] is False and d["error"] == "no_key" and "system" not in d


def test_write_octave_forecast_without_keys_says_so(monkeypatch):
    d = _no_key_call(monkeypatch, stella_server.write_octave_forecast, fresh=True)
    assert d["ok"] is False and d["error"] == "no_key" and "system" not in d


def test_explain_tool_passes_through_404(monkeypatch):
    d = _no_key_call(monkeypatch, stella_server.explain_octave_statement)
    assert d["ok"] is False and "system" not in d


def test_synodic_gate_matches_the_live_stack():
    d = json.loads(run(stella_server.get_synodic_gate_now(target_date="2026-11-11")))
    assert d["synodic_gate"]["ki"] == 1
    assert str(d["gate_boundary"]["lichun_date"]).startswith("2022")
    assert d["next_gate"]["ki"] == 9
    doc = stella_server.get_synodic_gate_now.__doc__
    assert "gate 8" not in doc and "2010" in doc and "2022" in doc
