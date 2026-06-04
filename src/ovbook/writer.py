"""Write chunk trees to disk with Part/Chapter hierarchy support."""

import re
from pathlib import Path

from ovbook.frontmatter import make_book_frontmatter, make_chunk_frontmatter
from ovbook.split import Chunk


def _slugify(text: str) -> str:
    """Convert heading text to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def write_chunks(
    output_dir: Path,
    book_meta: dict,
    chunks: list[Chunk],
    slug: str | None = None,
) -> None:
    """Write chunk trees to *output_dir*.

    Structure without Part:
        slug/
            00-book.md
            NN-chunk-slug/
                NN-chunk-slug.md

    Structure with Part:
        slug/
            00-book.md
            NN-part-slug/
                01-chapter-slug.md
                02-chapter-slug.md
    """
    target = output_dir / slug if slug else output_dir
    target.mkdir(parents=True, exist_ok=True)

    # --- 00-book.md ---
    book_card = make_book_frontmatter(book_meta)
    (target / "00-book.md").write_text(book_card)

    # --- Check if we have Parts ---
    has_parts = any(c.part for c in chunks)

    if has_parts:
        _write_with_parts(target, chunks)
    else:
        _write_flat(target, chunks)


def _write_flat(target: Path, chunks: list[Chunk]) -> None:
    """Group chunks by chapter_no when available, otherwise flat."""
    from collections import OrderedDict

    has_chapters = any(c.chapter_no > 0 for c in chunks)
    if has_chapters:
        _write_by_chapter(target, chunks)
    else:
        _write_each_chunk_dir(target, chunks)


def _write_each_chunk_dir(target: Path, chunks: list[Chunk]) -> None:
    """Original flat behavior: each chunk in its own NN-slug/ directory."""
    for chunk in chunks:
        slug = _slugify(chunk.heading)
        seq_str = f"{chunk.sequence + 1:02d}"
        dir_name = f"{seq_str}-{slug}"
        file_name = f"{seq_str}-{slug}.md"

        chunk_dir = target / dir_name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        _write_chunk(chunk_dir / file_name, chunk)


def _write_by_chapter(target: Path, chunks: list[Chunk]) -> None:
    """Group chunks by chapter_no into chapter directories.

        slug/
            00-book.md
            chapter-01-title/
                01-chunk-slug.md
                02-chunk-slug.md
            chapter-05-title/
                126-chunk-slug.md
    """
    from collections import OrderedDict

    pre_chapter: list[Chunk] = []
    chapters: OrderedDict[int, list[Chunk]] = OrderedDict()

    for chunk in chunks:
        if chunk.chapter_no == 0:
            pre_chapter.append(chunk)
        else:
            chapters.setdefault(chunk.chapter_no, []).append(chunk)

    # Pre-chapter chunks (foreword, introduction without "Chapter" heading)
    _write_each_chunk_dir(target, pre_chapter)

    # Grouped by chapter
    for chapter_no, chapter_chunks in chapters.items():
        chapter_title = chapter_chunks[0].chapter_title or f"Chapter {chapter_no}"
        chapter_slug = _slugify(chapter_title)
        chapter_dir = target / f"chapter-{chapter_no:02d}-{chapter_slug}"

        for chunk in chapter_chunks:
            slug = _slugify(chunk.heading)
            seq_str = f"{chunk.sequence + 1:02d}"
            file_name = f"{seq_str}-{slug}.md"
            chunk_path = chapter_dir / file_name
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            _write_chunk(chunk_path, chunk)


def _write_chunk(path: Path, chunk: Chunk) -> None:
    """Write a single chunk file with frontmatter."""
    front = make_chunk_frontmatter({
        "heading": chunk.heading,
        "level": chunk.level,
        "sequence": chunk.sequence,
        "chapter_no": chunk.chapter_no or None,
        "chapter_title": chunk.chapter_title or None,
        "section_no": chunk.section_no or None,
        "section_title": chunk.section_title or None,
        "part": chunk.part or None,
        "sequence_str": chunk.sequence_str or None,
    })
    body = chunk.content if chunk.content else ""
    path.write_text(front + body)


def _write_with_parts(target: Path, chunks: list[Chunk]) -> None:
    """Group chunks by Part into part directories, then by chapter inside each part."""
    from collections import OrderedDict

    parts: OrderedDict[str, list[Chunk]] = OrderedDict()

    for chunk in chunks:
        part_key = chunk.part or ""
        if part_key not in parts:
            parts[part_key] = []
        parts[part_key].append(chunk)

    for part_idx, (part_name, part_chunks) in enumerate(parts.items()):
        part_slug = _slugify(part_name) if part_name else "misc"
        part_dir = target / f"{part_idx + 1:02d}-{part_slug}"
        part_dir.mkdir(parents=True, exist_ok=True)

        # Within a part, group by chapter
        chapters: OrderedDict[int, list[Chunk]] = OrderedDict()
        for chunk in part_chunks:
            chapters.setdefault(chunk.chapter_no, []).append(chunk)

        for chapter_no, chapter_chunks in chapters.items():
            if chapter_no == 0:
                # Pre-chapter chunks in the part
                for chunk in chapter_chunks:
                    slug = _slugify(chunk.heading)
                    seq_str = f"{chunk.sequence + 1:02d}"
                    dir_name = f"{seq_str}-{slug}"
                    file_name = f"{seq_str}-{slug}.md"
                    chunk_dir = part_dir / dir_name
                    chunk_dir.mkdir(parents=True, exist_ok=True)
                    _write_chunk(chunk_dir / file_name, chunk)
            else:
                chapter_title = chapter_chunks[0].chapter_title or f"Chapter {chapter_no}"
                chapter_slug = _slugify(chapter_title)
                chapter_dir = part_dir / f"chapter-{chapter_no:02d}-{chapter_slug}"

                for chunk in chapter_chunks:
                    slug = _slugify(chunk.heading)
                    seq_str = f"{chunk.sequence + 1:02d}"
                    file_name = f"{seq_str}-{slug}.md"
                    chunk_path = chapter_dir / file_name
                    chunk_path.parent.mkdir(parents=True, exist_ok=True)
                    _write_chunk(chunk_path, chunk)
