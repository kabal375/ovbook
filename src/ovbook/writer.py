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

    # Bare "CHAPTER N" — the first non-blank content line is the candidate
    # title. If that line is too long to be a title, treat it as body and
    # fall back to the heading rather than scanning deeper.
    if chunk.content:
        for line in chunk.content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            return stripped if len(stripped) <= 80 else heading

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
            # level 2 -> ##, level 3 -> ###, clamp into [2, 6]
            depth = min(max(chunk.level, 2), 6)
            chunk_parts.append(f"{'#' * depth} {chunk.heading}")
        if chunk.content:
            chunk_parts.append(chunk.content)
        if chunk_parts:
            sections.append("\n\n".join(chunk_parts))

    path.write_text("\n\n".join(sections) + "\n")
