"""
Tests for RenderOrchestrator including performance optimizations.

Note: Parallel/sequential decision is now made at the BuildOrchestrator level
via should_parallelize(). The RenderOrchestrator.process() method directly
uses the parallel parameter passed to it without additional threshold logic.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.core.page import Page
from bengal.orchestration.render import RenderOrchestrator


@pytest.fixture
def mock_site():
    """Create a mock site."""
    site = Mock()
    site.root_path = Path("/fake/site")
    site.output_dir = Path("/fake/site/public")
    site.config = {}
    site.pages = []
    site.data = Mock()
    site.data.tracks = {}
    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create a RenderOrchestrator instance."""
    return RenderOrchestrator(mock_site)


class TestParallelRendering:
    """Test suite for parallel rendering behavior."""

    def test_sequential_when_parallel_false(self, orchestrator, mock_site):
        """Test that parallel=False uses sequential rendering."""
        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={})
        ]

        with (
            patch.object(orchestrator, "_render_sequential") as mock_seq,
            patch.object(orchestrator, "_render_parallel") as mock_par,
            patch.object(orchestrator, "_set_output_paths_for_pages"),
        ):
            orchestrator.process(pages, parallel=False)

            # Should use sequential when parallel=False
            mock_seq.assert_called_once()
            mock_par.assert_not_called()

    def test_parallel_when_parallel_true(self, orchestrator, mock_site):
        """Test that parallel=True uses parallel rendering."""
        pages = [
            Page(
                source_path=Path(f"/fake/site/content/page{i}.md"),
                _raw_content="",
                _raw_metadata={},
            )
            for i in range(5)
        ]

        with (
            patch.object(orchestrator, "_render_sequential") as mock_seq,
            patch.object(orchestrator, "_render_parallel") as mock_par,
            patch.object(orchestrator, "_set_output_paths_for_pages"),
        ):
            orchestrator.process(pages, parallel=True)

            # Should use parallel when parallel=True
            mock_par.assert_called_once()
            mock_seq.assert_not_called()

    def test_parallel_true_with_few_pages(self, orchestrator, mock_site):
        """Test that parallel=True still uses parallel even with few pages.

        Note: The threshold logic for deciding parallel vs sequential based on
        page count is now at the BuildOrchestrator level (should_parallelize).
        RenderOrchestrator directly respects the parallel parameter.
        """
        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={})
        ]

        with (
            patch.object(orchestrator, "_render_sequential") as mock_seq,
            patch.object(orchestrator, "_render_parallel") as mock_par,
            patch.object(orchestrator, "_set_output_paths_for_pages"),
        ):
            orchestrator.process(pages, parallel=True)

            # With parallel=True, uses parallel rendering regardless of page count
            mock_par.assert_called_once()
            mock_seq.assert_not_called()


class TestOutputPathOptimization:
    """Test suite for output path setting optimization."""

    def test_set_output_paths_for_pages(self, orchestrator, mock_site):
        """Test that output paths are set only for specified pages."""
        pages = [
            Page(
                source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={}
            ),
            Page(
                source_path=Path("/fake/site/content/page2.md"), _raw_content="", _raw_metadata={}
            ),
        ]

        # Pages start with no output_path
        assert pages[0].output_path is None
        assert pages[1].output_path is None

        # Call the method
        orchestrator._set_output_paths_for_pages(pages)

        # Now pages should have output paths
        assert pages[0].output_path is not None
        assert pages[1].output_path is not None

    def test_set_output_paths_skips_existing(self, orchestrator, mock_site):
        """Test that pages with existing output_path are skipped."""
        existing_path = Path("/fake/existing/output.html")
        pages = [
            Page(
                source_path=Path("/fake/site/content/page1.md"),
                _raw_content="",
                _raw_metadata={},
                output_path=existing_path,
            ),
        ]

        orchestrator._set_output_paths_for_pages(pages)

        # Should not change existing path
        assert pages[0].output_path == existing_path

    def test_set_output_paths_for_subset(self, orchestrator, mock_site):
        """Test that only specified pages get paths, not all site pages."""
        # Add some pages to the site
        mock_site.pages = [
            Page(
                source_path=Path(f"/fake/site/content/page{i}.md"),
                _raw_content="",
                _raw_metadata={},
            )
            for i in range(10)
        ]

        # But only set paths for 2 pages
        pages_to_set = mock_site.pages[:2]
        orchestrator._set_output_paths_for_pages(pages_to_set)

        # Only the first 2 should have paths
        assert mock_site.pages[0].output_path is not None
        assert mock_site.pages[1].output_path is not None
        assert mock_site.pages[2].output_path is None
        assert mock_site.pages[9].output_path is None

    def test_output_path_computation(self, orchestrator, mock_site):
        """Test that output paths are computed correctly."""
        page = Page(
            source_path=Path("/fake/site/content/blog/post.md"), _raw_content="", _raw_metadata={}
        )

        orchestrator._set_output_paths_for_pages([page])

        # Should create pretty URL
        assert page.output_path is not None
        assert page.output_path.name == "index.html"
        assert "post" in str(page.output_path)

    def test_output_path_for_index_file(self, orchestrator, mock_site):
        """Test output path for _index.md files."""
        page = Page(
            source_path=Path("/fake/site/content/blog/_index.md"), _raw_content="", _raw_metadata={}
        )

        orchestrator._set_output_paths_for_pages([page])

        # _index.md should become index.html in the same directory
        assert page.output_path is not None
        assert page.output_path.name == "index.html"
        assert "blog" in str(page.output_path)


