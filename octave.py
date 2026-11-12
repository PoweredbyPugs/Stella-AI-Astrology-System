"""Octave: Nine Star Ki cycles on Gurdjieff's enneagram, each period read as an I Ching figure.

The math lives in octave_math.py (a port of the Nine-Year Spiral app's library, with hub
inheritance for Ki 5). The readings come from The Gnostic Book of Changes, read from
data/gnostic.json (GNOSTIC_JSON overrides the path).

FRAMEWORK is the way of thinking, served as an MCP prompt and resource and used to generate
the Hermes skill:  python -c "import octave; print(octave.hermes_skill())"
"""

import json
import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

import octave_ledger
from octave_math import build_report

GNOSTIC_JSON = os.environ.get("GNOSTIC_JSON") or str(Path(__file__).parent / "data" / "gnostic.json")
SUPPORTED_TZ = "America/New_York"

FRAMEWORK = """# The Octave: reading a life as nine-year spirals

A way of reading time. A person's Nine Star Ki cycles are laid on Gurdjieff's enneagram, and every
period is read as an I Ching hexagram formed against the cycle that contains it. The source text for
the readings is The Gnostic Book of Changes ("Michael Servetus"): psychological, Jungian, framed as
the Work of individuation.

## The clock
- Ki years run Lichun to Lichun (Sun at 15° Aquarius, about Feb 3-5). Ki months begin when the Sun
  crosses 15° of each sign, around the 4th to 8th of the month.
- Every level counts down by one, continuously, and never resets at a seam: great age, Ki Age, great
  year, year, month, day, hour. Twelve of anything is its parent and nine of anything is one cycle of
  its numbers; 12 mod 9 = 3, so every Lichun opens on an Earth month (2, 5 or 8), and every great-year
  gate opens on an Earth year. Continuity is the test of any calculation: if a count jumps at a seam,
  it is wrong. Below the month, a day is one degree of the Sun past Lichun and an hour five arcminutes.
- Global year: 2026 = 1, descending one per year. The global Feb month for years 1·4·7 is 8, 9·6·3 is
  5, 8·5·2 is 2.
- Great year: 12-year gates, 2 from Lichun 2010, 1 from Lichun 2022 to Lichun 2034, then 9, descending
  one per gate. Nine gates = 108 years.
- Ki Age: 12 great years = 144 years, 5 from Lichun 2010; great age: 12 Ki Ages = 1,728 years (24° of
  precession, one fifteenth of the 25,920-year cycle), 8 from Lichun 2010, the gate before the vernal
  point passed 24° beyond the Lahiri sidereal zero. Each descends one per period. At Lichun 2010 every
  level turned together and the stack read 8 · 5 · 2 · 8 · 2 · 8 · 5. A level is Earth at its own seam
  only when its parent turns too, which is why the 2022 great year is 1.
- Personal Ki: the natal year number read against any global number, personal = ((n - g + 4) mod 9) + 1.
  The same at every level. Personal months rise by one each month.
- Natal triple: natal year . natal month . the personal month at birth (e.g. 5.9.1).

## The octave
- Personal year 1 opens an octave; nine years later the next opens. The octave a person was born into
  is Octave 0, entered at their natal point.
- The number is the rim position, at every level. A personal year 3 sits on point 3 of the enneagram;
  a personal month 6 sits on point 6.
- 3 is the given shock: one-third in, usually from outside, an event the year arranges.
- 6 is the shock that must be made: two-thirds in, cannot be supplied by circumstance. Whether it was
  made decides whether the next octave is a loop or a spiral.
- 9 is source and arrival: not a stage of the cycle but the seeing from which the strikes come and to
  which they return.
- The hexagon 1-4-2-8-5-7 pairs the rest into echo pairs: 1 with 4, 2 with 8, 5 with 7. The earlier
  year poses what the later one tests, carries home, or releases. Each stage hands forward what it
  could not finish.
- Families: 1·4·7 receptive (water), 2·5·8 substrate (earth), 3·6·9 expansive (fire).
- Never use solfege (do, re, mi). Speak of opening, interval, shock, return.

## The figures
- A period's hexagram is its own trigram over the trigram of the cycle that contains it. Year figure
  = personal year over personal great year. Month figure = personal month over personal year.
- Trigrams (Later Heaven): 1 Kan water, 2 Kun earth, 3 Zhen thunder, 4 Sun wind, 6 Qian heaven,
  7 Dui lake, 8 Gen mountain, 9 Li fire. 5 is the centre and has no trigram: it inherits the trigram
  of the nearest level above it that is not 5 (month from year, year from great year, great year
  from Ki Age). A 5 over 5 is the parent's trigram doubled. The output names what was inherited.
- An echo pair is a change: the earlier year's figure is primary, the later is transformed, and the
  moving lines are exactly the lines that differ. If the great year shifted between them, lower lines
  move too; say so.

## The three lenses
- Ba (場), the field: the period's hexagram, its own trigram over its container's (hour over day, day over
  month, month over year, year over great year). The top level has no container and no figure. The
  Gnostic text for it is get_octave_reading(hexagram).
- Shi (勢), the movement: the lines (1 = bottom) where the next period's figure differs from this one.
  Quote the ba's text at those lines; where it lands is the next figure.
- Ji (機), the native in the field: the person's own hexagram, built from the natal month number the
  same way the ba is built from the period, where it differs from the ba. The ji lines are the lines
  that differ, read field to native, so the text quoted is the ba's at those lines. Profiles only;
  the Global period has no ji.
- The circuit 1-4-2-8-5-7 gives every line one figure: destination over origin, both resolved. The
  Tri-force (3, 6, 9, the Law of Three) takes its own trigram doubled at any scale: 51 at 3, 1 at 6,
  30 at 9. It touches the path of time and never the circuit.

## Elements: condition and flow
- One relation between an actor and a field, in five words: resonates (same element), fed by (the field
  generates the actor), feeds (the actor generates the field), controls, controlled by. Generative cycle
  Wood, Fire, Earth, Metal, Water; controlling cycle Wood, Earth, Water, Fire, Metal.
- The condition is the native in the period: the native's element (from the natal year number; a 5
  native is earth) against the period's element (a 5 period takes what it inherits). It reads from the
  25 condition texts.
- The flow is the period in its container (an earth hour in a metal day: feeds). There is none at the
  top level.
- Always say whose element it is: "Your earth in an earth hour". An earth hour feeds its metal day while
  the earth native resonates in it; without the subject the two read as a contradiction.

## The palace
- The Lo Shu with south at the top, home arrangement 4 9 2 / 3 5 7 / 8 1 6. The period's global number
  takes the center and every other number flies the fixed path: the number in a palace is
  ki(home - 5 + global).
- Flags: Five Yellow (the home palace where 5 landed), Broken (the palace opposite Five Yellow), Own (the
  home palace of the person's number at the level), Opposite (opposite Own), Coincides (Own is the Five
  Yellow palace).
- On the palace face each number carries its traditional star, not the point name. The palace steps one
  period at a time and reads no traces and no circuit: the house, the condition and the folded ba only.
- House 1, North: Winter. Dormancy and the hidden work; rest, plan, do not push.
- House 2, South-west: Germination. Preparation, listening, slow groundwork; the risk is Stagnation.
- House 3, East: Spring. Sudden starts and new energy that outruns its body; begin, but keep Composure.
- House 4, South-east: Growth. Expansion, travel, communication; things take off and can scatter.
- House 5, Center: The pivot. Everything comes to you and nothing is displaced; stay put, receive, do not initiate.
- House 6, North-west: Authority. Responsibility and the first harvest; maturity with a perfectionist edge.
- House 7, West: Harvest. Joy, money, reflection, pleasure and its excesses.
- House 8, North-east: The turning point. Stillness before change; revolution held in the mountain.
- House 9, South: Illumination. Recognition and exposure; things come to light.

## The ledger
The nine points, each a name and the question every reading is built from:
- 1 Potential: What's under the surface?
- 2 Field: What is being received?
- 3 Power: What arrived?
- 4 River: Which way?
- 5 Delta: What landed here from above?
- 6 Will: What was the ego magnetic to?
- 7 Lake: What is the yield?
- 8 Mountain: This is what lasted. Not touching it yet.
- 9 Clarity: What is clear from here?
- Families: 1·4·7 receptive, 2·5·8 substrate, 3·6·9 expansive.
- The three forces take their own trigram doubled: 3 Power, 51 Shock, force from the outside in; 6 Will,
  1 The Dynamic, force from the inside out, brought under will; 9 Clarity, 30 Clarity, the force that
  sees the two as one. This is the Tri-force.
The six lines of the circuit, each a verb and a trace kind:
- 1 → 4 nourish, interval trace
- 4 → 2 break, octave trace
- 2 → 8 inherit, interval trace
- 8 → 5 keep, octave trace
- 5 → 7 reflect, interval trace
- 7 → 1 shape, octave trace
- Tending: the three earth points are three scales of tending. 2 tends everything, in the dark, in
  private, not for show. 5 tends the self: unblocking, so that what is coming through can land, not
  pushing outward. 8 tends one thing, with great care. An earth period closes on a tending at that
  scale, not a push.
- get_octave_point(n) and get_octave_line(from, to) return the full brief of a point and of a line;
  the whole ledger is the octave://ledger resource.

## Reading order
The page's order, on every face: the head (the number and the point's name; on the palace, the
traditional star), the condition (whose element sits in whose, and the flow), ji (the native in the
field), shi (what is moving), and in practice (the line's verb and its practice, and the tending for an
earth point). Read a circuit point's two lines interval trace first (1 to 4, 2 to 8, 5 to 7, inside the
octave), octave trace second (4 to 2, 8 to 5, 7 to 1, leaving it), whichever is incoming. Without a
profile, give the point's plain question; with one, the question carries the condition clause.

## Standing rules
- The reading is a reading, not a system explanation: no attribute lists, no method words, no account of the mechanics in anything a person reads. Explanation lives in the ledger.
- The ledger text is verbatim; change it in the study ledger first. Rewords for the reading are overrides in briefs.js.
- Jev decides and grades; Jev never writes. Never ask Jev what code can count (sentences, words, an ending).
- The forecast and the statement are synthesis, "something new, not a cookbook recipe".
- Always say whose element it is ("Your earth in an earth hour"); never the bare pair.
- American spelling everywhere. No em-dashes in page text (the pipelines turn them into commas). No emoji in UI.
- UI names: the three faces octave, plot, palace; the path of time and the circuit; Tri-force with the hyphen; Ba, Shi, Ji, In Practice. The ledger keeps rim, hexad, Triforce.

## How to read
Every number and text comes from a tool; never compute Ki, a figure or a relation by hand.
1. get_octave(birth_date): the person's octave, today's position, years, echo pairs and shocks.
2. get_octave_reading(hexagram, lines): the Gnostic Book of Changes at a figure and its moving lines.
3. get_octave_period(level, datetime, natal): start here for any period. The ba, shi, house, point and
   palace; with natal, the full packet with ji and the six sources.
4. get_octave_condition(natal, level, datetime): the condition and the flow with their words and
   readings, the composed statement and the quiet sentence.
5. get_native_figure(natal, level, datetime): the native hexagram, the ji lines and the ba's text there.
6. get_octave_shi(level, datetime, natal): the lines that change into the next period, and the text.
7. get_palace(level, datetime, natal): the Lo Shu flight, flags, house line and star.
8. get_octave_point(number): one point's brief, tending and family; the Tri-force at 3, 6, 9.
9. get_octave_line(from_number, to_number, datetime): one circuit line, its verb, practice and figure.
10. write_octave_statement(natal, level, datetime): one written thought, Jev deciding and grading.
11. explain_octave_statement(natal, level, datetime): the reading of that thought, phrase by phrase.
12. write_octave_forecast(natal, level, datetime): one paragraph of synthesis for the period.
Order: get_octave_period, then get_octave_condition, get_native_figure and get_octave_shi, then the
palace and the point as the question needs. Read the year as its figure over the great year and the
month as its figure over the year. For each echo pair call get_octave_reading(primary, lines=moving
lines), then the transformed figure. Ask of the 6 year whether the strike was made, and whether the
coming octave repeats the wiring on new ground or the same ground. Quote the editor where it lands;
keep his register: plain, psychological, about the Work. Period indexes count gate levels from 2010.
"""


