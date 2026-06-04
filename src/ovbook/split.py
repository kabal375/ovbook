"""Split markdown text into chunks by heading boundaries."""

from dataclasses import dataclass, field
import re


@dataclass
class Chunk:
    heading: str
    content: str
    level: int = 2
    sequence: int = 0

    def __post_init__(self):
        self.content = self.content.strip()


def split_into_chunks(markdown: str) -> list[Chunk]:
    """Split markdown into chunks by H2+ headings.

    H1 (book title) is consumed but not returned as a chunk.
    Each H2+ heading starts a new chunk.
    """
    lines = markdown.split("\n")
    chunks: list[Chunk] = []
    current_heading: str | None = None
    current_level: int = 2
    current_content: list[str] = []
    seq = 0
    found_any_heading = False

    for line in lines:
        m = re.match(r"^(#{2,6})\s+(.+)$", line)
        if m:
            found_any_heading = True
            level = len(m.group(1))
            heading = m.group(2)

            # Save previous chunk
            if current_heading is not None:
                chunks.append(Chunk(
                    heading=current_heading,
                    content="\n".join(current_content).strip(),
                    level=current_level,
                    sequence=seq,
                ))
                seq += 1

            current_heading = heading
            current_level = level
            current_content = []
        else:
            if found_any_heading:
                current_content.append(line)
            # Before first heading — skip (book title / preamble)

    # Last chunk
    if current_heading is not None:
        joined = "\n".join(current_content).strip()
        if joined:
            chunks.append(Chunk(
                heading=current_heading,
                content=joined,
                level=current_level,
                sequence=seq,
            ))

    return chunks
