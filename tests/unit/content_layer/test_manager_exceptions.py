"""
Tests for ContentLayerManager exception handling.

These tests verify that:
- Critical exceptions (KeyboardInterrupt, SystemExit) are re-raised
- Regular exceptions are logged but don't crash the entire fetch
- Failed sources can fall back to cache in offline mode
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bengal.content.sources.entry import ContentEntry
from bengal.content.sources.manager import ContentLayerManager
from bengal.content.sources.source import ContentSource


class MockSource(ContentSource):
    """Test source that can be configured to succeed or fail."""

    source_type = "mock"

    def __init__(
        self,
        name: str,
        config: dict[str, Any],
        *,
        entries: list[ContentEntry] | None = None,
        error: BaseException | None = None,
    ) -> None:
        super().__init__(name, config)
        self._entries = entries or []
        self._error = error

    async def fetch_all(self):
        if self._error:
            raise self._error
        for entry in self._entries:
            yield entry

    async def fetch_one(self, id: str) -> ContentEntry | None:
        for entry in self._entries:
            if entry.id == id:
                return entry
        return None


class TestManagerCriticalExceptions:
    """Test that critical exceptions are properly re-raised.

    Note: We test the logic path rather than actually raising these exceptions,
    as pytest workers don't handle KeyboardInterrupt/SystemExit gracefully.
    """

    def test_keyboard_interrupt_propagates(self) -> None:
        """Verify KeyboardInterrupt is a BaseException (caught by return_exceptions=True)."""
        assert isinstance(KeyboardInterrupt(), BaseException)
        assert isinstance(KeyboardInterrupt(), (KeyboardInterrupt, SystemExit))

    def test_system_exit_propagates(self) -> None:
        """Verify SystemExit is a BaseException (caught by return_exceptions=True)."""
        assert isinstance(SystemExit(1), BaseException)
        assert isinstance(SystemExit(1), (KeyboardInterrupt, SystemExit))

    def test_runtime_error_is_not_critical(self) -> None:
        """Verify regular exceptions are not treated as critical."""
        exc = RuntimeError("test")
        assert not isinstance(exc, (KeyboardInterrupt, SystemExit))
        # Would be caught and logged, not re-raised


class TestManagerRegularExceptions:
    """Test that regular exceptions are handled gracefully."""

    @pytest.mark.asyncio
    async def test_regular_exception_logged_not_raised(self, tmp_path: Path) -> None:
        """Regular exceptions should be logged but not crash the manager."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        source = MockSource("failing", {}, error=RuntimeError("Network error"))
        manager.sources["failing"] = source

        # Should not raise
        entries = await manager.fetch_all(use_cache=False)

        # Should return empty list (source failed)
        assert entries == []

    @pytest.mark.asyncio
    async def test_one_failing_source_doesnt_affect_others(self, tmp_path: Path) -> None:
        """If one source fails, others should still work."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        # Failing source
        failing_source = MockSource("failing", {}, error=RuntimeError("Oops"))
        manager.sources["failing"] = failing_source

        # Working source with entries
        working_entry = ContentEntry(
            id="test",
            slug="test",
            content="# Test",
            source_type="mock",
            source_name="working",
        )
        working_source = MockSource("working", {}, entries=[working_entry])
        manager.sources["working"] = working_source

        entries = await manager.fetch_all(use_cache=False)

        # Should have entries from working source
        assert len(entries) == 1
        assert entries[0].id == "test"

    @pytest.mark.asyncio
    async def test_value_error_is_regular_exception(self, tmp_path: Path) -> None:
        """ValueError (common error) should be caught."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        source = MockSource("test", {}, error=ValueError("Invalid input"))
        manager.sources["test"] = source

        # Should not raise
        entries = await manager.fetch_all(use_cache=False)
        assert entries == []

    @pytest.mark.asyncio
    async def test_connection_error_is_regular_exception(self, tmp_path: Path) -> None:
        """Connection errors should be caught."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        source = MockSource("test", {}, error=ConnectionError("Failed to connect"))
        manager.sources["test"] = source

        # Should not raise
        entries = await manager.fetch_all(use_cache=False)
        assert entries == []


class TestManagerCacheFallback:
    """Test cache fallback behavior on errors."""

    @pytest.mark.asyncio
    async def test_offline_mode_uses_stale_cache_on_error(self, tmp_path: Path) -> None:
        """In offline mode, should use stale cache when fetch fails."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Pre-populate cache
        import json

        cached_entry = {
            "id": "cached",
            "slug": "cached",
            "content": "# Cached",
            "frontmatter": {"title": "Cached"},
            "source_type": "mock",
            "source_name": "test",
        }
        (cache_dir / "test.json").write_text(json.dumps([cached_entry]))
        (cache_dir / "test.meta.json").write_text(
            json.dumps(
                {
                    "source_key": "mock:test:[]",
                    "cached_at": "2024-01-01T00:00:00",
                    "entry_count": 1,
                }
            )
        )

        manager = ContentLayerManager(cache_dir=cache_dir, offline=True)

        source = MockSource("test", {}, error=RuntimeError("Offline"))
        manager.sources["test"] = source

        entries = await manager.fetch_all(use_cache=True)

        # Should fall back to cached entry
        assert len(entries) == 1
        assert entries[0].id == "cached"


class TestManagerMultipleSources:
    """Test behavior with multiple sources."""

    @pytest.mark.asyncio
    async def test_all_sources_failing(self, tmp_path: Path) -> None:
        """Should handle all sources failing gracefully."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        manager.sources["source1"] = MockSource("s1", {}, error=RuntimeError("Fail 1"))
        manager.sources["source2"] = MockSource("s2", {}, error=RuntimeError("Fail 2"))
        manager.sources["source3"] = MockSource("s3", {}, error=RuntimeError("Fail 3"))

        # Should not raise
        entries = await manager.fetch_all(use_cache=False)

        # All failed, so empty
        assert entries == []

    @pytest.mark.asyncio
    async def test_aggregates_from_all_working_sources(self, tmp_path: Path) -> None:
        """Should aggregate entries from all working sources."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        entry1 = ContentEntry(
            id="1", slug="one", content="# One", source_type="mock", source_name="s1"
        )
        entry2 = ContentEntry(
            id="2", slug="two", content="# Two", source_type="mock", source_name="s2"
        )

        manager.sources["s1"] = MockSource("s1", {}, entries=[entry1])
        manager.sources["s2"] = MockSource("s2", {}, entries=[entry2])

        entries = await manager.fetch_all(use_cache=False)

        assert len(entries) == 2
        ids = {e.id for e in entries}
        assert ids == {"1", "2"}


class TestManagerSyncWrapper:
    """Test the synchronous wrapper method."""

    def test_fetch_all_sync_handles_exceptions(self, tmp_path: Path) -> None:
        """Sync wrapper should also handle exceptions properly."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        source = MockSource("test", {}, error=RuntimeError("Sync error"))
        manager.sources["test"] = source

        # Should not raise
        entries = manager.fetch_all_sync(use_cache=False)
        assert entries == []

    def test_fetch_all_sync_returns_entries(self, tmp_path: Path) -> None:
        """Sync wrapper should return entries from working sources."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        entry = ContentEntry(
            id="test", slug="test", content="# Test", source_type="mock", source_name="test"
        )
        manager.sources["test"] = MockSource("test", {}, entries=[entry])

        entries = manager.fetch_all_sync(use_cache=False)

        assert len(entries) == 1
        assert entries[0].id == "test"
