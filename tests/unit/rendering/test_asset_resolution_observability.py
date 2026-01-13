"""Unit tests for asset resolution observability.

RFC: rfc-asset-resolution-observability.md

Tests the logging, warning deduplication, and stats tracking added to
asset manifest resolution for better observability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bengal.rendering.assets import (
    AssetManifestContext,
    _ensure_resolution_stats,
    _resolve_fingerprinted,
    asset_manifest_context,
    clear_manifest_cache,
    get_resolution_stats,
)
from bengal.utils.logger import get_logger, reset_loggers


@dataclass
class MockSite:
    """Mock Site for testing asset resolution."""

    output_dir: Path
    dev_mode: bool = False


@pytest.fixture
def mock_site(tmp_path: Path) -> MockSite:
    """Create a mock site for testing."""
    return MockSite(output_dir=tmp_path, dev_mode=False)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean state before and after each test."""
    clear_manifest_cache()
    reset_loggers()  # Reset logger state to get fresh events
    yield
    clear_manifest_cache()
    reset_loggers()


def _get_logger_events(logger_name: str = "bengal.rendering.assets") -> list:
    """Get events from the BengalLogger for assertions.
    
    Bengal uses a custom BengalLogger that stores events internally,
    rather than using Python's standard logging module.
    """
    from bengal.utils.logger import _loggers
    
    if logger_name in _loggers:
        return _loggers[logger_name].get_events()
    return []


def _get_event_messages(events: list) -> list[str]:
    """Extract message strings from BengalLogger events."""
    return [e.message for e in events]


class TestWarningLogging:
    """Tests for warning logs on unexpected fallback."""

    def test_warning_logged_on_unexpected_fallback(self, mock_site: MockSite) -> None:
        """Warning should be logged when fallback used outside dev mode."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        messages = _get_event_messages(events)
        assert "asset_manifest_disk_fallback" in messages

    def test_no_warning_when_contextvar_set(self, mock_site: MockSite) -> None:
        """No warning when ContextVar is properly set."""
        ctx = AssetManifestContext(
            entries={"css/style.css": "assets/css/style.abc123.css"}
        )

        with asset_manifest_context(ctx):
            result = _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        messages = _get_event_messages(events)
        assert "asset_manifest_disk_fallback" not in messages
        assert result == "assets/css/style.abc123.css"

    def test_warning_includes_output_dir_context(self, mock_site: MockSite) -> None:
        """Warning should include output_dir for debugging."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        warning_events = [e for e in events if e.message == "asset_manifest_disk_fallback"]
        assert len(warning_events) == 1
        assert str(mock_site.output_dir) in str(warning_events[0].context.get("output_dir", ""))

    def test_warning_includes_hint(self, mock_site: MockSite) -> None:
        """Warning should include helpful hint about ContextVar."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        warning_events = [e for e in events if e.message == "asset_manifest_disk_fallback"]
        assert len(warning_events) == 1
        hint = warning_events[0].context.get("hint", "")
        assert "ContextVar not set" in hint or "asset_manifest_context" in hint


class TestWarningDeduplication:
    """Tests for warning deduplication to prevent log spam."""

    def test_warning_deduplicated(self, mock_site: MockSite) -> None:
        """Same path should only warn once."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        warning_count = sum(1 for e in events if e.message == "asset_manifest_disk_fallback")
        assert warning_count == 1

    def test_different_paths_warn_separately(self, mock_site: MockSite) -> None:
        """Different paths should each warn once."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("js/main.js", mock_site)
        _resolve_fingerprinted("images/logo.png", mock_site)

        events = _get_logger_events()
        warning_count = sum(1 for e in events if e.message == "asset_manifest_disk_fallback")
        assert warning_count == 3

    def test_deduplication_reset_on_clear_cache(self, mock_site: MockSite) -> None:
        """clear_manifest_cache should reset deduplication state."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)

        # Count warnings before reset
        events_before = _get_logger_events()
        warning_count_before = sum(1 for e in events_before if e.message == "asset_manifest_disk_fallback")
        assert warning_count_before == 1

        # Clear resets both cache and deduplication
        clear_manifest_cache()
        reset_loggers()  # Reset to get fresh event tracking

        # Should warn again after cache clear
        _resolve_fingerprinted("css/style.css", mock_site)

        events_after = _get_logger_events()
        warning_count_after = sum(1 for e in events_after if e.message == "asset_manifest_disk_fallback")
        assert warning_count_after == 1


