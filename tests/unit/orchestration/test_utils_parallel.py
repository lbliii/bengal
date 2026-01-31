"""
Tests for orchestration/utils/parallel.py.

Tests BatchProgressUpdater and ProcessResult.
ParallelProcessor is tested indirectly via orchestrator tests.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from bengal.orchestration.utils.parallel import (
    BatchProgressUpdater,
    ProcessResult,
)


class TestProcessResult:
    """Test ProcessResult dataclass."""

    def test_default_values(self) -> None:
        """Default values should be empty/zero."""
        result = ProcessResult()
        assert result.results == []
        assert result.errors == []
        assert result.total_processed == 0
        assert result.total_errors == 0

    def test_generic_type(self) -> None:
        """Should work with different result types."""
        result: ProcessResult[str] = ProcessResult()
        result.results.append("item1")
        result.results.append("item2")
        result.total_processed = 2

        assert len(result.results) == 2
        assert result.total_processed == 2


class TestBatchProgressUpdater:
    """Test BatchProgressUpdater for throttled progress updates."""

    def test_no_op_without_manager(self) -> None:
        """Should be a no-op when progress_manager is None."""
        updater = BatchProgressUpdater(None, phase="test")
        # Should not raise
        updater.increment("item1")
        updater.increment("item2")
        updater.finalize()

    def test_batches_updates(self) -> None:
        """Should batch updates instead of calling on every increment."""
        mock_manager = MagicMock()
        updater = BatchProgressUpdater(
            mock_manager, phase="rendering", batch_size=5, update_interval_s=1.0
        )

        # Increment 3 times (below batch size, no update yet)
        for i in range(3):
            updater.increment(f"item_{i}")

        # Should not have called update yet (batch not full)
        assert mock_manager.update_phase.call_count == 0

        # Increment 2 more (total 5 = batch size)
        for i in range(3, 5):
            updater.increment(f"item_{i}")

        # Should have called update once
        assert mock_manager.update_phase.call_count == 1

    def test_updates_on_time_interval(self) -> None:
        """Should update when time interval passes even if batch not full."""
        mock_manager = MagicMock()
        updater = BatchProgressUpdater(
            mock_manager, phase="test", batch_size=100, update_interval_s=0.01
        )

        # Increment once
        updater.increment("item1")

        # Wait for interval
        time.sleep(0.02)

        # Second increment should trigger update due to time
        updater.increment("item2")

        assert mock_manager.update_phase.call_count >= 1

    def test_finalize_flushes_pending(self) -> None:
        """finalize() should flush any pending updates."""
        mock_manager = MagicMock()
        updater = BatchProgressUpdater(
            mock_manager, phase="assets", batch_size=100
        )

        # Increment a few times (won't trigger batch)
        for i in range(3):
            updater.increment(f"item_{i}")

        # Finalize should flush
        updater.finalize(total=10)

        # Check final call was made
        assert mock_manager.update_phase.called
        final_call = mock_manager.update_phase.call_args
        assert final_call[1]["current"] == 10

    def test_completed_count_property(self) -> None:
        """completed_count should include pending updates."""
        updater = BatchProgressUpdater(None, phase="test", batch_size=100)

        for i in range(7):
            updater.increment(f"item_{i}")

        assert updater.completed_count == 7

    def test_thread_safety(self) -> None:
        """Should be thread-safe for concurrent increments."""
        mock_manager = MagicMock()
        updater = BatchProgressUpdater(
            mock_manager, phase="parallel", batch_size=10
        )

        def increment_many():
            for i in range(100):
                updater.increment(f"item_{i}")

        threads = [threading.Thread(target=increment_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        updater.finalize()

        # Should have counted all 400 increments
        assert updater.completed_count == 400

    def test_passes_metadata_to_update(self) -> None:
        """Should pass additional metadata to update_phase."""
        mock_manager = MagicMock()
        updater = BatchProgressUpdater(
            mock_manager, phase="assets", batch_size=1
        )

        updater.increment("style.css", minified=True, size=1024)

        assert mock_manager.update_phase.called
        call_kwargs = mock_manager.update_phase.call_args[1]
        assert call_kwargs["minified"] is True
        assert call_kwargs["size"] == 1024
