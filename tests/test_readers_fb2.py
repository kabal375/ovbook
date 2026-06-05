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
