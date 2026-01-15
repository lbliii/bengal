"""
Tests for build-integrated validation (RFC: rfc-build-integrated-validation.md).

Verifies that:
1. BuildContext content caching works correctly
2. ContentDiscovery populates the cache during discovery
3. DirectiveAnalyzer uses cached content when available
4. Tiered validation filtering works correctly
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bengal.orchestration.build_context import BuildContext

if TYPE_CHECKING:
    pass


class TestBuildContextContentCache:
    """Tests for BuildContext content caching functionality."""

    def test_cache_content_stores_and_retrieves(self) -> None:
        """Test that cache_content stores content and get_content retrieves it."""
        ctx = BuildContext()
        path = Path("/content/test.md")
        content = "# Hello World\n\nThis is test content."

        ctx.cache_content(path, content)

        assert ctx.get_content(path) == content

    def test_get_content_returns_none_for_uncached(self) -> None:
        """Test that get_content returns None for paths not in cache."""
        ctx = BuildContext()

        result = ctx.get_content(Path("/nonexistent/path.md"))

        assert result is None

    def test_has_cached_content_false_when_empty(self) -> None:
        """Test has_cached_content returns False when cache is empty."""
        ctx = BuildContext()

        assert ctx.has_cached_content is False

    def test_has_cached_content_true_when_populated(self) -> None:
        """Test has_cached_content returns True when cache has entries."""
        ctx = BuildContext()
        ctx.cache_content(Path("/test.md"), "content")

        assert ctx.has_cached_content is True

    def test_content_cache_size(self) -> None:
        """Test content_cache_size returns correct count."""
        ctx = BuildContext()

        assert ctx.content_cache_size == 0

        ctx.cache_content(Path("/a.md"), "content a")
        ctx.cache_content(Path("/b.md"), "content b")
        ctx.cache_content(Path("/c.md"), "content c")

        assert ctx.content_cache_size == 3

    def test_clear_content_cache(self) -> None:
        """Test clear_content_cache removes all cached content."""
        ctx = BuildContext()
        ctx.cache_content(Path("/a.md"), "content a")
        ctx.cache_content(Path("/b.md"), "content b")

        ctx.clear_content_cache()

        assert ctx.content_cache_size == 0
        assert ctx.has_cached_content is False

    def test_clear_lazy_artifacts_clears_content_cache(self) -> None:
        """Test clear_lazy_artifacts also clears content cache."""
        ctx = BuildContext()
        ctx.cache_content(Path("/test.md"), "content")

        ctx.clear_lazy_artifacts()

        assert ctx.has_cached_content is False

    def test_get_all_cached_contents_returns_copy(self) -> None:
        """Test get_all_cached_contents returns a copy for thread safety."""
        ctx = BuildContext()
        ctx.cache_content(Path("/a.md"), "content a")
        ctx.cache_content(Path("/b.md"), "content b")

        all_contents = ctx.get_all_cached_contents()

        assert len(all_contents) == 2
        assert "/a.md" in all_contents or str(Path("/a.md")) in all_contents
        # Verify it's a copy by modifying it
        all_contents["new_key"] = "new_value"
        assert ctx.content_cache_size == 2  # Original unchanged

    def test_cache_content_thread_safe(self) -> None:
        """Test that cache operations are thread-safe."""
        ctx = BuildContext()
        errors = []

        def cache_items(start: int, count: int) -> None:
            try:
                for i in range(count):
                    path = Path(f"/content_{start}_{i}.md")
                    ctx.cache_content(path, f"content_{start}_{i}")
            except Exception as e:
                errors.append(e)

        # Start multiple threads caching simultaneously
        threads = [Thread(target=cache_items, args=(i, 100)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert ctx.content_cache_size == 500  # 5 threads * 100 items


class TestContentDiscoveryIntegration:
    """Tests for ContentDiscovery integration with BuildContext."""

    def test_discovery_caches_content_when_build_context_provided(self, tmp_path: Path) -> None:
        """Test that ContentDiscovery caches content when build_context is provided."""
        from bengal.content.discovery.content_discovery import ContentDiscovery

        # Create test content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        test_file = content_dir / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n\n# Hello World", encoding="utf-8")

        # Create BuildContext
        ctx = BuildContext()

        # Run discovery with build_context
        discovery = ContentDiscovery(content_dir, build_context=ctx)
        discovery.discover()

        # Verify content was cached
        assert ctx.has_cached_content
        assert ctx.get_content(test_file) is not None

    def test_discovery_works_without_build_context(self, tmp_path: Path) -> None:
        """Test that ContentDiscovery works normally without build_context."""
        from bengal.content.discovery.content_discovery import ContentDiscovery

        # Create test content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        test_file = content_dir / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n\n# Hello World", encoding="utf-8")

        # Run discovery without build_context (backward compat)
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        assert len(pages) == 1
        assert pages[0].title == "Test"


class TestDirectiveAnalyzerCacheIntegration:
    """Tests for DirectiveAnalyzer using cached content."""

    def test_analyzer_uses_cached_content(self, tmp_path: Path) -> None:
        """Test that DirectiveAnalyzer uses cached content when available."""
        from bengal.health.validators.directives.analysis import DirectiveAnalyzer

        # Create a real file so exists() works
        test_file = tmp_path / "test.md"
        test_file.write_text("placeholder", encoding="utf-8")

        # Create mock page with real path
        mock_page = MagicMock()
        mock_page.source_path = test_file
        mock_page.metadata = {}

        mock_site = MagicMock()
        mock_site.pages = [mock_page]

        # Create BuildContext with cached content (different from file)
        ctx = BuildContext()
        cached_content = """---
