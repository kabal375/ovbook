"""Extract text from books (PDF primary, fb2 fallback) and convert to markdown."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import fitz  # PyMuPDF

FB2_NS = "{http://www.gribuser.ru/xml/fictionbook/2.0}"

# --- PDF extraction (primary) ---


def extract_pdf(path: Path) -> str:
    """Extract structured markdown from a PDF using font-size heuristics."""
    doc = fitz.open(str(path))
    lines: list[str] = []
    body_sizes: list[float] = []

    # First pass: sample font sizes to determine body text baseline
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text
                for line in block["lines"]:
                    for span in line["spans"]:
                        body_sizes.append(span["size"])
        if len(body_sizes) > 50:
            break

    if not body_sizes:
        return ""

    # Determine body text size (most common size)
    from collections import Counter
    size_counter = Counter(round(s, 1) for s in body_sizes)
    body_size = size_counter.most_common(1)[0][0]

    # Second pass: extract text with heading detection
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    text_parts = []
                    max_size = 0
                    for span in line["spans"]:
                        text_parts.append(span["text"])
                        max_size = max(max_size, span["size"])

                    text = "".join(text_parts).strip()
                    if not text:
                        continue

                    # Heading detection: font significantly larger than body
                    if max_size >= body_size * 1.3:
                        # Determine heading level by size ratio
                        ratio = max_size / body_size
                        if ratio >= 2.0:
                            level = 1
                        elif ratio >= 1.6:
                            level = 2
                        else:
                            level = 3
                        prefix = "#" * level
                        lines.append(f"{prefix} {text}")
                        lines.append("")
                    else:
                        lines.append(text)
                        lines.append("")

    doc.close()
    return "\n".join(lines)


def _compute_body_size(doc: fitz.Document) -> float:
    """Compute body font size as median of all span sizes."""
    sizes: list[float] = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text
                for line in block["lines"]:
                    for span in line["spans"]:
                        sizes.append(span["size"])
        if len(sizes) > 200:
            break
    if not sizes:
        return 12.0
    sizes.sort()
    return sizes[len(sizes) // 2]


def _is_near_drawing(bbox, drawings, threshold: float = 20.0) -> bool:
    """Check if bbox is near any drawing cluster."""
    if not bbox or not drawings:
        return False
    for drawing in drawings:
        if isinstance(drawing, (list, tuple)):
            d_rect = fitz.Rect(drawing)
        else:
            d_rect = drawing
        if hasattr(bbox, "distance_to"):
            try:
                if bbox.distance_to(d_rect) < threshold:
                    return True
            except Exception:
                pass
    return False


def extract_pdf_rich(path: Path) -> list:
    """Extract structured chunks from a PDF with rich metadata for scoring.

    Returns list[Chunk] with font_size, is_bold, near_drawing, etc.
    Body-level text blocks are accumulated and attached to the nearest
    preceding heading chunk as content.
    """
    from .split import Chunk, score_heading

    doc = fitz.open(str(path))
    body_size = _compute_body_size(doc)

    chunks: list[Chunk] = []
    seq = 0
    body_accumulator: list[str] = []

    def flush_body():
        """Attach accumulated body text to the most recent chunk, if any."""
        nonlocal body_accumulator
        if not body_accumulator:
            return
        body_text = "\n\n".join(b for b in body_accumulator if b.strip())
        body_accumulator = []
        if body_text and chunks:
            prev = chunks[-1]
            if prev.content:
                prev.content += "\n\n" + body_text
            else:
                prev.content = body_text

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        drawings = []
        if hasattr(page, "cluster_drawings"):
            try:
                drawings = page.cluster_drawings()
            except Exception:
                pass

        for block in blocks:
            if block["type"] != 0:  # skip images
                continue

            # Aggregate all spans in this block into a single text
            block_text = ""
            block_max_size = 0.0
            block_is_bold = False
            block_bbox = None

            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]
                    block_max_size = max(block_max_size, span["size"])
                    font = span.get("font", "")
                    if "Bold" in font or "bold" in font or "Black" in font:
                        block_is_bold = True
                    if span.get("flags", 0) & 2:
                        block_is_bold = True
                block_text += "\n"

                if "bbox" in line and block_bbox is None:
                    block_bbox = fitz.Rect(line["bbox"])

            text = block_text.strip()
            if not text:
                continue

            # Determine if near drawing
            near_drawing = False
            if block_bbox and drawings:
                near_drawing = _is_near_drawing(block_bbox, drawings)

            # Detect TOC entry: leader dots with optional page tail
            first_line = text.split("\n")[0]
            looks_like_toc = bool(re.search(r"\.{3,}\s*\d*\s*$", first_line)) or bool(re.match(r"\.{3,}", first_line))

            # Detect Index letter
            looks_like_index = bool(re.match(r"^[A-ZА-Я]$", first_line)) or bool(re.match(r"^[A-Z],\s*[A-Z]$", first_line))

            # Decide: heading-level or body-level?
            is_heading_level = block_max_size >= body_size * 1.3

            if is_heading_level:
                # Flush any accumulated body text before starting new chunk
                flush_body()

                ratio = block_max_size / body_size
                if ratio >= 2.0:
                    level = 1
                elif ratio >= 1.6:
                    level = 2
                else:
                    level = 3

                # Split heading from body for H2+ level blocks
                lines = text.split("\n", 1)
                heading_text = first_line.strip().replace("\x07", "").replace("\b", "")
                if level < 3 and len(lines) > 1:
                    body_text = lines[1].strip()
                else:
                    body_text = ""

                chunk = Chunk(
                    heading=heading_text,
                    content=body_text or "",
                    level=level,
                    sequence=seq,
                    font_size=block_max_size,
                    is_bold=block_is_bold,
                    near_drawing=near_drawing,
                    looks_like_toc_entry=looks_like_toc,
                    looks_like_index_letter=looks_like_index,
                )

                chunk.score = score_heading(chunk, body_size)
                chunks.append(chunk)
                seq += 1
            else:
                # Body-level block — accumulate for attaching to preceding heading
                body_accumulator.append(text)

    # Flush remaining body text
    flush_body()

    doc.close()
    return chunks


def get_pdf_metadata(path: Path) -> dict:
    """Extract book metadata from PDF metadata."""
    doc = fitz.open(str(path))
    meta = doc.metadata
    doc.close()

    import re
    title = meta.get("title", path.stem)
    book_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    # Extract year from creationDate (format: D:20220315184501Z)
    year = None
    cdate = meta.get("creationDate", "")
    if cdate:
        ym = re.search(r"D:(\d{4})", cdate)
        if ym:
            year = int(ym.group(1))

    result: dict = {
        "id": book_id,
        "title": title,
        "authors": [],
        "language": meta.get("language", "en"),
        "year": year,
        "source_format": "pdf",
        "book_type": "technical",
    }

    author = meta.get("author", "")
    if author:
        import re
        # Split on ; first (PDF format: Last1,First1;Last2,First2)
        for part in re.split(r"\s*;\s*", author):
            part = part.strip().rstrip(";")
            if not part:
                continue
            # If "Last, First" format, reverse it
            if "," in part:
                names = [n.strip() for n in part.split(",") if n.strip()]
                if len(names) == 2:
                    result["authors"].append(f"{names[1]} {names[0]}")
                else:
                    result["authors"].append(part)
            else:
                result["authors"].append(part)

    return result


# --- FB2 extraction (fallback) ---


def extract_fb2(path: Path) -> str:
    """Parse an FB2 file and return its content as structured markdown."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    body = root.find(f".//{FB2_NS}body")
    if body is None:
        raise ValueError("No <body> found in fb2")
    lines: list[str] = []
    _parse_element(body, lines, 0)
    return "\n".join(lines)


