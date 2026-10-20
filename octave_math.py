"""octave_math — Nine Star Ki octaves on Gurdjieff's enneagram, computed in Stella.

A Python port of the Nine-Year Spiral library (lib/ki, lib/enneagram, lib/iching/form,
lib/report, lib/summary). Every period is read as an I Ching figure formed over the cycle
that contains it: year over great year, month over year. Ki 5 has no trigram and inherits
the nearest level above it that is not 5 (hub_inheritance), so a 5 year forms over its
great year's trigram and a 5 month in a 5 year is that trigram doubled. There is no
"no figure" case.

Output keys are the app's camelCase so the JSON shape is unchanged for readers of
get_octave; `inherited` is added to every figure.
"""

from datetime import date
from typing import Optional

from hub_inheritance import hexagram as _hexagram, moving_lines
from ki_calendar import MONTH_NAMES, ki_month_label, ki_month_of, ki_month_span, ki_year_of
from ki_levels import (
    global_great_year, global_month, global_year, global_stack, personal, personal_stack,
)

HEX_NAMES = [
    "", "The Creative", "The Receptive", "Difficulty at the Beginning", "Youthful Folly", "Waiting", "Conflict",
    "The Army", "Holding Together", "Small Taming", "Treading", "Peace", "Standstill", "Fellowship", "Great Possession",
    "Modesty", "Enthusiasm", "Following", "Work on the Decayed", "Approach", "Contemplation", "Biting Through", "Grace",
    "Splitting Apart", "Return", "Innocence", "Great Taming", "Nourishment", "Great Exceeding", "The Abysmal",
    "The Clinging", "Influence", "Duration", "Retreat", "Great Power", "Progress", "Darkening of the Light", "The Family",
    "Opposition", "Obstruction", "Deliverance", "Decrease", "Increase", "Breakthrough", "Coming to Meet", "Gathering",
    "Pushing Upward", "Oppression", "The Well", "Revolution", "The Cauldron", "The Arousing", "Keeping Still",
    "Development", "Marrying Maiden", "Abundance", "The Wanderer", "The Gentle", "The Joyous", "Dispersion", "Limitation",
    "Inner Truth", "Small Exceeding", "After Completion", "Before Completion",
]

# ── Trigram names and images (Later Heaven); 5 is the centre ──
_KI_NAME = {1: "Kan", 2: "Kun", 3: "Zhen", 4: "Sun", 5: "Centre", 6: "Qian", 7: "Dui", 8: "Gen", 9: "Li"}
_KI_IMAGE = {1: "water", 2: "earth", 3: "thunder", 4: "wind", 5: "centre", 6: "heaven", 7: "lake", 8: "mountain", 9: "fire"}


def ki_name(k: int) -> str:
    return _KI_NAME[k]


def ki_image(k: int) -> str:
    return _KI_IMAGE[k]


# ── Enneagram rim ──
ECHO = {1: 4, 4: 1, 2: 8, 8: 2, 5: 7, 7: 5}
HEXAGON = [1, 4, 2, 8, 5, 7, 1]


def rim_role(k: int) -> str:
    if k == 3:
        return "shock-given"
    if k == 6:
        return "shock-made"
    if k == 9:
        return "source"
    return "echo"


def echo_partner(k: int) -> Optional[int]:
    return ECHO.get(k)


def rim_label(k: int, partners: Optional[list] = None) -> str:
    """'Shock 3 · given', 'Shock 6 · to be made', 'Source and arrival · 9', or '1 ↔ 4' (+ partners)."""
    role = rim_role(k)
    if role == "shock-given":
        return "Shock 3 · given"
    if role == "shock-made":
        return "Shock 6 · to be made"
    if role == "source":
        return "Source and arrival · 9"
    p = ECHO[k]
    pair = f"{min(k, p)} ↔ {max(k, p)}"
    return f"{pair} · with {', '.join(partners)}" if partners else pair


_IMAGE_TEXT = {
    1: "Water takes the form of whatever holds it.",
    2: "Earth receives.",
    3: "Thunder from below.",
    4: "Wind penetrates; what was begun gets worked through in practice.",
    5: "The centre holds everything in reserve.",
    6: "Heaven from above, into settled ground.",
    7: "Lake releases. Expression, loosening, pleasure.",
    8: "Mountain. Stillness before the return.",
    9: "Fire. Source and arrival.",
}


