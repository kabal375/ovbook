"""Article reader — plain-text section detector for journal papers & reports.

Uses regex-based heading detection on raw PDF text. Designed as a fallback
when the font-size scoring pipeline finds no chapters (all text same font).

Two detection strategies, tried in order:
  1. Known academic headings   — all-caps INTRODUCTION, CONCLUSION, etc.
  2. Numbered sections          — "1. ", "1.1 ", "2. " with proper spacing
"""

import re
from pathlib import Path

import pymupdf

from ovbook.readers.base import BookContent
from ovbook.split import ChapterGroup, Chunk

# ── strategy 1: known all-caps academic headings ──────────────────────

_ACADEMIC_HEADINGS = {
    "ABSTRACT", "INTRODUCTION", "BACKGROUND",
    "RELATED WORK", "LITERATURE REVIEW", "STATE OF THE ART",
    "METHODOLOGY", "METHOD", "APPROACH",
    "IMPLEMENTATION",
    "EXPERIMENTS", "EXPERIMENT", "EVALUATION", "RESULTS", "DISCUSSION",
    "CONCLUSION", "FUTURE WORK", "SUMMARY",
    "REFERENCES", "BIBLIOGRAPHY",
    "ACKNOWLEDGMENTS", "ACKNOWLEDGMENT",
    "APPENDIX", "APPENDIX A", "APPENDIX B", "APPENDIX C",
    "TABLE OF CONTENTS", "INDEX",
    "PROPOSED APPROACH", "PROPOSED WORK", "PROPOSED SYSTEM",
    "SYSTEM DESIGN", "SYSTEM ARCHITECTURE",
}

# Also match uppercase with trailing colon or whitespace
_ACADEMIC_RE = re.compile(
    r"^(" + "|".join(re.escape(h) for h in sorted(_ACADEMIC_HEADINGS, key=len, reverse=True)) + r"):?\s*$",
)


def _is_academic_heading(line: str) -> bool:
    """Check if a line is a standalone academic section heading."""
    stripped = line.strip()
    if len(stripped) > 40:
        return False
    # Match exact all-caps headings
    if stripped.isupper() and _ACADEMIC_RE.match(stripped):
        return True
    # Match CHAPTER + number (with or without space: CHAPTER1, CHAPTER 1)
    if re.match(r"^CHAPTER\s*\d+$", stripped, re.IGNORECASE):
        return True
    # Match APPENDIX + letter (with or without space: APPENDIXA, APPENDIX A)
    if re.match(r"^APPENDIX\s*[A-Z]$", stripped, re.IGNORECASE):
        return True
    return False


# ── strategy 2: numbered sections ─────────────────────────────────────

_NUMBERED_RE = re.compile(
    r"^(\d+)[.)\s]{1,2}\s*([A-Z][A-Za-z\s/-]{3,45})$"
)
# Only match FIRST-LEVEL numbered sections (no dots: "1 ", not "1.1 ")


_BODY_TEXT_STARTS = {
    "for", "the", "there", "this", "that", "these", "those", "with",
    "from", "which", "where", "when", "while", "using", "based",
    "according", "however", "therefore", "furthermore", "moreover",
    "although", "because", "since", "after", "before", "between",
    "through", "during", "within", "without", "across", "among",
    "about", "above", "below", "under", "over", "into", "onto",
    "also", "than", "then", "else", "even", "such", "each", "both",
    "shows", "showing", "following", "including", "provides",
}


def _is_numbered_heading(line: str) -> bool:
    """Check if a line is a numbered section heading."""
    stripped = line.strip()
    if len(stripped) > 100:
        return False
    m = _NUMBERED_RE.match(stripped)
    if not m:
        return False
    # Check the text after the number doesn't start with body-text words
    heading_text = m.group(2).strip().lower()
    first_word = heading_text.split()[0] if heading_text.split() else ""
    if first_word in _BODY_TEXT_STARTS:
        return False
    return True


# ── main pipeline ─────────────────────────────────────────────────────


def _strip_junk(lines: list[str]) -> list[str]:
    """Remove repeated journal headers, page numbers, and empty lines."""
    skip = re.compile(
        r"("
        r"European\s+Journal\s+of"
        r"|Print\s+ISSN"
        r"|Online\s+ISSN"
        r"|Website:\s*https?://"
        r"|Publication\s+of\s+the"
        r"|^\d+$"  # standalone page numbers
        r"|^-\s*\d+\s*-$"  # page numbers like "- 3 -"
        r")",
        re.IGNORECASE,
    )
    result = []
    for l in lines:
        stripped = l.strip()
        if not stripped:
            continue
        if skip.search(stripped):
            continue
        result.append(stripped)
    return result


