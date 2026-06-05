"""Tests for the reader registry."""

import pytest

from ovbook.readers import get_reader
from ovbook.readers import pdf, fb2, epub


def test_registry_maps_known_formats():
    assert get_reader("pdf") is pdf.read
    assert get_reader("fb2") is fb2.read
    assert get_reader("epub") is epub.read


def test_registry_unknown_format_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        get_reader("mobi")
