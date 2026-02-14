#!/usr/bin/env python3
"""
Benchmark: DirectiveCache impact on rendering performance.

Tests the potential speedup from caching rendered directive HTML
when the same directive (name + options + content) is repeated.

Usage:
    python -m benchmarks.directive_cache_benchmark

Expected output:
    - Baseline rendering time (no cache)
    - Cached rendering time (with cache)
    - Speedup ratio and cache hit rate
"""

from __future__ import annotations

import statistics
import time
from typing import Any

# ============================================================================
# Test content generation
# ============================================================================


def generate_repeated_directives(num_directives: int = 50, unique_ratio: float = 0.2) -> str:
    """Generate markdown with repeated directive patterns.

    Args:
        num_directives: Total number of directives to generate
        unique_ratio: Fraction of directives that are unique (0.0-1.0)
                      Lower = more cache hits, higher = fewer cache hits

    Returns:
        Markdown string with repeated directive blocks
    """
    num_unique = max(1, int(num_directives * unique_ratio))

    # Create pool of unique directive types
    # Note: Patitas requires :::{name} syntax (with braces)
    directive_templates = [
        # Note admonitions (common in docs)
        ":::{note}\nThis is important note #%d.\n:::\n\n",
        ":::{warning}\nBe careful about #%d.\n:::\n\n",
        ":::{tip}\nPro tip #%d for better results.\n:::\n\n",
        # Cards (common in landing pages)
        ":::{card}\n:title: Feature #%d\n:icon: star\n\nDescription of feature.\n:::\n\n",
        # Dropdowns (common in FAQs)
        ":::{dropdown} Question #%d?\nThe answer to question.\n:::\n\n",
        # Simple containers
        ":::{aside}\nAside content #%d goes here.\n:::\n\n",
    ]

    # Build content by repeating directives
    content_parts = ["# Directive Benchmark Page\n\n"]

    for i in range(num_directives):
        # Select directive - use modulo to create repetition patterns
        unique_id = i % num_unique
        template_idx = unique_id % len(directive_templates)
        template = directive_templates[template_idx]

        # For repeated directives, use same ID to get cache hits
        directive_id = unique_id if unique_ratio < 1.0 else i
        content_parts.append(template % directive_id)

    return "".join(content_parts)


def generate_autodoc_style_content(num_items: int = 30) -> str:
    """Generate content similar to autodoc API pages.

    Autodoc pages have MANY repeated patterns:
    - Parameter tables
    - Return type boxes
    - Example blocks
    - Warning admonitions for deprecated items
    """
    content_parts = ["# API Reference\n\n"]

    for i in range(num_items):
        # Note: Using consistent content to enable cache hits
        content_parts.append(
            """
## `function_%d`

:::{note}
This function is part of the core API.
:::

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `arg1` | `str` | First argument |
| `arg2` | `int` | Second argument |

:::{dropdown} Example
```python
result = function("hello", 42)
```
:::

**Returns:** `bool`

---

"""
            % i
        )

    return "".join(content_parts)


# ============================================================================
# Rendering helpers
# ============================================================================


def render_with_patitas(content: str, use_cache: bool = False) -> tuple[str, dict[str, Any]]:
    """Render content using Patitas parser.

    Args:
        content: Markdown content
        use_cache: Whether to enable directive cache

    Returns:
        Tuple of (rendered_html, stats_dict)
    """
    from bengal.parsing.backends.patitas import create_markdown

    # Create markdown instance with all plugins
    md = create_markdown(plugins=["all"], highlight=False)

    # If testing with cache, we'd wire it up here
    # For now, just track timing
    stats: dict[str, Any] = {"cache_enabled": use_cache}

    start = time.perf_counter()
    html = md(content)
    elapsed = time.perf_counter() - start

    stats["render_time_ms"] = elapsed * 1000
    stats["output_size"] = len(html)

    return html, stats


