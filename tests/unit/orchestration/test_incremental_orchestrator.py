"""
Tests for IncrementalOrchestrator including phase ordering optimizations.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.cache import BuildCache
from bengal.core.page import Page
from bengal.orchestration.incremental import IncrementalOrchestrator


@pytest.fixture
def mock_site():
    """Create a mock site with pages and assets."""
    site = Mock()
    site.root_path = Path("/fake/site")
    site.output_dir = Path("/fake/site/public")
    site.config = {}

    # Create some mock pages
    site.pages = [
        Page(
            source_path=Path("/fake/site/content/page1.md"),
            content="Content 1",
            metadata={"title": "Page 1", "tags": ["python", "testing"]},
        ),
        Page(
            source_path=Path("/fake/site/content/page2.md"),
            content="Content 2",
            metadata={"title": "Page 2", "tags": ["python"]},
        ),
        Page(
            source_path=Path("/fake/site/content/_generated/tags.md"),
            content="",
            metadata={"title": "Tags", "_generated": True, "type": "tag-index"},
        ),
    ]

    # Create some mock assets
    site.assets = [
        Mock(source_path=Path("/fake/site/assets/style.css")),
        Mock(source_path=Path("/fake/site/assets/script.js")),
    ]

    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create an IncrementalOrchestrator instance."""
    return IncrementalOrchestrator(mock_site)


class TestIncrementalOrchestrator:
    """Test suite for IncrementalOrchestrator."""

    def test_initialization(self, orchestrator, mock_site):
        """Test that orchestrator initializes correctly."""
        assert orchestrator.site == mock_site
        assert orchestrator.cache is None
        assert orchestrator.tracker is None

    def test_initialize_with_cache_disabled(self, orchestrator):
        """Test initialization with caching disabled."""
        cache, tracker = orchestrator.initialize(enabled=False)

        assert cache is not None
        assert tracker is not None
        assert orchestrator.cache is cache
        assert orchestrator.tracker is tracker

    @patch("bengal.cache.BuildCache.load")
    def test_initialize_with_cache_enabled(self, mock_load, orchestrator, mock_site):
        """Test initialization with caching enabled."""
        mock_cache = Mock()
        mock_load.return_value = mock_cache

        cache, tracker = orchestrator.initialize(enabled=True)

        # Should load existing cache
        cache_path = mock_site.output_dir / ".bengal-cache.json"
        mock_load.assert_called_once_with(cache_path)
        assert cache is mock_cache

    def test_check_config_changed_no_cache(self, orchestrator):
        """Test config change detection when cache is None."""
        result = orchestrator.check_config_changed()
        assert result is False

    def test_check_config_changed_file_exists(self, orchestrator, mock_site, tmp_path):
        """Test config change detection with existing file."""
        # Setup
        orchestrator.cache = Mock(spec=BuildCache)
        orchestrator.cache.is_changed.return_value = True

        # Create a temporary config file
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("title = 'Test'")
        mock_site.root_path = tmp_path

        # Test
        result = orchestrator.check_config_changed()

        assert result is True
        orchestrator.cache.is_changed.assert_called_once()
        orchestrator.cache.update_file.assert_called_once()

    def test_find_work_early_without_cache(self, orchestrator):
        """Test find_work_early raises error without cache."""
        with pytest.raises(RuntimeError, match="Cache not initialized"):
            orchestrator.find_work_early()

    def test_find_work_early_no_changes(self, orchestrator, mock_site):
        """Test find_work_early when no files changed."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()
        orchestrator.cache.is_changed.return_value = False

        # Mock the _get_theme_templates_dir to return None (no templates to check)
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, assets_to_process, change_summary = orchestrator.find_work_early()

        # Should return empty lists
        assert len(pages_to_build) == 0
        assert len(assets_to_process) == 0
        assert change_summary["Modified content"] == []
        assert change_summary["Modified assets"] == []

    def test_find_work_early_with_page_changes(self, orchestrator, mock_site):
        """Test find_work_early detects changed pages."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        # Simulate page1.md changed
        def is_changed(path):
            return str(path).endswith("page1.md")

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, assets_to_process, change_summary = orchestrator.find_work_early(
                verbose=True
            )

        # Should find page1.md
        assert len(pages_to_build) == 1
        assert pages_to_build[0].source_path.name == "page1.md"
        assert len(change_summary["Modified content"]) == 1

        # Should track taxonomy for changed page
        orchestrator.tracker.track_taxonomy.assert_called_once()

    def test_find_work_early_skips_generated_pages(self, orchestrator, mock_site):
        """Test that find_work_early skips generated pages."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()
        orchestrator.cache.is_changed.return_value = True

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, _ = orchestrator.find_work_early()

        # Should not include the generated page (tags.md)
        for page in pages_to_build:
            assert not page.metadata.get("_generated")

    def test_find_work_early_with_asset_changes(self, orchestrator, mock_site):
        """Test find_work_early detects changed assets."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        # Simulate style.css changed
        def is_changed(path):
            return str(path).endswith("style.css")

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, assets_to_process, change_summary = orchestrator.find_work_early(
                verbose=True
            )

        # Should find style.css
        assert len(assets_to_process) == 1
        assert len(change_summary["Modified assets"]) == 1

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_find_work_early_with_template_changes(
        self, mock_rglob, mock_exists, orchestrator, mock_site
    ):
        """Test find_work_early detects template changes and affected pages."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        # Mock template directory
        mock_exists.return_value = True
        template_file = Path("/fake/theme/templates/page.html")
        mock_rglob.return_value = [template_file]

        # Template changed and affects page1.md
        def is_changed(path):
            # Only template is changed, not content pages
            return str(path).endswith("page.html")

        orchestrator.cache.is_changed.side_effect = is_changed
        orchestrator.cache.get_affected_pages.return_value = [str(mock_site.pages[0].source_path)]

        with patch.object(
            orchestrator, "_get_theme_templates_dir", return_value=Path("/fake/theme/templates")
        ):
            pages_to_build, _, change_summary = orchestrator.find_work_early(verbose=True)

        # Should rebuild page1.md due to template change
        assert len(pages_to_build) == 1
        assert len(change_summary["Modified templates"]) == 1


class TestPhaseOrderingOptimization:
    """Test suite for phase ordering optimization."""

    def test_find_work_early_returns_pages_without_generated(self, orchestrator, mock_site):
        """Test that find_work_early returns only real pages, not generated ones."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()
        orchestrator.cache.is_changed.return_value = True

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, _ = orchestrator.find_work_early()

        # Should only return non-generated pages
        assert len(pages_to_build) == 2  # page1.md and page2.md, not tags.md
        assert all(not p.metadata.get("_generated") for p in pages_to_build)

    def test_find_work_early_tracks_tags(self, orchestrator, mock_site):
        """Test that changed pages with tags are tracked."""
        # Setup
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        # Only page1.md changed (has tags: python, testing)
        def is_changed(path):
            return str(path).endswith("page1.md")

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, _ = orchestrator.find_work_early()

        # Should track taxonomy for the changed page
        orchestrator.tracker.track_taxonomy.assert_called_once()
        call_args = orchestrator.tracker.track_taxonomy.call_args[0]
        assert call_args[1] == {"python", "testing"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
