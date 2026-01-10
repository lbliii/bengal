#!/usr/bin/env python3
"""Benchmark comparing regex-based vs state-machine lexers.

Run with: python -m benchmarks.lexer_benchmark
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def load_sample_code() -> str:
    """Load a sample Python file for benchmarking.

    Uses the lexer implementation itself as a reasonably complex sample.
    """
    # Try to load a substantial Python file
    candidates = [
        # Rosettes is now an external package - use fallback synthetic code
        # These paths no longer exist in Bengal
    ]

    for path in candidates:
        if path.exists():
            return path.read_text()

    # Fallback: generate synthetic code
    return generate_synthetic_code(10000)


def generate_synthetic_code(lines: int) -> str:
    """Generate synthetic Python code for benchmarking."""
    parts = [
        '"""Synthetic Python code for benchmarking."""',
        "",
        "import os",
        "import sys",
        "from pathlib import Path",
        "",
    ]

    for i in range(lines):
        if i % 10 == 0:
            parts.append(f"\n\nclass Class{i}:")
            parts.append(f'    """Docstring for Class{i}."""')
            parts.append("")
        elif i % 5 == 0:
            parts.append(f"    def method_{i}(self, arg1: str, arg2: int = 42) -> bool:")
            parts.append('        """Method docstring."""')
            parts.append("        # This is a comment")
            parts.append('        result = f"Value: {arg1}, {arg2}"')
            parts.append("        return len(result) > 0")
        else:
            parts.append(f"        x_{i} = {i} + 0x{i:04x} + 0b{i % 256:08b}")

    return "\n".join(parts)


def benchmark_lexer(
    name: str,
    tokenize_func: callable,
    code: str,
    iterations: int = 10,
) -> dict:
    """Benchmark a lexer.

    Args:
        name: Name of the lexer.
        tokenize_func: Function that takes code and returns tokens.
        code: Source code to tokenize.
        iterations: Number of iterations to run.

    Returns:
        Dictionary with benchmark results.
    """
    times = []
    token_count = 0

    # Warmup
    list(tokenize_func(code))

    for _ in range(iterations):
        start = time.perf_counter()
        tokens = list(tokenize_func(code))
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        token_count = len(tokens)

    return {
        "name": name,
        "iterations": iterations,
        "code_size": len(code),
        "token_count": token_count,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "avg_ms": sum(times) / len(times) * 1000,
        "tokens_per_sec": token_count / (sum(times) / len(times)),
        "mb_per_sec": len(code) / 1024 / 1024 / (sum(times) / len(times)),
    }


def print_results(results: list[dict]) -> None:
    """Print benchmark results in a table."""
    print("\n" + "=" * 80)
    print("LEXER BENCHMARK RESULTS")
    print("=" * 80)

    if not results:
        print("No results to display.")
        return

    # Header
    print(f"{'Lexer':<25} {'Avg (ms)':<12} {'Min (ms)':<12} {'Tokens/sec':<15} {'MB/sec':<10}")
    print("-" * 80)

    # Sort by average time
    for r in sorted(results, key=lambda x: x["avg_ms"]):
        print(
            f"{r['name']:<25} {r['avg_ms']:<12.3f} {r['min_ms']:<12.3f} "
            f"{r['tokens_per_sec']:<15,.0f} {r['mb_per_sec']:<10.2f}"
        )

    print("-" * 80)
    print(f"Code size: {results[0]['code_size']:,} bytes")
    print(f"Tokens: {results[0]['token_count']:,}")
    print(f"Iterations: {results[0]['iterations']}")

    # Calculate speedup
    if len(results) >= 2:
        sorted_results = sorted(results, key=lambda x: x["avg_ms"])
        fastest = sorted_results[0]
        slowest = sorted_results[-1]
        speedup = slowest["avg_ms"] / fastest["avg_ms"]
        print(f"\nSpeedup ({fastest['name']} vs {slowest['name']}): {speedup:.2f}x")

    print("=" * 80)


def main() -> None:
    """Run the benchmark."""
    print("Loading sample code...")
    code = load_sample_code()
    print(f"Sample code size: {len(code):,} bytes, {code.count(chr(10)):,} lines")

    results = []

    # Benchmark rosettes state-machine lexer (external package)
    try:
        from rosettes import get_lexer

        python_lexer = get_lexer("python")
        print("\nBenchmarking rosettes PythonStateMachineLexer...")
        result = benchmark_lexer("rosettes (state-machine)", python_lexer.tokenize, code)
        results.append(result)
    except ImportError as e:
        print(f"Could not import rosettes: {e}")

    # Print results
    print_results(results)

    # Test with larger synthetic code
    print("\n" + "=" * 80)
    print("LARGE FILE BENCHMARK (synthetic 100K lines)")
    print("=" * 80)

    large_code = generate_synthetic_code(100_000)
    print(f"Large code size: {len(large_code):,} bytes")

    large_results = []

    try:
        from rosettes import get_lexer

        python_lexer = get_lexer("python")
        print("\nBenchmarking rosettes PythonStateMachineLexer on large file...")
        result = benchmark_lexer(
            "rosettes (state-machine)",
            python_lexer.tokenize,
            large_code,
            iterations=3,
        )
        large_results.append(result)
    except ImportError:
        pass

    print_results(large_results)


if __name__ == "__main__":
    main()
