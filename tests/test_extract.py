from pathlib import Path
from ovbook.extract import extract_fb2


def test_extract_fb2_returns_markdown():
    fixture = Path(__file__).parent / "fixtures" / "sample.fb2"
    result = extract_fb2(fixture)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Chapter 1" in result


def test_extract_fb2_title_as_h1():
    fixture = Path(__file__).parent / "fixtures" / "sample.fb2"
    result = extract_fb2(fixture)
    lines = result.strip().split("\n")
    assert lines[0].startswith("# ")


def test_extract_fb2_sections_as_h2():
    fixture = Path(__file__).parent / "fixtures" / "sample.fb2"
    result = extract_fb2(fixture)
    assert "# Chapter 1" in result  # body title → H1
    assert "## Section 1.1" in result  # sections inside body → H2
    assert "## Section 1.2" in result


def test_extract_fb2_preserves_text():
    fixture = Path(__file__).parent / "fixtures" / "sample.fb2"
    result = extract_fb2(fixture)
    assert "Content of section 1.1" in result
    assert "Content of section 1.2" in result