title: Test
---

:::{note}
This is a note directive
:::
"""
        ctx.cache_content(test_file, cached_content)

        # Run analyzer with build_context
        analyzer = DirectiveAnalyzer()
        result = analyzer.analyze(mock_site, build_context=ctx)

        # Verify we found the directive from cached content (not the placeholder file)
        assert result["total_directives"] == 1

    def test_analyzer_falls_back_to_disk(self, tmp_path: Path) -> None:
        """Test that DirectiveAnalyzer falls back to disk when content not cached."""
        from bengal.health.validators.directives.analysis import DirectiveAnalyzer

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n\nNo directives here.", encoding="utf-8")

        # Create mock page with real path
        mock_page = MagicMock()
        mock_page.source_path = test_file
        mock_page.metadata = {}

        mock_site = MagicMock()
        mock_site.pages = [mock_page]

        # Empty BuildContext (no cached content)
        ctx = BuildContext()

        # Run analyzer with build_context (empty cache)
        analyzer = DirectiveAnalyzer()
        result = analyzer.analyze(mock_site, build_context=ctx)

        # Verify no directives found (from disk)
        assert result["total_directives"] == 0

    def test_analyzer_works_without_build_context(self, tmp_path: Path) -> None:
        """Test that DirectiveAnalyzer works normally without build_context."""
        from bengal.health.validators.directives.analysis import DirectiveAnalyzer

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n\nNo directives here.", encoding="utf-8")

        # Create mock page with real path
        mock_page = MagicMock()
        mock_page.source_path = test_file
        mock_page.metadata = {}

        mock_site = MagicMock()
        mock_site.pages = [mock_page]

        # Run analyzer without build_context (backward compat)
        analyzer = DirectiveAnalyzer()
        result = analyzer.analyze(mock_site)

        # Verify no directives found (from disk)
        assert result["total_directives"] == 0


class TestTieredValidation:
    """Tests for tiered validation filtering."""

    def test_build_tier_includes_fast_validators(self) -> None:
        """Test that 'build' tier only includes fast validators."""
        from bengal.health.health_check import HealthCheck

        # Create mock site with config
        mock_site = MagicMock()
        mock_site.config = {
            "health_check": {
                "enabled": True,
                "build_validators": ["config", "output", "directives"],
                "full_validators": ["connectivity", "performance"],
                "ci_validators": ["fonts", "assets"],
            }
        }

        health = HealthCheck(mock_site, auto_register=False)

        # Create mock validators
        mock_validators = []
        for name in ["config", "output", "directives", "connectivity", "fonts"]:
            v = MagicMock()
            v.name = name.title()
            mock_validators.append(v)

        health.validators = mock_validators

        # Check tier filtering for build tier
        in_build = [v for v in mock_validators if health._is_validator_in_tier(v, "build")]
        names_in_build = {v.name.lower() for v in in_build}

        assert "config" in names_in_build
        assert "output" in names_in_build
        assert "directives" in names_in_build
        assert "connectivity" not in names_in_build
        assert "fonts" not in names_in_build

    def test_full_tier_includes_build_and_full_validators(self) -> None:
        """Test that 'full' tier includes build + full validators."""
        from bengal.health.health_check import HealthCheck

        mock_site = MagicMock()
        mock_site.config = {
            "health_check": {
                "enabled": True,
                "build_validators": ["config", "output"],
                "full_validators": ["connectivity", "performance"],
                "ci_validators": ["fonts"],
            }
        }

        health = HealthCheck(mock_site, auto_register=False)

        mock_validators = []
        for name in ["config", "output", "connectivity", "performance", "fonts"]:
            v = MagicMock()
            v.name = name.title()
            mock_validators.append(v)

        health.validators = mock_validators

        in_full = [v for v in mock_validators if health._is_validator_in_tier(v, "full")]
        names_in_full = {v.name.lower() for v in in_full}

        assert "config" in names_in_full
        assert "output" in names_in_full
        assert "connectivity" in names_in_full
        assert "performance" in names_in_full
        assert "fonts" not in names_in_full

    def test_ci_tier_includes_all_validators(self) -> None:
        """Test that 'ci' tier includes all validators."""
        from bengal.health.health_check import HealthCheck

        mock_site = MagicMock()
        mock_site.config = {
            "health_check": {
                "enabled": True,
                "build_validators": ["config"],
                "full_validators": ["connectivity"],
                "ci_validators": ["fonts"],
            }
        }

        health = HealthCheck(mock_site, auto_register=False)

        mock_validators = []
        for name in ["config", "connectivity", "fonts"]:
            v = MagicMock()
            v.name = name.title()
            mock_validators.append(v)

        health.validators = mock_validators

        in_ci = [v for v in mock_validators if health._is_validator_in_tier(v, "ci")]

        assert len(in_ci) == 3  # All validators

    def test_unconfigured_validators_included_by_default(self) -> None:
        """Test that validators not in any tier list are included by default."""
        from bengal.health.health_check import HealthCheck

        mock_site = MagicMock()
        mock_site.config = {
            "health_check": {
                "enabled": True,
                "build_validators": ["config"],
                "full_validators": [],
                "ci_validators": [],
            }
        }

        health = HealthCheck(mock_site, auto_register=False)

        # Validator not in any tier list
        mock_validator = MagicMock()
        mock_validator.name = "CustomValidator"

        # Should be included by default (backward compat)
        assert health._is_validator_in_tier(mock_validator, "build") is True


class TestEndToEnd:
    """End-to-end integration tests for build-integrated validation."""

    def test_full_build_with_validation(self, tmp_path: Path) -> None:
        """Test that a full build correctly caches content for validation."""
        # Create minimal site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create test page with a directive
        test_page = content_dir / "test.md"
        test_page.write_text(
            """---
title: Test Page
---

:::{note}
This is a test note
:::
""",
            encoding="utf-8",
        )

        # Create config
        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
baseurl = "/"
""",
            encoding="utf-8",
        )

        # Create BuildContext and run discovery
        from bengal.content.discovery.content_discovery import ContentDiscovery

        ctx = BuildContext()
        discovery = ContentDiscovery(content_dir, build_context=ctx)
        sections, pages = discovery.discover()

        # Verify content was cached
        assert ctx.has_cached_content
        cached = ctx.get_content(test_page)
        assert cached is not None
        assert ":::{note}" in cached

        # Verify pages were discovered
        assert len(pages) == 1
        assert pages[0].title == "Test Page"
