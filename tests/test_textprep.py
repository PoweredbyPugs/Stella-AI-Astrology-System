"""Tests for graph/textprep.py: extraction, chunking, frontmatter and entity tagging."""

import io
import zipfile

import pytest

from graph.textprep import (
    Section,
    chunk_text,
    detect_entities,
    extract_epub,
    html_to_paragraphs,
    looks_like_frontmatter,
    strip_running_lines,
)


# ── HTML → paragraphs ────────────────────────────────────────────────────────

def test_html_paragraph_breaks_survive():
    html = "<html><head><style>p{margin:0}</style><title>x</title></head><body>" \
           "<h1>Chapter One</h1><p>First   para\nwraps.</p><p>Second para.</p></body></html>"
    heading, paras = html_to_paragraphs(html)
    assert heading == "Chapter One"
    assert paras == ["Chapter One", "First para wraps.", "Second para."]


def test_style_and_script_content_is_dropped():
    html = "<body><style>svg {padding: 0pt}</style><script>var x=1;</script><p>Real text.</p></body>"
    _, paras = html_to_paragraphs(html)
    assert paras == ["Real text."]


def test_entities_are_unescaped_and_br_splits():
    html = "<body><p>Sun &amp; Moon<br/>second line</p></body>"
    _, paras = html_to_paragraphs(html)
    assert paras == ["Sun & Moon", "second line"]


# ── EPUB spine order ─────────────────────────────────────────────────────────

def _make_epub(docs: dict[str, str], spine: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        manifest = "".join(f'<item id="{n}" href="{n}" media-type="application/xhtml+xml"/>' for n in docs)
        itemrefs = "".join(f'<itemref idref="{n}"/>' for n in spine)
        z.writestr("OEBPS/content.opf",
                   '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf">'
                   f"<manifest>{manifest}</manifest><spine>{itemrefs}</spine></package>")
        for name, body in docs.items():
            z.writestr(f"OEBPS/{name}", body)
    return buf.getvalue()


def test_epub_follows_spine_not_alphabetical_order(tmp_path):
    docs = {
        "b.xhtml": "<body><h2>Chapter 2</h2><p>Second chapter text.</p></body>",
        "a.xhtml": "<body><h2>Chapter 1</h2><p>First chapter text.</p></body>",
    }
    path = tmp_path / "book.epub"
    path.write_bytes(_make_epub(docs, spine=["b.xhtml", "a.xhtml"]))
    sections = extract_epub(path)
    assert [s.heading for s in sections] == ["Chapter 2", "Chapter 1"]
    assert "Second chapter text." in sections[0].text
    assert "\n\n" in sections[0].text  # heading and body stay separate paragraphs


def test_epub_marks_copyright_page_as_frontmatter(tmp_path):
    docs = {
        "c.xhtml": "<body><p>Copyright © 2006 Someone. All rights reserved.</p><p>ISBN 978-0-452-28859-1</p></body>",
        "d.xhtml": "<body><h1>Introduction</h1><p>" + "Real prose about Saturn. " * 40 + "</p></body>",
    }
    path = tmp_path / "book.epub"
    path.write_bytes(_make_epub(docs, spine=["c.xhtml", "d.xhtml"]))
    sections = extract_epub(path)
    assert [s.frontmatter for s in sections] == [True, False]


# ── Chunking ─────────────────────────────────────────────────────────────────

def test_chunks_respect_max_size_even_for_one_giant_paragraph():
    giant = " ".join(f"Sentence number {i} talks about the Moon in Taurus." for i in range(2000))
    chunks = chunk_text(giant, max_chars=3200, overlap=200)
    assert len(chunks) > 20
    assert max(len(c) for c in chunks) <= 3200
    # Nothing is lost: every sentence index appears somewhere.
    joined = " ".join(chunks)
    assert "Sentence number 0 " in joined and "Sentence number 1999 " in joined


def test_chunks_split_on_paragraphs_when_possible():
    paras = [f"Paragraph {i}. " + "word " * 150 for i in range(10)]  # ~770 chars each
    chunks = chunk_text("\n\n".join(paras), max_chars=3200, overlap=200)
    assert all(len(c) <= 3200 for c in chunks)
    assert len(chunks) in (3, 4)
    # Each chunk after the first starts with overlap carried from the previous one.
    assert chunks[1].split()[0] == "word" or chunks[1].startswith("Paragraph")


def test_overlap_is_carried_between_chunks():
    text = "\n\n".join(f"Alpha{i} " + "x " * 600 for i in range(3))
    chunks = chunk_text(text, max_chars=1500, overlap=200)
    assert len(chunks) >= 2
    tail = chunks[0][-100:].split()[-1]
    assert tail in chunks[1][:300]


def test_short_text_is_one_chunk_and_empty_is_none():
    assert chunk_text("A short note on Venus.") == ["A short note on Venus."]
    assert chunk_text("   \n\n  ") == []


def test_text_without_spaces_is_hard_split():
    chunks = chunk_text("x" * 10000, max_chars=3200, overlap=200)
    assert max(len(c) for c in chunks) <= 3200
    assert sum(len(c) for c in chunks) >= 10000


# ── Frontmatter ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "VIKING Published by the Penguin Group. Copyright © Richard Tarnas, 2006. All rights reserved. ISBN 0-670-03292-1",
    "Library of Congress Cataloging-in-Publication Data. Printed in the United States of America.",
    "Contents\nIntroduction 1\nChapter One 13\nChapter Two 45\nChapter Three 77\nChapter Four 101\nNotes 300\nIndex 350",
])
def test_frontmatter_detected(text):
    assert looks_like_frontmatter(text)


