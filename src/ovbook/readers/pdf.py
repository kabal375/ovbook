"""PDF reader — wraps the font-size scoring pipeline."""

from pathlib import Path

from ovbook.extract import extract_pdf_rich, get_metadata
from ovbook.profile import detect_profile
from ovbook.readers.base import BookContent
from ovbook.split import (
    filter_low_score_chunks,
    filter_toc_chunks,
    group_chunks_by_chapter,
)


def read(path: Path) -> BookContent:
    """Convert a PDF into BookContent via profile -> extract -> filter -> group."""
    profile = detect_profile(path)
    body_size = profile["body_size"]

    raw = extract_pdf_rich(path, body_size=body_size)
    raw = filter_toc_chunks(raw)
    raw = filter_low_score_chunks(raw, min_score=-1.0)

    groups = group_chunks_by_chapter(raw, min_chapter_score=7.0)
    meta = get_metadata(path)
    return BookContent(meta=meta, groups=groups)
