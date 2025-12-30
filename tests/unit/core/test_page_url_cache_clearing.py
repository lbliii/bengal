"""
Test that page URL cache is properly cleared after setting output_path.

This prevents a bug where url is accessed before output_path is set,
causing it to cache the fallback slug-based URL (e.g., "/0.1.0/" instead
of "/releases/0.1.0/").
"""

from pathlib import Path
from unittest.mock import MagicMock

from bengal.core.page import Page
from bengal.core.site import Site


def test_url_cache_cleared_after_output_path_set():
    """Test that accessing url before output_path doesn't break URL generation."""

    # Create a mock site
    site = MagicMock(spec=Site)
    site.output_dir = Path("/tmp/public")
    site.config = {}

    # Create a page with numeric filename (the problematic case)
    page = Page(
        source_path=Path("/tmp/content/releases/0.1.0.md"),
        _raw_content="Test content",
        metadata={"title": "Release 0.1.0"},
    )
    page._site = site

    # Access URL BEFORE setting output_path (simulates early access during discovery)
    # This should return fallback: "/0.1.0/" - but NOT cache it (new behavior)
    early_url = page.href
    assert early_url == "/0.1.0/", "Should use fallback slug-based URL"

    # Verify it's NOT cached (fallback values are not cached to prevent stale URLs)
    # This is the new behavior - fallbacks don't get cached to allow proper URL
    # computation once output_path is set
    assert "_url_cache" not in page.__dict__, "Fallback URL should not be cached"
    assert "_relative_url_cache" not in page.__dict__, "Fallback relative_url should not be cached"

    # Now set the proper output_path
    page.output_path = Path("/tmp/public/releases/0.1.0/index.html")

    # No need to clear cache anymore since fallbacks are not cached
    # The next access will compute the correct URL from output_path

    # Now accessing url should compute the correct value
    correct_url = page.href
    assert correct_url == "/releases/0.1.0/", f"Should use path-based URL, got: {correct_url}"


def test_url_correct_when_output_path_set_first():
    """Test that URL is correct when output_path is set before first access."""

    # Create a mock site
    site = MagicMock(spec=Site)
    site.output_dir = Path("/tmp/public")
    site.config = {}

    # Create a page
    page = Page(
        source_path=Path("/tmp/content/releases/0.1.0.md"),
        _raw_content="Test content",
        metadata={"title": "Release 0.1.0"},
    )
    page._site = site

    # Set output_path BEFORE accessing url (correct order)
    page.output_path = Path("/tmp/public/releases/0.1.0/index.html")

    # Now access URL - should be correct
    url = page.href
    assert url == "/releases/0.1.0/", f"Should use path-based URL, got: {url}"


def test_url_fallback_without_output_path():
    """Test that URL falls back to slug when output_path not set."""

    page = Page(
        source_path=Path("/tmp/content/releases/0.1.0.md"),
        _raw_content="Test content",
        metadata={"title": "Release 0.1.0"},
    )
    # No site or output_path set

    url = page.href
    assert url == "/0.1.0/", "Should use slug-based fallback"


def test_numeric_filename_with_section():
    """Test that numeric filenames in sections generate correct URLs."""

    site = MagicMock(spec=Site)
    site.output_dir = Path("/tmp/public")
    site.config = {}

    page = Page(
        source_path=Path("/tmp/content/releases/0.1.2.md"),
        _raw_content="Test",
        metadata={"title": "Release 0.1.2"},
    )
    page._site = site
    page.output_path = Path("/tmp/public/releases/0.1.2/index.html")

    url = page.href
    assert url == "/releases/0.1.2/", f"Expected /releases/0.1.2/, got: {url}"
    assert not url.startswith("/0.1.2/"), "Should not drop section path"
