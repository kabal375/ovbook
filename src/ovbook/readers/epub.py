"""Structural EPUB reader.

Top-level TOC entry = chapter. Each chapter's XHTML is converted to markdown
(markdownify) and split into a chapter chunk + <h2>/<h3> subsection chunks.
Falls back to spine documents when there is no usable TOC.
"""

import re
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from markdownify import markdownify as md

from ovbook.readers.base import BookContent
from ovbook.split import Chunk, ChapterGroup

_H_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _to_markdown(html: str) -> str:
    """Convert an XHTML chapter document to markdown.

    Isolates <body> first so the XML declaration and <head> (title, styles,
    links) do not leak into the output. Falls back to the whole document if
    there is no <body>.
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    return md(str(body), heading_style="ATX", bullets="-", strip=["img"])


def _mk_sub(cur: dict) -> Chunk:
    return Chunk(
        heading=cur["heading"],
        content="\n".join(cur["lines"]).strip(),
        level=cur["level"],
    )


def _split_markdown_sections(markdown: str, toc_title: str):
    """Return (title, chapter_body, subsection_chunks) from a chapter's markdown."""
    title = toc_title or ""
    chapter_body: list[str] = []
    subs: list[Chunk] = []
    cur: dict | None = None

    for line in markdown.split("\n"):
        m = _H_RE.match(line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            if level == 1:
                if not title:
                    title = heading
                if cur is not None:
                    subs.append(_mk_sub(cur))
                    cur = None
                continue
            if cur is not None:
                subs.append(_mk_sub(cur))
            cur = {"heading": heading, "level": min(level, 3), "lines": []}
        else:
            if cur is not None:
                cur["lines"].append(line)
            else:
                chapter_body.append(line)

    if cur is not None:
        subs.append(_mk_sub(cur))

    return title.strip(), "\n".join(chapter_body).strip(), subs


def _html_to_group(html: str, toc_title: str, chapter_no: int) -> ChapterGroup:
    markdown = _to_markdown(html)
    title, body, subs = _split_markdown_sections(markdown, toc_title)
    if not title:
        title = f"Chapter {chapter_no}"
    chapter_chunk = Chunk(
        heading=title,
        content=body,
        level=1,
        chapter_no=chapter_no,
        chapter_title=title,
        sequence=0,
    )
    return ChapterGroup(chapter_no=chapter_no, chapter_title=title,
                        chunks=[chapter_chunk] + subs)


def _flatten_toc(toc) -> list[tuple[str, str]]:
    """Top-level (title, href) pairs. Nested entries become in-doc subsections."""
    out: list[tuple[str, str]] = []
    for entry in toc:
        if isinstance(entry, tuple):
            node = entry[0]
            href = getattr(node, "href", None)
            title = getattr(node, "title", None)
        else:
            href = getattr(entry, "href", None)
            title = getattr(entry, "title", None)
        if href:
            out.append((title or "", href))
    return out


def _groups_from_toc(book, entries) -> list[ChapterGroup]:
    groups: list[ChapterGroup] = []
    seen: set[str] = set()
    chapter_no = 0
    for title, href in entries:
        doc_href = href.split("#")[0]
        if doc_href in seen:
            continue
        seen.add(doc_href)
        item = book.get_item_with_href(doc_href)
        if item is None:
            continue
        chapter_no += 1
        html = item.get_content().decode("utf-8", errors="replace")
        groups.append(_html_to_group(html, title, chapter_no))
    return groups


def _groups_from_spine(book) -> list[ChapterGroup]:
    groups: list[ChapterGroup] = []
    chapter_no = 0
    for entry in book.spine:
        item_id = entry[0] if isinstance(entry, tuple) else entry
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        chapter_no += 1
        html = item.get_content().decode("utf-8", errors="replace")
        groups.append(_html_to_group(html, "", chapter_no))
    return groups


def _read_metadata(book, path: Path) -> dict:
    def first(name: str):
        vals = book.get_metadata("DC", name)
        return vals[0][0] if vals else None

    title = first("title") or path.stem
    authors = [v[0] for v in book.get_metadata("DC", "creator")]
    language = first("language") or "en"

    year = None
    date = first("date")
    if date:
        m = re.search(r"(\d{4})", date)
        if m:
            year = int(m.group(1))

    return {
        "id": _slugify(title),
        "title": title,
        "authors": authors,
        "language": language,
        "year": year,
        "source_format": "epub",
        "book_type": "technical",
    }


def read(path: Path) -> BookContent:
    """Parse an EPUB file into BookContent."""
    book = epub.read_epub(str(path))
    meta = _read_metadata(book, path)

    entries = _flatten_toc(book.toc)
    groups = _groups_from_toc(book, entries) if entries else _groups_from_spine(book)

    return BookContent(meta=meta, groups=groups)
