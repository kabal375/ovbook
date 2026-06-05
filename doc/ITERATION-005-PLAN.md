# FB2 & EPUB Structural Readers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structural FB2 and EPUB readers that produce the same `list[ChapterGroup]` output as the PDF pipeline, feeding the unified `write_chapter_groups` writer.

**Architecture:** A new `readers/` package where each format is an isolated module exposing `read(path) -> BookContent`. PDF wraps the existing scoring pipeline; FB2/EPUB build chapters directly from markup (top-level section / top-level TOC entry = chapter, nested sections / `<h2>`/`<h3>` = subsections). `cli.py` becomes format-agnostic via a registry. The legacy per-file `write_chunks` path is removed.

**Tech Stack:** Python 3.11+, uv, Typer, PyMuPDF (PDF), stdlib ElementTree (FB2), ebooklib + markdownify (EPUB), pytest.

**Spec:** `doc/ITERATION-005.md`

**Branch:** `feat/fb2-epub-readers` (branched from `fix/review-p0-p3`)

---

## Task 1: BookContent intermediate type

**Files:**
- Create: `src/ovbook/readers/__init__.py` (empty for now — registry added in Task 7)
- Create: `src/ovbook/readers/base.py`
- Test: `tests/test_readers_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readers_base.py
"""Tests for the BookContent intermediate type."""

from ovbook.readers.base import BookContent
from ovbook.split import ChapterGroup, Chunk


def test_bookcontent_holds_meta_and_groups():
    group = ChapterGroup(chapter_no=1, chapter_title="Ch1",
                         chunks=[Chunk(heading="Ch1", content="body", level=1)])
    content = BookContent(meta={"title": "T"}, groups=[group])
    assert content.meta["title"] == "T"
    assert len(content.groups) == 1
    assert content.groups[0].chapter_title == "Ch1"


def test_bookcontent_groups_default_empty():
    content = BookContent(meta={"title": "T"})
    assert content.groups == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_readers_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ovbook.readers'`

- [ ] **Step 3: Create the package and BookContent**

```python
# src/ovbook/readers/__init__.py
"""Per-format book readers producing a unified BookContent."""
```

```python
# src/ovbook/readers/base.py
"""Common intermediate representation shared by all format readers."""

from dataclasses import dataclass, field

from ovbook.split import ChapterGroup


@dataclass
class BookContent:
    """Normalized output of any reader.

    meta:   book frontmatter dict (id, title, authors, language, year, ...)
    groups: chapters ready for write_chapter_groups
    """

    meta: dict
    groups: list[ChapterGroup] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_readers_base.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ovbook/readers/__init__.py src/ovbook/readers/base.py tests/test_readers_base.py
git commit -m "feat(readers): add BookContent intermediate type"
```

---

## Task 2: Writer respects subsection heading level

**Files:**
- Modify: `src/ovbook/writer.py` (`_write_chapter_file`)
- Test: `tests/test_writer_chapter_levels.py`

Currently `_write_chapter_file` emits `## {heading}` for every chunk after the first. Subsection chunks with `level=3` must become `###`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_writer_chapter_levels.py
"""Subsection chunks render with a heading prefix matching their level."""

from ovbook.split import Chunk, ChapterGroup
from ovbook.writer import write_chapter_groups


def test_subsection_levels_render_correct_prefix(tmp_path):
    group = ChapterGroup(
        chapter_no=1,
        chapter_title="Getting Started",
        chunks=[
            Chunk(heading="Getting Started", content="Intro.", level=1,
                  chapter_no=1, chapter_title="Getting Started"),
            Chunk(heading="Installation", content="Install body.", level=2),
            Chunk(heading="Prerequisites", content="Deep detail.", level=3),
        ],
    )
    write_chapter_groups(tmp_path, [group], {"id": "b", "title": "B"}, "b")

    chapter_file = next(
        f for f in (tmp_path / "b").iterdir()
        if f.name != "00-book.md"
    )
    text = chapter_file.read_text()
    assert "## Installation" in text
    assert "### Prerequisites" in text
    assert "#### " not in text  # level capped, no over-deep headings
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_writer_chapter_levels.py -v`
Expected: FAIL — `### Prerequisites` not found (currently rendered as `## Prerequisites`)

