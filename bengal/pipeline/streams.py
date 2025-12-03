"""
Concrete stream implementations for the reactive dataflow pipeline.

This module provides:
- SourceStream: Entry point that produces items from a function
- MapStream: Transforms each item
- FilterStream: Filters items based on predicate
- FlatMapStream: Transforms each item into multiple items
- CollectStream: Collects all items into a list
- CombineStream: Combines multiple streams
- ParallelStream: Marks stream for parallel execution
- CachedStream: Adds explicit disk caching

Related:
    - bengal/pipeline/core.py - Base Stream class and StreamItem
    - bengal/pipeline/builder.py - Pipeline builder API
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from bengal.pipeline.core import Stream, StreamItem, StreamKey


class SourceStream[T](Stream[T]):
    """
    Stream that produces items from a source function.

    This is the entry point for pipelines - it produces initial items
    that flow through subsequent transformations.

    Example:
        >>> def discover_files():
        ...     for path in Path(".").glob("**/*.md"):
        ...         yield StreamItem.create("files", str(path), path)
        >>> stream = SourceStream(discover_files, name="files")
    """

    def __init__(
        self,
        producer: Callable[[], Iterator[StreamItem[T]]],
        name: str = "source",
    ) -> None:
        """
        Initialize source stream.

        Args:
            producer: Function that yields StreamItems
            name: Stream name for debugging and caching
        """
        super().__init__(name)
        self._producer = producer

    def _produce(self) -> Iterator[StreamItem[T]]:
        """Produce items from the source function."""
        yield from self._producer()


class MapStream[T, U](Stream[U]):
    """
    Stream that transforms each item.

    Each input item is transformed by the provided function,
    producing one output item per input.

    Example:
        >>> stream.map(lambda x: x.upper())
    """

    def __init__(
        self,
        upstream: Stream[T],
        fn: Callable[[T], U],
        name: str = "map",
    ) -> None:
        """
        Initialize map stream.

        Args:
            upstream: Source stream
            fn: Transformation function
            name: Stream name
        """
        super().__init__(name)
        self._upstream = upstream
        self._fn = fn

    def _produce(self) -> Iterator[StreamItem[U]]:
        """Transform each upstream item."""
        for item in self._upstream.iterate():
            result = self._fn(item.value)
            yield StreamItem.create(
                source=self.name,
                id=item.key.id,
                value=result,
            )


class FilterStream[T](Stream[T]):
    """
    Stream that filters items based on predicate.

    Only items where predicate returns True are passed through.

    Example:
        >>> stream.filter(lambda x: x.endswith(".md"))
    """

    def __init__(
        self,
        upstream: Stream[T],
        predicate: Callable[[T], bool],
        name: str = "filter",
    ) -> None:
        """
        Initialize filter stream.

        Args:
            upstream: Source stream
            predicate: Function returning True for items to keep
            name: Stream name
        """
        super().__init__(name)
        self._upstream = upstream
        self._predicate = predicate

    def _produce(self) -> Iterator[StreamItem[T]]:
        """Filter upstream items."""
        for item in self._upstream.iterate():
            if self._predicate(item.value):
                yield item


class FlatMapStream[T, U](Stream[U]):
    """
    Stream that transforms each item into multiple items.

    The transformation function returns an iterator, and all
    results are flattened into the output stream.

    Example:
        >>> stream.flat_map(lambda x: x.split(","))
    """

    def __init__(
        self,
        upstream: Stream[T],
        fn: Callable[[T], Iterator[U]],
        name: str = "flat_map",
    ) -> None:
        """
        Initialize flat_map stream.

        Args:
            upstream: Source stream
            fn: Function returning iterator of new values
            name: Stream name
        """
        super().__init__(name)
        self._upstream = upstream
        self._fn = fn

    def _produce(self) -> Iterator[StreamItem[U]]:
        """Transform each upstream item into multiple items."""
        for item in self._upstream.iterate():
            for i, result in enumerate(self._fn(item.value)):
                yield StreamItem.create(
                    source=self.name,
                    id=f"{item.key.id}:{i}",
                    value=result,
                )


class CollectStream[T](Stream[list[T]]):
    """
    Stream that collects all items into a single list.

    This is a barrier operation - all upstream items must complete
    before the collected list is emitted as a single item.

    Example:
        >>> stream.collect()  # Emits one item: [all, values, here]
    """

    def __init__(
        self,
        upstream: Stream[T],
        name: str = "collect",
    ) -> None:
        """
        Initialize collect stream.

        Args:
            upstream: Source stream
            name: Stream name
        """
        super().__init__(name)
        self._upstream = upstream

    def _produce(self) -> Iterator[StreamItem[list[T]]]:
        """Collect all upstream items into a list."""
        items = list(self._upstream.iterate())
        values = [item.value for item in items]

        # Version is hash of all item versions combined
        if items:
            versions = ":".join(item.key.version for item in items)
            version = hashlib.sha256(versions.encode()).hexdigest()[:16]
        else:
            version = "empty"

        yield StreamItem(
            key=StreamKey(source=self.name, id="all", version=version),
            value=values,
        )


class CombineStream(Stream[tuple[Any, ...]]):
    """
    Stream that combines multiple streams.

    Collects all upstream streams and emits a single tuple containing
    the collected results from each stream.

    Example:
        >>> pages.combine(navigation, config)
        # Emits: ([pages], navigation_data, config_data)
    """

    def __init__(
        self,
        *upstreams: Stream[Any],
        name: str = "combine",
    ) -> None:
        """
        Initialize combine stream.

        Args:
            upstreams: Streams to combine
            name: Stream name
        """
        super().__init__(name)
        self._upstreams = upstreams

    def _produce(self) -> Iterator[StreamItem[tuple[Any, ...]]]:
        """Collect all upstreams and combine into tuple."""
        # Collect each upstream
        collected: list[list[StreamItem[Any]]] = []
        for stream in self._upstreams:
            items = list(stream.iterate())
            collected.append(items)

        # If any stream is empty, yield empty tuple
        if not all(collected):
            yield StreamItem(
                key=StreamKey(source=self.name, id="combined", version="empty"),
                value=tuple(),
            )
            return

        # Extract values - if collected has single item, use that value
        # otherwise use the list of values
        values: list[Any] = []
        versions: list[str] = []

        for items in collected:
            if len(items) == 1:
                values.append(items[0].value)
                versions.append(items[0].key.version)
            else:
                # Multiple items - use list of values
                values.append([item.value for item in items])
                versions.append(
                    hashlib.sha256(
                        ":".join(item.key.version for item in items).encode()
                    ).hexdigest()[:16]
                )

        version = hashlib.sha256(":".join(versions).encode()).hexdigest()[:16]

        yield StreamItem(
            key=StreamKey(source=self.name, id="combined", version=version),
            value=tuple(values),
        )


class ParallelStream[T](Stream[T]):
    """
    Stream that executes upstream transformations in parallel.

    Uses a thread pool to process items concurrently.

    Note:
        Due to Python's GIL, this is most effective for I/O-bound
        operations. For CPU-bound work, consider ProcessPoolExecutor.

    Example:
        >>> stream.map(expensive_io_operation).parallel(workers=8)
    """

    def __init__(
        self,
        upstream: Stream[T],
        workers: int = 4,
    ) -> None:
        """
        Initialize parallel stream.

        Args:
            upstream: Source stream
            workers: Number of worker threads
        """
        super().__init__(f"{upstream.name}.parallel")
        self._upstream = upstream
        self._workers = workers

    def _produce(self) -> Iterator[StreamItem[T]]:
        """
        Execute upstream MapStream transformation in parallel.

        If upstream is a MapStream, extracts its source items and transformation
        function, then applies the function in parallel using ThreadPoolExecutor.
        For other stream types, just passes through items as-is.
        """
        # If upstream is a MapStream, parallelize the transformation
        if isinstance(self._upstream, MapStream):
            yield from self._parallel_map()
        else:
            # For other streams, just iterate normally
            yield from self._upstream.iterate()

    def _parallel_map(self) -> Iterator[StreamItem[T]]:
        """Execute map transformation in parallel using ThreadPoolExecutor."""
        upstream_map = self._upstream
        if not isinstance(upstream_map, MapStream):
            yield from upstream_map.iterate()
            return

        # Get source items BEFORE transformation (from map's upstream)
        source_items = list(upstream_map._upstream.iterate())
        if not source_items:
            return

        fn = upstream_map._fn
        name = upstream_map.name

        results: dict[str, StreamItem[T]] = {}

        with ThreadPoolExecutor(max_workers=self._workers) as executor:
            # Submit all transformations in parallel
            futures = {executor.submit(fn, item.value): item for item in source_items}

            # Collect results as they complete
            for future in as_completed(futures):
                source_item = futures[future]
                try:
                    result = future.result()
                    result_item = StreamItem.create(
                        source=name,
                        id=source_item.key.id,
                        value=result,
                    )
                    results[source_item.key.id] = result_item
                except Exception as e:
                    # Re-raise with context
                    raise RuntimeError(
                        f"Parallel execution failed for {source_item.key}: {e}"
                    ) from e

        # Yield in original order (for deterministic output)
        for item in source_items:
            if item.key.id in results:
                yield results[item.key.id]


class CachedStream[T](Stream[T]):
    """
    Stream with explicit caching using custom key function.

    Allows specifying a custom key function for cache lookups,
    enabling more control over cache behavior.

    Example:
        >>> stream.cache(key_fn=lambda page: page.source_path)
    """

    def __init__(
        self,
        upstream: Stream[T],
        key_fn: Callable[[T], str] | None = None,
    ) -> None:
        """
        Initialize cached stream.

        Args:
            upstream: Source stream
            key_fn: Optional function to compute cache key from value
        """
        super().__init__(f"{upstream.name}.cached")
        self._upstream = upstream
        self._key_fn = key_fn

    def _produce(self) -> Iterator[StreamItem[T]]:
        """Pass through upstream items with caching."""
        for item in self._upstream.iterate():
            # If custom key function provided, rekey the item
            if self._key_fn:
                custom_key = self._key_fn(item.value)
                new_key = StreamKey(
                    source=self.name,
                    id=custom_key,
                    version=item.key.version,
                )
                yield StreamItem(
                    key=new_key,
                    value=item.value,
                    produced_at=item.produced_at,
                )
            else:
                yield item
