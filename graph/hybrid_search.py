"""Hybrid retrieval over Interpretation nodes: full-text + vector, fused by rank.

Full-text (Lucene BM25) is good at exact names such as "Rohini" or "Valens";
vectors are good at meaning ("why do I keep repeating my mother's patterns").
Each retriever returns its own ranked list under the same structural filters,
and Reciprocal Rank Fusion merges them. When the embedding service is down or
the vector index is missing, search quietly degrades to full-text only.
"""

from __future__ import annotations

import re
import sys
from itertools import zip_longest
from typing import Callable

from graph.embeddings import VECTOR_INDEX, EmbeddingUnavailable, embed_query

FULLTEXT_INDEX = "interpretation_text"
RRF_K = 60

_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')

_PLANET_ALIASES = {
    "north node": "north_node", "northnode": "north_node", "rahu": "north_node",
    "south node": "south_node", "southnode": "south_node", "ketu": "south_node",
    "lot of fortune": "lot_fortune", "part of fortune": "lot_fortune", "fortune": "lot_fortune",
    "lot of spirit": "lot_spirit", "spirit": "lot_spirit",
}

Runner = Callable[..., list[dict]]


def escape_lucene(query: str) -> str:
    """Escape Lucene syntax so free text never raises a parse error."""
    escaped = _LUCENE_SPECIAL.sub(r"\\\1", query)
    # Bare boolean words would be read as operators.
    return re.sub(r"\b(AND|OR|NOT)\b", lambda m: m.group(1).lower(), escaped)


def normalize_planet(planet: str) -> str:
    key = planet.strip().lower().replace("_", " ")
    return _PLANET_ALIASES.get(key, key.replace(" ", "_"))


def build_filters(*, layer=None, trust_tier=None, planet=None, sign=None, house=None,
                  aspect=None, technique=None, tradition=None, author=None) -> tuple[list[str], dict]:
    """WHERE predicates on `i` plus their parameters. Frontmatter is always excluded."""
    preds = ["coalesce(i.frontmatter, false) = false"]
    params: dict = {}
    if layer:
        preds.append("EXISTS { (i)-[:IN_LAYER]->(:Layer {id: $f_layer}) }")
        params["f_layer"] = layer.strip().lower()
    if trust_tier is not None:
        preds.append("i.trust_tier = $f_tier")
        params["f_tier"] = int(trust_tier)
    if planet:
        preds.append("EXISTS { (i)-[:DESCRIBES]->(:Planet {id: $f_planet}) }")
        params["f_planet"] = normalize_planet(planet)
    if sign:
        preds.append("EXISTS { (i)-[:DESCRIBES]->(:Sign {id: $f_sign}) }")
        params["f_sign"] = sign.strip().lower()
    if house:
        preds.append("EXISTS { (i)-[:DESCRIBES]->(:House {number: $f_house}) }")
        params["f_house"] = int(str(house).strip().rstrip("stndrdth") or 0)
    if aspect:
        preds.append("EXISTS { (i)-[:DESCRIBES]->(:Aspect {id: $f_aspect}) }")
        params["f_aspect"] = aspect.strip().lower()
    if technique:
        preds.append("EXISTS { (i)-[:DESCRIBES]->(:Technique {id: $f_technique}) }")
        params["f_technique"] = technique.strip().lower().replace(" ", "_")
    if tradition:
        preds.append("toLower(i.tradition) = $f_tradition")
        params["f_tradition"] = tradition.strip().lower()
    if author:
        preds.append("EXISTS { MATCH (i)-[:AUTHORED_BY]->(au:Author) WHERE toLower(au.name) CONTAINS $f_author }")
        params["f_author"] = author.strip().lower()
    return preds, params


def synthesize_query(*, planet=None, sign=None, house=None, aspect=None, technique=None) -> str:
    """A natural-language query for filter-only calls such as interpret_placement."""
    parts = []
    if planet:
        parts.append(normalize_planet(planet).replace("_", " ").title())
    if aspect:
        parts.append(aspect.lower())
    if sign:
        parts.append(f"in {sign.title()}")
    if house:
        parts.append(f"in the {house} house")
    if technique:
        parts.append(technique.replace("_", " "))
    return " ".join(parts)


