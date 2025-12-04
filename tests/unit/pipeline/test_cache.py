"""
Unit tests for bengal.pipeline.cache - disk caching for streams.

Tests:
    - StreamCacheEntry serialization
    - StreamCache persistence
    - DiskCachedStream behavior
    - Cache invalidation
"""

from __future__ import annotations

import json
from pathlib import Path

from bengal.pipeline.cache import (
    DiskCachedStream,
    StreamCache,
    StreamCacheEntry,
)
from bengal.pipeline.core import StreamItem, StreamKey
from bengal.pipeline.streams import SourceStream


class TestStreamCacheEntry:
    """Tests for StreamCacheEntry dataclass."""

    def test_creation(self) -> None:
        """StreamCacheEntry stores all fields."""
        entry = StreamCacheEntry(
            source="test",
            id="item1",
            version="abc123",
            value_json='{"x": 1}',
            cached_at=1234567890.0,
        )

        assert entry.source == "test"
        assert entry.id == "item1"
        assert entry.version == "abc123"
        assert entry.value_json == '{"x": 1}'
        assert entry.cached_at == 1234567890.0

    def test_key_property(self) -> None:
        """key property reconstructs StreamKey."""
        entry = StreamCacheEntry(
            source="test",
            id="item1",
            version="abc123",
            value_json="{}",
        )

        key = entry.key
        assert key.source == "test"
        assert key.id == "item1"
        assert key.version == "abc123"

    def test_to_cache_dict(self) -> None:
        """to_cache_dict returns serializable dict."""
        entry = StreamCacheEntry(
            source="test",
            id="item1",
            version="abc123",
            value_json='{"x": 1}',
            cached_at=1234567890.0,
        )

        data = entry.to_cache_dict()

        assert data["source"] == "test"
        assert data["id"] == "item1"
        assert data["version"] == "abc123"
        assert data["value_json"] == '{"x": 1}'
        assert data["cached_at"] == 1234567890.0

    def test_from_cache_dict(self) -> None:
        """from_cache_dict reconstructs entry."""
        data = {
            "source": "test",
            "id": "item1",
            "version": "abc123",
            "value_json": '{"x": 1}',
            "cached_at": 1234567890.0,
        }

        entry = StreamCacheEntry.from_cache_dict(data)

        assert entry.source == "test"
        assert entry.id == "item1"
        assert entry.version == "abc123"
        assert entry.value_json == '{"x": 1}'

    def test_roundtrip(self) -> None:
        """Roundtrip serialization preserves data."""
        original = StreamCacheEntry(
            source="test",
            id="item1",
            version="abc123",
            value_json='{"x": 1}',
            cached_at=1234567890.0,
        )

        data = original.to_cache_dict()
        loaded = StreamCacheEntry.from_cache_dict(data)

        assert loaded.source == original.source
        assert loaded.id == original.id
        assert loaded.version == original.version
        assert loaded.value_json == original.value_json


