"""The Octave ledger dump: text tables exported from the page's ledger.js and briefs.js.

Run: .venv/bin/python -m pytest tests/test_octave_ledger.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
ROOT = Path(__file__).resolve().parent.parent


def test_ledger_json_has_every_table():
    d = json.load(open(ROOT / "data" / "octave_ledger.json"))
    for k in ("BRIEF", "CONDITION", "COND_CLAUSE", "HOUSES", "RELATION_WORD", "FLOW_WORD", "PAIRS", "VERB", "TENDING", "STAR", "LPOINTS", "LLINKS"):
        assert k in d, k
    assert d["BRIEF"]["2"]["q"] == "What is being received?"
    assert d["BRIEF"]["6"]["q"] == "What was the ego magnetic to?"          # the briefs override, not the ledger's pin
    assert d["CONDITION"]["Earth"]["Earth"].startswith("Earth on earth. Weight and stillness.")
    assert d["COND_CLAUSE"]["Earth"]["Wood"] == "with roots drawing on you"
    assert d["VERB"] == {"1>4": "nourish", "4>2": "break", "2>8": "inherit", "8>5": "keep", "5>7": "reflect", "7>1": "shape"}
    assert d["TENDING"]["5"]["scale"] == "self"
    assert d["HOUSES"]["8"]["dir"] == "North-east"
    assert d["STAR"]["5"] == "Yellow Earth"


import octave_ledger as L  # noqa: E402


def test_statement_appends_the_condition_clause():
    rel = {"cond": "controlled_by", "ne": "Earth", "pe": "Wood"}
    assert L.statement("What is being received?", rel) == "What is being received, with roots drawing on you?"
    assert L.statement("What is being received?", None) == "What is being received?"


def test_trad_and_its_key():
    rel = {"cond": "resonates", "ne": "Earth", "pe": "Earth"}
    assert L.trad(rel, "hour") == "Your earth in an earth hour. Weight and stillness. Nothing cuts, nothing pushes; the risk is Stagnation. Do not grasp."
    assert L.trad_key(rel, "hour") == "Your earth in an earth hour."
    rel2 = {"cond": "controlled_by", "ne": "Earth", "pe": "Wood"}
    assert L.trad(rel2, "day").startswith("Your earth in a wood day: roots in the soil.")


def test_pair_and_brief():
    assert L.pair(8, 5)["verb"] == "keep" and L.pair(8, 5)["kind"] == "octave trace"
    assert L.pair(1, 4)["kind"] == "interval trace"
    assert L.brief(5)["q"] == "What landed here from above?"
    assert L.tending(2)["scale"] == "all" and L.tending(3) is None
    assert L.house(1)["dir"] == "North" and L.star(9) == "Purple Fire"
