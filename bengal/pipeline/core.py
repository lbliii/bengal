"""
Core stream primitives for the reactive dataflow pipeline.

This module defines the foundational types for Bengal's reactive build system:

- StreamKey: Unique identifier for cache-friendly stream items
- StreamItem: A single item flowing through the pipeline with metadata
- Stream: Abstract base class for all stream types

Design Principles:
    - Streams are lazy: transformations define a computation graph
      but don't execute until materialized
    - Items have keys for automatic caching and invalidation
    - Version tracking enables fine-grained incremental builds

Related:
    - bengal/pipeline/streams.py - Concrete stream implementations
    - bengal/pipeline/builder.py - Pipeline builder API
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.pipeline.streams import (
        CachedStream,
        CollectStream,
        CombineStream,
        FilterStream,
        FlatMapStream,
        MapStream,
        ParallelStream,
    )


@dataclass(frozen=True)
class StreamKey:
    """
    Unique identifier for a stream item.

    StreamKeys enable:
    - Cache lookup across builds
    - Version-based invalidation
    - Dependency tracking

    Attributes:
        source: Name of the stream that produced this item
        id: Unique identifier within the source stream
        version: Content hash or timestamp for invalidation
    """

    source: str
    id: str
    version: str

    def __str__(self) -> str:
        """Human-readable key representation."""
        return f"{self.source}:{self.id}@{self.version[:8]}"

    def with_version(self, version: str) -> StreamKey:
        """Create new key with updated version."""
        return StreamKey(source=self.source, id=self.id, version=version)


@dataclass
class StreamItem[T]:
    """
    A single item flowing through the pipeline.

    Each item carries:
    - A unique key for caching
    - The actual value
    - Timestamp for debugging/metrics

    Attributes:
        key: Unique identifier for caching and invalidation
        value: The actual data payload
        produced_at: Unix timestamp when this item was created
    """

    key: StreamKey
    value: T
    produced_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        source: str,
        id: str,
        value: T,
        version: str | None = None,
    ) -> StreamItem[T]:
        """
        Create a stream item with automatic version computation.

        Args:
            source: Name of the producing stream
            id: Unique identifier within the stream
            value: The actual data
            version: Content version (computed from value hash if not provided)

        Returns:
            New StreamItem instance
        """
        if version is None:
            version = cls._compute_hash(value)
        return cls(
            key=StreamKey(source=source, id=id, version=version),
            value=value,
        )

    @staticmethod
    def _compute_hash(value: Any) -> str:
        """
        Compute content hash for version tracking.

        Uses value's hash if available, otherwise string representation.
        """
        try:
            if hasattr(value, "content_hash"):
                # Use content_hash if available (e.g., Page objects)
                return str(value.content_hash)[:16]
            if hasattr(value, "__hash__") and value.__hash__ is not None:
                return hashlib.sha256(str(hash(value)).encode()).hexdigest()[:16]
        except TypeError:
            # Value is unhashable; fall through to string-based hash
            pass
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

    def map_value[U](self, fn: Callable[[T], U], new_source: str) -> StreamItem[U]:
        """
        Transform the value while preserving the item structure.

        Args:
            fn: Transformation function
            new_source: Source name for the new item

        Returns:
            New StreamItem with transformed value
        """
        new_value = fn(self.value)
        return StreamItem.create(
            source=new_source,
            id=self.key.id,
            value=new_value,
        )


class Stream[T](ABC):
    """
    Abstract base class for reactive streams.

    Streams are lazy - they define a computation graph but don't
    execute until `run()` or `materialize()` is called.

    Subclasses must implement `_produce()` to generate items.

    Attributes:
        name: Human-readable name for debugging and caching
    """

    def __init__(self, name: str | None = None) -> None:
        """
        Initialize stream.

        Args:
            name: Optional name (defaults to class name)
        """
        self.name = name or self.__class__.__name__
        self._cache: dict[StreamKey, StreamItem[T]] = {}
        self._cache_enabled = True

    @abstractmethod
    def _produce(self) -> Iterator[StreamItem[T]]:
        """
        Produce items from this stream.

        Subclasses implement this to define stream behavior.

        Yields:
            StreamItem instances
        """
        ...

    def iterate(self) -> Iterator[StreamItem[T]]:
        """
        Iterate over stream items with caching.

        Items are cached by key. If an item with the same key and version
        is requested again, the cached value is returned.

        Yields:
            StreamItem instances (from cache or fresh)
        """
        for item in self._produce():
            if self._cache_enabled:
                cached = self._cache.get(item.key)
                if cached is not None and cached.key.version == item.key.version:
                    yield cached
                    continue
                self._cache[item.key] = item
            yield item

    def materialize(self) -> list[T]:
        """
        Execute stream and return all values.

        This is a terminal operation that triggers stream execution.

        Returns:
            List of all values produced by the stream
        """
        return [item.value for item in self.iterate()]

    def clear_cache(self) -> None:
        """Clear the stream's internal cache."""
        self._cache.clear()

    def disable_cache(self) -> Stream[T]:
        """Disable caching for this stream."""
        self._cache_enabled = False
        return self

    # =========================================================================
    # Transformation Operators
    # =========================================================================

    def map[U](self, fn: Callable[[T], U], name: str | None = None) -> MapStream[T, U]:
        """
        Transform each item in the stream.

        Args:
            fn: Transformation function applied to each value
            name: Optional name for the new stream

        Returns:
            New stream with transformed values

        Example:
            >>> stream.map(lambda x: x * 2)
        """
        from bengal.pipeline.streams import MapStream

        return MapStream(self, fn, name=name or f"{self.name}.map")

    def filter(self, predicate: Callable[[T], bool], name: str | None = None) -> FilterStream[T]:
        """
        Filter items based on predicate.

        Args:
            predicate: Function returning True for items to keep
            name: Optional name for the new stream

        Returns:
            New stream with filtered values

        Example:
            >>> stream.filter(lambda x: x > 0)
        """
        from bengal.pipeline.streams import FilterStream

        return FilterStream(self, predicate, name=name or f"{self.name}.filter")

    def flat_map[U](
        self, fn: Callable[[T], Iterator[U]], name: str | None = None
    ) -> FlatMapStream[T, U]:
        """
        Transform each item into multiple items.

        Args:
            fn: Function returning iterator of new values
            name: Optional name for the new stream

        Returns:
            New stream with flattened values

        Example:
            >>> stream.flat_map(lambda x: [x, x + 1])
        """
        from bengal.pipeline.streams import FlatMapStream

        return FlatMapStream(self, fn, name=name or f"{self.name}.flat_map")

    def collect(self, name: str | None = None) -> CollectStream[T]:
        """
        Collect all items into a single list.

        This is a barrier operation - all upstream items must complete
        before the collected list is emitted.

        Args:
            name: Optional name for the new stream

        Returns:
            Stream emitting a single list of all values

        Example:
            >>> stream.collect()  # Emits [item1, item2, ...]
        """
        from bengal.pipeline.streams import CollectStream

        return CollectStream(self, name=name or f"{self.name}.collect")

    def combine(self, *others: Stream[Any], name: str | None = None) -> CombineStream:
        """
        Combine with other streams.

        Collects this stream and all others, then emits a tuple of results.

        Args:
            others: Other streams to combine with
            name: Optional name for the new stream

        Returns:
            Stream emitting tuple of combined results

        Example:
            >>> pages.combine(nav).map(lambda args: render(*args))
        """
        from bengal.pipeline.streams import CombineStream

        return CombineStream(self, *others, name=name or f"{self.name}.combine")

    def parallel(self, workers: int = 4) -> ParallelStream[T]:
        """
        Mark stream for parallel execution.

        Args:
            workers: Number of worker threads

        Returns:
            Stream marked for parallel execution
        """
        from bengal.pipeline.streams import ParallelStream

        return ParallelStream(self, workers)

    def cache(self, key_fn: Callable[[T], str] | None = None) -> CachedStream[T]:
        """
        Add explicit caching with custom key function.

        Args:
            key_fn: Optional function to compute cache key from value

        Returns:
            Stream with explicit caching
        """
        from bengal.pipeline.streams import CachedStream

        return CachedStream(self, key_fn)

    # =========================================================================
    # Terminal Operators
    # =========================================================================

    def for_each(self, fn: Callable[[T], None]) -> None:
        """
        Execute function for each item (side effect).

        This is a terminal operation that triggers stream execution.

        Args:
            fn: Function to call for each value
        """
        for item in self.iterate():
            fn(item.value)

    def run(self) -> int:
        """
        Execute stream and return count of items processed.

        This is a terminal operation that triggers stream execution.

        Returns:
            Number of items processed
        """
        count = 0
        for _ in self.iterate():
            count += 1
        return count

    def first(self) -> T | None:
        """
        Get first item from stream.

        Returns:
            First value or None if stream is empty
        """
        for item in self.iterate():
            return item.value
        return None

    def count(self) -> int:
        """
        Count items in stream.

        Returns:
            Number of items
        """
        return sum(1 for _ in self.iterate())
