"""Text preparation for knowledge-graph ingestion.

Extracts readable text from EPUB and PDF sources while keeping paragraph
structure, splits it into bounded chunks, flags frontmatter, and tags
astrological entities with the ids used by the graph's ontology nodes.

The 2025 ingest scripts collapsed every whitespace run inside each EPUB file,
which erased paragraph breaks, so whole chapters became single chunks. This
module is the replacement used by graph/rebuild_knowledge.py.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_CHUNK_CHARS = 3200
OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 100


@dataclass
class Section:
    heading: str | None
    text: str
    frontmatter: bool = False


# ── HTML → paragraphs ────────────────────────────────────────────────────────

_BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "blockquote",
    "section", "article", "header", "footer", "aside", "nav", "pre", "table", "tr",
    "td", "th", "dd", "dt", "dl", "figcaption", "figure", "hr", "body", "title",
}
_SKIP_TAGS = {"head", "style", "script", "svg", "math", "noscript"}
_HEADING_TAGS = {"h1", "h2", "h3"}


_LINE_BREAK = "\u2028"


@dataclass
class _Block:
    text: str
    style: tuple | None = None  # set when the block reads as a heading: short and all bold


class _ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[_Block] = []
        self.heading: str | None = None
        self._buf: list[str] = []
        self._skip_depth = 0
        self._in_heading = False
        self._heading_buf: list[str] = []
        self._bold_depth = 0
        self._italic_depth = 0
        self._block_style: tuple = ("", "")
        self._all_bold = True

    def _flush(self) -> None:
        raw = "".join(self._buf)
        parts = [" ".join(part.split()) for part in raw.split(_LINE_BREAK)]
        parts = [part for part in parts if part]
        if parts:
            joined = " ".join(parts)
            if self._all_bold and len(joined) <= 100 and not joined.endswith((".", ",", ";", ":")):
                self.blocks.append(_Block(joined, style=self._block_style + (self._italic_depth > 0,)))
            else:
                self.blocks.extend(_Block(part) for part in parts)
        self._buf = []
        self._all_bold = True

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self._buf.append(_LINE_BREAK)
        elif tag in _BLOCK_TAGS:
            self._flush()
            self._block_style = (tag, dict(attrs).get("class") or "")
        if tag in ("b", "strong"):
            self._bold_depth += 1
        elif tag in ("i", "em"):
            self._italic_depth += 1
        if tag in _HEADING_TAGS and self.heading is None:
            self._in_heading = True
            self._heading_buf = []

    def handle_startendtag(self, tag, attrs):
        if self._skip_depth:
            return
        if tag == "br":
            self._buf.append(_LINE_BREAK)
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in ("b", "strong"):
            self._bold_depth = max(0, self._bold_depth - 1)
        elif tag in ("i", "em"):
            self._italic_depth = max(0, self._italic_depth - 1)
        if tag in _BLOCK_TAGS:
            self._flush()
        if tag in _HEADING_TAGS and self._in_heading:
            self._in_heading = False
            heading = " ".join("".join(self._heading_buf).replace(_LINE_BREAK, " ").split())
            if heading:
                self.heading = heading

    def handle_data(self, data):
        if self._skip_depth:
            return
        self._buf.append(data)
        if data.strip() and self._bold_depth == 0:
            self._all_bold = False
        if self._in_heading:
            self._heading_buf.append(data)

    def close(self):
        super().close()
        self._flush()


def html_to_blocks(html: str) -> tuple[str | None, list[_Block]]:
    """Return (first h1-h3 heading, blocks) for one XHTML document."""
    parser = _ParagraphParser()
    parser.feed(html)
    parser.close()
    return parser.heading, parser.blocks


def html_to_paragraphs(html: str) -> tuple[str | None, list[str]]:
    """Return (first h1-h3 heading, paragraphs) for one XHTML document."""
    heading, blocks = html_to_blocks(html)
    return heading, [b.text for b in blocks]


def _split_style(blocks: list[_Block], min_avg_chars: int = 1200) -> tuple | None:
    """The bold-heading style that marks a file's main subdivisions, if it has any.

    Rarer styles rank higher (a book has fewer "First Number: One" headings than
    "Inner Depth" ones). A style qualifies when it occurs at least twice and
    splitting on it leaves sections of useful size.
    """
    counts: dict[tuple, int] = {}
    for b in blocks:
        if b.style:
            counts[b.style] = counts.get(b.style, 0) + 1
    total = sum(len(b.text) for b in blocks)
    for style, n in sorted(counts.items(), key=lambda kv: kv[1]):
        if n >= 2 and total / (n + 1) >= min_avg_chars:
            return style
    return None


# ── EPUB ─────────────────────────────────────────────────────────────────────

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _natural_key(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _epub_spine(z: zipfile.ZipFile) -> list[str]:
    """Zip member names of the content documents in reading order."""
    try:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        opf_path = next(el.get("full-path") for el in container.iter() if _local(el.tag) == "rootfile")
        opf = ET.fromstring(z.read(opf_path))
        base = posixpath.dirname(opf_path)
        manifest = {}
        for el in opf.iter():
            if _local(el.tag) == "item":
                manifest[el.get("id")] = el.get("href")
        order = []
        for el in opf.iter():
            if _local(el.tag) == "itemref" and el.get("idref") in manifest:
                href = manifest[el.get("idref")].split("#", 1)[0]
                order.append(posixpath.normpath(posixpath.join(base, href)))
        names = set(z.namelist())
        order = [n for n in order if n in names]
        if order:
            return order
    except (KeyError, StopIteration, ET.ParseError):
        pass
    docs = [n for n in z.namelist() if n.lower().endswith((".html", ".xhtml", ".htm"))]
    return sorted(docs, key=_natural_key)


def extract_epub(path: Path | str) -> list[Section]:
    sections: list[Section] = []
    with zipfile.ZipFile(path) as z:
        for position, name in enumerate(_epub_spine(z)):
            raw = z.read(name).decode("utf-8", errors="replace")
            heading, blocks = html_to_blocks(raw)
            if not blocks:
                continue
            text = "\n\n".join(b.text for b in blocks)
            if heading is None and len(blocks[0].text) <= 80:
                heading = blocks[0].text  # chapter titles styled as <p class="...">
            # Title and half-title pages near the front: a few short lines, no sentences.
            title_page = position < 6 and len(text) < 400 and text.count(". ") == 0
            if title_page or looks_like_frontmatter(text, heading):
                sections.append(Section(heading=heading, text=text, frontmatter=True))
                continue
            split = _split_style(blocks)
            groups: list[tuple[str | None, list[str]]] = [(heading, [])]
            for b in blocks:
                if split and b.style == split:
                    label = f"{heading} › {b.text}" if heading else b.text
                    groups.append((label, [b.text]))
                else:
                    groups[-1][1].append(b.text)
            for label, paras in groups:
                if paras:
                    sections.append(Section(heading=label, text="\n\n".join(paras)))
    return sections


# ── PDF ──────────────────────────────────────────────────────────────────────

def _norm_line(line: str) -> str:
    return re.sub(r"\d+", "#", " ".join(line.split())).strip().lower()


def _edge_indexes(lines: list[str], depth: int = 2) -> set[int]:
    """Indexes of the first and last `depth` non-empty lines of a page."""
    filled = [i for i, ln in enumerate(lines) if ln.strip()]
    return set(filled[:depth] + filled[-depth:])


def strip_running_lines(pages: list[str], min_share: float = 0.3) -> list[str]:
    """Drop running headers/footers and bare page numbers from PDF pages.

    Only the first and last two lines of a page are candidates, so body text
    that happens to repeat is never removed.
    """
    split_pages = [page.splitlines() for page in pages]
    counts: dict[str, int] = {}
    for lines in split_pages:
        seen = set()
        for i in _edge_indexes(lines):
            key = _norm_line(lines[i])
            if key and len(key) <= 90 and key not in seen:
                seen.add(key)
                counts[key] = counts.get(key, 0) + 1
    threshold = max(3, int(len(pages) * min_share))
    running = {k for k, c in counts.items() if c >= threshold}
    cleaned = []
    for lines in split_pages:
        edges = _edge_indexes(lines)
        keep = []
        for i, line in enumerate(lines):
            key = _norm_line(line)
            if i in edges and key and (key in running or re.fullmatch(r"[#\s\-–—ivxlc.]*", key)):
                continue
            keep.append(line)
        cleaned.append("\n".join(keep))
    return cleaned


def _join_pdf_lines(text: str) -> str:
    """Join wrapped lines inside paragraphs; keep blank-line paragraph breaks."""
    text = re.sub(r"(\w)-\n(?=[a-z])", r"\1", text)  # de-hyphenate line wraps
    paras = re.split(r"\n\s*\n", text)
    return "\n\n".join(" ".join(p.split()) for p in paras if p.strip())


def extract_pdf(path: Path | str) -> list[Section]:
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"],
                         capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    return pages_to_sections(out.split("\f"))


def extract_paged_text(path: Path | str) -> list[Section]:
    """Plain text with form feeds between pages, e.g. OCR output of a scanned book."""
    return pages_to_sections(Path(path).read_text(encoding="utf-8", errors="replace").split("\f"))


def pages_to_sections(raw_pages: list[str]) -> list[Section]:
    pages = strip_running_lines(raw_pages)
    sections: list[Section] = []
    for page in pages:
        text = _join_pdf_lines(page)
        if not text:
            continue
        sections.append(Section(heading=None, text=text, frontmatter=looks_like_frontmatter(page)))
    # Merge consecutive body pages so paragraphs that cross a page boundary chunk together.
    merged: list[Section] = []
    for s in sections:
        if merged and not s.frontmatter and not merged[-1].frontmatter:
            merged[-1].text += "\n\n" + s.text
        else:
            merged.append(s)
    return merged


def extract_any(path: Path | str) -> list[Section]:
    suffix = Path(path).suffix.lower()
    if suffix == ".epub":
        return extract_epub(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".txt":
        return extract_paged_text(path)
    raise ValueError(f"Unsupported source type: {suffix}")


# ── Frontmatter ──────────────────────────────────────────────────────────────

_FRONT_PATTERNS = [
    r"copyright\s*©|©\s*\d{4}|\bcopyright\s+\d{4}", r"all rights reserved", r"\bisbn\b",
    r"library of congress", r"cataloging[- ]in[- ]publication", r"printed in (the )?(united states|great britain|canada|india)",
    r"^praise for\b", r"^also by\b", r"no part of this (book|publication) may be reproduced",
    r"please purchase only authorized electronic editions",
]
_BACKMATTER_HEADINGS = re.compile(r"^(index|bibliography|works cited|select bibliography|contents|table of contents)\b", re.I)


_PAGE_REF = r"(?:[ivxlc]+|\d{1,4})(?:[-–]\d{1,4})?(?:n\d+)?(?:fig\.)?"
_TOC_LINE = re.compile(r"(\.{3,}|\(cid:9\)|\t)\s*" + _PAGE_REF + r"\s*$", re.I)
_INDEX_LINE = re.compile(r",\s*" + _PAGE_REF + r"(?:,\s*" + _PAGE_REF + r")+", re.I)


def _listy_share(text: str) -> float:
    """Share of lines that look like table-of-contents or back-of-book index entries.

    TOC lines end in dot leaders or tabs then a page number; index lines carry two or
    more comma-separated page references. Data tables (years separated by semicolons,
    numbered keyword lists) match neither.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 6:
        return 0.0
    hits = sum(1 for ln in lines if _TOC_LINE.search(ln) or _INDEX_LINE.search(ln))
    return hits / len(lines)


