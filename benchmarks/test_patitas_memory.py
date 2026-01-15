"""
Patitas vs Mistune Memory Usage Comparison.

Measures memory consumption during parsing of various document sizes.

Run with:
    python benchmarks/test_patitas_memory.py

Expected results (RFC target: ≤60% of Mistune memory):
    - Patitas should use less memory due to StringBuilder pattern
    - Memory advantage should be more pronounced on large documents

Related:
    - plan/drafted/rfc-patitas-markdown-parser.md
    - bengal/rendering/parsers/patitas/stringbuilder.py
"""

import gc
import tracemalloc
from statistics import mean


def measure_memory(func, *args, iterations=10):
    """Measure peak memory usage of a function.

    Returns (mean_peak_kb, measurements).
    """
    measurements = []

    for _ in range(iterations):
        # Force garbage collection
        gc.collect()

        # Start tracing
        tracemalloc.start()

        try:
            func(*args)
        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        measurements.append(peak / 1024)  # Convert to KB

    return mean(measurements), measurements


# Test documents
SMALL_DOC = """
# Heading 1

This is a paragraph with **bold** and *italic* text.

## Heading 2

- List item 1
- List item 2

```python
def hello():
    print("Hello!")
```
"""

MEDIUM_DOC = (
    """
# API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List users |
| POST | /users | Create user |

```python
def api_call():
    return {"status": "ok"}
```

> Note: This is important.
"""
    * 5
)

LARGE_DOC = MEDIUM_DOC * 10


def main():
    print("=" * 70)
    print("Patitas vs Mistune Memory Usage Comparison")
    print("=" * 70)
    print()

    # Setup parsers
    from bengal.parsing.backends.mistune import MistuneParser
    from bengal.parsing.backends.patitas import create_markdown

    mistune_parser = MistuneParser(enable_highlighting=False)
    patitas_md = create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )

    def mistune_parse(doc):
        return mistune_parser.parse(doc, {})

    def patitas_parse(doc):
        return patitas_md(doc)

    # Warm up
    for _ in range(3):
        mistune_parse(SMALL_DOC)
        patitas_parse(SMALL_DOC)

    # Test each document size
    docs = [
        ("Small (~200 chars)", SMALL_DOC),
        ("Medium (~1500 chars)", MEDIUM_DOC),
        ("Large (~15000 chars)", LARGE_DOC),
    ]

    results = []

    for name, doc in docs:
        print(f"{name}:")
        print(f"  Document size: {len(doc):,} chars")

        mistune_mem, _ = measure_memory(mistune_parse, doc)
        patitas_mem, _ = measure_memory(patitas_parse, doc)

        ratio = patitas_mem / mistune_mem if mistune_mem > 0 else 0
        savings = (1 - ratio) * 100

        print(f"  Mistune:  {mistune_mem:,.1f} KB")
        print(f"  Patitas:  {patitas_mem:,.1f} KB")
        print(f"  Ratio:    {ratio:.2f}x ({savings:+.1f}% memory)")
        print()

        results.append(
            {
                "name": name,
                "doc_size": len(doc),
                "mistune_kb": mistune_mem,
                "patitas_kb": patitas_mem,
                "ratio": ratio,
                "savings_pct": savings,
            }
        )

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    avg_ratio = mean(r["ratio"] for r in results)
    avg_savings = mean(r["savings_pct"] for r in results)

    print(f"Average memory ratio: {avg_ratio:.2f}x")
    print(f"Average memory savings: {avg_savings:+.1f}%")
    print()

    # Check RFC target
    target_ratio = 0.60
    if avg_ratio <= target_ratio:
        print(f"✅ RFC target met: Patitas uses ≤{target_ratio * 100:.0f}% of Mistune memory")
    else:
        print(f"⚠️  RFC target: ≤{target_ratio * 100:.0f}% of Mistune memory")
        print(f"    Actual: {avg_ratio * 100:.1f}%")

    return results


if __name__ == "__main__":
    main()
