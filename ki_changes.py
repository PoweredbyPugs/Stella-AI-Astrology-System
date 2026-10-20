"""Ki Changes — Mercury's function applied to Ki.

Mercury reads the transitions, not the states. This module computes:
1. When each Ki level changes next (hour, day, month, year, synodic)
2. The hexagram formed by each pair of adjacent Ki levels (lower=stable, upper=changing)
3. The changing lines between current and next Ki at each level
4. Cross-references to the Gnostic Book of Changes for interpretation

The I Ching IS Mercury's grid: 64 = 8², and every Ki transition is a hexagram
because every pair of trigrams forms a hexagram in the King Wen sequence.

Ki 5 (Center/Tai Chi) has no trigram. In the timekeeping stack a 5 inherits the
trigram of the nearest level above it that is not 5 (hour from day, day from month,
month from year, year from great year, great year from Ki Age, Ki Age from great
age). Every figure is formed from the full stack through hub_inheritance, personal
figures from the personal stack only, and moving lines are always the line-by-line
difference of two figures. The stack carries the Ki Age (144 years) and great age
(1,296 years) above the great year ("synodic" in this module's output).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from hub_inheritance import (
    LEVELS as HUB_LEVELS, TRIGRAM_ELEMENT, TRIGRAM_IMAGE, TRIGRAM_LINES, TRIGRAM_PINYIN,
    TRIGRAM_SYMBOL, HubUnresolvable, hexagram, moving_lines, resolve,
)
from ki_levels import gate_start, global_great_age, global_ki_age, personal_stack, PERIOD_YEARS

TZ = ZoneInfo("America/New_York")

# Ki number → trigram (Later Heaven). 5 has no entry: it inherits (see hub_inheritance).
KI_TO_TRIGRAM = {
    k: {"name": TRIGRAM_PINYIN[k], "symbol": TRIGRAM_SYMBOL[k], "element": TRIGRAM_IMAGE[k],
        "lines": list(TRIGRAM_LINES[k])}
    for k in TRIGRAM_LINES
}

# Wu Xing (Five Phases) productive and controlling cycles
WU_XING_PRODUCES = {
    "Wood": "Fire", "Fire": "Earth", "Earth": "Metal",
    "Metal": "Water", "Water": "Wood",
}
WU_XING_CONTROLS = {
    "Wood": "Earth", "Fire": "Metal", "Earth": "Water",
    "Metal": "Wood", "Water": "Fire",
}

LEVEL_NAMES = ["synodic", "year", "month", "day", "hour"]
UPPER_LEVELS = ["great_age", "ki_age"]
# Adjacent pairs: (lower = slower/stable, upper = faster/changing)
PAIRS = [("synodic", "year"), ("year", "month"), ("month", "day"), ("day", "hour")]

_DISPLAY = {"great_year": "synodic"}
_HUB = {"synodic": "great_year"}


def hub_level(name: str) -> str:
    """Output level name → hub_inheritance level name ('synodic' → 'great_year')."""
    return _HUB.get(name, name)


def display_level(name: str) -> str:
    return _DISPLAY.get(name, name)


def _descend(k: int) -> int:
    return (k - 2) % 9 + 1


def next_stack(stack_now: dict, level: str, change_times: dict) -> dict:
    """The stack just after ``level`` changes: that level descends by one, and so does every
    parent whose change instant equals this level's (a great-year, Ki Age or great-age gate
    coinciding with the next Lichun). ``change_times`` is keyed by output level names."""
    lvl = hub_level(level)
    out = dict(stack_now)
    out[lvl] = _descend(out[lvl])
    when = change_times.get(display_level(lvl))
    for parent in HUB_LEVELS[:HUB_LEVELS.index(lvl)]:
        if parent in out and when is not None and change_times.get(display_level(parent)) == when:
            out[parent] = _descend(out[parent])
    return out


def _trigram_view(r) -> dict:
    tag = f" (inherited from {r.inherited_from})" if r.inherited_from else ""
    return {
        "ki": r.ki,
        "trigram": TRIGRAM_PINYIN[r.source_ki] + tag,
        "symbol": TRIGRAM_SYMBOL[r.source_ki],
        "lines": list(r.lines),
        "inherited_from": r.inherited_from,
    }


def _hexagram_from_ki(stack: dict, lower_level: str, upper_level: str) -> dict:
    """Form the hexagram of upper over lower from a full stack (output level names)."""
    h = hexagram(stack, upper=hub_level(upper_level), lower=hub_level(lower_level))
    h["lower"]["level"] = lower_level
    h["upper"]["level"] = upper_level
    return h


def _direction(m: dict) -> dict:
    return {"line": m["line"], "direction": f"{m['from']}→{m['to']}"}


def _changing_lines(level: str, stack_now: dict, stack_next: dict) -> dict:
    """Changing lines of one level: its resolved trigram now against its resolved trigram after
    the change (parents as they are at that instant)."""
    curr = resolve(stack_now, hub_level(level))
    nxt = resolve(stack_next, hub_level(level))
    changes = [_direction(m) for m in moving_lines(curr.lines, nxt.lines)]
    return {
        "current": _trigram_view(curr),
        "next": _trigram_view(nxt),
        "changing_lines": changes,
        "num_changes": len(changes),
    }


def _wu_xing_relationship(elem1: str, elem2: str) -> str:
    """Describe the Wu Xing relationship between two elements."""
    if elem1 == elem2:
        return "same element (resonance)"
    if WU_XING_PRODUCES.get(elem1) == elem2:
        return f"{elem1} GENERATES {elem2} (productive/shēng)"
    if WU_XING_PRODUCES.get(elem2) == elem1:
        return f"{elem2} GENERATES {elem1} (productive/shēng, reverse)"
    if WU_XING_CONTROLS.get(elem1) == elem2:
        return f"{elem1} CONTROLS {elem2} (controlling/kè)"
    if WU_XING_CONTROLS.get(elem2) == elem1:
        return f"{elem2} CONTROLS {elem1} (controlling/kè, reverse)"
    return f"{elem1} → {elem2} (no direct cycle relationship)"


def _pair_figure(stack_now: dict, lower_name: str, upper_name: str, change_instants: dict) -> dict:
    """A pair's hexagram now, the figure after the upper level changes, and the lines between."""
    h = _hexagram_from_ki(stack_now, lower_name, upper_name)
    after = _hexagram_from_ki(next_stack(stack_now, upper_name, change_instants), lower_name, upper_name)
    h["transformed"] = {"hexagram": after["hexagram"], "lines": after["lines"]}
    h["changing"] = [_direction(m) for m in moving_lines(tuple(h["lines"]), tuple(after["lines"]))]
    h["wu_xing"] = _wu_xing_relationship(h["lower"]["element"], h["upper"]["element"])
    h["pair"] = f"{lower_name} (stable) / {upper_name} (changing)"
    return h


