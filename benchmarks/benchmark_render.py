#!/usr/bin/env python3
"""HtmlRenderer Performance Benchmarks.

Measures HtmlRenderer performance for Phase 3 decomposition gate.

RFC Gate Criteria:
- < 5% regression after decomposition
- Must maintain ≥100 pages/sec render rate

Run with:
    # Standard pytest benchmark
    uv run pytest benchmarks/benchmark_render.py -v --benchmark-only
    
    # Direct execution (no pytest)
    uv run python benchmarks/benchmark_render.py
    
    # Save baseline for comparison
    uv run pytest benchmarks/benchmark_render.py --benchmark-save=render-baseline
    
    # Compare against baseline
    uv run pytest benchmarks/benchmark_render.py --benchmark-compare=render-baseline

Output JSON (for CI):
    uv run python benchmarks/benchmark_render.py --output reports/render-baseline.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

# =============================================================================
# Test Documents
# =============================================================================

SIMPLE_DOC = """# Hello World

This is a simple paragraph.

- Item 1
- Item 2
"""

MEDIUM_DOC = """# API Reference

This document describes the **REST API** endpoints.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List all users |
| POST | /users | Create a new user |
| GET | /users/:id | Get user by ID |
| PUT | /users/:id | Update user |
| DELETE | /users/:id | Delete user |

## Authentication

Use the `Authorization` header with a bearer token:

```python
import requests

headers = {"Authorization": f"Bearer {token}"}
response = requests.get("https://api.example.com/users", headers=headers)
```

### Response Format

All responses return JSON:

```json
{
    "data": {...},
    "meta": {"page": 1, "total": 100}
}
```

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Server Error |

> **Note**: Rate limiting applies to all endpoints.

### Links

