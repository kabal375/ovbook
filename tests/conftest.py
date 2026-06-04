"""Pytest fixtures for ovbook tests."""

from pathlib import Path
import pytest


def _generate_test_pdf(path: Path) -> None:
    """Create a minimal PDF with title, chapter headings, sections."""
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

    # Page 3: section (H3)
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