def _chain(stack_now: dict, change_instants: dict, change_times: dict) -> tuple:
    """level_changes and hexagrams for one chain (global or personal)."""
    level_changes = {}
    for level in LEVEL_NAMES:
        lc = _changing_lines(level, stack_now, next_stack(stack_now, level, change_instants))
        lc["changes_at"] = change_times[level]
        lc["wu_xing"] = _wu_xing_relationship(
            TRIGRAM_ELEMENT[resolve(stack_now, hub_level(level)).source_ki],
            TRIGRAM_ELEMENT[resolve(next_stack(stack_now, level, change_instants), hub_level(level)).source_ki],
        )
        level_changes[level] = lc
    hexagrams = {f"{lo}_{up}": _pair_figure(stack_now, lo, up, change_instants) for lo, up in PAIRS}
    return level_changes, hexagrams


def _view(stack: dict) -> dict:
    """Hub stack → output dict with the great year named 'synodic'."""
    return {display_level(k): v for k, v in stack.items()}


def get_ki_changes(target_date: str = None, birth_date: str = None) -> dict:
    """Compute Ki changes at all levels — Mercury's reading of the Ki field.

    For each level (synodic, year, month, day, hour):
    - Current Ki number and when it changes next
    - Next Ki number after the change
    - Changing lines (resolved trigram now → resolved trigram after)
    - Wu Xing phase relationship of the transition

    For each adjacent pair of levels:
    - The hexagram formed (lower=slower/stable, upper=faster/changing), its lines,
      the figure after the upper level changes, the lines between, and any inheritance

    The stack also carries ki_age and great_age. Includes personal Ki if birth_date is
    provided. Returns {"error": ...} if a stack cannot be resolved.

    Args:
        target_date: ISO date YYYY-MM-DD (default: now)
        birth_date: Birth date YYYY-MM-DD for personal Ki overlay
    """
    from convergence_ki import (
        get_convergence_ki, _find_lichun, _dt_to_jd, _jd_to_dt,
        synodic_gate_start, SYNODIC_GATE_YEARS,
    )
    import swisseph as swe

    if target_date:
        td = datetime.fromisoformat(target_date)
        if td.tzinfo is None:
            td = td.replace(tzinfo=TZ)
    else:
        td = datetime.now(TZ)

    # Get current full Ki state
    ki_data = get_convergence_ki(
        target_date=td.strftime("%Y-%m-%d"),
        birth_date=birth_date,
    )

    from ki_calendar import ki_year_of
    lichun_year = ki_year_of(td.date())

    stack_now = {
        "great_age": global_great_age(lichun_year),
        "ki_age": global_ki_age(lichun_year),
        "great_year": ki_data["synodic"]["ki"],
        "year": ki_data["year"]["ki"],
        "month": ki_data["month"]["ki"],
        "day": ki_data["day"]["ki"],
        "hour": ki_data["hour"]["ki"],
    }

    # ── When each level changes next ──

    # Hour: changes every 2 hours (double-hour boundary)
    local_hour = td.hour
    if local_hour >= 23:
        double_hour = 1
    elif local_hour < 1:
        double_hour = 1
    else:
        double_hour = (local_hour + 1) // 2 + 1

    dh_starts = [23, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
    if double_hour < 12:
        next_dh_hour = dh_starts[double_hour]
        next_hour_dt = td.replace(hour=next_dh_hour, minute=0, second=0, microsecond=0)
        if next_dh_hour <= td.hour:
            next_hour_dt += timedelta(days=1)
    else:
        next_hour_dt = td.replace(hour=23, minute=0, second=0, microsecond=0)
        if td.hour >= 23:
            next_hour_dt += timedelta(days=1)

    # Day: changes at midnight (solar day boundary)
    next_day_dt = (td + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Month: changes when Sun crosses next 30° boundary from Lichun
    now_jd = _dt_to_jd(td)
    sun_lon = swe.calc_ut(now_jd, swe.SUN)[0][0]
    deg_from_lichun = (sun_lon - 315) % 360
    current_month_seg = int(deg_from_lichun / 30)
    next_month_deg = (315 + (current_month_seg + 1) * 30) % 360
    days_to_next = ((next_month_deg - sun_lon) % 360) / 1.0
    approx_jd = now_jd + days_to_next
    for _ in range(20):
        s = swe.calc_ut(approx_jd, swe.SUN)[0][0]
        diff = (next_month_deg - s) % 360
        if diff > 180:
            diff -= 360
        if abs(diff) < 0.001:
            break
        approx_jd += diff / 1.0
    next_month_dt = _jd_to_dt(approx_jd)

    # Year: changes at the next Lichun. Gates above it open at a Lichun too.
    next_year_dt = _jd_to_dt(_find_lichun(lichun_year + 1))
    gate_years = {
        "synodic": synodic_gate_start(lichun_year) + SYNODIC_GATE_YEARS,
        "ki_age": gate_start(lichun_year, "ki_age") + PERIOD_YEARS["ki_age"],
        "great_age": gate_start(lichun_year, "great_age") + PERIOD_YEARS["great_age"],
    }
    # A gate opens at a Lichun; it coincides with the year change exactly when it is the next
    # Lichun. Far gates (the great age) are beyond the ephemeris, so compare by gate year.
    gate_instants = {k: next_year_dt if y == lichun_year + 1 else f"Lichun {y}" for k, y in gate_years.items()}

    change_instants = {
        "hour": next_hour_dt, "day": next_day_dt, "month": next_month_dt, "year": next_year_dt,
        **gate_instants,
    }
    change_times = {
        "hour": next_hour_dt.isoformat(),
        "day": next_day_dt.isoformat(),
        "month": next_month_dt.strftime("%Y-%m-%d %I:%M %p"),
        "year": next_year_dt.strftime("%Y-%m-%d %I:%M %p"),
        "synodic": f"Lichun {gate_years['synodic']} (next 12-year gate)",
        "ki_age": f"Lichun {gate_years['ki_age']} (next Ki Age gate)",
        "great_age": f"Lichun {gate_years['great_age']} (next great age gate)",
    }

    next_global = {display_level(lvl): next_stack(stack_now, display_level(lvl), change_instants)[lvl]
                   for lvl in stack_now}

    try:
        level_changes, hexagrams = _chain(stack_now, change_instants, change_times)
    except HubUnresolvable as e:
        return {"error": str(e)}

    # ── Personal Ki changes (if birth_date) ──
    personal = None
    if birth_date and "personal" in ki_data:
        natal_yki = ki_data["personal"]["natal_year_ki"]
        p_now = personal_stack(natal_yki, stack_now)
        p_next = {display_level(lvl): personal_stack(natal_yki, next_stack(stack_now, display_level(lvl), change_instants))[lvl]
                  for lvl in stack_now}
        try:
            p_changes, p_hexagrams = _chain(p_now, change_instants, change_times)
        except HubUnresolvable as e:
            return {"error": str(e)}
        personal = {
            "natal_year_ki": natal_yki,
            "current": _view(p_now),
            "next": p_next,
            "level_changes": p_changes,
            "hexagrams": p_hexagrams,
        }

    return {
        "timestamp": td.isoformat(),
        "global": {
            "current": _view(stack_now),
            "next": next_global,
            "change_times": change_times,
        },
        "level_changes": level_changes,
        "hexagrams": hexagrams,
        "personal": personal,
        "note": "Mercury reads the delta. Lower trigram = slower level (stable ground). Upper trigram = faster level (what's cycling). A 5 inherits the nearest non-5 level above it; changing lines are the difference between the resolved figures.",
    }


NUM_WORDS = {
    1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE",
    6: "SIX", 7: "SEVEN", 8: "EIGHT", 9: "NINE", 10: "TEN",
    11: "ELEVEN", 12: "TWELVE", 13: "THIRTEEN", 14: "FOURTEEN",
    15: "FIFTEEN", 16: "SIXTEEN", 17: "SEVENTEEN", 18: "EIGHTEEN",
    19: "NINETEEN", 20: "TWENTY", 21: "TWENTY-ONE", 22: "TWENTY-TWO",
    23: "TWENTY-THREE", 24: "TWENTY-FOUR", 25: "TWENTY-FIVE",
    26: "TWENTY-SIX", 27: "TWENTY-SEVEN", 28: "TWENTY-EIGHT",
    29: "TWENTY-NINE", 30: "THIRTY", 31: "THIRTY-ONE",
    32: "THIRTY-TWO", 33: "THIRTY-THREE", 34: "THIRTY-FOUR",
    35: "THIRTY-FIVE", 36: "THIRTY-SIX", 37: "THIRTY-SEVEN",
    38: "THIRTY-EIGHT", 39: "THIRTY-NINE", 40: "FORTY",
    41: "FORTY-ONE", 42: "FORTY-TWO", 43: "FORTY-THREE",
    44: "FORTY-FOUR", 45: "FORTY-FIVE", 46: "FORTY-SIX",
    47: "FORTY-SEVEN", 48: "FORTY-EIGHT", 49: "FORTY-NINE",
    50: "FIFTY", 51: "FIFTY-ONE", 52: "FIFTY-TWO", 53: "FIFTY-THREE",
    54: "FIFTY-FOUR", 55: "FIFTY-FIVE", 56: "FIFTY-SIX",
    57: "FIFTY-SEVEN", 58: "FIFTY-EIGHT", 59: "FIFTY-NINE",
    60: "SIXTY", 61: "SIXTY-ONE", 62: "SIXTY-TWO", 63: "SIXTY-THREE",
    64: "SIXTY-FOUR",
}

LINE_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def lookup_hexagram_gnostic(hex_num: int, changing_lines: list = None) -> dict:
    """Search Neo4j for Gnostic Book of Changes content for a hexagram.

    Returns the full line text for each changing line including:
    - All translator versions (Legge, Wilhelm, Blofeld, Liu, etc.)
    - Confucian commentary
    - Editor's commentary with quotes
    - Lettered statements (A, B, C, D...)

    Args:
        hex_num: King Wen hexagram number (1-64)
        changing_lines: List of changing line numbers (1-6)

    Returns:
        Dict with judgment text, full line texts, and chunk references.
    """
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "[REDACTED]"))

        results = {"hexagram": hex_num, "judgment": None, "line_readings": {}}

        with driver.session() as session:
            # ── Get judgment/title text ──
            num_word = NUM_WORDS.get(hex_num, "")
            # Hex marker patterns used in Gnostic I Ching chunks
            # Format varies: "24 -- Return -- 24" or "-- 24 --" or just the number
            hex_marker = f"{hex_num} -- "

            # Try HEXAGRAM NUMBER pattern first (most reliable for title chunk)
            if num_word:
                recs = session.run("""
                    MATCH (i:Interpretation)
                    WHERE i.source_title CONTAINS 'Gnostic Book of Changes'
                      AND i.text CONTAINS $pattern
                    RETURN i.text
                    ORDER BY size(i.text) DESC
                    LIMIT 1
                """, pattern=f"HEXAGRAM NUMBER {num_word}").data()

                if recs:
                    text = recs[0]["i.text"]
                    idx = text.find(f"HEXAGRAM NUMBER {num_word}")
                    if idx >= 0:
                        results["judgment"] = text[idx:idx+1500]

            # ── Get changing line texts ──
            if changing_lines:
                for line_num in changing_lines:
                    line_word = LINE_WORDS.get(line_num, str(line_num))

                    # Search for the Line-N marker (format used in Gnostic I Ching)
                    # and also "Line N" / "line N" in context of this hexagram
                    for search_pattern in [
                        f"Line-{line_num}",
                        f"Legge: The {line_word}",
                        f"Legge: Line {line_word}",
                    ]:
                        recs = session.run("""
                            MATCH (i:Interpretation)
                            WHERE i.source_title CONTAINS 'Gnostic Book of Changes'
                              AND i.text CONTAINS $line_pattern
                              AND i.text CONTAINS $hex_marker
                            RETURN i.text
                            ORDER BY size(i.text) DESC
                            LIMIT 1
                        """, line_pattern=search_pattern, hex_marker=hex_marker).data()

                        if recs:
                            text = recs[0]["i.text"]
                            # Find the line section start
                            line_start = -1
                            for marker in [f"Line-{line_num}", f"Legge: The {line_word}",
                                           f"Legge: Line {line_word}"]:
                                idx = text.find(marker)
                                if idx >= 0:
                                    line_start = idx
                                    break

                            if line_start >= 0:
                                # Find the end: next Line-N marker or end of chunk
                                line_end = len(text)
                                next_line = line_num + 1
                                for end_marker in [
                                    f"Line-{next_line}",
                                    f"Legge: The {LINE_WORDS.get(next_line, '')}",
                                    f"Legge: Line {LINE_WORDS.get(next_line, '')}",
                                ]:
                                    eidx = text.find(end_marker, line_start + 20)
                                    if eidx > 0 and eidx < line_end:
                                        line_end = eidx

                                # Grab the Editor/Notes section BEFORE the line marker.
                                # In the Gnostic I Ching, the pattern is:
                                #   Editor: [commentary]
                                #   [quotes]
                                #   A. [statement]
                                #   B. [statement]
                                #   24 -- Return -- 24
                                #   C. [more statements]
                                #   Line-4
                                #   Legge: [translations]
                                #   COMMENTARY
                                # So we need to go back to "Editor:" or "NOTES AND PARAPHRASES"
                                editor_start = line_start
                                for back_marker in ["Editor:", "NOTES AND PARAPHRASES"]:
                                    bidx = text.rfind(back_marker, max(0, line_start - 3000), line_start)
                                    if bidx >= 0 and bidx < editor_start:
                                        editor_start = bidx

                                full_line_text = text[editor_start:line_end].strip()
                                results["line_readings"][line_num] = full_line_text
                            break

                    # If we still didn't find it, try broader search
                    if line_num not in results["line_readings"]:
                        recs = session.run("""
                            MATCH (i:Interpretation)
                            WHERE i.source_title CONTAINS 'Gnostic Book of Changes'
                              AND i.text CONTAINS $hex_marker
                              AND i.text CONTAINS $editor_marker
                            RETURN i.text
                            ORDER BY size(i.text) DESC
                            LIMIT 3
                        """, hex_marker=hex_marker, editor_marker="Editor:").data()

                        for r in recs:
                            text = r["i.text"]
                            # Check if this chunk has our line
                            for marker in [f"Line-{line_num}", f"line {line_word}"]:
                                if marker.lower() in text.lower():
                                    idx = text.lower().find(marker.lower())
                                    # Get from Editor section before this line to end
                                    editor_idx = text.rfind("Editor:", max(0, idx - 3000), idx)
                                    if editor_idx < 0:
                                        editor_idx = max(0, idx - 500)
                                    line_end = len(text)
                                    next_line = line_num + 1
                                    for em in [f"Line-{next_line}", f"line {LINE_WORDS.get(next_line, '')}"]:
                                        eidx = text.lower().find(em.lower(), idx + 20)
                                        if eidx > 0 and eidx < line_end:
                                            line_end = eidx
                                    results["line_readings"][line_num] = text[editor_idx:line_end].strip()
                                    break
                            if line_num in results["line_readings"]:
                                break

        driver.close()
        return results

    except Exception as e:
        return {"hexagram": hex_num, "error": str(e), "line_readings": {}}


