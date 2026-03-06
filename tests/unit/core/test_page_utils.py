"""
Tests for page utilities (factories and helpers).
"""

from __future__ import annotations

from bengal.core.page.utils import create_synthetic_page, normalize_tags


def test_create_synthetic_page_defaults() -> None:
    """Test that synthetic pages have required component model fields."""
    page = create_synthetic_page(title="404", description="Not Found", url="/404.html")

    # Check Component Model fields
    assert page.type == "special"
    assert page.variant is None
    assert page.props == {}  # Defaults to empty dict

    # Check template compatibility fields
    assert page.toc == ""
    assert page.toc_items == []
    assert page.reading_time == 0


def test_create_synthetic_page_custom() -> None:
    """Test customizing synthetic page fields."""
    page = create_synthetic_page(
        title="Search",
        description="Search",
        url="/search/",
        type="search",
        variant="wide",
        metadata={"foo": "bar"},
    )

    assert page.type == "search"
    assert page.variant == "wide"
    assert page.props["foo"] == "bar"
    assert page.metadata["foo"] == "bar"


# --- normalize_tags (frontmatter defense-in-depth) ---


def test_normalize_tags_none() -> None:
    """tags: null or missing → []."""
    assert normalize_tags(None) == []


def test_normalize_tags_string() -> None:
    """tags: 'single' (string) → ['single']."""
    assert normalize_tags("single") == ["single"]


def test_normalize_tags_string_empty() -> None:
    """tags: '' or whitespace-only string → []."""
    assert normalize_tags("") == []
    assert normalize_tags("   ") == []


def test_normalize_tags_list_with_empty_items() -> None:
    """tags: ['', 'a', '  ', 'b'] → ['a', 'b']."""
    assert normalize_tags(["", "a", "  ", "b"]) == ["a", "b"]


def test_normalize_tags_list_valid() -> None:
    """tags: ['a', 'b'] → ['a', 'b']."""
    assert normalize_tags(["a", "b"]) == ["a", "b"]


def test_normalize_tags_list_empty() -> None:
    """tags: [] → []."""
    assert normalize_tags([]) == []


def test_normalize_tags_non_iterable() -> None:
    """Non-iterable (e.g. int) → []."""
    assert normalize_tags(42) == []
