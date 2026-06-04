"""Per-format book readers producing a unified BookContent."""

from collections.abc import Callable
from pathlib import Path

from ovbook.readers import epub, fb2, pdf
from ovbook.readers.base import BookContent

_REGISTRY: dict[str, Callable[[Path], BookContent]] = {
    "pdf": pdf.read,
    "fb2": fb2.read,
    "epub": epub.read,
}


def get_reader(fmt: str) -> Callable[[Path], BookContent]:
    """Return the reader function for a format, or raise ValueError."""
    reader = _REGISTRY.get(fmt.lower())
    if reader is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unsupported format: '{fmt}' (supported: {supported})")
    return reader


__all__ = ["BookContent", "get_reader"]