def _stack_line(cur: dict) -> str:
    return ".".join(str(cur.get(l, "?")) for l in UPPER_LEVELS + LEVEL_NAMES)


def _hexagram_block(hx: dict, lower_name: str, upper_name: str) -> list:
    """Diagram + changing lines + transformed figure for one pair, from its dict."""
    out = []
    out.append(f"{'═' * 60}")
    out.append(f"HEXAGRAM {hx['hexagram']} — {lower_name.upper()}/{upper_name.upper()}")
    out.append(f"  {hx['upper']['trigram']} above  (Ki {hx['upper']['ki']})")
    out.append(f"  {hx['lower']['trigram']} below  (Ki {hx['lower']['ki']})")
    out.append(f"  Wu Xing: {hx.get('wu_xing', '')}")
    out.append("")
    changing = hx["changing"]
    for i in range(5, -1, -1):
        val = hx["lines"][i]
        sym = "━━━━━" if val == 1 else "━━ ━━"
        ch = next((c for c in changing if c["line"] == i + 1), None)
        marker = f" ← ({ch['direction']})" if ch else ""
        out.append(f"  Line {i+1}: {sym}{marker}")
    out.append("")
    if changing:
        out.append(f"  Changing lines: {', '.join(str(c['line']) for c in changing)}")
        out.append(f"  → Transforms to: Hexagram {hx['transformed']['hexagram']}")
    else:
        out.append("  No changing lines (pure hexagram)")
    out.append("")
    return out