def render_with_simulated_cache(content: str) -> tuple[str, dict[str, Any]]:
    """Render content with simulated directive caching.

    This simulates what would happen if we wired up DirectiveCache
    by manually caching at the render level.
    """
    from bengal.directives.cache import DirectiveCache
    from patitas.nodes import Directive
    from patitas.stringbuilder import StringBuilder

    from bengal.parsing.backends.patitas import create_markdown
    from bengal.parsing.backends.patitas.directives.registry import create_default_registry
    from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer
    from bengal.utils.primitives.hashing import hash_str

    cache = DirectiveCache(max_size=500)
    registry = create_default_registry()

    def _extract_content_signature(node) -> str:
        """Extract location-independent content signature from AST node.

        This extracts just the semantic content (text, structure) without
        line numbers or source locations.
        """
        from patitas.nodes import (
            CodeSpan,
            Emphasis,
            FencedCode,
            Heading,
            Link,
            Paragraph,
            Strong,
            Text,
        )

        parts = []

        def visit(n):
            if isinstance(n, Text):
                parts.append(f"T:{n.content}")
            elif isinstance(n, CodeSpan):
                parts.append(f"C:{n.code}")
            elif isinstance(n, Strong):
                parts.append("**")
                for child in n.children:
                    visit(child)
                parts.append("**")
            elif isinstance(n, Emphasis):
                parts.append("*")
                for child in n.children:
                    visit(child)
                parts.append("*")
            elif isinstance(n, Link):
                parts.append(f"L:{n.destination}")
                for child in n.children:
                    visit(child)
            elif isinstance(n, Paragraph):
                parts.append("P[")
                for child in n.children:
                    visit(child)
                parts.append("]")
            elif isinstance(n, FencedCode):
                parts.append(f"FC:{n.info}:{n.code}")
            elif isinstance(n, Heading):
                parts.append(f"H{n.level}[")
                for child in n.children:
                    visit(child)
                parts.append("]")
            elif hasattr(n, "children"):
                for child in n.children:
                    visit(child)

        for child in node.children:
            visit(child)

        return "|".join(parts)

    # Create custom renderer that uses cache
    class CachingHtmlRenderer(HtmlRenderer):
        def __init__(self, *args, directive_cache: DirectiveCache, **kwargs):
            super().__init__(*args, **kwargs)
            self._directive_cache = directive_cache

        def _render_directive(self, node: Directive, sb: StringBuilder) -> None:
            # Create cache key from directive signature (location-independent)
            # Include: name, title, options (as str), and children content hash
            options_str = str(node.options) if node.options else ""

            # Use location-independent content signature
            content_sig = _extract_content_signature(node)

            cache_key = (
                f"{node.name}:{node.title or ''}:{options_str}:{hash_str(content_sig, truncate=16)}"
            )

            # Check cache
            cached = self._directive_cache.get("directive_html", cache_key)
            if cached:
                sb.append(cached)
                return

            # Render and cache
            temp_sb = StringBuilder()
            super()._render_directive(node, temp_sb)
            result = temp_sb.build()

            self._directive_cache.put("directive_html", cache_key, result)
            sb.append(result)

    # Parse to AST
    md = create_markdown(plugins=["all"], highlight=False)

    start = time.perf_counter()

    # Parse
    ast = md.parse_to_ast(content)

    # Render with caching
    renderer = CachingHtmlRenderer(
        highlight=False,
        directive_registry=registry,
        directive_cache=cache,
    )
    html = renderer.render(ast)

    elapsed = time.perf_counter() - start

    cache_stats = cache.stats()

    return html, {
        "cache_enabled": True,
        "render_time_ms": elapsed * 1000,
        "output_size": len(html),
        "cache_hits": cache_stats["hits"],
        "cache_misses": cache_stats["misses"],
        "cache_hit_rate": cache_stats["hit_rate"],
    }


# ============================================================================
# Benchmark runner
# ============================================================================