- [Documentation](https://docs.example.com)
- [API Status](https://status.example.com)
"""

COMPLEX_DOC = """# Complete Feature Test

This document tests **all major** Markdown features.

## Text Formatting

- **Bold text**
- *Italic text*
- ~~Strikethrough text~~
- `Inline code`
- ***Bold and italic***

## Lists

### Unordered
- Item 1
- Item 2
  - Nested 2.1
  - Nested 2.2
    - Deep nested
- Item 3

### Ordered
1. First
2. Second
3. Third

## Code Blocks

```python
def fibonacci(n: int) -> int:
    '''Calculate Fibonacci number.'''
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

```javascript
const add = (a, b) => a + b;
console.log(add(1, 2));
```

## Tables

| Feature | Patitas | Mistune |
|---------|:-------:|--------:|
| O(n) parsing | ✅ | ❌ |
| Typed AST | ✅ | ❌ |
| Thread-safe | ✅ | ⚠️ |

## Block Quotes

> This is a block quote.
>
> It can span multiple lines.
>
> > And can be nested.

## Links and Images

- [External link](https://example.com)
- [Link with title](https://example.com "Example Site")
- ![Alt text](image.png)

## Math (when enabled)

Inline math: $E = mc^2$

Block math:
$$
\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$

## Horizontal Rules

---

***

___
"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def patitas_parser():
    """Create Patitas parser with plugins."""
    from bengal.parsing.backends.patitas import create_markdown

    return create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,  # Disable highlighting for consistent benchmarks
    )


@pytest.fixture(scope="module")
def patitas_markdown():
    """Create Markdown instance for AST generation."""
    from bengal.parsing.backends.patitas import create_markdown

    return create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )


# =============================================================================
# Parse + Render Benchmarks (end-to-end)
# =============================================================================


class TestEndToEndRender:
    """End-to-end parse + render benchmarks."""

    def test_simple_doc(self, benchmark, patitas_parser):
        """Simple document (5 blocks)."""
        result = benchmark(patitas_parser, SIMPLE_DOC)
        assert "<h1" in result
        assert "<ul>" in result

    def test_medium_doc(self, benchmark, patitas_parser):
        """Medium document with tables (~30 blocks)."""
        result = benchmark(patitas_parser, MEDIUM_DOC)
        assert "<table>" in result
        assert "<pre><code" in result

    def test_complex_doc(self, benchmark, patitas_parser):
        """Complex document with all features (~50 blocks)."""
        result = benchmark(patitas_parser, COMPLEX_DOC)
        assert "<del>" in result  # Strikethrough
        assert "<table>" in result
        assert "<blockquote>" in result


# =============================================================================
# Render-Only Benchmarks (AST pre-parsed)
# =============================================================================


class TestRenderOnly:
    """Benchmarks for HtmlRenderer.render() with pre-parsed AST."""

    @pytest.fixture
    def simple_ast(self, patitas_markdown):
        """Pre-parsed AST for simple document."""
        return patitas_markdown.parse_to_ast(SIMPLE_DOC)

    @pytest.fixture
    def medium_ast(self, patitas_markdown):
        """Pre-parsed AST for medium document."""
        return patitas_markdown.parse_to_ast(MEDIUM_DOC)

    @pytest.fixture
    def complex_ast(self, patitas_markdown):
        """Pre-parsed AST for complex document."""
        return patitas_markdown.parse_to_ast(COMPLEX_DOC)

    def test_render_simple(self, benchmark, patitas_markdown, simple_ast):
        """Render simple AST."""
        result = benchmark(patitas_markdown.render_ast, simple_ast, SIMPLE_DOC)
        assert "<h1" in result

    def test_render_medium(self, benchmark, patitas_markdown, medium_ast):
        """Render medium AST with tables."""
        result = benchmark(patitas_markdown.render_ast, medium_ast, MEDIUM_DOC)
        assert "<table>" in result

    def test_render_complex(self, benchmark, patitas_markdown, complex_ast):
        """Render complex AST with all features."""
        result = benchmark(patitas_markdown.render_ast, complex_ast, COMPLEX_DOC)
        assert "<del>" in result
        assert "<table>" in result


# =============================================================================
# Throughput Benchmarks
# =============================================================================


class TestThroughput:
    """Throughput benchmarks measuring pages/sec."""

    def test_100_page_throughput(self, patitas_parser):
        """Measure pages/second for 100-page batch."""
        pages = [MEDIUM_DOC] * 100

        # Warm up
        for _ in range(10):
            patitas_parser(MEDIUM_DOC)

        # Benchmark
        start = time.perf_counter()
        for page in pages:
            patitas_parser(page)
        elapsed = time.perf_counter() - start

        pages_per_sec = len(pages) / elapsed

        print(f"\nThroughput: {pages_per_sec:.1f} pages/sec")
        print(f"Total time: {elapsed * 1000:.1f}ms for {len(pages)} pages")
        print(f"Per-page: {elapsed / len(pages) * 1000:.2f}ms")

        # RFC gate: must maintain ≥100 pages/sec
        assert pages_per_sec >= 100, f"Performance below threshold: {pages_per_sec:.1f} pages/sec"

    def test_render_only_throughput(self, patitas_parser):
        """Measure render-only throughput (AST pre-parsed)."""
        from bengal.parsing.backends.patitas import create_markdown

        md = create_markdown(
            plugins=["table", "strikethrough", "math"],
            highlight=False,
        )

        # Pre-parse AST
        ast = md.parse_to_ast(MEDIUM_DOC)

        # Warm up
        for _ in range(10):
            md.render_ast(ast, MEDIUM_DOC)

        # Benchmark
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            md.render_ast(ast, MEDIUM_DOC)
        elapsed = time.perf_counter() - start

        renders_per_sec = iterations / elapsed

        print(f"\nRender-only throughput: {renders_per_sec:.1f} renders/sec")
        print(f"Total time: {elapsed * 1000:.1f}ms for {iterations} renders")
        print(f"Per-render: {elapsed / iterations * 1000:.3f}ms")


# =============================================================================
# Direct Execution (without pytest-benchmark)
# =============================================================================


def run_benchmarks(output_path: str | None = None) -> dict:
    """Run benchmarks and optionally save to JSON."""
    from bengal.parsing.backends.patitas import create_markdown

    # Setup
    parser = create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )

    # Pre-parse ASTs using the Markdown instance
    medium_ast = parser.parse_to_ast(MEDIUM_DOC)
    complex_ast = parser.parse_to_ast(COMPLEX_DOC)

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmarks": {},
    }

    def benchmark(name: str, func, iterations: int = 100):
        """Run a benchmark and record results."""
        # Warm up
        for _ in range(min(10, iterations)):
            func()

        # Benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            times.append(time.perf_counter() - start)

        mean = sum(times) / len(times)
        stddev = (sum((t - mean) ** 2 for t in times) / len(times)) ** 0.5
        min_time = min(times)
        max_time = max(times)

        results["benchmarks"][name] = {
            "mean_ms": mean * 1000,
            "stddev_ms": stddev * 1000,
            "min_ms": min_time * 1000,
            "max_ms": max_time * 1000,
            "iterations": iterations,
            "ops_per_sec": 1 / mean,
        }

        return mean, stddev

    # Run benchmarks
    print("=" * 60)
    print("HTMLRENDERER PERFORMANCE BENCHMARK")
    print("=" * 60)
    print()

    # End-to-end benchmarks
    print("End-to-End (Parse + Render):")
    mean, stddev = benchmark("e2e_medium", lambda: parser(MEDIUM_DOC), 500)
    print(f"  Medium doc: {mean * 1000:.3f}ms ± {stddev * 1000:.3f}ms")

    mean, stddev = benchmark("e2e_complex", lambda: parser(COMPLEX_DOC), 500)
    print(f"  Complex doc: {mean * 1000:.3f}ms ± {stddev * 1000:.3f}ms")

    print()

    # Render-only benchmarks
    print("Render-Only (AST pre-parsed):")
    mean, stddev = benchmark("render_medium", lambda: parser.render_ast(medium_ast, MEDIUM_DOC), 1000)
    print(f"  Medium doc: {mean * 1000:.3f}ms ± {stddev * 1000:.3f}ms")

    mean, stddev = benchmark("render_complex", lambda: parser.render_ast(complex_ast, COMPLEX_DOC), 1000)
    print(f"  Complex doc: {mean * 1000:.3f}ms ± {stddev * 1000:.3f}ms")

    print()

    # Throughput test
    print("Throughput (100-page batch):")
    pages = [MEDIUM_DOC] * 100
    start = time.perf_counter()
    for page in pages:
        parser(page)
    elapsed = time.perf_counter() - start
    pages_per_sec = len(pages) / elapsed

    results["throughput"] = {
        "pages_per_sec": pages_per_sec,
        "total_ms": elapsed * 1000,
        "per_page_ms": elapsed / len(pages) * 1000,
    }

    print(f"  {pages_per_sec:.1f} pages/sec")
    print(f"  {elapsed / len(pages) * 1000:.2f}ms per page")
    print()

    # Gate check
    gate_passed = pages_per_sec >= 100
    results["gate_passed"] = gate_passed

    if gate_passed:
        print("✅ Performance gate PASSED: ≥100 pages/sec")
    else:
        print(f"❌ Performance gate FAILED: {pages_per_sec:.1f} < 100 pages/sec")

    print()
    print("=" * 60)

    # Save to file if requested
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {path}")

    return results


def main():
    """CLI entry point."""
    arg_parser = argparse.ArgumentParser(description="HtmlRenderer Performance Benchmark")
    arg_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output JSON file path (e.g., reports/render-baseline.json)",
    )
    arg_parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=100,
        help="Number of iterations per benchmark",
    )

    args = arg_parser.parse_args()

    try:
        results = run_benchmarks(args.output)
        sys.exit(0 if results["gate_passed"] else 1)
    except ImportError as e:
        print(f"Error: Could not import Bengal. Run from project root: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