def octave_report(birth_date: str, octave: Optional[int] = None, target_date: Optional[str] = None,
                  tz: Optional[str] = None, name: Optional[str] = None, include_months: bool = False) -> dict:
    if tz and tz != SUPPORTED_TZ:
        raise ValueError(f"Only {SUPPORTED_TZ} boundaries are supported (got {tz})")
    today = date.fromisoformat(target_date) if target_date else date.today()
    data = build_report(date.fromisoformat(birth_date), octave, today, name)
    if not include_months:
        # Months only for the year containing today, to keep the report short.
        for y in data.get("years", []):
            if not any(m.get("now") for m in y.get("months", [])):
                y.pop("months", None)
    return data


@lru_cache(maxsize=1)
def load_gnostic() -> dict:
    """The Gnostic Book of Changes keyed by King Wen number; empty if the file is missing."""
    try:
        with open(GNOSTIC_JSON, encoding="utf-8") as f:
            return {int(h["number"]): h for h in json.load(f)}
    except (OSError, ValueError):
        return {}


def _blocks(blocks: list, limit: Optional[int] = None) -> str:
    out = []
    for b in blocks[:limit]:
        t = b["text"].replace(" -- ", " — ")
        if b["kind"] == "quote":
            out.append("> " + t + (f"\n> — {b['by']}" if b.get("by") else ""))
        elif b["kind"] == "summary":
            out.append(f"{b['by']}. {t}")
        elif b["kind"] == "heading":
            out.append(f"**{t}**")
        elif b["kind"] == "date":
            out.append(f"(editor's cast: {t})")
        else:
            out.append((f"{b['by']}: " if b.get("by") else "") + t)
    return "\n\n".join(out)


