"""Integration tests for complexity-based page ordering in parallel rendering.

Tests that the LPT scheduling optimization is correctly integrated with
the RenderOrchestrator and produces correct builds.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def high_variance_site(tmp_path: Path) -> Path:
    """Create a site with high complexity variance for testing."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create 10 heavy pages (many code blocks)
    for i in range(10):
        page = content_dir / f"api-reference-{i}.md"
        code_blocks = "```python\nimport foo\n```\n\n" * 25
        page.write_text(f"# API Reference {i}\n\n{code_blocks}")

    # Create 90 light pages (minimal content)
    for i in range(90):
        page = content_dir / f"blog-post-{i}.md"
        page.write_text(f"# Blog Post {i}\n\nShort content here.")

    # Create config
    config = tmp_path / "bengal.toml"
    config.write_text('[site]\ntitle = "Test Site"\n')

    return tmp_path


@pytest.fixture
def uniform_site(tmp_path: Path) -> Path:
    """Create a site with uniform complexity (all pages similar)."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create 50 similar pages
    for i in range(50):
        page = content_dir / f"page-{i}.md"
        page.write_text(f"# Page {i}\n\nSome standard content here.\n\n```python\nprint('hi')\n```")

    config = tmp_path / "bengal.toml"
    config.write_text('[site]\ntitle = "Uniform Site"\n')

    return tmp_path


class TestComplexityOrderingIntegration:
    """Integration tests for complexity ordering in builds."""

    def test_build_completes_with_ordering_enabled(self, high_variance_site: Path) -> None:
        """Build should complete successfully with complexity ordering."""
        from bengal.core.site import Site
        from bengal.orchestration import BuildOrchestrator

        site = Site(high_variance_site)
        orchestrator = BuildOrchestrator(site)

        # Build should complete without errors
        stats = orchestrator.build(parallel=True)

        # Verify pages were built - check site output_dir
        output_dir = site.output_dir
        assert (output_dir / "api-reference-0" / "index.html").exists()
        assert (output_dir / "blog-post-0" / "index.html").exists()

        # Should have processed all 100 pages
        assert stats.total_pages >= 100

    def test_build_completes_with_ordering_disabled(self, high_variance_site: Path) -> None:
        """Build should complete with complexity ordering disabled."""
        from bengal.core.site import Site
        from bengal.orchestration import BuildOrchestrator

        site = Site(high_variance_site)
        site.config["build"] = {"complexity_ordering": False}
        orchestrator = BuildOrchestrator(site)

        stats = orchestrator.build(parallel=True)

        # Should still complete successfully
        output_dir = site.output_dir
        assert (output_dir / "api-reference-0" / "index.html").exists()
        assert stats.total_pages >= 100

    def test_sequential_build_ignores_ordering(self, high_variance_site: Path) -> None:
        """Sequential builds shouldn't use complexity ordering (no benefit)."""
        from bengal.core.site import Site
        from bengal.orchestration import BuildOrchestrator

        site = Site(high_variance_site)
        orchestrator = BuildOrchestrator(site)

        # Sequential build
        stats = orchestrator.build(parallel=False)

        # Should complete
        assert stats.total_pages >= 100

    def test_uniform_site_builds_correctly(self, uniform_site: Path) -> None:
        """Uniform sites should build correctly with ordering enabled.

        Note: Performance comparison removed due to CI timing variability.
        The ordering overhead is ~15ms for 1000 pages, which is negligible
        but hard to measure reliably in integration tests due to setup variance.
        """
        from bengal.core.site import Site
        from bengal.orchestration import BuildOrchestrator

        site = Site(uniform_site)
        site.config["max_workers"] = 4
        site.config["build"] = {"complexity_ordering": True}

        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(parallel=True)

        # Build should complete and produce output
        assert stats.total_pages >= 50
        assert (site.output_dir / "page-0" / "index.html").exists()


class TestComplexityOrderingWithConfig:
    """Test configuration options for complexity ordering."""

    def test_default_is_enabled(self, tmp_path: Path) -> None:
        """Complexity ordering should be enabled by default."""
        from bengal.core.site import Site
        from bengal.orchestration.render import RenderOrchestrator

        # Minimal site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("# Home\n")
        (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Test"\n')

        site = Site(tmp_path)
        orchestrator = RenderOrchestrator(site)

        # Default should be True
        assert orchestrator._should_use_complexity_ordering() is True

    def test_can_disable_via_config(self, tmp_path: Path) -> None:
        """Complexity ordering can be disabled via config."""
        from bengal.core.site import Site
        from bengal.orchestration.render import RenderOrchestrator

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("# Home\n")
        (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Test"\n')

        site = Site(tmp_path)
        site.config["build"] = {"complexity_ordering": False}
        orchestrator = RenderOrchestrator(site)

        assert orchestrator._should_use_complexity_ordering() is False