_NOTICE = re.compile(
    r"copyright|©|all rights reserved|\bisbn\b|library of congress|cataloging[- ]in[- ]publication"
    r"|no part of this|published (by|in)\b|printed in|https?://|www\.", re.I)


_SENTENCE_BREAK = re.compile(r"[a-z]{2}[.!?][\"”’)]?\s+[A-Z“\"]")


def _has_prose_block(text: str, min_chars: int = 350) -> bool:
    """True if some run of consecutive lines free of publishing notices reads as prose."""
    block: list[str] = []
    blocks: list[str] = []
    for line in text.splitlines():
        if not line.strip() or _NOTICE.search(line):
            if block:
                blocks.append(" ".join(block))
            block = []
        else:
            block.append(line.strip())
    if block:
        blocks.append(" ".join(block))
    for b in blocks:
        digits = sum(ch.isdigit() for ch in b) / max(1, len(b))
        if len(b) >= min_chars and len(_SENTENCE_BREAK.findall(b)) >= 2 and digits < 0.06:
            return True
    return False


_STRONG_FRONT = re.compile(
    r"\A\s*(praise for|(also|other books) by)\b|all rights reserved|\bisbn\b|library of congress"
    r"|cataloging[- ]in[- ]publication|no part of this (book|publication) may be reproduced", re.I)


