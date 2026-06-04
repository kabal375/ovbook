"""Write chunk trees to disk."""

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
) -> None:
    """Write chunk trees to *output_dir*.

    Creates:
        output_dir/
            00-book.md          -- book card with frontmatter
            01-chapter-slug/
                01-chapter-slug.md  -- chunk file
            02-another-slug/
                02-another-slug.md
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 00-book.md ---
    book_card = make_book_frontmatter(book_meta)
    (output_dir / "00-book.md").write_text(book_card)

    # --- Chapter directories and chunk files ---
    for chunk in chunks:
        slug = _slugify(chunk.heading)
        seq_str = f"{chunk.sequence + 1:02d}"
        dir_name = f"{seq_str}-{slug}"
        file_name = f"{seq_str}-{slug}.md"

        chunk_dir = output_dir / dir_name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        chunk_meta = {
            "heading": chunk.heading,
            "level": chunk.level,
            "sequence": chunk.sequence,
        }
        front = make_chunk_frontmatter(chunk_meta)
        body = chunk.content if chunk.content else ""
        content = front + body

        (chunk_dir / file_name).write_text(content)