def octave_reading(hexagram: int, lines: Optional[list] = None, full: bool = True) -> str:
    h = load_gnostic().get(int(hexagram))
    if h is None:
        return f"No reading for hexagram {hexagram}: not in The Gnostic Book of Changes at {GNOSTIC_JSON}."
    parts = [
        f"# {h['number']} {h['title']}",
        f"Other titles: {h['otherTitles']}",
        f"Editor's judgment: {h['editorJudgment']}",
        h["superiorMan"],
    ]
    if full:
        parts.append(_blocks(h["notes"]))
    for n in lines or []:
        l = h["lines"][int(n) - 1]
        text = next((t["text"] for t in l["translations"] if t["source"] == "Wilhelm/Baynes"), "")
        parts.append(f"## Line {n}\n{text}\n\n{_blocks(l['notes'])}")
    return "\n\n".join(p for p in parts if p).replace(" -- ", " — ")


def hermes_skill() -> str:
    return """---
name: octave
description: "Read a person's life as nine-year octaves: Nine Star Ki on Gurdjieff's enneagram, every year and month an I Ching figure formed over the cycle above it, read through The Gnostic Book of Changes, with the three lenses ba, shi and ji, the condition and the flow, the Lo Shu palace, and written readings. Loads on 'octave', 'nine star ki', 'ki cycle', 'personal year', 'great year', 'echo pair', 'which hexagram is my year', or any reading of life cycles with the I Ching."
version: 2.0.0
author: Stella
license: MIT
metadata:
  hermes:
    tags: [NineStarKi, Enneagram, IChing, Gurdjieff, Stella, Octave]
    category: domain
    related_skills: []
---

Use Stella's MCP tools (`get_octave`, `get_octave_reading` and the ten period tools in 'How to read') for every number and text; never compute Ki by hand.

""" + FRAMEWORK