def get_fb2_metadata(path: Path) -> dict:
    """Extract book metadata (title, authors) from an FB2 file."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    title_info = root.find(f".//{FB2_NS}title-info")
    if title_info is None:
        return {"id": path.stem, "title": path.stem}

    title_el = title_info.find(f"{FB2_NS}book-title")
    title = _get_inner_text(title_el) if title_el is not None else path.stem

    authors: list[str] = []
    for author_el in title_info.findall(f"{FB2_NS}author"):
        first = author_el.findtext(f"{FB2_NS}first-name", default="")
        last = author_el.findtext(f"{FB2_NS}last-name", default="")
        name = f"{first} {last}".strip()
        if name:
            authors.append(name)

    lang_el = root.findtext(f".//{FB2_NS}lang", default="en")
    return {"id": path.stem, "title": title, "authors": authors, "language": lang_el}


def extract(path: Path) -> str:
    """Auto-detect format and extract structured markdown."""
    fmt = path.suffix.lstrip(".").lower()
    if fmt == "pdf":
        return extract_pdf(path)
    elif fmt == "fb2":
        return extract_fb2(path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def get_metadata(path: Path) -> dict:
    """Auto-detect format and extract book metadata."""
    fmt = path.suffix.lstrip(".").lower()
    if fmt == "pdf":
        return get_pdf_metadata(path)
    elif fmt == "fb2":
        return get_fb2_metadata(path)
    else:
        return {"id": path.stem, "title": path.stem}


# --- FB2 internals ---


def _parse_element(el: ET.Element, lines: list[str], depth: int) -> None:
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
    parts: list[str] = []
    if el.text:
        parts.append(el.text.strip())
    for child in el:
        if child.tag in (f"{FB2_NS}p", "p"):
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
