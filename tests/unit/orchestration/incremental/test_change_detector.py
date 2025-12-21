"""
Tests for ChangeDetector component of the incremental package.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.cache import BuildCache
from bengal.core.page import Page
from bengal.orchestration.incremental.change_detector import ChangeDetector


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with basic structure."""
    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.theme = None
    site.sections = []

    # Create pages
    site.pages = [
        Page(
            source_path=tmp_path / "content/page1.md",
            content="Content 1",
            metadata={"title": "Page 1", "tags": ["python"]},
        ),
        Page(
            source_path=tmp_path / "content/page2.md",
            content="Content 2",
            metadata={"title": "Page 2"},
        ),
    ]
    site.assets = []
    site.regular_pages = site.pages
    site.generated_pages = []
    return site


@pytest.fixture
def mock_cache():
    """Create a mock BuildCache."""
    cache = Mock(spec=BuildCache)
    cache.should_bypass = Mock(return_value=False)
    cache.is_changed = Mock(return_value=False)
    cache.get_affected_pages = Mock(return_value=[])
    cache.autodoc_dependencies = {}
    cache.last_build = None
    cache.parsed_content = {}
    return cache


@pytest.fixture
def mock_tracker():
    """Create a mock DependencyTracker."""
    tracker = Mock()
    tracker.track_taxonomy = Mock()
    return tracker


@pytest.fixture
def detector(mock_site, mock_cache, mock_tracker):
    """Create a ChangeDetector instance."""
    return ChangeDetector(mock_site, mock_cache, mock_tracker)


class TestChangeDetectorBasic:
    """Basic tests for ChangeDetector."""

    def test_detect_changes_no_changes(self, detector):
        """Test detection when no files changed."""
        change_set = detector.detect_changes("early")

        assert change_set.pages_to_build == []
        assert change_set.assets_to_process == []
        assert change_set.change_summary.modified_content == []

    def test_detect_changes_with_page_change(self, detector, mock_cache, mock_site):
        """Test detection when a page changed."""

        # Simulate page1.md changed
        def should_bypass(path, changed_sources=None):
            return str(path).endswith("page1.md")

        mock_cache.should_bypass.side_effect = should_bypass

        change_set = detector.detect_changes("early", verbose=True)

        assert len(change_set.pages_to_build) == 1
        assert change_set.pages_to_build[0].source_path.name == "page1.md"
        assert len(change_set.change_summary.modified_content) == 1

    def test_detect_changes_skips_generated_pages(self, detector, mock_cache, mock_site):
        """Test that generated pages are skipped."""
        # Add a generated page
        generated_page = Page(
            source_path=mock_site.root_path / "content/_generated/tags.md",
            content="",
            metadata={"_generated": True},
        )
        mock_site.pages.append(generated_page)

        # All pages "changed"
        mock_cache.should_bypass.return_value = True

        change_set = detector.detect_changes("early")

        # Generated page should not be in results
        for page in change_set.pages_to_build:
            assert not page.metadata.get("_generated")

    def test_detect_changes_with_forced_sources(self, detector, mock_cache, mock_site):
        """Test detection with forced changed sources."""
        forced_path = mock_site.root_path / "content/page2.md"

        # Only return True for page2.md when in forced set
        def should_bypass(path, changed_sources=None):
            return changed_sources and path in changed_sources

        mock_cache.should_bypass.side_effect = should_bypass

        change_set = detector.detect_changes(
            "early",
            verbose=True,
            forced_changed_sources={forced_path},
        )

        assert len(change_set.pages_to_build) == 1
        assert change_set.pages_to_build[0].source_path == forced_path


class TestChangeDetectorPhases:
    """Test phase-specific behavior."""

    def test_early_phase_tracks_taxonomy(self, detector, mock_cache, mock_tracker, mock_site):
        """Test that early phase tracks taxonomy for changed pages with tags."""

        # page1.md changed (has tags)
        def should_bypass(path, changed_sources=None):
            return str(path).endswith("page1.md")

        mock_cache.should_bypass.side_effect = should_bypass

        detector.detect_changes("early")

        # Should track taxonomy for the page with tags
        mock_tracker.track_taxonomy.assert_called()

    def test_full_phase_detection(self, detector, mock_cache, mock_site):
        """Test full phase detection includes all changes."""
        # All pages changed
        mock_cache.should_bypass.return_value = True
        mock_cache.get_previous_tags.return_value = set()

        change_set = detector.detect_changes("full")

        # Should include all non-generated pages
        assert len(change_set.pages_to_build) == 2


class TestChangeDetectorAssets:
    """Test asset change detection."""

    def test_detect_asset_changes(self, detector, mock_cache, mock_site):
        """Test detection of changed assets."""
        # Add an asset
        asset = Mock()
        asset.source_path = mock_site.root_path / "assets/style.css"
        mock_site.assets = [asset]

        # Asset changed
        def should_bypass(path, changed_sources=None):
            return str(path).endswith(".css")

        mock_cache.should_bypass.side_effect = should_bypass

        change_set = detector.detect_changes("early", verbose=True)

        assert len(change_set.assets_to_process) == 1
        assert len(change_set.change_summary.modified_assets) == 1


class TestChangeDetectorTemplates:
    """Test template change detection."""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_detect_template_changes(
        self, mock_rglob, mock_exists, detector, mock_cache, mock_site
    ):
        """Test detection of changed templates."""
        mock_site.theme = "default"

        mock_exists.return_value = True
        template_file = Path("/fake/theme/templates/page.html")
        mock_rglob.return_value = [template_file]

        # Template changed
        def is_changed(path):
            return str(path).endswith(".html")

        mock_cache.is_changed.side_effect = is_changed
        mock_cache.should_bypass.return_value = False
        mock_cache.get_affected_pages.return_value = [str(mock_site.pages[0].source_path)]

        # Patch _get_theme_templates_dir
        with patch.object(
            detector, "_get_theme_templates_dir", return_value=Path("/fake/theme/templates")
        ):
            change_set = detector.detect_changes("early", verbose=True)

        # Page affected by template change should be included
        assert len(change_set.pages_to_build) == 1
        assert len(change_set.change_summary.modified_templates) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
