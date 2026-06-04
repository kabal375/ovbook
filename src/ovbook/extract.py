"""Extract text from fb2 format and convert to markdown."""

from pathlib import Path
import xml.etree.ElementTree as ET

FB2_NS = "{http://www.gribuser.ru/xml/fictionbook/2.0}"


def extract_fb2(path: Path) -> str:
    """Parse an FB2 file and return its content as structured markdown."""
    tree = ET.parse(str(path))
    root = tree.getroot()

    body = root.find(f".//{FB2_NS}body")
    if body is None:
        raise ValueError("No <body> found in fb2")

    lines = []
    _parse_element(body, lines, 0)
    return "\n".join(lines)


def _parse_element(el: ET.Element, lines: list[str], depth: int) -> None:
    """Recursively parse FB2 elements into markdown lines."""
    tag = el.tag
    local = tag.split("}")[-1] if "}" in tag else tag

    if local == "title":
        text = _get_inner_text(el)
        if text:
            prefix = "#" * min(depth + 1, 6)
            lines.append(f"{prefix} {text}")
            lines.append("")
        return

    if local == "p":
        text = _get_inner_text(el)
        if text:
            lines.append(text)
            lines.append("")
        return

    for child in el:
        _parse_element(child, lines, depth + 1 if local == "section" else depth)


def _get_inner_text(el: ET.Element) -> str:
    """Get all text content from an element, stripping whitespace."""
    parts = []
    if el.text:
        parts.append(el.text.strip())
    for child in el:
        if child.tag == f"{FB2_NS}p" or child.tag == "p":
            child_text = _get_inner_text(child)
            if child_text:
                parts.append(child_text)
        else:
            if child.text:
                parts.append(child.text.strip())
            if child.tail:
                parts.append(child.tail.strip())
    if el.tail:
        parts.append(el.tail.strip())
    return " ".join(p for p in parts if p)