class TestStreamCache:
    """Tests for StreamCache."""

    def test_put_and_get(self, tmp_path: Path) -> None:
        """Can store and retrieve values."""
        cache = StreamCache(tmp_path / "pipeline")
        key = StreamKey(source="test", id="item1", version="v1")

        cache.put(key, {"x": 1})
        result = cache.get(key, json.loads)

        assert result == {"x": 1}

    def test_get_missing_key(self, tmp_path: Path) -> None:
        """Returns None for missing key."""
        cache = StreamCache(tmp_path / "pipeline")
        key = StreamKey(source="test", id="missing", version="v1")

        result = cache.get(key)

        assert result is None

    def test_version_mismatch(self, tmp_path: Path) -> None:
        """Returns None when version doesn't match."""
        cache = StreamCache(tmp_path / "pipeline")
        key_v1 = StreamKey(source="test", id="item1", version="v1")
        key_v2 = StreamKey(source="test", id="item1", version="v2")

        cache.put(key_v1, {"x": 1})

        # Same id but different version = cache miss
        result = cache.get(key_v2, json.loads)

        assert result is None

    def test_invalidate(self, tmp_path: Path) -> None:
        """Invalidate removes entry."""
        cache = StreamCache(tmp_path / "pipeline")
        key = StreamKey(source="test", id="item1", version="v1")

        cache.put(key, {"x": 1})
        removed = cache.invalidate(key)

        assert removed is True
        assert cache.get(key) is None

    def test_invalidate_missing(self, tmp_path: Path) -> None:
        """Invalidate returns False for missing key."""
        cache = StreamCache(tmp_path / "pipeline")
        key = StreamKey(source="test", id="missing", version="v1")

        removed = cache.invalidate(key)

        assert removed is False

    def test_invalidate_source(self, tmp_path: Path) -> None:
        """Invalidate source removes all entries from that source."""
        cache = StreamCache(tmp_path / "pipeline")

        # Add entries from two sources
        cache.put(StreamKey("source1", "a", "v1"), "a")
        cache.put(StreamKey("source1", "b", "v1"), "b")
        cache.put(StreamKey("source2", "c", "v1"), "c")

        # Invalidate source1
        count = cache.invalidate_source("source1")

        assert count == 2
        assert cache.get(StreamKey("source1", "a", "v1")) is None
        assert cache.get(StreamKey("source1", "b", "v1")) is None
        assert cache.get(StreamKey("source2", "c", "v1")) is not None

    def test_clear(self, tmp_path: Path) -> None:
        """Clear removes all entries."""
        cache = StreamCache(tmp_path / "pipeline")
        cache.put(StreamKey("test", "a", "v1"), "a")
        cache.put(StreamKey("test", "b", "v1"), "b")

        cache.clear()

        assert cache.get(StreamKey("test", "a", "v1")) is None
        assert cache.get(StreamKey("test", "b", "v1")) is None

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Cache persists to disk and loads on restart."""
        cache_dir = tmp_path / "pipeline"

        # Create cache and add entries
        cache1 = StreamCache(cache_dir)
        cache1.put(StreamKey("test", "item1", "v1"), {"x": 1})
        cache1.put(StreamKey("test", "item2", "v1"), {"x": 2})
        cache1.save()

        # Create new cache instance (simulates restart)
        cache2 = StreamCache(cache_dir)

        # Entries should be loaded
        assert cache2.get(StreamKey("test", "item1", "v1"), json.loads) == {"x": 1}
        assert cache2.get(StreamKey("test", "item2", "v1"), json.loads) == {"x": 2}

    def test_get_stats(self, tmp_path: Path) -> None:
        """get_stats returns cache statistics."""
        cache = StreamCache(tmp_path / "pipeline")
        cache.put(StreamKey("source1", "a", "v1"), "a")
        cache.put(StreamKey("source1", "b", "v1"), "b")
        cache.put(StreamKey("source2", "c", "v1"), "c")

        stats = cache.get_stats()

        assert stats["total_entries"] == 3
        assert stats["entries_by_source"]["source1"] == 2
        assert stats["entries_by_source"]["source2"] == 1

    def test_custom_serialization(self, tmp_path: Path) -> None:
        """Custom serialize/deserialize functions work."""
        cache = StreamCache(tmp_path / "pipeline")
        key = StreamKey(source="test", id="item1", version="v1")

        # Custom type
        class Point:
            def __init__(self, x: int, y: int):
                self.x = x
                self.y = y

        def serialize(p: Point) -> str:
            return json.dumps({"x": p.x, "y": p.y})

        def deserialize(s: str) -> Point:
            data = json.loads(s)
            return Point(data["x"], data["y"])

        cache.put(key, Point(10, 20), serialize)
        result = cache.get(key, deserialize)

        assert result is not None
        assert result.x == 10
        assert result.y == 20


class TestDiskCachedStream:
    """Tests for DiskCachedStream."""

    def test_caches_values(self, tmp_path: Path) -> None:
        """Stream values are cached."""
        cache = StreamCache(tmp_path / "pipeline")

        items = [
            StreamItem.create("test", "1", {"x": 1}),
            StreamItem.create("test", "2", {"x": 2}),
        ]
        source = SourceStream(lambda: iter(items), name="test")
        cached_stream = DiskCachedStream(source, cache)

        # First iteration - all misses
        result1 = cached_stream.materialize()
        stats1 = cached_stream.get_cache_stats()

        assert result1 == [{"x": 1}, {"x": 2}]
        assert stats1["misses"] == 2
        assert stats1["hits"] == 0

    def test_returns_cached_on_hit(self, tmp_path: Path) -> None:
        """Cached values are returned without recomputing."""
        cache = StreamCache(tmp_path / "pipeline")

        # Pre-populate cache with same version
        key = StreamKey(source="test", id="1", version="v1")
        cache.put(key, {"cached": True})

        # Create stream with same key+version
        items = [StreamItem(key=key, value={"computed": True})]
        source = SourceStream(lambda: iter(items), name="test")
        cached_stream = DiskCachedStream(source, cache)

        result = cached_stream.materialize()
        stats = cached_stream.get_cache_stats()

        # Should return cached value, not computed value
        assert result == [{"cached": True}]
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_recomputes_on_version_change(self, tmp_path: Path) -> None:
        """Changed version causes recompute."""
        cache = StreamCache(tmp_path / "pipeline")

        # Pre-populate cache with old version
        old_key = StreamKey(source="test", id="1", version="old")
        cache.put(old_key, {"old": True})

        # Create stream with new version
        new_key = StreamKey(source="test", id="1", version="new")
        items = [StreamItem(key=new_key, value={"new": True})]
        source = SourceStream(lambda: iter(items), name="test")
        cached_stream = DiskCachedStream(source, cache)

        result = cached_stream.materialize()
        stats = cached_stream.get_cache_stats()

        # Should compute new value (version mismatch)
        assert result == [{"new": True}]
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    def test_persists_across_runs(self, tmp_path: Path) -> None:
        """Cache persists across stream instances."""
        cache_dir = tmp_path / "pipeline"

        # First run - populate cache
        items = [StreamItem.create("test", "1", {"x": 1}, version="v1")]
        cache1 = StreamCache(cache_dir)
        source1 = SourceStream(lambda: iter(items), name="test")
        stream1 = DiskCachedStream(source1, cache1)
        stream1.materialize()
        cache1.save()

        # Second run - should use cached values
        cache2 = StreamCache(cache_dir)

        # New source that would return different value if computed
        items2 = [
            StreamItem(
                key=StreamKey("test", "1", "v1"),  # Same version
                value={"x": 999},  # Different value
            )
        ]
        source2 = SourceStream(lambda: iter(items2), name="test")
        stream2 = DiskCachedStream(source2, cache2)

        result = stream2.materialize()
        stats = stream2.get_cache_stats()

        # Should return cached value from first run
        assert result == [{"x": 1}]
        assert stats["hits"] == 1

    def test_fluent_api(self, tmp_path: Path) -> None:
        """disk_cache method on Stream works."""
        cache = StreamCache(tmp_path / "pipeline")

        items = [StreamItem.create("test", "1", "value")]
        source = SourceStream(lambda: iter(items), name="test")

        # Use fluent API
        cached_stream = source.disk_cache(cache)

        assert isinstance(cached_stream, DiskCachedStream)
        assert cached_stream.materialize() == ["value"]


class TestDiskCachedStreamIntegration:
    """Integration tests for disk caching with pipeline operations."""

    def test_cache_after_map(self, tmp_path: Path) -> None:
        """Caching works after map transformation."""
        cache = StreamCache(tmp_path / "pipeline")

        items = [
            StreamItem.create("test", "1", 1),
            StreamItem.create("test", "2", 2),
        ]
        source = SourceStream(lambda: iter(items), name="test")

        result = source.map(lambda x: x * 2).disk_cache(cache).materialize()

        assert result == [2, 4]

    def test_cache_in_pipeline(self, tmp_path: Path) -> None:
        """Disk caching integrates with pipeline."""
        cache = StreamCache(tmp_path / "pipeline")

        items = [
            StreamItem.create("test", "1", 1),
            StreamItem.create("test", "2", 2),
            StreamItem.create("test", "3", 3),
        ]
        source = SourceStream(lambda: iter(items), name="test")

        result = (
            source.filter(lambda x: x > 1).map(lambda x: x * 10).disk_cache(cache).materialize()
        )

        assert result == [20, 30]