def test_real_prose_mentioning_copyright_is_not_frontmatter():
    prose = ("The Saturn-Pluto cycle coincides with periods of contraction and crisis. " * 30
             + "He later wrote that he held the copyright to the idea.")
    assert not looks_like_frontmatter(prose)


# ── Running headers in PDFs ──────────────────────────────────────────────────

def test_running_headers_and_page_numbers_removed():
    body = "\n".join(f"Line {n} of ordinary prose about Ketu." for n in range(30))
    pages = [f"136 The Lunar Nodes - Crisis and Redemption\n{body}\nBody text on page {i} about Rahu.\n{body}\n{i}" for i in range(20)]
    cleaned = strip_running_lines(pages)
    assert all("Crisis and Redemption" not in p for p in cleaned)
    assert all(f"page {i} about Rahu" in p for i, p in enumerate(cleaned))
    assert all(p.strip().splitlines()[-1] != str(i) for i, p in enumerate(cleaned))


# ── Entity tagging ───────────────────────────────────────────────────────────

def test_detect_entities_maps_to_graph_ids():
    text = ("Saturn square the Moon from the tenth house; Mars in Capricorn trines Jupiter. "
            "The North Node and Rahu point forward. Zodiacal releasing from the Lot of Fortune. "
            "Annual profections reach the 7th house.")
    e = detect_entities(text)
    assert {"saturn", "moon", "mars", "jupiter", "north_node", "lot_fortune"} <= set(e["planets"])
    assert e["signs"] == ["capricorn"]
    assert set(e["houses"]) == {10, 7}
    assert {"square", "trine"} <= set(e["aspects"])
    assert {"zodiacal_releasing", "profections", "lots"} <= set(e["techniques"])


def test_lowercase_cancer_is_not_the_sign():
    assert detect_entities("He died of cancer.")["signs"] == []
    assert detect_entities("Mars in Cancer is in fall.")["signs"] == ["cancer"]


def test_section_dataclass_defaults():
    s = Section(heading=None, text="x")
    assert s.frontmatter is False


# ── Frontmatter regressions taken from real chunks (2026-10 rebuild) ────────

AGRIPPA_WEB_HEADER = (
    "Heinrich Cornelius Agrippa: Of Occult Philosophy, Book II. (part 4)\n"
    "This digital edition by Joseph H. Peterson, Copyright © 2000. All rights reserved.\n"
    "You will need a Hebrew font installed to read some of this book. Chap. xlvi. Of the Images of the\n"
    "Mansions of the Moon. Moreover they made Images for every Mansion of the Moon. In the first for the\n"
    "destruction of some one, they made in an Iron Ring the Image of a black man, in a garment of hair,\n"
    "and girdle, casting a small lance with his right hand. They sealed this in black wax, and perfumed it\n"
    "with liquid Storax, and wished some evil to come. In the second, against the wrath of the Prince,\n"
    "and for reconciliation with him, they sealed in white wax and mastick, the Image of a King crowned.\n"
)

