"""Split markdown text into chunks by heading boundaries with hierarchy."""

from dataclasses import dataclass
import re


_PART_RE = re.compile(r"^Part\s+\w+", re.IGNORECASE)
_CHAPTER_RE = re.compile(r"(?:CHAPTER|Chapter)\s*(\d+)")
_SECTION_RE = re.compile(r"(?:Section|SECTION)\s*(\d+)")
_SECTION_NUM_RE = re.compile(r"^(\d+)[.)]\s+")


@dataclass
class Chunk:
    heading: str
    content: str
    level: int = 2
    sequence: int = 0
    # Hierarchy metadata
    chapter_no: int = 0
    chapter_title: str = ""
    section_no: int = 0
    section_title: str = ""
    part: str = ""
    sequence_str: str = ""

    def __post_init__(self):
        self.content = self.content.strip()


def _enrich_chunks(chunks: list[Chunk]) -> None:
    """Assign hierarchy metadata (chapter_no, section_no, part, sequence_str)."""
    current_part = ""
    current_chapter_no = 0
    current_chapter_title = ""
    section_counter = 0

    for chunk in chunks:
        # Track part transitions (set by splitter)
        if chunk.part:
            current_part = chunk.part
        chunk.part = current_part

        # Detect Chapter
        m = _CHAPTER_RE.search(chunk.heading)
        if m:
            current_chapter_no = int(m.group(1))
            current_chapter_title = chunk.heading
            section_counter = 0

        chunk.chapter_no = current_chapter_no
        chunk.chapter_title = current_chapter_title

        # Detect Section (H3)
        if chunk.level == 3:
            sm = _SECTION_RE.search(chunk.heading)
            if sm:
                chunk.section_no = int(sm.group(1))
            else:
                # Try leading number pattern: "### 2. Section title" or "### 3) Title"
                nm = _SECTION_NUM_RE.match(chunk.heading)
                if nm:
                    chunk.section_no = int(nm.group(1))
                else:
                    section_counter += 1
                    chunk.section_no = section_counter
            chunk.section_title = chunk.heading
        else:
            chunk.section_no = 0

        chunk.sequence_str = f"{chunk.chapter_no:02d}{chunk.section_no:02d}"


def split_into_chunks(markdown: str) -> list[Chunk]:
    """Split markdown into chunks by heading boundaries.

    H1 headings matching "Part X" are Part boundaries (not chunks).
    H2+ headings become chunks: H2 = chapter, H3 = section.
    """
    lines = markdown.split("\n")
    chunks: list[Chunk] = []
    current_heading: str | None = None
    current_level: int = 2
    current_content: list[str] = []
    seq = 0
    found_any_heading = False
    _part_state = [""]  # mutable container for closure access

    def flush():
        nonlocal seq, current_heading
        part = _part_state[0]
        if current_heading is not None:
            joined = "\n".join(current_content).strip()
            if joined:
                chunks.append(Chunk(
                    heading=current_heading,
                    content=joined,
                    level=current_level,
                    sequence=seq,
                    part=part,
                ))
                seq += 1
        # Reset state after flush to prevent double-emit
        current_heading = None
        current_content.clear()

    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            heading = m.group(2)

            # H1: Part or book title
            if level == 1:
                if _PART_RE.match(heading):
                    # Part boundary — flush current chunk first
                    flush()
                    _part_state[0] = heading
                # Book title or other H1 — skip
                continue

            # H2+ — start a new chunk
            flush()
            current_heading = heading
            current_level = level
            current_content = []
            found_any_heading = True
        else:
            if found_any_heading:
                current_content.append(line)

    flush()

    _enrich_chunks(chunks)
    return chunks


_CONTENT_START_RE = re.compile(
    r"^(?:CHAPTER|Part|Appendix)\s",
    re.IGNORECASE,
)
_CONTENT_END_RE = re.compile(r"^Index$|^Where to Go Next$", re.IGNORECASE)


def filter_content(chunks: list[Chunk]) -> list[Chunk]:
    """Remove front matter (before first Chapter/Part/Appendix) and index (from 'Index' onward)."""
    if not chunks:
        return []

    # Find content start
    start = 0
    for i, c in enumerate(chunks):
        if _CONTENT_START_RE.match(c.heading):
            start = i
            break
    else:
        # No content boundary found — return all
        return chunks

    # Find content end (Index)
    end = len(chunks)
    for i, c in enumerate(chunks[start:], start=start):
        if _CONTENT_END_RE.match(c.heading):
            end = i
            break

    return chunks[start:end]