# ── Nine Star Ki notation ────────────────────────────────────────────────────
# Stella reads each Ki star through two books that never write "1 Water":
# Jean Haner (Your Hidden Symmetry) calls it "the One", and The Gnostic Book of
# Changes reads it as the Kan trigram, doubled in hexagram 29. Same Later Heaven
# mapping as octave.py; 5 is the centre and has no trigram.

_KI_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_KI_STARS = {
    1: dict(element="water", colour="white", images={"water"}, trigram="Kan", image="water", hexagram=29),
    2: dict(element="earth", colour="black", images={"earth"}, trigram="Kun", image="earth", hexagram=2),
    3: dict(element="wood", colour="jade", images={"wood", "tree", "thunder"}, trigram="Zhen", image="thunder", hexagram=51),
    4: dict(element="wood", colour="green", images={"wood", "tree", "wind"}, trigram="Xun", image="wind", hexagram=57),
    5: dict(element="earth", colour="yellow", images={"earth"}, trigram=None, image=None, hexagram=None),
    6: dict(element="metal", colour="white", images={"metal", "heaven"}, trigram="Qian", image="heaven", hexagram=1),
    7: dict(element="metal", colour="red", images={"metal", "lake"}, trigram="Dui", image="lake", hexagram=58),
    8: dict(element="earth", colour="white", images={"earth", "mountain"}, trigram="Gen", image="mountain", hexagram=52),
    9: dict(element="fire", colour="purple", images={"fire"}, trigram="Li", image="fire", hexagram=30),
}
_KI_RE = re.compile(
    r"\b(?P<num>[1-9]|" + "|".join(_KI_WORDS) + r")[\s-]*"
    r"(?:(?:white|black|jade|bright green|green|yellow|red|purple)\s+)?"
    r"(?P<image>water|earth|wood|tree|thunder|wind|metal|heaven|lake|mountain|fire)\b",
    re.I,
)
_GNOSTIC_TITLES: dict[int, str] | None = None


def _gnostic_title(hexagram: int) -> str:
    """Hexagram title as The Gnostic Book of Changes gives it, e.g. 29 -> "Danger"."""
    global _GNOSTIC_TITLES
    if _GNOSTIC_TITLES is None:
        try:
            import json
            from pathlib import Path
            path = Path(__file__).resolve().parent.parent / "data" / "gnostic.json"
            _GNOSTIC_TITLES = {h["number"]: h["title"] for h in json.loads(path.read_text())}
        except (OSError, ValueError, KeyError):
            _GNOSTIC_TITLES = {}
    return _GNOSTIC_TITLES.get(hexagram, "")


def ki_expansion(query: str) -> dict | None:
    """Recognise a Nine Star Ki star such as "1 water" or "9 purple fire"."""
    m = _KI_RE.search(query)
    if not m:
        return None
    raw = m.group("num").lower()
    number = int(raw) if raw.isdigit() else _KI_WORDS.index(raw) + 1
    star = _KI_STARS[number]
    if m.group("image").lower() not in star["images"]:
        return None
    rest = (query[:m.start()] + " " + query[m.end():]).strip()
    word = _KI_WORDS[number - 1].title()
    haner = f"First Number: {word}. The image in nature for the {word} is {star['element']}. {rest}".strip()
    gnostic = None
    if star["hexagram"]:
        title = _gnostic_title(star["hexagram"])
        gnostic = (f"Hexagram {star['hexagram']} {title}: {star['trigram']} over {star['trigram']}, "
                   f"the trigram of {star['image']}. {rest}").strip()
    return {"number": number, "hexagram": star["hexagram"], "haner_query": haner, "gnostic_query": gnostic}


def _interleave(*lists: list[dict], top: int) -> list[dict]:
    out, seen = [], set()
    for row in (r for group in zip_longest(*lists) for r in group if r):
        if row["chunk_id"] not in seen:
            seen.add(row["chunk_id"])
            out.append(row)
    return out[:top]


