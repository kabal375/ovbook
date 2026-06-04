"""Tests for ovbook.writer — hierarchical tree with Part/Chapter grouping."""

from pathlib import Path

from ovbook.split import Chunk
from ovbook.writer import write_chunks


# ---------------------------------------------------------------------------
# Hierarchical grouping
# ---------------------------------------------------------------------------


def test_no_part_structure_unchanged(tmp_path: Path):
    """Without Part but with chapters — grouped by chapter_no."""
    chunks = [
        Chunk(heading="Chapter 1", content="Intro", level=2, sequence=0,
              chapter_no=1, chapter_title="Chapter 1"),
        Chunk(heading="Section 1", content="Detail", level=3, sequence=1,
              chapter_no=1, section_no=1, section_title="Section 1"),
    ]
    write_chunks(tmp_path, {}, chunks, slug="test-book")
    assert (tmp_path / "test-book" / "00-book.md").is_file()
    # Chunks grouped under chapter-01-chapter-1/
    chapter_dir = tmp_path / "test-book" / "chapter-01-chapter-1"
    assert chapter_dir.is_dir()
    assert (chapter_dir / "01-chapter-1.md").is_file()
    assert (chapter_dir / "02-section-1.md").is_file()


def test_part_groups_chapters(tmp_path: Path):
    """With Part, chapters are grouped under part and further by chapter."""
    chunks = [
        Chunk(heading="Chapter 1", content="A", level=2, sequence=0,
              chapter_no=1, chapter_title="Chapter 1", part="Part I"),
        Chunk(heading="Chapter 2", content="B", level=2, sequence=1,
              chapter_no=2, chapter_title="Chapter 2", part="Part I"),
    ]
    write_chunks(tmp_path, {}, chunks, slug="test-book")
    book_dir = tmp_path / "test-book"
    assert (book_dir / "00-book.md").is_file()
    # Find the part directory (slugified "Part I")
    part_dirs = sorted([d for d in book_dir.iterdir() if d.is_dir()])
    assert len(part_dirs) == 1
    assert "part-i" in part_dirs[0].name
    # Chapter directories inside part dir
    chapter_dirs = sorted(part_dirs[0].iterdir())
    assert len(chapter_dirs) == 2
    assert "chapter-01-chapter-1" in chapter_dirs[0].name
    assert "chapter-02-chapter-2" in chapter_dirs[1].name
    # Files inside each chapter dir
    ch1_files = sorted(chapter_dirs[0].iterdir())
    assert len(ch1_files) == 1
    assert "01-chapter-1.md" in ch1_files[0].name


def test_multiple_parts(tmp_path: Path):
    """Multiple parts each get their own directory."""
    chunks = [
        Chunk(heading="Chapter 1", content="A", level=2, sequence=0,
              chapter_no=1, chapter_title="Chapter 1", part="Part I"),
        Chunk(heading="Chapter 1", content="B", level=2, sequence=1,
              chapter_no=1, chapter_title="Chapter 1", part="Part II"),
    ]
    write_chunks(tmp_path, {}, chunks, slug="test-book")
    book_dir = tmp_path / "test-book"
    part_dirs = sorted([d for d in book_dir.iterdir() if d.is_dir()])
    assert len(part_dirs) == 2
    assert "part-i" in part_dirs[0].name
    assert "part-ii" in part_dirs[1].name