PENGUIN_COPYRIGHT = (
    "VIKING\nPublished by the Penguin Group\nPenguin Group (USA) Inc., 375 Hudson Street, New York, New York 10014, U.S.A.\n"
    "Penguin Group (Canada), 90 Eglinton Avenue East, Suite 700, Toronto, Ontario, Canada M4P 2Y3\n"
    "Penguin Books Ltd, 80 Strand, London WC2R 0RL, England\nFirst published in 2006 by Viking Penguin.\n"
    "Copyright © Richard Tarnas, 2006\nAll rights reserved\nISBN: 1-4295-2245-2\n"
)

KI_YEAR_TABLE = "\n\n".join(
    f"Your {n} Years Are: 2028; 2019; 2010; 2001; 1992; 1983; 1974; 1965; 1956"
    for n in ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"])

BOOK_INDEX = "\n".join([
    "Manetho (astrologer), 40, 76, 106, 117, 145, Medium Coeli (MC). See Midheaven.",
    "159, 203, 223, 237, 261, 286-87, 391 melothesia, 2",
    "on interrogations, 58 unique/original, 60, 371-74",
    "joys and, 340 horoscopic astrology, xiii, 17-18, 22, 32-33,",
    "on lots, 70, 515, 525-28 38,",
    "Rudhyar, Dane, 134 conflict with gender, 198",
    "running in the void (kenodromia), 128, 345",
    "Sheen, Charlie, 550, 569-70, 600 striking with a ray (aktinobolia), 44, 80",
])

DOTTED_TOC = "\n".join(f"Moon in House {n} {'.' * 40} {20 + n}" for n in range(1, 13))

ZR_KEYWORDS = (
    "Zodiacal Releasing Keywords\nChris Brennan & Tom Pommerel\n"
    "1. Fortune Angles: periods of heightened activity and importance\n"
    "a. Major peak = 1st & 10th from Fortune\nb. Moderate peak = 7th from Fortune\n"
    "c. Minor peak = 4th from Fortune\n2. Angular Triads of Fortune\n"
    "a. 1st, 5th, 9th from Fortune: peak of the year 1\nb. 10th, 2nd, 6th from Fortune 2\n"
)


@pytest.mark.parametrize("text", [PENGUIN_COPYRIGHT, BOOK_INDEX, DOTTED_TOC])
def test_real_frontmatter_is_flagged(text):
    assert looks_like_frontmatter(text)


@pytest.mark.parametrize("text", [AGRIPPA_WEB_HEADER, KI_YEAR_TABLE, ZR_KEYWORDS])
def test_real_content_is_not_flagged(text):
    assert not looks_like_frontmatter(text)


# ── In-chapter headings (Haner styles headings as bold paragraphs, not <h*>) ──

HANER_CH3 = """<html><head><title>Your Hidden Symmetry</title></head><body>
<p class="cn"><a>CHAPTER 3</a></p>
<p class="ct"><a>Y<small>OUR</small> M<small>AIN</small><br/>P<small>ERSONALITY</small></a></p>
<p class="tx">Your first number reveals your overall personality. """ + "Intro sentence about numbers. " * 40 + """</p>
<p class="ttx1"><b><i><a>First Number: One<br/>Innovator</a></i></b></p>
<p class="tx">The image in nature for the One is water. """ + "One prose about flow and depth. " * 60 + """</p>
<p class="h3"><b>Inner Depth</b></p>
<p class="tx">""" + "You process things slowly and deeply. " * 60 + """</p>
<p class="ttx1"><b><i><a>First Number: Two<br/>Nurturer</a></i></b></p>
<p class="tx">The image in nature for the Two is earth. """ + "Two prose about caring for others. " * 60 + """</p>
<p class="h3"><b>Devotion to Others</b></p>
<p class="tx">""" + "You give and give to others. " * 60 + """</p>
</body></html>"""


def test_bold_subheadings_split_chapter_into_labelled_sections(tmp_path):
    path = tmp_path / "book.epub"
    path.write_bytes(_make_epub({"ch03.html": HANER_CH3}, spine=["ch03.html"]))
    sections = extract_epub(path)
    headings = [s.heading for s in sections]
    assert headings == ["CHAPTER 3", "CHAPTER 3 › First Number: One Innovator",
                        "CHAPTER 3 › First Number: Two Nurturer"]
    one = sections[1].text
    assert one.startswith("First Number: One Innovator")
    assert "Inner Depth" in one and "slowly and deeply" in one  # minor headings stay inline
    assert "Two prose" not in one


def test_non_bold_br_still_splits_paragraphs():
    _, paras = html_to_paragraphs("<body><p>Sun &amp; Moon<br/>second line</p></body>")
    assert paras == ["Sun & Moon", "second line"]