def rim_text(k: int, partner_year: Optional[int] = None) -> str:
    """Rim text for a personal year k; partner_year is its echo partner's Ki year in the same octave."""
    I = _IMAGE_TEXT
    return {
        1: f"Opening of the cycle. {I[1]} The question posed here is the one {partner_year} tested.",
        2: f"{I[2]} The hesitation of this year is what {partner_year} carried home.",
        3: f"First shock, given. {I[3]} The year did not need to be chosen.",
        4: f"The question of {partner_year}, tested. {I[4]}",
        5: f"The centre. {I[5]} What is held here, {partner_year} releases.",
        6: f"Second shock, to be made. {I[6]} The hard one.",
        7: f"Lake releases what the centre held in {partner_year}. Expression, loosening, pleasure.",
        8: f"{I[8]} The refusal of {partner_year} returns to be settled.",
    }.get(k, f"{I[9]} Not a strike, but where the two strikes came from and where they land.")


PAIR_TEXT = {
    1: lambda a, b: {
        "title": "The same question, posed then tested.",
        "body": f"What began in the Water year set the terms of what the Wind year had to carry out. The incompleteness of {a} was the material of {b}.",
    },
    2: lambda a, b: {
        "title": "The same hesitation, early then late.",
        "body": f"What was refused or left waiting in the Earth year of {a} is what came home to be settled in the Mountain year of {b}. The last stage before the return.",
    },
    5: lambda a, b: {
        "title": "The same ripening, held then released.",
        "body": f"The 5 year is the centre: everything held. The Lake year of {b} is where what {a} kept was let out.",
    },
}

SHOCK_TEXT = {
    3: {
        "title": "The given shock",
        "body": "One-third in. Usually arrives from outside: a hand, a resource, an event. Thunder is the seed cracking from below. The year did not need to be chosen.",
    },
    6: {
        "title": "The shock that must be made",
        "body": "Two-thirds in. Pure yang entering where the ground is most settled. Could not be supplied by the wiring. Ask of this year: was the strike made, or pushed through? That decides whether the figure below is a loop or a spiral.",
    },
    9: {
        "title": "Source and arrival",
        "body": "Fire is the seeing, not a stage of the seen. Not a strike, but where the two strikes came from and where they land.",
    },
}


# ── Natal and octaves ──
def natal(birth: date) -> dict:
    """Natal triple year.month.third for a birth date. 1986-05-01 → 5.9.1."""
    ki_year, index = ki_month_of(birth)
    month_abs = ki_year * 12 + index
    year = global_year(ki_year)
    month = global_month(month_abs)
    return {"year": year, "month": month, "third": personal(year, month), "kiYear": ki_year, "monthAbs": month_abs}


def natal_label(n: dict) -> str:
    return f"{n['year']} · {n['month']} · {n['third']}"


def personal_year(natal_year: int, ki_year: int) -> int:
    return personal(natal_year, global_year(ki_year))


def personal_great_year(natal_year: int, ki_year: int) -> int:
    return personal(natal_year, global_great_year(ki_year))


def octaves(natal_year: int, birth_ki_year: int, until_age: int = 90) -> list:
    """Nine-year octaves from the one the native was born into (index 0) to until_age."""
    start0 = birth_ki_year - (personal_year(natal_year, birth_ki_year) - 1)
    out = []
    i, s = 0, start0
    while s <= birth_ki_year + until_age:
        great_years = []
        for y in range(s, s + 9):
            g = global_great_year(y)
            if not great_years or great_years[-1]["global"] != g:
                great_years.append({"from": y, "global": g, "personal": personal_great_year(natal_year, y)})
        o = {"index": i, "start": s, "end": s + 8, "greatYears": great_years}
        if i == 0:
            o["enteredAt"] = personal_year(natal_year, birth_ki_year)
        out.append(o)
        i, s = i + 1, s + 9
    return out


def octave_containing(lst: list, ki_year: int) -> Optional[dict]:
    return next((o for o in lst if o["start"] <= ki_year <= o["end"]), None)


def great_year_label(o: dict) -> str:
    """'great year 2' or 'great year 1 → 2 in 2022' (personal numbers)."""
    first, *rest = o["greatYears"]
    if not rest:
        return f"great year {first['personal']}"
    return (f"great year {' → '.join(str(g['personal']) for g in [first, *rest])}"
            f" in {', '.join(str(g['from']) for g in rest)}")


def octave_label(o: dict) -> str:
    return f"Octave {o['index']} · Feb {o['start']} → Jan {o['end'] + 1}"


# ── Figures ──
def figure(stack: dict, upper: str, lower: str) -> dict:
    """A period's figure: its own trigram over the trigram of the cycle containing it."""
    h = _hexagram(stack, upper=upper, lower=lower)
    return {
        "number": h["hexagram"],
        "name": HEX_NAMES[h["hexagram"]],
        "lines": "".join(str(b) for b in h["lines"]),
        "upperKi": stack[upper],
        "lowerKi": stack[lower],
        "upper": h["upper"]["pinyin"],
        "lower": h["lower"]["pinyin"],
        "inherited": h["inherited"],
    }


