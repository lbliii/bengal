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
def mock_site(tmp_path):
    """Create a mock site with pages and assets."""
    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"

    # Create a proper config mock with path attribute
    mock_config = Mock()
    mock_config.path = tmp_path / "bengal.toml"
    site.config = mock_config

    # Create some mock pages
    site.pages = [
        Page(
            source_path=tmp_path / "content/page1.md",
            content="Content 1",
            metadata={"title": "Page 1", "tags": ["python", "testing"]},
        ),
        Page(
            source_path=tmp_path / "content/page2.md",
            content="Content 2",
            metadata={"title": "Page 2", "tags": ["python"]},
        ),
        Page(
            source_path=tmp_path / "content/_generated/tags.md",
            content="",
            metadata={"title": "Tags", "_generated": True, "type": "tag-index"},
        ),
    ]

    # Create some mock assets
    site.assets = [
        Mock(source_path=tmp_path / "assets/style.css"),
        Mock(source_path=tmp_path / "assets/script.js"),
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

        # Should load existing cache from .bengal/cache.json
        cache_path = mock_site.root_path / ".bengal" / "cache.json"
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
        orchestrator.cache.file_hashes = {}  # Add file_hashes attribute

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


class TestCascadeDependencyTracking:
    """Test suite for cascade dependency tracking in incremental builds."""

    def test_cascade_change_marks_descendants_for_rebuild(self, orchestrator, mock_site):
        """When section _index.md with cascade changes, mark all descendants."""
        # Setup - Create a section with an index page that has cascade
        from bengal.core.section import Section

        section = Section(name="docs", path=Path("/fake/site/content/docs"))

        # Create section index with cascade
        index_page = Page(
            source_path=Path("/fake/site/content/docs/_index.md"),
            content="Section index",
            metadata={"title": "Docs", "cascade": {"type": "doc", "layout": "doc-page"}},
        )
        section.index_page = index_page
        section.pages.append(index_page)

        # Create child pages
        child1 = Page(
            source_path=Path("/fake/site/content/docs/page1.md"),
            content="Child 1",
            metadata={"title": "Page 1"},
        )
        child2 = Page(
            source_path=Path("/fake/site/content/docs/page2.md"),
            content="Child 2",
            metadata={"title": "Page 2"},
        )
        section.pages.extend([child1, child2])

        # Update mock site
        mock_site.pages = [index_page, child1, child2]
        mock_site.sections = [section]

        # Setup cache - only _index.md changed
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        def is_changed(path):
            return str(path).endswith("_index.md")

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, change_summary = orchestrator.find_work_early(verbose=True)

        # Should rebuild all 3 pages: _index.md + 2 children
        assert len(pages_to_build) == 3
        assert index_page in pages_to_build
        assert child1 in pages_to_build
        assert child2 in pages_to_build

        # Should have cascade change info
        assert "Cascade changes" in change_summary
        assert len(change_summary["Cascade changes"]) > 0

    def test_cascade_change_in_nested_section(self, orchestrator, mock_site):
        """When nested section cascade changes, mark only its descendants."""
        from bengal.core.section import Section

        # Create parent section
        parent_section = Section(name="docs", path=Path("/fake/site/content/docs"))
        parent_index = Page(
            source_path=Path("/fake/site/content/docs/_index.md"),
            content="Parent",
            metadata={"title": "Docs"},
        )
        parent_section.index_page = parent_index
        parent_section.pages.append(parent_index)

        # Create child section with cascade
        child_section = Section(name="advanced", path=Path("/fake/site/content/docs/advanced"))
        child_section.parent = parent_section
        child_index = Page(
            source_path=Path("/fake/site/content/docs/advanced/_index.md"),
            content="Child section",
            metadata={"title": "Advanced", "cascade": {"difficulty": "hard"}},
        )
        child_section.index_page = child_index
        child_section.pages.append(child_index)

        # Add pages to child section
        nested_page = Page(
            source_path=Path("/fake/site/content/docs/advanced/guide.md"),
            content="Guide",
            metadata={"title": "Guide"},
        )
        child_section.pages.append(nested_page)

        # Add page to parent section (should NOT be affected)
        parent_page = Page(
            source_path=Path("/fake/site/content/docs/intro.md"),
            content="Intro",
            metadata={"title": "Intro"},
        )
        parent_section.pages.append(parent_page)
        parent_section.subsections.append(child_section)

        # Update mock site
        mock_site.pages = [parent_index, parent_page, child_index, nested_page]
        mock_site.sections = [parent_section, child_section]

        # Setup cache - only child _index.md changed
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        def is_changed(path):
            return "advanced/_index.md" in str(path)

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, _ = orchestrator.find_work_early()

        # Should rebuild child section pages only, not parent section pages
        assert child_index in pages_to_build
        assert nested_page in pages_to_build
        assert parent_page not in pages_to_build
        assert parent_index not in pages_to_build

    def test_root_level_cascade_marks_all_pages(self, orchestrator, mock_site):
        """When top-level page with cascade changes, mark all pages."""
        # Create a root-level index page with cascade
        root_index = Page(
            source_path=Path("/fake/site/content/index.md"),
            content="Root",
            metadata={"title": "Home", "cascade": {"site_wide": "value"}},
        )

        # Create other pages
        page1 = Page(
            source_path=Path("/fake/site/content/page1.md"),
            content="Page 1",
            metadata={"title": "Page 1"},
        )
        page2 = Page(
            source_path=Path("/fake/site/content/page2.md"),
            content="Page 2",
            metadata={"title": "Page 2"},
        )

        # Update mock site - no sections (root level)
        mock_site.pages = [root_index, page1, page2]
        mock_site.sections = []

        # Setup cache - only root index changed
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        def is_changed(path):
            return "content/index.md" in str(path)

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, _ = orchestrator.find_work_early()

        # Should rebuild ALL pages due to root-level cascade
        assert len(pages_to_build) == 3
        assert root_index in pages_to_build
        assert page1 in pages_to_build
        assert page2 in pages_to_build

    def test_no_cascade_no_extra_rebuilds(self, orchestrator, mock_site):
        """When _index.md without cascade changes, don't mark descendants."""
        from bengal.core.section import Section

        section = Section(name="blog", path=Path("/fake/site/content/blog"))

        # Create section index WITHOUT cascade
        index_page = Page(
            source_path=Path("/fake/site/content/blog/_index.md"),
            content="Blog index",
            metadata={"title": "Blog"},  # No cascade!
        )
        section.index_page = index_page
        section.pages.append(index_page)

        # Create child page
        child = Page(
            source_path=Path("/fake/site/content/blog/post.md"),
            content="Post",
            metadata={"title": "Post"},
        )
        section.pages.append(child)

        # Update mock site
        mock_site.pages = [index_page, child]
        mock_site.sections = [section]

        # Setup cache - only _index.md changed
        orchestrator.cache = Mock()
        orchestrator.tracker = Mock()

        def is_changed(path):
            return str(path).endswith("_index.md")

        orchestrator.cache.is_changed.side_effect = is_changed

        # Mock the _get_theme_templates_dir to return None
        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            # Test
            pages_to_build, _, change_summary = orchestrator.find_work_early(verbose=True)

        # Should only rebuild _index.md, not the child (no cascade)
        assert len(pages_to_build) == 1
        assert index_page in pages_to_build
        assert child not in pages_to_build

        # Should NOT have cascade change info
        assert (
            "Cascade changes" not in change_summary or len(change_summary["Cascade changes"]) == 0
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
