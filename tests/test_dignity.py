import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dignity import essential_dignities, condition_word, sect_status, sect_block

FIX = json.load(open(Path(__file__).parent / "fixtures" / "skyki_hour_chris.json"))
SIGN_START = {"Aries": 0, "Taurus": 30, "Gemini": 60, "Cancer": 90, "Leo": 120, "Virgo": 150,
              "Libra": 180, "Scorpio": 210, "Sagittarius": 240, "Capricorn": 270, "Aquarius": 300, "Pisces": 330}

def test_fixture_planets_score_as_the_handoff_says():
    for p in FIX["moment"]["planets"]:
        d = essential_dignities(p["planet"], SIGN_START[p["sign"]] + p["degree"], is_day=False)
        assert (d["score"], d["condition"], d["dignities"]) == (p["score"], p["condition"], p["dignities"]), p["planet"]

def test_fixture_sect_status_at_night():
    for p in FIX["moment"]["planets"]:
        assert sect_status(p["planet"], is_day=False) == p["sect"], p["planet"]

def test_chris_natal_matches_the_stored_api_dignities():
    chart = json.load(open(Path(__file__).parent.parent / "charts" / "chris.json"))
    for pl in chart["planets"]:
        if pl["name"] not in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            continue
        d = essential_dignities(pl["name"], float(pl["longitude"]), is_day=chart["sect"]["isDaySect"])
        s = pl["dignities"]
        assert d["score"] == s["score"], pl["name"]
        assert d["condition"] == s["condition"], pl["name"]
        assert ("domicile" in d["dignities"]) == s["domicile"], pl["name"]
        assert ("exaltation" in d["dignities"]) == s["exaltation"], pl["name"]
        assert ("triplicity" in d["dignities"]) == s["triplicity"]["isTriplicityRuler"], pl["name"]
        assert ("term" in d["dignities"]) == s["term"]["isInOwnTerm"], pl["name"]
        assert ("face" in d["dignities"]) == s["face"]["isInOwnFace"], pl["name"]
        assert ("detriment" in d["dignities"]) == s["detriment"], pl["name"]
        assert ("fall" in d["dignities"]) == s["fall"], pl["name"]

def test_condition_words():
    assert [condition_word(s) for s in (7, 5, 4, 2, 1, 0, -1, -4, -5, -9)] == \
        ["strong", "strong", "moderate", "moderate", "neutral", "neutral", "weakened", "weakened", "debilitated", "debilitated"]

def test_term_boundary_is_half_open():
    assert essential_dignities("Venus", 6.0, True)["term_ruler"] == "Venus"      # Aries 6°00' opens Venus's term
    assert essential_dignities("Jupiter", 5.999, True)["term_ruler"] == "Jupiter"

def test_participating_triplicity_counts_in_both_sects():
    assert "triplicity" in essential_dignities("Saturn", 8.57, True)["dignities"]
    assert essential_dignities("Saturn", 8.57, False)["triplicity_ruler_type"] == "participating"

def test_sect_blocks():
    assert sect_block(True) == {"label": "day", "light": "Sun", "benefic": "Jupiter", "malefic": "Saturn"}
    assert sect_block(False) == {"label": "night", "light": "Moon", "benefic": "Venus", "malefic": "Mars"}


def test_longitude_a_hair_below_zero_is_aries():
    assert essential_dignities("Sun", -1e-15, True)["sign"] == "Aries"
