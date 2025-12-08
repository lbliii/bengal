"""
Tests for page utilities (factories).
"""

from __future__ import annotations

from bengal.core.page.utils import create_synthetic_page


def test_create_synthetic_page_defaults() -> None:
    """Test that synthetic pages have required component model fields."""
    page = create_synthetic_page(
        title="404",
        description="Not Found",
        url="/404.html"
    )
    
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
        metadata={"foo": "bar"}
    )
    
    assert page.type == "search"
    assert page.variant == "wide"
    assert page.props["foo"] == "bar"
    assert page.metadata["foo"] == "bar"


