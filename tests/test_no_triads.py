"""The Ki outputs carry numbers and trigrams, not the Man/Earth/Heaven triad labels.

Run: .venv/bin/python -m pytest tests/test_no_triads.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convergence_ki import get_convergence_ki, get_synodic_gate  # noqa: E402
import stella_server  # noqa: E402


def test_convergence_payload_has_no_triads():
    r = get_convergence_ki("2026-10-20", birth_date="1986-05-01")
    text = json.dumps(r)
    assert "triad" not in text.lower()
    assert "(Man)" not in text and "(Heaven)" not in text and "(Earth)" not in text
    # the hour follows the clock at run time, so only the levels above it are pinned
    assert r["summary"].startswith("Synodic 8 · Year 1 · Month 9 · Day 7 · Hour ")
    assert r["personal"]["summary"].startswith("Personal: Synodic 2 · Year 9 · Month 1 · Day 3 · Hour ")


def test_synodic_gate_has_no_triads():
    assert "triad" not in json.dumps(get_synodic_gate("2026-10-20", birth_date="1986-05-01")).lower()


def test_ki_change_text_has_no_triads(monkeypatch):
    import ki_changes
    real = ki_changes.get_ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: real(target_date="2026-10-20", **kw))
    out = asyncio.run(stella_server.ki_change_day(birth_date="1986-05-01"))
    assert "(Man)" not in out and "(Heaven)" not in out and "(Earth)" not in out
    assert "Current: 7 ☱ Dui" in out
