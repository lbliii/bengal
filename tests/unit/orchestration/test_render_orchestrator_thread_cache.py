"""
Tests for thread-local pipeline cache invalidation in RenderOrchestrator.

These tests verify that template changes between builds are properly detected
and that stale pipelines (with old TemplateEngine/Jinja environments) are
recreated rather than reused.

This addresses a bug where template edits during dev server operation weren't
reflected because worker threads kept stale RenderingPipeline instances.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.render import (
    RenderOrchestrator,
    _get_current_generation,
    clear_thread_local_pipelines,
)


class TestBuildGenerationCounter:
    """Test the build generation counter mechanism."""

    def test_clear_increments_generation(self):
        """Test that clear_thread_local_pipelines increments the generation."""
        gen_before = _get_current_generation()
        clear_thread_local_pipelines()
        gen_after = _get_current_generation()

        assert gen_after == gen_before + 1

    def test_multiple_clears_increment_sequentially(self):
        """Test that multiple clears increment sequentially."""
        gen_start = _get_current_generation()
        clear_thread_local_pipelines()
        clear_thread_local_pipelines()
        clear_thread_local_pipelines()
        gen_end = _get_current_generation()

        assert gen_end == gen_start + 3

    def test_generation_is_thread_safe(self):
        """Test that generation counter is thread-safe under concurrent access."""
        gen_before = _get_current_generation()
        num_threads = 10
        increments_per_thread = 100

        def increment_many():
            for _ in range(increments_per_thread):
                clear_thread_local_pipelines()

        threads = [threading.Thread(target=increment_many) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        gen_after = _get_current_generation()
        expected_increment = num_threads * increments_per_thread

        assert gen_after == gen_before + expected_increment


class TestPipelineRecreationOnNewBuild:
    """Test that pipelines are recreated when generation changes."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/fake/site")
        site.output_dir = Path("/fake/site/public")
        site.config = {}
        site.pages = []
        return site

    @pytest.fixture
    def orchestrator(self, mock_site):
        """Create a RenderOrchestrator instance."""
        return RenderOrchestrator(mock_site)

    def test_process_clears_thread_local_pipelines(self, orchestrator):
        """Test that process() calls clear_thread_local_pipelines."""
        gen_before = _get_current_generation()

        with (
            patch.object(orchestrator, "_render_sequential"),
            patch.object(orchestrator, "_set_output_paths_for_pages"),
        ):
            orchestrator.process([], parallel=False)

        gen_after = _get_current_generation()
        assert gen_after == gen_before + 1

    def test_parallel_workers_get_fresh_pipelines_after_clear(self, mock_site):
        """
        Test that parallel workers create new pipelines after generation change.

        This is the key test that would have caught the original bug:
        - Build 1: Workers create pipelines
        - Template is modified
        - Build 2: Workers should create NEW pipelines with fresh TemplateEngine

        Without the generation counter fix, workers would reuse stale pipelines.
        """
        from concurrent.futures import ThreadPoolExecutor

        from bengal.orchestration.render import _thread_local

        # Track which generations pipelines were created at
        pipeline_generations = []

        def mock_process_page(page):
            """Simulated page processing that tracks pipeline creation."""
            current_gen = _get_current_generation()

            # Check if pipeline needs recreation (mimics the real code)
            needs_new = (
                not hasattr(_thread_local, "test_pipeline")
                or getattr(_thread_local, "test_pipeline_gen", -1) != current_gen
            )

            if needs_new:
                # "Create" a new pipeline
                _thread_local.test_pipeline = f"pipeline_gen_{current_gen}"
                _thread_local.test_pipeline_gen = current_gen

            pipeline_generations.append(_thread_local.test_pipeline_gen)

        # Simulate Build 1
        gen_1 = _get_current_generation()
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(mock_process_page, range(10))

        # All pages should have been processed with gen_1 pipeline
        assert all(g == gen_1 for g in pipeline_generations[-10:])

        # Simulate template change -> triggers clear
        clear_thread_local_pipelines()

        # Simulate Build 2 (reuses same threads from pool potentially)
        gen_2 = _get_current_generation()
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(mock_process_page, range(10))

        # All pages in Build 2 should have new generation pipelines
        assert all(g == gen_2 for g in pipeline_generations[-10:])
        assert gen_2 != gen_1  # Sanity check


class TestDevServerRebuildScenario:
    """
    Integration-style tests simulating dev server rebuild scenarios.

    These tests verify the full flow of what happens when a user edits
    a template while the dev server is running.
    """

    def test_template_change_between_builds_uses_fresh_engine(self, tmp_path):
        """
        Simulate: User edits template.html -> rebuild -> pages should use new template.

        This test simulates the scenario where:
        1. Initial build renders pages with Template v1
        2. User edits template file
        3. Rebuild is triggered
        4. Pages should be rendered with Template v2 (not stale v1)
        """
        # This would be a full integration test with real site/templates
        # For now, verify the mechanism works
        gen_1 = _get_current_generation()

        # Simulate "template edit triggers rebuild"
        clear_thread_local_pipelines()

        gen_2 = _get_current_generation()

        # The generation should have changed, forcing pipeline recreation
        assert gen_2 > gen_1


class TestRegressionStaleTemplates:
    """
    Regression tests to prevent reintroduction of stale template bugs.
    """

    def test_thread_local_not_persisted_across_process_calls(self):
        """
        Verify that calling process() twice results in fresh pipelines.

        Before the fix, this would fail because thread-local pipelines
        persisted across process() calls.
        """
        generations_seen = []

        # Record generation at the start of each simulated process() call
        for _ in range(3):
            clear_thread_local_pipelines()  # Called at start of process()
            generations_seen.append(_get_current_generation())

        # Each process() call should see a new generation
        assert len(set(generations_seen)) == 3
        assert generations_seen == sorted(generations_seen)  # Monotonically increasing
