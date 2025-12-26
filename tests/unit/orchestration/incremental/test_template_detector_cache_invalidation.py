"""Tests for template engine cache invalidation integration.

Tests that Bengal optionally calls clear_template_cache() when templates change,
if the engine supports it.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.cache.build_cache.core import BuildCache
from bengal.orchestration.incremental.template_detector import TemplateChangeDetector


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


class TestTemplateEngineCacheInvalidation:
    """Tests for optional template engine cache invalidation."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with template directories."""
        site = MagicMock()
        site.root_path = tmp_path
        site.theme = "default"
        site.config = {}
        return site

    @pytest.fixture
    def mock_cache(self):
        """Create a mock build cache."""
        cache = MagicMock(spec=BuildCache)
        cache.file_fingerprints = {}
        cache.dependencies = {}
        cache.reverse_dependencies = {}
        cache.output_sources = {}
        cache.is_changed = MagicMock(return_value=False)
        cache.get_affected_pages = MagicMock(return_value=set())
        cache.update_file = MagicMock()
        return cache

    def test_cache_invalidation_called_when_engine_supports_it(
        self, mock_site, mock_cache, tmp_path
    ):
        """Bengal calls clear_template_cache() when engine supports it."""
        # Create template file
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        # Create mock engine with cache invalidation
        mock_engine = MockTemplateEngine()

        # Mock create_engine to return our mock
        with pytest.MonkeyPatch().context() as m:
            from bengal.rendering import engines

            m.setattr(engines, "create_engine", lambda site: mock_engine)

            # Mark template as changed
            mock_cache.is_changed = MagicMock(return_value=True)
            mock_cache.get_affected_pages = MagicMock(return_value=set())

            detector = TemplateChangeDetector(mock_site, mock_cache)
            detector.check_templates(
                pages_to_rebuild=set(),
                change_summary=MagicMock(),
                verbose=False,
            )

            # Engine's clear_template_cache should have been called
            assert len(mock_engine.cleared_templates) > 0
            # Should have been called with list of template names
            assert isinstance(mock_engine.cleared_templates[0], list)
            assert "base.html" in mock_engine.cleared_templates[0]

    def test_cache_invalidation_not_called_when_engine_doesnt_support_it(
        self, mock_site, mock_cache, tmp_path
    ):
        """Bengal doesn't fail when engine doesn't support cache invalidation."""
        # Create template file
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        # Create mock engine without cache invalidation
        mock_engine = MockTemplateEngineWithoutCache()

        # Mock create_engine to return our mock
        with pytest.MonkeyPatch().context() as m:
            from bengal.rendering import engines

            m.setattr(engines, "create_engine", lambda site: mock_engine)

            # Mark template as changed
            mock_cache.is_changed = MagicMock(return_value=True)
            mock_cache.get_affected_pages = MagicMock(return_value=set())

            detector = TemplateChangeDetector(mock_site, mock_cache)
            # Should not raise error
            detector.check_templates(
                pages_to_rebuild=set(),
                change_summary=MagicMock(),
                verbose=False,
            )

    def test_cache_invalidation_not_called_when_no_templates_changed(
        self, mock_site, mock_cache, tmp_path
    ):
        """Cache invalidation not called when no templates changed."""
        # Create template file
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        # Create mock engine
        mock_engine = MockTemplateEngine()

        # Mock create_engine
        with pytest.MonkeyPatch().context() as m:
            from bengal.rendering import engines

            m.setattr(engines, "create_engine", lambda site: mock_engine)

            # Mark template as unchanged
            mock_cache.is_changed = MagicMock(return_value=False)

            detector = TemplateChangeDetector(mock_site, mock_cache)
            detector.check_templates(
                pages_to_rebuild=set(),
                change_summary=MagicMock(),
                verbose=False,
            )

            # Engine's clear_template_cache should NOT have been called
            assert len(mock_engine.cleared_templates) == 0
