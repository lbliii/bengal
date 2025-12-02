"""Tests for ContentLayerManager."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bengal.content_layer.entry import ContentEntry
from bengal.content_layer.manager import ContentLayerManager
from bengal.content_layer.source import ContentSource


class MockSource(ContentSource):
    """Mock source for testing."""

    source_type = "mock"

    def __init__(
        self,
        name: str,
        config: dict,
        entries: list[ContentEntry] | None = None,
    ) -> None:
        super().__init__(name, config)
        self._entries = entries or []

    async def fetch_all(self):
        for entry in self._entries:
            yield entry

    async def fetch_one(self, id: str):
        for entry in self._entries:
            if entry.id == id:
                return entry
        return None


class TestContentLayerManager:
    """Tests for ContentLayerManager."""

    def test_init_creates_cache_dir(self, tmp_path: Path) -> None:
        """Test that manager creates cache directory."""
        cache_dir = tmp_path / "cache"
        assert not cache_dir.exists()

        ContentLayerManager(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_register_custom_source(self) -> None:
        """Test registering custom source."""
        manager = ContentLayerManager()
        source = MockSource("test", {})

        manager.register_custom_source("test", source)

        assert "test" in manager.sources
        assert manager.sources["test"] is source

    def test_register_unknown_source_type(self, tmp_path: Path) -> None:
        """Test registering unknown source type raises error."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        with pytest.raises(ValueError, match="Unknown source type"):
            manager.register_source("test", "unknown_type", {})

    def test_register_local_source(self, tmp_path: Path) -> None:
        """Test registering local source."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        manager = ContentLayerManager(cache_dir=tmp_path / "cache")
        manager.register_source("docs", "local", {"directory": str(content_dir)})

        assert "docs" in manager.sources
        assert manager.sources["docs"].source_type == "local"

    @pytest.mark.asyncio
    async def test_fetch_all_no_sources(self, tmp_path: Path) -> None:
        """Test fetching with no sources returns empty list."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")
        entries = await manager.fetch_all()

        assert entries == []

    @pytest.mark.asyncio
    async def test_fetch_all_with_entries(self, tmp_path: Path) -> None:
        """Test fetching aggregates entries from all sources."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")

        # Add two mock sources
        entries1 = [
            ContentEntry(id="1.md", slug="one", content="one", source_name="s1"),
            ContentEntry(id="2.md", slug="two", content="two", source_name="s1"),
        ]
        entries2 = [
            ContentEntry(id="3.md", slug="three", content="three", source_name="s2"),
        ]

        manager.register_custom_source("s1", MockSource("s1", {}, entries1))
        manager.register_custom_source("s2", MockSource("s2", {}, entries2))

        result = await manager.fetch_all(use_cache=False)

        assert len(result) == 3
        slugs = {e.slug for e in result}
        assert slugs == {"one", "two", "three"}

    def test_fetch_all_sync(self, tmp_path: Path) -> None:
        """Test synchronous fetch wrapper."""
        manager = ContentLayerManager(cache_dir=tmp_path / "cache")
        entries = [ContentEntry(id="1.md", slug="one", content="")]

        manager.register_custom_source("test", MockSource("test", {}, entries))

        result = manager.fetch_all_sync(use_cache=False)

        assert len(result) == 1
        assert result[0].slug == "one"

    def test_cache_save_and_load(self, tmp_path: Path) -> None:
        """Test cache persistence."""
        cache_dir = tmp_path / "cache"
        manager = ContentLayerManager(cache_dir=cache_dir)

        entries = [
            ContentEntry(
                id="test.md",
                slug="test",
                content="# Test",
                frontmatter={"title": "Test"},
                source_name="test",
            )
        ]

        # Save to cache
        manager._save_cache("test", entries, "cache-key-123")

        # Verify files exist
        assert (cache_dir / "test.json").exists()
        assert (cache_dir / "test.meta.json").exists()

        # Load from cache
        loaded = manager._load_cache("test")

        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].slug == "test"
        assert loaded[0].frontmatter == {"title": "Test"}

    def test_cache_validity(self, tmp_path: Path) -> None:
        """Test cache validity checks."""
        cache_dir = tmp_path / "cache"
        manager = ContentLayerManager(
            cache_dir=cache_dir,
            cache_ttl=timedelta(hours=1),
        )

        entries = [ContentEntry(id="1.md", slug="one", content="")]
        manager._save_cache("test", entries, "key-123")

        # Valid cache
        assert manager._is_cache_valid("test", "key-123")

        # Wrong key (config changed)
        assert not manager._is_cache_valid("test", "different-key")

        # Non-existent
        assert not manager._is_cache_valid("nonexistent", "any-key")

    def test_clear_cache_specific(self, tmp_path: Path) -> None:
        """Test clearing specific source cache."""
        cache_dir = tmp_path / "cache"
        manager = ContentLayerManager(cache_dir=cache_dir)

        # Save caches for two sources
        manager._save_cache("source1", [], "key1")
        manager._save_cache("source2", [], "key2")

        # Clear one
        deleted = manager.clear_cache("source1")

        assert deleted == 2  # .json and .meta.json
        assert not (cache_dir / "source1.json").exists()
        assert (cache_dir / "source2.json").exists()

    def test_clear_cache_all(self, tmp_path: Path) -> None:
        """Test clearing all caches."""
        cache_dir = tmp_path / "cache"
        manager = ContentLayerManager(cache_dir=cache_dir)

        manager._save_cache("source1", [], "key1")
        manager._save_cache("source2", [], "key2")

        deleted = manager.clear_cache()

        assert deleted == 4  # 2 sources × 2 files
        assert list(cache_dir.glob("*.json")) == []

    def test_get_cache_status(self, tmp_path: Path) -> None:
        """Test getting cache status."""
        cache_dir = tmp_path / "cache"
        manager = ContentLayerManager(cache_dir=cache_dir)

        # Register sources
        manager.register_custom_source("cached", MockSource("cached", {}))
        manager.register_custom_source("uncached", MockSource("uncached", {}))

        # Only cache one
        entries = [ContentEntry(id="1.md", slug="one", content="")]
        manager._save_cache("cached", entries, "key")

        status = manager.get_cache_status()

        assert "cached" in status
        assert status["cached"]["cached"] is True
        assert status["cached"]["entry_count"] == 1

        assert "uncached" in status
        assert status["uncached"]["cached"] is False

