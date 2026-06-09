"""Integration tests for the full ovbook pipeline via readers."""

from ovbook.readers import get_reader
from ovbook.writer import write_chapter_groups, make_slug


def test_pdf_pipeline_roundtrip(tmp_path, pdf_fixture):
    content = get_reader("pdf")(pdf_fixture)
    assert content.meta["title"] == "Test Book"
    assert len(content.groups) >= 1

    slug = make_slug(content.meta["title"])
    write_chapter_groups(tmp_path, content.groups, content.meta, slug)

    book_dir = tmp_path / slug
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) >= 1
    assert "book_id:" in chapter_files[0].read_text()


def test_cli_convert_pdf(pdf_fixture, tech_lib):
    from typer.testing import CliRunner
    from ovbook.cli import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])
    assert result.exit_code == 0
    assert "Written" in result.output
    assert (tech_lib / "test-book" / "00-book.md").exists()
