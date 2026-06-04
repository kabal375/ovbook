"""Tests for ovbook.writer."""

from pathlib import Path

from ovbook.split import Chunk
from ovbook.writer import write_chunks, _slugify, _resolve_chapter_title


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

def test_slugify_lowercases():
    assert _slugify("Chapter One") == "chapter-one"


def test_slugify_collapses_spaces():
    assert _slugify("  Hello   World  ") == "hello-world"


def test_slugify_removes_punctuation():
    assert _slugify("What's New?") == "what-s-new"


def test_slugify_already_clean():
    assert _slugify("hello") == "hello"


def test_slugify_strips_trailing_hyphens():
    assert _slugify("hello-") == "hello"


def test_slugify_strips_leading_hyphens():
    assert _slugify("-hello") == "hello"


# ---------------------------------------------------------------------------
# _resolve_chapter_title
# ---------------------------------------------------------------------------

def test_resolve_descriptive_heading_unchanged():
    """Heading with descriptive suffix is returned as-is."""
    chunk = Chunk(heading="Chapter 1: Introduction", content="Body text here.")
    assert _resolve_chapter_title(chunk) == "Chapter 1: Introduction"


def test_resolve_bare_chapter_uses_first_content_line():
    """Bare 'CHAPTER 1' → first line of content."""
    chunk = Chunk(
        heading="CHAPTER 1",
        content="Revolution in the Cloud\n\nThere was never a time...",
    )
    assert _resolve_chapter_title(chunk) == "Revolution in the Cloud"


def test_resolve_bare_chapter_lowercase():
    """'Chapter 2' (no suffix) also triggers content extraction."""
    chunk = Chunk(
        heading="Chapter 2",
        content="First Contact with Kubernetes\n\nBody text.",
    )
    assert _resolve_chapter_title(chunk) == "First Contact with Kubernetes"


def test_resolve_bare_chapter_falls_back_when_content_empty():
    """No content → fall back to heading."""
    chunk = Chunk(heading="CHAPTER 3", content="")
    assert _resolve_chapter_title(chunk) == "CHAPTER 3"


def test_resolve_bare_chapter_skips_long_first_line():
    """First content line > 80 chars is treated as body, not title → fallback."""
    long_line = "A" * 81
    chunk = Chunk(heading="CHAPTER 4", content=f"{long_line}\nShort line.")
    assert _resolve_chapter_title(chunk) == "CHAPTER 4"


def test_resolve_bare_chapter_skips_blank_lines():
    """Leading blank lines before the title are skipped."""
    chunk = Chunk(
        heading="CHAPTER 5",
        content="\n\nThe Real Title\n\nBody.",
    )
    assert _resolve_chapter_title(chunk) == "The Real Title"


# ---------------------------------------------------------------------------
# write_chunks
# ---------------------------------------------------------------------------

def test_writes_book_card(tmp_path: Path):
    """A 00-book.md with frontmatter is always created."""
    meta = {"title": "My Book", "author": "Me"}
    write_chunks(tmp_path, meta, [])
    book = tmp_path / "00-book.md"
    assert book.is_file()
    text = book.read_text()
    assert text.startswith("---\n")
    assert "title: My Book" in text
    assert "author: Me" in text
    assert text.endswith("---\n")


def test_writes_chunk_directory_and_file(tmp_path: Path):
    """Each chunk gets a numbered slug directory and .md file."""
    chunks = [Chunk(heading="Chapter 1", content="Hello.", level=2, sequence=0)]
    write_chunks(tmp_path, {"title": "T"}, chunks)
    d = tmp_path / "01-chapter-1"
    assert d.is_dir()
    f = d / "01-chapter-1.md"
    assert f.is_file()


def test_chunk_file_contains_frontmatter(tmp_path: Path):
    """Chunk files include YAML frontmatter."""
    chunks = [Chunk(heading="Intro", content="Hi.", level=3, sequence=0)]
    write_chunks(tmp_path, {}, chunks)
    text = (tmp_path / "01-intro" / "01-intro.md").read_text()
    assert text.startswith("---\n")
    assert "heading: Intro" in text
    assert "level: 3" in text
    assert "sequence: 0" in text


def test_chunk_file_contains_content_after_frontmatter(tmp_path: Path):
    """Content is written after the frontmatter block."""
    chunks = [Chunk(heading="Ch1", content="Some body text.", level=2, sequence=0)]
    write_chunks(tmp_path, {}, chunks)
    text = (tmp_path / "01-ch1" / "01-ch1.md").read_text()
    assert text.endswith("Some body text.")


def test_multiple_chunks_get_incrementing_numbers(tmp_path: Path):
    """Chunks get 01, 02, … sequence prefixes."""
    chunks = [
        Chunk(heading="First", content="A", level=2, sequence=0),
        Chunk(heading="Second", content="B", level=2, sequence=1),
    ]
    write_chunks(tmp_path, {}, chunks)
    assert (tmp_path / "01-first").is_dir()
    assert (tmp_path / "02-second").is_dir()


def test_empty_chunks_only_creates_book_card(tmp_path: Path):
    """With no chunks only 00-book.md is created."""
    write_chunks(tmp_path, {"title": "T"}, [])
    assert (tmp_path / "00-book.md").is_file()
    items = [p for p in tmp_path.iterdir()]
    assert len(items) == 1


def test_output_dir_created_if_missing(tmp_path: Path):
    """write_chunks creates the output directory."""
    nested = tmp_path / "a" / "b"
    assert not nested.exists()
    write_chunks(nested, {"title": "T"}, [])
    assert nested.is_dir()


def test_slugify_used_for_directory_and_file_names(tmp_path: Path):
    """Headings are slugified for filenames."""
    chunks = [Chunk(heading="**Special** Ch.", content="X", level=2, sequence=0)]
    write_chunks(tmp_path, {"title": "T"}, chunks)
    assert (tmp_path / "01-special-ch").is_dir()
    assert (tmp_path / "01-special-ch" / "01-special-ch.md").is_file()
