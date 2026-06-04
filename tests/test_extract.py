"""Test the PDF extraction module."""

from pathlib import Path

from ovbook.extract import extract_pdf, get_pdf_metadata
from ovbook.profile import detect_profile


def test_detect_profile_normal_pdf(pdf_fixture):
    """detect_profile returns valid metadata for a normal PDF."""
    profile = detect_profile(pdf_fixture)
    assert "type" in profile
    assert profile["type"] in ("born-digital", "diagram-heavy")
    assert profile["body_size"] > 0
    assert isinstance(profile["encoding_ok"], bool)
    assert isinstance(profile["page_count"], int)


def test_extract_pdf_returns_string(pdf_fixture):
    result = extract_pdf(pdf_fixture)
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_pdf_has_headings(pdf_fixture):
    result = extract_pdf(pdf_fixture)
    assert "# " in result  # H1 (book title)
    assert "## " in result or "### " in result  # chapter/section headings


def test_extract_pdf_preserves_paragraphs(pdf_fixture):
    result = extract_pdf(pdf_fixture)
    assert "Introduction" in result or "First" in result or "Content" in result


def test_get_pdf_metadata(pdf_fixture):
    meta = get_pdf_metadata(pdf_fixture)
    assert "title" in meta
    assert meta["title"]
    assert "id" in meta
