"""The PDF reader returns BookContent with chapter groups."""

from ovbook.readers.pdf import read
from ovbook.readers.base import BookContent


def test_pdf_reader_returns_bookcontent(pdf_fixture):
    content = read(pdf_fixture)
    assert isinstance(content, BookContent)
    assert content.meta["title"] == "Test Book"
    assert content.meta["source_format"] == "pdf"
    assert len(content.groups) >= 1
    # first group has at least the chapter chunk
    assert content.groups[0].chunks
