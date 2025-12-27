"""Comprehensive tests for Kida caching behavior.

Tests the LRU cache for templates and fragment caching.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from bengal.rendering.kida import DictLoader, Environment
from bengal.rendering.kida.environment.core import LRUCache


class TestLRUCache:
    """Test the LRU cache implementation."""

    def test_basic_get_set(self) -> None:
        """Basic get and set operations."""
        cache = LRUCache(maxsize=10)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing(self) -> None:
        """Get returns None for missing keys."""
        cache = LRUCache(maxsize=10)
        assert cache.get("missing") is None

    def test_overwrite(self) -> None:
        """Overwriting existing key."""
        cache = LRUCache(maxsize=10)
        cache.set("key", "value1")
        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_lru_eviction(self) -> None:
        """LRU eviction when at capacity."""
        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Access 'a' to make it recently used
        cache.get("a")

        # Add 'd' - should evict 'b' (least recently used)
        cache.set("d", 4)

        assert cache.get("a") == 1  # Still present (was accessed)
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_order_updates(self) -> None:
        """Accessing a key updates its LRU position."""
        cache = LRUCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)

        # Access 'a' - now 'b' is LRU
        cache.get("a")

        # Add 'c' - should evict 'b'
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_set_updates_lru(self) -> None:
        """Setting existing key updates LRU position."""
        cache = LRUCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)

        # Update 'a' - now 'b' is LRU
        cache.set("a", 10)

        # Add 'c' - should evict 'b'
        cache.set("c", 3)

        assert cache.get("a") == 10
        assert cache.get("b") is None

    def test_ttl_expiry(self) -> None:
        """TTL-based expiry."""
        cache = LRUCache(maxsize=10, ttl=0.1)  # 100ms TTL
        cache.set("key", "value")
        assert cache.get("key") == "value"

        # Wait for expiry
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_ttl_refresh_on_set(self) -> None:
        """Setting refreshes TTL."""
        cache = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", "value")
        time.sleep(0.05)
        cache.set("key", "new_value")
        time.sleep(0.08)
        # Should still be valid (reset at 0.05, now at 0.13)
        assert cache.get("key") == "new_value"

    def test_clear(self) -> None:
        """Clear removes all entries."""
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert len(cache) == 0

    def test_len(self) -> None:
        """len returns number of entries."""
        cache = LRUCache(maxsize=10)
        assert len(cache) == 0
        cache.set("a", 1)
        assert len(cache) == 1
        cache.set("b", 2)
        assert len(cache) == 2

    def test_contains(self) -> None:
        """in operator checks existence."""
        cache = LRUCache(maxsize=10)
        cache.set("key", "value")
        assert "key" in cache
        assert "missing" not in cache

    def test_contains_respects_ttl(self) -> None:
        """in operator respects TTL."""
        cache = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", "value")
        assert "key" in cache
        time.sleep(0.15)
        assert "key" not in cache

    def test_stats(self) -> None:
        """Statistics tracking."""
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)

        # Hit
        cache.get("a")

        # Miss
        cache.get("missing")

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1
        assert stats["max_size"] == 10

    def test_reset_stats(self) -> None:
        """Reset statistics without clearing cache."""
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")
        cache.get("missing")

        cache.reset_stats()

        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 1  # Cache not cleared

    def test_enable_disable(self) -> None:
        """Enable/disable caching."""
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)
        assert cache.get("a") == 1

        cache.disable()
        cache.set("b", 2)
        assert cache.get("b") is None  # Not stored when disabled
        assert cache.get("a") is None  # Returns None when disabled

        cache.enable()
        assert cache.get("a") == 1  # Original value still there

    def test_maxsize_zero(self) -> None:
        """Unlimited cache with maxsize=0."""
        cache = LRUCache(maxsize=0)
        for i in range(100):
            cache.set(f"key{i}", i)
        assert len(cache) == 100


class TestLRUCacheThreadSafety:
    """Test thread safety of LRU cache."""

    def test_concurrent_reads(self) -> None:
        """Concurrent reads don't cause issues."""
        cache = LRUCache(maxsize=100)
        for i in range(100):
            cache.set(f"key{i}", i)

        def read(n: int) -> None:
            for _ in range(100):
                cache.get(f"key{n % 100}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read, i) for i in range(100)]
            for f in futures:
                f.result()

    def test_concurrent_writes(self) -> None:
        """Concurrent writes don't corrupt cache."""
        cache = LRUCache(maxsize=100)

        def write(n: int) -> None:
            for i in range(100):
                cache.set(f"key{n}_{i}", n * 100 + i)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write, i) for i in range(10)]
            for f in futures:
                f.result()

        # Cache should be consistent
        assert len(cache) <= 100

    def test_concurrent_read_write(self) -> None:
        """Concurrent reads and writes."""
        cache = LRUCache(maxsize=50)

        def worker(n: int) -> None:
            for i in range(100):
                if i % 2 == 0:
                    cache.set(f"key{n}_{i}", i)
                else:
                    cache.get(f"key{n}_{i - 1}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for f in futures:
                f.result()


class TestTemplateCaching:
    """Test template caching behavior."""

    def test_template_cached(self) -> None:
        """Templates are cached."""
        loader = DictLoader({"test.html": "Hello"})
        env = Environment(loader=loader)

        t1 = env.get_template("test.html")
        t2 = env.get_template("test.html")

        assert t1 is t2

    def test_different_templates_cached_separately(self) -> None:
        """Different templates cached separately."""
        loader = DictLoader({"a.html": "A", "b.html": "B"})
        env = Environment(loader=loader)

        ta = env.get_template("a.html")
        tb = env.get_template("b.html")

        assert ta is not tb
        assert ta.render() == "A"
        assert tb.render() == "B"

    def test_from_string_not_cached(self) -> None:
        """from_string creates new template each time."""
        env = Environment()

        t1 = env.from_string("Hello")
        t2 = env.from_string("Hello")

        # Same source but different objects
        assert t1 is not t2

    def test_cache_eviction(self) -> None:
        """Templates evicted when cache full."""
        templates = {f"t{i}.html": f"Template {i}" for i in range(100)}
        loader = DictLoader(templates)
        env = Environment(loader=loader, cache_size=10)

        # Load more templates than cache size
        for i in range(50):
            env.get_template(f"t{i}.html")

        # Cache should have at most cache_size entries
        stats = env.cache_info()
        assert stats["template"]["size"] <= 10

    def test_clear_cache(self) -> None:
        """Clearing cache works."""
        loader = DictLoader({"test.html": "Hello"})
        env = Environment(loader=loader)

        t1 = env.get_template("test.html")
        env.clear_cache()
        t2 = env.get_template("test.html")

        # Different objects after cache clear
        assert t1 is not t2

    def test_cache_info(self) -> None:
        """Cache info returns statistics."""
        loader = DictLoader({"a.html": "A", "b.html": "B"})
        env = Environment(loader=loader)

        env.get_template("a.html")
        env.get_template("a.html")  # Hit
        env.get_template("b.html")  # Miss

        info = env.cache_info()
        assert "template" in info
        assert info["template"]["hits"] >= 1


class TestFragmentCaching:
    """Test fragment caching behavior."""

    def test_cache_block_basic(self) -> None:
        """Basic cache block."""
        env = Environment()
        tmpl = env.from_string("{% cache 'key' %}Content{% endcache %}")
        result = tmpl.render()
        assert result == "Content"

    def test_cache_block_returns_cached(self) -> None:
        """Cache block returns cached value."""
        env = Environment()

        # Template with counter to detect caching
        tmpl = env.from_string("{% cache 'counter' %}{{ counter }}{% endcache %}")

        result1 = tmpl.render(counter=1)
        result2 = tmpl.render(counter=2)

        # Both should return first value (cached)
        assert result1 == "1"
        assert result2 == "1"

    def test_cache_different_keys(self) -> None:
        """Different cache keys store different values."""
        env = Environment()

        tmpl = env.from_string("{% cache key %}{{ value }}{% endcache %}")

        result1 = tmpl.render(key="key1", value="A")
        result2 = tmpl.render(key="key2", value="B")

        assert result1 == "A"
        assert result2 == "B"

    def test_clear_fragment_cache(self) -> None:
        """Clearing fragment cache."""
        env = Environment()
        tmpl = env.from_string("{% cache 'key' %}{{ counter }}{% endcache %}")

        result1 = tmpl.render(counter=1)
        env.clear_fragment_cache()
        result2 = tmpl.render(counter=2)

        assert result1 == "1"
        assert result2 == "2"  # Fresh after clear

    def test_fragment_cache_ttl(self) -> None:
        """Fragment cache respects TTL."""
        env = Environment(fragment_ttl=0.1)  # 100ms TTL
        tmpl = env.from_string("{% cache 'key' %}{{ counter }}{% endcache %}")

        result1 = tmpl.render(counter=1)
        time.sleep(0.15)  # Wait for expiry
        result2 = tmpl.render(counter=2)

        assert result1 == "1"
        assert result2 == "2"  # Refreshed after expiry


class TestCacheThreadSafety:
    """Test cache thread safety in template operations."""

    def test_concurrent_template_compilation(self) -> None:
        """Concurrent template compilation."""
        loader = DictLoader({"test.html": "Hello {{ name }}"})
        env = Environment(loader=loader)

        results = []

        def compile_and_render(n: int) -> None:
            tmpl = env.get_template("test.html")
            result = tmpl.render(name=f"User{n}")
            results.append(result)

        threads = [threading.Thread(target=compile_and_render, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        for _i, r in enumerate(results):
            assert "Hello" in r

    def test_concurrent_fragment_caching(self) -> None:
        """Concurrent fragment caching."""
        env = Environment()
        tmpl = env.from_string("{% cache 'shared' %}{{ value }}{% endcache %}")

        results = []

        def render(n: int) -> None:
            result = tmpl.render(value=n)
            results.append(result)

        threads = [threading.Thread(target=render, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All results should be the same (first cached value)
        assert len(results) == 20
        first = results[0]
        assert all(r == first for r in results)


class TestCacheConfiguration:
    """Test cache configuration options."""

    def test_custom_cache_size(self) -> None:
        """Custom template cache size."""
        env = Environment(cache_size=5)
        assert env._cache.maxsize == 5

    def test_custom_fragment_cache_size(self) -> None:
        """Custom fragment cache size."""
        env = Environment(fragment_cache_size=50)
        assert env._fragment_cache.maxsize == 50

    def test_custom_fragment_ttl(self) -> None:
        """Custom fragment TTL."""
        env = Environment(fragment_ttl=60.0)
        assert env._fragment_cache._ttl == 60.0

    def test_disabled_caching(self) -> None:
        """Template cache can be disabled."""
        # With size 0, cache should still work (unlimited)
        loader = DictLoader({"test.html": "Hello"})
        env_with_loader = Environment(loader=loader, cache_size=0)

        t1 = env_with_loader.get_template("test.html")
        t2 = env_with_loader.get_template("test.html")
        # With unlimited size, should be cached
        assert t1 is t2


class TestCacheIntegration:
    """Integration tests for caching with complex templates."""

    def test_cache_with_inheritance(self) -> None:
        """Caching works with template inheritance."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": '{% extends "base.html" %}{% block content %}Hello{% endblock %}',
            }
        )
        env = Environment(loader=loader)

        # Load multiple times
        for _ in range(5):
            tmpl = env.get_template("child.html")
            result = tmpl.render()
            assert "<html>Hello</html>" in result

        # Base should also be cached
        info = env.cache_info()
        assert info["template"]["size"] >= 2

    def test_cache_with_includes(self) -> None:
        """Caching works with includes."""
        loader = DictLoader(
            {
                "main.html": 'Before {% include "partial.html" %} After',
                "partial.html": "Partial",
            }
        )
        env = Environment(loader=loader)

        for _ in range(5):
            result = env.get_template("main.html").render()
            assert "Before Partial After" in result

    def test_cache_with_imports(self) -> None:
        """Caching works with macro imports."""
        loader = DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hello {{ name }}{% endmacro %}",
                "main.html": '{% from "macros.html" import greet %}{{ greet("World") }}',
            }
        )
        env = Environment(loader=loader)

        for _ in range(5):
            result = env.get_template("main.html").render()
            assert "Hello World" in result
