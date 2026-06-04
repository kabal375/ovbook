"""Tests for the frontmatter generator module."""

from ovbook.frontmatter import make_book_frontmatter, make_chunk_frontmatter


# ── book frontmatter ──────────────────────────────────────────────

def test_book_frontmatter_delimiters():
    """Result is wrapped in --- lines."""
    fm = make_book_frontmatter({"title": "Test"})
    lines = fm.split("\n")
    assert lines[0] == "---"
    assert lines[-2] == "---"
    assert fm.endswith("\n")


def test_book_frontmatter_simple_string():
    fm = make_book_frontmatter({"title": "Moby Dick"})
    assert "title: Moby Dick" in fm


def test_book_frontmatter_multiple_fields():
    fm = make_book_frontmatter({
        "title": "War and Peace",
        "author": "Leo Tolstoy",
        "year": 1869,
    })
    assert "title: War and Peace" in fm
    assert "author: Leo Tolstoy" in fm
    assert "year: 1869" in fm


def test_book_frontmatter_boolean():
    fm = make_book_frontmatter({"draft": True, "fiction": False})
    assert "draft: true" in fm
    assert "fiction: false" in fm


def test_book_frontmatter_list():
    fm = make_book_frontmatter({
        "title": "Dune",
        "tags": ["fiction", "sci-fi", "classic"],
    })
    assert "tags:" in fm
    assert "  - fiction" in fm
    assert "  - sci-fi" in fm
    assert "  - classic" in fm


def test_book_frontmatter_empty_list():
    fm = make_book_frontmatter({"tags": []})
    assert "tags: []" in fm


def test_book_frontmatter_empty_dict():
    fm = make_book_frontmatter({"extra": {}})
    assert "extra: {}" in fm


def test_book_frontmatter_nested_dict():
    fm = make_book_frontmatter({
        "metadata": {
            "source": "gutenberg",
            "language": "en",
        }
    })
    assert "metadata:" in fm
    assert "  source: gutenberg" in fm
    assert "  language: en" in fm


def test_book_frontmatter_none_value():
    fm = make_book_frontmatter({"subtitle": None})
    assert "subtitle: null" in fm


def test_book_frontmatter_string_needs_quoting():
    """Strings with colons, hashes, or leading special chars get quoted."""
    fm = make_book_frontmatter({"url": "https://example.com"})
    assert "url: 'https://example.com'" in fm


def test_book_frontmatter_bool_like_string():
    """A string that looks like a YAML bool must be quoted."""
    fm = make_book_frontmatter({"status": "yes", "flag": "true"})
    assert "status: 'yes'" in fm
    assert "flag: 'true'" in fm


def test_book_frontmatter_empty_string():
    fm = make_book_frontmatter({"subtitle": ""})
    assert "subtitle: ''" in fm


# ── chunk frontmatter ─────────────────────────────────────────────

def test_chunk_frontmatter_delimiters():
    fm = make_chunk_frontmatter({"heading": "Intro"})
    lines = fm.split("\n")
    assert lines[0] == "---"
    assert lines[-2] == "---"


def test_chunk_frontmatter_heading():
    fm = make_chunk_frontmatter({"heading": "Chapter 1", "level": 2})
    assert "heading: Chapter 1" in fm
    assert "level: 2" in fm


def test_chunk_frontmatter_sequence():
    fm = make_chunk_frontmatter({"heading": "Intro", "sequence": 0})
    assert "sequence: 0" in fm


def test_chunk_frontmatter_source():
    fm = make_chunk_frontmatter({
        "heading": "Methods",
        "source": "pg12345.txt",
    })
    assert "source: pg12345.txt" in fm


def test_chunk_frontmatter_tags():
    fm = make_chunk_frontmatter({
        "heading": "Analysis",
        "tags": ["methods", "statistics"],
    })
    assert "  - methods" in fm
    assert "  - statistics" in fm


def test_chunk_frontmatter_integer_zero():
    fm = make_chunk_frontmatter({"sequence": 0})
    assert "sequence: 0" in fm


def test_chunk_frontmatter_float():
    fm = make_chunk_frontmatter({"score": 3.14})
    assert "score: 3.14" in fm


# ── edge cases ────────────────────────────────────────────────────

def test_empty_meta():
    fm = make_book_frontmatter({})
    lines = fm.strip().split("\n")
    assert lines == ["---", "---"]


def test_list_of_dicts():
    fm = make_book_frontmatter({
        "contributors": [
            {"name": "Alice", "role": "author"},
            {"name": "Bob", "role": "editor"},
        ]
    })
    assert "contributors:" in fm
    assert "  - name: Alice" in fm
    assert "    role: author" in fm
    assert "  - name: Bob" in fm
    assert "    role: editor" in fm


def test_string_with_apostrophe():
    """Single quotes inside a quoted string are escaped by doubling."""
    fm = make_book_frontmatter({"title": "Don't Panic"})
    assert "title: 'Don''t Panic'" in fm


def test_mixed_types_in_list():
    fm = make_book_frontmatter({"items": ["a", 1, True]})
    assert "  - a" in fm
    assert "  - 1" in fm
    assert "  - true" in fm


def test_empty_list_of_strings():
    fm = make_chunk_frontmatter({"tags": []})
    assert "tags: []" in fm


def test_roundtrip_book_keys_typical():
    """Verify typical book card keys produce valid YAML structure."""
    fm = make_book_frontmatter({
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "language": "en",
        "source": "gutenberg",
        "tags": ["fiction", "classic", "american"],
        "draft": False,
    })
    assert fm.startswith("---")
    assert "title: The Great Gatsby" in fm
    assert "author: F. Scott Fitzgerald" in fm
    assert "year: 1925" in fm
    assert "language: en" in fm
    assert "draft: false" in fm
    assert "  - fiction" in fm
    assert "  - classic" in fm


def test_roundtrip_chunk_keys_typical():
    """Verify typical chunk metadata keys produce valid YAML structure."""
    fm = make_chunk_frontmatter({
        "heading": "Results",
        "level": 2,
        "sequence": 3,
        "source": "pg12345_chunk_03.md",
        "tags": ["results"],
    })
    assert fm.startswith("---")
    assert "heading: Results" in fm
    assert "level: 2" in fm
    assert "sequence: 3" in fm
    assert "source: pg12345_chunk_03.md" in fm
    assert "  - results" in fm
