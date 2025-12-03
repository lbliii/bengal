"""
Unit tests for bengal.pipeline.streams - concrete stream implementations.

Tests:
    - SourceStream: Initial item production
    - MapStream: Value transformation
    - FilterStream: Predicate filtering
    - FlatMapStream: One-to-many transformation
    - CollectStream: Aggregation to list
    - CombineStream: Multiple stream combination
    - ParallelStream: Concurrent execution
    - CachedStream: Custom cache keys
"""

from __future__ import annotations

import time
from collections.abc import Iterator

from bengal.pipeline.core import StreamItem
from bengal.pipeline.streams import (
    CachedStream,
    CollectStream,
    CombineStream,
    FilterStream,
    FlatMapStream,
    MapStream,
    ParallelStream,
    SourceStream,
)


class TestSourceStream:
    """Tests for SourceStream."""

    def test_produces_items(self) -> None:
        """SourceStream yields items from producer function."""
        items = [
            StreamItem.create("test", "1", "a"),
            StreamItem.create("test", "2", "b"),
        ]

        stream = SourceStream(lambda: iter(items), name="test-source")

        result = stream.materialize()
        assert result == ["a", "b"]

    def test_name_is_set(self) -> None:
        """Stream name is set from constructor."""
        stream = SourceStream(lambda: iter([]), name="my-source")

        assert stream.name == "my-source"


class TestMapStream:
    """Tests for MapStream."""

    def test_transforms_values(self) -> None:
        """MapStream applies function to each value."""
        items = [
            StreamItem.create("in", "1", 1),
            StreamItem.create("in", "2", 2),
            StreamItem.create("in", "3", 3),
        ]
        source = SourceStream(lambda: iter(items), name="numbers")

        stream = MapStream(source, lambda x: x * 2, name="doubled")

        result = stream.materialize()
        assert result == [2, 4, 6]

    def test_preserves_item_ids(self) -> None:
        """Transformed items keep the same id."""
        items = [StreamItem.create("in", "my-id", "value")]
        source = SourceStream(lambda: iter(items), name="in")

        stream = MapStream(source, str.upper, name="out")

        for item in stream.iterate():
            assert item.key.id == "my-id"
            assert item.key.source == "out"

    def test_fluent_api(self) -> None:
        """map() method returns MapStream."""
        items = [StreamItem.create("in", "1", 5)]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.map(lambda x: x + 1)

        assert isinstance(stream, MapStream)
        assert stream.materialize() == [6]


class TestFilterStream:
    """Tests for FilterStream."""

    def test_filters_by_predicate(self) -> None:
        """FilterStream only passes items where predicate is True."""
        items = [
            StreamItem.create("in", "1", 1),
            StreamItem.create("in", "2", 2),
            StreamItem.create("in", "3", 3),
            StreamItem.create("in", "4", 4),
        ]
        source = SourceStream(lambda: iter(items), name="numbers")

        stream = FilterStream(source, lambda x: x % 2 == 0, name="evens")

        result = stream.materialize()
        assert result == [2, 4]

    def test_empty_when_none_match(self) -> None:
        """Empty result when no items match predicate."""
        items = [
            StreamItem.create("in", "1", 1),
            StreamItem.create("in", "2", 2),
        ]
        source = SourceStream(lambda: iter(items), name="numbers")

        stream = FilterStream(source, lambda x: x > 10, name="big")

        result = stream.materialize()
        assert result == []

    def test_fluent_api(self) -> None:
        """filter() method returns FilterStream."""
        items = [
            StreamItem.create("in", "1", "yes"),
            StreamItem.create("in", "2", "no"),
        ]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.filter(lambda x: x == "yes")

        assert isinstance(stream, FilterStream)
        assert stream.materialize() == ["yes"]


class TestFlatMapStream:
    """Tests for FlatMapStream."""

    def test_expands_items(self) -> None:
        """FlatMapStream turns each input into multiple outputs."""
        items = [
            StreamItem.create("in", "1", "a,b"),
            StreamItem.create("in", "2", "c,d,e"),
        ]
        source = SourceStream(lambda: iter(items), name="csv")

        def split(s: str) -> Iterator[str]:
            yield from s.split(",")

        stream = FlatMapStream(source, split, name="split")

        result = stream.materialize()
        assert result == ["a", "b", "c", "d", "e"]

    def test_generates_unique_ids(self) -> None:
        """Expanded items have unique IDs based on parent + index."""
        items = [StreamItem.create("in", "parent", [1, 2, 3])]
        source = SourceStream(lambda: iter(items), name="in")

        stream = FlatMapStream(source, iter, name="expand")

        result = list(stream.iterate())
        ids = [item.key.id for item in result]

        assert ids == ["parent:0", "parent:1", "parent:2"]

    def test_fluent_api(self) -> None:
        """flat_map() method returns FlatMapStream."""
        items = [StreamItem.create("in", "1", [1, 2])]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.flat_map(iter)

        assert isinstance(stream, FlatMapStream)
        assert stream.materialize() == [1, 2]


