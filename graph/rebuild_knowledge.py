#!/usr/bin/env python3
"""Repair and re-embed Stella's knowledge graph (Interpretation nodes).

Steps, each idempotent and runnable on its own:

  backup           Export every Interpretation node and its edges to backups/*.jsonl.gz
  cleanup          Merge duplicate Layer nodes, fix "unknown" authors, delete blank orphan
                   nodes, trim the Sabian Pisces 30 node that swallowed the book's tail
  reingest         Re-extract books from source files with graph/textprep.py and replace
                   their chunks (BOOKS below; --source-dir holds one folder per slug)
  resplit          Split any remaining chunk longer than --max-chars in place
  tag              Add DESCRIBES edges to chunks that have none
  label-hexagrams  Label Gnostic Book of Changes chunks with their hexagram
  frontmatter      Flag copyright/contents/index chunks so search skips them
  embed            Embed chunks missing a vector for the current model (--url for Ollama)
  index            Create the vector index
  stats            Print a per-book summary

Run with the server venv from the repo root:
  .venv/bin/python -m graph.rebuild_knowledge backup
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from graph.embeddings import VECTOR_INDEX, document_text, embed_documents, embed_model
from graph.textprep import chunk_text, detect_entities, extract_any, looks_like_frontmatter
from stella_config import STELLA_DIR, open_neo4j_driver

INGEST_VERSION = "textprep-2026-10"
OVERSIZE_CHARS = 4000

LAYER_NAMES = {
    "reference": "Reference", "technical": "Technical", "psychological": "Psychological",
    "archetypal": "Archetypal", "philosophical": "Philosophical", "hermetic": "Hermetic",
    "vedic": "Vedic",
}

# Books whose chunks are rebuilt from source. `file` is a glob inside <source-dir>/<slug>/.
BOOKS = [
    dict(slug="cosmos_psyche", file="*.epub", title="Cosmos and Psyche: Intimations of a New World View",
         author="Richard Tarnas", tier=2, layer="archetypal", tradition="archetypal"),
    dict(slug="stars_beyond", file="*.epub", title="The Nakshatras: The Stars Beyond the Zodiac",
         author="Komilla Sutton", tier=1, layer="vedic", tradition="vedic"),
    dict(slug="authentic_self", file="*.epub", title="Astrology and the Authentic Self",
         author="Demetra George", tier=1, layer="technical", tradition="hellenistic"),
    dict(slug="healing_soul", file="*.epub", title="Healing the Soul: Pluto, Uranus and the Lunar Nodes",
         author="Mark Jones", tier=2, layer="psychological", tradition="modern_western"),
    dict(slug="hidden_symmetry", file="*.epub",
         title="Your Hidden Symmetry: How Your Birth Date Reveals the Plan for Your Life",
         author="Jean Haner", tier=2, layer="technical", tradition="9star_ki"),
    dict(slug="enoch", file="*.epub", title="The Book of Enoch",
         author="R.H. Charles (translator)", tier=1, layer="hermetic", tradition="judaic"),
    dict(slug="beautifully_rational", file="*.epub", title="The Beautifully Rational Philosophy of Astrology",
         author="Vic DiCara", tier=2, layer="vedic", tradition="vedic"),
    dict(slug="book_of_moon", file="*.pdf", title="The Book of the Moon",
         author="Steven Forrest", tier=2, layer="psychological", tradition="modern_western"),
    dict(slug="planets_in_youth", file="*.txt", title="Planets in Youth: Patterns of Early Development",
         author="Robert Hand", tier=2, layer="psychological", tradition="modern"),
]

# Chunks currently filed under Author "unknown" whose author is not in doubt.
AUTHOR_FIXES = {
    "36 Faces: The History, Astrology and Magic of the Decans": "Austin Coppock",
    "Anthology": "Vettius Valens",
    "Planets in Transit: Life Cycles for Living": "Robert Hand",
    "Planets in Houses: Experiencing Your Environment": "Robert Pelletier",
    "The Houses: Temples of the Sky": "Deborah Houlding",
    "How Astrology Works: Process-Relational Foundations with Whitehead, Jung, & Plato": "Kent Bye",
    "Astrology and the Authentic Self": "Demetra George",
    "Your Hidden Symmetry: How Your Birth Date Reveals the Plan for Your Life": "Jean Haner",
}

SABIAN_TITLE = "The Sabian Symbols in Astrology"
SABIAN_SPLIT = " part0023 "


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def batched(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


# ── backup ───────────────────────────────────────────────────────────────────

def cmd_backup(driver, args) -> None:
    out_dir = STELLA_DIR / "backups"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"knowledge-{datetime.now():%Y%m%d-%H%M%S}.jsonl.gz"
    count = 0
    with driver.session() as s, gzip.open(path, "wt", encoding="utf-8") as fh:
        result = s.run("""
            MATCH (i:Interpretation)
            RETURN elementId(i) AS eid, labels(i) AS labels,
                   properties(i) AS props,
                   [(i)-[r]->(x) | {type: type(r), props: properties(r), labels: labels(x),
                                    key: coalesce(x.id, x.name, x.number, x.chunk_id)}] AS out
        """)
        for rec in result:
            row = dict(rec)
            row["props"] = {k: v for k, v in row["props"].items() if k not in ("embedding", "vec")}
            fh.write(json.dumps(row, default=str) + "\n")
            count += 1
    log(f"backed up {count} Interpretation nodes to {path}")


# ── cleanup ──────────────────────────────────────────────────────────────────

def cmd_cleanup(driver, args) -> None:
    with driver.session() as s:
        deleted = s.run("""
            MATCH (n) WHERE size(labels(n)) = 0 AND size(keys(n)) = 0 AND NOT (n)--()
            DELETE n RETURN count(*) AS c""").single()["c"]
        log(f"deleted {deleted} blank orphan nodes")

        dups = s.run("MATCH (l:Layer) WHERE l.id IS NULL RETURN elementId(l) AS eid, l.name AS name").data()
        for d in dups:
            lid = (d["name"] or "").strip().lower()
            canon = s.run("MATCH (c:Layer {id: $lid}) RETURN elementId(c) AS eid", lid=lid).single()
            if canon:
                moved = s.run("""
                    MATCH (dup) WHERE elementId(dup) = $dup
                    MATCH (canon) WHERE elementId(canon) = $canon
                    MATCH (i)-[r:IN_LAYER]->(dup)
                    MERGE (i)-[:IN_LAYER]->(canon)
                    DELETE r RETURN count(*) AS c""", dup=d["eid"], canon=canon["eid"]).single()["c"]
                s.run("MATCH (dup) WHERE elementId(dup) = $dup DETACH DELETE dup", dup=d["eid"])
                log(f"layer '{d['name']}': moved {moved} chunks onto canonical Layer {{id: '{lid}'}}")
            else:
                s.run("MATCH (l) WHERE elementId(l) = $eid SET l.id = $lid, l.name = $name",
                      eid=d["eid"], lid=lid, name=LAYER_NAMES.get(lid, lid.title()))
                log(f"layer '{d['name']}': gave it id '{lid}'")

        for title, author in AUTHOR_FIXES.items():
            c = s.run("""
                MERGE (a:Author {name: $author})
                WITH a
                MATCH (i:Interpretation {source_title: $title})-[r:AUTHORED_BY]->(:Author {name: 'unknown'})
                MERGE (i)-[:AUTHORED_BY]->(a)
                DELETE r RETURN count(*) AS c""", title=title, author=author).single()["c"]
            if c:
                log(f"author: {c} chunks of '{title}' now credited to {author}")

        rec = s.run("""
            MATCH (sab:SabianSymbol {sign: 'Pisces', degree: 30})
            WHERE sab.text CONTAINS $marker
            RETURN elementId(sab) AS eid, sab.text AS text, sab.interpretation AS interp""",
                    marker=SABIAN_SPLIT).single()
        if rec:
            head, tail = rec["text"].split(SABIAN_SPLIT, 1)
            interp = (rec["interp"] or "").split(SABIAN_SPLIT, 1)[0]
            s.run("MATCH (n) WHERE elementId(n) = $eid SET n.text = $t, n.interpretation = $i",
                  eid=rec["eid"], t=head.strip(), i=interp.strip())
            book = dict(slug="sabian_tail", title=SABIAN_TITLE, author="Marc Edmund Jones",
                        tier=2, layer="reference", tradition="Sabian")
            chunks = [(None, c) for c in chunk_text(tail)]
            _write_chunks(s, book, chunks, source_file="graph:sabian-pisces30-tail")
            log(f"sabian: trimmed Pisces 30 from {len(rec['text'])} chars; tail kept as {len(chunks)} chunks")


# ── chunk writing ────────────────────────────────────────────────────────────

def _write_chunks(session, book: dict, chunks: list[tuple[str | None, str]], source_file: str,
                  start_index: int = 0, id_prefix: str | None = None) -> int:
    session.run("MERGE (a:Author {name: $name})", name=book["author"])
    session.run("MERGE (l:Layer {id: $id}) ON CREATE SET l.name = $name",
                id=book["layer"], name=LAYER_NAMES.get(book["layer"], book["layer"].title()))
    rows, edges = [], []
    prefix = id_prefix or book["slug"]
    for n, (section, text) in enumerate(chunks, start=start_index):
        cid = f"{prefix}_{n:04d}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        rows.append({"cid": cid, "props": {
            "text": text, "source_title": book["title"], "trust_tier": book["tier"],
            "tradition": book["tradition"], "layer": book["layer"], "chunk_index": n,
            "section": section, "source_file": source_file, "ingest_version": INGEST_VERSION,
            "frontmatter": looks_like_frontmatter(text)}})
        edges.extend(_entity_edges(cid, text))
    for batch in batched(rows, 200):
        session.run("""
            UNWIND $rows AS r
            MERGE (i:Interpretation {chunk_id: r.cid})
            SET i += r.props
            WITH i
            MATCH (a:Author {name: $author}), (l:Layer {id: $layer})
            MERGE (i)-[:AUTHORED_BY]->(a)
            MERGE (i)-[:IN_LAYER]->(l)""", rows=batch, author=book["author"], layer=book["layer"])
    _write_describes(session, edges)
    return len(rows)


def _entity_edges(cid: str, text: str) -> list[dict]:
    ents = detect_entities(text)
    edges = [{"cid": cid, "label": "Planet", "v": v} for v in ents["planets"]]
    edges += [{"cid": cid, "label": "Sign", "v": v} for v in ents["signs"]]
    edges += [{"cid": cid, "label": "House", "v": v} for v in ents["houses"]]
    edges += [{"cid": cid, "label": "Aspect", "v": v} for v in ents["aspects"]]
    edges += [{"cid": cid, "label": "Technique", "v": v} for v in ents["techniques"]]
    return edges


def _write_describes(session, edges: list[dict]) -> None:
    for label, key in (("Planet", "id"), ("Sign", "id"), ("House", "number"),
                       ("Aspect", "id"), ("Technique", "id")):
        subset = [e for e in edges if e["label"] == label]
        for batch in batched(subset, 1000):
            session.run(f"""
                UNWIND $edges AS e
                MATCH (i:Interpretation {{chunk_id: e.cid}})
                MATCH (t:{label} {{{key}: e.v}})
                MERGE (i)-[:DESCRIBES]->(t)""", edges=batch)


# ── reingest ─────────────────────────────────────────────────────────────────

def cmd_reingest(driver, args) -> None:
    source_dir = Path(args.source_dir)
    wanted = set(args.books or [])
    for book in BOOKS:
        if wanted and book["slug"] not in wanted:
            continue
        matches = sorted((source_dir / book["slug"]).glob(book["file"]))
        if not matches:
            log(f"SKIP {book['slug']}: no {book['file']} in {source_dir / book['slug']}")
            continue
        src = matches[0]
        sections = extract_any(src)
        chunks = [(sec.heading, c) for sec in sections if not sec.frontmatter for c in chunk_text(sec.text)]
        if not chunks:
            log(f"SKIP {book['slug']}: extraction produced no text")
            continue
        if args.dry_run:
            log(f"[dry-run] {book['title']}: {len(chunks)} chunks, max {max(len(c) for _, c in chunks)} chars")
            continue
        with driver.session() as s:
            old = s.run("""
                MATCH (i:Interpretation {source_title: $t}) WHERE NOT i:SabianSymbol
                WITH collect(i) AS nodes, count(i) AS c
                FOREACH (n IN nodes | DETACH DELETE n)
                RETURN c""", t=book["title"]).single()["c"]
            written = _write_chunks(s, book, chunks, source_file=src.name)
        log(f"{book['title']}: replaced {old} chunks with {written}")


# ── resplit ──────────────────────────────────────────────────────────────────

def cmd_resplit(driver, args) -> None:
    with driver.session() as s:
        nodes = s.run("""
            MATCH (i:Interpretation) WHERE size(i.text) > $max AND NOT i:SabianSymbol
            OPTIONAL MATCH (i)-[:AUTHORED_BY]->(a:Author)
            OPTIONAL MATCH (i)-[:IN_LAYER]->(l:Layer)
            RETURN i.chunk_id AS cid, i.text AS text, properties(i) AS props,
                   head(collect(a.name)) AS author, head(collect(l.id)) AS layer""",
                      max=args.max_chars).data()
        for node in nodes:
            props = node["props"]
            book = dict(slug=node["cid"], title=props.get("source_title"),
                        author=node["author"] or "unknown", tier=props.get("trust_tier", 4),
                        layer=node["layer"] or props.get("layer") or "reference",
                        tradition=props.get("tradition", ""))
            pieces = [(props.get("section"), c) for c in chunk_text(node["text"])]
            written = _write_chunks(s, book, pieces, source_file=props.get("source_file") or "resplit",
                                    id_prefix=f"{node['cid']}_r")
            s.run("MATCH (i:Interpretation {chunk_id: $cid}) DETACH DELETE i", cid=node["cid"])
            log(f"resplit {props.get('source_title')!r} {len(node['text'])} chars -> {written} chunks")
        log(f"resplit {len(nodes)} oversized chunks")


# ── tag / frontmatter ────────────────────────────────────────────────────────

def cmd_tag(driver, args) -> None:
    with driver.session() as s:
        rows = s.run("""
            MATCH (i:Interpretation)
            WHERE NOT i:SabianSymbol AND NOT EXISTS { (i)-[:DESCRIBES]->() } AND i.text IS NOT NULL
            RETURN i.chunk_id AS cid, i.text AS text""").data()
        edges = [e for r in rows for e in _entity_edges(r["cid"], r["text"])]
        _write_describes(s, edges)
    log(f"tagged {len(rows)} untagged chunks with {len(edges)} DESCRIBES edges")


def cmd_frontmatter(driver, args) -> None:
    with driver.session() as s:
        rows = s.run("""
            MATCH (i:Interpretation) WHERE NOT i:SabianSymbol AND i.text IS NOT NULL
            RETURN i.chunk_id AS cid, i.text AS text, i.source_title AS title""").data()
        sizes: dict[str, int] = {}
        for r in rows:
            sizes[r["title"]] = sizes.get(r["title"], 0) + 1
        # A source with only a handful of chunks is a handout or worksheet; keep all of it.
        flagged = [r for r in rows if sizes[r["title"]] >= 5 and looks_like_frontmatter(r["text"])]
        by_title: dict[str, int] = {}
        for r in flagged:
            by_title[r["title"]] = by_title.get(r["title"], 0) + 1
        for t, c in sorted(by_title.items(), key=lambda kv: -kv[1]):
            log(f"  {c:3} {t}")
        if args.dry_run:
            for r in flagged[:args.show]:
                log(f"  e.g. {r['title']}: {r['text'][:140]!r}")
            log(f"[dry-run] would flag {len(flagged)} of {len(rows)} chunks")
            return
        s.run("MATCH (i:Interpretation) WHERE i.frontmatter = true SET i.frontmatter = false")
        for batch in batched([r["cid"] for r in flagged], 1000):
            s.run("UNWIND $ids AS cid MATCH (i:Interpretation {chunk_id: cid}) SET i.frontmatter = true",
                  ids=batch)
    log(f"flagged {len(flagged)} of {len(rows)} chunks as frontmatter")


# ── hexagram labels ──────────────────────────────────────────────────────────

GNOSTIC_TITLE = "The Gnostic Book of Changes: Complete Hexagram Interpretations"
_HEX_HEADER = re.compile(r"(?m)^\s*(\d{1,2})\s*--\s*[^\n]{2,40}?\s*--\s*(\d{1,2})\s*$")


def cmd_label_hexagrams(driver, args) -> None:
    """Label Gnostic chunks with their hexagram from the PDF running headers ("29 -- Danger --29")."""
    hexes = {h["number"]: h for h in json.loads((STELLA_DIR / "data" / "gnostic.json").read_text())}
    with driver.session() as s:
        rows = s.run("MATCH (i:Interpretation {source_title: $t}) RETURN i.chunk_id AS cid, i.text AS text",
                     t=GNOSTIC_TITLE).data()
        updates = []
        for r in rows:
            counts: dict[int, int] = {}
            for m in _HEX_HEADER.finditer(r["text"]):
                if m.group(1) == m.group(2) and int(m.group(1)) in hexes:
                    counts[int(m.group(1))] = counts.get(int(m.group(1)), 0) + 1
            if not counts:
                continue
            nums = sorted(counts)
            labels = []
            for n in nums:
                h = hexes[n]
                alts = ", ".join(a.strip() for a in (h.get("otherTitles") or "").split(",")[:3] if a.strip())
                labels.append(f"Hexagram {n} {h['title']}" + (f" ({alts})" if alts else ""))
            updates.append({"cid": r["cid"], "section": " / ".join(labels), "hexagrams": nums})
        for batch in batched(updates, 500):
            s.run("""UNWIND $rows AS r MATCH (i:Interpretation {chunk_id: r.cid})
                     SET i.section = r.section, i.hexagrams = r.hexagrams, i.vec_model = 'stale'""", rows=batch)
    log(f"labelled {len(updates)} of {len(rows)} Gnostic chunks with their hexagram; run `embed` next")


# ── embed / index ────────────────────────────────────────────────────────────

def cmd_embed(driver, args) -> None:
    model = args.model or embed_model()
    with driver.session() as s:
        rows = s.run("""
            MATCH (i:Interpretation)
            WHERE i.text IS NOT NULL AND size(i.text) > 0
              AND (i.vec IS NULL OR coalesce(i.vec_model, '') <> $model)
            OPTIONAL MATCH (i)-[:AUTHORED_BY]->(a:Author)
            RETURN elementId(i) AS eid, i.text AS text, i.source_title AS title,
                   i.section AS section, head(collect(a.name)) AS author""", model=model).data()
    if args.limit:
        rows = rows[:args.limit]
    log(f"embedding {len(rows)} chunks with {model} via {args.url or 'default URL'}")
    started, done = time.time(), 0
    with driver.session() as s:
        for batch in batched(rows, args.batch):
            texts = [document_text(r["text"], r["title"], r["author"], r["section"]) for r in batch]
            vectors = embed_documents(texts, url=args.url, model=model)
            s.run("""
                UNWIND $rows AS r
                MATCH (i) WHERE elementId(i) = r.eid
                CALL db.create.setNodeVectorProperty(i, 'vec', r.v)
                SET i.vec_model = $model""",
                  rows=[{"eid": r["eid"], "v": v} for r, v in zip(batch, vectors)], model=model)
            done += len(batch)
            if done % (args.batch * 10) == 0 or done == len(rows):
                rate = done / max(1e-6, time.time() - started)
                log(f"  {done}/{len(rows)} ({rate:.1f} chunks/s)")


def cmd_index(driver, args) -> None:
    with driver.session() as s:
        dims = s.run("""MATCH (i:Interpretation) WHERE i.vec IS NOT NULL
                        RETURN size(i.vec) AS d LIMIT 1""").single()
        if not dims:
            sys.exit("no vectors yet; run `embed` first")
        s.run(f"""CREATE VECTOR INDEX {VECTOR_INDEX} IF NOT EXISTS
                  FOR (i:Interpretation) ON i.vec
                  OPTIONS {{indexConfig: {{`vector.dimensions`: {dims['d']},
                                           `vector.similarity_function`: 'cosine'}}}}""")
        log(f"vector index {VECTOR_INDEX} ready ({dims['d']} dims)")


def cmd_stats(driver, args) -> None:
    with driver.session() as s:
        rows = s.run("""
            MATCH (i:Interpretation)
            WITH i.source_title AS title, count(*) AS n, max(size(i.text)) AS max_len,
                 sum(CASE WHEN EXISTS { (i)-[:DESCRIBES]->() } THEN 1 ELSE 0 END) AS tagged,
                 sum(CASE WHEN i.vec IS NOT NULL THEN 1 ELSE 0 END) AS embedded,
                 sum(CASE WHEN i.frontmatter THEN 1 ELSE 0 END) AS front
            RETURN title, n, max_len, tagged, embedded, front ORDER BY title""").data()
    print(f"{'chunks':>6} {'max':>6} {'tagged':>6} {'vec':>6} {'front':>5}  title")
    for r in rows:
        print(f"{r['n']:6} {r['max_len'] or 0:6} {r['tagged']:6} {r['embedded']:6} {r['front']:5}  {r['title']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup")
    sub.add_parser("cleanup")
    p = sub.add_parser("reingest")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--books", nargs="*")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("resplit")
    p.add_argument("--max-chars", type=int, default=OVERSIZE_CHARS)
    sub.add_parser("tag")
    sub.add_parser("label-hexagrams")
    p = sub.add_parser("frontmatter")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--show", type=int, default=15)
    p = sub.add_parser("embed")
    p.add_argument("--url")
    p.add_argument("--model")
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--limit", type=int)
    sub.add_parser("index")
    sub.add_parser("stats")
    args = parser.parse_args()

    driver, _ = open_neo4j_driver()
    try:
        globals()[f"cmd_{args.cmd.replace('-', '_')}"](driver, args)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
