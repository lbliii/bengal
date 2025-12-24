"""
Test that cache errors are tracked in error sessions.

Validates that critical cache errors (corruption, write failures) are properly
recorded in the error session for build summaries and pattern detection.
"""

import pytest

from bengal.cache.compression import load_compressed
from bengal.errors import BengalCacheError, get_session, reset_session


@pytest.fixture(autouse=True)
def fresh_session():
    """Reset session before and after each test."""
    reset_session()
    yield
    reset_session()


class TestCacheSessionTracking:
    """Tests for cache error session tracking."""

    def test_cache_version_error_tracked_in_session(self, tmp_path):
        """Verify cache version errors are recorded in error session."""
        cache_path = tmp_path / "cache.json.zst"
        # Write invalid magic header
        cache_path.write_bytes(b"invalid magic header content")

        with pytest.raises(BengalCacheError) as exc_info:
            load_compressed(cache_path)

        # Verify the error was raised with correct code
        assert exc_info.value.code is not None
        assert exc_info.value.code.value == "cache_version_mismatch"

        # Verify error was recorded in session
        session = get_session()
        summary = session.get_summary()

        assert summary["total_errors"] >= 1

        # Check that errors by code includes cache_version_mismatch
        errors_by_code = summary.get("errors_by_code", {})
        assert any("cache_version_mismatch" in code or "A002" in code for code in errors_by_code), (
            f"Expected cache_version_mismatch in errors_by_code: {errors_by_code}"
        )

    def test_cache_error_includes_file_path(self, tmp_path):
        """Verify cache errors include file path in session."""
        cache_path = tmp_path / "test_cache.json.zst"
        cache_path.write_bytes(b"bad header")

        with pytest.raises(BengalCacheError):
            load_compressed(cache_path)

        session = get_session()
        summary = session.get_summary()

        # Verify affected files count increased
        assert summary["affected_files"] >= 1

    def test_session_summary_counts_cache_errors(self, tmp_path):
        """Verify session summary correctly counts cache errors."""
        # Trigger multiple cache errors
        for i in range(3):
            cache_path = tmp_path / f"cache_{i}.json.zst"
            cache_path.write_bytes(b"invalid header")

            with pytest.raises(BengalCacheError):
                load_compressed(cache_path)

        session = get_session()
        summary = session.get_summary()

        # Should have at least 3 errors recorded
        assert summary["total_errors"] >= 3
