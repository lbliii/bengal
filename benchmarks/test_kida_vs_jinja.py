"""Benchmark: Kida vs Jinja2 on real Bengal site/ templates.

This benchmark uses Kida's Jinja compatibility layer to parse existing
Jinja2 templates and run them through Kida's fast runtime.

Run with:
    python -m pytest benchmarks/test_kida_vs_jinja.py -v --benchmark-only

Or standalone:
    python benchmarks/test_kida_vs_jinja.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

# Test data
SITE_DIR = Path(__file__).parent.parent / "site"
TEMPLATES_DIR = SITE_DIR / "content"


def get_sample_context() -> dict[str, Any]:
    """Create a sample context matching Bengal's template expectations."""
    return {
        "page": {
            "title": "Test Page",
            "url": "/test/",
            "content": "<p>This is test content.</p>",
            "date": "2025-12-25",
            "draft": False,
            "tags": ["python", "templates", "benchmark"],
            "metadata": {"author": "Test Author"},
        },
        "site": {
            "title": "Bengal Documentation",
            "url": "https://bengal.dev",
            "pages": [
                {"title": f"Page {i}", "url": f"/page-{i}/", "draft": False} for i in range(100)
            ],
            "nav_version": "1.0.0",
        },
        "config": {
            "theme": "default",
            "debug": False,
        },
        "loop": type(
            "Loop",
            (),
            {
                "index": 1,
                "index0": 0,
                "first": True,
                "last": False,
                "length": 100,
            },
        )(),
    }


# =============================================================================
# Simple Template Benchmarks
# =============================================================================

SIMPLE_TEMPLATES = {
    "variable": "{{ name }}",
    "attribute": "{{ page.title }}",
    "nested_attribute": "{{ page.metadata.author }}",
    "filter_upper": "{{ name | upper }}",
    "filter_chain": "{{ name | upper | trim }}",
    "conditional": "{% if page.draft %}Draft{% else %}Published{% endif %}",
    "loop_simple": "{% for i in items %}{{ i }}{% endfor %}",
    "loop_with_attr": "{% for p in pages %}{{ p.title }}{% endfor %}",
}


class BenchmarkResult:
    """Store benchmark results."""

    def __init__(self, name: str, jinja_time: float, kida_time: float):
        self.name = name
        self.jinja_time = jinja_time
        self.kida_time = kida_time
        self.speedup = jinja_time / kida_time if kida_time > 0 else float("inf")

    def __repr__(self) -> str:
        return (
            f"{self.name:30} | "
            f"Jinja: {self.jinja_time * 1000:8.3f}ms | "
            f"Kida: {self.kida_time * 1000:8.3f}ms | "
            f"Speedup: {self.speedup:5.1f}x"
        )


def benchmark_template(
    template_source: str,
    context: dict[str, Any],
    iterations: int = 1000,
) -> BenchmarkResult:
    """Benchmark a template with both engines."""
    from jinja2 import Environment as JinjaEnv

    from bengal.rendering.kida import Environment as KidaEnv

    # Setup Jinja2
    jinja_env = JinjaEnv(autoescape=True)
    jinja_template = jinja_env.from_string(template_source)

    # Setup Kida
    kida_env = KidaEnv(autoescape=True)
    kida_template = kida_env.from_string(template_source)

    # Warmup
    for _ in range(10):
        jinja_template.render(**context)
        kida_template.render(**context)

    # Benchmark Jinja2
    start = time.perf_counter()
    for _ in range(iterations):
        jinja_template.render(**context)
    jinja_time = time.perf_counter() - start

    # Benchmark Kida
    start = time.perf_counter()
    for _ in range(iterations):
        kida_template.render(**context)
    kida_time = time.perf_counter() - start

    return BenchmarkResult(
        name=template_source[:30] if len(template_source) > 30 else template_source,
        jinja_time=jinja_time,
        kida_time=kida_time,
    )


