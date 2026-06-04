from ovbook.split import split_into_chunks, score_heading, Chunk
from ovbook.split import group_chunks_by_chapter, ChapterGroup
from ovbook.split import filter_toc_chunks, filter_low_score_chunks


def test_group_by_chapter_collects_subsections():
    """Subsections (H3) are grouped under their parent chapter."""
    chunks = [
        Chunk(heading="Chapter 1", content="Intro text", level=2,
              chapter_no=1, chapter_title="Chapter 1", score=10.0),
        Chunk(heading="1.1 Background", content="Background text", level=3,
              chapter_no=1, section_no=1, score=5.0),
        Chunk(heading="1.2 Problem", content="Problem text", level=3,
              chapter_no=1, section_no=2),
        Chunk(heading="Chapter 2", content="Second chapter", level=2,
              chapter_no=2, chapter_title="Chapter 2", score=10.0),
        Chunk(heading="2.1 Method", content="Method text", level=3,
              chapter_no=2, section_no=1),
    ]
    groups = group_chunks_by_chapter(chunks, min_chapter_score=6.0)
    assert len(groups) == 2
    assert len(groups[0].chunks) == 3
    assert groups[0].chunks[0].heading == "Chapter 1"
    assert len(groups[1].chunks) == 2
    assert groups[1].chunks[1].heading == "2.1 Method"


def test_filter_toc_chunks_removes_toc_entries():
    """Chunks with looks_like_toc_entry are removed."""
    chunks = [
        Chunk(heading="Chapter 1: Intro...........1", content="...", level=2, looks_like_toc_entry=True),
        Chunk(heading="1.1 Background.............5", content="...", level=3, looks_like_toc_entry=True),
        Chunk(heading="Chapter 1", content="Real content", level=2, looks_like_toc_entry=False),
    ]
    filtered = filter_toc_chunks(chunks)
    assert len(filtered) == 1
    assert filtered[0].heading == "Chapter 1"


def test_filter_low_score_removes_noise():
    """Chunks with score <= threshold are removed."""
    chunks = [
        Chunk(heading="x", content="", level=2, score=-2.0),
        Chunk(heading="Chapter 2", content="Real", level=2, score=10.0),
    ]
    filtered = filter_low_score_chunks(chunks, min_score=0.0)
    assert len(filtered) == 1
    assert filtered[0].heading == "Chapter 2"


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
