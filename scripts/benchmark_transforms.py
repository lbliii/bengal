#!/usr/bin/env python3
"""
Benchmark HTML Transform Approaches.

Compares the current 3-pass transform chain with proposed hybrid approaches
to validate whether combining transforms provides meaningful improvement.

Usage:
    uv run python scripts/benchmark_transforms.py

This script measures:
1. Current approach: escape_jinja_blocks + normalize_markdown_links + transform_internal_links
2. Hybrid approach: str.replace() for Jinja + combined regex for links

RFC Reference: plan/drafted/rfc-rendering-package-optimizations.md
"""

from __future__ import annotations

import re
import statistics
import time
from dataclasses import dataclass

# Current implementations (imported for baseline)
from bengal.rendering.pipeline.transforms import (
    escape_jinja_blocks,
    normalize_markdown_links,
    transform_internal_links,
)

# =============================================================================
# Proposed Hybrid Transformer
# =============================================================================


class HybridHTMLTransformer:
    """
    Hybrid transformation approach.

    Strategy:
    - Jinja escaping: Keep fast str.replace() (C-optimized)
    - Link transforms: Combine into single regex pass
    """

    def __init__(self, baseurl: str = ""):
        self.baseurl = baseurl.rstrip("/") if baseurl else ""
        self.should_transform_links = bool(self.baseurl)

        # Normalize baseurl for comparison
        if self.baseurl and not self.baseurl.startswith(("http://", "https://", "file://", "/")):
            self.baseurl = "/" + self.baseurl

        # Combined pattern for both .md and internal link transforms
        # Note: We use two separate patterns and run them sequentially
        # because combining them leads to complex backreference issues
        self._md_pattern = re.compile(r'(href)=(["\'])([^"\']*?\.md)\2')
        self._internal_pattern = re.compile(r'(href|src)=(["\'])(/(?!/)[^"\'#][^"\']*)\2')

    def transform(self, html: str) -> str:
        """
        Transform HTML with hybrid approach.

        O(n) for Jinja str.replace() + O(n) for md links + O(n) for internal = O(3n)
        Same as current, but cleaner code structure.
        """
        if not html:
            return html

        # Step 1: Jinja escaping - str.replace() is C-optimized, very fast
        result = html.replace("{%", "&#123;%").replace("%}", "%&#125;")

        # Step 2: Normalize .md links
        if ".md" in result:
            result = self._md_pattern.sub(self._md_replacer, result)

        # Step 3: Transform internal links with baseurl
        if self.should_transform_links and '="/' in result:
            result = self._internal_pattern.sub(self._internal_replacer, result)

        return result

    def _md_replacer(self, match: re.Match) -> str:
        """Transform .md link to clean URL."""
        attr = match.group(1)
        quote = match.group(2)
        path = match.group(3)

        # Handle _index.md and index.md special cases
        if path.endswith("/_index.md"):
            clean = path[:-10] + "/"
            if clean == "/":
                clean = "./"
        elif path.endswith("_index.md"):
            clean = "./"
        elif path.endswith("/index.md"):
            clean = path[:-9] + "/"
        elif path.endswith("index.md"):
            clean = "./"
        else:
            clean = path[:-3] + "/"

        return f"{attr}={quote}{clean}{quote}"

    def _internal_replacer(self, match: re.Match) -> str:
        """Transform internal link with baseurl."""
        attr = match.group(1)
        quote = match.group(2)
        path = match.group(3)

        # Skip if already has baseurl
        if path.startswith(self.baseurl + "/") or path == self.baseurl:
            return match.group(0)

        return f"{attr}={quote}{self.baseurl}{path}{quote}"


# =============================================================================
# Benchmark Infrastructure
# =============================================================================


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    name: str
    total_ms: float
    per_page_ms: float
    iterations: int
    pages: int


