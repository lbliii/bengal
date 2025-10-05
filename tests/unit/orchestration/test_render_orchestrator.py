"""
Tests for RenderOrchestrator including performance optimizations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from bengal.orchestration.render import RenderOrchestrator
from bengal.core.page import Page


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


class TestParallelThreshold:
    """Test suite for parallel rendering threshold optimization."""
    
    def test_sequential_for_single_page(self, orchestrator, mock_site):
        """Test that single page uses sequential rendering."""
        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})
        ]
        
        with patch.object(orchestrator, '_render_sequential') as mock_seq:
            with patch.object(orchestrator, '_render_parallel') as mock_par:
                with patch.object(orchestrator, '_set_output_paths_for_pages'):
                    orchestrator.process(pages, parallel=True)
                
                # Should use sequential
                mock_seq.assert_called_once()
                mock_par.assert_not_called()
    
    def test_sequential_for_few_pages(self, orchestrator, mock_site):
        """Test that 2-4 pages use sequential rendering (below threshold)."""
        pages = [
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
            for i in range(4)
        ]
        
        with patch.object(orchestrator, '_render_sequential') as mock_seq:
            with patch.object(orchestrator, '_render_parallel') as mock_par:
                with patch.object(orchestrator, '_set_output_paths_for_pages'):
                    orchestrator.process(pages, parallel=True)
                
                # Should use sequential (below threshold of 5)
                mock_seq.assert_called_once()
                mock_par.assert_not_called()
    
    def test_parallel_for_many_pages(self, orchestrator, mock_site):
        """Test that 5+ pages use parallel rendering (meets threshold)."""
        pages = [
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
            for i in range(5)
        ]
        
        with patch.object(orchestrator, '_render_sequential') as mock_seq:
            with patch.object(orchestrator, '_render_parallel') as mock_par:
                with patch.object(orchestrator, '_set_output_paths_for_pages'):
                    orchestrator.process(pages, parallel=True)
                
                # Should use parallel (meets threshold of 5)
                mock_par.assert_called_once()
                mock_seq.assert_not_called()
    
    def test_parallel_disabled(self, orchestrator, mock_site):
        """Test that parallel=False always uses sequential."""
        pages = [
            Page(source_path=Path(f"/fake/site/content/page{i}.md"), content="", metadata={})
            for i in range(10)
        ]
        
        with patch.object(orchestrator, '_render_sequential') as mock_seq:
            with patch.object(orchestrator, '_render_parallel') as mock_par:
                with patch.object(orchestrator, '_set_output_paths_for_pages'):
                    orchestrator.process(pages, parallel=False)
                
                # Should use sequential even with many pages
                mock_seq.assert_called_once()
                mock_par.assert_not_called()


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
                output_path=existing_path
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
        page = Page(
            source_path=Path("/fake/site/content/blog/post.md"),
            content="",
            metadata={}
        )
        
        orchestrator._set_output_paths_for_pages([page])
        
        # Should create pretty URL
        assert page.output_path is not None
        assert page.output_path.name == "index.html"
        assert "post" in str(page.output_path)
    
    def test_output_path_for_index_file(self, orchestrator, mock_site):
        """Test output path for _index.md files."""
        page = Page(
            source_path=Path("/fake/site/content/blog/_index.md"),
            content="",
            metadata={}
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
            Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})
        ]
        
        with patch.object(orchestrator, '_set_output_paths_for_pages') as mock_set:
            with patch.object(orchestrator, '_render_sequential'):
                orchestrator.process(pages, parallel=False)
            
            # Should call _set_output_paths_for_pages with the pages
            mock_set.assert_called_once_with(pages)
    
    def test_process_passes_tracker_to_sequential(self, orchestrator, mock_site):
        """Test that process passes tracker to sequential rendering."""
        pages = [
            Page(source_path=Path("/fake/site/content/page1.md"), content="", metadata={})
        ]
        mock_tracker = Mock()
        
        with patch.object(orchestrator, '_set_output_paths_for_pages'):
            with patch.object(orchestrator, '_render_sequential') as mock_seq:
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
        
        with patch.object(orchestrator, '_set_output_paths_for_pages'):
            with patch.object(orchestrator, '_render_parallel') as mock_par:
                orchestrator.process(pages, parallel=True, stats=mock_stats)
            
            # Should pass stats
            call_args = mock_par.call_args[0]
            assert call_args[3] == mock_stats


class TestPerformanceOptimization:
    """Test that optimizations improve performance."""
    
    def test_parallel_threshold_reduces_overhead(self, orchestrator):
        """Test that small batches avoid thread pool overhead."""
        # This is more of a documentation test - the actual performance
        # improvement is measured by benchmarks, not unit tests
        
        # With threshold=5, batches of 2-4 pages avoid ThreadPoolExecutor
        # overhead which is ~10-20ms per batch
        
        # Verify the threshold constant
        from bengal.orchestration.render import _thread_local
        # The threshold is in the process() method
        pass  # This test documents the optimization
    
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

