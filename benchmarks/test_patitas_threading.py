"""
Patitas Free-Threading Stress Tests.

Validates that Patitas scales correctly across multiple threads on Python 3.14t.
Tests parallel parsing with no GIL contention.

Run with:
    python benchmarks/test_patitas_threading.py

Requirements:
    - Python 3.14+ with free-threading (python3.14t)
    - No GIL: sys._is_gil_enabled() should return False

Expected results:
    - Near-linear scaling up to CPU core count
    - No race conditions or data corruption
    - Consistent output across all threads

Related:
    - plan/drafted/rfc-patitas-markdown-parser.md (Phase 5)
    - PEP 703: Making the Global Interpreter Lock Optional
"""

import concurrent.futures
import sys
import time
from hashlib import sha256


def check_free_threading():
    """Check if running on free-threaded Python."""
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()
    return False


# Test document with various features
TEST_DOC = """
# API Documentation

This document describes the **REST API** with *emphasis* on correctness.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List all users |
| POST | /users | Create user |
| DELETE | /users/:id | Delete user |

## Code Example

```python
import requests

def get_users():
    response = requests.get("/users")
    return response.json()
```

> **Note**: All endpoints require authentication.

## Features

- ~~Deprecated~~ endpoints are marked
- Task lists: [x] Complete, [ ] Incomplete
- Math: $E = mc^2$

[Link to docs](https://example.com)
"""


def main():
    print("=" * 70)
    print("Patitas Free-Threading Stress Test")
    print("=" * 70)
    print()
    print(f"Python: {sys.version}")
    print(f"Free-threaded: {check_free_threading()}")
    print()

    if not check_free_threading():
        print("⚠️  Warning: Not running on free-threaded Python.")
        print("   Results may show GIL contention.")
        print()

    # Setup parser
    from bengal.parsing.backends.patitas import create_markdown

    patitas_md = create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )

    def parse_doc(doc):
        """Parse a document and return its hash for verification."""
        result = patitas_md(doc)
        return sha256(result.encode()).hexdigest()

    # Create test workload
    num_docs = 200
    documents = [TEST_DOC] * num_docs

    # Warm up
    for doc in documents[:5]:
        parse_doc(doc)

    # Get expected hash (all docs should produce same output)
    expected_hash = parse_doc(TEST_DOC)

    print(f"Workload: {num_docs} documents")
    print(f"Expected hash: {expected_hash[:16]}...")
    print()
    print("-" * 70)

    results = {}

    # Sequential baseline
    print("Sequential (1 thread):")
    start = time.perf_counter()
    hashes = [parse_doc(doc) for doc in documents]
    sequential_time = time.perf_counter() - start
    all_correct = all(h == expected_hash for h in hashes)
    results[1] = sequential_time
    print(f"  Time: {sequential_time * 1000:.1f}ms")
    print(f"  Correct: {'✅' if all_correct else '❌'}")
    print()

    # Parallel tests
    for num_threads in [2, 4, 8, 16]:
        print(f"Parallel ({num_threads} threads):")
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            hashes = list(executor.map(parse_doc, documents))
        parallel_time = time.perf_counter() - start
        results[num_threads] = parallel_time

        all_correct = all(h == expected_hash for h in hashes)
        speedup = sequential_time / parallel_time
        efficiency = speedup / num_threads * 100

        print(f"  Time: {parallel_time * 1000:.1f}ms")
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Efficiency: {efficiency:.0f}%")
        print(f"  Correct: {'✅' if all_correct else '❌'}")
        print()

    # Summary
    print("-" * 70)
    print("Summary")
    print("-" * 70)
    print()

    # Check for scaling
    speedup_4 = results[1] / results[4]
    speedup_8 = results[1] / results[8]

    print(f"4-thread speedup: {speedup_4:.2f}x")
    print(f"8-thread speedup: {speedup_8:.2f}x")
    print()

    # Verify results
    if speedup_4 >= 1.5:
        print("✅ Good parallel scaling (4 threads ≥1.5x)")
    else:
        print("⚠️  Limited parallel scaling on 4 threads")

    if all_correct:
        print("✅ All outputs consistent (no race conditions)")
    else:
        print("❌ Output mismatch detected (possible race condition)")

    return results


if __name__ == "__main__":
    main()
