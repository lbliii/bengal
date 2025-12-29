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
    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create a RenderOrchestrator instance."""
    return RenderOrchestrator(mock_site)


class TestParallelRendering:
    """Test suite for parallel rendering behavior."""

    def test_sequential_when_parallel_false(self, orchestrator, mock_site):
        """Test that parallel=False uses sequential rendering."""
        pages = [Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})]

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
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
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
        pages = [Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})]

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
            Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={}),
            Page(source_path=Path("/fake/site/content/page2.md"), content="", metadata={}),
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
                content="",
                metadata={},
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
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
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
        page = Page(source_path=Path("/fake/site/content/blog/post.md"), content="", metadata={})

        orchestrator._set_output_paths_for_pages([page])

        # Should create pretty URL
        assert page.output_path is not None
        assert page.output_path.name == "index.html"
        assert "post" in str(page.output_path)

    def test_output_path_for_index_file(self, orchestrator, mock_site):
        """Test output path for _index.md files."""
        page = Page(source_path=Path("/fake/site/content/blog/_index.md"), content="", metadata={})

        orchestrator._set_output_paths_for_pages([page])

        # _index.md should become index.html in the same directory
        assert page.output_path is not None
        assert page.output_path.name == "index.html"
        assert "blog" in str(page.output_path)


class TestProcessMethod:
    """Test the main process method."""

    def test_process_calls_set_output_paths(self, orchestrator, mock_site):
        """Test that process() calls _set_output_paths_for_pages."""
        pages = [Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})]

        with patch.object(orchestrator, "_set_output_paths_for_pages") as mock_set:
            with patch.object(orchestrator, "_render_sequential"):
                orchestrator.process(pages, parallel=False)

            # Should call _set_output_paths_for_pages with the pages
            mock_set.assert_called_once_with(pages)

    def test_process_passes_tracker_to_sequential(self, orchestrator, mock_site):
        """Test that process passes tracker to sequential rendering."""
        pages = [Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})]
        mock_tracker = Mock()

        with patch.object(orchestrator, "_set_output_paths_for_pages"):
            with patch.object(orchestrator, "_render_sequential") as mock_seq:
                orchestrator.process(pages, parallel=False, tracker=mock_tracker)

            # Should pass tracker
            call_args = mock_seq.call_args[0]
            assert call_args[1] == mock_tracker

    def test_process_passes_stats_to_parallel(self, orchestrator, mock_site):
        """Test that process passes stats to parallel rendering."""
        pages = [
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
            for i in range(5)
        ]
        mock_stats = Mock()

        with patch.object(orchestrator, "_set_output_paths_for_pages"):
            with patch.object(orchestrator, "_render_parallel") as mock_par:
                orchestrator.process(pages, parallel=True, stats=mock_stats)

            # Should pass stats
            call_args = mock_par.call_args[0]
            assert call_args[3] == mock_stats


class TestPerformanceOptimization:
    """Test that optimizations improve performance."""

    def test_output_path_optimization_reduces_iteration(self, orchestrator, mock_site):
        """Test that path setting only processes needed pages."""
        # Add 100 pages to site
        mock_site.pages = [
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
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
