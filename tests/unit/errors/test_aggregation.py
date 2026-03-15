"""
Unit tests for error aggregation.

Tests: ErrorAggregator add_error, should_log_individual, log_summary,
get_summary, extract_error_context.
"""

from __future__ import annotations

from pathlib import Path

from bengal.errors import BengalDiscoveryError, ErrorCode
from bengal.errors.aggregation import ErrorAggregator, extract_error_context


class TestErrorAggregatorAddError:
    """Test ErrorAggregator.add_error."""

    def test_add_error_increments_count(self) -> None:
        """add_error increments count for same signature."""
        agg = ErrorAggregator(total_items=10)
        agg.add_error(ValueError("same"))
        agg.add_error(ValueError("same"))
        assert sum(agg.error_counts.values()) == 2

    def test_add_error_different_signatures(self) -> None:
        """Different errors create separate counts."""
        agg = ErrorAggregator(total_items=10)
        agg.add_error(ValueError("err1"))
        agg.add_error(ValueError("err2"))
        assert len(agg.error_counts) == 2

    def test_add_error_stores_context_samples(self) -> None:
        """add_error stores context up to max_context_samples."""
        agg = ErrorAggregator(total_items=10, max_context_samples=2)
        agg.add_error(ValueError("x"), context={"file": "a.md"})
        agg.add_error(ValueError("x"), context={"file": "b.md"})
        agg.add_error(ValueError("x"), context={"file": "c.md"})
        sig = next(iter(agg.error_counts))
        assert len(agg.error_contexts[sig]) == 2


class TestErrorAggregatorShouldLogIndividual:
    """Test should_log_individual."""

    def test_below_threshold_always_log(self) -> None:
        """Below threshold always returns True."""
        agg = ErrorAggregator(total_items=10)
        agg.add_error(ValueError("x"))
        assert agg.should_log_individual(ValueError("x"), threshold=5) is True

    def test_above_threshold_limits_samples(self) -> None:
        """Above threshold limits samples per error type."""
        agg = ErrorAggregator(total_items=100)
        for _ in range(10):
            agg.add_error(ValueError("same"))
        # First 3 should log, rest suppress
        results = [
            agg.should_log_individual(ValueError("same"), threshold=5, max_samples=3)
            for _ in range(5)
        ]
        assert sum(results) == 3


class TestErrorAggregatorGetSummary:
    """Test get_summary."""

    def test_get_summary_structure(self) -> None:
        """get_summary returns expected keys."""
        agg = ErrorAggregator(total_items=20)
        agg.add_error(ValueError("x"))
        agg.add_error(ValueError("x"))
        summary = agg.get_summary()
        assert summary["total_errors"] == 2
        assert summary["unique_error_types"] == 1
        assert summary["total_items"] == 20
        assert "error_rate" in summary


class TestExtractErrorContext:
    """Test extract_error_context."""

    def test_extract_from_value_error(self) -> None:
        """Extract context from ValueError."""
        ctx = extract_error_context(ValueError("msg"))
        assert ctx["error"] == "msg"
        assert ctx["error_type"] == "ValueError"

    def test_extract_from_bengal_error(self) -> None:
        """Extract context from BengalError with file_path, suggestion."""
        err = BengalDiscoveryError(
            "Content dir missing",
            code=ErrorCode.D001,
            file_path=Path("/site/content"),
            suggestion="Create content directory",
        )
        ctx = extract_error_context(err)
        assert "content" in str(ctx.get("file_path", ""))
        assert ctx.get("suggestion") == "Create content directory"

    def test_extract_with_item_source_path(self) -> None:
        """Extract adds source_path from item."""
        item = type("Page", (), {"source_path": Path("content/post.md")})()
        ctx = extract_error_context(ValueError("x"), item=item)
        assert "content/post" in str(ctx.get("source_path", ""))
