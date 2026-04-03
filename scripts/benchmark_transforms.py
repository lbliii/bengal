#!/usr/bin/env python3
"""
Benchmark HTML Transform Performance.

Measures the production HybridHTMLTransformer across different content
profiles (small, medium, large, no-op) to establish performance baselines.

Usage:
    uv run python scripts/benchmark_transforms.py

RFC Reference: plan/drafted/rfc-rendering-package-optimizations.md
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from bengal.rendering.pipeline.unified_transform import HybridHTMLTransformer

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
<p>See also: <a href="./CHANGELOG.md">Changelog</a> | <a href="/about/">About</a></p>
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
        return samples["small"] + samples["medium"] + samples["large"]

    return samples.get(page_type, samples["medium"])


def benchmark_transformer(
    html_samples: list[str], baseurl: str, iterations: int
) -> BenchmarkResult:
    """Benchmark the production HybridHTMLTransformer."""
    transformer = HybridHTMLTransformer(baseurl)

    start = time.perf_counter()

    for _ in range(iterations):
        for html in html_samples:
            transformer.transform(html)

    elapsed = time.perf_counter() - start
    total_pages = iterations * len(html_samples)

    return BenchmarkResult(
        name="HybridHTMLTransformer",
        total_ms=elapsed * 1000,
        per_page_ms=(elapsed * 1000) / total_pages,
        iterations=iterations,
        pages=len(html_samples),
    )


def run_benchmarks():
    """Run complete benchmark suite."""
    print("=" * 70)
    print("HTML Transform Benchmark")
    print("=" * 70)
    print()

    baseurl = "/bengal"
    iterations = 1000

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

    # Run multiple times for stability
    runs = 5
    times = []

    print("Running benchmarks...")
    print("-" * 70)

    for _run in range(runs):
        result = benchmark_transformer(samples, baseurl, iterations)
        times.append(result.total_ms)

    median_ms = statistics.median(times)
    total_pages = iterations * len(samples)

    print(f"{'Approach':<25} {'Total (ms)':<15} {'Per-page (ms)':<15}")
    print("-" * 55)
    print(f"{'HybridHTMLTransformer':<25} {median_ms:>10.2f}     {median_ms / total_pages:>10.4f}")
    print()

    # Per-page breakdown
    print("-" * 70)
    print("Per-page breakdown:")
    print()
    for sample_type in ["small", "medium", "large", "no_transforms"]:
        sample = [generate_sample_html(sample_type)]
        result = benchmark_transformer(sample, baseurl, 1000)
        print(f"  {sample_type:<15}: {result.per_page_ms:.4f}ms")


if __name__ == "__main__":
    run_benchmarks()
