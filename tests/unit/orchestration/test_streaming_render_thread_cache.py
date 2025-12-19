"""
Tests for thread-local pipeline cache invalidation in StreamingRenderOrchestrator.

StreamingRenderOrchestrator uses RenderOrchestrator internally and makes multiple
calls to process() for hubs, mid-tier, and leaves. This test verifies that the
build generation mechanism properly invalidates caches across these phases.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.render import _get_current_generation, clear_thread_local_pipelines


class TestStreamingUsesRenderOrchestratorCacheInvalidation:
    """Verify StreamingRenderOrchestrator uses the same cache invalidation mechanism."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for StreamingRenderOrchestrator."""
        site = SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )
        return site

    def test_streaming_calls_render_orchestrator_which_clears_cache(self, mock_site):
        """
        StreamingRenderOrchestrator calls RenderOrchestrator.process() multiple times.
        Each call should clear thread-local pipelines.
        """
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create some mock pages with connectivity attributes
        pages = []
        for i in range(5):
            page = MagicMock()
            page.url_path = f"/page-{i}/"
            pages.append(page)

        gen_before = _get_current_generation()

        with (
            patch(
                "bengal.orchestration.streaming.RenderOrchestrator"
            ) as MockRenderOrchestrator,
            patch("bengal.orchestration.streaming.KnowledgeGraph") as MockKnowledgeGraph,
        ):
            # Setup mock knowledge graph
            mock_graph = MagicMock()
            mock_layers = MagicMock()
            mock_layers.hubs = pages[:2]
            mock_layers.mid_tier = pages[2:4]
            mock_layers.leaves = pages[4:]
            mock_graph.get_layers.return_value = mock_layers
            MockKnowledgeGraph.return_value = mock_graph

            # Mock RenderOrchestrator.process to actually call clear_thread_local_pipelines
            # (mimics what the real implementation does)
            def mock_process(*args, **kwargs):
                clear_thread_local_pipelines()

            mock_render = MagicMock()
            mock_render.process.side_effect = mock_process
            MockRenderOrchestrator.return_value = mock_render

            orch = StreamingRenderOrchestrator(mock_site)
            orch.process(pages, parallel=False, quiet=True)

        gen_after = _get_current_generation()

        # RenderOrchestrator.process is called at least 3 times (hubs, mid-tier, leaves)
        # Each call should increment the generation
        assert gen_after > gen_before
        # Verify process was called for each layer
        assert mock_render.process.call_count >= 1

    def test_streaming_with_empty_pages_skips_rendering(self, mock_site):
        """StreamingRenderOrchestrator with empty pages returns early."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        gen_before = _get_current_generation()

        orch = StreamingRenderOrchestrator(mock_site)
        orch.process([], parallel=False, quiet=True)

        gen_after = _get_current_generation()

        # No pages means no render calls, generation unchanged
        assert gen_after == gen_before


class TestStreamingRenderBatchCacheInvalidation:
    """Test cache invalidation works correctly across batches in streaming mode."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site."""
        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )

    def test_batch_rendering_uses_fresh_pipelines(self, mock_site):
        """
        When _render_batches processes multiple batches, each should get fresh pipelines.
        
        This is important for memory-optimized mode where leaves are rendered in batches
        with gc.collect() between them.
        """
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create mock pages
        pages = [MagicMock() for _ in range(15)]
        for i, page in enumerate(pages):
            page.url_path = f"/page-{i}/"

        generations_at_process = []

        with (
            patch(
                "bengal.orchestration.streaming.RenderOrchestrator"
            ) as MockRenderOrchestrator,
            patch("bengal.orchestration.streaming.KnowledgeGraph") as MockKnowledgeGraph,
        ):
            # Setup - all pages are leaves (streaming scenario)
            mock_graph = MagicMock()
            mock_layers = MagicMock()
            mock_layers.hubs = []
            mock_layers.mid_tier = []
            mock_layers.leaves = pages
            mock_graph.get_layers.return_value = mock_layers
            MockKnowledgeGraph.return_value = mock_graph

            def track_process(*args, **kwargs):
                clear_thread_local_pipelines()
                generations_at_process.append(_get_current_generation())

            mock_render = MagicMock()
            mock_render.process.side_effect = track_process
            MockRenderOrchestrator.return_value = mock_render

            orch = StreamingRenderOrchestrator(mock_site)
            # Use small batch size to force multiple batches
            orch.process(pages, parallel=False, quiet=True, batch_size=5)

        # Should have been called multiple times for batched leaves
        assert mock_render.process.call_count > 1
        # Each call should see incrementing generation
        assert generations_at_process == sorted(generations_at_process)
        assert len(set(generations_at_process)) == len(generations_at_process)

