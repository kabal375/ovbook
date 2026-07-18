"""PDF reader — wraps the font-size scoring pipeline with article fallback.

Pipeline:
  1. Rich pipeline (font-size scored headings) — best for born-digital PDFs
     with "Chapter X" keywords and font-size hierarchy.
  2. Article pipeline (plain-text regex section detection) — fallback for
     SHORT documents (<50 pages): journal papers, reports, articles.
  3. Low-score pipeline (lowered threshold) — last resort for structured
     PDFs without "Chapter X" but with font-size variance (score >= 3).
"""

from pathlib import Path

from ovbook.extract import extract_pdf_rich, get_metadata
from ovbook.profile import detect_profile
from ovbook.readers.article import read as read_article
from ovbook.readers.base import BookContent
from ovbook.split import (
    filter_low_score_chunks,
    filter_toc_chunks,
    group_chunks_by_chapter,
)

# Article pipeline is only tried as auto-fallback for short documents
_MAX_ARTICLE_PAGES = 30


def read(path: Path, **kwargs: str) -> BookContent:
    """Convert a PDF into BookContent via profile → extract → filter → group.

    Falls back to article pipeline when the rich scoring pipeline produces
    no chapters (common for journal articles, reports, and technical papers
    where all text uses the same font size).

    Kwargs:
        mode: 'rich' — force rich pipeline only
              'article' — force article pipeline only
              'lowscore' — force lowered threshold (3)
              None (default) — auto: rich → article(short) → lowscore
    """
    mode = kwargs.get("mode")
    profile = detect_profile(path)
    body_size = profile["body_size"]
    page_count = profile.get("page_count", 0)
    meta = get_metadata(path)

    # ── Mode override: article only ───────────────────────────────────
    if mode == "article":
        article = read_article(path)
        if article.groups:
            article.meta.update(
                {k: v for k, v in meta.items() if v and k not in ("title",)}
            )
        return article

    # ── Rich pipeline (font-size scoring) ─────────────────────────────
    raw = extract_pdf_rich(path, body_size=body_size)
    raw = filter_toc_chunks(raw)
    raw = filter_low_score_chunks(raw, min_score=-1.0)

    if mode == "rich":
        groups = group_chunks_by_chapter(raw, min_chapter_score=7.0)
        return BookContent(meta=meta, groups=groups)

    # Auto: rich succeeded?
    groups = group_chunks_by_chapter(raw, min_chapter_score=7.0)
    if groups:
        return BookContent(meta=meta, groups=groups)

    # ── Article pipeline (only for short documents) ───────────────────
    if page_count < _MAX_ARTICLE_PAGES:
        article = read_article(path)
        if article.groups:
            article.meta.update(
                {k: v for k, v in meta.items() if v and k not in ("title",)}
            )
            return article

    # ── Low-score pipeline (lowered threshold) ────────────────────────
    if mode == "lowscore":
        groups = group_chunks_by_chapter(raw, min_chapter_score=3.0)
        return BookContent(meta=meta, groups=groups)

    # Auto: try lowscore as last resort
    groups = group_chunks_by_chapter(raw, min_chapter_score=3.0)
    return BookContent(meta=meta, groups=groups)
