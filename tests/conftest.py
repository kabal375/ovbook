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


@pytest.fixture(scope="session")
def pdf_fixture(tmp_path_factory) -> Path:
    """Generate a test PDF once per test session."""
    path = tmp_path_factory.mktemp("fixtures") / "test-book.pdf"
    _generate_test_pdf(path)
    return path