def rrf_fuse(*ranked_lists: list[str], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score(id) = sum over lists of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


_DETAILS = """
    UNWIND $ids AS id
    MATCH (i:Interpretation) WHERE elementId(i) = id
    OPTIONAL MATCH (i)-[:AUTHORED_BY]->(auth:Author)
    OPTIONAL MATCH (i)-[:IN_LAYER]->(ly:Layer)
    RETURN id, i.text AS text, head(collect(auth.name)) AS author, i.source_title AS title,
           i.trust_tier AS tier, head(collect(ly.id)) AS layer, i.tradition AS tradition,
           i.section AS section, i.chunk_id AS chunk_id
"""


def _log(msg: str) -> None:
    print(f"[hybrid_search] {msg}", file=sys.stderr, flush=True)


def search(run: Runner, query: str = "", *, top: int = 5, embed: Callable[[str], list[float]] = embed_query,
           **filters) -> list[dict]:
    """Ranked Interpretation rows for a query under structural filters.

    `run(cypher, **params)` executes Cypher and returns a list of dicts.
    """
    ki = ki_expansion(query) if query and not filters.get("tradition") else None
    if ki:
        haner = search(run, ki["haner_query"], top=top, embed=embed, **{**filters, "tradition": "9star_ki"})
        gnostic = (search(run, ki["gnostic_query"], top=top, embed=embed, **{**filters, "tradition": "iching"})
                   if ki["gnostic_query"] else [])
        rows = _interleave(haner, gnostic, top=top)
        if rows:
            return rows

    preds, params = build_filters(**filters)
    structural = len(preds) > 1
    if not query.strip():
        query = synthesize_query(**{k: filters.get(k) for k in ("planet", "sign", "house", "aspect", "technique")})
    where = " AND ".join(preds)
    pool = max(top * 8, 40)

    if not query.strip():  # no text and no ontology filter to phrase one from
        rows = run(f"MATCH (i:Interpretation) WHERE {where} "
                   "RETURN elementId(i) AS id ORDER BY i.trust_tier ASC, i.chunk_id LIMIT $n",
                   n=top, **params)
        return _details(run, [r["id"] for r in rows], {}, "structural")

    fulltext_ids: list[str] = []
    try:
        rows = run(f"""
            CALL db.index.fulltext.queryNodes('{FULLTEXT_INDEX}', $ftq, {{limit: $k}})
            YIELD node AS i, score WHERE {where}
            RETURN elementId(i) AS id ORDER BY score DESC LIMIT $n""",
                   ftq=escape_lucene(query), k=pool * 5 if structural else pool, n=pool, **params)
        fulltext_ids = [r["id"] for r in rows]
    except Exception as exc:  # malformed query or missing index
        _log(f"full-text failed: {exc}")

    vector_ids: list[str] = []
    try:
        qvec = embed(query)
        if structural:
            # Exact cosine over the filtered set: an approximate top-k from the index
            # can contain nothing that survives narrow filters.
            rows = run(f"""
                MATCH (i:Interpretation) WHERE {where} AND i.vec IS NOT NULL
                WITH i, vector.similarity.cosine(i.vec, $qvec) AS score
                RETURN elementId(i) AS id ORDER BY score DESC LIMIT $n""",
                       qvec=qvec, n=pool, **params)
        else:
            rows = run(f"""
                CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $k, $qvec)
                YIELD node AS i, score WHERE {where}
                RETURN elementId(i) AS id ORDER BY score DESC LIMIT $n""",
                       qvec=qvec, k=pool, n=pool, **params)
        vector_ids = [r["id"] for r in rows]
    except EmbeddingUnavailable as exc:
        _log(f"embedding service unavailable, full-text only: {exc}")
    except Exception as exc:
        _log(f"vector search failed, full-text only: {exc}")

    fused = rrf_fuse(fulltext_ids, vector_ids)[:top]
    if not fused:
        rows = run(f"MATCH (i:Interpretation) WHERE {where} AND toLower(i.text) CONTAINS $q "
                   "RETURN elementId(i) AS id ORDER BY i.trust_tier ASC LIMIT $n",
                   q=query.lower(), n=top, **params)
        return _details(run, [r["id"] for r in rows], {}, "contains")

    in_ft, in_vec = set(fulltext_ids), set(vector_ids)
    how = {i: ("hybrid" if i in in_ft and i in in_vec else "fulltext" if i in in_ft else "vector")
           for i, _ in fused}
    return _details(run, [i for i, _ in fused], dict(fused), how)


def _details(run: Runner, ids: list[str], scores: dict, how) -> list[dict]:
    if not ids:
        return []
    rows = {r["id"]: r for r in run(_DETAILS, ids=ids)}
    out = []
    for i in ids:
        if i in rows:
            row = dict(rows[i])
            row["score"] = round(scores.get(i, 0.0), 5)
            row["match"] = how if isinstance(how, str) else how.get(i)
            row["tags"] = None
            out.append(row)
    return out
