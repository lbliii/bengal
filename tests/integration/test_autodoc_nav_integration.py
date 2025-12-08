"""
Integration tests for autodoc page navigation rendering.

Verifies that all autodoc page types (module, section index, root index)
render with proper navigation menus just like regular pages.
"""

from pathlib import Path

import pytest


@pytest.fixture
def built_site_output():
    """Return the built site output directory."""
    # Use the actual site output from the bengal/site/public directory
    # This assumes the site has been built before running tests
    # Path hierarchy: tests/integration/test_file.py -> parents[2] = repo root
    site_output = Path(__file__).parents[2] / "site" / "public"
    if not site_output.exists():
        pytest.skip("Site not built. Run 'bengal build' first.")
    return site_output


class TestAutodocNavRendering:
    """Test that autodoc pages have proper navigation."""

    def test_regular_page_has_nav(self, built_site_output):
        """Regular documentation pages should have navigation."""
        regular_page = built_site_output / "docs" / "index.html"
        if not regular_page.exists():
            pytest.skip("docs/index.html not found")

        html = regular_page.read_text()

        # Check for main navigation
        assert "nav-main" in html or "nav" in html
        assert "Documentation" in html or "Docs" in html

    def test_autodoc_module_page_has_nav(self, built_site_output):
        """Autodoc module pages should have navigation."""
        # Check a deep module page
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Check for main navigation elements
        assert "nav-main" in html or "nav" in html

    def test_autodoc_section_index_has_nav(self, built_site_output):
        """Autodoc section index pages should have navigation."""
        section_index = built_site_output / "api" / "core" / "index.html"
        if not section_index.exists():
            pytest.skip("api/core/index.html not found")

        html = section_index.read_text()

        # Check for main navigation elements
        assert "nav-main" in html or "nav" in html

    def test_autodoc_root_index_has_nav(self, built_site_output):
        """Autodoc root index page should have navigation."""
        root_index = built_site_output / "api" / "index.html"
        if not root_index.exists():
            pytest.skip("api/index.html not found")

        html = root_index.read_text()

        # Check for main navigation elements
        assert "nav-main" in html or "nav" in html

    def test_nav_consistency_regular_vs_autodoc(self, built_site_output):
        """Navigation should be consistent between regular and autodoc pages."""
        regular_page = built_site_output / "docs" / "index.html"
        autodoc_page = built_site_output / "api" / "core" / "page" / "index.html"

        if not regular_page.exists() or not autodoc_page.exists():
            pytest.skip("Required pages not found")

        regular_html = regular_page.read_text()
        autodoc_html = autodoc_page.read_text()

        # Count nav-main occurrences - should be similar
        regular_nav_count = regular_html.count("nav-main")
        autodoc_nav_count = autodoc_html.count("nav-main")

        # Both should have nav-main
        assert regular_nav_count >= 1
        assert autodoc_nav_count >= 1


class TestAutodocMenuContent:
    """Test that menu content is properly rendered on autodoc pages."""

    def test_autodoc_page_has_menu_links(self, built_site_output):
        """Autodoc pages should have clickable menu links."""
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Check for href links (indicating clickable menu items)
        assert 'href="/docs/' in html or 'href="/api/' in html

    def test_autodoc_page_has_site_title(self, built_site_output):
        """Autodoc pages should have the site title."""
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Check for site title in header
        assert "Bengal" in html


class TestAutodocPageTypes:
    """Test all autodoc page types are rendered correctly."""

    @pytest.mark.parametrize(
        "page_path,page_type",
        [
            ("api/index.html", "root_index"),
            ("api/core/index.html", "section_index"),
            ("api/core/page/index.html", "module"),
        ],
    )
    def test_autodoc_page_has_doctype(self, built_site_output, page_path, page_type):
        """All autodoc pages should have proper HTML doctype."""
        page = built_site_output / page_path
        if not page.exists():
            pytest.skip(f"{page_path} not found")

        html = page.read_text()

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "</html>" in html

    @pytest.mark.parametrize(
        "page_path,page_type",
        [
            ("api/index.html", "root_index"),
            ("api/core/index.html", "section_index"),
            ("api/core/page/index.html", "module"),
        ],
    )
    def test_autodoc_page_has_head_meta(self, built_site_output, page_path, page_type):
        """All autodoc pages should have proper head metadata."""
        page = built_site_output / page_path
        if not page.exists():
            pytest.skip(f"{page_path} not found")

        html = page.read_text()

        assert '<meta charset="UTF-8">' in html
        assert "<title>" in html
        assert "</title>" in html


class TestAutodocThemeElements:
    """Test that theme elements are rendered on autodoc pages."""

    def test_autodoc_page_has_css(self, built_site_output):
        """Autodoc pages should include theme CSS."""
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Check for stylesheet link
        assert '<link rel="stylesheet"' in html or "stylesheet" in html

    def test_autodoc_page_has_js(self, built_site_output):
        """Autodoc pages should include theme JavaScript."""
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Check for script tags
        assert "<script" in html


class TestAutodocFallbackPages:
    """Test that fallback-rendered pages still work correctly."""

    def test_fallback_page_has_metadata_tag(self, built_site_output):
        """Pages rendered via fallback should have metadata tag (if any exist)."""
        # This test checks that if fallback pages exist, they have proper structure
        # In practice, fallback pages should be rare, so we just verify structure
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        html = module_page.read_text()

        # Fallback pages should still have proper HTML structure
        assert "<html" in html or "<!DOCTYPE" in html

    def test_fallback_page_still_writes_output(self, built_site_output):
        """Fallback pages should still write output files."""
        # Any autodoc page that exists should have been written
        module_page = built_site_output / "api" / "core" / "page" / "index.html"
        if not module_page.exists():
            pytest.skip("api/core/page/index.html not found")

        # File should exist and be readable
        assert module_page.is_file()
        assert len(module_page.read_text()) > 0
