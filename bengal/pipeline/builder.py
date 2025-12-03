"""
Pipeline builder for constructing declarative build pipelines.

The Pipeline class provides a fluent API for defining build pipelines
as a series of transformations on data streams.

Example:
    >>> pipeline = (
    ...     Pipeline("bengal-build")
    ...     .source("files", lambda: discover_files(content_dir))
    ...     .filter("markdown", lambda f: f.suffix == ".md")
    ...     .map("parse", parse_markdown)
    ...     .map("page", create_page)
    ...     .parallel(workers=4)
    ...     .collect("all_pages")
    ...     .map("with_nav", lambda pages: (pages, build_nav(pages)))
    ...     .flat_map("render", lambda args: render_pages(*args))
    ...     .for_each("write", write_output)
    ... )
    >>> result = pipeline.run()

Related:
    - bengal/pipeline/core.py - Base Stream class
    - bengal/pipeline/streams.py - Stream implementations
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from bengal.pipeline.core import Stream, StreamItem
from bengal.pipeline.streams import SourceStream
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """
    Result of pipeline execution.

    Contains metrics and any errors encountered during execution.

    Attributes:
        name: Pipeline name
        items_processed: Number of items that flowed through
        elapsed_seconds: Total execution time
        errors: List of (stage_name, item_key, exception) tuples
        stages_executed: Names of stages that ran
    """

    name: str
    items_processed: int
    elapsed_seconds: float
    errors: list[tuple[str, Any, Exception]] = field(default_factory=list)
    stages_executed: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0

    @property
    def items_per_second(self) -> float:
        """Processing rate."""
        if self.elapsed_seconds > 0:
            return self.items_processed / self.elapsed_seconds
        return 0.0

    def __str__(self) -> str:
        """Human-readable summary."""
        status = "✅" if self.success else f"❌ ({len(self.errors)} errors)"
        return (
            f"Pipeline '{self.name}': {status}\n"
            f"  Items: {self.items_processed}\n"
            f"  Time: {self.elapsed_seconds:.2f}s\n"
            f"  Rate: {self.items_per_second:.1f} items/s"
        )


class Pipeline:
    """
    Builder for constructing build pipelines.

    Pipelines are defined declaratively using a fluent API.
    Execution is deferred until `run()` is called.

    Example:
        >>> pipeline = (
        ...     Pipeline("build")
        ...     .source("files", discover_files)
        ...     .map("parse", parse_markdown)
        ...     .map("page", create_page)
        ...     .for_each("write", write_output)
        ... )
        >>> result = pipeline.run()

    Attributes:
        name: Pipeline name for logging and debugging
    """

    def __init__(self, name: str = "pipeline") -> None:
        """
        Initialize pipeline.

        Args:
            name: Pipeline name for logging
        """
        self.name = name
        self._stages: list[tuple[str, Stream[Any]]] = []
        self._current: Stream[Any] | None = None
        self._side_effects: list[tuple[str, Callable[[Any], None]]] = []

    def source(
        self,
        name: str,
        producer: Callable[[], Any],
    ) -> Pipeline:
        """
        Add a source stage that produces initial items.

        The producer function can return:
        - A list of items
        - An iterator/generator of items
        - Any iterable

        Args:
            name: Stage name for debugging and caching
            producer: Function that returns items

        Returns:
            Self for chaining

        Example:
            >>> pipeline.source("files", lambda: Path(".").glob("**/*.md"))
        """

        def make_items() -> Iterator[StreamItem[Any]]:
            result = producer()
            # Handle iterables
            if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                for i, item in enumerate(result):
                    yield StreamItem.create(
                        source=name,
                        id=self._get_item_id(item, i),
                        value=item,
                    )
            else:
                # Single item
                yield StreamItem.create(
                    source=name,
                    id="0",
                    value=result,
                )

        stream: Stream[Any] = SourceStream(make_items, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def map(self, name: str, fn: Callable[[Any], Any]) -> Pipeline:
        """
        Add a map transformation stage.

        Each input item is transformed by the function.

        Args:
            name: Stage name
            fn: Transformation function

        Returns:
            Self for chaining

        Example:
            >>> pipeline.map("parse", parse_markdown)
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.map(fn, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def filter(self, name: str, predicate: Callable[[Any], bool]) -> Pipeline:
        """
        Add a filter stage.

        Only items where predicate returns True pass through.

        Args:
            name: Stage name
            predicate: Filter function

        Returns:
            Self for chaining

        Example:
            >>> pipeline.filter("markdown", lambda f: f.suffix == ".md")
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.filter(predicate, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def flat_map(self, name: str, fn: Callable[[Any], Iterator[Any]]) -> Pipeline:
        """
        Add a flat_map stage.

        Each input item is transformed into multiple output items.

        Args:
            name: Stage name
            fn: Function returning iterator of new items

        Returns:
            Self for chaining

        Example:
            >>> pipeline.flat_map("split", lambda page: page.sections)
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.flat_map(fn, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def collect(self, name: str = "collect") -> Pipeline:
        """
        Collect all items into a single list.

        This is a barrier - all upstream items must complete
        before the list is emitted.

        Args:
            name: Stage name

        Returns:
            Self for chaining

        Example:
            >>> pipeline.collect("all_pages")
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.collect(name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def combine(self, *other_pipelines: Pipeline, name: str = "combine") -> Pipeline:
        """
        Combine with other pipelines.

        Collects this pipeline and all others, emitting a tuple.

        Args:
            other_pipelines: Other pipelines to combine with
            name: Stage name

        Returns:
            Self for chaining

        Example:
            >>> content_pipeline.combine(nav_pipeline, name="render_context")
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        other_streams = [p._current for p in other_pipelines if p._current is not None]
        stream = self._current.combine(*other_streams, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def parallel(self, workers: int = 4) -> Pipeline:
        """
        Enable parallel execution for the current stage.

        Effective for I/O-bound operations.

        Args:
            workers: Number of worker threads

        Returns:
            Self for chaining

        Example:
            >>> pipeline.map("render", render_page).parallel(workers=8)
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.parallel(workers)
        # Don't add to stages - just wraps current
        self._current = stream
        return self

    def cache(self, key_fn: Callable[[Any], str] | None = None) -> Pipeline:
        """
        Add explicit caching with optional custom key function.

        Args:
            key_fn: Optional function to compute cache key

        Returns:
            Self for chaining
        """
        if self._current is None:
            raise ValueError("Pipeline has no source - call .source() first")

        stream = self._current.cache(key_fn)
        self._current = stream
        return self

    def for_each(self, name: str, fn: Callable[[Any], None]) -> Pipeline:
        """
        Add a side-effect stage.

        The function is called for each item but doesn't transform it.
        Typically used for writing output.

        Args:
            name: Stage name
            fn: Side-effect function

        Returns:
            Self for chaining

        Example:
            >>> pipeline.for_each("write", write_to_disk)
        """
        self._side_effects.append((name, fn))
        return self

    def run(self) -> PipelineResult:
        """
        Execute the pipeline.

        Iterates through all items, executing side effects,
        and returns execution metrics.

        Returns:
            PipelineResult with metrics and any errors

        Raises:
            ValueError: If pipeline has no stages
        """
        if self._current is None:
            raise ValueError("Pipeline has no stages - call .source() first")

        logger.info(f"Running pipeline: {self.name}")
        start_time = time.time()

        count = 0
        errors: list[tuple[str, Any, Exception]] = []
        stages_executed = [name for name, _ in self._stages]

        try:
            for item in self._current.iterate():
                # Execute side effects
                for effect_name, fn in self._side_effects:
                    try:
                        fn(item.value)
                    except Exception as e:
                        errors.append((effect_name, item.key, e))
                        logger.error(f"Error in {effect_name} for {item.key}: {e}")
                count += 1

        except Exception as e:
            errors.append(("pipeline", None, e))
            logger.error(f"Pipeline error: {e}")

        elapsed = time.time() - start_time

        result = PipelineResult(
            name=self.name,
            items_processed=count,
            elapsed_seconds=elapsed,
            errors=errors,
            stages_executed=stages_executed,
        )

        if result.success:
            logger.info(f"Pipeline '{self.name}' complete: {count} items in {elapsed:.2f}s")
        else:
            logger.warning(f"Pipeline '{self.name}' finished with {len(errors)} errors")

        return result

    def _get_item_id(self, item: Any, index: int) -> str:
        """
        Get unique ID for an item.

        Tries common attributes, falls back to index.
        """
        # Try common path-like attributes
        for attr in ("path", "source_path", "file_path"):
            if hasattr(item, attr):
                value = getattr(item, attr)
                return str(value)

        # Try identity attributes
        for attr in ("id", "slug", "name"):
            if hasattr(item, attr):
                value = getattr(item, attr)
                return str(value)

        # Fall back to string representation or index
        if hasattr(item, "__fspath__"):
            return str(item)

        return str(index)

    def __repr__(self) -> str:
        """Debug representation."""
        stages = " → ".join(name for name, _ in self._stages)
        effects = ", ".join(name for name, _ in self._side_effects)
        return f"Pipeline({self.name!r}, stages=[{stages}], effects=[{effects}])"
