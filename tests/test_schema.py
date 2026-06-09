"""Tests for the metadata schema + controlled-vocabulary validation layer."""

import textwrap

import pytest

from ovbook import schema


# ── normalize_topics ─────────────────────────────────────────────────────────


def test_normalize_topics_lowercases_and_hyphenates():
    assert schema.normalize_topics(["Memory Management"]) == ["memory-management"]


def test_normalize_topics_collapses_and_strips_separators():
    assert schema.normalize_topics(["  File   Systems  "]) == ["file-systems"]


def test_normalize_topics_preserves_cyrillic():
    assert schema.normalize_topics(["Управление Памятью"]) == ["управление-памятью"]


def test_normalize_topics_drops_empties():
    assert schema.normalize_topics(["", "  ", "threads"]) == ["threads"]


# ── validate_domains ─────────────────────────────────────────────────────────


@pytest.fixture
def tech_vocab():
    return schema.Vocabulary(
        collection="tech-lib",
        domains=frozenset({"operating-systems", "devops-sre", "networks-protocols"}),
        topics_registry=["scheduling"],
    )


def test_validate_domains_accepts_known_domain(tech_vocab):
    # Does not raise.
    schema.validate_domains(["operating-systems"], tech_vocab)


def test_validate_domains_rejects_empty(tech_vocab):
    with pytest.raises(schema.SchemaError):
        schema.validate_domains([], tech_vocab)


def test_validate_domains_rejects_unknown_and_lists_allowed(tech_vocab):
    with pytest.raises(schema.SchemaError) as exc:
        schema.validate_domains(["kubernetes"], tech_vocab)
    msg = str(exc.value)
    assert "kubernetes" in msg
    # The error must surface the allowed vocabulary so the agent can self-correct.
    assert "operating-systems" in msg


# ── load_vocabulary ──────────────────────────────────────────────────────────


def _write_vocab(root):
    (root / "vocabulary.yaml").write_text(textwrap.dedent("""
        collections:
          tech-lib:
            domains:
              - operating-systems
              - devops-sre
            topics_registry:
              - scheduling
    """))


def test_load_vocabulary_walks_up_from_output(tmp_path):
    _write_vocab(tmp_path)
    output = tmp_path / "tech-lib" / "some-book"
    output.mkdir(parents=True)

    vocab = schema.load_vocabulary(output, "tech-lib")

    assert vocab.collection == "tech-lib"
    assert vocab.domains == frozenset({"operating-systems", "devops-sre"})
    assert vocab.topics_registry == ["scheduling"]


def test_load_vocabulary_missing_file_raises(tmp_path):
    with pytest.raises(schema.SchemaError) as exc:
        schema.load_vocabulary(tmp_path, "tech-lib")
    assert "vocabulary.yaml" in str(exc.value)


def test_load_vocabulary_unknown_collection_raises(tmp_path):
    _write_vocab(tmp_path)
    with pytest.raises(schema.SchemaError) as exc:
        schema.load_vocabulary(tmp_path, "psychology-lib")
    assert "psychology-lib" in str(exc.value)


# ── normalize_book_meta ──────────────────────────────────────────────────────


def test_normalize_book_meta_injects_domains_and_topics():
    out = schema.normalize_book_meta(
        {"title": "Modern Operating Systems"},
        domains=["operating-systems"],
        topics=["scheduling"],
    )
    assert out["domains"] == ["operating-systems"]
    assert out["topics"] == ["scheduling"]


def test_normalize_book_meta_fills_status_and_priority_defaults():
    out = schema.normalize_book_meta(
        {"title": "X"}, domains=["devops-sre"], topics=[]
    )
    assert out["status"] == "unread"
    assert out["priority"] == "high"


def test_normalize_book_meta_defaults_book_type_technical():
    out = schema.normalize_book_meta(
        {"title": "X"}, domains=["devops-sre"], topics=[]
    )
    assert out["book_type"] == "technical"


def test_normalize_book_meta_preserves_reader_fields():
    out = schema.normalize_book_meta(
        {"title": "X", "authors": ["A. Tanenbaum"], "id": "modern-os",
         "language": "en", "year": 2014, "source_format": "epub"},
        domains=["operating-systems"], topics=[],
    )
    assert out["title"] == "X"
    assert out["authors"] == ["A. Tanenbaum"]
    assert out["id"] == "modern-os"
    assert out["year"] == 2014
    assert out["source_format"] == "epub"


def test_normalize_book_meta_derives_bare_slug_id_when_missing():
    out = schema.normalize_book_meta(
        {"title": "Modern Operating Systems"},
        domains=["operating-systems"], topics=[],
    )
    # Bare slug, no 'tech-book-' prefix (per project decision).
    assert out["id"] == "modern-operating-systems"


def test_normalize_book_meta_has_all_contract_fields():
    out = schema.normalize_book_meta(
        {"title": "X"}, domains=["devops-sre"], topics=[]
    )
    assert set(schema.BOOK_FIELDS) <= set(out)
