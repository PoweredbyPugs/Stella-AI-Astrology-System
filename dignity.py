"""Essential dignity scoring at any ecliptic longitude, computed locally.

Sources: Lilly's point values (domicile 5, exaltation 4, triplicity 3, term 2,
face 1, detriment -5, fall -4), Dorothean triplicity rulers, Egyptian terms and
Chaldean decan faces. The scores and condition words reproduce the fields the
chart store's API returns for the seven classical planets.
"""
from ephemeris import SIGN_NAMES

POINTS = {"domicile": 5, "exaltation": 4, "triplicity": 3, "term": 2, "face": 1,
          "detriment": -5, "fall": -4}
ORDER = ["domicile", "exaltation", "triplicity", "term", "face", "detriment", "fall"]

_RULERS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
           "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
DOMICILE = dict(zip(SIGN_NAMES, _RULERS))
DETRIMENT = {s: DOMICILE[SIGN_NAMES[(i + 6) % 12]] for i, s in enumerate(SIGN_NAMES)}
EXALTATION = {"Aries": "Sun", "Taurus": "Moon", "Cancer": "Jupiter", "Virgo": "Mercury",
              "Libra": "Saturn", "Capricorn": "Mars", "Pisces": "Venus"}
FALL = {SIGN_NAMES[(SIGN_NAMES.index(s) + 6) % 12]: p for s, p in EXALTATION.items()}

TRIPLICITY = {
    "Fire": {"day": "Sun", "night": "Jupiter", "participating": "Saturn"},
    "Earth": {"day": "Venus", "night": "Moon", "participating": "Mars"},
    "Air": {"day": "Saturn", "night": "Mercury", "participating": "Jupiter"},
    "Water": {"day": "Venus", "night": "Mars", "participating": "Moon"},
}
_ELEMENTS = ["Fire", "Earth", "Air", "Water"]

TERMS = {
    "Aries": [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    "Taurus": [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    "Gemini": [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    "Cancer": [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],
    "Leo": [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],
    "Virgo": [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],
    "Libra": [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],
    "Scorpio": [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],
    "Sagittarius": [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],
    "Capricorn": [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],
    "Aquarius": [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    "Pisces": [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],
}

_CHALDEAN = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]
FACES = {s: [_CHALDEAN[(i * 3 + k) % 7] for k in range(3)] for i, s in enumerate(SIGN_NAMES)}

_DIURNAL = {"Sun", "Jupiter", "Saturn"}
_NOCTURNAL = {"Moon", "Venus", "Mars"}


def condition_word(score: int) -> str:
    if score >= 5:
        return "strong"
    if score >= 2:
        return "moderate"
    if score >= 0:
        return "neutral"
    if score >= -4:
        return "weakened"
    return "debilitated"


def _as_list(v):
    return v if isinstance(v, (list, tuple)) else [v]


def essential_dignities(planet: str, longitude: float, is_day: bool) -> dict:
    lon = longitude % 360
    idx = int(lon // 30)
    sign = SIGN_NAMES[idx]
    deg = lon - idx * 30

    tri = TRIPLICITY[_ELEMENTS[idx % 4]]
    sect_key = "day" if is_day else "night"
    tri_type = None
    for key in (sect_key, "participating"):
        if tri[key] == planet:
            tri_type = key
            break

    term_ruler = next(p for ub, p in TERMS[sign] if ub > deg)
    face_ruler = FACES[sign][min(int(deg // 10), 2)]

    held = {
        "domicile": planet in _as_list(DOMICILE[sign]),
        "exaltation": planet in _as_list(EXALTATION.get(sign, [])),
        "triplicity": tri_type is not None,
        "term": term_ruler == planet,
        "face": face_ruler == planet,
        "detriment": planet in _as_list(DETRIMENT[sign]),
        "fall": planet in _as_list(FALL.get(sign, [])),
    }
    flags = [k for k in ORDER if held[k]]
    score = sum(POINTS[k] for k in flags)
    return {
        "planet": planet, "sign": sign, "degree": round(deg, 2), "score": score,
        "condition": condition_word(score), "dignities": flags,
        "triplicity_ruler_type": tri_type, "term_ruler": term_ruler, "face_ruler": face_ruler,
    }


def sect_status(planet: str, is_day: bool) -> str:
    if planet in _DIURNAL:
        return "in sect" if is_day else "contrary to sect"
    if planet in _NOCTURNAL:
        return "contrary to sect" if is_day else "in sect"
    return "neutral"


def sect_block(is_day: bool) -> dict:
    if is_day:
        return {"label": "day", "light": "Sun", "benefic": "Jupiter", "malefic": "Saturn"}
    return {"label": "night", "light": "Moon", "benefic": "Venus", "malefic": "Mars"}
