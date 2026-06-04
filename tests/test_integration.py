"""Integration tests for the full ovbook pipeline."""

from pathlib import Path
import shutil

from ovbook.extract import extract_fb2
from ovbook.split import split_into_chunks
from ovbook.writer import write_chunks


def test_full_pipeline_roundtrip(tmp_path):
    """Run the full pipeline: fb2 → markdown → chunks → writer → verify tree."""
    fixture = Path(__file__).parent / "fixtures" / "sample.fb2"

    md = extract_fb2(fixture)
    assert md.startswith("# ")
    assert "Chapter 1" in md

    chunks = split_into_chunks(md)
    assert len(chunks) >= 2

    book_meta = {"id": "sample", "title": "Test Book", "authors": ["Test Author"]}
    output_dir = tmp_path / "sample"
    write_chunks(output_dir, book_meta, chunks)

    assert (output_dir / "00-book.md").exists()
    dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    assert len(dirs) == len(chunks)

    # Verify book card has metadata
    book_card = (output_dir / "00-book.md").read_text()
    assert "title: Test Book" in book_card
    assert "authors:" in book_card
    assert "---" in book_card

    # Verify chunk files have content
    for d in sorted(dirs):
        files = list(d.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "---" in content  # has frontmatter
        assert len(content) > 20  # has actual content
