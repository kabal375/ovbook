"""ovbook CLI — convert books to structured markdown chunks for OpenViking."""

from pathlib import Path

import typer

from ovbook.writer import make_slug


app = typer.Typer(
    name="ovbook",
    help="Convert books to structured markdown chunks for OpenViking indexing.",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """ovbook — book-to-chunk converter for OpenViking."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def convert(
    input: Path = typer.Argument(
        ...,
        help="Path to input book file (.pdf / .fb2)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    format: str = typer.Option(
        None, "--format", "-f", help="Book format (auto-detect from extension)"
    ),
    output: Path = typer.Option(
        Path.cwd(),
        "--output",
        "-o",
        help="Output directory for chunk tree",
        file_okay=False,
        dir_okay=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show chunk structure without writing files",
    ),
    domain: list[str] = typer.Option(
        [], "--domain", help="Book domain (can be repeated)"),
    topic: list[str] = typer.Option(
        [], "--topic", help="Book topic (can be repeated)"),
    edition: str = typer.Option(
        None, "--edition", help="Book edition (e.g. '2nd')"
    ),
):
    """Convert a book file into structured markdown chunks for OpenViking.

    Detects format from file extension by default. Supports: pdf, fb2.
    Writes a chunk tree suitable for OpenViking watch indexing.
    """
    fmt = format or input.suffix.lstrip(".").lower()
    groups: list = []
    chunks: list = []

    if fmt == "pdf":
        from ovbook.extract import get_metadata, extract_pdf_rich
        from ovbook.split import filter_toc_chunks, filter_low_score_chunks, group_chunks_by_chapter
        from ovbook.profile import detect_profile

        profile = detect_profile(input)
        body_size = profile["body_size"]

        # body_size passed in — extract_pdf_rich skips its own scan
        raw_chunks = extract_pdf_rich(input, body_size=body_size)

        raw_chunks = filter_toc_chunks(raw_chunks)
        raw_chunks = filter_low_score_chunks(raw_chunks, min_score=-1.0)

        groups = group_chunks_by_chapter(raw_chunks, min_chapter_score=7.0)
        for g in groups:
            chunks.extend(g.chunks)

        book_meta = get_metadata(input)

        if not profile["encoding_ok"]:
            typer.echo(
                "Warning: Encoding issues detected — consider OCR pipeline",
                err=True,
            )

    elif fmt == "fb2":
        from ovbook.extract import extract_fb2, get_fb2_metadata
        from ovbook.split import split_into_chunks, filter_content

        markdown = extract_fb2(input)
        book_meta = get_fb2_metadata(input)
        chunks = split_into_chunks(markdown)
        chunks = filter_content(chunks)

    else:
        typer.echo(f"Error: unsupported format '{fmt}' (supported: pdf, fb2)", err=True)
        raise typer.Exit(1)

    if domain:
        book_meta["domains"] = domain
    if topic:
        book_meta["topics"] = topic
    if edition:
        book_meta["edition"] = edition

    if dry_run:
        _print_dry_run(book_meta, groups if fmt == "pdf" else None, chunks)
        return

    from ovbook.writer import write_chapter_groups, write_chunks

    slug = make_slug(book_meta.get("title", input.stem))
    if fmt == "pdf":
        write_chapter_groups(output, groups, book_meta, slug)
        total = sum(len(g.chunks) for g in groups)
        typer.echo(f"Written {total} chunks ({len(groups)} chapters) to {output / slug}")
    else:
        output_path = output / slug
        output_path.mkdir(parents=True, exist_ok=True)
        write_chunks(output_path, book_meta, chunks)
        typer.echo(f"Written {len(chunks)} chunks to {output_path}")


def _print_dry_run(book_meta: dict, groups: list | None, chunks: list) -> None:
    """Print a dry-run summary of what would be written."""
    typer.echo(f"Book: {book_meta.get('title', '(no title)')}")
    if book_meta.get("authors"):
        typer.echo(f"Authors: {', '.join(book_meta['authors'])}")
    if book_meta.get("domains"):
        typer.echo(f"Domains: {', '.join(book_meta['domains'])}")
    if book_meta.get("topics"):
        typer.echo(f"Topics: {', '.join(book_meta['topics'])}")

    if groups is not None:
        total = sum(len(g.chunks) for g in groups)
        typer.echo(f"Chapters: {len(groups)}")
        typer.echo(f"Chunks: {total}")
        for g in groups:
            for c in g.chunks:
                preview = c.content[:80].replace("\n", " ").strip()
                typer.echo(f"  [{c.sequence + 1:02d}] {c.heading}")
                if preview:
                    typer.echo(f"       {preview}...")
    else:
        typer.echo(f"Chunks: {len(chunks)}")
        for c in chunks:
            preview = c.content[:80].replace("\n", " ").strip()
            typer.echo(f"  [{c.sequence + 1:02d}] {c.heading}")
            if preview:
                typer.echo(f"       {preview}...")