class TestDevModeLogging:
    """Tests for debug logging in dev mode."""

    def test_debug_log_in_dev_mode(self, mock_site: MockSite) -> None:
        """Debug log in dev mode (expected fallback)."""
        from bengal.utils.logger import configure_logging, LogLevel
        
        # Enable DEBUG level to capture debug events
        configure_logging(level=LogLevel.DEBUG)
        mock_site.dev_mode = True

        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        messages = _get_event_messages(events)
        assert "asset_manifest_dev_mode_fallback" in messages

    def test_no_warning_in_dev_mode(self, mock_site: MockSite) -> None:
        """No warning should be logged in dev mode."""
        mock_site.dev_mode = True

        _resolve_fingerprinted("css/style.css", mock_site)

        events = _get_logger_events()
        messages = _get_event_messages(events)
        assert "asset_manifest_disk_fallback" not in messages


class TestStatsTracking:
    """Tests for ComponentStats integration."""

    def test_stats_track_cache_hits(self, mock_site: MockSite) -> None:
        """Cache hits should be tracked when ContextVar is set."""
        ctx = AssetManifestContext(
            entries={"css/style.css": "assets/css/style.abc123.css"}
        )

        with asset_manifest_context(ctx):
            _resolve_fingerprinted("css/style.css", mock_site)
            _resolve_fingerprinted("css/style.css", mock_site)
            _resolve_fingerprinted("css/style.css", mock_site)

        stats = get_resolution_stats()
        assert stats is not None
        assert stats.cache_hits == 3
        assert stats.cache_misses == 0

    def test_stats_track_cache_misses(self, mock_site: MockSite) -> None:
        """Cache misses should be tracked on fallback."""
        mock_site.dev_mode = True  # Avoid warning spam

        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("js/main.js", mock_site)

        stats = get_resolution_stats()
        assert stats is not None
        assert stats.cache_hits == 0
        assert stats.cache_misses == 2

    def test_stats_track_unexpected_fallback(self, mock_site: MockSite) -> None:
        """Unexpected fallbacks should be tracked in items_skipped."""
        mock_site.dev_mode = False

        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("js/main.js", mock_site)

        stats = get_resolution_stats()
        assert stats is not None
        assert stats.items_skipped.get("unexpected_fallback", 0) == 2

    def test_stats_track_dev_mode_fallback(self, mock_site: MockSite) -> None:
        """Dev mode fallbacks should be tracked separately."""
        mock_site.dev_mode = True

        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("js/main.js", mock_site)

        stats = get_resolution_stats()
        assert stats is not None
        assert stats.items_skipped.get("dev_mode_fallback", 0) == 2
        assert stats.items_skipped.get("unexpected_fallback", 0) == 0

    def test_stats_reset_on_clear_cache(self, mock_site: MockSite) -> None:
        """Stats should reset on clear_manifest_cache()."""
        # Create some stats
        stats = _ensure_resolution_stats()
        stats.cache_hits = 100
        stats.cache_misses = 50

        # Clear should reset
        clear_manifest_cache()

        assert get_resolution_stats() is None

    def test_stats_format_summary(self, mock_site: MockSite) -> None:
        """Stats should produce useful format_summary output."""
        ctx = AssetManifestContext(entries={"css/style.css": "css/style.abc.css"})

        with asset_manifest_context(ctx):
            _resolve_fingerprinted("css/style.css", mock_site)
            _resolve_fingerprinted("css/style.css", mock_site)

        stats = get_resolution_stats()
        assert stats is not None
        summary = stats.format_summary("AssetResolution")
        assert "AssetResolution" in summary
        assert "cache=" in summary


class TestContextVarStatsIsolation:
    """Tests for thread-safe stats via ContextVar."""

    def test_stats_created_per_context(self, mock_site: MockSite) -> None:
        """Each resolution context should have independent stats."""
        clear_manifest_cache()

        # First resolution creates stats
        _resolve_fingerprinted("css/style.css", mock_site)
        stats1 = get_resolution_stats()
        assert stats1 is not None

        # Stats persist in same context
        _resolve_fingerprinted("js/main.js", mock_site)
        stats2 = get_resolution_stats()
        assert stats2 is stats1  # Same object

    def test_ensure_resolution_stats_creates_if_missing(self) -> None:
        """_ensure_resolution_stats should create stats if None."""
        clear_manifest_cache()
        assert get_resolution_stats() is None

        stats = _ensure_resolution_stats()
        assert stats is not None
        assert get_resolution_stats() is stats

    def test_ensure_resolution_stats_returns_existing(self) -> None:
        """_ensure_resolution_stats should return existing stats."""
        clear_manifest_cache()

        stats1 = _ensure_resolution_stats()
        stats1.cache_hits = 42

        stats2 = _ensure_resolution_stats()
        assert stats2 is stats1
        assert stats2.cache_hits == 42
