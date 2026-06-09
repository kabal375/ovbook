"""Tests for ovbook CLI — metadata flags (domain, topic, edition)."""

from typer.testing import CliRunner

from ovbook.cli import app


def test_domain_flag(tech_lib, pdf_fixture):
    """--domain adds domains to book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
        "--domain", "devops-sre",
    ])
    assert result.exit_code == 0
    book_dir = tech_lib / "test-book"
    card = (book_dir / "00-book.md").read_text()
    assert "domains:" in card
    assert "operating-systems" in card
    assert "devops-sre" in card


def test_topic_flag(tech_lib, pdf_fixture):
    """--topic adds topics to book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
        "--topic", "containers",
        "--topic", "ci-cd",
    ])
    assert result.exit_code == 0
    book_dir = tech_lib / "test-book"
    card = (book_dir / "00-book.md").read_text()
    assert "topics:" in card
    assert "containers" in card
    assert "ci-cd" in card


def test_edition_flag(tech_lib, pdf_fixture):
    """--edition sets edition in book metadata."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
        "--edition", "2nd",
    ])
    assert result.exit_code == 0
    book_dir = tech_lib / "test-book"
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


def test_domains_written_to_book_card(tech_lib, pdf_fixture):
    """--domain / --topic land in the book card frontmatter."""
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems", "--topic", "kubernetes",
    ])
    assert result.exit_code == 0
    card = next(tech_lib.rglob("00-book.md")).read_text()
    assert "operating-systems" in card
    assert "kubernetes" in card