- [ ] **Step 3: Update `_write_chapter_file`**

In `src/ovbook/writer.py`, replace the subsection loop inside `_write_chapter_file`:

```python
    for chunk in group.chunks[1:]:
        chunk_parts: list[str] = []
        if chunk.heading:
            # level 2 -> ##, level 3 -> ###, clamp into [2, 6]
            depth = min(max(chunk.level, 2), 6)
            chunk_parts.append(f"{'#' * depth} {chunk.heading}")
        if chunk.content:
            chunk_parts.append(chunk.content)
        if chunk_parts:
            sections.append("\n\n".join(chunk_parts))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_writer_chapter_levels.py tests/test_writer.py -v`
Expected: PASS (new test + existing writer tests still green)

- [ ] **Step 5: Commit**

```bash
git add src/ovbook/writer.py tests/test_writer_chapter_levels.py
git commit -m "feat(writer): render subsection heading prefix by chunk level"
```

---

## Task 3: PDF reader (wrap existing pipeline)

**Files:**
- Create: `src/ovbook/readers/pdf.py`
- Test: `tests/test_readers_pdf.py`

Moves the PDF pipeline currently inlined in `cli.py` into a reader. The stderr encoding warning is dropped here (readers stay pure); the warning is reintroduced in cli via the meta in a later iteration if needed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readers_pdf.py
"""The PDF reader returns BookContent with chapter groups."""

from ovbook.readers.pdf import read
from ovbook.readers.base import BookContent


def test_pdf_reader_returns_bookcontent(pdf_fixture):
    content = read(pdf_fixture)
    assert isinstance(content, BookContent)
    assert content.meta["title"] == "Test Book"
    assert content.meta["source_format"] == "pdf"
    assert len(content.groups) >= 1
    # first group has at least the chapter chunk
    assert content.groups[0].chunks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_readers_pdf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ovbook.readers.pdf'`

- [ ] **Step 3: Implement the reader**

```python
# src/ovbook/readers/pdf.py
"""PDF reader — wraps the font-size scoring pipeline."""

from pathlib import Path

from ovbook.extract import extract_pdf_rich, get_metadata
from ovbook.profile import detect_profile
from ovbook.readers.base import BookContent
from ovbook.split import (
    filter_low_score_chunks,
    filter_toc_chunks,
    group_chunks_by_chapter,
)


def read(path: Path) -> BookContent:
    """Convert a PDF into BookContent via profile → extract → filter → group."""
    profile = detect_profile(path)
    body_size = profile["body_size"]

    raw = extract_pdf_rich(path, body_size=body_size)
    raw = filter_toc_chunks(raw)
    raw = filter_low_score_chunks(raw, min_score=-1.0)

    groups = group_chunks_by_chapter(raw, min_chapter_score=7.0)
    meta = get_metadata(path)
    return BookContent(meta=meta, groups=groups)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_readers_pdf.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ovbook/readers/pdf.py tests/test_readers_pdf.py
git commit -m "feat(readers): add PDF reader wrapping scoring pipeline"
```

---

## Task 4: FB2 reader — metadata + inline markdown helpers

**Files:**
- Create: `src/ovbook/readers/fb2.py`
- Test: `tests/test_readers_fb2.py`
- Modify: `tests/conftest.py` (add `fb2_fixture`)

Build the helpers first (metadata, inline-markup → markdown, block extraction), then assemble groups in Task 5. This task delivers metadata + a working `read()` for flat chapters.

- [ ] **Step 1: Add the FB2 fixture to conftest.py**

Append to `tests/conftest.py`:

