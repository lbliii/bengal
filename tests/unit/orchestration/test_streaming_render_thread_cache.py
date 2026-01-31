"""
Tests for thread-local pipeline cache invalidation in StreamingRenderOrchestrator.

StreamingRenderOrchestrator uses RenderOrchestrator internally and makes multiple
calls to process() for hubs, mid-tier, and leaves. This test verifies that the
build generation mechanism properly invalidates caches across these phases.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.render import get_current_generation, clear_thread_local_pipelines


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

    def test_streaming_with_empty_pages_skips_rendering(self, mock_site):
        """StreamingRenderOrchestrator with empty pages returns early."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        gen_before = get_current_generation()

        orch = StreamingRenderOrchestrator(mock_site)
        orch.process([], parallel=False, quiet=True)

        gen_after = get_current_generation()

        # No pages means no render calls, generation unchanged
        assert gen_after == gen_before

    def test_render_orchestrator_process_increments_generation(self, tmp_path):
        """
        RenderOrchestrator.process() should increment the build generation.

        This is the core mechanism that StreamingRenderOrchestrator relies on
        when it calls RenderOrchestrator.process() for each batch.
        """
        from bengal.orchestration.render import RenderOrchestrator

        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.config = {}
        site.pages = []

        orch = RenderOrchestrator(site)

        gen_before = get_current_generation()

        # Process with no pages (just to trigger generation increment)
        with patch.object(orch, "_set_output_paths_for_pages"):
            orch.process([], parallel=False, quiet=True)

        gen_after = get_current_generation()

        # Generation should have been incremented
        assert gen_after == gen_before + 1

    def test_multiple_process_calls_increment_generation_each_time(self, tmp_path):
        """
        Each call to RenderOrchestrator.process() should increment generation.

        This is critical for StreamingRenderOrchestrator which calls process()
        multiple times (hubs, mid-tier, leaves).
        """
        from bengal.orchestration.render import RenderOrchestrator

        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.config = {}
        site.pages = []

        orch = RenderOrchestrator(site)

        gen_start = get_current_generation()

        # Simulate 3 process calls (like hub/mid/leaf batches)
        for _ in range(3):
            with patch.object(orch, "_set_output_paths_for_pages"):
                orch.process([], parallel=False, quiet=True)

        gen_end = get_current_generation()

        # Should have incremented 3 times
        assert gen_end == gen_start + 3


class TestBuildGenerationForCacheInvalidation:
    """Test build generation counter is properly used for cache invalidation."""

    def test_clear_thread_local_pipelines_increments_generation(self):
        """Verify clear_thread_local_pipelines increments the build generation."""
        gen_before = get_current_generation()
        clear_thread_local_pipelines()
        gen_after = get_current_generation()

        assert gen_after == gen_before + 1

    def test_generation_monotonically_increases(self):
        """Build generation should always increase, never decrease."""
        generations = []
        for _ in range(5):
            clear_thread_local_pipelines()
            generations.append(get_current_generation())

        # Should be strictly increasing
        for i in range(1, len(generations)):
            assert generations[i] > generations[i - 1]
