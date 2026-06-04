"""Generate a minimal test PDF for integration tests."""

from pathlib import Path
import fitz


def generate_test_pdf(path: Path) -> None:
    """Create a minimal PDF with title, chapter headings, sections."""
    doc = fitz.open()

    # Set metadata
    doc.set_metadata({
        "title": "Test Book",
        "author": "Test Author",
        "language": "en",
    })

    # Page 1: title
    page = doc.new_page()
    # Title uses large font → H1
    rect = fitz.Rect(72, 200, 540, 300)
    page.insert_textbox(rect, "Test Book", fontsize=24, align=1)

    # Page 2: chapter 1
    page = doc.new_page()
    # Chapter heading → H2 (fontsize 18 vs body 11)
    rect = fitz.Rect(72, 72, 540, 120)
    page.insert_textbox(rect, "Chapter 1: Introduction", fontsize=18)

    # Body text
    rect = fitz.Rect(72, 140, 540, 200)
    page.insert_textbox(rect, (
        "This is the first paragraph of the introduction. "
        "It contains some technical content that should be extracted."
    ), fontsize=11)

    # Page 3: section 1.1
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 540, 120)
    page.insert_textbox(rect, "Section 1.1: Getting Started", fontsize=14)

    rect = fitz.Rect(72, 140, 540, 200)
    page.insert_textbox(rect, (
        "Detailed content for the first section. "
        "Explaining how to get started with the topic."
    ), fontsize=11)

    # Page 4: chapter 2
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 540, 120)
    page.insert_textbox(rect, "Chapter 2: Advanced Topics", fontsize=18)

    rect = fitz.Rect(72, 140, 540, 200)
    page.insert_textbox(rect, (
        "Content for the advanced chapter. "
        "More complex concepts explained here."
    ), fontsize=11)

    doc.save(str(path))
    doc.close()
