from ovbook.split import split_into_chunks


def test_split_basic():
    md = "# Book Title\n\n## Chapter 1\n\nContent 1\n\n## Chapter 2\n\nContent 2"
    chunks = split_into_chunks(md)
    assert len(chunks) == 2
    assert chunks[0].heading == "Chapter 1"
    assert chunks[1].heading == "Chapter 2"
    assert "Content 1" in chunks[0].content


def test_split_preserves_h2_only():
    """H1 is skipped (book title), only H2+ become chunks."""
    md = "# Book\n\n## Chapter 1\n\nBody\n\n### Subsection\n\nDetail\n\n## Chapter 2\n\nBody"
    chunks = split_into_chunks(md)
    assert len(chunks) == 3  # Chapter 1, Subsection, Chapter 2
    assert chunks[0].heading == "Chapter 1"
    assert chunks[1].heading == "Subsection"


def test_split_empty_body():
    chunks = split_into_chunks("")
    assert len(chunks) == 0


def test_split_no_headings():
    chunks = split_into_chunks("Just text\nwithout any headings")
    assert len(chunks) == 0


def test_split_chunk_has_content():
    md = "# Book\n\n## Chapter\n\nParagraph one.\n\nParagraph two."
    chunks = split_into_chunks(md)
    assert len(chunks) == 1
    assert "Paragraph one" in chunks[0].content
    assert "Paragraph two" in chunks[0].content