def looks_like_frontmatter(text: str, heading: str | None = None) -> bool:
    """Copyright pages, tables of contents, praise pages, and back-of-book indexes."""
    if heading and _BACKMATTER_HEADINGS.match(heading.strip()):
        return True
    if _listy_share(text) > 0.4 and not _has_prose_block(text):
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines and _BACKMATTER_HEADINGS.match(lines[0]) and not _has_prose_block(text):
        numbered = sum(1 for ln in lines[1:] if re.search(r"\s" + _PAGE_REF + r"$", ln, re.I))
        if numbered >= max(3, len(lines[1:]) // 2):
            return True
    if len(text) > 4000 or _has_prose_block(text):
        return False
    notice_chars = sum(len(ln) for ln in lines if _NOTICE.search(ln))
    if len(text) > 600 and notice_chars / len(text) < 0.15:
        return False  # a web-edition notice line on top of real content
    if _STRONG_FRONT.search(text):
        return True
    lower = text.lower()
    hits = sum(1 for p in _FRONT_PATTERNS if re.search(p, lower, re.M))
    return hits >= 2 or (hits == 1 and len(text) < 1500)


# ── Chunking ─────────────────────────────────────────────────────────────────

_SENTENCE_END = re.compile(r"(?<=[.!?;:…\"”’)\]])\s+")


def _split_long(paragraph: str, limit: int) -> list[str]:
    """Split one paragraph into pieces no longer than limit, preferring sentence ends."""
    if len(paragraph) <= limit:
        return [paragraph]
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(paragraph):
        while len(sentence) > limit:  # a run-on sentence or text without punctuation
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            head, sentence = sentence[:cut].rstrip(), sentence[cut:].lstrip()
            if current:
                pieces.append(current)
                current = ""
            pieces.append(head)
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        pieces.append(current)
    return pieces


def _tail(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return "" if overlap <= 0 else text
    tail = text[-overlap:]
    space = tail.find(" ")
    return tail[space + 1:] if 0 <= space < overlap // 2 else tail


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP_CHARS,
               min_chars: int = MIN_CHUNK_CHARS) -> list[str]:
    """Pack paragraphs into chunks of at most max_chars, carrying a word-aligned overlap."""
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    piece_limit = max(200, max_chars - overlap - 2)
    pieces: list[str] = []
    for para in paragraphs:
        pieces.extend(_split_long(para, piece_limit))

    chunks: list[str] = []
    current = ""
    fresh = True  # True while current holds only carried-over overlap
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= max_chars:
            current, fresh = candidate, False
            continue
        if current and not fresh:
            chunks.append(current)
        carry = _tail(current, overlap) if current and not fresh else ""
        current = f"{carry}\n\n{piece}" if carry else piece
        if len(current) > max_chars:
            current = piece
        fresh = False
    if current and not fresh:
        if chunks and len(current) < min_chars and len(chunks[-1]) + len(current) + 2 <= max_chars:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)
    return chunks


