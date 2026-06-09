"""Tests for the ovbook CLI entry point."""

from typer.testing import CliRunner

from ovbook.cli import app

runner = CliRunner()


def test_convert_dry_run_shows_book_and_chunks(pdf_fixture):
    result = runner.invoke(app, ["convert", str(pdf_fixture), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Book:" in result.output
    assert "Chapters:" in result.output
    assert "Chunks:" in result.output


def test_convert_writes_flat_chapter_files(pdf_fixture, tech_lib):
    """Depth guard: chapters are .md files directly under book dir, no subdirs."""
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])
    assert result.exit_code == 0, result.output

    book_dirs = [d for d in tech_lib.iterdir() if d.is_dir()]
    assert len(book_dirs) == 1, "Expected exactly one book directory"

    book_dir = book_dirs[0]
    assert (book_dir / "00-book.md").exists()

    # Chapter files are .md directly under book_dir, not in subdirectories
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) >= 1

    # No chapter subdirectories should exist
    subdirs = [d for d in book_dir.iterdir() if d.is_dir()]
    assert subdirs == [], f"Unexpected subdirectories: {subdirs}"


def test_convert_chapter_files_have_book_id(pdf_fixture, tech_lib):
    """Each chapter file must declare book_id in its frontmatter."""
    runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])

    chapter_files = [
        f for f in tech_lib.rglob("*.md")
        if f.name != "00-book.md"
    ]
    assert len(chapter_files) >= 1

    for f in chapter_files:
        content = f.read_text()
        assert "book_id:" in content, f"{f.name} is missing book_id in frontmatter"


def test_convert_chapter_files_have_sequential_local_numbers(pdf_fixture, tech_lib):
    """Chapter files are numbered 01-, 02-, ... starting from 1 (not global index)."""
    runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])

    book_dir = next(d for d in tech_lib.iterdir() if d.is_dir())
    chapter_files = sorted(
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    )
    for i, f in enumerate(chapter_files, start=1):
        assert f.name.startswith(f"{i:02d}-"), (
            f"Expected file #{i} to start with '{i:02d}-', got '{f.name}'"
        )


def test_dry_run_does_not_write_files(pdf_fixture, tmp_path):
    runner.invoke(app, ["convert", str(pdf_fixture), "-o", str(tmp_path), "--dry-run"])
    assert list(tmp_path.iterdir()) == [], "dry-run must not write any files"


def test_no_subcommand_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "convert" in result.output


def test_unsupported_format_exits_nonzero(tmp_path):
    fake = tmp_path / "book.xyz"
    fake.write_text("data")
    result = runner.invoke(app, ["convert", str(fake)])
    assert result.exit_code != 0 or "unsupported" in result.output


def test_convert_with_all_metadata_flags(pdf_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "devops-sre",
        "--topic", "kubernetes",
        "--edition", "2nd",
    ])
    assert result.exit_code == 0, result.output

    book_cards = list(tech_lib.rglob("00-book.md"))
    assert len(book_cards) == 1
    content = book_cards[0].read_text()
    assert "devops-sre" in content
    assert "kubernetes" in content
    assert "2nd" in content


def test_convert_success_message_contains_written(pdf_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])
    assert "Written" in result.output


def test_convert_fb2_writes_chapter_files(fb2_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(fb2_fixture), "-o", str(tech_lib),
        "--domain", "software-development",
    ])
    assert result.exit_code == 0, result.output
    book_dir = next(d for d in tech_lib.iterdir() if d.is_dir())
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) == 2
    assert "book_id:" in chapter_files[0].read_text()


def test_convert_epub_writes_chapter_files(epub_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(epub_fixture), "-o", str(tech_lib),
        "--domain", "software-development",
    ])
    assert result.exit_code == 0, result.output
    book_dir = next(d for d in tech_lib.iterdir() if d.is_dir())
    assert (book_dir / "00-book.md").exists()
    chapter_files = [
        f for f in book_dir.iterdir()
        if f.suffix == ".md" and f.name != "00-book.md"
    ]
    assert len(chapter_files) == 2


def test_convert_fb2_dry_run(fb2_fixture):
    result = runner.invoke(app, ["convert", str(fb2_fixture), "--dry-run"])
    assert result.exit_code == 0
    assert "FB2 Test Book" in result.output
    assert "Chapters:" in result.output


# ── controlled-vocabulary enforcement (real writes) ──────────────────────────


def test_convert_without_domain_fails(pdf_fixture, tech_lib):
    """A real write with no --domain must hard-fail, not silently produce junk."""
    result = runner.invoke(app, ["convert", str(pdf_fixture), "-o", str(tech_lib)])
    assert result.exit_code != 0
    assert "domain" in result.output.lower()
    assert list(tech_lib.iterdir()) == [], "must not write without classification"


def test_convert_unknown_domain_fails(pdf_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib), "--domain", "kubernetes",
    ])
    assert result.exit_code != 0
    assert "kubernetes" in result.output


def test_convert_missing_vocabulary_fails(pdf_fixture, tmp_path):
    """No vocabulary.yaml above the output → cannot validate → hard fail."""
    out = tmp_path / "nowhere"
    out.mkdir()
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(out), "--domain", "operating-systems",
    ])
    assert result.exit_code != 0
    assert "vocabulary.yaml" in result.output


def test_convert_valid_domain_succeeds(pdf_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems",
    ])
    assert result.exit_code == 0, result.output
    card = next(tech_lib.rglob("00-book.md")).read_text()
    assert "operating-systems" in card
    assert "status:" in card  # canonical fields present


def test_convert_normalizes_topic_format(pdf_fixture, tech_lib):
    result = runner.invoke(app, [
        "convert", str(pdf_fixture), "-o", str(tech_lib),
        "--domain", "operating-systems", "--topic", "Memory Management",
    ])
    assert result.exit_code == 0, result.output
    card = next(tech_lib.rglob("00-book.md")).read_text()
    assert "memory-management" in card
