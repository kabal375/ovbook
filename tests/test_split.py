from ovbook.split import split_into_chunks, score_heading, Chunk


def test_score_heading_scores_correctly():
    """Verify score_heading() assigns correct scores for various inputs."""
    body_size = 12.0

    # Chapter heading — strong positive
    ch = Chunk(heading="Chapter 1: Introduction", content="", level=2, font_size=20.0, is_bold=True)
    s = score_heading(ch, body_size)
    assert s >= 8, f"Chapter heading should score high, got {s}"

    # TOC entry — strong negative
    toc = Chunk(heading="Chapter 1: Introduction......................1", content="", level=2, font_size=12.0)
    s = score_heading(toc, body_size)
    assert s <= 0, f"TOC entry should score low or negative, got {s}"

    # Index letter — negative
    idx = Chunk(heading="A", content="", level=2, font_size=14.0)
    s = score_heading(idx, body_size)
    assert s <= 0, f"Index letter should score negative, got {s}"

    # Short heading (diagram noise) — negative
    short = Chunk(heading="x", content="", level=2, font_size=18.0)
    s = score_heading(short, body_size)
    assert s < 0, f"Short heading should be negative, got {s}"

    # Numbered heading — strong positive even if font not huge
    numbered = Chunk(heading="1 Scope", content="", level=2, font_size=13.0)
    s = score_heading(numbered, body_size)
    assert s >= 3, f"Numbered heading should score positive, got {s}"


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
