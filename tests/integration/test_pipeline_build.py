"""
Integration tests for the reactive dataflow pipeline build.

Tests that Site.build(use_pipeline=True) produces the same output as the
standard orchestrator build, including:
- All pages rendered
- All assets copied
- Taxonomies generated
- Postprocessing (sitemap, RSS, etc.)
"""

from __future__ import annotations

import pytest


@pytest.fixture
def basic_site(site_factory):
    """Create a basic test site."""
    return site_factory("test-basic")


class TestPipelineBuildIntegration:
    """Integration tests for pipeline builds."""

    def test_pipeline_build_renders_all_pages(self, basic_site):
        """Pipeline build should render all pages."""
        # Build with pipeline
        stats = basic_site.build(use_pipeline=True)

        # Verify pages were rendered
        assert stats.total_pages > 0

        # Check output directory has HTML files
        html_files = list(basic_site.output_dir.rglob("*.html"))
        assert len(html_files) > 0, "No HTML files generated"

    def test_pipeline_build_copies_assets(self, basic_site):
        """Pipeline build should copy all assets to output."""
        # Build with pipeline
        basic_site.build(use_pipeline=True)

        # Check assets directory exists
        assets_dir = basic_site.output_dir / "assets"
        assert assets_dir.exists(), "Assets directory not created"

        # Check for CSS files (theme should have CSS)
        css_files = list(assets_dir.rglob("*.css"))
        assert len(css_files) > 0, "No CSS files copied"

        # Check for JS files
        js_files = list(assets_dir.rglob("*.js"))
        assert len(js_files) > 0, "No JS files copied"

    def test_pipeline_build_generates_index(self, basic_site):
        """Pipeline build should generate index.html at root."""
        basic_site.build(use_pipeline=True)

        index_path = basic_site.output_dir / "index.html"
        assert index_path.exists(), "index.html not generated"

        # Verify it has content
        content = index_path.read_text()
        assert len(content) > 100, "index.html appears empty"
        assert "<html" in content.lower(), "index.html missing html tag"

    def test_pipeline_build_generates_sitemap(self, basic_site):
        """Pipeline build should generate sitemap.xml."""
        basic_site.build(use_pipeline=True)

        sitemap_path = basic_site.output_dir / "sitemap.xml"
        assert sitemap_path.exists(), "sitemap.xml not generated"

        content = sitemap_path.read_text()
        assert "<urlset" in content, "sitemap.xml missing urlset"

    def test_pipeline_matches_orchestrator_page_count(self, basic_site):
        """Pipeline build should produce same page count as orchestrator."""
        # Build with orchestrator first
        stats_orch = basic_site.build(use_pipeline=False)
        orch_page_count = stats_orch.total_pages

        # Clean and rebuild with pipeline
        import shutil

        if basic_site.output_dir.exists():
            shutil.rmtree(basic_site.output_dir)

        # Reset ephemeral state for fresh build
        basic_site.reset_ephemeral_state()

        stats_pipe = basic_site.build(use_pipeline=True)

        # Compare page counts
        assert stats_pipe.total_pages == orch_page_count, (
            f"Pipeline built {stats_pipe.total_pages} pages, orchestrator built {orch_page_count}"
        )

    def test_pipeline_build_with_taxonomies(self, site_factory):
        """Pipeline build should generate taxonomy pages (tags, categories)."""
        site = site_factory("test-basic")
        site.build(use_pipeline=True)

        # Check if any tag pages exist (if the test site has tags)
        tags_dir = site.output_dir / "tags"
        if tags_dir.exists():
            tag_pages = list(tags_dir.rglob("*.html"))
            assert len(tag_pages) > 0, "No tag pages generated"


class TestPipelineBuildAssets:
    """Specific tests for asset handling in pipeline builds."""

    def test_theme_assets_copied(self, basic_site):
        """Theme assets should be copied to output."""
        basic_site.build(use_pipeline=True)

        # Check assets directory exists and has CSS files (may be bundled)
        assets_dir = basic_site.output_dir / "assets"
        assert assets_dir.exists(), "Assets directory not created"

        css_files = list(assets_dir.rglob("*.css"))
        assert len(css_files) > 0, "No CSS files copied/bundled"

    def test_font_assets_copied(self, basic_site):
        """Font assets should be copied to output."""
        basic_site.build(use_pipeline=True)

        fonts_dir = basic_site.output_dir / "assets" / "fonts"
        if fonts_dir.exists():
            font_files = list(fonts_dir.rglob("*"))
            # If fonts dir exists, it should have files
            assert len(font_files) > 0, "Fonts directory empty"

    def test_js_assets_copied(self, basic_site):
        """JavaScript assets should be copied to output."""
        basic_site.build(use_pipeline=True)

        js_dir = basic_site.output_dir / "assets" / "js"
        assert js_dir.exists(), "JS directory not created"

        js_files = list(js_dir.rglob("*.js"))
        assert len(js_files) > 0, "No JS files copied"


class TestPipelineBuildEdgeCases:
    """Edge case tests for pipeline builds."""

    def test_empty_site_builds(self, tmp_path):
        """Pipeline should handle site with minimal content."""
        from bengal.core.site import Site

        # Create minimal site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Welcome")

        # Create minimal config
        (tmp_path / "bengal.toml").write_text('title = "Test"')

        site = Site.from_config(tmp_path)
        stats = site.build(use_pipeline=True)

        assert stats.total_pages >= 1

    def test_pipeline_parallel_flag(self, basic_site):
        """Pipeline should respect parallel=False."""
        # Should not raise
        stats = basic_site.build(use_pipeline=True, parallel=False)
        assert stats.total_pages > 0
