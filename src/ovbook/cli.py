"""ovbook CLI — convert books to structured markdown chunks for OpenViking."""

from pathlib import Path

import typer

from ovbook.readers import get_reader
from ovbook.writer import make_slug, write_chapter_groups


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
        help="Path to input book file (.pdf / .fb2 / .epub)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    format: str = typer.Option(
        None, "--format", "-f", help="Book format (auto-detect from extension)"
    ),
    output: Path = typer.Option(
        Path.cwd(), "--output", "-o",
        help="Output directory for chunk tree",
        file_okay=False, dir_okay=True,
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show chunk structure without writing files",
    ),
    domain: list[str] = typer.Option(
        [], "--domain", help="Book domain (can be repeated)"),
    topic: list[str] = typer.Option(
        [], "--topic", help="Book topic (can be repeated)"),
    edition: str = typer.Option(
        None, "--edition", help="Book edition (e.g. '2nd')"),
):
    """Convert a book file into structured markdown chunks for OpenViking.

    Detects format from file extension by default. Supports: pdf, fb2, epub.
    """
    fmt = format or input.suffix.lstrip(".").lower()

    try:
        reader = get_reader(fmt)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    content = reader(input)
    meta = content.meta
    groups = content.groups

    if domain:
        meta["domains"] = domain
    if topic:
        meta["topics"] = topic
    if edition:
        meta["edition"] = edition

    if dry_run:
        _print_dry_run(meta, groups)
        return

    slug = make_slug(meta.get("title", input.stem))
    write_chapter_groups(output, groups, meta, slug)
    total = sum(len(g.chunks) for g in groups)
    typer.echo(f"Written {total} chunks ({len(groups)} chapters) to {output / slug}")


def _print_dry_run(meta: dict, groups: list) -> None:
    """Print a dry-run summary of what would be written."""
    typer.echo(f"Book: {meta.get('title', '(no title)')}")
    if meta.get("authors"):
        typer.echo(f"Authors: {', '.join(meta['authors'])}")
    if meta.get("domains"):
        typer.echo(f"Domains: {', '.join(meta['domains'])}")
    if meta.get("topics"):
        typer.echo(f"Topics: {', '.join(meta['topics'])}")

    total = sum(len(g.chunks) for g in groups)
    typer.echo(f"Chapters: {len(groups)}")
    typer.echo(f"Chunks: {total}")
    for g in groups:
        for c in g.chunks:
            preview = c.content[:80].replace("\n", " ").strip()
            typer.echo(f"  [{c.sequence + 1:02d}] {c.heading}")
            if preview:
                typer.echo(f"       {preview}...")
