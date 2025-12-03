"""
Unit tests for bengal.pipeline.core - StreamItem, StreamKey, and Stream base class.

Tests:
    - StreamKey creation and operations
    - StreamItem creation with automatic versioning
    - Stream iteration and caching behavior
"""

from __future__ import annotations

from bengal.pipeline.core import StreamItem, StreamKey


class TestStreamKey:
    """Tests for StreamKey dataclass."""

    def test_creation(self) -> None:
        """StreamKey stores source, id, and version."""
        key = StreamKey(source="files", id="test.md", version="abc123")

        assert key.source == "files"
        assert key.id == "test.md"
        assert key.version == "abc123"

    def test_immutability(self) -> None:
        """StreamKey is frozen (immutable)."""
        key = StreamKey(source="files", id="test.md", version="abc123")

        # Should raise FrozenInstanceError
        try:
            key.source = "other"  # type: ignore
            raise AssertionError("Should have raised")
        except Exception:
            pass

    def test_str_representation(self) -> None:
        """__str__ returns human-readable format."""
        key = StreamKey(source="files", id="test.md", version="abcdef123456")

        result = str(key)

        assert "files" in result
        assert "test.md" in result
        assert "abcdef12" in result  # First 8 chars of version

    def test_with_version(self) -> None:
        """with_version creates new key with updated version."""
        key = StreamKey(source="files", id="test.md", version="v1")

        new_key = key.with_version("v2")

        assert new_key.source == "files"
        assert new_key.id == "test.md"
        assert new_key.version == "v2"
        # Original unchanged
        assert key.version == "v1"

    def test_equality(self) -> None:
        """Keys with same values are equal."""
        key1 = StreamKey(source="files", id="test.md", version="v1")
        key2 = StreamKey(source="files", id="test.md", version="v1")

        assert key1 == key2

    def test_hashable(self) -> None:
        """Keys can be used in sets/dicts."""
        key = StreamKey(source="files", id="test.md", version="v1")

        # Should be hashable
        s = {key}
        assert key in s


class TestStreamItem:
    """Tests for StreamItem dataclass."""

    def test_create_with_explicit_version(self) -> None:
        """create() with explicit version uses that version."""
        item = StreamItem.create(
            source="files",
            id="test.md",
            value="content",
            version="explicit-v1",
        )

        assert item.key.source == "files"
        assert item.key.id == "test.md"
        assert item.key.version == "explicit-v1"
        assert item.value == "content"

    def test_create_auto_version(self) -> None:
        """create() without version computes hash from value."""
        item = StreamItem.create(
            source="files",
            id="test.md",
            value="content",
        )

        # Version should be computed
        assert item.key.version is not None
        assert len(item.key.version) > 0

    def test_auto_version_differs_by_value(self) -> None:
        """Different values produce different auto-versions."""
        item1 = StreamItem.create(source="test", id="1", value="content1")
        item2 = StreamItem.create(source="test", id="1", value="content2")

        assert item1.key.version != item2.key.version

    def test_produced_at_timestamp(self) -> None:
        """Items have produced_at timestamp."""
        item = StreamItem.create(source="test", id="1", value="x")

        assert item.produced_at > 0

    def test_map_value(self) -> None:
        """map_value transforms value and creates new item."""
        item = StreamItem.create(source="input", id="1", value="hello")

        result = item.map_value(str.upper, "output")

        assert result.value == "HELLO"
        assert result.key.source == "output"
        assert result.key.id == "1"

    def test_content_hash_attribute(self) -> None:
        """Uses content_hash attribute if available."""

        class MockPage:
            content_hash = "custom-hash-123"

        item = StreamItem.create(source="pages", id="page1", value=MockPage())

        assert "custom-hash" in item.key.version


class TestStreamBase:
    """Tests for Stream base class behavior."""

    def test_materialize_returns_values(self) -> None:
        """materialize() returns list of values."""
        from bengal.pipeline.streams import SourceStream

        items = [
            StreamItem.create("test", "1", "a"),
            StreamItem.create("test", "2", "b"),
            StreamItem.create("test", "3", "c"),
        ]
        stream = SourceStream(lambda: iter(items), name="test")

        result = stream.materialize()

        assert result == ["a", "b", "c"]

    def test_iterate_caches_items(self) -> None:
        """iterate() caches items by key."""
        from bengal.pipeline.streams import SourceStream

        call_count = 0

        def producer():
            nonlocal call_count
            call_count += 1
            return iter([StreamItem.create("test", "1", "value", version="v1")])

        stream = SourceStream(producer, name="test")

        # First iteration
        list(stream.iterate())
        assert call_count == 1

        # Second iteration still calls producer (cache is at item level, not producer)
        list(stream.iterate())
        assert call_count == 2

    def test_clear_cache(self) -> None:
        """clear_cache() empties the cache."""
        from bengal.pipeline.streams import SourceStream

        items = [StreamItem.create("test", "1", "a")]
        stream = SourceStream(lambda: iter(items), name="test")

        # Populate cache
        list(stream.iterate())
        assert len(stream._cache) == 1

        # Clear
        stream.clear_cache()

        assert len(stream._cache) == 0

    def test_disable_cache(self) -> None:
        """disable_cache() prevents caching."""
        from bengal.pipeline.streams import SourceStream

        items = [StreamItem.create("test", "1", "a")]
        stream = SourceStream(lambda: iter(items), name="test")
        stream.disable_cache()

        # Iterate
        list(stream.iterate())

        # Cache should be empty
        assert len(stream._cache) == 0

    def test_first(self) -> None:
        """first() returns first value."""
        from bengal.pipeline.streams import SourceStream

        items = [
            StreamItem.create("test", "1", "first"),
            StreamItem.create("test", "2", "second"),
        ]
        stream = SourceStream(lambda: iter(items), name="test")

        assert stream.first() == "first"

    def test_first_empty(self) -> None:
        """first() returns None for empty stream."""
        from bengal.pipeline.streams import SourceStream

        stream = SourceStream(lambda: iter([]), name="test")

        assert stream.first() is None

    def test_count(self) -> None:
        """count() returns item count."""
        from bengal.pipeline.streams import SourceStream

        items = [StreamItem.create("test", str(i), i) for i in range(5)]
        stream = SourceStream(lambda: iter(items), name="test")

        assert stream.count() == 5

    def test_run(self) -> None:
        """run() executes stream and returns count."""
        from bengal.pipeline.streams import SourceStream

        items = [StreamItem.create("test", str(i), i) for i in range(3)]
        stream = SourceStream(lambda: iter(items), name="test")

        count = stream.run()

        assert count == 3

    def test_for_each(self) -> None:
        """for_each() calls function for each value."""
        from bengal.pipeline.streams import SourceStream

        items = [
            StreamItem.create("test", "1", "a"),
            StreamItem.create("test", "2", "b"),
        ]
        stream = SourceStream(lambda: iter(items), name="test")

        collected: list[str] = []
        stream.for_each(collected.append)

        assert collected == ["a", "b"]