```python
_FB2_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>FB2 Test Book</book-title>
      <author><first-name>Jane</first-name><last-name>Doe</last-name></author>
      <lang>en</lang>
      <date>2021</date>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Getting Started</p></title>
      <p>Intro paragraph with <emphasis>emphasis</emphasis> and <code>snippet</code>.</p>
      <empty-line/>
      <p>Second intro paragraph.</p>
      <section>
        <title><p>Installation</p></title>
        <p>Install steps with <strong>bold</strong> text.</p>
      </section>
    </section>
    <section>
      <title><p>Advanced Topics</p></title>
      <p>Second chapter body.</p>
    </section>
  </body>
</FictionBook>
"""


@pytest.fixture(scope="session")
def fb2_fixture(tmp_path_factory) -> Path:
    """Generate a structural FB2 test file."""
    path = tmp_path_factory.mktemp("fixtures") / "test-book.fb2"
    path.write_text(_FB2_CONTENT, encoding="utf-8")
    return path
```

- [ ] **Step 2: Write the failing test (metadata)**

```python
# tests/test_readers_fb2.py
"""Tests for the structural FB2 reader."""

from ovbook.readers.fb2 import read
from ovbook.readers.base import BookContent


def test_fb2_metadata(fb2_fixture):
    content = read(fb2_fixture)
    assert isinstance(content, BookContent)
    assert content.meta["title"] == "FB2 Test Book"
    assert content.meta["authors"] == ["Jane Doe"]
    assert content.meta["language"] == "en"
    assert content.meta["year"] == 2021
    assert content.meta["source_format"] == "fb2"


def test_fb2_chapters_from_top_level_sections(fb2_fixture):
    content = read(fb2_fixture)
    assert len(content.groups) == 2
    assert content.groups[0].chapter_title == "Getting Started"
    assert content.groups[1].chapter_title == "Advanced Topics"


def test_fb2_inline_markdown(fb2_fixture):
    content = read(fb2_fixture)
    ch1 = content.groups[0].chunks[0]
    assert "*emphasis*" in ch1.content
    assert "`snippet`" in ch1.content


def test_fb2_nested_section_becomes_subsection(fb2_fixture):
    content = read(fb2_fixture)
    subs = content.groups[0].chunks[1:]
    assert len(subs) == 1
    assert subs[0].heading == "Installation"
    assert subs[0].level == 2
    assert "**bold**" in subs[0].content
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_readers_fb2.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ovbook.readers.fb2'`

- [ ] **Step 4: Implement the FB2 reader**

```python
# src/ovbook/readers/fb2.py
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
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_readers_fb2.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add src/ovbook/readers/fb2.py tests/test_readers_fb2.py tests/conftest.py
git commit -m "feat(readers): add structural FB2 reader"
```

---

## Task 5: FB2 reader — full pipeline through writer

**Files:**
- Test: `tests/test_readers_fb2.py` (extend)

Verifies the FB2 reader output writes correctly via `write_chapter_groups`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_readers_fb2.py`:

```python
def test_fb2_full_pipeline_writes_chapter_files(fb2_fixture, tmp_path):
    from ovbook.writer import write_chapter_groups

    content = read(fb2_fixture)
    write_chapter_groups(tmp_path, content.groups, content.meta, "fb2-test-book")

    book_dir = tmp_path / "fb2-test-book"
    assert (book_dir / "00-book.md").is_file()

    chapter_files = sorted(
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    )
    assert len(chapter_files) == 2

    first = chapter_files[0].read_text()
    assert "book_id:" in first
    assert "## Installation" in first       # nested section embedded as ##
    assert "*emphasis*" in first            # inline markdown preserved
    # no per-chapter subdirectories
    assert [d for d in book_dir.iterdir() if d.is_dir()] == []
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/test_readers_fb2.py::test_fb2_full_pipeline_writes_chapter_files -v`
Expected: PASS (Task 4 + Task 2 already provide the behavior; this is the integration guard). If it FAILS on `## Installation`, confirm Task 2 landed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_readers_fb2.py
git commit -m "test(readers): FB2 full pipeline through writer"
```

---

## Task 6: EPUB reader

**Files:**
- Create: `src/ovbook/readers/epub.py`
- Test: `tests/test_readers_epub.py`
- Modify: `tests/conftest.py` (add `epub_fixture`)
- Modify: `pyproject.toml` (add `ebooklib`, `markdownify`)

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `pyproject.toml`, under `[project] dependencies`, add:

```toml
    "ebooklib>=0.18",
    "markdownify>=0.13",
