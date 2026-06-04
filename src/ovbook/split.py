"""Split markdown text into chunks by heading boundaries with hierarchy."""

from dataclasses import dataclass
import re


_PART_RE = re.compile(r"^(?:Part|Часть|Том|Book|Книга)\s+\w+", re.IGNORECASE)
# H2‑level: leading digit (1. / 2 / 4) or keyword + digit (Chapter 5 / Глава 3)
_H2_NUM_RE = re.compile(r"^(?:(\d+)[.)\s]|(?:Chapter|Глава|Section|Chapitre|Kapitel|Lecture|Параграф)\s+(\d+))\s*", re.IGNORECASE)
# H3‑level: X.Y (4.1) or keyword + X.Y (Section 4.1 / Параграф 4.1)
_H3_NUM_RE = re.compile(
    r"^(?:"
    r"(\d+)\.(\d+)"                           # 4.1
    r"|"
    r"(?:Section|Параграф|Paragraf|Paragraph)\s+(\d+)\.(\d+)"  # Section 4.1
    r"|"
    r"(?:Section|Параграф|Paragraf|Paragraph)\s+(\d+)"          # Section 4
    r")",
    re.IGNORECASE,
)


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
    # Scoring metadata
    font_size: float = 0.0
    is_bold: bool = False
    near_drawing: bool = False
    looks_like_toc_entry: bool = False
    looks_like_index_letter: bool = False
    page_type: str = "body"  # body / toc / index / front-matter / appendix / diagram
    score: float = 0.0

    def __post_init__(self):
        self.content = self.content.strip()


def score_heading(c: "Chunk", body_font_size: float) -> float:
    """Score a Chunk candidate for being a real heading.

    Positive signals: chapter keyword, numbered heading, larger font, bold.
    Negative signals: too short, TOC dots, near drawing, index letter.
    """
    s = 0.0
    text = c.heading.strip()

    if not text:
        return s

    # --- Negative signals ---
    if len(text) < 4:
        s -= 5
    if re.search(r"\.{3,}\s*\d*\s*$", text):
        s -= 8
    if re.match(r"\.{3,}", text):
        s -= 8
    if re.match(r"^[A-ZА-Я]$", text) or re.match(r"^[A-Z],\s*[A-Z]$", text):
        if c.level >= 2:
            s -= 8
    if re.match(r"^[\W_]+$", text):
        s -= 10

    # --- Positive signals ---
    if re.match(r"^(chapter|part|appendix|lecture|lesson|module)\b", text, re.IGNORECASE):
        s += 6
    if re.match(r"^\d+(\.\d+)*\s+\S+", text):
        s += 5
    if c.font_size >= body_font_size * 2.0:
        s += 5
    elif c.font_size >= body_font_size * 1.6:
        s += 3
    elif c.font_size >= body_font_size * 1.18:
        s += 1
    if c.is_bold:
        s += 1

    # --- Pre-computed flags ---
    if c.near_drawing:
        s -= 6
    if c.looks_like_toc_entry:
        s -= 10
    if c.looks_like_index_letter:
        s -= 8

    return s