def format_ki_changes_full(data: dict, personal: bool = True) -> str:
    """Format Ki changes — FULL STACK view (compact).

    Shows hexagram diagram + judgment + transformed hexagram for each pair.
    Does NOT include individual changing line readings (use individual level
    tools like ki_change_day for that).

    Args:
        data: Output from get_ki_changes()
        personal: If True and personal data exists, show personal hexagrams
    """
    if "error" in data:
        return f"Ki stack unresolvable: {data['error']}"
    lines = []
    lines.append("═══ KI CHANGES — MERCURY'S READING ═══")
    lines.append(f"Timestamp: {data['timestamp']}")
    lines.append("")

    if personal and data.get("personal"):
        p = data["personal"]
        lines.append(f"PERSONAL: {_stack_line(p['current'])}")
        lines.append(f"NEXT:     {_stack_line(p['next'])}")
        hex_source = p.get("hexagrams", {})
    else:
        g = data["global"]
        lines.append(f"GLOBAL: {_stack_line(g['current'])}")
        lines.append(f"NEXT:   {_stack_line(g['next'])}")
        hex_source = data.get("hexagrams", {})
    lines.append("  (great age . Ki Age . great year . year . month . day . hour)")
    lines.append("")

    for lower_name, upper_name in PAIRS:
        hx = hex_source.get(f"{lower_name}_{upper_name}")
        if not hx:
            continue
        lines.extend(_hexagram_block(hx, lower_name, upper_name))

        gnostic = lookup_hexagram_gnostic(hx["hexagram"])
        if gnostic.get("judgment"):
            lines.append("  JUDGMENT:")
            for jl in gnostic["judgment"][:800].split("\n"):
                lines.append(f"  {jl}")
            lines.append("")
        lines.append("")

    return "\n".join(lines)


