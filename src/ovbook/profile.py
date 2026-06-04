"""Document profile detection for PDF processing.

Analyzes a PDF before extraction to determine document type and
appropriate extraction strategy: born-digital / diagram-heavy / cjk-broken.
"""

from pathlib import Path
import re

import fitz  # PyMuPDF


def detect_profile(path: Path) -> dict:
    """Analyze PDF and return a document profile dict.

    Returns:
        type: born-digital | diagram-heavy | cjk-broken
        body_size: estimated body font size (median)
        encoding_ok: True if text extraction produces readable text
        page_count: number of pages
        has_index: True if document has Index section
        drawing_clusters: number of drawing clusters in first 10 pages
    """
    doc = fitz.open(str(path))
    page_count = len(doc)

    # --- Body font size ---
    sizes = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text
                for line in block["lines"]:
                    for span in line["spans"]:
                        sizes.append(span["size"])
        if len(sizes) > 200:
            break

    body_size = 12.0
    if sizes:
        sizes.sort()
        body_size = sizes[len(sizes) // 2]

    # --- Check encoding (mojibake) ---
    garbled_chars = 0
    total_chars = 0
    for i in range(min(5, len(doc))):
        text = doc[i].get_text()
        for ch in text:
            if ord(ch) > 127 and not (0x4E00 <= ord(ch) <= 0x9FFF):
                garbled_chars += 1
            total_chars += 1

    encoding_ok = total_chars == 0 or (garbled_chars / max(total_chars, 1)) < 0.3

    # --- Drawing clusters (diagram-heavy) ---
    drawing_count = 0
    for i in range(min(10, len(doc))):
        if hasattr(doc[i], "cluster_drawings"):
            try:
                drawings = doc[i].cluster_drawings()
                drawing_count += len(drawings)
            except Exception:
                pass

    # --- Index detection in last pages ---
    has_index = False
    for i in range(max(0, len(doc) - 20), len(doc)):
        text = doc[i].get_text("text")
        if re.search(r"^Index\s*$", text, re.MULTILINE):
            has_index = True
            break

    doc.close()

    # --- Determine profile type ---
    if not encoding_ok:
        doc_type = "cjk-broken"
    elif drawing_count > 50:
        doc_type = "diagram-heavy"
    else:
        doc_type = "born-digital"

    return {
        "type": doc_type,
        "body_size": round(body_size, 1),
        "encoding_ok": encoding_ok,
        "page_count": page_count,
        "has_index": has_index,
        "drawing_clusters": drawing_count,
    }