```

Then run: `uv sync`
Expected: ebooklib and markdownify installed.

- [ ] **Step 2: Add the EPUB fixture to conftest.py**

Append to `tests/conftest.py`:

```python
def _generate_epub(path: Path) -> None:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("epub-test-book")
    book.set_title("EPUB Test Book")
    book.set_language("en")
    book.add_author("John Smith")
    book.add_metadata("DC", "date", "2023-05-01")

    c1 = epub.EpubHtml(title="Chapter One", file_name="c1.xhtml", lang="en")
    c1.content = (
        "<html><body>"
        "<h1>Chapter One</h1>"
        "<p>Intro text for chapter one.</p>"
        "<h2>Section A</h2>"
        "<p>Section A body.</p>"
        "<pre><code>print('hello')</code></pre>"
        "<ul><li>first item</li><li>second item</li></ul>"
        "</body></html>"
    )
    c2 = epub.EpubHtml(title="Chapter Two", file_name="c2.xhtml", lang="en")
    c2.content = "<html><body><h1>Chapter Two</h1><p>Second chapter body.</p></body></html>"
    cover = epub.EpubHtml(title="Cover", file_name="cover.xhtml", lang="en")
    cover.content = "<html><body><p>Cover page, not in TOC.</p></body></html>"

    book.add_item(c1)
    book.add_item(c2)
    book.add_item(cover)
    book.toc = (
        epub.Link("c1.xhtml", "Chapter One", "c1"),
        epub.Link("c2.xhtml", "Chapter Two", "c2"),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = [cover, c1, c2]
    epub.write_epub(str(path), book)


@pytest.fixture(scope="session")
def epub_fixture(tmp_path_factory) -> Path:
    """Generate a structural EPUB test file."""
    path = tmp_path_factory.mktemp("fixtures") / "test-book.epub"
    _generate_epub(path)
    return path
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_readers_epub.py
"""Tests for the structural EPUB reader."""

from ovbook.readers.epub import read
from ovbook.readers.base import BookContent


def test_epub_metadata(epub_fixture):
    content = read(epub_fixture)
    assert isinstance(content, BookContent)
    assert content.meta["title"] == "EPUB Test Book"
    assert content.meta["authors"] == ["John Smith"]
    assert content.meta["language"] == "en"
    assert content.meta["year"] == 2023
    assert content.meta["source_format"] == "epub"


def test_epub_chapters_from_toc(epub_fixture):
    content = read(epub_fixture)
    assert len(content.groups) == 2
    assert content.groups[0].chapter_title == "Chapter One"
    assert content.groups[1].chapter_title == "Chapter Two"


def test_epub_h2_becomes_subsection(epub_fixture):
    content = read(epub_fixture)
    subs = content.groups[0].chunks[1:]
    assert any(s.heading == "Section A" and s.level == 2 for s in subs)


def test_epub_preserves_code_and_lists(epub_fixture):
    content = read(epub_fixture)
    all_text = "\n".join(
        c.content for g in content.groups for c in g.chunks
    )
    assert "print('hello')" in all_text   # code block survived
    assert "first item" in all_text       # list survived


def test_epub_front_matter_skipped(epub_fixture):
    """Cover page is in spine but not TOC → not a chapter."""
    content = read(epub_fixture)
    titles = [g.chapter_title for g in content.groups]
    assert "Cover" not in titles
    assert len(content.groups) == 2
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_readers_epub.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ovbook.readers.epub'`

- [ ] **Step 5: Implement the EPUB reader**

```python
# src/ovbook/readers/epub.py
"""Structural EPUB reader.

Top-level TOC entry = chapter. Each chapter's XHTML is converted to markdown
(markdownify) and split into a chapter chunk + <h2>/<h3> subsection chunks.
Falls back to spine documents when there is no usable TOC.
"""

import re
from pathlib import Path

import ebooklib
from ebooklib import epub
from markdownify import markdownify as md

from ovbook.readers.base import BookContent
from ovbook.split import Chunk, ChapterGroup

_H_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _to_markdown(html: str) -> str:
    return md(html, heading_style="ATX", bullets="-", strip=["img"])


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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_readers_epub.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git add src/ovbook/readers/epub.py tests/test_readers_epub.py tests/conftest.py pyproject.toml uv.lock
git commit -m "feat(readers): add structural EPUB reader (ebooklib + markdownify)"
```

---

## Task 7: Reader registry

**Files:**
- Modify: `src/ovbook/readers/__init__.py`
- Test: `tests/test_readers_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readers_registry.py
"""Tests for the reader registry."""

import pytest

from ovbook.readers import get_reader
from ovbook.readers import pdf, fb2, epub


def test_registry_maps_known_formats():
    assert get_reader("pdf") is pdf.read
    assert get_reader("fb2") is fb2.read
    assert get_reader("epub") is epub.read


def test_registry_unknown_format_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        get_reader("mobi")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_readers_registry.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_reader'`

- [ ] **Step 3: Implement the registry**

Replace `src/ovbook/readers/__init__.py`:

```python
"""Per-format book readers producing a unified BookContent."""

from collections.abc import Callable
from pathlib import Path

from ovbook.readers import epub, fb2, pdf
from ovbook.readers.base import BookContent

_REGISTRY: dict[str, Callable[[Path], BookContent]] = {
    "pdf": pdf.read,
    "fb2": fb2.read,
    "epub": epub.read,
}


def get_reader(fmt: str) -> Callable[[Path], BookContent]:
    """Return the reader function for a format, or raise ValueError."""
    reader = _REGISTRY.get(fmt.lower())
    if reader is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unsupported format: '{fmt}' (supported: {supported})")
    return reader


__all__ = ["BookContent", "get_reader"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_readers_registry.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ovbook/readers/__init__.py tests/test_readers_registry.py
git commit -m "feat(readers): add format registry"
```

---

## Task 8: Make cli.py format-agnostic

**Files:**
- Modify: `src/ovbook/cli.py`
- Test: `tests/test_cli.py` (extend with FB2/EPUB cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
def test_convert_fb2_writes_chapter_files(fb2_fixture, tmp_path):
    result = runner.invoke(app, ["convert", str(fb2_fixture), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output
    book_dir = next(d for d in tmp_path.iterdir() if d.is_dir())
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) == 2
    assert "book_id:" in chapter_files[0].read_text()


def test_convert_epub_writes_chapter_files(epub_fixture, tmp_path):
    result = runner.invoke(app, ["convert", str(epub_fixture), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output
    book_dir = next(d for d in tmp_path.iterdir() if d.is_dir())
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) == 2


def test_convert_fb2_dry_run(fb2_fixture):
    result = runner.invoke(app, ["convert", str(fb2_fixture), "--dry-run"])
    assert result.exit_code == 0
    assert "FB2 Test Book" in result.output
    assert "Chapters:" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -k "fb2 or epub" -v`
Expected: FAIL (cli still has the old pdf/fb2 branching using split_into_chunks)

- [ ] **Step 3: Rewrite cli.py**

Replace the body of `convert()` and `_print_dry_run()` in `src/ovbook/cli.py`:

```python
"""ovbook CLI — convert books to structured markdown chunks for OpenViking."""

from pathlib import Path

import typer

from ovbook.readers import get_reader
from ovbook.writer import make_slug, write_chapter_groups


app = typer.Typer(
    name="ovbook",
    help="Convert books to structured markdown chunks for OpenViking indexing.",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """ovbook — book-to-chunk converter for OpenViking."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def convert(
    input: Path = typer.Argument(
        ...,
        help="Path to input book file (.pdf / .fb2 / .epub)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    format: str = typer.Option(
        None, "--format", "-f", help="Book format (auto-detect from extension)"
    ),
    output: Path = typer.Option(
        Path.cwd(), "--output", "-o",
        help="Output directory for chunk tree",
        file_okay=False, dir_okay=True,
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show chunk structure without writing files",
    ),
    domain: list[str] = typer.Option(
        [], "--domain", help="Book domain (can be repeated)"),
    topic: list[str] = typer.Option(
        [], "--topic", help="Book topic (can be repeated)"),
    edition: str = typer.Option(
        None, "--edition", help="Book edition (e.g. '2nd')"),
):
    """Convert a book file into structured markdown chunks for OpenViking.

    Detects format from file extension by default. Supports: pdf, fb2, epub.
    """
    fmt = format or input.suffix.lstrip(".").lower()

    try:
        reader = get_reader(fmt)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    content = reader(input)
    meta = content.meta
    groups = content.groups

    if domain:
        meta["domains"] = domain
    if topic:
        meta["topics"] = topic
    if edition:
        meta["edition"] = edition

    if dry_run:
        _print_dry_run(meta, groups)
        return

    slug = make_slug(meta.get("title", input.stem))
    write_chapter_groups(output, groups, meta, slug)
    total = sum(len(g.chunks) for g in groups)
    typer.echo(f"Written {total} chunks ({len(groups)} chapters) to {output / slug}")


def _print_dry_run(meta: dict, groups: list) -> None:
    """Print a dry-run summary of what would be written."""
    typer.echo(f"Book: {meta.get('title', '(no title)')}")
    if meta.get("authors"):
        typer.echo(f"Authors: {', '.join(meta['authors'])}")
    if meta.get("domains"):
        typer.echo(f"Domains: {', '.join(meta['domains'])}")
    if meta.get("topics"):
        typer.echo(f"Topics: {', '.join(meta['topics'])}")

    total = sum(len(g.chunks) for g in groups)
    typer.echo(f"Chapters: {len(groups)}")
    typer.echo(f"Chunks: {total}")
    for g in groups:
        for c in g.chunks:
            preview = c.content[:80].replace("\n", " ").strip()
            typer.echo(f"  [{c.sequence + 1:02d}] {c.heading}")
            if preview:
                typer.echo(f"       {preview}...")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (existing PDF cli tests + new FB2/EPUB tests)

- [ ] **Step 5: Commit**

```bash
git add src/ovbook/cli.py tests/test_cli.py
git commit -m "refactor(cli): format-agnostic routing via reader registry"
```

---

## Task 9: Remove legacy write_chunks path

**Files:**
- Modify: `src/ovbook/writer.py` (delete `write_chunks` and FB2 helpers)
- Delete: `tests/test_writer_hierarchy.py`
- Modify: `tests/test_writer.py` (remove write_chunks tests)
- Modify: `tests/test_metadata.py` (rewrite `test_domains_propagate_to_chunks`)
- Modify: `tests/test_integration.py` (rewrite to use reader path)

- [ ] **Step 1: Delete write_chunks and its helpers from writer.py**

In `src/ovbook/writer.py`, remove these functions entirely:
`write_chunks`, `_write_flat`, `_write_each_chunk_dir`, `_write_by_chapter`,
`_write_chunk`, `_write_with_parts`.

Keep: `_slugify`, `make_slug`, `_BARE_CHAPTER_RE`, `_resolve_chapter_title`,
`write_chapter_groups`, `_write_chapter_file`.

Remove the now-unused `Chunk` import if `_write_chapter_file` no longer
references it (it references `ChapterGroup` and `Chunk` via group.chunks — keep
`from ovbook.split import Chunk, ChapterGroup` only if still used; otherwise
reduce to `ChapterGroup`). Verify with: `uv run python -c "import ovbook.writer"`.

- [ ] **Step 2: Delete the obsolete hierarchy test**

```bash
git rm tests/test_writer_hierarchy.py
```

- [ ] **Step 3: Trim test_writer.py**

In `tests/test_writer.py`, remove every test that calls `write_chunks`
(all tests under the `write_chunks` section). Keep the `_slugify` tests and
the `_resolve_chapter_title` tests. Update the import line to:

```python
from ovbook.writer import _slugify, _resolve_chapter_title
```

- [ ] **Step 4: Rewrite the domains propagation test**

Replace `test_domains_propagate_to_chunks` in `tests/test_metadata.py` with a
book-card check (chunk-level domains are not part of the depth-guarded output;
domains live in 00-book.md):

```python
def test_domains_written_to_book_card(tmp_path, pdf_fixture):
    """--domain / --topic land in the book card frontmatter."""
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tmp_path),
        "--domain", "cloud-native", "--topic", "kubernetes",
    ])
    assert result.exit_code == 0
    card = next(tmp_path.rglob("00-book.md")).read_text()
    assert "cloud-native" in card
    assert "kubernetes" in card
```

- [ ] **Step 5: Rewrite the integration test**

Replace `tests/test_integration.py` contents:

```python
"""Integration tests for the full ovbook pipeline via readers."""

from ovbook.readers import get_reader
from ovbook.writer import write_chapter_groups, make_slug


def test_pdf_pipeline_roundtrip(tmp_path, pdf_fixture):
    content = get_reader("pdf")(pdf_fixture)
    assert content.meta["title"] == "Test Book"
    assert len(content.groups) >= 1

    slug = make_slug(content.meta["title"])
    write_chapter_groups(tmp_path, content.groups, content.meta, slug)

    book_dir = tmp_path / slug
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) >= 1
    assert "book_id:" in chapter_files[0].read_text()


def test_cli_convert_pdf(pdf_fixture, tmp_path):
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["convert", str(pdf_fixture), "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert "Written" in result.output
    assert (tmp_path / "test-book" / "00-book.md").exists()
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: ALL PASS. No references to `write_chunks` remain.

Verify nothing imports the removed symbol:
Run: `grep -rn "write_chunks" src tests`
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: remove legacy per-file write_chunks path"
```

---

## Task 10: Update README and convert a real book

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README usage**

In `README.md`, update the Usage and Tech sections to mention all three formats:

```markdown
## Usage

```bash
uv run ovbook convert book.pdf  -o ~/ov-lib/tech-lib/
uv run ovbook convert book.fb2  -o ~/ov-lib/tech-lib/
uv run ovbook convert book.epub -o ~/ov-lib/tech-lib/
```

Поддерживаемые форматы: **pdf** (font-size scoring), **fb2** и **epub**
(структурный парсинг — точнее, чем PDF).
```

Update the Tech list to add:
```markdown
- FB2: stdlib ElementTree (structural)
- EPUB: [ebooklib](https://github.com/aerkalov/ebooklib) + [markdownify](https://github.com/matthewwithanm/python-markdownify)
```

- [ ] **Step 2: Convert a real FB2 or EPUB book and eyeball the output**

```bash
uv run ovbook convert /path/to/real-book.epub --dry-run
# then, if structure looks right:
uv run ovbook convert /path/to/real-book.epub -o ~/ov-lib/tech-lib/
```

Check: chapter titles are descriptive, code blocks/lists preserved, no junk
chapters. Adjust as needed (this is the "look at it in practice" step the user
asked for).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document FB2 and EPUB support"
```

- [ ] **Step 4: Push and open PR**

```bash
git push -u origin feat/fb2-epub-readers
```

Open a PR into `fix/review-p0-p3` (or `master` if review branch is already merged).

---

## Self-Review Notes

- **Spec coverage:** readers package (T1,3,4,6,7), unified output (T1,8), FB2 structural (T4,5), EPUB structural (T6), writer level fix (T2), write_chunks removal (T9), deps (T6), fixtures + tests (T4,6), CLI (T8), docs (T10). All spec sections mapped.
- **Type consistency:** `BookContent(meta, groups)`, `ChapterGroup(chapter_no, chapter_title, chunks)`, `Chunk(heading, content, level, ...)`, `read(path) -> BookContent`, `get_reader(fmt) -> Callable` — consistent across all tasks.
- **Known simplification:** EPUB chapters are doc-level (one chapter per unique TOC document); anchor-based mid-document splitting is deferred. `split_into_chunks` / `filter_content` in `split.py` remain (still tested) but are no longer on a production path — left as-is to avoid deleting useful, tested utilities.