def format_ki_changes(data: dict, include_gnostic: bool = True) -> str:
    """Format Ki changes output — compact version without Gnostic text.

    Args:
        data: Output from get_ki_changes()
        include_gnostic: Ignored (kept for backward compat). Use format_ki_changes_full for Gnostic text.
    """
    if "error" in data:
        return f"Ki stack unresolvable: {data['error']}"
    lines = []
    lines.append("═══ KI CHANGES — MERCURY'S READING ═══")
    lines.append(f"Timestamp: {data['timestamp']}")
    lines.append("")

    g = data["global"]
    lines.append(f"CURRENT: {_stack_line(g['current'])}")
    lines.append(f"NEXT:    {_stack_line(g['next'])}")
    lines.append("  (great age . Ki Age . great year . year . month . day . hour)")
    lines.append("")

    lines.append("── TRANSITIONS (when each level shifts) ──")
    for level in LEVEL_NAMES:
        lc = data["level_changes"][level]
        curr_t = lc["current"]
        next_t = lc["next"]
        changes_str = ", ".join(
            f"L{c['line']} {c['direction']}" for c in lc["changing_lines"]
        ) if lc["num_changes"] > 0 else "no change (same trigram)"
        lines.append(f"  {level.upper():>8}: {curr_t['ki']} {curr_t['symbol']} {curr_t['trigram']}"
                      f" → {next_t['ki']} {next_t['symbol']} {next_t['trigram']}"
                      f"  [{changes_str}]")
        lines.append(f"           Wu Xing: {lc['wu_xing']}")
        lines.append(f"           Changes: {lc['changes_at']}")
        lines.append("")
    for level in UPPER_LEVELS:
        lines.append(f"  {level.upper():>9}: {g['current'][level]} → {g['next'][level]}  Changes: {g['change_times'][level]}")
    lines.append("")

    lines.append("── HEXAGRAMS (level pairs) ──")
    for pair_key, hx in data["hexagrams"].items():
        lines.append(f"  {hx['pair']}")
        lines.append(f"    {hx['upper']['trigram']} (above)  Ki {hx['upper']['ki']}")
        lines.append(f"    {hx['lower']['trigram']} (below)  Ki {hx['lower']['ki']}")
        lines.append(f"    = Hexagram {hx['hexagram']}")
        lines.append(f"    Wu Xing: {hx['wu_xing']}")
        lines.append("")

    if data.get("personal"):
        p = data["personal"]
        lines.append("── PERSONAL KI CHANGES ──")
        lines.append(f"  CURRENT: {_stack_line(p['current'])}")
        lines.append(f"  NEXT:    {_stack_line(p['next'])}")
        lines.append("")

        for level in LEVEL_NAMES:
            if level not in p["level_changes"]:
                continue
            lc = p["level_changes"][level]
            curr_t = lc["current"]
            next_t = lc["next"]
            changes_str = ", ".join(
                f"L{c['line']} {c['direction']}" for c in lc["changing_lines"]
            ) if lc["num_changes"] > 0 else "no change"
            lines.append(f"  {level.upper():>8}: {curr_t['ki']} {curr_t['symbol']} {curr_t['trigram']}"
                          f" → {next_t['ki']} {next_t['symbol']} {next_t['trigram']}"
                          f"  [{changes_str}]")
        lines.append("")

        lines.append("  PERSONAL HEXAGRAMS:")
        for pair_key, hx in p["hexagrams"].items():
            lines.append(f"    {hx['pair']}: Hex {hx['hexagram']}"
                          f" ({hx['lower']['symbol']}/{hx['upper']['symbol']})"
                          f" — {hx['wu_xing']}")
        lines.append("")

    return "\n".join(lines)