def change(primary: dict, transformed: dict) -> dict:
    """The earlier period's figure is primary; the moving lines are exactly where the two differ."""
    moving = [m["line"] for m in moving_lines(tuple(int(c) for c in primary["lines"]),
                                              tuple(int(c) for c in transformed["lines"]))]
    return {"primary": primary, "transformed": transformed, "moving": moving,
            "lowerMoved": any(l <= 3 for l in moving)}


def _year_stack(natal_year: int, ki_year: int, index: Optional[int] = None) -> dict:
    abs_month = ki_year * 12 + index if index is not None else None
    return personal_stack(natal_year, global_stack(ki_year, abs_month))


def year_figure(natal_year: int, ki_year: int) -> dict:
    return figure(_year_stack(natal_year, ki_year), upper="year", lower="great_year")


def month_figure(natal_year: int, ki_year: int, index: int) -> dict:
    return figure(_year_stack(natal_year, ki_year, index), upper="month", lower="year")


# ── Report ──
def _month_cell(natal_year: int, ki_year: int, index: int, birth_abs: int, now_abs: int) -> dict:
    abs_month = ki_year * 12 + index
    stack = _year_stack(natal_year, ki_year, index)
    py, pm = stack["year"], stack["month"]
    partner = echo_partner(pm)
    partners = None
    if partner:
        partners = [ki_month_label(ki_year, i) for i in range(12)
                    if personal(natal_year, global_month(ki_year * 12 + i)) == partner]
    first, last = ki_month_span(ki_year, index)
    return {
        "abs": abs_month, "kiYear": ki_year, "index": index, "label": ki_month_label(ki_year, index),
        "firstDay": first.isoformat(), "lastDay": last.isoformat(),
        "py": py, "pm": pm, "figure": figure(stack, upper="month", lower="year"),
        "role": rim_role(pm), "position": rim_label(pm, partners),
        "isNow": abs_month == now_abs, "beforeBirth": abs_month < birth_abs, "echoes": [],
    }


def _link_echoes(months: list) -> None:
    for m in months:
        p = echo_partner(m["pm"])
        if not p:
            continue
        m["echoes"] = [
            {"label": o["label"],
             "change": change(o["figure"], m["figure"]) if o["abs"] < m["abs"] else change(m["figure"], o["figure"])}
            for o in months if o["pm"] == p
        ]


def _fig(f: dict) -> dict:
    return {
        "number": f["number"], "name": f["name"],
        "upper": f"{f['upperKi']} {ki_name(f['upperKi'])} ({ki_image(f['upperKi'])})",
        "lower": f"{f['lowerKi']} {ki_name(f['lowerKi'])} ({ki_image(f['lowerKi'])})",
        "lines": f["lines"], "inherited": f["inherited"],
    }


