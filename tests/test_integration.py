"""Integration tests for the full ovbook pipeline."""

from pathlib import Path

from ovbook.extract import extract, get_metadata
from ovbook.split import split_into_chunks
from ovbook.writer import write_chunks


def test_full_pipeline_pdf_roundtrip(tmp_path, pdf_fixture):
    """Run the full pipeline: pdf → markdown → chunks → writer → verify tree."""
    fixture = Path(pdf_fixture)

    md = extract(fixture)
    assert isinstance(md, str)
    assert len(md) > 0

    meta = get_metadata(fixture)
    assert meta["title"] == "Test Book"

    chunks = split_into_chunks(md)
    assert len(chunks) >= 2

    book_meta = {"id": "test-book", "title": "Test Book", "authors": ["Test Author"]}
    output_dir = tmp_path / "test-book"
    write_chunks(output_dir, book_meta, chunks)

    # Verify tree structure
    assert (output_dir / "00-book.md").exists()
    dirs = sorted([d for d in output_dir.iterdir() if d.is_dir()])
    assert len(dirs) >= 2

    # Book card has metadata
    book_card = (output_dir / "00-book.md").read_text()
    assert "title: Test Book" in book_card
    assert "---" in book_card

    # Each chunk dir has a .md file with content
    for d in dirs:
        files = list(d.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "---" in content
        assert len(content) > 20


def test_cli_dry_run(pdf_fixture):
    """Test CLI dry-run mode via Python invocation."""
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["convert", str(pdf_fixture), "--dry-run"])
    assert result.exit_code == 0
    assert "Test Book" in result.output
    assert "Chunks:" in result.output


def test_cli_convert(pdf_fixture, tmp_path):
    """Test CLI full convert."""
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["convert", str(pdf_fixture), "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert "Written" in result.output
    # Output dir is slugified from PDF title "Test Book" → "test-book"
    output_dir = tmp_path / "test-book"
    assert (output_dir / "00-book.md").exists()