def run_benchmark(
    name: str,
    content: str,
    iterations: int = 5,
    warmup: int = 1,
) -> dict[str, Any]:
    """Run benchmark comparing cached vs uncached rendering.

    Args:
        name: Benchmark name
        content: Markdown content to render
        iterations: Number of iterations per variant
        warmup: Warmup iterations (not counted)

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: {name}")
    print(f"Content size: {len(content):,} chars")
    print(f"Iterations: {iterations} (+ {warmup} warmup)")
    print("=" * 60)

    results: dict[str, Any] = {
        "name": name,
        "content_size": len(content),
        "iterations": iterations,
    }

    # Warmup
    for _ in range(warmup):
        render_with_patitas(content, use_cache=False)
        render_with_simulated_cache(content)

    # Benchmark: No cache
    print("\n[1/2] Baseline (no directive cache)...")
    no_cache_times = []
    for i in range(iterations):
        _, stats = render_with_patitas(content, use_cache=False)
        no_cache_times.append(stats["render_time_ms"])
        print(f"  Run {i + 1}: {stats['render_time_ms']:.2f}ms")

    results["no_cache"] = {
        "mean_ms": statistics.mean(no_cache_times),
        "stdev_ms": statistics.stdev(no_cache_times) if len(no_cache_times) > 1 else 0,
        "min_ms": min(no_cache_times),
        "max_ms": max(no_cache_times),
    }

    # Benchmark: With cache
    print("\n[2/2] With directive cache...")
    cache_times = []
    cache_stats_list = []
    for i in range(iterations):
        _, stats = render_with_simulated_cache(content)
        cache_times.append(stats["render_time_ms"])
        cache_stats_list.append(stats)
        print(
            f"  Run {i + 1}: {stats['render_time_ms']:.2f}ms "
            f"(hits: {stats['cache_hits']}, misses: {stats['cache_misses']})"
        )

    # Use stats from last run for cache metrics
    last_cache_stats = cache_stats_list[-1]

    results["with_cache"] = {
        "mean_ms": statistics.mean(cache_times),
        "stdev_ms": statistics.stdev(cache_times) if len(cache_times) > 1 else 0,
        "min_ms": min(cache_times),
        "max_ms": max(cache_times),
        "cache_hit_rate": last_cache_stats["cache_hit_rate"],
        "cache_hits": last_cache_stats["cache_hits"],
        "cache_misses": last_cache_stats["cache_misses"],
    }

    # Calculate speedup
    speedup = results["no_cache"]["mean_ms"] / results["with_cache"]["mean_ms"]
    results["speedup"] = speedup

    # Print summary
    print("\n--- Results ---")
    print(
        f"Baseline:    {results['no_cache']['mean_ms']:.2f}ms ± {results['no_cache']['stdev_ms']:.2f}ms"
    )
    print(
        f"With cache:  {results['with_cache']['mean_ms']:.2f}ms ± {results['with_cache']['stdev_ms']:.2f}ms"
    )
    print(f"Speedup:     {speedup:.2f}x")
    print(
        f"Cache hits:  {last_cache_stats['cache_hit_rate']:.1%} ({last_cache_stats['cache_hits']}/{last_cache_stats['cache_hits'] + last_cache_stats['cache_misses']})"
    )

    return results


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("DirectiveCache Benchmark Suite")
    print("=" * 60)

    all_results = []

    # Benchmark 1: High repetition (80% repeated)
    content1 = generate_repeated_directives(num_directives=100, unique_ratio=0.2)
    results1 = run_benchmark(
        "High repetition (80% repeated directives)",
        content1,
        iterations=5,
    )
    all_results.append(results1)

    # Benchmark 2: Medium repetition (50% repeated)
    content2 = generate_repeated_directives(num_directives=100, unique_ratio=0.5)
    results2 = run_benchmark(
        "Medium repetition (50% repeated directives)",
        content2,
        iterations=5,
    )
    all_results.append(results2)

    # Benchmark 3: Low repetition (90% unique)
    content3 = generate_repeated_directives(num_directives=100, unique_ratio=0.9)
    results3 = run_benchmark(
        "Low repetition (10% repeated directives)",
        content3,
        iterations=5,
    )
    all_results.append(results3)

    # Benchmark 4: Autodoc-style content
    content4 = generate_autodoc_style_content(num_items=50)
    results4 = run_benchmark(
        "Autodoc-style API reference",
        content4,
        iterations=5,
    )
    all_results.append(results4)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n{'Benchmark':<45} {'Speedup':>10} {'Cache Hit Rate':>15}")
    print("-" * 70)
    for r in all_results:
        print(f"{r['name']:<45} {r['speedup']:>9.2f}x {r['with_cache']['cache_hit_rate']:>14.1%}")

    # Recommendation
    avg_speedup = statistics.mean(r["speedup"] for r in all_results)
    print(f"\n{'Average speedup:':<45} {avg_speedup:>9.2f}x")

    if avg_speedup > 1.1:
        print("\n✅ Recommendation: Wiring up DirectiveCache is worth it!")
    else:
        print("\n⚠️ Recommendation: Speedup is marginal, may not be worth the complexity.")


if __name__ == "__main__":
    main()
