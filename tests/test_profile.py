"""Tests for ovbook.profile — document profile detection."""

from ovbook.profile import detect_profile


def test_returns_all_required_keys(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    for key in ("type", "body_size", "encoding_ok", "page_count", "has_index", "drawing_clusters"):
        assert key in profile, f"Missing key: {key}"


def test_born_digital_type(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    assert profile["encoding_ok"] is True
    assert profile["type"] == "born-digital"


def test_body_size_positive(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    assert profile["body_size"] > 0


def test_page_count(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    assert profile["page_count"] == 7  # test PDF now has 7 pages


def test_drawing_clusters_non_negative(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    assert profile["drawing_clusters"] >= 0


def test_no_index_in_test_pdf(pdf_fixture):
    profile = detect_profile(pdf_fixture)
    assert profile["has_index"] is False


def test_body_size_consistent_with_extract(pdf_fixture):
    """body_size from detect_profile should match _compute_body_size in extract."""
    from ovbook.extract import _compute_body_size
    import fitz

    profile = detect_profile(pdf_fixture)
    doc = fitz.open(str(pdf_fixture))
    computed = _compute_body_size(doc)
    doc.close()

    assert abs(profile["body_size"] - computed) < 0.5, (
        f"detect_profile body_size {profile['body_size']} diverges from "
        f"_compute_body_size {computed}"
    )
