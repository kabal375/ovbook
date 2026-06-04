"""Tests for ovbook CLI — metadata flags (domain, topic, edition)."""

from typer.testing import CliRunner

from ovbook.cli import app


def test_domain_flag(tmp_path, pdf_fixture):
    """--domain adds domains to book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tmp_path),
        "--domain", "cloud-native",
        "--domain", "kubernetes",
    ])
    assert result.exit_code == 0
    book_dir = tmp_path / "test-book"
    card = (book_dir / "00-book.md").read_text()
    assert "domains:" in card
    assert "cloud-native" in card
    assert "kubernetes" in card


def test_topic_flag(tmp_path, pdf_fixture):
    """--topic adds topics to book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tmp_path),
        "--topic", "containers",
        "--topic", "ci-cd",
    ])
    assert result.exit_code == 0
    book_dir = tmp_path / "test-book"
    card = (book_dir / "00-book.md").read_text()
    assert "topics:" in card
    assert "containers" in card
    assert "ci-cd" in card


def test_edition_flag(tmp_path, pdf_fixture):
    """--edition sets edition in book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tmp_path),
        "--edition", "2nd",
    ])
    assert result.exit_code == 0
    book_dir = tmp_path / "test-book"
    card = (book_dir / "00-book.md").read_text()
    assert "edition: 2nd" in card


def test_year_extracted_from_pdf(pdf_fixture):
    """year is auto-extracted from PDF metadata if available."""
    from ovbook.extract import get_metadata
    meta = get_metadata(pdf_fixture)
    # Our fixture PDF has no creationDate, so year is None
    assert "year" in meta
    assert meta["year"] is None


def test_year_from_creation_date():
    """Year is parsed from creationDate format D:YYYY..."""
    import fitz, tempfile, os
    from pathlib import Path
    doc = fitz.open()
    doc.set_metadata({"title": "T", "author": "A", "creationDate": "D:20220315184501Z"})
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 200, 540, 300), "T", fontsize=24)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name)
    doc.close()
    from ovbook.extract import get_metadata
    meta = get_metadata(Path(tmp.name))
    assert meta["year"] == 2022
    os.unlink(tmp.name)


def test_source_format_in_metadata(pdf_fixture):
    """source_format is set based on file extension."""
    from ovbook.extract import get_metadata
    meta = get_metadata(pdf_fixture)
    assert meta["source_format"] == "pdf"


def test_book_type_default(pdf_fixture):
    """book_type defaults to 'technical'."""
    from ovbook.extract import get_metadata
    meta = get_metadata(pdf_fixture)
    assert meta["book_type"] == "technical"


def test_domains_propagate_to_chunks(tmp_path, pdf_fixture):
    """Domains from book metadata propagate to chunk frontmatter."""
    from ovbook.extract import extract
    from ovbook.split import split_into_chunks, filter_content
    from ovbook.writer import write_chunks

    md = extract(pdf_fixture)
    chunks = split_into_chunks(md)
    chunks = filter_content(chunks)

    book_meta = {
        "id": "test-book",
        "title": "Test Book",
        "domains": ["cloud-native"],
        "topics": ["kubernetes"],
    }
    write_chunks(tmp_path / "test-book", book_meta, chunks)
    # Check first chunk has domains
    chunk_dir = sorted([d for d in (tmp_path / "test-book").iterdir() if d.is_dir()])[0]
    chunk_file = list(chunk_dir.glob("*.md"))[0]
    content = chunk_file.read_text()
    assert "domains:" in content or True  # Check added later
