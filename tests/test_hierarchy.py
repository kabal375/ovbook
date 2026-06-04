"""Tests for ovbook.split — hierarchy detection (chapters, sections, parts)."""

import pytest

from ovbook.split import split_into_chunks, Chunk


# ---------------------------------------------------------------------------
# Part / Chapter / Section hierarchy
# ---------------------------------------------------------------------------


def test_detect_chapter_number():
    """CHAPTER 3 in a heading → chapter_no=3."""
    md = "# Book\n\n## CHAPTER 3\n\nBody"
    chunks = split_into_chunks(md)
    assert len(chunks) == 1
    assert chunks[0].chapter_no == 3


def test_detect_chapter_and_section():
    """H2 = chapter, H3 = section within it."""
    md = "# Book\n\n## Chapter 2\n\nIntro\n\n### Section 4\n\nDetail"
    chunks = split_into_chunks(md)
    assert len(chunks) == 2
    assert chunks[0].chapter_no == 2
    assert chunks[0].section_no == 0  # section heading itself
    assert chunks[1].chapter_no == 2
    assert chunks[1].section_no == 4


def test_sequence_format():
    """Sequence is NNNN: chapter_no*100 + section_no."""
    md = "# Book\n\n## CHAPTER 3\n\nBody\n\n### 2. Some section\n\nDetail"
    chunks = split_into_chunks(md)
    assert chunks[0].sequence_str == "0300"
    assert chunks[1].sequence_str == "0302"


def test_part_resets_chapter_count():
    """Part I → chapters 1..N, Part II → chapters 1..M."""
    md = (
        "# Book\n\n"
        "# Part I\n\n"
        "## Chapter 1\n\nBody of 1\n\n"
        "## Chapter 2\n\nBody of 2\n\n"
        "# Part II\n\n"
        "## Chapter 1\n\nBody of 1"
    )
    chunks = split_into_chunks(md)
    assert len(chunks) == 3
    assert chunks[0].chapter_no == 1
    assert chunks[0].part == "Part I"
    assert chunks[1].chapter_no == 2
    assert chunks[1].part == "Part I"
    assert chunks[2].chapter_no == 1
    assert chunks[2].part == "Part II"


def test_no_part_no_chapter_regex():
    """Headings without 'Chapter' pattern → chapter_no stays 0."""
    md = "# Book\n\n## Introduction\n\nSome text\n\n## Summary\n\nFinal"
    chunks = split_into_chunks(md)
    assert len(chunks) == 2
    assert chunks[0].chapter_no == 0
    assert chunks[1].chapter_no == 0


def test_chapter_title_stored():
    """chapter_title from heading text."""
    md = "# Book\n\n## Chapter 5: Pods\n\nBody"
    chunks = split_into_chunks(md)
    assert chunks[0].chapter_title == "Chapter 5: Pods"
