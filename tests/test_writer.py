"""Tests for ovbook.writer."""

from ovbook.split import Chunk
from ovbook.writer import _slugify, _resolve_chapter_title


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
