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
    """Cover page is in spine but not TOC -> not a chapter."""
    content = read(epub_fixture)
    titles = [g.chapter_title for g in content.groups]
    assert "Cover" not in titles
    assert len(content.groups) == 2


def test_epub_no_xml_declaration_leak(epub_fixture):
    """The XML declaration and <head> must not leak into chapter content."""
    content = read(epub_fixture)
    all_text = "\n".join(c.content for g in content.groups for c in g.chunks)
    assert "xml version" not in all_text
    assert "<?xml" not in all_text
    assert "<head" not in all_text
