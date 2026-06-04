"""Common intermediate representation shared by all format readers."""

from dataclasses import dataclass, field

from ovbook.split import ChapterGroup


@dataclass
class BookContent:
    """Normalized output of any reader.

    meta:   book frontmatter dict (id, title, authors, language, year, ...)
    groups: chapters ready for write_chapter_groups
    """

    meta: dict
    groups: list[ChapterGroup] = field(default_factory=list)
