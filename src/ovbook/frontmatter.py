"""Generate YAML frontmatter for book cards (00-book.md) and chunk metadata files.

No pyyaml dependency — manual YAML generation with support for strings,
booleans, integers, lists, and nested dicts.
"""

from typing import Any


def _yaml_value(value: Any, indent: int = 0) -> str:
    """Serialize a Python value to a YAML string.

    Supports: str, bool, int, float, list, dict, None.
    Strings containing special characters are single-quoted.
    """
    pad = "  " * indent

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        return _quote_yaml_str(value)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines: list[str] = []
        for item in value:
            v = _yaml_value(item, indent + 1)
            lines.append(f"{pad}  - {v}")
        return "\n".join(lines)

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for k, v in value.items():
            k_str = _quote_yaml_str(str(k))
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}  {k_str}:")
                child = _yaml_value(v, indent + 1)
                lines.append(child)
            else:
                v_str = _yaml_value(v, indent + 1)
                lines.append(f"{pad}  {k_str}: {v_str}")
        return "\n".join(lines)

    return _quote_yaml_str(str(value))


def _quote_yaml_str(s: str) -> str:
    """Single-quote a YAML string if it contains special characters."""
    if not s:
        return "''"
    needs_quoting = (
        s.startswith(("{", "[", "'", '"', "&", "*", "!", "|", ">", "%"))
        or s in ("true", "false", "null", "yes", "no", "on", "off")
        or any(c in s for c in (":", "#", "{", "}", "[", "]", ",", "&",
                                "*", "?", "|", "-", "<", ">", "=", "!",
                                "%", "@", "`"))
        or s[0].isspace()
        or s[-1].isspace()
    )
    if needs_quoting:
        # Escape single quotes by doubling them
        escaped = s.replace("'", "''")
        return f"'{escaped}'"
    return s


def _make_frontmatter(meta: dict) -> str:
    """Build a YAML frontmatter string from a metadata dict."""
    parts = ["---"]
    for key, value in meta.items():
        k_str = _quote_yaml_str(str(key))
        if isinstance(value, (dict, list)):
            parts.append(f"{k_str}:")
            parts.append(_yaml_value(value, indent=1))
        else:
            v_str = _yaml_value(value, indent=0)
            parts.append(f"{k_str}: {v_str}")
    parts.append("---")
    return "\n".join(parts) + "\n"


def make_book_frontmatter(meta: dict) -> str:
    """Generate YAML frontmatter for a book card (00-book.md).

    Args:
        meta: Dictionary of book metadata. Common keys:
            title, author, source, year, tags, language, genre, etc.

    Returns:
        A string with YAML frontmatter enclosed by ``---`` lines.
    """
    return _make_frontmatter(meta)


def make_chunk_frontmatter(meta: dict) -> str:
    """Generate YAML frontmatter for a chunk metadata file.

    Args:
        meta: Dictionary of chunk metadata. Common keys:
            heading, level, sequence, source, tags, etc.

    Returns:
        A string with YAML frontmatter enclosed by ``---`` lines.
    """
    return _make_frontmatter(meta)