class TestProcessMethod:
    """Test the main process method."""

    def test_process_calls_set_output_paths(self, orchestrator, mock_site):
        """Test that process() calls _set_output_paths_for_pages."""
        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={})
        ]

        with patch.object(orchestrator, "_set_output_paths_for_pages") as mock_set:
            with patch.object(orchestrator, "_render_sequential"):
                orchestrator.process(pages, parallel=False)

            # Should call _set_output_paths_for_pages with the pages
            mock_set.assert_called_once_with(pages)

    def test_process_passes_stats_to_parallel(self, orchestrator, mock_site):
        """Test that process passes stats to parallel rendering."""
        pages = [
            Page(
                source_path=Path(f"/fake/site/content/page{i}.md"),
                _raw_content="",
                _raw_metadata={},
            )
            for i in range(5)
        ]
        mock_stats = Mock()

        with patch.object(orchestrator, "_set_output_paths_for_pages"):
            with patch.object(orchestrator, "_render_parallel") as mock_par:
                orchestrator.process(pages, parallel=True, stats=mock_stats)

            # Should pass stats (pages=0, quiet=1, stats=2)
            call_args = mock_par.call_args[0]
            assert call_args[2] == mock_stats


class TestTrackDependencyOrdering:
    """Test track dependency ordering for render performance."""

    def test_track_items_ordered_before_track_pages(self, orchestrator, mock_site):
        """Track items are rendered before track pages that embed them."""
        mock_site.data = Mock()
        mock_site.data.tracks = {
            "getting-started": {
                "title": "Getting Started",
                "items": ["docs/getting-started/page1.md", "docs/getting-started/page2.md"],
            },
        }
        mock_site.config = {"build": {"track_dependency_ordering": True}}

        track_item = Page(
            source_path=Path("/fake/site/content/docs/getting-started/page1.md"),
            _raw_content="",
            _raw_metadata={},
        )
        track_page = Page(
            source_path=Path("/fake/site/content/tracks/getting-started.md"),
            _raw_content="",
            _raw_metadata={"template": "tracks/single.html", "track_id": "getting-started"},
        )
        other_page = Page(
            source_path=Path("/fake/site/content/blog/post.md"),
            _raw_content="",
            _raw_metadata={},
        )

        pages = [track_page, other_page, track_item]
        result = orchestrator._track_dependency_sort(pages)

        assert result[0] == track_item
        assert result[1] == track_page
        assert result[2] == other_page

    def test_site_without_tracks_pages_unchanged(self, orchestrator, mock_site):
        """Site without tracks or with empty tracks returns pages unchanged."""
        mock_site.data = Mock()
        mock_site.data.tracks = {}
        mock_site.config = {"build": {"track_dependency_ordering": True}}

        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={}),
        ]
        result = orchestrator._track_dependency_sort(pages)

        assert result == pages

    def test_site_without_tracks_data_pages_unchanged(self, orchestrator, mock_site):
        """Site without site.data.tracks returns pages unchanged."""
        mock_site.data = Mock()
        mock_site.data.tracks = None
        mock_site.config = {"build": {"track_dependency_ordering": True}}

        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), _raw_content="", _raw_metadata={}),
        ]
        result = orchestrator._track_dependency_sort(pages)

        assert result == pages

    def test_track_item_in_multiple_tracks_ordered_first(self, orchestrator, mock_site):
        """Page that appears in multiple tracks is still ordered as track item."""
        mock_site.data = Mock()
        mock_site.data.tracks = {
            "track-a": {"items": ["docs/shared.md"]},
            "track-b": {"items": ["docs/shared.md"]},
        }
        mock_site.config = {"build": {"track_dependency_ordering": True}}

        shared_page = Page(
            source_path=Path("/fake/site/content/docs/shared.md"),
            _raw_content="",
            _raw_metadata={},
        )
        track_page = Page(
            source_path=Path("/fake/site/content/tracks/track-a.md"),
            _raw_content="",
            _raw_metadata={"template": "tracks/single.html", "track_id": "track-a"},
        )

        pages = [track_page, shared_page]
        result = orchestrator._track_dependency_sort(pages)

        assert result[0] == shared_page
        assert result[1] == track_page

    def test_page_both_track_item_and_track_page_ordered_as_item(self, orchestrator, mock_site):
        """Page that is both track item and track page is ordered as track item."""
        mock_site.data = Mock()
        mock_site.data.tracks = {
            "main": {"items": ["docs/landing.md"]},
        }
        mock_site.config = {"build": {"track_dependency_ordering": True}}

        landing = Page(
            source_path=Path("/fake/site/content/docs/landing.md"),
            _raw_content="",
            _raw_metadata={"template": "tracks/single.html", "track_id": "main"},
        )
        other = Page(
            source_path=Path("/fake/site/content/blog/post.md"),
            _raw_content="",
            _raw_metadata={},
        )

        pages = [other, landing]
        result = orchestrator._track_dependency_sort(pages)

        assert result[0] == landing
        assert result[1] == other

    def test_track_dependency_ordering_disabled_config(self, orchestrator, mock_site):
        """When track_dependency_ordering is False, pages are unchanged."""
        mock_site.data = Mock()
        mock_site.data.tracks = {
            "getting-started": {"items": ["docs/page1.md"]},
        }
        mock_site.config = {"build": {"track_dependency_ordering": False}}

        track_item = Page(
            source_path=Path("/fake/site/content/docs/page1.md"),
            _raw_content="",
            _raw_metadata={},
        )
        track_page = Page(
            source_path=Path("/fake/site/content/tracks/getting-started.md"),
            _raw_content="",
            _raw_metadata={"template": "tracks/single.html"},
        )

        pages = [track_page, track_item]
        result = orchestrator._track_dependency_sort(pages)

        assert result == pages

    def test_maybe_sort_preserves_track_order_within_complexity(self, orchestrator, mock_site):
        """_maybe_sort_by_complexity preserves track_items before track_pages when both enabled."""
        mock_site.data = Mock()
        mock_site.data.tracks = {
            "getting-started": {"items": ["docs/page1.md", "docs/page2.md"]},
        }
        mock_site.config = {"build": {"track_dependency_ordering": True, "complexity_ordering": True}}

        # Track page (light), track item (heavy), other - complexity sort would put heavy first
        track_page = Page(
            source_path=Path("/fake/site/content/tracks/getting-started.md"),
            _raw_content="short",
            _raw_metadata={"template": "tracks/single.html", "track_id": "getting-started"},
        )
        track_item = Page(
            source_path=Path("/fake/site/content/docs/page1.md"),
            _raw_content="x" * 10000,  # Heavier content
            _raw_metadata={},
        )
        other = Page(
            source_path=Path("/fake/site/content/blog/post.md"),
            _raw_content="medium",
            _raw_metadata={},
        )

        pages = [track_page, track_item, other]
        result = orchestrator._maybe_sort_by_complexity(pages, max_workers=2)

        # Track item must come before track page (dependency order preserved)
        track_item_idx = result.index(track_item)
        track_page_idx = result.index(track_page)
        assert track_item_idx < track_page_idx


class TestPerformanceOptimization:
    """Test that optimizations improve performance."""

    def test_output_path_optimization_reduces_iteration(self, orchestrator, mock_site):
        """Test that path setting only processes needed pages."""
        # Add 100 pages to site
        mock_site.pages = [
            Page(
                source_path=Path(f"/fake/site/content/page{i}.md"),
                _raw_content="",
                _raw_metadata={},
            )
            for i in range(100)
        ]

        # But only render 5 pages
        pages_to_render = mock_site.pages[:5]

        # Call _set_output_paths_for_pages
        orchestrator._set_output_paths_for_pages(pages_to_render)

        # Only 5 pages should have paths, not all 100
        paths_set = sum(1 for p in mock_site.pages if p.output_path is not None)
        assert paths_set == 5  # Only the pages we processed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
