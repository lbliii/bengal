"""Comprehensive Kida benchmark: compilation + rendering, simple + complex templates.

This benchmark measures:
1. Template compilation time (cold start)
2. Template rendering time (hot path)
3. Simple vs complex template performance
4. Loop performance at different scales

Run with:
    python benchmarks/test_kida_comprehensive.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

BENGAL_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = BENGAL_ROOT / "bengal" / "themes" / "default" / "templates"


def create_context() -> dict[str, Any]:
    """Create realistic template context."""
    return {
        "page": {
            "title": "Getting Started with Bengal",
            "content": "<p>Welcome to Bengal documentation.</p>" * 10,
            "excerpt": "Learn how to get started with Bengal SSG.",
            "date": "2025-12-25",
            "draft": False,
            "tags": ["python", "ssg", "documentation"],
            "metadata": {"author": "Bengal Team"},
        },
        "site": {
            "title": "Bengal Documentation",
            "url": "https://lbliii.github.io/bengal",
            "pages": [{"title": f"Page {i}", "href": f"/page-{i}/"} for i in range(100)],
        },
        "name": "World",
        "items": list(range(1000)),
    }


def benchmark_compilation_and_rendering(
    template_source: str, context: dict[str, Any], iterations: int = 1000
) -> dict[str, float]:
    """Benchmark both compilation and rendering times."""
    from kida import Environment

    env = Environment(autoescape=True)

    # Measure compilation time (cold start)
    compile_times = []
    for _ in range(10):
        start = time.perf_counter()
        template = env.from_string(template_source)
        compile_times.append(time.perf_counter() - start)

    # Get the compiled template
    template = env.from_string(template_source)

    # Warmup rendering
    for _ in range(10):
        template.render(**context)

    # Measure rendering time (hot path)
    start = time.perf_counter()
    for _ in range(iterations):
        template.render(**context)
    render_time = time.perf_counter() - start

    return {
        "compile_time_ms": (sum(compile_times) / len(compile_times)) * 1000,
        "render_time_ms": (render_time / iterations) * 1000,
        "total_time_ms": (sum(compile_times) / len(compile_times) + render_time / iterations)
        * 1000,
    }


def run_comprehensive_benchmarks():
    """Run comprehensive benchmarks."""
    print("=" * 90)
    print("Kida Comprehensive Performance Benchmark")
    print("=" * 90)
    print()

    context = create_context()

    # Test cases: (name, template_source, iterations)
    test_cases = [
        # Simple operations
        ("Simple variable", "{{ name }}", 10000),
        ("Nested attribute", "{{ page.metadata.author }}", 10000),
        ("Filter chain", "{{ name | upper | trim }}", 10000),
        ("Conditional", "{% if page.draft %}Draft{% else %}Published{% end %}", 10000),
        # Loops at different scales
        ("Loop (10 items)", "{% for i in items[:10] %}{{ i }}{% end %}", 1000),
        ("Loop (100 items)", "{% for i in items[:100] %}{{ i }}{% end %}", 1000),
        ("Loop (1000 items)", "{% for i in items %}{{ i }}{% end %}", 100),
        # Complex operations
        (
            "Loop with conditional",
            "{% for p in site.pages %}{% if not p.draft %}{{ p.title }}{% end %}{% end %}",
            100,
        ),
        (
            "Nested loops",
            "{% for p in site.pages[:10] %}{% for tag in page.tags %}{{ tag }}{% end %}{% end %}",
            100,
        ),
        # Real-world patterns
        ("Complex expression", "{{ 'Draft' if page.draft else page.title }}", 10000),
        ("Filter with args", "{{ page.tags | join(', ') }}", 10000),
    ]

    print(f"{'Test Case':40} | {'Compile':>10} | {'Render':>10} | {'Total':>10}")
    print("-" * 90)

    results = []
    for name, template_source, iterations in test_cases:
        try:
            metrics = benchmark_compilation_and_rendering(template_source, context, iterations)
            results.append((name, metrics))
            print(
                f"{name:40} | {metrics['compile_time_ms']:8.2f}ms | "
                f"{metrics['render_time_ms']:8.2f}ms | {metrics['total_time_ms']:8.2f}ms"
            )
        except Exception as e:
            print(f"{name:40} | ERROR: {e}")

    print("-" * 90)
    print()

    # Summary statistics
    if results:
        avg_compile = sum(r[1]["compile_time_ms"] for r in results) / len(results)
        avg_render = sum(r[1]["render_time_ms"] for r in results) / len(results)
        avg_total = sum(r[1]["total_time_ms"] for r in results) / len(results)

        print("Summary Statistics:")
        print(f"  Average compilation time: {avg_compile:.2f}ms")
        print(f"  Average rendering time:   {avg_render:.2f}ms")
        print(f"  Average total time:       {avg_total:.2f}ms")
        print()

        # Find slowest operations
        slowest_compile = max(results, key=lambda x: x[1]["compile_time_ms"])
        slowest_render = max(results, key=lambda x: x[1]["render_time_ms"])

        print("Slowest Operations:")
        print(
            f"  Compilation: {slowest_compile[0]} ({slowest_compile[1]['compile_time_ms']:.2f}ms)"
        )
        print(f"  Rendering:   {slowest_render[0]} ({slowest_render[1]['render_time_ms']:.2f}ms)")

    # Test with real template files (Kida syntax)
    print()
    print("=" * 90)
    print("Real Template Files (Kida Syntax)")
    print("=" * 90)
    print()

    real_templates = [
        ("partials/header.html", "Header partial"),
        ("partials/footer.html", "Footer partial"),
        ("tags.html", "Tags listing"),
        ("404.html", "404 page"),
    ]

    print(f"{'Template':40} | {'Compile':>10} | {'Render':>10} | {'Total':>10}")
    print("-" * 90)

    real_results = []
    for filename, _description in real_templates:
        path = TEMPLATES_DIR / filename
        if not path.exists():
            print(f"{filename:40} | NOT FOUND")
            continue

        try:
            template_source = path.read_text()
            metrics = benchmark_compilation_and_rendering(template_source, context, iterations=100)
            real_results.append((filename, metrics))
            print(
                f"{filename:40} | {metrics['compile_time_ms']:8.2f}ms | "
                f"{metrics['render_time_ms']:8.2f}ms | {metrics['total_time_ms']:8.2f}ms"
            )
        except Exception as e:
            print(f"{filename:40} | ERROR: {e}")

    print("-" * 90)

    if real_results:
        avg_compile_real = sum(r[1]["compile_time_ms"] for r in real_results) / len(real_results)
        avg_render_real = sum(r[1]["render_time_ms"] for r in real_results) / len(real_results)

        print()
        print("Real Templates Summary:")
        print(f"  Average compilation: {avg_compile_real:.2f}ms")
        print(f"  Average rendering:  {avg_render_real:.2f}ms")


if __name__ == "__main__":
    try:
        run_comprehensive_benchmarks()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure bengal is installed.")
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
