"""Octave tools against the running Nine-Year Spiral app.

Run: .venv/bin/python tests/test_octave.py
"""
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


def test_reading():
    t = octave.octave_reading(29, [6], full=False)
    assert t.startswith("# 29 Danger") and "## Line 6" in t


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
