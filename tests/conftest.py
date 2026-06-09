"""Pytest fixtures for ovbook tests."""

from pathlib import Path
import textwrap
import pytest


@pytest.fixture
def tech_lib(tmp_path) -> Path:
    """A tech-lib output dir under a root holding a vocabulary.yaml.

    Returns the output directory (``<root>/tech-lib``). Books written here
    walk up to find the vocabulary at ``<root>/vocabulary.yaml``.
    """
    (tmp_path / "vocabulary.yaml").write_text(textwrap.dedent("""
        collections:
          tech-lib:
            domains:
              - software-development
              - operating-systems
              - devops-sre
            topics_registry: []
    """))
    out = tmp_path / "tech-lib"
    out.mkdir()
    return out


def _generate_test_pdf(path: Path) -> None:
    """Create a minimal PDF with title, chapter headings, sections.

    Font: title=24pt, chapters=18pt, sections=14pt, body=11pt.
    Body text is the most common size (6 pages × 2 blocks) → median ≈ 11pt.
    18pt/11pt=1.64 ≥ 1.3 → chapter headings detected. 14pt/11pt=1.27 < 1.3
    → section heading accumulated into chapter body.
    """
    import fitz

    doc = fitz.open()
    doc.set_metadata({"title": "Test Book", "author": "Test Author"})

    # Page 1: title page with large font → H1
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 200, 540, 300), "Test Book", fontsize=24, align=1)

    # Page 2: chapter heading (H2) + body text
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "Chapter 1: Introduction", fontsize=18)
    page.insert_textbox(fitz.Rect(72, 140, 540, 400), (
        "This is the first paragraph of the introduction. "
        "It contains some technical content that should be extracted."
    ), fontsize=11)

    # Page 3: section (H3, below heading threshold) + body
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "Section 1.1: Getting Started", fontsize=14)
    page.insert_textbox(fitz.Rect(72, 140, 540, 400), (
        "Detailed content for the first section."
    ), fontsize=11)

    # Page 4: another chapter
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "Chapter 2: Advanced Topics", fontsize=18)
    page.insert_textbox(fitz.Rect(72, 140, 540, 400), (
        "Content for the advanced chapter. More complex concepts explained here."
    ), fontsize=11)

    # Pages 5-7: extra body text to push median font size down to 11pt
    for extra in range(3):
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 540, 200), (
            "This is additional body text to ensure the body font size detection "
            "correctly identifies 11pt as the dominant size. Without enough body text "
            "spans, the median gets skewed by heading fonts."
        ), fontsize=11)
        page.insert_textbox(fitz.Rect(72, 220, 540, 400), (
            "More filler text that serves only to increase the count of 11pt font spans "
            "so that _compute_body_size returns 11pt as the body baseline."
        ), fontsize=11)

    doc.save(str(path))
    doc.close()


def _generate_rich_pdf(path: Path) -> None:
    """Create a multi-paragraph PDF to test body accumulation in extract_pdf_rich().

    Structure:
      page 1: title (H1, 24pt)
      page 2: "Chapter 1" heading (18pt) + paragraph 1 (11pt) + paragraph 2 (11pt)
      page 3: subsection "1.1 Details" (16pt) + body paragraph (11pt)
      page 4: "Chapter 2" heading (18pt) + body paragraph (11pt)

    Font sizes: chapter=18pt (≥1.6 body → H2), subsection=16pt (≥1.3 body → H3),
    body=11pt. Body median ≈ 11pt → 1.3× = 14.3pt → 16pt clears it.
    """
    import fitz

    doc = fitz.open()
    doc.set_metadata({"title": "Rich Test Book", "author": "Test Author"})

    # Page 1: title
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 200, 540, 300), "Rich Test Book", fontsize=24, align=1)

    # Page 2: chapter heading + two separate body text blocks on same page
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "Chapter 1", fontsize=18)

    # Multiple text blocks on the same page, all at body font size
    page.insert_textbox(fitz.Rect(72, 150, 540, 250), (
        "This is the first body paragraph after the chapter heading. "
        "It explains the basic concepts and sets the stage for what follows."
    ), fontsize=11)
    page.insert_textbox(fitz.Rect(72, 270, 540, 370), (
        "This is a second body paragraph in the same chapter. "
        "It continues the discussion with more detailed information."
    ), fontsize=11)

    # Page 3: subsection (16pt to clear 1.3×body threshold) + body
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "1.1 Details and Examples", fontsize=16)
    page.insert_textbox(fitz.Rect(72, 150, 540, 350), (
        "Detailed body content for the subsection. "
        "This text should be accumulated and attached to the '1.1 Details and Examples' chunk."
    ), fontsize=11)

    # Page 4: another chapter + body
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 120), "Chapter 2: Advanced", fontsize=18)
    page.insert_textbox(fitz.Rect(72, 150, 540, 350), (
        "Body content for the second chapter. "
        "This should end up in the 'Chapter 2: Advanced' chunk."
    ), fontsize=11)

    doc.save(str(path))
    doc.close()


@pytest.fixture(scope="session")
def pdf_fixture(tmp_path_factory) -> Path:
    """Generate a test PDF once per test session."""
    path = tmp_path_factory.mktemp("fixtures") / "test-book.pdf"
    _generate_test_pdf(path)
    return path


@pytest.fixture(scope="session")
def rich_pdf_fixture(tmp_path_factory) -> Path:
    """Generate a multi-paragraph test PDF for body accumulation tests."""
    path = tmp_path_factory.mktemp("fixtures") / "rich-test-book.pdf"
    _generate_rich_pdf(path)
    return path


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