class TestCollectStream:
    """Tests for CollectStream."""

    def test_collects_to_list(self) -> None:
        """CollectStream gathers all items into one list."""
        items = [
            StreamItem.create("in", "1", "a"),
            StreamItem.create("in", "2", "b"),
            StreamItem.create("in", "3", "c"),
        ]
        source = SourceStream(lambda: iter(items), name="letters")

        stream = CollectStream(source, name="all")

        result = stream.materialize()
        assert result == [["a", "b", "c"]]

    def test_empty_collection(self) -> None:
        """Empty input produces empty list."""
        source = SourceStream(lambda: iter([]), name="empty")

        stream = CollectStream(source, name="all")

        result = stream.materialize()
        assert result == [[]]

    def test_single_item_output(self) -> None:
        """CollectStream produces exactly one StreamItem."""
        items = [
            StreamItem.create("in", "1", "a"),
            StreamItem.create("in", "2", "b"),
        ]
        source = SourceStream(lambda: iter(items), name="in")

        stream = CollectStream(source, name="all")

        result = list(stream.iterate())
        assert len(result) == 1
        assert result[0].key.id == "all"

    def test_fluent_api(self) -> None:
        """collect() method returns CollectStream."""
        items = [StreamItem.create("in", "1", 1)]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.collect()

        assert isinstance(stream, CollectStream)


class TestCombineStream:
    """Tests for CombineStream."""

    def test_combines_two_streams(self) -> None:
        """CombineStream produces tuple of collected results."""
        items1 = [StreamItem.create("s1", "1", "a")]
        items2 = [StreamItem.create("s2", "1", "b")]

        stream1 = SourceStream(lambda: iter(items1), name="s1")
        stream2 = SourceStream(lambda: iter(items2), name="s2")

        combined = CombineStream(stream1, stream2, name="combo")

        result = combined.materialize()
        assert len(result) == 1
        # Single items come through as values, not lists
        assert result[0] == ("a", "b")

    def test_combines_multiple_items(self) -> None:
        """Multiple items per stream come through as lists."""
        items1 = [
            StreamItem.create("s1", "1", "a"),
            StreamItem.create("s1", "2", "b"),
        ]
        items2 = [StreamItem.create("s2", "1", "x")]

        stream1 = SourceStream(lambda: iter(items1), name="s1")
        stream2 = SourceStream(lambda: iter(items2), name="s2")

        combined = CombineStream(stream1, stream2, name="combo")

        result = combined.materialize()
        assert len(result) == 1
        # Multiple items come through as list
        assert result[0] == (["a", "b"], "x")

    def test_fluent_api(self) -> None:
        """combine() method returns CombineStream."""
        items1 = [StreamItem.create("s1", "1", 1)]
        items2 = [StreamItem.create("s2", "1", 2)]

        stream1 = SourceStream(lambda: iter(items1), name="s1")
        stream2 = SourceStream(lambda: iter(items2), name="s2")

        combined = stream1.combine(stream2)

        assert isinstance(combined, CombineStream)


class TestParallelStream:
    """Tests for ParallelStream."""

    def test_parallel_execution(self) -> None:
        """ParallelStream executes in parallel and produces correct values."""
        items = [
            StreamItem.create("in", "1", 1),
            StreamItem.create("in", "2", 2),
            StreamItem.create("in", "3", 3),
        ]
        source = SourceStream(lambda: iter(items), name="in")

        def slow_double(x: int) -> int:
            time.sleep(0.02)  # 20ms
            return x * 2

        # With parallel execution
        mapped = MapStream(source, slow_double, name="doubled")
        parallel = ParallelStream(mapped, workers=3)
        result = parallel.materialize()

        # Verify values are correct (order may vary)
        assert sorted(result) == [2, 4, 6]

    def test_preserves_values(self) -> None:
        """ParallelStream produces same values as sequential."""
        items = [StreamItem.create("in", str(i), i) for i in range(10)]
        source = SourceStream(lambda: iter(items), name="in")
        mapped = MapStream(source, lambda x: x * 2, name="doubled")

        stream = ParallelStream(mapped, workers=4)

        result = stream.materialize()
        assert sorted(result) == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    def test_fluent_api(self) -> None:
        """parallel() method returns ParallelStream."""
        items = [StreamItem.create("in", "1", 1)]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.parallel(workers=2)

        assert isinstance(stream, ParallelStream)


class TestCachedStream:
    """Tests for CachedStream."""

    def test_custom_key_function(self) -> None:
        """CachedStream uses custom key function."""
        items = [
            StreamItem.create("in", "1", {"path": "/a/b.md", "content": "x"}),
        ]
        source = SourceStream(lambda: iter(items), name="in")

        stream = CachedStream(source, key_fn=lambda x: x["path"])

        result = list(stream.iterate())
        assert result[0].key.id == "/a/b.md"

    def test_fluent_api(self) -> None:
        """cache() method returns CachedStream."""
        items = [StreamItem.create("in", "1", "value")]
        source = SourceStream(lambda: iter(items), name="in")

        stream = source.cache()

        assert isinstance(stream, CachedStream)


class TestChainedOperators:
    """Tests for chained stream operations."""

    def test_map_filter_chain(self) -> None:
        """Chain map → filter."""
        items = [StreamItem.create("in", str(i), i) for i in range(1, 6)]
        source = SourceStream(lambda: iter(items), name="numbers")

        result = source.map(lambda x: x * 2).filter(lambda x: x > 5).materialize()

        assert result == [6, 8, 10]

    def test_filter_map_collect(self) -> None:
        """Chain filter → map → collect."""
        items = [StreamItem.create("in", str(i), i) for i in range(5)]
        source = SourceStream(lambda: iter(items), name="in")

        result = source.filter(lambda x: x % 2 == 0).map(str).collect().materialize()

        assert result == [["0", "2", "4"]]

    def test_complex_chain(self) -> None:
        """Complex pipeline with multiple operations."""
        items = [
            StreamItem.create("in", "1", "a,b"),
            StreamItem.create("in", "2", "c,d"),
        ]
        source = SourceStream(lambda: iter(items), name="csv")

        result = (
            source.flat_map(lambda s: s.split(","))
            .map(str.upper)
            .filter(lambda s: s != "B")
            .collect()
            .materialize()
        )

        assert result == [["A", "C", "D"]]
