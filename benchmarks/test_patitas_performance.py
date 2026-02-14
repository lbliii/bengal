"""
Patitas vs Mistune Parser Performance Benchmarks.

Compares Patitas (O(n) state-machine parser) against Mistune (regex-based parser)
across various document sizes and feature sets.

Run with:
    pytest benchmarks/test_patitas_performance.py -v --benchmark-only

Expected results (per patitas/docs/performance-investigation.md):
    - Patitas is ~2x slower than mistune on typical documents (architectural)
    - Mistune uses C-accelerated regex; Patitas is pure Python with typed AST
    - Patitas trades raw speed for: O(n) ReDoS-proof parsing, typed AST,
      full thread-safety (free-threading), and incremental re-parse (~200x faster
      for small edits)
    - Regression threshold: Patitas should not exceed ~3x slower than mistune

Related:
    - plan/drafted/rfc-patitas-markdown-parser.md
    - patitas/docs/performance-investigation.md
    - bengal/parsing/backends/patitas/
"""

import pytest

# Test documents with various Markdown features
SMALL_DOC = """
# Heading 1

This is a paragraph with **bold** and *italic* text.

## Heading 2

- List item 1
- List item 2
  - Nested item

```python
def hello():
    print("Hello, World!")
```

> Block quote with **emphasis**.

[Link text](https://example.com)
"""

MEDIUM_DOC_WITH_TABLE = """
# API Reference

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

```bash
curl -H "Authorization: Bearer <token>" https://api.example.com/users
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
"""

FEATURE_RICH_DOC = """
# Complete Feature Test

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


@pytest.fixture(scope="module")
def mistune_parser():
    """Create Mistune parser instance (skipped if mistune backend not available)."""
    try:
        from bengal.parsing.backends.mistune import MistuneParser

        return MistuneParser(enable_highlighting=False)
    except ImportError:
        pytest.skip("Mistune backend not available (Bengal may use Patitas-only)")


@pytest.fixture(scope="module")
def patitas_parser():
    """Create Patitas parser instance."""
    from bengal.parsing.backends.patitas import create_markdown

    return create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )


# =============================================================================
# Small Document Benchmarks
# =============================================================================


class TestSmallDocument:
    """Benchmarks for small documents (~200 chars)."""

    def test_mistune_small(self, benchmark, mistune_parser):
        """Mistune: Parse small document."""
        result = benchmark(mistune_parser.parse, SMALL_DOC, {})
        assert "<h1" in result  # May have id attribute

    def test_patitas_small(self, benchmark, patitas_parser):
        """Patitas: Parse small document."""
        result = benchmark(patitas_parser, SMALL_DOC)
        assert "<h1" in result  # May have id attribute


# =============================================================================
# Medium Document Benchmarks (with tables)
# =============================================================================


class TestMediumDocument:
    """Benchmarks for medium documents with tables (~800 chars)."""

    def test_mistune_medium(self, benchmark, mistune_parser):
        """Mistune: Parse medium document with tables."""
        result = benchmark(mistune_parser.parse, MEDIUM_DOC_WITH_TABLE, {})
        assert "<table>" in result

    def test_patitas_medium(self, benchmark, patitas_parser):
        """Patitas: Parse medium document with tables."""
        result = benchmark(patitas_parser, MEDIUM_DOC_WITH_TABLE)
        assert "<table>" in result


# =============================================================================
# Feature-Rich Document Benchmarks
# =============================================================================


class TestFeatureRichDocument:
    """Benchmarks for documents using many Markdown features."""

    def test_mistune_features(self, benchmark, mistune_parser):
        """Mistune: Parse feature-rich document."""
        result = benchmark(mistune_parser.parse, FEATURE_RICH_DOC, {})
        assert "<del>" in result  # Strikethrough

    def test_patitas_features(self, benchmark, patitas_parser):
        """Patitas: Parse feature-rich document."""
        result = benchmark(patitas_parser, FEATURE_RICH_DOC)
        assert "<del>" in result  # Strikethrough


# =============================================================================
# Large Document Benchmarks (stress test)
# =============================================================================


class TestLargeDocument:
    """Benchmarks for large documents (10x medium doc)."""

    @pytest.fixture
    def large_doc(self):
        return MEDIUM_DOC_WITH_TABLE * 10

    def test_mistune_large(self, benchmark, mistune_parser, large_doc):
        """Mistune: Parse large document."""
        result = benchmark(mistune_parser.parse, large_doc, {})
        assert result.count("<table>") == 20  # 2 tables * 10 repeats

    def test_patitas_large(self, benchmark, patitas_parser, large_doc):
        """Patitas: Parse large document."""
        result = benchmark(patitas_parser, large_doc)
        assert result.count("<table>") == 20  # 2 tables * 10 repeats


# =============================================================================
# Very Large Document Benchmarks (50x for scaling analysis)
# =============================================================================


class TestVeryLargeDocument:
    """Benchmarks for very large documents (50x medium doc)."""

    @pytest.fixture
    def very_large_doc(self):
        return MEDIUM_DOC_WITH_TABLE * 50

    def test_mistune_very_large(self, benchmark, mistune_parser, very_large_doc):
        """Mistune: Parse very large document."""
        benchmark.pedantic(
            mistune_parser.parse,
            args=(very_large_doc, {}),
            rounds=10,
            iterations=1,
        )

    def test_patitas_very_large(self, benchmark, patitas_parser, very_large_doc):
        """Patitas: Parse very large document."""
        benchmark.pedantic(
            patitas_parser,
            args=(very_large_doc,),
            rounds=10,
            iterations=1,
        )


# =============================================================================
# Comparative Summary Test
# =============================================================================


class TestPerformanceComparison:
    """Direct comparison tests that track Patitas vs Mistune ratio."""

    def test_patitas_vs_mistune_ratio(self, mistune_parser, patitas_parser):
        """Track Patitas vs Mistune parse time ratio (informational + regression guard)."""
        import time

        # Warm up
        for _ in range(5):
            mistune_parser.parse(MEDIUM_DOC_WITH_TABLE, {})
            patitas_parser(MEDIUM_DOC_WITH_TABLE)

        # Benchmark
        iterations = 100

        # Mistune timing
        start = time.perf_counter()
        for _ in range(iterations):
            mistune_parser.parse(MEDIUM_DOC_WITH_TABLE, {})
        mistune_time = time.perf_counter() - start

        # Patitas timing
        start = time.perf_counter()
        for _ in range(iterations):
            patitas_parser(MEDIUM_DOC_WITH_TABLE)
        patitas_time = time.perf_counter() - start

        # Patitas is typically ~2x slower (pure Python vs C-accelerated mistune)
        ratio = patitas_time / mistune_time
        slowdown_percent = (ratio - 1) * 100

        print(f"\nPerformance comparison ({iterations} iterations):")
        print(f"  Mistune total: {mistune_time * 1000:.2f}ms")
        print(f"  Patitas total: {patitas_time * 1000:.2f}ms")
        print(f"  Ratio (Patitas/Mistune): {ratio:.2f}x")
        print(f"  Patitas slowdown: {slowdown_percent:.1f}%")

        # Regression guard: Patitas should not exceed ~3x slower than mistune
        # (per performance-investigation.md, ~2x is expected; 3x suggests regression)
        if ratio > 3.0:
            pytest.fail(
                f"Patitas performance regression: {ratio:.2f}x slower than Mistune "
                f"(expected ~2x). See patitas/docs/performance-investigation.md."
            )