def _enrich_chunks(chunks: list["Chunk"]) -> None:
    """Assign hierarchy metadata (chapter_no, section_no, part, sequence_str).

    H1/H2 headings: extract number from leading digit or keyword.
    H3 headings: extract X.Y number or sequential position.
    Unnumbered headings get sequential numbering.
    """
    current_part = ""
    current_chapter_no = 0
    current_chapter_title = ""
    chapter_counter = 0
    section_counter = 0

    for chunk in chunks:
        if chunk.part:
            current_part = chunk.part
        chunk.part = current_part

        # Detect Chapter: H1 (large-font "CHAPTER 1" from PDFs) or H2
        if chunk.level <= 2:
            m = _H2_NUM_RE.match(chunk.heading)
            if m:
                num = m.group(1) or m.group(2)
                current_chapter_no = int(num)
                chapter_counter = current_chapter_no
            else:
                chapter_counter += 1
                current_chapter_no = chapter_counter
            current_chapter_title = chunk.heading
            section_counter = 0

        chunk.chapter_no = current_chapter_no
        chunk.chapter_title = current_chapter_title

        # Detect Section (H3)
        if chunk.level == 3:
            m = _H3_NUM_RE.match(chunk.heading)
            if m:
                if m.group(5):
                    chunk.section_no = int(m.group(5))
                else:
                    ch = m.group(1) or m.group(3)
                    sec = m.group(2) or m.group(4)
                    chunk.section_no = int(sec)
                    section_ch = int(ch)
                    if section_ch != current_chapter_no:
                        current_chapter_no = section_ch
                        chunk.chapter_no = current_chapter_no
            else:
                sn = re.match(r"^(\d+)[.)]\s+", chunk.heading)
                if sn:
                    chunk.section_no = int(sn.group(1))
                else:
                    section_counter += 1
                    chunk.section_no = section_counter
            chunk.section_title = chunk.heading
        else:
            chunk.section_no = 0

        chunk.sequence_str = f"{chunk.chapter_no:02d}{chunk.section_no:02d}"


def split_into_chunks(markdown: str) -> list["Chunk"]:
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
    current_part = ""  # replaces _part_state = [""] mutable-container trick

    def flush():
        nonlocal seq, current_heading
        if current_heading is not None:
            joined = "\n".join(current_content).strip()
            if joined:
                chunks.append(Chunk(
                    heading=current_heading,
                    content=joined,
                    level=current_level,
                    sequence=seq,
                    part=current_part,
                ))
                seq += 1
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
                    flush()
                    current_part = heading
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


def _is_content_start(heading: str) -> bool:
    """Check if heading signals start of real content."""
    if _CONTENT_START_RE.match(heading):
        return True
    if re.match(r"^\d+[.)\s]", heading):
        return True
    return False


def filter_content(chunks: list["Chunk"]) -> list["Chunk"]:
    """Remove front matter (before first Chapter/Part/Appendix) and index."""
    if not chunks:
        return []

    start = 0
    for i, c in enumerate(chunks):
        if _is_content_start(c.heading):
            start = i
            break
    else:
        return chunks

    end = len(chunks)
    for i, c in enumerate(chunks[start:], start=start):
        if _CONTENT_END_RE.match(c.heading):
            end = i
            break

    return chunks[start:end]


@dataclass
class ChapterGroup:
    """A chapter with its subsections, ready for depth-guarded writing."""

    chapter_no: int
    chapter_title: str
    chunks: list["Chunk"]


def group_chunks_by_chapter(
    chunks: list["Chunk"],
    min_chapter_score: float = 5.0,
) -> list[ChapterGroup]:
    """Group chunks into chapters.

    H1/H2 chunks with score >= min_chapter_score start a new chapter.
    H3 chunks and low-score chunks are grouped under the nearest preceding chapter.
    Chunks before the first chapter are dropped.
    """
    groups: list[ChapterGroup] = []
    current: ChapterGroup | None = None
    chapter_counter = 0

    for chunk in chunks:
        if chunk.level <= 2 and chunk.score >= min_chapter_score:
            if chunk.chapter_no == 0:
                chapter_counter += 1
                chunk.chapter_no = chapter_counter
            else:
                chapter_counter = chunk.chapter_no

            current = ChapterGroup(
                chapter_no=chunk.chapter_no,
                chapter_title=chunk.heading,
                chunks=[chunk],
            )
            groups.append(current)
        elif current is not None:
            current.chunks.append(chunk)

    return groups


def filter_toc_chunks(chunks: list["Chunk"]) -> list["Chunk"]:
    """Remove chunks that look like TOC entries."""
    return [c for c in chunks if not c.looks_like_toc_entry]


def filter_low_score_chunks(chunks: list["Chunk"], min_score: float = 0.0) -> list["Chunk"]:
    """Remove chunks with score at or below threshold (noise/artifacts)."""
    return [c for c in chunks if c.score > min_score]