def run_simple_benchmarks() -> list[BenchmarkResult]:
    """Run benchmarks on simple templates."""
    context = {
        "name": "World",
        "items": list(range(100)),
        "pages": [{"title": f"Page {i}"} for i in range(100)],
        "page": {"title": "Test", "draft": False, "metadata": {"author": "Test"}},
    }

    results = []
    for name, source in SIMPLE_TEMPLATES.items():
        result = benchmark_template(source, context, iterations=10000)
        result.name = name
        results.append(result)

    return results


# =============================================================================
# pytest-benchmark integration
# =============================================================================


@pytest.fixture
def simple_context() -> dict[str, Any]:
    """Simple context for benchmarks."""
    return {
        "name": "World",
        "items": list(range(100)),
        "pages": [{"title": f"Page {i}"} for i in range(100)],
        "page": {"title": "Test", "draft": False, "metadata": {"author": "Test"}},
    }


@pytest.fixture
def jinja_env():
    """Jinja2 environment."""
    from jinja2 import Environment

    return Environment(autoescape=True)


@pytest.fixture
def kida_env():
    """Kida environment."""
    from bengal.rendering.kida import Environment

    return Environment(autoescape=True)


@pytest.mark.parametrize("template_name,template_source", SIMPLE_TEMPLATES.items())
def test_kida_faster_than_jinja(
    benchmark, template_name, template_source, simple_context, jinja_env, kida_env
):
    """Verify Kida is faster than Jinja2 on simple templates."""
    # Compile templates
    jinja_template = jinja_env.from_string(template_source)
    kida_template = kida_env.from_string(template_source)

    # Verify same output
    jinja_result = jinja_template.render(**simple_context)
    kida_result = kida_template.render(**simple_context)
    assert jinja_result == kida_result, f"Output mismatch for {template_name}"

    # Benchmark Kida
    benchmark(kida_template.render, **simple_context)


def test_loop_performance(benchmark, simple_context, kida_env):
    """Benchmark loop with 1000 items."""
    template = kida_env.from_string("{% for i in items %}{{ i }}{% endfor %}")
    context = {"items": list(range(1000))}
    benchmark(template.render, **context)


def test_nested_loop_performance(benchmark, simple_context, kida_env):
    """Benchmark nested loops."""
    template = kida_env.from_string(
        "{% for row in rows %}{% for col in row %}{{ col }}{% endfor %}{% endfor %}"
    )
    context = {"rows": [[j for j in range(10)] for i in range(100)]}
    benchmark(template.render, **context)


def test_filter_chain_performance(benchmark, simple_context, kida_env):
    """Benchmark filter chains."""
    template = kida_env.from_string("{{ text | upper | trim | replace('A', 'X') }}")
    context = {"text": "  hello world  " * 100}
    benchmark(template.render, **context)


def test_conditional_performance(benchmark, simple_context, kida_env):
    """Benchmark conditionals."""
    template = kida_env.from_string(
        "{% if x > 50 %}big{% elif x > 25 %}medium{% else %}small{% endif %}"
    )
    for x in range(100):
        template.render(x=x)


# =============================================================================
# Standalone runner
# =============================================================================


def main():
    """Run benchmarks and print results."""
    print("=" * 80)
    print("Kida vs Jinja2 Benchmark")
    print("=" * 80)
    print()

    try:
        results = run_simple_benchmarks()

        print(f"{'Template':30} | {'Jinja2':>12} | {'Kida':>12} | {'Speedup':>10}")
        print("-" * 80)

        total_jinja = 0.0
        total_kida = 0.0
        wins = 0

        for result in results:
            print(result)
            total_jinja += result.jinja_time
            total_kida += result.kida_time
            if result.speedup > 1.0:
                wins += 1

        print("-" * 80)
        avg_speedup = total_jinja / total_kida if total_kida > 0 else 0
        print(
            f"{'TOTAL':30} | {total_jinja * 1000:8.3f}ms | "
            f"{total_kida * 1000:8.3f}ms | {avg_speedup:5.1f}x"
        )
        print()
        print(f"Kida wins: {wins}/{len(results)} benchmarks")
        print(f"Average speedup: {avg_speedup:.1f}x")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure both jinja2 and kida are installed.")
        return 1

    except Exception as e:
        print(f"Error running benchmarks: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