def generate_sample_html(page_type: str = "mixed") -> str:
    """Generate realistic HTML samples for benchmarking."""

    samples = {
        "small": """
<p>Simple paragraph with <a href="/docs/guide/">a link</a>.</p>
<p>Another paragraph with <code>inline code</code>.</p>
""",
        "medium": """
<article>
<h1>Getting Started</h1>
<p>Welcome to the documentation. See <a href="./intro.md">introduction</a> or
jump to <a href="/api/reference/">API Reference</a>.</p>
<p>For examples, check <a href="../examples.md">examples page</a>.</p>
<pre><code>{% raw %}
{{ variable }}
{% endraw %}</code></pre>
<p>More content with <a href="/docs/advanced/">advanced topics</a>.</p>
<ul>
<li><a href="./basics.md">Basics</a></li>
<li><a href="./intermediate.md">Intermediate</a></li>
<li><a href="/tutorials/">Tutorials</a></li>
</ul>
<img src="/assets/diagram.svg" alt="Architecture">
</article>
""",
        "large": """
<article class="documentation">
<h1>Complete API Reference</h1>
<nav class="toc">
<ul>
<li><a href="#overview">Overview</a></li>
<li><a href="./getting-started.md">Getting Started</a></li>
<li><a href="/api/core/">Core API</a></li>
<li><a href="/api/utils/">Utilities</a></li>
</ul>
</nav>

<section id="overview">
<h2>Overview</h2>
<p>This is a comprehensive guide. See <a href="./intro.md">introduction</a>.</p>
<p>Related: <a href="../related/_index.md">Related Topics</a></p>
</section>

<section>
<h2>Configuration</h2>
<pre><code class="language-yaml">
# Site configuration
title: My Site
baseurl: /bengal
{% if production %}
minify: true
{% endif %}
</code></pre>
<p>After configuration, see <a href="/docs/deployment/">Deployment Guide</a>.</p>
</section>

<section>
<h2>Template Syntax</h2>
<p>Use Jinja2 syntax:</p>
<pre><code>{% for item in items %}
  {{ item.name }}: {{ item.value }}
{% endfor %}</code></pre>
<p>Variables: <code>{{ page.title }}</code>, <code>{{ site.name }}</code></p>
</section>

<section>
<h2>Links</h2>
<ul>
<li><a href="./feature-a.md">Feature A</a></li>
<li><a href="./feature-b.md">Feature B</a></li>
<li><a href="../advanced/feature-c.md">Feature C (Advanced)</a></li>
<li><a href="/blog/">Blog</a></li>
<li><a href="/docs/faq/">FAQ</a></li>
<li><a href="https://external.com/">External Link</a></li>
</ul>
<img src="/assets/images/hero.png" alt="Hero Image">
<img src="/assets/icons/logo.svg" alt="Logo">
</section>

<footer>
<p>See also: <a href="./changelog.md">Changelog</a> | <a href="/about/">About</a></p>
</footer>
</article>
""",
        "no_transforms": """
<article>
<h1>Simple Content</h1>
<p>This content has no special patterns that need transformation.</p>
<p>Just plain HTML with regular text and <strong>formatting</strong>.</p>
<ul>
<li>Item one</li>
<li>Item two</li>
<li>Item three</li>
</ul>
</article>
""",
    }

    if page_type == "mixed":
        # Return a mix that represents realistic site distribution
        return samples["small"] + samples["medium"] + samples["large"]

    return samples.get(page_type, samples["medium"])


def benchmark_current_approach(
    html_samples: list[str], config: dict, iterations: int
) -> BenchmarkResult:
    """Benchmark current 3-pass transform chain."""
    start = time.perf_counter()

    for _ in range(iterations):
        for html in html_samples:
            result = escape_jinja_blocks(html)
            result = normalize_markdown_links(result)
            result = transform_internal_links(result, config)

    elapsed = time.perf_counter() - start
    total_pages = iterations * len(html_samples)

    return BenchmarkResult(
        name="Current (3-pass)",
        total_ms=elapsed * 1000,
        per_page_ms=(elapsed * 1000) / total_pages,
        iterations=iterations,
        pages=len(html_samples),
    )


def benchmark_hybrid_approach(
    html_samples: list[str], baseurl: str, iterations: int
) -> BenchmarkResult:
    """Benchmark proposed hybrid transformer."""
    transformer = HybridHTMLTransformer(baseurl)

    start = time.perf_counter()

    for _ in range(iterations):
        for html in html_samples:
            transformer.transform(html)

    elapsed = time.perf_counter() - start
    total_pages = iterations * len(html_samples)

    return BenchmarkResult(
        name="Hybrid (2-pass)",
        total_ms=elapsed * 1000,
        per_page_ms=(elapsed * 1000) / total_pages,
        iterations=iterations,
        pages=len(html_samples),
    )


