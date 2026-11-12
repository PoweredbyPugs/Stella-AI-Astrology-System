"""Seven deterministic Octave tools (no model in the loop): period, condition, native figure, shi, palace, point, line;
then three that write: forecast, statement, explain (Jev decides and grades, a writer model phrases; see octave_forecast).

Thin wrappers over octave_engine, octave_ledger and octave_packet. Times are America/New_York unless an offset is given.
The tool functions live at module level so stella_server can re-export them; register_octave_tools(mcp) registers them.
"""
import json
import os
from typing import Optional

import ki_solar
import octave_engine as E
import octave_forecast as F
import octave_ledger as L
import octave_packet as P

_LEVELS_MSG = "level must be one of " + ", ".join(E.LEVELS)


def _out(d) -> str:
    return json.dumps(d, ensure_ascii=False, indent=1)


def _err(msg) -> str:
    return json.dumps({"error": str(msg)}, ensure_ascii=False)


def _idx(level: str, datetime: Optional[str], idx: Optional[int]) -> int:
    if level not in E.LEVELS:
        raise ValueError(_LEVELS_MSG)
    if idx is not None:
        return int(idx)
    return ki_solar.period_index(ki_solar.dt_to_jd(ki_solar.parse_target(datetime)), level)


def _span(start, end) -> dict:
    return {"start": P._iso(start), "end": P._iso(end)}


def _shi(sh: dict) -> dict:
    return {"to": sh["to"], "ba": P._hex(sh["fig"]), "lines": sh["lines"], "span": _span(sh["start"], sh["end"])}


def _res(r: E.Resolved) -> dict:
    return {"ki": r.ki, "source": r.source, "element": r.element, "inherited": r.inherited}


def _house(n: int) -> dict:
    return {"number": n, **L.house(n)}


def _point(b: dict) -> dict:
    return {"name": b["name"], "question": b["q"], "image": b["img"], "practice": b["practice"]}


async def get_octave_period(level: str, datetime: Optional[str] = None, idx: Optional[int] = None,
                            natal: Optional[str] = None) -> str:
    """The Octave period at a level: its ba (figure), shi (next), house, point and palace; with a birth date, the personal packet with ji and sources.

    Args:
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; a bare date means local noon; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
        natal: birth date YYYY-MM-DD for the personal reading (ba, shi, ji); omit for the Global period
    """
    try:
        i = _idx(level, datetime, idx)
        if natal:
            d = P.packet(level, i, natal)
            d["palace"] = E.palace(d["global"], d["number"])
            return _out(d)
        p = E.period(level, i, None)
        return _out({"level": level, "idx": i, "number": p.number, "global": p.global_number,
                     "span": _span(p.start, p.end), "point": _point(L.brief(p.number)), "house": _house(p.number),
                     "tending": L.tending(p.number), "ba": P._hex(p.fig), "inherited": p.own.inherited,
                     "shi": _shi(E.shi(p)), "palace": E.palace(p.global_number, None)})
    except ValueError as e:
        return _err(e)


async def get_octave_condition(natal: str, level: str, datetime: Optional[str] = None,
                               idx: Optional[int] = None) -> str:
    """The condition (whose element sits in whose), the flow, the statement and the traditional sentence for a native in a period.

    Args:
        natal: birth date YYYY-MM-DD
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
    """
    try:
        d = P.packet(level, _idx(level, datetime, idx), natal)
        c = d["condition"]
        rel = {"cond": c["relation"], "ne": c["native"], "pe": c["field"]} if c else None
        q = L.brief(d["number"])["q"]
        return _out({"level": level, "idx": d["idx"], "number": d["number"], "condition": c, "flow": d["flow"],
                     "statement": L.statement(q, rel), "trad": L.trad(rel, level),
                     "trad_key": L.trad_key(rel, level)})
    except ValueError as e:
        return _err(e)


async def get_native_figure(natal: str, level: str, datetime: Optional[str] = None,
                            idx: Optional[int] = None) -> str:
    """The ba (the period's figure), the native figure and the ji lines where they differ, with the ba's text at those lines.

    Args:
        natal: birth date YYYY-MM-DD
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
    """
    try:
        d = P.packet(level, _idx(level, datetime, idx), natal)
        ba = d["ba"]
        return _out({"level": level, "idx": d["idx"], "ba": ba, "native": d["native"], "ji": d["ji"],
                     "text": P.line_text(ba["n"], d["ji"]) if ba and d["ji"] else None})
    except ValueError as e:
        return _err(e)


async def get_octave_shi(level: str, datetime: Optional[str] = None, idx: Optional[int] = None,
                         natal: Optional[str] = None) -> str:
    """The shi: what moves from this period's ba into the next period, the lines that change and the text at them.

    Args:
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
        natal: birth date YYYY-MM-DD for the personal sequence; omit for Global
    """
    try:
        i = _idx(level, datetime, idx)
        p = E.period(level, i, E.natal_of(natal)["year"] if natal else None)
        sh = E.shi(p)
        ba, nb = p.fig, sh["fig"]
        text = P.line_text(ba.n, sh["lines"]) if ba and nb and sh["lines"] else None
        return _out({"level": level, "idx": i, "ba": P._hex(ba), "shi": _shi(sh), "text": text,
                     "next": P.book_text(nb.n, [], False) if nb else None})
    except ValueError as e:
        return _err(e)