def build_report(birth: date, octave_index: Optional[int], today: date, name: Optional[str] = None) -> dict:
    """The octave report summary: natal, today's position, the octave's years and months with
    their figures, echo pairs with moving lines, shocks and the next cycle."""
    nat = natal(birth)
    n = nat["year"]
    octs = octaves(n, nat["kiYear"])
    now_year, now_index = ki_month_of(today)
    now_abs = now_year * 12 + now_index
    today_octave = octave_containing(octs, ki_year_of(today))
    octave = next((o for o in octs if o["index"] == octave_index), None) or today_octave or octs[0]

    years_by_py = {personal_year(n, Y): Y for Y in range(octave["start"], octave["end"] + 1)}
    years = []
    for Y in range(octave["start"], octave["end"] + 1):
        py = personal_year(n, Y)
        partner = echo_partner(py)
        partner_year = years_by_py.get(partner) if partner else None
        months = [_month_cell(n, Y, i, nat["monthAbs"], now_abs) for i in range(12)]
        _link_echoes(months)
        years.append({
            "kiYear": Y, "py": py, "gy": personal_great_year(n, Y), "gyGlobal": global_great_year(Y),
            "figure": year_figure(n, Y), "role": rim_role(py), "partner": partner, "partnerYear": partner_year,
            "text": rim_text(py, partner_year), "toNext": change(year_figure(n, Y), year_figure(n, Y + 1)),
            "months": months, "isNow": Y == now_year, "beforeBirth": Y < nat["kiYear"],
        })
    for y in years:
        p = next((o for o in years if o["kiYear"] == y["partnerYear"]), None) if y["partnerYear"] is not None else None
        if p:
            y["echo"] = change(p["figure"], y["figure"]) if p["kiYear"] < y["kiYear"] else change(y["figure"], p["figure"])

    def by_py(k):
        return next(y for y in years if y["py"] == k)

    pairs = []
    for lo, hi in ((1, 4), (2, 8), (5, 7)):
        a, b = by_py(lo), by_py(hi)
        pairs.append({"lower": lo, "upper": hi, "a": a, "b": b, "change": change(a["figure"], b["figure"]),
                      "text": PAIR_TEXT[lo](a["kiYear"], b["kiYear"])})
    shocks = [{"k": k, "year": by_py(k), **SHOCK_TEXT[k]} for k in (3, 6, 9)]

    next_cell = _month_cell(n, octave["end"] + 1, 0, nat["monthAbs"], now_abs)
    all_months = [m for y in years for m in y["months"]]
    for i, m in enumerate(all_months):
        following = all_months[i + 1] if i + 1 < len(all_months) else next_cell
        m["toNext"] = change(m["figure"], following["figure"])
    now_cell = _month_cell(n, now_year, now_index, nat["monthAbs"], now_abs)

    gy_now = personal_great_year(n, now_year)
    next_shift = None
    for Y in range(now_year + 1, now_year + 14):
        g = personal_great_year(n, Y)
        if g != gy_now:
            next_shift = {"kiYear": Y, "from": gy_now, "to": g}
            break
    next_cycle_year = (today_octave["end"] if today_octave else now_year) + 1

    return {
        "natal": {"birth": birth.isoformat(), "name": name, "tz": "America/New_York",
                  "triple": natal_label(nat), "kiYear": nat["kiYear"]},
        "today": {
            "date": today.isoformat(),
            "kiMonth": now_cell["label"],
            "personal": f"{now_cell['py']}.{now_cell['pm']}",
            "greatYear": gy_now,
            "yearFigure": _fig(year_figure(n, now_year)),
            "monthFigure": _fig(now_cell["figure"]),
            "monthPosition": now_cell["position"],
            "nextGreatYearShift": next_shift,
            "nextCycle": {"kiYear": next_cycle_year, "figure": _fig(year_figure(n, next_cycle_year))},
        },
        "octave": {
            "index": octave["index"], "label": octave_label(octave), "greatYear": great_year_label(octave),
            "enteredAt": octave.get("enteredAt"),
            "containsToday": bool(today_octave) and today_octave["index"] == octave["index"],
        },
        "octaves": [{"index": o["index"], "label": octave_label(o), "greatYear": great_year_label(o),
                     "today": bool(today_octave) and o["index"] == today_octave["index"]} for o in octs],
        "years": [{
            "kiYear": y["kiYear"], "span": f"Feb {y['kiYear']} → Jan {y['kiYear'] + 1}",
            "personalYear": y["py"], "rim": y["role"], "greatYear": y["gy"], "figure": _fig(y["figure"]),
            "echoPartnerYear": y["partnerYear"], "beforeBirth": y["beforeBirth"],
            "months": [{
                "label": m["label"], "days": f"{m['firstDay']} → {m['lastDay']}",
                "personal": f"{m['py']}.{m['pm']}",
                "figure": f"{m['figure']['number']} {m['figure']['name']}",
                "inherited": m["figure"]["inherited"],
                "position": m["position"],
                **({"now": True} if m["isNow"] else {}),
                **({"beforeBirth": True} if m["beforeBirth"] else {}),
            } for m in y["months"]],
        } for y in years],
        "echoPairs": [{
            "digits": f"{p['lower']} ↔ {p['upper']}", "years": [p["a"]["kiYear"], p["b"]["kiYear"]],
            "primary": _fig(p["change"]["primary"]), "transformed": _fig(p["change"]["transformed"]),
            "movingLines": p["change"]["moving"], "greatYearChanged": p["change"]["lowerMoved"],
            "text": f"{p['text']['title']} {p['text']['body']}",
        } for p in pairs],
        "shocks": [{"digit": s["k"], "title": s["title"], "kiYear": s["year"]["kiYear"],
                    "figure": _fig(s["year"]["figure"]), "text": s["body"]} for s in shocks],
        "nextCycle": {
            "label": next_cell["label"], "personal": f"{next_cell['py']}.{next_cell['pm']}",
            "yearFigure": _fig(year_figure(n, octave["end"] + 1)), "monthFigure": _fig(next_cell["figure"]),
            "greatYear": personal_great_year(n, octave["end"] + 1),
        },
    }