def verify_correctness(html_samples: list[str], config: dict, baseurl: str) -> bool:
    """Verify hybrid produces identical output to current approach."""
    transformer = HybridHTMLTransformer(baseurl)

    for i, html in enumerate(html_samples):
        # Current approach
        current = escape_jinja_blocks(html)
        current = normalize_markdown_links(current)
        current = transform_internal_links(current, config)

        # Hybrid approach
        hybrid = transformer.transform(html)

        if current != hybrid:
            print(f"\n❌ Output mismatch on sample {i}!")
            print(f"Current length: {len(current)}")
            print(f"Hybrid length: {len(hybrid)}")

            # Find first difference
            for j, (c, h) in enumerate(zip(current, hybrid, strict=False)):
                if c != h:
                    print(f"First diff at position {j}:")
                    print(f"  Current: ...{current[max(0, j - 20) : j + 20]}...")
                    print(f"  Hybrid:  ...{hybrid[max(0, j - 20) : j + 20]}...")
                    break

            return False

    return True


def run_benchmarks():
    """Run complete benchmark suite."""
    print("=" * 70)
    print("HTML Transform Benchmark")
    print("=" * 70)
    print()

    # Configuration
    config = {"baseurl": "/bengal"}
    baseurl = "/bengal"
    iterations = 1000

    # Generate samples
    samples = [
        generate_sample_html("small"),
        generate_sample_html("medium"),
        generate_sample_html("large"),
        generate_sample_html("no_transforms"),
    ]

    total_chars = sum(len(s) for s in samples)
    print(f"Test samples: {len(samples)} pages, {total_chars:,} total chars")
    print(f"Iterations: {iterations:,}")
    print(f"Total operations: {iterations * len(samples):,} page transforms")
    print()

    # Verify correctness first
    print("Verifying correctness...")
    if not verify_correctness(samples, config, baseurl):
        print("❌ Correctness check failed! Aborting benchmark.")
        return

    print("✅ Output is identical\n")

    # Run benchmarks
    print("Running benchmarks...")
    print("-" * 70)

    results = []

    # Run multiple times for stability
    runs = 5
    current_times = []
    hybrid_times = []

    for _run in range(runs):
        current = benchmark_current_approach(samples, config, iterations)
        hybrid = benchmark_hybrid_approach(samples, baseurl, iterations)
        current_times.append(current.total_ms)
        hybrid_times.append(hybrid.total_ms)

    # Use median for stability
    current_median = statistics.median(current_times)
    hybrid_median = statistics.median(hybrid_times)

    # Final results
    current_result = BenchmarkResult(
        name="Current (3-pass)",
        total_ms=current_median,
        per_page_ms=current_median / (iterations * len(samples)),
        iterations=iterations,
        pages=len(samples),
    )

    hybrid_result = BenchmarkResult(
        name="Hybrid (2-pass)",
        total_ms=hybrid_median,
        per_page_ms=hybrid_median / (iterations * len(samples)),
        iterations=iterations,
        pages=len(samples),
    )

    results = [current_result, hybrid_result]

    # Print results
    print(f"{'Approach':<20} {'Total (ms)':<15} {'Per-page (ms)':<15}")
    print("-" * 50)

    for r in results:
        print(f"{r.name:<20} {r.total_ms:>10.2f}     {r.per_page_ms:>10.4f}")

    print()

    # Calculate improvement
    speedup = current_median / hybrid_median
    improvement_pct = (1 - hybrid_median / current_median) * 100

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Speedup: {speedup:.2f}x")
    print(f"Improvement: {improvement_pct:.1f}%")
    print()

    if improvement_pct >= 15:
        print("✅ RECOMMENDATION: Proceed with hybrid implementation")
        print("   Improvement exceeds 15% threshold from RFC")
    elif improvement_pct >= 5:
        print("⚠️  MARGINAL: Hybrid is faster but improvement is modest")
        print("   Consider proceeding if code simplification is valuable")
    else:
        print("❌ NOT RECOMMENDED: Improvement is negligible")
        print("   Current implementation is adequate")

    print()

    # Per-page breakdown
    print("-" * 70)
    print("Per-page breakdown:")
    print()
    for sample_type in ["small", "medium", "large", "no_transforms"]:
        sample = [generate_sample_html(sample_type)]
        current = benchmark_current_approach(sample, config, 1000)
        hybrid = benchmark_hybrid_approach(sample, baseurl, 1000)
        diff = current.per_page_ms - hybrid.per_page_ms
        pct = (diff / current.per_page_ms) * 100 if current.per_page_ms > 0 else 0
        print(
            f"  {sample_type:<15}: Current={current.per_page_ms:.4f}ms, "
            f"Hybrid={hybrid.per_page_ms:.4f}ms ({pct:+.1f}%)"
        )


if __name__ == "__main__":
    run_benchmarks()
