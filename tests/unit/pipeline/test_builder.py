"""
Unit tests for bengal.pipeline.builder - Pipeline builder API.

Tests:
    - Pipeline construction and fluent API
    - PipelineResult metrics
    - Error handling
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from bengal.pipeline.builder import Pipeline, PipelineResult


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_success_when_no_errors(self) -> None:
        """success is True when errors list is empty."""
        result = PipelineResult(
            name="test",
            items_processed=10,
            elapsed_seconds=1.0,
            errors=[],
            stages_executed=["source", "map"],
        )

        assert result.success is True

    def test_failure_when_errors(self) -> None:
        """success is False when errors list has items."""
        result = PipelineResult(
            name="test",
            items_processed=5,
            elapsed_seconds=1.0,
            errors=[("stage", "key", Exception("fail"))],
            stages_executed=["source"],
        )

        assert result.success is False

    def test_items_per_second(self) -> None:
        """items_per_second computes rate."""
        result = PipelineResult(
            name="test",
            items_processed=100,
            elapsed_seconds=2.0,
            errors=[],
            stages_executed=[],
        )

        assert result.items_per_second == 50.0

    def test_items_per_second_zero_time(self) -> None:
        """items_per_second returns 0 when elapsed is 0."""
        result = PipelineResult(
            name="test",
            items_processed=100,
            elapsed_seconds=0.0,
            errors=[],
            stages_executed=[],
        )

        assert result.items_per_second == 0.0

    def test_str_representation(self) -> None:
        """__str__ returns human-readable summary."""
        result = PipelineResult(
            name="my-build",
            items_processed=50,
            elapsed_seconds=2.5,
            errors=[],
            stages_executed=["source", "map", "write"],
        )

        output = str(result)

        assert "my-build" in output
        assert "50" in output
        assert "2.5" in output or "2.50" in output


class TestPipelineBuilder:
    """Tests for Pipeline builder API."""

    def test_requires_source(self) -> None:
        """Pipeline raises error if no source before operations."""
        pipeline = Pipeline("test")

        with pytest.raises(ValueError, match="no source"):
            pipeline.map("double", lambda x: x * 2)

    def test_source_from_list(self) -> None:
        """source() accepts list-returning function."""
        pipeline = Pipeline("test")
        pipeline.source("numbers", lambda: [1, 2, 3])

        result = pipeline.run()

        assert result.items_processed == 3

    def test_source_from_generator(self) -> None:
        """source() accepts generator function."""

        def gen() -> Iterator[int]:
            yield 1
            yield 2
            yield 3

        pipeline = Pipeline("test")
        pipeline.source("numbers", gen)

        result = pipeline.run()

        assert result.items_processed == 3

    def test_map_stage(self) -> None:
        """map() adds transformation stage."""
        collected: list[int] = []

        result = (
            Pipeline("test")
            .source("numbers", lambda: [1, 2, 3])
            .map("double", lambda x: x * 2)
            .for_each("collect", collected.append)
            .run()
        )

        assert result.success
        assert collected == [2, 4, 6]

    def test_filter_stage(self) -> None:
        """filter() adds filtering stage."""
        collected: list[int] = []

        result = (
            Pipeline("test")
            .source("numbers", lambda: [1, 2, 3, 4, 5])
            .filter("evens", lambda x: x % 2 == 0)
            .for_each("collect", collected.append)
            .run()
        )

        assert result.success
        assert collected == [2, 4]

    def test_flat_map_stage(self) -> None:
        """flat_map() adds expansion stage."""
        collected: list[str] = []

        result = (
            Pipeline("test")
            .source("csv", lambda: ["a,b", "c,d"])
            .flat_map("split", lambda s: s.split(","))
            .for_each("collect", collected.append)
            .run()
        )

        assert result.success
        assert collected == ["a", "b", "c", "d"]

    def test_collect_stage(self) -> None:
        """collect() aggregates into list."""
        collected: list[list[int]] = []

        result = (
            Pipeline("test")
            .source("numbers", lambda: [1, 2, 3])
            .collect("all")
            .for_each("collect", collected.append)
            .run()
        )

        assert result.success
        assert collected == [[1, 2, 3]]

    def test_parallel_stage(self) -> None:
        """parallel() enables concurrent execution."""
        collected: list[int] = []

        result = (
            Pipeline("test")
            .source("numbers", lambda: [1, 2, 3])
            .map("double", lambda x: x * 2)
            .parallel(workers=2)
            .for_each("collect", collected.append)
            .run()
        )

        assert result.success
        assert sorted(collected) == [2, 4, 6]

    def test_cache_stage(self) -> None:
        """cache() adds caching with custom key."""
        result = (
            Pipeline("test")
            .source("items", lambda: [{"id": "a"}, {"id": "b"}])
            .cache(key_fn=lambda x: x["id"])
            .run()
        )

        assert result.success
        assert result.items_processed == 2

    def test_stages_executed_tracking(self) -> None:
        """stages_executed lists all stage names."""
        result = (
            Pipeline("test")
            .source("input", lambda: [1, 2])
            .map("double", lambda x: x * 2)
            .filter("positive", lambda x: x > 0)
            .run()
        )

        assert result.stages_executed == ["input", "double", "positive"]

    def test_error_in_for_each(self) -> None:
        """Errors in for_each are captured."""

        def failing_effect(x: int) -> None:
            if x == 2:
                raise ValueError("Bad value")

        result = (
            Pipeline("test")
            .source("numbers", lambda: [1, 2, 3])
            .for_each("write", failing_effect)
            .run()
        )

        assert not result.success
        assert len(result.errors) == 1
        assert result.errors[0][0] == "write"

    def test_chained_fluent_api(self) -> None:
        """Full fluent API chain works."""
        collected: list[str] = []

        result = (
            Pipeline("build")
            .source("files", lambda: ["a.md", "b.txt", "c.md"])
            .filter("markdown", lambda f: f.endswith(".md"))
            .map("upper", str.upper)
            .for_each("log", collected.append)
            .run()
        )

        assert result.success
        assert collected == ["A.MD", "C.MD"]

    def test_repr(self) -> None:
        """__repr__ shows pipeline structure."""
        pipeline = (
            Pipeline("my-build")
            .source("files", lambda: [])
            .map("parse", lambda x: x)
            .filter("valid", lambda x: True)
        )

        output = repr(pipeline)

        assert "my-build" in output
        assert "files" in output

    def test_item_id_from_path_attribute(self) -> None:
        """Items with path attribute use it as ID."""

        class FakePath:
            def __init__(self, p: str) -> None:
                self.path = p

        items = [FakePath("/a/b.md"), FakePath("/c/d.md")]

        collected: list[str] = []

        (
            Pipeline("test")
            .source("files", lambda: items)
            .for_each("collect", lambda x: collected.append(x.path))
            .run()
        )

        assert collected == ["/a/b.md", "/c/d.md"]

    def test_item_id_from_fspath(self) -> None:
        """Path objects use __fspath__ for ID."""
        items = [Path("/a/b.md"), Path("/c/d.md")]

        result = Pipeline("test").source("files", lambda: items).run()

        assert result.items_processed == 2


class TestPipelineIntegration:
    """Integration tests for realistic pipeline patterns."""

    def test_file_processing_pipeline(self) -> None:
        """Simulates file → parse → transform → write pattern."""
        # Mock file discovery
        files = ["page1.md", "page2.md", "readme.txt"]

        # Mock parser
        def parse(filename: str) -> dict:
            return {"name": filename, "content": f"Content of {filename}"}

        # Mock transform
        def transform(doc: dict) -> dict:
            return {**doc, "title": doc["name"].upper()}

        # Collect outputs
        outputs: list[dict] = []

        result = (
            Pipeline("build-site")
            .source("files", lambda: files)
            .filter("markdown", lambda f: f.endswith(".md"))
            .map("parse", parse)
            .map("transform", transform)
            .for_each("write", outputs.append)
            .run()
        )

        assert result.success
        assert len(outputs) == 2
        assert outputs[0]["title"] == "PAGE1.MD"
        assert outputs[1]["title"] == "PAGE2.MD"

    def test_aggregation_pipeline(self) -> None:
        """Simulates collect → process-all → emit pattern."""
        numbers = [1, 2, 3, 4, 5]

        outputs: list[dict] = []

        result = (
            Pipeline("aggregate")
            .source("numbers", lambda: numbers)
            .collect("all")
            .map(
                "stats",
                lambda nums: {
                    "sum": sum(nums),
                    "count": len(nums),
                    "avg": sum(nums) / len(nums),
                },
            )
            .for_each("emit", outputs.append)
            .run()
        )

        assert result.success
        assert len(outputs) == 1
        assert outputs[0] == {"sum": 15, "count": 5, "avg": 3.0}


