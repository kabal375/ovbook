"""Metadata schema + controlled-vocabulary validation for OpenViking book chunks.

This module is the single source of truth for the *shape* of book/chunk
frontmatter. The allowed *values* for ``domains`` live as data in ov-lib
(``vocabulary.yaml``), loaded via :func:`load_vocabulary`.

Design split:
    - field contract (which keys a book/chunk card has) → code, here
    - controlled vocabulary (which domains are legal) → data, in ov-lib
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

VOCABULARY_FILENAME = "vocabulary.yaml"

# Canonical book-card frontmatter fields, in MVP order. Single source of truth
# for the *shape* of 00-book.md (the allowed domain *values* live in ov-lib).
BOOK_FIELDS = (
    "id", "title", "authors", "domains", "topics", "book_type",
    "source_format", "language", "year", "edition", "status", "priority",
)


def _slug(text: str) -> str:
    return re.sub(r"[^0-9a-zа-я]+", "-", text.lower()).strip("-")


def normalize_book_meta(
    raw: dict, *, domains: list[str], topics: list[str]
) -> dict:
    """Reconcile a reader's loose meta dict into the canonical book card.

    Fills every field in :data:`BOOK_FIELDS`, preserving reader-provided values
    and applying MVP defaults for the rest. ``id`` is a bare slug of the title
    when absent (no ``tech-book-`` prefix, per project decision). Domains and
    topics are injected from the (already validated/normalized) arguments.
    """
    title = raw.get("title") or "untitled"
    out: dict = {
        "id": raw.get("id") or _slug(title),
        "title": title,
        "authors": raw.get("authors") or [],
        "domains": domains,
        "topics": topics,
        "book_type": raw.get("book_type") or "technical",
        "source_format": raw.get("source_format"),
        "language": raw.get("language") or "en",
        "year": raw.get("year"),
        "edition": raw.get("edition"),
        "status": raw.get("status") or "unread",
        "priority": raw.get("priority") or "high",
    }
    return out


class SchemaError(Exception):
    """Raised when book metadata violates the schema or controlled vocabulary."""


@dataclass(frozen=True)
class Vocabulary:
    """Controlled vocabulary for one collection, loaded from ov-lib.

    domains:         closed set — any domain outside it is rejected.
    topics_registry: open, accumulating list — used for soft governance only.
    """

    collection: str
    domains: frozenset[str]
    topics_registry: list[str]


def load_vocabulary(start: Path, collection: str) -> Vocabulary:
    """Find and load the controlled vocabulary for ``collection``.

    Searches for ``vocabulary.yaml`` starting at ``start`` and walking up the
    directory tree (the file lives at the root of the ov-lib content repo,
    above the per-collection ``tech-lib/`` directory).

    Raises :class:`SchemaError` when the file is absent (so a book can never be
    written without a validated classification) or when the collection is not
    defined in it.
    """
    path = _find_upwards(start, VOCABULARY_FILENAME)
    if path is None:
        raise SchemaError(
            f"No {VOCABULARY_FILENAME} found at or above {start}. "
            f"Domains cannot be validated without it."
        )

    data = yaml.safe_load(path.read_text()) or {}
    collections = data.get("collections", {})
    if collection not in collections:
        raise SchemaError(
            f"Collection '{collection}' not defined in {path}. "
            f"Available: {sorted(collections)}"
        )

    spec = collections[collection] or {}
    return Vocabulary(
        collection=collection,
        domains=frozenset(spec.get("domains") or []),
        topics_registry=list(spec.get("topics_registry") or []),
    )


def _find_upwards(start: Path, filename: str) -> Path | None:
    start = start.resolve()
    candidates = [start, *start.parents] if start.is_dir() else list(start.parents)
    for directory in candidates:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def validate_domains(domains: list[str], vocab: Vocabulary) -> None:
    """Validate book domains against a collection's closed vocabulary.

    Hard-fails (raises :class:`SchemaError`) when:
        - ``domains`` is empty — the agent forgot to classify the book;
        - any domain is not in ``vocab.domains`` — the agent invented one.

    New domains are added only by editing ``vocabulary.yaml`` (human request),
    never silently here.
    """
    if not domains:
        raise SchemaError(
            f"No domains given for collection '{vocab.collection}'. "
            f"Pick at least one from: {_sorted(vocab.domains)}"
        )
    unknown = [d for d in domains if d not in vocab.domains]
    if unknown:
        raise SchemaError(
            f"Unknown domain(s) {unknown} for collection '{vocab.collection}'. "
            f"Allowed: {_sorted(vocab.domains)}. "
            f"To add a new domain, request it and edit vocabulary.yaml."
        )


def _sorted(domains: frozenset[str]) -> list[str]:
    return sorted(domains)


def normalize_topics(topics: list[str]) -> list[str]:
    """Normalize free-form topics to kebab-case, dropping empties.

    Topics are open vocabulary: the agent proposes them from book content.
    Only their *format* is enforced (never blocks conversion). Cyrillic is
    preserved per vault conventions.
    """
    out: list[str] = []
    for raw in topics:
        slug = re.sub(r"[^0-9a-zа-я]+", "-", raw.strip().lower()).strip("-")
        if slug:
            out.append(slug)
    return out
