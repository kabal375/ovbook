"""ovbook CLI — convert books to structured markdown chunks for OpenViking."""

from pathlib import Path

import typer

app = typer.Typer(
    name="ovbook",
    help="Convert books to structured markdown chunks for OpenViking indexing.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
):
    """ovbook — book-to-chunk converter for OpenViking."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def convert(
    input: Path = typer.Argument(
        ...,
        help="Path to input book file (.fb2)",
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
):
    """Convert a book file into structured markdown chunks for OpenViking.

    Detects format from file extension by default. Supports: fb2.
    Writes a chunk tree suitable for OpenViking watch indexing.
    """
    fmt = format or input.suffix.lstrip(".").lower()

    if fmt == "fb2":
        from ovbook.extract import extract_fb2, get_fb2_metadata
        from ovbook.split import split_into_chunks

        markdown = extract_fb2(input)
        book_meta = get_fb2_metadata(input)
        chunks = split_into_chunks(markdown)
    else:
        typer.echo(f"Error: unsupported format '{fmt}' (supported: fb2)", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Book: {book_meta.get('title', input.name)}")
        if book_meta.get("authors"):
            typer.echo(f"Authors: {', '.join(book_meta['authors'])}")
        typer.echo(f"Chunks: {len(chunks)}")
        for c in chunks:
            preview = c.content[:80].replace("\n", " ").strip()
            typer.echo(f"  [{c.sequence + 1:02d}] {c.heading}")
            if preview:
                typer.echo(f"       {preview}...")
        return

    from ovbook.writer import write_chunks

    output_path = output / input.stem
    output_path.mkdir(parents=True, exist_ok=True)
    write_chunks(output_path, book_meta, chunks)
    typer.echo(f"Written {len(chunks)} chunks to {output_path}")