# ── Entity tagging (ids match Planet/Sign/House/Aspect/Technique nodes) ──────

_PLANETS = {
    "sun": r"\bsun\b|\bsolar\b", "moon": r"\bmoon\b|\blunar\b", "mercury": r"\bmercury\b",
    "venus": r"\bvenus\b", "mars": r"\bmars\b", "jupiter": r"\bjupiter\b", "saturn": r"\bsaturn\b",
    "uranus": r"\buranus\b", "neptune": r"\bneptune\b", "pluto": r"\bpluto\b",
    "north_node": r"\bnorth node\b|\brahu\b|\bascending node\b",
    "south_node": r"\bsouth node\b|\bketu\b|\bdescending node\b",
    "lot_fortune": r"\b(lot|part) of fortune\b", "lot_spirit": r"\b(lot|part) of spirit\b",
}
_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
             "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}
_HOUSE_RE = re.compile(r"\b(?:(1[0-2]|[1-9])(?:st|nd|rd|th)|(" + "|".join(_ORDINALS) + r"))[- ]house\b", re.I)
_ASPECTS = {
    "conjunction": r"\bconjunct(ion|s|ing)?\b", "sextile": r"\bsextil(e|es|ing)\b",
    "square": r"\bsquar(e|es|ing)\b", "trine": r"\btrin(e|es|ing)\b",
    "opposition": r"\bopposition\b|\bopposes\b|\bopposing\b",
}
_TECHNIQUES = {
    "zodiacal_releasing": r"\bzodiacal releasing\b", "profections": r"\bprofection",
    "essential_dignities": r"\bessential dignit|\bdomicile\b|\bexaltation\b|\bdetriment\b",
    "sect": r"\bsect\b", "lots": r"\b(lot|lots|part) of\b|\barabic parts?\b",
    "transits": r"\btransit(s|ing|ed)?\b", "synastry": r"\bsynastry\b",
    "houses": r"\bhouse rul|\bruler of the \w+ house\b", "depositors": r"\bdepositor",
}
_ASPECT_CONTEXT = re.compile("|".join(_PLANETS.values()), re.I)


def detect_entities(text: str) -> dict[str, list]:
    lower = text.lower()
    planets = [pid for pid, pat in _PLANETS.items() if re.search(pat, lower)]
    signs = [s.lower() for s in _SIGNS if re.search(rf"\b{s}\b", text)]
    houses = sorted({int(m.group(1)) if m.group(1) else _ORDINALS[m.group(2).lower()]
                     for m in _HOUSE_RE.finditer(text)})
    aspects = []
    if _ASPECT_CONTEXT.search(text):  # "square" and "trine" are only aspects near planets
        aspects = [aid for aid, pat in _ASPECTS.items() if re.search(pat, lower)]
    techniques = [tid for tid, pat in _TECHNIQUES.items() if re.search(pat, lower)]
    return {"planets": planets, "signs": signs, "houses": houses,
            "aspects": aspects, "techniques": techniques}
