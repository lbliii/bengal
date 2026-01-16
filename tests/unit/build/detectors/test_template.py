"""
Unit tests for bengal.build.detectors.template.

Tests TemplateChangeDetector for template file change detection
and template engine cache invalidation integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import RebuildReasonCode
from bengal.build.detectors.template import TemplateChangeDetector


# =============================================================================
# Mock Template Engines
# =============================================================================


class MockTemplateEngine:
    """Mock template engine that supports cache invalidation."""

    def __init__(self) -> None:
        self.cleared_templates: list[list[str] | None] = []

    def clear_template_cache(self, names: list[str] | None = None) -> None:
        """Mock cache clearing method."""
        self.cleared_templates.append(names)


class MockTemplateEngineWithoutCache:
    """Mock template engine without cache invalidation support."""

    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.is_changed.return_value = False
    cache.get_affected_pages.return_value = []
    return cache


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site with temp directory."""
    site = MagicMock()
    site.root_path = tmp_path
    site.theme = None
    return site


@pytest.fixture
def detector() -> TemplateChangeDetector:
    """Create TemplateChangeDetector instance."""
    return TemplateChangeDetector()


# =============================================================================
# Basic Detection Tests
# =============================================================================


class TestTemplateChangeDetectorBasics:
    """Basic tests for TemplateChangeDetector."""

    def test_no_templates_returns_empty(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Missing templates directory returns empty result."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()
        assert result.templates_changed == frozenset()

    def test_empty_templates_dir_returns_empty(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Empty templates directory returns empty result."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()
        assert result.templates_changed == frozenset()


# =============================================================================
# Template Discovery Tests
# =============================================================================


class TestTemplateDiscovery:
    """Tests for template file discovery."""

    def test_site_templates_discovered(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Templates in site templates directory are discovered."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("base.html" in str(k) for k in result.templates_changed)

    def test_nested_templates_discovered(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Templates in nested directories are discovered."""
        templates_dir = mock_site.root_path / "templates"
        partials_dir = templates_dir / "partials"
        partials_dir.mkdir(parents=True)
        (partials_dir / "header.html").write_text("<header>")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("header.html" in str(k) for k in result.templates_changed)

    def test_only_html_files_discovered(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Only .html files are discovered as templates."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        (templates_dir / "style.css").write_text("body {}")
        (templates_dir / "script.js").write_text("console.log('hi')")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("base.html" in str(k) for k in result.templates_changed)
        assert not any(".css" in str(k) for k in result.templates_changed)
        assert not any(".js" in str(k) for k in result.templates_changed)


# =============================================================================
# Theme Templates Tests
# =============================================================================


class TestThemeTemplates:
    """Tests for theme template discovery."""

    def test_site_theme_templates_discovered(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Templates in site themes directory are discovered."""
        mock_site.theme = "default"
        theme_templates_dir = mock_site.root_path / "themes" / "default" / "templates"
        theme_templates_dir.mkdir(parents=True)
        (theme_templates_dir / "single.html").write_text("<article>")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("single.html" in str(k) for k in result.templates_changed)


# =============================================================================
# Change Detection Tests
# =============================================================================


class TestChangeDetection:
    """Tests for template change detection."""

    def test_unchanged_template_not_detected(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Unchanged templates don't trigger rebuild."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = False
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.templates_changed == frozenset()

    def test_forced_template_detected(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Template in forced_changed is detected."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = False
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            forced_changed=frozenset([CacheKey("templates/base.html")]),
        )
        result = detector.detect(ctx)
        
        assert any("base.html" in str(k) for k in result.templates_changed)


# =============================================================================
# Affected Pages Tests
# =============================================================================


class TestAffectedPages:
    """Tests for affected page detection."""

    def test_affected_pages_from_cache(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Pages affected by template change are detected."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md", "content/index.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/about.md") in result.pages_to_rebuild
        assert CacheKey("content/index.md") in result.pages_to_rebuild


# =============================================================================
# Rebuild Reason Tests
# =============================================================================


class TestRebuildReasons:
    """Tests for rebuild reason assignment."""

    def test_rebuild_reason_is_template_changed(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason code is TEMPLATE_CHANGED."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.TEMPLATE_CHANGED

    def test_rebuild_reason_trigger_contains_template_path(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason trigger contains template file path."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert "base.html" in reason.trigger


# =============================================================================
# Template Name Resolution Tests
# =============================================================================


class TestTemplateNameResolution:
    """Tests for template name resolution."""

    def test_template_name_relative_to_templates_dir(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Template name is relative to templates directory."""
        templates_dir = mock_site.root_path / "templates"
        partials_dir = templates_dir / "partials"
        partials_dir.mkdir(parents=True)
        template_path = partials_dir / "header.html"
        template_path.write_text("<header>")
        
        # Test private method
        result = detector._path_to_template_name(
            DetectionContext(cache=mock_cache, site=mock_site),
            template_path,
        )
        
        assert result == "partials/header.html"


# =============================================================================
# Template Engine Cache Invalidation Tests
# =============================================================================


class TestTemplateEngineCacheInvalidation:
    """Tests for template engine cache invalidation integration."""

    def test_cache_invalidation_called_when_engine_supports_it(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Bengal calls clear_template_cache() when engine supports it."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        mock_engine = MockTemplateEngine()
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = []

        with patch("bengal.rendering.engines.create_engine", return_value=mock_engine):
            ctx = DetectionContext(cache=mock_cache, site=mock_site)
            detector.detect(ctx)

            # Engine's clear_template_cache should have been called
            assert len(mock_engine.cleared_templates) > 0
            # Should have been called with list of template names
            assert isinstance(mock_engine.cleared_templates[0], list)
            assert "base.html" in mock_engine.cleared_templates[0]

    def test_cache_invalidation_not_called_when_engine_doesnt_support_it(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Bengal doesn't fail when engine doesn't support cache invalidation."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        mock_engine = MockTemplateEngineWithoutCache()
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = []

        with patch("bengal.rendering.engines.create_engine", return_value=mock_engine):
            ctx = DetectionContext(cache=mock_cache, site=mock_site)
            # Should not raise error
            result = detector.detect(ctx)
            assert result is not None

    def test_cache_invalidation_not_called_when_no_templates_changed(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Cache invalidation not called when no templates changed."""
        templates_dir = mock_site.root_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        mock_engine = MockTemplateEngine()
        mock_cache.is_changed.return_value = False  # No templates changed

        with patch("bengal.rendering.engines.create_engine", return_value=mock_engine):
            ctx = DetectionContext(cache=mock_cache, site=mock_site)
            detector.detect(ctx)

            # Engine's clear_template_cache should NOT have been called
            assert len(mock_engine.cleared_templates) == 0

    def test_cache_invalidation_includes_nested_templates(
        self, detector: TemplateChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Nested template names are correctly passed to engine cache."""
        templates_dir = mock_site.root_path / "templates"
        partials_dir = templates_dir / "partials"
        partials_dir.mkdir(parents=True)
        (partials_dir / "header.html").write_text("<header>")

        mock_engine = MockTemplateEngine()
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = []

        with patch("bengal.rendering.engines.create_engine", return_value=mock_engine):
            ctx = DetectionContext(cache=mock_cache, site=mock_site)
            detector.detect(ctx)

            assert len(mock_engine.cleared_templates) > 0
            # Should include the relative path
            assert "partials/header.html" in mock_engine.cleared_templates[0]
