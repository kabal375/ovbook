"""Write chunk trees to disk with Part/Chapter hierarchy support."""

import re
from pathlib import Path

from ovbook.frontmatter import make_book_frontmatter, make_chunk_frontmatter
from ovbook.split import Chunk, ChapterGroup


def _slugify(text: str) -> str:
    """Convert heading text to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_slug(text: str, max_len: int = 60) -> str:
    """Create a filesystem-safe slug from text, truncated to max_len."""
    slug = _slugify(text)
    return slug[:max_len] if slug else "untitled"


# Matches bare "CHAPTER 1", "Chapter 3", "ГЛАВА 2" — no descriptive suffix.
_BARE_CHAPTER_RE = re.compile(
    r"^(?:CHAPTER|Chapter|Глава|ГЛАВА|SECTION|Section)\s+\d+\.?\s*$",
    re.IGNORECASE,
)


def _resolve_chapter_title(chunk: Chunk) -> str:
    """Return the best available chapter title for a chunk.

    PDFs often use bare "CHAPTER 1" as the heading, with the real title
    ("Revolution in the Cloud") as the first line of body text.
    This function returns that first content line when the heading is bare,
    falling back to the heading itself if content is empty or too long.
    """
    heading = chunk.heading.strip()

    # Heading already has descriptive content — use it directly.
    if not _BARE_CHAPTER_RE.match(heading):
        return heading

    # Bare "CHAPTER N" — look for descriptive title in first content line.
    if chunk.content:
        for line in chunk.content.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) <= 80:
                return stripped

    return heading


# ── PDF path: depth-guarded chapter files ────────────────────────────────────


def write_chapter_groups(
    output_dir: Path,
    groups: list[ChapterGroup],
    book_meta: dict,
    book_slug: str,
) -> None:
    """Write depth-guarded output: one .md file per chapter.

    All subsections are embedded as ## headings inside the chapter file.

    Structure:
        book-slug/
            00-book.md
            01-<chapter-title-slug>.md
            02-<chapter-title-slug>.md
    """
    book_id = book_meta.get("id", book_slug)
    book_dir = output_dir / book_slug
    book_dir.mkdir(parents=True, exist_ok=True)

    (book_dir / "00-book.md").write_text(make_book_frontmatter(book_meta))

    for seq, group in enumerate(groups, start=1):
        title = _resolve_chapter_title(group.chunks[0])
        chapter_slug = make_slug(title)
        chapter_file = book_dir / f"{seq:02d}-{chapter_slug}.md"
        _write_chapter_file(chapter_file, group, book_id, seq)


def _write_chapter_file(path: Path, group: ChapterGroup, book_id: str, seq: int) -> None:
    """Write all chunks in a chapter group into a single .md file.

    The chapter heading chunk provides frontmatter. Subsequent chunks
    (subsections) are appended as ## headings with their body text.
    """
    chapter_chunk = group.chunks[0]
    resolved_title = _resolve_chapter_title(chapter_chunk)

    front_meta: dict = {
        "book_id": book_id,
        "chapter_no": group.chapter_no,
        "chapter_title": resolved_title,
        "sequence": seq,
    }
    if chapter_chunk.part:
        front_meta["part"] = chapter_chunk.part

    front = make_chunk_frontmatter(front_meta)

    sections: list[str] = [front.rstrip()]

    if chapter_chunk.content:
        sections.append(chapter_chunk.content)

    for chunk in group.chunks[1:]:
        chunk_parts: list[str] = []
        if chunk.heading:
            chunk_parts.append(f"## {chunk.heading}")
        if chunk.content:
            chunk_parts.append(chunk.content)
        if chunk_parts:
            sections.append("\n\n".join(chunk_parts))

    path.write_text("\n\n".join(sections) + "\n")


# ── FB2 path: per-chunk files with hierarchy ─────────────────────────────────


def write_chunks(
    output_dir: Path,
    book_meta: dict,
    chunks: list[Chunk],
    slug: str | None = None,
) -> None:
    """Write chunk trees to output_dir (used by FB2 pipeline).

    Structure without Part:
        slug/00-book.md + chapter-NN-title/NN-chunk.md

    Structure with Part:
        slug/00-book.md + NN-part-slug/chapter-NN-title/NN-chunk.md
    """
    target = output_dir / slug if slug else output_dir
    target.mkdir(parents=True, exist_ok=True)

    (target / "00-book.md").write_text(make_book_frontmatter(book_meta))

    if any(c.part for c in chunks):
        _write_with_parts(target, chunks)
    else:
        _write_flat(target, chunks)


def _write_flat(target: Path, chunks: list[Chunk]) -> None:
    if any(c.chapter_no > 0 for c in chunks):
        _write_by_chapter(target, chunks)
    else:
        _write_each_chunk_dir(target, chunks)


def _write_each_chunk_dir(target: Path, chunks: list[Chunk]) -> None:
    """Each chunk in its own NN-slug/ directory (fallback for unnumbered chunks)."""
    for chunk in chunks:
        slug = _slugify(chunk.heading)
        seq_str = f"{chunk.sequence + 1:02d}"
        chunk_dir = target / f"{seq_str}-{slug}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        _write_chunk(chunk_dir / f"{seq_str}-{slug}.md", chunk)


def _write_by_chapter(target: Path, chunks: list[Chunk]) -> None:
    """Group chunks by chapter_no into chapter directories."""
    chapters: dict[int, list[Chunk]] = {}
    pre_chapter: list[Chunk] = []

    for chunk in chunks:
        if chunk.chapter_no == 0:
            pre_chapter.append(chunk)
        else:
            chapters.setdefault(chunk.chapter_no, []).append(chunk)

    _write_each_chunk_dir(target, pre_chapter)

    for chapter_no, chapter_chunks in chapters.items():
        chapter_title = chapter_chunks[0].chapter_title or f"Chapter {chapter_no}"
        chapter_slug = _slugify(chapter_title)
        chapter_dir = target / f"chapter-{chapter_no:02d}-{chapter_slug}"

        for chunk in chapter_chunks:
            slug = _slugify(chunk.heading)
            seq_str = f"{chunk.sequence + 1:02d}"
            chunk_path = chapter_dir / f"{seq_str}-{slug}.md"
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            _write_chunk(chunk_path, chunk)


def _write_chunk(path: Path, chunk: Chunk) -> None:
    """Write a single chunk file with frontmatter (used by FB2 path)."""
    front = make_chunk_frontmatter({
        "heading": chunk.heading,
        "level": chunk.level,
        "sequence": chunk.sequence,
        "chapter_no": chunk.chapter_no if chunk.chapter_no else None,
        "chapter_title": chunk.chapter_title if chunk.chapter_title else None,
        "section_no": chunk.section_no if chunk.section_no else None,
        "section_title": chunk.section_title if chunk.section_title else None,
        "part": chunk.part if chunk.part else None,
        "sequence_str": chunk.sequence_str if chunk.sequence_str else None,
    })
    path.write_text(front + (chunk.content or ""))


def _write_with_parts(target: Path, chunks: list[Chunk]) -> None:
    """Group chunks by Part, then by chapter inside each part."""
    parts: dict[str, list[Chunk]] = {}

    for chunk in chunks:
        parts.setdefault(chunk.part or "", []).append(chunk)

    for part_idx, (part_name, part_chunks) in enumerate(parts.items()):
        part_slug = _slugify(part_name) if part_name else "misc"
        part_dir = target / f"{part_idx + 1:02d}-{part_slug}"
        part_dir.mkdir(parents=True, exist_ok=True)

        chapters: dict[int, list[Chunk]] = {}
        for chunk in part_chunks:
            chapters.setdefault(chunk.chapter_no, []).append(chunk)

        for chapter_no, chapter_chunks in chapters.items():
            if chapter_no == 0:
                for chunk in chapter_chunks:
                    slug = _slugify(chunk.heading)
                    seq_str = f"{chunk.sequence + 1:02d}"
                    chunk_dir = part_dir / f"{seq_str}-{slug}"
                    chunk_dir.mkdir(parents=True, exist_ok=True)
                    _write_chunk(chunk_dir / f"{seq_str}-{slug}.md", chunk)
            else:
                chapter_title = chapter_chunks[0].chapter_title or f"Chapter {chapter_no}"
                chapter_slug = _slugify(chapter_title)
                chapter_dir = part_dir / f"chapter-{chapter_no:02d}-{chapter_slug}"

                for chunk in chapter_chunks:
                    slug = _slugify(chunk.heading)
                    seq_str = f"{chunk.sequence + 1:02d}"
                    chunk_path = chapter_dir / f"{seq_str}-{slug}.md"
                    chunk_path.parent.mkdir(parents=True, exist_ok=True)
                    _write_chunk(chunk_path, chunk)
