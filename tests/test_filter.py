"""Tests for ovbook.split — content filtering (front matter, index)."""

from ovbook.split import split_into_chunks, filter_content


def test_front_matter_removed():
    """Chunks before first Chapter/Part/Appendix are removed."""
    md = (
        "# Book\n\n"
        "## Introduction\n\nSome intro\n\n"
        "## About This Book\n\nMore intro\n\n"
        "## CHAPTER 1\n\nReal content\n\n"
        "## CHAPTER 2\n\nMore content"
    )
    chunks = split_into_chunks(md)
    filtered = filter_content(chunks)
    assert len(filtered) == 2
    assert filtered[0].heading == "CHAPTER 1"
    assert filtered[1].heading == "CHAPTER 2"


def test_index_removed():
    """Chunks from 'Index' onward are removed."""
    md = (
        "# Book\n\n"
        "## Chapter 1\n\nBody\n\n"
        "## Index\n\nA, 1\n\nB, 2\n\n"
        "## About the Authors\n\nBio"
    )
    chunks = split_into_chunks(md)
    filtered = filter_content(chunks)
    assert len(filtered) == 1
    assert filtered[0].heading == "Chapter 1"


def test_appendix_kept():
    """Appendix is kept as content."""
    md = (
        "# Book\n\n"
        "## Chapter 1\n\nBody\n\n"
        "## Appendix A\n\nReference\n\n"
        "## Index\n\nA, 1"
    )
    chunks = split_into_chunks(md)
    filtered = filter_content(chunks)
    assert len(filtered) == 2
    assert filtered[0].heading == "Chapter 1"
    assert filtered[1].heading == "Appendix A"


def test_no_front_matter_no_op():
    """Without front matter or index, all chunks pass through."""
    md = (
        "# Book\n\n"
        "## Chapter 1\n\nBody\n\n"
        "## Chapter 2\n\nMore"
    )
    chunks = split_into_chunks(md)
    filtered = filter_content(chunks)
    assert len(filtered) == 2


def test_empty_chunks_no_op():
    """Empty chunks list returns empty."""
    assert filter_content([]) == []


def test_where_to_go_next_filtered():
    """'Where to Go Next' and everything after is removed."""
    md = (
        "# Book\n\n"
        "## Chapter 1\n\nBody\n\n"
        "## Where to Go Next\n\nResources\n\n"
        "## Second Edition Notes\n\nNotes\n\n"
        "## About the Authors\n\nBio"
    )
    chunks = split_into_chunks(md)
    filtered = filter_content(chunks)
    assert len(filtered) == 1
    assert filtered[0].heading == "Chapter 1"
