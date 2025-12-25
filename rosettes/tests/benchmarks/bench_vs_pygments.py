"""Benchmark Rosettes vs Pygments performance.

Run with:
    python tests/benchmarks/bench_vs_pygments.py

Or with pytest-benchmark:
    pytest tests/benchmarks/ -v
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


# Sample code for benchmarking
PYTHON_CODE = '''
def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    """A simple calculator with history tracking."""

    def __init__(self) -> None:
        self.history: list[str] = []

    def add(self, a: float, b: float) -> float:
        """Add two numbers and record the operation."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers and record the operation."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result


# Example usage
if __name__ == "__main__":
    calc = Calculator()
    print(calc.add(10, 20))
    print(fibonacci(10))
'''

JS_CODE = """
const fibonacci = (n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
};

class Calculator {
    constructor() {
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }

    async fetchData(url) {
        const response = await fetch(url);
        return response.json();
    }
}

export { Calculator, fibonacci };
"""

JSON_CODE = """
{
    "name": "rosettes",
    "version": "0.1.0",
    "dependencies": {
        "python": ">=3.12"
    },
    "features": ["free-threading", "streaming", "lazy-loading"],
    "metrics": {
        "import_time_ms": 5,
        "memory_per_block_bytes": 200
    }
}
"""


@dataclass
class BenchmarkResult:
    """Results from a single benchmark."""

    name: str
    language: str
    iterations: int
    total_ms: float
    per_call_ms: float
    chars: int
    chars_per_ms: float


def bench_function(
    fn: Callable[[], str],
    name: str,
    language: str,
    code: str,
    iterations: int = 1000,
) -> BenchmarkResult:
    """Benchmark a function."""
    # Warm up
    for _ in range(10):
        fn()

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter() - start

    total_ms = elapsed * 1000
    per_call_ms = total_ms / iterations
    chars = len(code)
    chars_per_ms = (chars * iterations) / total_ms

    return BenchmarkResult(
        name=name,
        language=language,
        iterations=iterations,
        total_ms=total_ms,
        per_call_ms=per_call_ms,
        chars=chars,
        chars_per_ms=chars_per_ms,
    )


def benchmark_rosettes(code: str, language: str, iterations: int = 1000) -> BenchmarkResult:
    """Benchmark Rosettes highlighting."""
    from rosettes import get_lexer
    from rosettes._config import FormatConfig
    from rosettes.formatters import HtmlFormatter

    # Pre-create objects like Pygments benchmark does
    lexer = get_lexer(language)
    formatter = HtmlFormatter()
    config = FormatConfig()

    def fn() -> str:
        return formatter.format_string_fast(lexer.tokenize_fast(code), config)

    return bench_function(fn, "rosettes", language, code, iterations)


def benchmark_pygments(code: str, language: str, iterations: int = 1000) -> BenchmarkResult:
    """Benchmark Pygments highlighting."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name

    lexer = get_lexer_by_name(language)
    formatter = HtmlFormatter()

    def fn() -> str:
        return highlight(code, lexer, formatter)

    return bench_function(fn, "pygments", language, code, iterations)


def measure_import_time(module_name: str) -> float:
    """Measure cold import time in milliseconds."""
    import subprocess
    import sys

    code = f"""
import time
start = time.perf_counter()
import {module_name}
elapsed = time.perf_counter() - start
print(elapsed * 1000)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def print_results(results: list[tuple[BenchmarkResult, BenchmarkResult]]) -> None:
    """Print benchmark results as a table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS: Rosettes vs Pygments")
    print("=" * 80)

    for rosettes, pygments in results:
        speedup = pygments.per_call_ms / rosettes.per_call_ms
        print(f"\n{rosettes.language.upper()} ({rosettes.chars} chars):")
        print(
            f"  Rosettes: {rosettes.per_call_ms:.4f}ms/call ({rosettes.chars_per_ms:.0f} chars/ms)"
        )
        print(
            f"  Pygments: {pygments.per_call_ms:.4f}ms/call ({pygments.chars_per_ms:.0f} chars/ms)"
        )
        print(f"  Speedup:  {speedup:.2f}x {'✅' if speedup >= 1 else '⚠️'}")


def run_benchmarks() -> None:
    """Run all benchmarks."""
    print("Rosettes vs Pygments Benchmark Suite")
    print("-" * 40)

    # Import time comparison
    print("\n📊 Import Time:")
    try:
        rosettes_import = measure_import_time("rosettes")
        print(f"  Rosettes: {rosettes_import:.1f}ms")
    except Exception as e:
        print(f"  Rosettes: Error - {e}")
        rosettes_import = float("inf")

    try:
        pygments_import = measure_import_time("pygments")
        print(f"  Pygments: {pygments_import:.1f}ms")
    except Exception as e:
        print(f"  Pygments: Error - {e}")
        pygments_import = float("inf")

    if rosettes_import < float("inf") and pygments_import < float("inf"):
        print(f"  Speedup:  {pygments_import / rosettes_import:.2f}x")

    # Highlighting benchmarks
    print("\n📊 Highlighting Performance (1000 iterations):")
    test_cases = [
        (PYTHON_CODE, "python"),
        (JS_CODE, "javascript"),
        (JSON_CODE, "json"),
    ]

    results: list[tuple[BenchmarkResult, BenchmarkResult]] = []
    for code, language in test_cases:
        try:
            rosettes_result = benchmark_rosettes(code, language)
            pygments_result = benchmark_pygments(code, language)
            results.append((rosettes_result, pygments_result))
        except Exception as e:
            print(f"  {language}: Error - {e}")

    print_results(results)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if results:
        avg_speedup = sum(p.per_call_ms / r.per_call_ms for r, p in results) / len(results)
        print(f"Average speedup: {avg_speedup:.2f}x")
        if avg_speedup >= 2:
            print("🎉 Rosettes is significantly faster!")
        elif avg_speedup >= 1:
            print("✅ Rosettes meets performance target")
        else:
            print("⚠️ Rosettes is slower than Pygments")


# Pytest-benchmark compatible tests
def test_rosettes_python(benchmark) -> None:
    """Pytest-benchmark: Rosettes Python highlighting."""
    from rosettes import highlight

    benchmark(highlight, PYTHON_CODE, "python")


def test_pygments_python(benchmark) -> None:
    """Pytest-benchmark: Pygments Python highlighting."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer

    lexer = PythonLexer()
    formatter = HtmlFormatter()

    def fn():
        return highlight(PYTHON_CODE, lexer, formatter)

    benchmark(fn)


def test_rosettes_javascript(benchmark) -> None:
    """Pytest-benchmark: Rosettes JavaScript highlighting."""
    from rosettes import highlight

    benchmark(highlight, JS_CODE, "javascript")


def test_pygments_javascript(benchmark) -> None:
    """Pytest-benchmark: Pygments JavaScript highlighting."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import JavaScriptLexer

    lexer = JavaScriptLexer()
    formatter = HtmlFormatter()

    def fn():
        return highlight(JS_CODE, lexer, formatter)

    benchmark(fn)


if __name__ == "__main__":
    run_benchmarks()
