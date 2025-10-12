"""Performance benchmark for DotDict caching optimization."""

import time

from bengal.utils.dotdict import DotDict


def test_nested_access_performance():
    """Benchmark nested dictionary access with caching."""
    # Create deeply nested structure
    data = DotDict({"level1": {"level2": {"level3": {"level4": {"level5": {"value": "deep"}}}}}})

    # Warm up cache
    _ = data.level1.level2.level3.level4.level5.value

    # Benchmark repeated access (should be fast due to caching)
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        _ = data.level1.level2.level3.level4.level5.value
    end = time.perf_counter()

    elapsed = end - start
    per_access = (elapsed / iterations) * 1000000  # microseconds

    print("\nDeeply nested access (5 levels):")
    print(f"  Iterations: {iterations:,}")
    print(f"  Total time: {elapsed:.4f} seconds")
    print(f"  Per access: {per_access:.2f} µs")
    print(f"  Access/sec: {iterations / elapsed:,.0f}")

    # Should be fast (< 10 µs per access with caching)
    assert per_access < 10, f"Access too slow: {per_access:.2f} µs (expected < 10 µs)"


def test_template_loop_simulation():
    """Simulate Jinja2 template loop accessing nested data."""
    # Simulate data that might be accessed in a template loop
    data = DotDict(
        {
            "users": [
                {"name": "Alice", "profile": {"bio": "Developer", "stats": {"posts": 100}}},
                {"name": "Bob", "profile": {"bio": "Designer", "stats": {"posts": 50}}},
                {"name": "Charlie", "profile": {"bio": "Manager", "stats": {"posts": 25}}},
            ]
            * 100  # 300 users total
        }
    )

    # Pre-wrap all user dicts (simulate from_dict behavior)
    data = DotDict.from_dict(data._data)

    # Simulate template loop accessing nested data
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        total_posts = 0
        for user in data.users:
            # Access nested data (profile.stats.posts)
            total_posts += user.profile.stats.posts
    end = time.perf_counter()

    elapsed = end - start
    per_iteration = (elapsed / iterations) * 1000  # milliseconds

    print("\nTemplate loop simulation (300 users):")
    print(f"  Iterations: {iterations:,}")
    print(f"  Total time: {elapsed:.4f} seconds")
    print(f"  Per iteration: {per_iteration:.2f} ms")
    print(f"  Iterations/sec: {iterations / elapsed:,.0f}")

    # Should complete reasonably fast
    assert per_iteration < 50, f"Loop too slow: {per_iteration:.2f} ms (expected < 50 ms)"


def test_cache_memory_efficiency():
    """Verify that caching doesn't create excessive objects."""
    # Create nested structure
    data = DotDict({"a": {"b": {"c": {"d": {"e": "value"}}}}, "x": {"y": {"z": "value"}}})

    # Access multiple times
    for _ in range(100):
        _ = data.a.b.c.d.e
        _ = data.x.y.z

    # Verify cache contains expected entries
    # (only first-level nested dicts are cached at each level)
    assert len(data._cache) == 2  # 'a' and 'x'
    assert len(data.a._cache) == 1  # 'b'
    assert len(data.a.b._cache) == 1  # 'c'

    print("\nCache efficiency:")
    print(f"  Root cache size: {len(data._cache)}")
    print(f"  Level 1 cache size: {len(data.a._cache)}")
    print(f"  Level 2 cache size: {len(data.a.b._cache)}")
    print("  ✓ Cache only stores accessed nested dicts")


def test_bracket_vs_dot_notation():
    """Compare bracket and dot notation performance (should be similar)."""
    data = DotDict({"user": {"profile": {"bio": "test"}}})

    # Warm up
    _ = data.user.profile.bio
    _ = data["user"]["profile"]["bio"]

    iterations = 10000

    # Dot notation
    start = time.perf_counter()
    for _ in range(iterations):
        _ = data.user.profile.bio
    dot_time = time.perf_counter() - start

    # Bracket notation
    start = time.perf_counter()
    for _ in range(iterations):
        _ = data["user"]["profile"]["bio"]
    bracket_time = time.perf_counter() - start

    print(f"\nDot vs Bracket notation ({iterations:,} iterations):")
    print(
        f"  Dot notation:     {dot_time:.4f}s ({(dot_time / iterations) * 1000000:.2f} µs/access)"
    )
    print(
        f"  Bracket notation: {bracket_time:.4f}s ({(bracket_time / iterations) * 1000000:.2f} µs/access)"
    )
    print(f"  Ratio: {bracket_time / dot_time:.2f}x")

    # Both should be fast (< 10 µs per access)
    assert (dot_time / iterations) * 1000000 < 10
    assert (bracket_time / iterations) * 1000000 < 10


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DotDict Performance Benchmarks (with caching optimization)")
    print("=" * 70)

    test_nested_access_performance()
    test_template_loop_simulation()
    test_cache_memory_efficiency()
    test_bracket_vs_dot_notation()

    print("\n" + "=" * 70)
    print("✓ All performance benchmarks passed!")
    print("=" * 70 + "\n")
