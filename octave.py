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
- Every level counts down by one, continuously, and never resets at a seam: great year, year, month.
  12 mod 9 = 3, so every Lichun opens on an Earth month (2, 5 or 8), and every great-year gate opens
  on an Earth year. Continuity is the test of any calculation: if a count jumps at a seam, it is wrong.
- Global year: 2026 = 1, descending one per year. The global Feb month for years 1·4·7 is 8, 9·6·3 is
  5, 8·5·2 is 2.
- Great year: 12-year gates, 8 from Lichun 2022 to Lichun 2034, then 7, descending one per gate. Nine
  gates = 108 years.
- Ki Age: 12 great years = 144 years, 2 from Lichun 2022; great age: 9 Ki Ages = 1,296 years, 5 from
  Lichun 2022. Each descends one per period. Read upward at Lichun 2022 the stack is 5 · 2 · 8 · 5 · 2.
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

## How to read
1. Call get_octave(birth_date) for the person's octave, today's position, years, echo pairs and shocks.
2. Locate now: personal year and month, the year and month figures, the rim position, and the next
   great-year shift.
3. Read the year as its figure over the great year. Read the month as its figure over the year.
4. For each echo pair, call get_octave_reading(primary, lines=moving lines) and read the editor's
   judgment, superior-man line, notes and the moving lines; then the transformed figure.
5. Ask of the 6 year whether the strike was made. Ask whether the coming octave repeats the wiring on
   new ground (same figures, shifted great year) or the same ground.
6. Quote the editor where it lands; keep his register: plain, psychological, about the Work.
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
description: "Read a person's life as nine-year octaves: Nine Star Ki on Gurdjieff's enneagram, every year and month an I Ching figure formed over the cycle above it, read through The Gnostic Book of Changes. Loads on 'octave', 'nine star ki', 'ki cycle', 'personal year', 'great year', 'echo pair', 'which hexagram is my year', or any reading of life cycles with the I Ching."
version: 1.0.0
author: Stella
license: MIT
metadata:
  hermes:
    tags: [NineStarKi, Enneagram, IChing, Gurdjieff, Stella, Octave]
    category: domain
    related_skills: []
---

Use Stella's MCP tools `get_octave` and `get_octave_reading` for every number and text; never compute Ki by hand.

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

    @mcp.prompt(name="octave_reading")
    def octave_reading_prompt(birth_date: str = "", focus: str = "") -> str:
        """Read a person's life as nine-year octaves with Stella's octave tools."""
        who = f"The person was born {birth_date}." if birth_date else "Ask for the birth date first."
        on = f" Focus on: {focus}." if focus else ""
        return f"{FRAMEWORK}\n\n## Now\n{who}{on} Follow 'How to read' above, using get_octave and get_octave_reading."
