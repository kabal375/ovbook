"""Tests for the BookContent intermediate type."""

from ovbook.readers.base import BookContent
from ovbook.split import ChapterGroup, Chunk


def test_bookcontent_holds_meta_and_groups():
    group = ChapterGroup(chapter_no=1, chapter_title="Ch1",
                         chunks=[Chunk(heading="Ch1", content="body", level=1)])
    content = BookContent(meta={"title": "T"}, groups=[group])
    assert content.meta["title"] == "T"
    assert len(content.groups) == 1
    assert content.groups[0].chapter_title == "Ch1"


def test_bookcontent_groups_default_empty():
    content = BookContent(meta={"title": "T"})
    assert content.groups == []
