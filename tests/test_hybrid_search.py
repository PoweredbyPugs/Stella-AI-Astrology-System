"""Tests for graph/hybrid_search.py with a fake Cypher runner (no Neo4j needed)."""

from graph.embeddings import EmbeddingUnavailable
from graph.hybrid_search import (
    build_filters,
    escape_lucene,
    normalize_planet,
    rrf_fuse,
    search,
    synthesize_query,
)


def test_escape_lucene_neutralises_syntax():
    assert escape_lucene("Saturn-Pluto: AND (crisis)") == r"Saturn\-Pluto\: and \(crisis\)"


def test_rrf_rewards_items_found_by_both_retrievers():
    fused = rrf_fuse(["a", "b", "c"], ["c", "d", "a"])
    order = [i for i, _ in fused]
    assert order[0] in {"a", "c"} and set(order[:2]) == {"a", "c"}
    assert set(order) == {"a", "b", "c", "d"}


def test_filters_use_describes_edges_and_drop_frontmatter():
    preds, params = build_filters(planet="North Node", house="10th", aspect="Square",
                                  technique="zodiacal releasing", layer="Vedic")
    joined = " ".join(preds)
    assert "frontmatter" in preds[0]
    assert "INTERPRETS_HOUSE" not in joined and "tags" not in joined
    assert params == {"f_layer": "vedic", "f_planet": "north_node", "f_house": 10,
                      "f_aspect": "square", "f_technique": "zodiacal_releasing"}


def test_planet_aliases():
    assert normalize_planet("Rahu") == "north_node"
    assert normalize_planet("lot_fortune") == "lot_fortune"
    assert normalize_planet("Saturn") == "saturn"


def test_synthesized_query_for_placement_calls():
    assert synthesize_query(planet="saturn", sign="capricorn", house="10") == "Saturn in Capricorn in the 10 house"


class FakeRunner:
    def __init__(self, fulltext=(), vector=(), fail_fulltext=False):
        self.fulltext, self.vector, self.fail_fulltext = list(fulltext), list(vector), fail_fulltext
        self.calls = []

    def __call__(self, cypher, **params):
        self.calls.append((cypher, params))
        if "fulltext.queryNodes" in cypher:
            if self.fail_fulltext:
                raise RuntimeError("bad lucene")
            return [{"id": i} for i in self.fulltext]
        if "vector.queryNodes" in cypher or "vector.similarity.cosine" in cypher:
            return [{"id": i} for i in self.vector]
        if "UNWIND $ids" in cypher:
            return [{"id": i, "text": f"text {i}", "author": "A", "title": "T", "tier": 1,
                     "layer": "technical", "tradition": "x", "section": None, "chunk_id": i}
                    for i in params["ids"]]
        return []


def test_hybrid_merges_both_lists_and_labels_matches():
    run = FakeRunner(fulltext=["ft1", "both"], vector=["both", "v1"])
    rows = search(run, "Rohini", top=3, embed=lambda q: [0.1, 0.2])
    assert rows[0]["chunk_id"] == "both" and rows[0]["match"] == "hybrid"
    assert {r["match"] for r in rows[1:]} == {"fulltext", "vector"}


def test_embedding_outage_degrades_to_fulltext():
    def down(q):
        raise EmbeddingUnavailable("connection refused")
    run = FakeRunner(fulltext=["ft1", "ft2"])
    rows = search(run, "Saturn return", top=5, embed=down)
    assert [r["chunk_id"] for r in rows] == ["ft1", "ft2"]
    assert all(r["match"] == "fulltext" for r in rows)


def test_fulltext_error_still_returns_vector_hits():
    run = FakeRunner(vector=["v1"], fail_fulltext=True)
    rows = search(run, "Saturn: return", top=5, embed=lambda q: [0.0])
    assert [r["chunk_id"] for r in rows] == ["v1"]


def test_filtered_search_uses_exact_cosine_not_the_ann_index():
    run = FakeRunner(vector=["v1"])
    search(run, "career", planet="saturn", top=2, embed=lambda q: [0.0])
    cyphers = " ".join(c for c, _ in run.calls)
    assert "vector.similarity.cosine" in cyphers and "vector.queryNodes" not in cyphers


def test_filter_only_call_synthesizes_a_query():
    run = FakeRunner(fulltext=["ft1"])
    search(run, "", planet="moon", sign="taurus", top=1, embed=lambda q: [0.0])
    ft_params = next(p for c, p in run.calls if "fulltext.queryNodes" in c)
    assert ft_params["ftq"] == "Moon in Taurus"


# ── Nine Star Ki notation ────────────────────────────────────────────────────

from graph.hybrid_search import ki_expansion


def test_ki_notation_is_recognised_in_its_common_forms():
    for q in ["1 water", "1 White Water", "one water", "1-water", "my 1 water nature"]:
        ki = ki_expansion(q)
        assert ki and ki["number"] == 1 and ki["hexagram"] == 29, q
    assert ki_expansion("9 purple fire")["hexagram"] == 30
    assert ki_expansion("5 yellow earth")["hexagram"] is None  # the centre has no trigram


def test_numbers_that_do_not_match_the_element_are_not_ki():
    assert ki_expansion("1 fire") is None
    assert ki_expansion("water in the 4th house") is None
    assert ki_expansion("Saturn") is None


def test_ki_query_searches_both_ki_books_and_interleaves():
    calls = []

    def run(cypher, **params):
        calls.append(params)
        if "fulltext.queryNodes" in cypher:
            tradition = params.get("f_tradition")
            return [{"id": f"{tradition}-{n}"} for n in range(3)]
        if "UNWIND $ids" in cypher:
            return [{"id": i, "text": i, "author": "A", "title": i.split("-")[0], "tier": 1,
                     "layer": "x", "tradition": i.split("-")[0], "section": None, "chunk_id": i}
                    for i in params["ids"]]
        return []

    def down(q):
        raise EmbeddingUnavailable("off")

    rows = search(run, "1 water", top=4, embed=down)
    assert [r["tradition"] for r in rows] == ["9star_ki", "iching", "9star_ki", "iching"]
    ft_queries = [p["ftq"] for p in calls if "ftq" in p]
    assert any("One" in q for q in ft_queries) and any("29" in q for q in ft_queries)
