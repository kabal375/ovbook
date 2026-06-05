"""Subsection chunks render with a heading prefix matching their level."""

from ovbook.split import Chunk, ChapterGroup
from ovbook.writer import write_chapter_groups


def test_subsection_levels_render_correct_prefix(tmp_path):
    group = ChapterGroup(
        chapter_no=1,
        chapter_title="Getting Started",
        chunks=[
            Chunk(heading="Getting Started", content="Intro.", level=1,
                  chapter_no=1, chapter_title="Getting Started"),
            Chunk(heading="Installation", content="Install body.", level=2),
            Chunk(heading="Prerequisites", content="Deep detail.", level=3),
        ],
    )
    write_chapter_groups(tmp_path, [group], {"id": "b", "title": "B"}, "b")

    chapter_file = next(
        f for f in (tmp_path / "b").iterdir()
        if f.name != "00-book.md"
    )
    text = chapter_file.read_text()
    assert "## Installation" in text
    assert "### Prerequisites" in text
    assert "#### " not in text  # level capped, no over-deep headings
