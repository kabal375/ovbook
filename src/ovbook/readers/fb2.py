"""Structural FB2 reader.

Top-level <section> = chapter, nested <section> = subsection.
Inline FB2 markup (emphasis/strong/code) is converted to markdown.
No external dependencies — stdlib ElementTree only.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ovbook.readers.base import BookContent
from ovbook.split import Chunk, ChapterGroup

NS = "{http://www.gribuser.ru/xml/fictionbook/2.0}"


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9\u0430-\u044f]+", "-", text.lower()).strip("-")


def _inline_text(el: ET.Element) -> str:
    """Render an element's inline content to markdown (recursive)."""
    out = [el.text or ""]
    for child in el:
        tag = _local(child.tag)
        inner = _inline_text(child)
        if tag == "emphasis":
            inner = f"*{inner}*"
        elif tag == "strong":
            inner = f"**{inner}**"
        elif tag == "code":
            inner = f"`{inner}`"
        out.append(inner)
        out.append(child.tail or "")
    return "".join(out)


def _title_text(section: ET.Element) -> str:
    """Extract the section title text from its direct <title> child."""
    title = section.find(f"{NS}title")
    if title is None:
        return ""
    parts = [_inline_text(p).strip() for p in title.findall(f"{NS}p")]
    if not parts:
        parts = [_inline_text(title).strip()]
    return " ".join(p for p in parts if p)


def _blocks_markdown(section: ET.Element) -> str:
    """Markdown for a section's direct block children (excludes nested sections/title)."""
    lines: list[str] = []
    for child in section:
        tag = _local(child.tag)
        if tag in ("section", "title"):
            continue
        if tag == "p":
            txt = _inline_text(child).strip()
            if txt:
                lines.append(txt)
        elif tag == "subtitle":
            txt = _inline_text(child).strip()
            if txt:
                lines.append(f"**{txt}**")
        elif tag == "empty-line":
            continue  # paragraph join below already separates blocks
        elif tag == "cite":
            cite = " ".join(
                _inline_text(p).strip()
                for p in child.findall(f"{NS}p")
            ).strip()
            if cite:
                lines.append(f"> {cite}")
    return "\n\n".join(lines)


def _collect_subsections(section: ET.Element, depth: int, out: list[Chunk]) -> None:
    """Append nested sections as subsection chunks, deepening level with nesting."""
    for sub in section.findall(f"{NS}section"):
        title = _title_text(sub)
        content = _blocks_markdown(sub)
        out.append(Chunk(heading=title, content=content, level=min(depth, 3)))
        _collect_subsections(sub, depth + 1, out)


def _section_to_group(section: ET.Element, chapter_no: int) -> ChapterGroup:
    title = _title_text(section) or f"Chapter {chapter_no}"
    content = _blocks_markdown(section)
    chapter_chunk = Chunk(
        heading=title,
        content=content,
        level=1,
        chapter_no=chapter_no,
        chapter_title=title,
        sequence=0,
    )
    subs: list[Chunk] = []
    _collect_subsections(section, 2, subs)
    return ChapterGroup(chapter_no=chapter_no, chapter_title=title,
                        chunks=[chapter_chunk] + subs)


def _read_metadata(root: ET.Element, path: Path) -> dict:
    ti = root.find(f".//{NS}title-info")
    title = path.stem
    authors: list[str] = []
    language = "en"
    year = None

    if ti is not None:
        bt = ti.find(f"{NS}book-title")
        if bt is not None and (bt.text or "").strip():
            title = bt.text.strip()
        for author_el in ti.findall(f"{NS}author"):
            first = author_el.findtext(f"{NS}first-name", default="").strip()
            last = author_el.findtext(f"{NS}last-name", default="").strip()
            name = f"{first} {last}".strip()
            if name:
                authors.append(name)
        lang = ti.findtext(f"{NS}lang", default="").strip()
        if lang:
            language = lang
        date = ti.findtext(f"{NS}date", default="").strip()
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
        "source_format": "fb2",
        "book_type": "technical",
    }


def read(path: Path) -> BookContent:
    """Parse an FB2 file into BookContent."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    meta = _read_metadata(root, path)

    body = root.find(f".//{NS}body")
    groups: list[ChapterGroup] = []
    if body is not None:
        for i, section in enumerate(body.findall(f"{NS}section"), start=1):
            groups.append(_section_to_group(section, i))

    return BookContent(meta=meta, groups=groups)
