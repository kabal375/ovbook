"""Test the extract_pdf_rich body accumulation behavior."""

from ovbook.extract import extract_pdf_rich, extract_pdf
from ovbook.split import score_heading, filter_low_score_chunks, filter_toc_chunks, group_chunks_by_chapter
from ovbook.profile import detect_profile


def test_rich_extraction_returns_chunks(rich_pdf_fixture):
    """extract_pdf_rich returns a list of Chunks (not empty string)."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    assert len(chunks) > 0
    assert all(c.heading for c in chunks if c.level < 3)  # H1/H2 have headings


def test_body_text_is_accumulated_into_preceding_heading(rich_pdf_fixture):
    """Body-level text blocks are attached to the preceding heading chunk."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    profile = detect_profile(rich_pdf_fixture)

    for c in chunks:
        c.score = score_heading(c, profile["body_size"])

    # Chapter 1 heading chunk should have both body paragraphs
    ch1 = chunks[1]
    assert ch1.heading == "Chapter 1"
    assert "first body paragraph" in ch1.content, (
        f"Expected 'first body paragraph' in Chapter 1 content, got: {ch1.content[:100]}"
    )
    assert "second body paragraph" in ch1.content, (
        f"Expected 'second body paragraph' in Chapter 1 content, got: {ch1.content[:100]}"
    )


def test_subsection_gets_its_own_body_text(rich_pdf_fixture):
    """A subsection (H3) chunk receives its following body text."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    profile = detect_profile(rich_pdf_fixture)

    for c in chunks:
        c.score = score_heading(c, profile["body_size"])

    # 1.1 Details chunk (index 2) should have its body
    sub = chunks[2]
    assert "Details and Examples" in sub.heading
    assert "Detailed body content" in sub.content, (
        f"Expected 'Detailed body content' in subsection, got: {sub.content[:100]}"
    )


def test_chapter_sections_have_unique_content(rich_pdf_fixture):
    """Each heading chunk has its own body, not shared/copied."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    profile = detect_profile(rich_pdf_fixture)

    for c in chunks:
        c.score = score_heading(c, profile["body_size"])

    # Chapter 1 should NOT contain Chapter 2's content
    ch1 = chunks[1]
    ch2 = chunks[3]
    assert "second chapter" not in ch1.content, (
        "Chapter 1 accumulated Chapter 2's body text — flush_body boundary lost"
    )
    assert "first body paragraph" not in ch2.content, (
        "Chapter 2 got Chapter 1's body text — flush_body on wrong side"
    )


def test_body_accumulation_not_empty(rich_pdf_fixture):
    """Total body content across all chunks is non-trivial (>300 chars)."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    total_body = sum(len(c.content) for c in chunks)
    assert total_body > 300, (
        f"Body content too small ({total_body} chars) — body blocks may be discarded"
    )


def test_title_chunk_has_no_body_content(rich_pdf_fixture):
    """The title chunk (first heading) has no body text — nothing before it."""
    chunks = extract_pdf_rich(rich_pdf_fixture)
    title = chunks[0]
    assert not title.content.strip(), (
        "Title chunk should have empty content (no body before first content heading)"
    )


def test_full_pipeline_preserves_body_content(rich_pdf_fixture):
    """Running through the full CLI pipeline (filter + group) keeps body text."""
    profile = detect_profile(rich_pdf_fixture)
    raw = extract_pdf_rich(rich_pdf_fixture)

    for c in raw:
        c.score = score_heading(c, profile["body_size"])

    filtered = filter_toc_chunks(raw)
    filtered = filter_low_score_chunks(filtered, min_score=-1.0)
    groups = group_chunks_by_chapter(filtered, min_chapter_score=7.0)

    total_body = sum(len(c.content) for g in groups for c in g.chunks)
    assert total_body > 300, (
        f"Pipeline output has too little body content ({total_body} chars) — "
        "body text may be lost during filtering or grouping"
    )

    # Verify both chapters exist and have body
    assert len(groups) == 2, f"Expected 2 chapter groups, got {len(groups)}"
    assert any("Chapter 1" in g.chapter_title for g in groups), "Chapter 1 not found"
    assert any("Chapter 2" in g.chapter_title for g in groups), "Chapter 2 not found"
    for g in groups:
        chapter_body = sum(len(c.content) for c in g.chunks)
        assert chapter_body > 50, (
            f"Chapter '{g.chapter_title}' has only {chapter_body} body chars"
        )


def test_body_text_via_writer(rich_pdf_fixture, tmp_path):
    """Writing through write_chapter_groups produces files with body content."""
    from ovbook.writer import write_chapter_groups
    from ovbook.extract import get_pdf_metadata

    profile = detect_profile(rich_pdf_fixture)
    raw = extract_pdf_rich(rich_pdf_fixture)

    for c in raw:
        c.score = score_heading(c, profile["body_size"])

    filtered = filter_toc_chunks(raw)
    filtered = filter_low_score_chunks(filtered, min_score=-1.0)
    groups = group_chunks_by_chapter(filtered, min_chapter_score=7.0)
    book_meta = get_pdf_metadata(rich_pdf_fixture)

    write_chapter_groups(tmp_path, groups, book_meta, "rich-test-book")

    # Find all written .md files and verify they have content beyond frontmatter
    md_files = sorted(tmp_path.rglob("*.md"))
    assert len(md_files) > 1, f"Expected multiple .md files, got {len(md_files)}"

    total_body_chars = 0
    for md_file in md_files:
        content = md_file.read_text()
        # Content after frontmatter (after ---\n---)
        if "---" in content:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
                total_body_chars += len(body)

    assert total_body_chars > 300, (
        f"Written files have insufficient body content ({total_body_chars} chars)"
    )
