"""
Integration tests for CSS optimization.

Tests the end-to-end CSS tree shaking functionality using skeleton-based test fixtures.
This dogfoods Bengal's skeleton manifest system for test site generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.orchestration.css_optimizer import CSSOptimizer, optimize_css_for_site

if TYPE_CHECKING:
    from bengal.core.site import Site


class TestCSSOptimizationIntegration:
    """Integration tests for CSS optimization with full site discovery."""

    def test_blog_only_site_includes_blog_css(self, site_factory) -> None:
        """Test that a blog-only site includes blog CSS and excludes doc CSS."""
        site: Site = site_factory("test-blog-only")

        # Create optimizer and get required files
        optimizer = CSSOptimizer(site)
        required_files = optimizer.get_required_css_files()

        # Should include blog CSS
        assert any("blog.css" in f for f in required_files), "Should include blog.css"

        # Should NOT include doc CSS
        assert not any("docs-nav.css" in f for f in required_files), "Should not include docs-nav.css"

        # Should NOT include tutorial CSS (not used)
        assert not any("tutorial.css" in f for f in required_files), "Should not include tutorial.css"

    def test_multi_type_site_includes_all_type_css(self, site_factory) -> None:
        """Test that a multi-type site includes CSS for all detected types."""
        site: Site = site_factory("test-multi-type-css")

        # Create optimizer
        optimizer = CSSOptimizer(site)
        content_types = optimizer.get_used_content_types()

        # Should detect all content types
        assert "blog" in content_types
        assert "doc" in content_types
        assert "tutorial" in content_types
        assert "landing" in content_types

        # Get required files
        required_files = optimizer.get_required_css_files()

        # Should include CSS for all types
        assert any("blog.css" in f for f in required_files)
        assert any("docs-nav.css" in f for f in required_files)
        assert any("tutorial.css" in f for f in required_files)
        assert any("landing.css" in f for f in required_files)

    def test_mermaid_detection_during_discovery(self, site_factory) -> None:
        """Test that mermaid feature is detected during content discovery."""
        site: Site = site_factory("test-mermaid-feature")

        # Features should be detected and stored in site during discover_content()
        assert "mermaid" in site.features_detected

        # Optimizer should include mermaid CSS
        optimizer = CSSOptimizer(site)
        required_files = optimizer.get_required_css_files()

        assert any("mermaid.css" in f for f in required_files), "Should include mermaid.css"

    def test_css_generation_returns_valid_css(self, site_factory) -> None:
        """Test that generated CSS is valid (non-empty with proper structure)."""
        site: Site = site_factory("test-blog-only")

        # Generate CSS
        optimizer = CSSOptimizer(site)
        css_content = optimizer.generate()

        # Should return valid CSS
        assert css_content is not None
        assert len(css_content) > 0

        # Should include @layer directive for proper CSS cascade
        assert "@layer" in css_content

    def test_css_report_provides_useful_metrics(self, site_factory) -> None:
        """Test that the CSS optimization report contains useful metrics."""
        site: Site = site_factory("test-multi-type-css")

        # Generate with report
        optimizer = CSSOptimizer(site)
        _, report = optimizer.generate(report=True)

        # Report should contain expected keys
        assert "types_detected" in report
        assert "features_detected" in report
        assert "included_files" in report
        assert "excluded_files" in report

        # Types should match what we created
        assert "blog" in report["types_detected"]
        assert "doc" in report["types_detected"]

    def test_optimize_css_for_site_convenience_function(self, site_factory) -> None:
        """Test the convenience function works end-to-end."""
        site: Site = site_factory("test-blog-only")

        # Use convenience function
        css = optimize_css_for_site(site)

        assert css is not None
        assert len(css) > 0
        assert "@layer" in css


class TestCSSConfigOverrides:
    """Test CSS optimization config overrides."""

    def test_force_include_adds_extra_css(self, site_factory) -> None:
        """Test that force_include config adds additional CSS files."""
        # Override config to force-include doc CSS
        site: Site = site_factory(
            "test-blog-only",
            confoverrides={"css.include": ["doc"]},
        )

        # Get optimizer
        optimizer = CSSOptimizer(site)
        required_files = optimizer.get_required_css_files()

        # Should include doc CSS even though no doc content exists
        assert any("docs-nav.css" in f for f in required_files)

    def test_force_exclude_removes_css(self, site_factory) -> None:
        """Test that force_exclude config removes CSS files."""
        # Override config to force-exclude blog CSS
        site: Site = site_factory(
            "test-multi-type-css",
            confoverrides={"css.exclude": ["blog"]},
        )

        # Get optimizer
        optimizer = CSSOptimizer(site)
        required_files = optimizer.get_required_css_files()

        # Should NOT include blog CSS
        assert not any("blog.css" in f for f in required_files)

        # Should still include doc CSS
        assert any("docs-nav.css" in f for f in required_files)


class TestSkeletonBasedFixtures:
    """Tests that verify our skeleton fixtures work correctly."""

    def test_blog_only_skeleton_creates_correct_structure(self, site_factory) -> None:
        """Verify the blog-only skeleton generates expected pages."""
        site: Site = site_factory("test-blog-only")

        # Should have pages from skeleton
        assert len(site.pages) >= 3  # _index, blog/_index, blog/post-1, blog/post-2

        # Find blog pages
        blog_pages = [p for p in site.pages if p.type == "blog"]
        assert len(blog_pages) >= 2, "Should have at least 2 blog pages"

    def test_multi_type_skeleton_creates_sections(self, site_factory) -> None:
        """Verify the multi-type skeleton generates expected sections."""
        site: Site = site_factory("test-multi-type-css")

        # Should have multiple sections
        section_paths = [str(s.path) for s in site.sections]
        assert any("blog" in p for p in section_paths), "Should have blog section"
        assert any("docs" in p for p in section_paths), "Should have docs section"
        assert any("tutorials" in p for p in section_paths), "Should have tutorials section"

    def test_mermaid_skeleton_contains_mermaid_content(self, site_factory) -> None:
        """Verify the mermaid skeleton has mermaid code blocks."""
        site: Site = site_factory("test-mermaid-feature")

        # Should have pages with mermaid content
        mermaid_pages = [p for p in site.pages if p.content and "```mermaid" in p.content]
        assert len(mermaid_pages) >= 1, "Should have at least 1 page with mermaid diagrams"