async def get_palace(level: str, datetime: Optional[str] = None, idx: Optional[int] = None,
                     natal: Optional[str] = None) -> str:
    """The Lo Shu palace of a period (nine cells, Five Yellow's home, the native's place) with its house and star.

    Args:
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
        natal: birth date YYYY-MM-DD to place the native; omit for Global
    """
    try:
        i = _idx(level, datetime, idx)
        p = E.period(level, i, E.natal_of(natal)["year"] if natal else None)
        d = E.palace(p.global_number, p.personal_number)
        return _out({"level": level, "idx": i, **d, "house": _house(p.number), "star": L.star(p.number)})
    except ValueError as e:
        return _err(e)


async def get_octave_point(number: int) -> str:
    """One point (1-9) of the Octave: its brief, what it tends, its family and, for 3, 6, 9, its Tri-force figure.

    Args:
        number: the point, 1 to 9
    """
    try:
        if number not in range(1, 10):
            raise ValueError("number must be 1 to 9")
        b = L.brief(number)
        f = E.triforce(number)
        return _out({"number": number, **b, "tending": L.tending(number), "family": b.get("family"),
                     "force": {"n": f.n, "name": f.name} if f else None})
    except ValueError as e:
        return _err(e)


async def get_octave_line(from_number: int, to_number: int, datetime: Optional[str] = None,
                          level: str = "day") -> str:
    """One of the six lines between points (verb, kind, title, lines, practice) and its figure; a 5 resolves on the stack at a datetime.

    Args:
        from_number: the origin point
        to_number: the destination point
        datetime: instant for resolving a 5 (ISO; America/New_York unless an offset is given)
        level: the level whose stack resolves a 5, default day
    """
    try:
        try:
            pr = L.pair(from_number, to_number)
        except KeyError:
            raise ValueError("not one of the six lines: " + ", ".join(sorted(L.load()["PAIRS"]))) from None
        five = 5 in (from_number, to_number)
        if five and datetime is None:
            raise ValueError("a line through 5 needs a datetime to resolve the 5")
        if level not in E.LEVELS:
            raise ValueError(_LEVELS_MSG)
        if datetime is not None:
            p = E.period_at(level, ki_solar.parse_target(datetime), None)
            fr, to = E.resolve({**p.gstack, level: from_number}, level), E.resolve({**p.gstack, level: to_number}, level)
        else:
            fr, to = E.resolve({"x": from_number}, "x"), E.resolve({"x": to_number}, "x")
        lf = E.line_figure(fr, to)
        fig = None
        if lf:
            fig = {**P._hex(lf["fig"]), "moving": lf["moving"], "base": P._hex(lf["base"]),
                   "inherited_from": lf["inherited_from"], "inherited_origin": lf["inherited_origin"]}
        return _out({"from": from_number, "to": to_number, **pr, "figure": fig,
                     "from_resolved": _res(fr), "to_resolved": _res(to)})
    except ValueError as e:
        return _err(e)


def _written(fn, level, datetime, idx, natal, **kw) -> str:
    try:
        i = _idx(level, datetime, idx)
        r = dict(fn(level, i, natal, data_dir=os.environ.get("DATA_DIR") or None, **kw))
        r.pop("system", None)
        return _out(r)
    except ValueError as e:
        return _err(e)


async def write_octave_forecast(natal: str, level: str, datetime: Optional[str] = None, idx: Optional[int] = None,
                                fresh: bool = False) -> str:
    """Write the forecast paragraph for a native in a period; Jev decides and grades, a writer model phrases; cached per period, fresh=True rewrites.

    Needs OPENROUTER_API_KEY and TYPESAFE_API_KEY on the server; FORECAST_MODEL and FORECAST_URL choose the writer.

    Args:
        natal: birth date YYYY-MM-DD
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
        fresh: write it again instead of returning the cached paragraph
    """
    return _written(F.forecast, level, datetime, idx, natal, fresh=fresh)


async def write_octave_statement(natal: str, level: str, datetime: Optional[str] = None, idx: Optional[int] = None,
                                 fresh: bool = False) -> str:
    """Write the thought under the headline for a native in a period; Jev decides and grades, a writer model phrases; cached per period, fresh=True rewrites.

    Needs OPENROUTER_API_KEY and TYPESAFE_API_KEY on the server; FORECAST_MODEL and FORECAST_URL choose the writer.

    Args:
        natal: birth date YYYY-MM-DD
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
        fresh: write it again instead of returning the cached thought
    """
    return _written(F.statement, level, datetime, idx, natal, fresh=fresh)


async def explain_octave_statement(natal: str, level: str, datetime: Optional[str] = None,
                                   idx: Optional[int] = None) -> str:
    """Write the reading of the written thought for a native in a period; Jev decides and grades, a writer model phrases; cached by the thought's text.

    Needs OPENROUTER_API_KEY and TYPESAFE_API_KEY on the server; FORECAST_MODEL and FORECAST_URL choose the writer. Returns 404 no_statement where no thought was written.

    Args:
        natal: birth date YYYY-MM-DD
        level: great_age, ki_age, great_year, year, month, day or hour
        datetime: instant to read (ISO; America/New_York unless an offset is given); default now
        idx: period index, wins over datetime
    """
    return _written(F.explain, level, datetime, idx, natal)


TOOLS = (get_octave_period, get_octave_condition, get_native_figure, get_octave_shi, get_palace,
         get_octave_point, get_octave_line, write_octave_forecast, write_octave_statement, explain_octave_statement)


def register_octave_tools(mcp) -> None:
    for fn in TOOLS:
        mcp.tool()(fn)
