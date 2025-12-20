"""
Tests to ensure BuildStats objects are accessed correctly (not as dicts).
"""

import pytest

from bengal.orchestration.stats import BuildStats


class TestBuildStatsAccess:
    """Test that BuildStats is accessed via attributes, not dict keys."""

    def test_buildstats_has_attributes(self):
        """Test that BuildStats has expected attributes."""
        stats = BuildStats()

        # These should work (attributes)
        assert hasattr(stats, "total_pages")
        assert hasattr(stats, "build_time_ms")
        assert hasattr(stats, "regular_pages")
        assert hasattr(stats, "generated_pages")
        assert hasattr(stats, "parallel")
        assert hasattr(stats, "incremental")

    def test_buildstats_attribute_access(self):
        """Test accessing BuildStats via attributes."""
        stats = BuildStats(
            total_pages=100,
            build_time_ms=500.0,
            regular_pages=80,
            generated_pages=20,
            parallel=True,
            incremental=False,
        )

        # Should be able to access via attributes
        assert stats.total_pages == 100
        assert stats.build_time_ms == 500.0
        assert stats.regular_pages == 80
        assert stats.generated_pages == 20
        assert stats.parallel is True
        assert stats.incremental is False

    def test_buildstats_does_not_have_get_method(self):
        """Test that BuildStats doesn't have .get() method like dict."""
        stats = BuildStats()

        # BuildStats should not have .get() method
        # (It's a dataclass, not a dict)
        assert not hasattr(stats, "get") or not callable(getattr(stats, "get", None))

    def test_buildstats_to_dict_method(self):
        """Test that BuildStats has to_dict() method for conversion."""
        stats = BuildStats(total_pages=50, build_time_ms=250.0)

        # Should have to_dict() method
        assert hasattr(stats, "to_dict")
        assert callable(stats.to_dict)

        # Should return a dict
        result = stats.to_dict()
        assert isinstance(result, dict)
        assert result["total_pages"] == 50
        assert result["build_time_ms"] == 250.0

    def test_accessing_buildstats_as_dict_fails(self):
        """Test that trying to access BuildStats as dict raises error."""
        stats = BuildStats(total_pages=100)

        # These should fail (dict-style access)
        with pytest.raises((TypeError, AttributeError)):
            _ = stats["total_pages"]

        with pytest.raises(AttributeError):
            _ = stats.get("total_pages", 0)


class TestBuildStatsInServerContext:
    """Test BuildStats usage patterns that were causing issues."""

    def test_server_should_use_attributes_not_get(self):
        """Test the correct way to access BuildStats in server code."""
        stats = BuildStats(total_pages=198, build_time_ms=756.1)

        # ❌ WRONG (what was causing the bug)
        # pages = stats.get('pages_rendered', 0)  # AttributeError!

        # ✅ CORRECT
        pages = stats.total_pages
        duration = stats.build_time_ms

        assert pages == 198
        assert duration == 756.1

    def test_logging_buildstats_correctly(self):
        """Test correct pattern for logging BuildStats data."""
        stats = BuildStats(total_pages=198, build_time_ms=756.1, parallel=True, incremental=False)

        # Correct pattern for logging
        log_data = {
            "pages_built": stats.total_pages,  # Not stats.get('pages_rendered')
            "duration_ms": stats.build_time_ms,  # Not stats.get('total_duration_ms')
            "parallel": stats.parallel,
            "incremental": stats.incremental,
        }

        assert log_data["pages_built"] == 198
        assert log_data["duration_ms"] == 756.1
        assert log_data["parallel"] is True
        assert log_data["incremental"] is False


class TestBuildStatsDefaults:
    """Test BuildStats default values."""

    def test_buildstats_defaults(self):
        """Test that BuildStats has sensible defaults."""
        stats = BuildStats()

        assert stats.total_pages == 0
        assert stats.regular_pages == 0
        assert stats.generated_pages == 0
        assert stats.build_time_ms == 0
        assert stats.parallel is True  # Default to parallel
        assert stats.incremental is False  # Default to full build
        assert stats.skipped is False

    def test_buildstats_with_partial_data(self):
        """Test creating BuildStats with partial data."""
        stats = BuildStats(total_pages=100, build_time_ms=500.0)

        # Specified values should be set
        assert stats.total_pages == 100
        assert stats.build_time_ms == 500.0

        # Unspecified values should use defaults
        assert stats.regular_pages == 0
        assert stats.parallel is True
