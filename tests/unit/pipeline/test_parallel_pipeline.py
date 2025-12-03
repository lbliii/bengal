"""
Unit tests for parallel pipeline execution.

Tests:
    - ParallelStream doesn't call map function twice (regression test for double-execution bug)
    - create_simple_pipeline parallel parameter
    - Thread-local pipeline caching
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from bengal.pipeline.core import StreamItem
from bengal.pipeline.streams import MapStream, ParallelStream, SourceStream


class TestParallelStreamNoDoubleExecution:
    """Regression tests for ParallelStream double-execution bug fix."""

    def test_map_function_called_once_per_item(self) -> None:
        """Map function should be called exactly once per item, not twice."""
        call_count = 0

        def counting_fn(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        items = [
            StreamItem.create("in", "1", 1),
            StreamItem.create("in", "2", 2),
            StreamItem.create("in", "3", 3),
        ]
        source = SourceStream(lambda: iter(items), name="in")
        mapped = MapStream(source, counting_fn, name="doubled")
        parallel = ParallelStream(mapped, workers=2)

        result = parallel.materialize()

        # Map function should be called exactly 3 times (once per item)
        # Before the fix, it was called 6 times (twice per item)
        assert call_count == 3, f"Expected 3 calls, got {call_count} (double execution bug?)"
        assert sorted(result) == [2, 4, 6]

    def test_parallel_with_side_effects_counted_correctly(self) -> None:
        """Side effects in map function should only happen once per item."""
        processed_items: list[int] = []

        def tracking_fn(x: int) -> int:
            processed_items.append(x)
            return x * 2

        items = [StreamItem.create("in", str(i), i) for i in range(5)]
        source = SourceStream(lambda: iter(items), name="in")
        mapped = MapStream(source, tracking_fn, name="tracked")
        parallel = ParallelStream(mapped, workers=3)

        parallel.materialize()

        # Each item should be processed exactly once
        assert len(processed_items) == 5, f"Expected 5 items, got {len(processed_items)}"
        assert sorted(processed_items) == [0, 1, 2, 3, 4]


class TestParallelStreamNonMapUpstream:
    """Tests for ParallelStream with non-MapStream upstream."""

    def test_parallel_with_filter_upstream_passes_through(self) -> None:
        """ParallelStream with non-map upstream should pass items through."""
        from bengal.pipeline.streams import FilterStream

        items = [StreamItem.create("in", str(i), i) for i in range(5)]
        source = SourceStream(lambda: iter(items), name="in")
        filtered = FilterStream(source, lambda x: x % 2 == 0, name="evens")
        parallel = ParallelStream(filtered, workers=2)

        result = parallel.materialize()

        # Filter results should pass through
        assert sorted(result) == [0, 2, 4]


class TestCreateSimplePipelineParallel:
    """Tests for create_simple_pipeline parallel functionality."""

    def test_create_simple_pipeline_default_parallel(self) -> None:
        """create_simple_pipeline should enable parallelism by default."""
        from types import SimpleNamespace

        from bengal.pipeline.build import create_simple_pipeline
        from bengal.pipeline.streams import ParallelStream

        # Create minimal mock site
        mock_site = SimpleNamespace(
            pages=[],
            config={"max_workers": 4},
        )

        # Create with 10 mock pages (above threshold)
        mock_pages = [MagicMock() for _ in range(10)]

        with patch("bengal.rendering.pipeline.RenderingPipeline"):
            pipeline = create_simple_pipeline(mock_site, pages=mock_pages, parallel=True)

        # Should have ParallelStream in the chain
        assert isinstance(pipeline._current, ParallelStream), (
            "Pipeline should use ParallelStream when parallel=True and pages >= 5"
        )

    def test_create_simple_pipeline_parallel_disabled(self) -> None:
        """create_simple_pipeline should not parallelize when parallel=False."""
        from types import SimpleNamespace

        from bengal.pipeline.build import create_simple_pipeline
        from bengal.pipeline.streams import ParallelStream

        mock_site = SimpleNamespace(
            pages=[],
            config={"max_workers": 4},
        )

        mock_pages = [MagicMock() for _ in range(10)]

        with patch("bengal.rendering.pipeline.RenderingPipeline"):
            pipeline = create_simple_pipeline(mock_site, pages=mock_pages, parallel=False)

        # Should NOT have ParallelStream
        assert not isinstance(pipeline._current, ParallelStream), (
            "Pipeline should not use ParallelStream when parallel=False"
        )

    def test_create_simple_pipeline_below_threshold_no_parallel(self) -> None:
        """create_simple_pipeline should not parallelize for < 5 pages."""
        from types import SimpleNamespace

        from bengal.pipeline.build import create_simple_pipeline
        from bengal.pipeline.streams import ParallelStream

        mock_site = SimpleNamespace(
            pages=[],
            config={"max_workers": 4},
        )

        # Only 3 pages - below threshold
        mock_pages = [MagicMock() for _ in range(3)]

        with patch("bengal.rendering.pipeline.RenderingPipeline"):
            pipeline = create_simple_pipeline(mock_site, pages=mock_pages, parallel=True)

        # Should NOT parallelize for small page counts
        assert not isinstance(pipeline._current, ParallelStream), (
            "Pipeline should not parallelize for < 5 pages"
        )

    def test_create_simple_pipeline_custom_workers(self) -> None:
        """create_simple_pipeline should respect custom worker count."""
        from types import SimpleNamespace

        from bengal.pipeline.build import create_simple_pipeline
        from bengal.pipeline.streams import ParallelStream

        mock_site = SimpleNamespace(
            pages=[],
            config={"max_workers": 2},  # Config says 2
        )

        mock_pages = [MagicMock() for _ in range(10)]

        with patch("bengal.rendering.pipeline.RenderingPipeline"):
            pipeline = create_simple_pipeline(
                mock_site,
                pages=mock_pages,
                parallel=True,
                workers=8,  # Override to 8
            )

        # Check the ParallelStream has 8 workers
        assert isinstance(pipeline._current, ParallelStream)
        assert pipeline._current._workers == 8


class TestThreadLocalPipelineCaching:
    """Tests for thread-local RenderingPipeline caching in create_simple_pipeline."""

    def test_thread_local_pipeline_reused_within_thread(self) -> None:
        """RenderingPipeline should be reused within the same thread."""
        from types import SimpleNamespace

        from bengal.pipeline.build import create_simple_pipeline

        mock_site = SimpleNamespace(
            pages=[],
            config={"max_workers": 4},
        )

        # Track RenderingPipeline instantiations
        pipeline_instances: list[MagicMock] = []

        def mock_pipeline_init(*args, **kwargs):
            instance = MagicMock()
            pipeline_instances.append(instance)
            return instance

        mock_pages = [MagicMock() for _ in range(3)]
        for i, page in enumerate(mock_pages):
            page.url = f"/page{i}/"
            page.rendered_html = f"<html>{i}</html>"

        with patch("bengal.rendering.pipeline.RenderingPipeline", side_effect=mock_pipeline_init):
            pipeline = create_simple_pipeline(
                mock_site,
                pages=mock_pages,
                parallel=False,  # Sequential to test single thread
            )
            pipeline.run()

        # Should only create ONE pipeline instance (reused via thread-local)
        assert len(pipeline_instances) == 1, (
            f"Expected 1 pipeline instance (thread-local reuse), got {len(pipeline_instances)}"
        )

    def test_multiple_threads_get_separate_pipelines(self) -> None:
        """Each thread should get its own RenderingPipeline instance."""

        thread_ids: set[int] = set()
        call_count = 0
        lock = threading.Lock()

        def track_thread_local():
            """Track which threads are calling the function."""
            nonlocal call_count
            with lock:
                thread_ids.add(threading.get_ident())
                call_count += 1

        # Create items for parallel processing
        items = [StreamItem.create("in", str(i), i) for i in range(10)]
        source = SourceStream(lambda: iter(items), name="in")

        def map_fn(x: int) -> int:
            track_thread_local()
            return x * 2

        mapped = MapStream(source, map_fn, name="doubled")
        parallel = ParallelStream(mapped, workers=4)

        parallel.materialize()

        # Verify all items were processed
        assert call_count == 10, f"Expected 10 calls, got {call_count}"

        # Verify multiple threads were used (with 4 workers and 10 items, expect >1 thread)
        assert len(thread_ids) > 1, (
            f"Expected multiple threads to be used with 4 workers, "
            f"but only {len(thread_ids)} thread(s) were used: {thread_ids}"
        )
