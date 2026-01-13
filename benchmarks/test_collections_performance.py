"""
Performance benchmarks for collections algorithm operations.

Tests bottleneck operations identified in RFC: Collections Algorithm Optimization:
1. get_collection_for_path() - O(C × P) linear scan of all collections
2. SchemaValidator.validate() with nested dataclasses - unbounded recursion depth

Run with:
    pytest benchmarks/test_collections_performance.py -v --benchmark-only
    pytest benchmarks/test_collections_performance.py -v  # Without benchmark plugin

This establishes baseline measurements before optimization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from bengal.collections import CollectionConfig, SchemaValidator, define_collection
from bengal.collections.loader import (
    build_collection_trie,
    get_collection_for_path,
)

# ---------------------------------------------------------------------------
# Synthetic Data Generators
# ---------------------------------------------------------------------------


def generate_collections(num_collections: int) -> dict[str, CollectionConfig[Any]]:
    """
    Generate synthetic collection configurations.

    Args:
        num_collections: Number of collections to generate

    Returns:
        Dictionary mapping collection names to CollectionConfig instances
    
    Note:
        Directory paths are relative to content_root (typically "content/"),
        so we use "section_N" not "content/section_N".
    """

    @dataclass
    class GenericSchema:
        title: str
        count: int = 0

    return {
        f"collection_{i}": define_collection(
            schema=GenericSchema,
            directory=f"section_{i}",  # Relative to content_root, not including it
        )
        for i in range(num_collections)
    }


def generate_file_paths(
    num_files: int,
    num_collections: int,
) -> list[Path]:
    """
    Generate synthetic file paths distributed across collections.

    Args:
        num_files: Total number of file paths to generate
        num_collections: Number of collections to distribute files across

    Returns:
        List of Path objects representing content files
    """
    paths = []
    for i in range(num_files):
        collection_idx = i % num_collections
        paths.append(Path(f"content/section_{collection_idx}/nested/post_{i:05d}.md"))
    return paths


# Pre-defined nested schemas for depth testing
# (avoids get_type_hints issues with dynamically generated schemas)


@dataclass
class BenchDepth1:
    """Flat schema (depth 1)."""

    value: str


@dataclass
class BenchDepth2:
    """Schema with 1 level of nesting."""

    nested: BenchDepth1
    name: str = ""


@dataclass
class BenchDepth3:
    """Schema with 2 levels of nesting."""

    nested: BenchDepth2
    name: str = ""


@dataclass
class BenchDepth4:
    """Schema with 3 levels of nesting."""

    nested: BenchDepth3
    name: str = ""


@dataclass
class BenchDepth5:
    """Schema with 4 levels of nesting."""

    nested: BenchDepth4
    name: str = ""


@dataclass
class BenchDepth6:
    """Schema with 5 levels of nesting."""

    nested: BenchDepth5
    name: str = ""


@dataclass
class BenchDepth7:
    """Schema with 6 levels of nesting."""

    nested: BenchDepth6
    name: str = ""


@dataclass
class BenchDepth8:
    """Schema with 7 levels of nesting."""

    nested: BenchDepth7
    name: str = ""


@dataclass
class BenchDepth9:
    """Schema with 8 levels of nesting."""

    nested: BenchDepth8
    name: str = ""


@dataclass
class BenchDepth10:
    """Schema with 9 levels of nesting."""

    nested: BenchDepth9
    name: str = ""


DEPTH_SCHEMAS = {
    1: BenchDepth1,
    2: BenchDepth2,
    3: BenchDepth3,
    4: BenchDepth4,
    5: BenchDepth5,
    6: BenchDepth6,
    7: BenchDepth7,
    8: BenchDepth8,
    9: BenchDepth9,
    10: BenchDepth10,
}


def get_nested_schema(depth: int) -> type:
    """
    Get a predefined schema with N levels of nesting.

    Args:
        depth: Number of nesting levels (1-10)

    Returns:
        The dataclass type for that depth
    """
    if depth not in DEPTH_SCHEMAS:
        raise ValueError(f"Only depths 1-10 supported, got {depth}")
    return DEPTH_SCHEMAS[depth]


def generate_nested_data(depth: int) -> dict[str, Any]:
    """
    Generate nested dictionary data matching the schema depth.

    Args:
        depth: Number of nesting levels

    Returns:
        Nested dictionary structure
    """
    if depth <= 1:
        return {"value": "leaf"}

    result: dict[str, Any] = {"name": "level_1"}
    current = result

    for level in range(2, depth):
        current["nested"] = {"name": f"level_{level}"}
        current = current["nested"]

    # Innermost level
    current["nested"] = {"value": "leaf"}
    return result


# ---------------------------------------------------------------------------
# Collection Path Matching Benchmarks
# ---------------------------------------------------------------------------


class TestCollectionPathMatchingPerformance:
    """Benchmarks for get_collection_for_path() performance."""

    @pytest.fixture
    def collections_10(self) -> dict[str, CollectionConfig[Any]]:
        """Generate 10 collection configurations."""
        return generate_collections(10)

    @pytest.fixture
    def collections_50(self) -> dict[str, CollectionConfig[Any]]:
        """Generate 50 collection configurations."""
        return generate_collections(50)

    @pytest.fixture
    def collections_100(self) -> dict[str, CollectionConfig[Any]]:
        """Generate 100 collection configurations."""
        return generate_collections(100)

    @pytest.fixture
    def collections_200(self) -> dict[str, CollectionConfig[Any]]:
        """Generate 200 collection configurations."""
        return generate_collections(200)

    def test_collection_matching_10_linear(
        self, collections_10: dict[str, CollectionConfig[Any]]
    ) -> None:
        """Baseline: linear scan collection matching with 10 collections."""
        content_root = Path("content")
        file_path = Path("content/section_5/nested/post.md")

        # Warm up
        get_collection_for_path(file_path, content_root, collections_10)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            name, config = get_collection_for_path(file_path, content_root, collections_10)
        elapsed = time.perf_counter() - start

        assert name == "collection_5"
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Linear scan (10 collections): {avg_us:.2f} μs/call")

    def test_collection_matching_100_linear(
        self, collections_100: dict[str, CollectionConfig[Any]]
    ) -> None:
        """Baseline: linear scan collection matching with 100 collections."""
        content_root = Path("content")
        file_path = Path("content/section_50/nested/post.md")

        # Warm up
        get_collection_for_path(file_path, content_root, collections_100)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            name, config = get_collection_for_path(file_path, content_root, collections_100)
        elapsed = time.perf_counter() - start

        assert name == "collection_50"
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Linear scan (100 collections): {avg_us:.2f} μs/call")

    def test_collection_matching_10_trie(
        self, collections_10: dict[str, CollectionConfig[Any]]
    ) -> None:
        """Optimized: trie-based collection matching with 10 collections."""
        content_root = Path("content")
        file_path = Path("content/section_5/nested/post.md")
        trie = build_collection_trie(collections_10)

        # Warm up
        get_collection_for_path(file_path, content_root, collections_10, trie=trie)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            name, config = get_collection_for_path(
                file_path, content_root, collections_10, trie=trie
            )
        elapsed = time.perf_counter() - start

        assert name == "collection_5"
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Trie lookup (10 collections): {avg_us:.2f} μs/call")

    def test_collection_matching_100_trie(
        self, collections_100: dict[str, CollectionConfig[Any]]
    ) -> None:
        """Optimized: trie-based collection matching with 100 collections."""
        content_root = Path("content")
        file_path = Path("content/section_50/nested/post.md")
        trie = build_collection_trie(collections_100)

        # Warm up
        get_collection_for_path(file_path, content_root, collections_100, trie=trie)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            name, config = get_collection_for_path(
                file_path, content_root, collections_100, trie=trie
            )
        elapsed = time.perf_counter() - start

        assert name == "collection_50"
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Trie lookup (100 collections): {avg_us:.2f} μs/call")

    def test_collection_matching_scaling(self) -> None:
        """Compare scaling: linear vs trie across collection counts."""
        content_root = Path("content")
        iterations = 500
        results = []

        for num_collections in [10, 50, 100, 200]:
            collections = generate_collections(num_collections)
            file_path = Path(f"content/section_{num_collections // 2}/nested/post.md")
            trie = build_collection_trie(collections)

            # Linear scan
            start = time.perf_counter()
            for _ in range(iterations):
                get_collection_for_path(file_path, content_root, collections)
            linear_time = (time.perf_counter() - start) / iterations * 1_000_000

            # Trie lookup
            start = time.perf_counter()
            for _ in range(iterations):
                get_collection_for_path(file_path, content_root, collections, trie=trie)
            trie_time = (time.perf_counter() - start) / iterations * 1_000_000

            results.append((num_collections, linear_time, trie_time))

        print("\n  Collection Matching Performance (μs/call):")
        print("  Collections | Linear | Trie   | Speedup")
        print("  ------------|--------|--------|--------")
        for num, linear, trie in results:
            speedup = linear / trie if trie > 0 else 0
            print(f"  {num:>11} | {linear:>6.2f} | {trie:>6.2f} | {speedup:>6.1f}x")


# ---------------------------------------------------------------------------
# Schema Validation Benchmarks
# ---------------------------------------------------------------------------


class TestSchemaValidationPerformance:
    """Benchmarks for SchemaValidator.validate() with nested schemas."""

    def test_validation_flat_schema(self) -> None:
        """Baseline: validation with flat (non-nested) schema."""

        @dataclass
        class FlatSchema:
            title: str
            count: int = 0
            active: bool = True
            tags: list[str] = field(default_factory=list)

        validator = SchemaValidator(FlatSchema)
        data = {"title": "Test", "count": 42, "active": True, "tags": ["a", "b"]}

        # Warm up
        validator.validate(data)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            result = validator.validate(data)
        elapsed = time.perf_counter() - start

        assert result.valid
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Flat schema validation: {avg_us:.2f} μs/call")

    def test_validation_nested_3_levels(self) -> None:
        """Validation with 3 levels of nesting."""
        schema = get_nested_schema(3)
        validator = SchemaValidator(schema)
        data = generate_nested_data(3)

        # Warm up
        validator.validate(data)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            result = validator.validate(data)
        elapsed = time.perf_counter() - start

        assert result.valid
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Nested 3-level validation: {avg_us:.2f} μs/call")

    def test_validation_nested_5_levels(self) -> None:
        """Validation with 5 levels of nesting."""
        schema = get_nested_schema(5)
        validator = SchemaValidator(schema)
        data = generate_nested_data(5)

        # Warm up
        validator.validate(data)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            result = validator.validate(data)
        elapsed = time.perf_counter() - start

        assert result.valid
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Nested 5-level validation: {avg_us:.2f} μs/call")

    def test_validation_nested_10_levels(self) -> None:
        """Validation with 10 levels of nesting (at default depth limit)."""
        schema = get_nested_schema(10)
        validator = SchemaValidator(schema)
        data = generate_nested_data(10)

        # Warm up
        validator.validate(data)

        # Measure
        iterations = 500
        start = time.perf_counter()
        for _ in range(iterations):
            result = validator.validate(data)
        elapsed = time.perf_counter() - start

        assert result.valid
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\n  Nested 10-level validation: {avg_us:.2f} μs/call")

    def test_validation_depth_limit_exceeded(self) -> None:
        """Test that depth limit is enforced and returns clean error."""
        # Use depth 10 schema with max_depth=5 to trigger depth limit
        schema = get_nested_schema(10)
        validator = SchemaValidator(schema, max_depth=5)
        data = generate_nested_data(10)

        result = validator.validate(data)

        # Should fail with depth exceeded error, not crash
        assert result.valid is False
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_validation_custom_depth_limit(self) -> None:
        """Test custom depth limit is respected."""
        schema = get_nested_schema(5)
        validator = SchemaValidator(schema, max_depth=3)
        data = generate_nested_data(5)

        result = validator.validate(data)

        # Should fail because data is 5 levels but limit is 3
        assert result.valid is False
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_validation_scaling_with_depth(self) -> None:
        """Compare validation time across nesting depths."""
        iterations = 200
        results = []

        for depth in [1, 3, 5, 8, 10]:
            schema = get_nested_schema(depth)
            validator = SchemaValidator(schema)
            data = generate_nested_data(depth)

            start = time.perf_counter()
            for _ in range(iterations):
                result = validator.validate(data)
            elapsed = time.perf_counter() - start

            assert result.valid
            avg_us = (elapsed / iterations) * 1_000_000
            results.append((depth, avg_us))

        print("\n  Validation Performance by Nesting Depth:")
        print("  Depth | Time (μs)")
        print("  ------|----------")
        for depth, time_us in results:
            print(f"  {depth:>5} | {time_us:>8.2f}")


# ---------------------------------------------------------------------------
# Trie Data Structure Benchmarks
# ---------------------------------------------------------------------------


class TestTriePerformance:
    """Benchmarks for CollectionPathTrie operations."""

    def test_trie_build_time(self) -> None:
        """Measure time to build trie from collections."""
        results = []

        for num_collections in [10, 50, 100, 200]:
            collections = generate_collections(num_collections)

            iterations = 100
            start = time.perf_counter()
            for _ in range(iterations):
                _trie = build_collection_trie(collections)
            elapsed = time.perf_counter() - start

            avg_us = (elapsed / iterations) * 1_000_000
            results.append((num_collections, avg_us))

        print("\n  Trie Build Time:")
        print("  Collections | Build Time (μs)")
        print("  ------------|----------------")
        for num, time_us in results:
            print(f"  {num:>11} | {time_us:>14.2f}")

    def test_trie_find_performance(self) -> None:
        """Measure trie find performance across path depths."""
        collections = generate_collections(100)
        trie = build_collection_trie(collections)

        iterations = 1000
        results = []

        # Test paths of varying depths
        test_paths = [
            ("shallow", Path("content/section_50/post.md")),
            ("medium", Path("content/section_50/nested/post.md")),
            ("deep", Path("content/section_50/a/b/c/d/post.md")),
        ]

        for name, path in test_paths:
            rel_path = path.relative_to(Path("content"))

            start = time.perf_counter()
            for _ in range(iterations):
                _result = trie.find(rel_path)
            elapsed = time.perf_counter() - start

            avg_us = (elapsed / iterations) * 1_000_000
            results.append((name, avg_us))

        print("\n  Trie Find Performance by Path Depth:")
        print("  Path Type | Time (μs)")
        print("  ----------|----------")
        for name, time_us in results:
            print(f"  {name:>9} | {time_us:>8.2f}")