def _find_headings(lines: list[str]) -> list[tuple[int, str]]:
    """Return list of (line_index, heading_text) for all detected headings."""
    headings: list[tuple[int, str]] = []

    # Strategy 1: academic all-caps headings
    for i, l in enumerate(lines):
        if _is_academic_heading(l):
            headings.append((i, l.strip().rstrip(":")))

    # Strategy 2: numbered sections (only if book is short — skip for full books)
    # For books > 50 pages, numbered patterns are likely running headers or TOC
    if len(lines) < 500:  # ~50 pages of average text
        for i, l in enumerate(lines):
            if _is_numbered_heading(l):
                m = _NUMBERED_RE.match(l.strip())
                if m:
                    headings.append((i, m.group(0).strip()))

    # Deduplicate by index
    seen: set[int] = set()
    unique: list[tuple[int, str]] = []
    for idx, h in sorted(headings, key=lambda x: x[0]):
        if idx not in seen:
            seen.add(idx)
            unique.append((idx, h))
    # Deduplicate: merge consecutive identical headings (PDF running headers)
    deduped: list[tuple[int, str]] = []
    for idx, h in unique:
        if deduped and h.lower() == deduped[-1][1].lower():
            continue  # skip running header — same heading
        deduped.append((idx, h))
    return deduped


def read(path: Path) -> BookContent:
    """Convert a PDF journal article into BookContent via plain-text section detection."""
    doc = pymupdf.open(path)
    text_parts: list[str] = []
    for i in range(len(doc)):
        page_text = doc[i].get_text()
        if isinstance(page_text, str):
            text_parts.append(page_text)
    doc.close()
    full_text = "\n".join(text_parts)

    lines = full_text.split("\n")
    lines = _strip_junk(lines)
    if not lines:
        return BookContent(meta={}, groups=[])

    headings = _find_headings(lines)

    if not headings:
        # No headings detected — return as single chapter
        groups = [
            ChapterGroup(
                chapter_no=1,
                chapter_title=path.stem,
                chunks=[
                    Chunk(
                        heading=path.stem,
                        content="\n".join(lines),
                        level=2,
                        sequence=1,
                    )
                ],
            )
        ]
        meta = _extract_meta(path, lines)
        return BookContent(meta=meta, groups=groups)

    # Split text at heading boundaries, collecting all body lines under each heading
    groups: list[ChapterGroup] = []

    # If there's content before the first heading, prepend a synthetic chapter
    if headings and headings[0][0] > 0:
        front_content = "\n".join(lines[: headings[0][0]]).strip()
        if front_content:
            groups.append(
                ChapterGroup(
                    chapter_no=1,
                    chapter_title="Front Matter",
                    chunks=[
                        Chunk(
                            heading="Front Matter",
                            content=front_content,
                            level=2,
                            sequence=1,
                        )
                    ],
                )
            )

    for idx, (heading_start, heading_text) in enumerate(headings):
        chapter_no = idx + 1 + (1 if groups else 0)  # account for front matter chapter
        content_start = heading_start + 1
        if idx + 1 < len(headings):
            content_end = headings[idx + 1][0] - 1
        else:
            content_end = len(lines) - 1

        content = "\n".join(lines[content_start : content_end + 1]).strip()
        groups.append(
            ChapterGroup(
                chapter_no=chapter_no,
                chapter_title=heading_text,
                chunks=[
                    Chunk(
                        heading=heading_text,
                        content=content,
                        level=2,
                        sequence=chapter_no,
                    )
                ],
            )
        )

    meta = _extract_meta(path, lines)
    return BookContent(meta=meta, groups=groups)


def _extract_meta(path: Path, lines: list[str]) -> dict:
    """Extract basic metadata from the article.

    Uses pymupdf metadata + heuristic title from first content lines."""
    doc = pymupdf.open(path)
    raw = doc.metadata or {}
    doc.close()

    # Try to get a meaningful title from the first few text lines
    pdf_title = raw.get("title", "").strip()
    if pdf_title and pdf_title != path.stem:
        title = pdf_title
    else:
        # Heuristic: read title from first few lines, stop at author/meta markers
        title = path.stem
        title_lines: list[str] = []
        stop_markers = {"doi:", "citation:", "keywords:", "abstract:",
                        "university", "college", "institute", "school of",
                        "department of", "faculty of", "©"}
        for l in lines[:20]:
            stripped = l.strip()
            if not stripped:
                continue
            low = stripped.lower()
            # Stop at meta markers
            if any(low.startswith(m) or m in low for m in stop_markers):
                break
            # Stop when line too short (likely author name, not title)
            if title_lines and len(stripped) < 10:
                break
            # Skip lines that look like personal names (3+ capitalized words, no lowercase)
            if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}$", stripped):
                break
            title_lines.append(stripped)
        if title_lines:
            title = " ".join(title_lines).strip()
    authors = [a.strip() for a in raw.get("author", "").split(",") if a.strip()]

    year = raw.get("creationDate", "") or raw.get("modDate", "")
    year_match = re.search(r"(20\d{2})", year)
    year_val = int(year_match.group(1)) if year_match else 0

    return {
        "title": title,
        "authors": authors,
        "source_format": "pdf",
        "language": "en",
        "year": year_val,
    }
