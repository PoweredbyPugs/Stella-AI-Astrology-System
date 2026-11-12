"""The packet: the deterministic half of every Octave reading.

One period at one level for one native: its figures, condition, flow, house, point and the six text sources.
A one-to-one port of the page's lib/forecast.js `packet`; the keys and their nesting are the page's, and the
pipelines index the packet by them. Spans are ISO strings in America/New_York (``end`` is None past the ephemeris).
"""
from datetime import datetime
from typing import Optional

import ki_solar
import octave_engine as E
import octave_ledger as L
from hub_inheritance import TRIGRAM_PINYIN
from octave import octave_reading


def book_text(n: Optional[int], lines: Optional[list], full: bool) -> Optional[str]:
    """The book's markdown for hexagram ``n`` (None when there is no figure or no reading)."""
    if not n:
        return None
    t = octave_reading(n, lines, full)
    return None if t.startswith("No reading") else t


def line_text(n: Optional[int], lines: Optional[list]) -> Optional[str]:
    """A line's text alone: the markdown after its "## Line n" heading."""
    t = book_text(n, lines, False)
    if not t:
        return None
    i = t.find("\n## Line ")
    return None if i < 0 else t[i + 1:]


def _hex(f: Optional[E.Figure]) -> Optional[dict]:
    if f is None:
        return None
    out = {"n": f.n, "name": f.name}
    if f.gnostic and f.gnostic != f.name:
        out["gnostic"] = f.gnostic
    out["upper"] = TRIGRAM_PINYIN[f.up.source]
    out["lower"] = TRIGRAM_PINYIN[f.lo.source]
    return out


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def packet(level: str, idx: int, natal: str) -> dict:
    """The packet for one period at a level, for a native born on ``natal`` (YYYY-MM-DD)."""
    if level not in E.LEVELS:
        raise ValueError(f"unknown level {level!r}")
    ni = E.natal_of(natal)
    p = E.period(level, idx, ni["year"])
    sh = E.shi(p)
    ba, nb = p.fig, sh["fig"]
    nat = E.native_figure(p, ni["month"])
    ne, pe = E.ELEMENT[ni["year"]], p.own.element
    up = E.upper(level)
    ce = E.resolve(p.stack, up).element if up else None
    cond, flow = E.relation(ne, pe), E.relation(pe, ce)
    ji = E.moving(ba.lines, nat.lines) if ba and nat else []
    shi_lines = sh["lines"] if ba and nb else []
    b = L.brief(p.number)
    condition = ({"native": ne, "field": pe, "relation": cond, "word": L.relation_word(cond),
                  "text": L.condition_text(ne, pe),
                  "statement": L.statement(b["q"], {"cond": cond, "ne": ne, "pe": pe})} if cond else None)
    flow_r = ({"field": pe, "container": ce, "containerLevel": up, "relation": flow, "word": L.flow_word(flow),
               "text": L.condition_text(pe, ce)} if flow else None)
    house = {"number": p.number, **L.house(p.number)}
    tend = L.tending(p.number)   # the earth points: 2 tends everything, 5 the self, 8 the one
    tend_short = f" This point {tend['text']}" if tend else ""
    tend_full = f"\nTending ({tend['scale']}): this point {tend['text']}" if tend else ""
    ground_short = [f"Condition, {condition['word']}: {condition['text']}" if condition else None,
                    f"Flow, {flow_r['word']}: {flow_r['text']}" if flow_r else None,
                    f"House {house['number']}, {house['dir']}: {house['line']}"]
    ground_full = [f"Condition: the person's {condition['native']} in the period's {condition['field']}, "
                   f"{condition['word']}. {condition['text']}" if condition else None,
                   f"Flow: the {flow_r['field']} {level} in a {flow_r['container']} {flow_r['containerLevel']}, "
                   f"{flow_r['word']}. {flow_r['text']}" if flow_r else None,
                   f"House {house['number']}, {house['dir']}: {house['line']}"]
    sources = {
        "ba": {"label": f"the period's figure, {ba.n} {ba.name}", "short": book_text(ba.n, [], False),
               "full": book_text(ba.n, [], True)} if ba else None,
        "ji": {"label": f"what the person meets: {ba.n} at line {', '.join(map(str, ji))}",
               "short": line_text(ba.n, ji), "full": line_text(ba.n, ji)} if ba and ji else None,
        "shi": {"label": f"what moves into the next period: {ba.n} at line {', '.join(map(str, shi_lines))}, "
                         f"becoming {nb.n} {nb.name}",
                "short": line_text(ba.n, shi_lines),
                "full": f"{line_text(ba.n, shi_lines)}\n\nWhere it lands: {book_text(nb.n, [], False)}",
                } if ba and nb and shi_lines else None,
        "native": {"label": f"the person's native figure, {nat.n} {nat.name}", "short": book_text(nat.n, [], False),
                   "full": book_text(nat.n, [], False)} if nat else None,
        "point": {"label": f"the point, {p.number} {b['name']}",
                  "short": f"{b['name']}. {b['fn']} {b['img']}{tend_short} Question: {b['q']}",
                  "full": f"{b['name']}. {b['fn']}\n{b['img']}\nShadow: {b['shadow']}\n"
                          f"Practice: {b['practice']}{tend_full}\nQuestion: {b['q']}"},
        "ground": {"label": "the condition, the flow and the house",
                   "short": "\n".join(x for x in ground_short if x), "full": "\n".join(x for x in ground_full if x)},
    }
    return {
        "level": level, "idx": idx, "natal": natal, "number": p.number, "global": p.global_number,
        "span": {"start": _iso(p.start), "end": _iso(p.end)},
        "point": {"name": b["name"], "question": b["q"], "image": b["img"], "practice": b["practice"]},
        "house": house, "tending": tend,
        "ba": _hex(ba), "inherited": p.own.inherited,
        "native": {**_hex(nat), "natalMonth": ni["month"]} if nat else None,
        "ji": ji,
        "shi": {"to": sh["to"], "ba": _hex(nb), "lines": shi_lines,
                "span": {"start": _iso(sh["start"]), "end": _iso(sh["end"])}},
        "condition": condition, "flow": flow_r, "sources": sources,
    }


def packet_at(level: str, dt: datetime, natal: str) -> dict:
    """The packet for the period at ``level`` containing ``dt`` (naive = America/New_York)."""
    if level not in E.LEVELS:
        raise ValueError(f"unknown level {level!r}")
    return packet(level, ki_solar.period_index(ki_solar.dt_to_jd(dt), level), natal)