def register_octave(mcp) -> None:
    """Add the octave tools, prompt and resource to Stella's FastMCP server."""

    @mcp.tool()
    async def get_octave(
        birth_date: str,
        octave: Optional[int] = None,
        target_date: Optional[str] = None,
        tz: Optional[str] = None,
        name: Optional[str] = None,
        include_months: bool = False,
    ) -> str:
        """Get a person's nine-year octave: natal Ki, all octaves, today's position, the nine years with
        their I Ching figures (year over great year), echo pairs with moving lines, shocks and the next cycle.

        Computed in Stella: continuous months, 12-year great-year gates, hub inheritance for 5 (a 5
        forms over the level above it and the figure says so). Read it with the `octave_reading`
        prompt or the octave://framework resource.

        Args:
            birth_date: Birth date YYYY-MM-DD
            octave: Octave index (0 = birth octave); default the octave containing target_date
            target_date: "Today" YYYY-MM-DD (default: today)
            tz: IANA time zone for period boundaries (default America/New_York)
            name: Optional name for the report
            include_months: Include all 108 months (default: only the current year's)
        """
        try:
            return json.dumps(octave_report(birth_date, octave, target_date, tz, name, include_months), ensure_ascii=False, indent=1)
        except ValueError as e:
            return f"Cannot build the octave: {e}"

    @mcp.tool()
    async def get_octave_reading(hexagram: int, lines: Optional[str] = None, full: bool = True) -> str:
        """Read a hexagram from The Gnostic Book of Changes: the editor's judgment, superior-man line,
        his notes with quotes, and any moving lines (classic text, Siu, Wing, editor, lettered readings).

        Args:
            hexagram: King Wen number 1-64
            lines: Moving lines, comma separated, e.g. "4,5"
            full: Include the editor's full notes (default true); false gives judgment and lines only
        """
        ls = [int(x) for x in lines.split(",") if x.strip()] if lines else []
        return octave_reading(hexagram, ls, full)

    @mcp.resource("octave://framework")
    def octave_framework() -> str:
        """The octave framework: Ki clock, enneagram rim, figure formation, how to read."""
        return FRAMEWORK

    @mcp.resource("octave://ledger")
    def octave_ledger_resource() -> str:
        """The Octave ledger as JSON: points, houses, stars, relation words, the 25 condition readings, lines, tending."""
        return json.dumps(octave_ledger.load(), ensure_ascii=False, indent=1)

    @mcp.prompt(name="octave_reading")
    def octave_reading_prompt(birth_date: str = "", focus: str = "") -> str:
        """Read a person's life as nine-year octaves with Stella's octave tools."""
        who = f"The person was born {birth_date}." if birth_date else "Ask for the birth date first."
        on = f" Focus on: {focus}." if focus else ""
        return f"{FRAMEWORK}\n\n## Now\n{who}{on} Follow 'How to read' above, using get_octave and get_octave_reading."

    @mcp.prompt(name="octave_period_reading")
    def octave_period_reading_prompt(birth_date: str = "", level: str = "day", datetime: str = "") -> str:
        """Read one period for a person in the page's order: head, condition, ji, shi, in practice."""
        who = f"The person was born {birth_date}." if birth_date else "Ask for the birth date first."
        at = f" at {datetime}" if datetime else " now"
        return (f"{FRAMEWORK}\n\n## Now\n{who} Read the {level}{at}. Call get_octave_period for that person, level "
                "and instant, then get_octave_condition, get_native_figure and get_octave_shi. Read in the "
                "page's order (head, condition, ji, shi, in practice), under the standing rules above.")
