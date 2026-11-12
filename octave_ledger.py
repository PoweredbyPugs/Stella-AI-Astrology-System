"""Octave ledger access and the composed reading text.

The tables come from data/octave_ledger.json, dumped verbatim from the Octave
Calendar page by scripts/export_octave_ledger.sh; the text is not edited here.
statement, trad and trad_key port STATEMENT, TRAD and TRAD_KEY from the page's
src/briefs.js.
"""
import functools
import json
import os
import re
from pathlib import Path
from typing import Optional

from octave_engine import LABEL


@functools.lru_cache(maxsize=None)
def load() -> dict:
    """The whole ledger dump (cached)."""
    path = os.environ.get("OCTAVE_LEDGER_JSON") or Path(__file__).parent / "data" / "octave_ledger.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def brief(n: int) -> dict:
    return load()["BRIEF"][str(n)]


def tending(n: int) -> Optional[dict]:
    return load()["TENDING"].get(str(n))


def house(n: int) -> dict:
    return load()["HOUSES"][str(n)]


def star(n: int) -> str:
    return load()["STAR"][str(n)]


def pair(from_n: int, to_n: int) -> dict:
    """One of the six lines; KeyError for any other pair."""
    key = f"{from_n}>{to_n}"
    p = load()["PAIRS"][key]
    return {"verb": load()["VERB"][key], "title": p["title"], "kind": p["kind"], "lines": p["lines"],
            "practice": p["practice"], "hex": p["hex"], "shadows": p["shadows"]}


def condition_text(actor: str, field: str) -> str:
    """CONDITION[actor][field], the reading of a native element in a period element."""
    return load()["CONDITION"][actor][field]


def _cond(rel) -> str:
    return rel["cond"] if isinstance(rel, dict) else rel


def relation_word(rel) -> str:
    return load()["RELATION_WORD"][_cond(rel)]


def flow_word(rel) -> str:
    return load()["FLOW_WORD"][_cond(rel)]


def _an(w: str) -> str:
    return ("an " if re.match(r"[aeiou]", w, re.I) else "a ") + w


def _open(rel: dict, level: str) -> str:
    level = LABEL.get(level, level)
    return f"Your {rel['ne'].lower()} in {_an(rel['pe'].lower())} {level}"


def trad_key(rel: Optional[dict], level: str) -> str:
    """The opening alone: "Your earth in an earth hour."."""
    return f"{_open(rel, level)}." if rel and rel.get("cond") and rel.get("ne") and rel.get("pe") else ""


def trad(rel: Optional[dict], level: str) -> str:
    """The quiet sentence: the opening, then the reading's image as its clause unless it only restates the pair."""
    if not rel or not rel.get("cond"):
        return ""
    text = load()["CONDITION"].get(rel["ne"], {}).get(rel["pe"])
    if not text:
        return ""
    ne, pe = rel["ne"].lower(), rel["pe"].lower()
    m = re.search(r"(?<=\.)\s", text)
    image, rest = (text, "") if not m else (text[:m.start()], text[m.start() + 1:])
    bare = len(image.split(" ")) <= 4 and re.search(rf"^{re.escape(ne)}\b.*\b{re.escape(pe)}\.$", image, re.I) is not None
    op = _open(rel, level)
    return (f"{op}. {rest}" if bare else f"{op}: {image[:1].lower()}{image[1:]} {rest}").strip()


def statement(q: str, rel: Optional[dict]) -> str:
    """The question with the condition clause before its final ? or ."""
    if not rel or not rel.get("cond"):
        return q
    clause = load()["COND_CLAUSE"].get(rel["ne"], {}).get(rel["pe"])
    if not clause:
        return q
    end = "?" if re.search(r"\?\s*$", q) else "."
    base = re.sub(r"[?.]\s*$", "", q)
    return f"{base}, {clause}{end}"
