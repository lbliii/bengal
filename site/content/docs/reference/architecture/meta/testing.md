---
title: Testing Strategy
description: Testing patterns and coverage goals
weight: 20
category: meta
tags:
- meta
- testing
- test-strategy
- unit-tests
- integration-tests
- benchmarks
- coverage
keywords:
- testing
- test strategy
- unit tests
- integration tests
- benchmarks
- coverage
- pytest
---

# Testing Strategy

Bengal maintains high code quality through a multi-layered testing strategy with 4,000+ tests.

## Test Layers

:::{cards}
:columns: 3
:gap: medium
:variant: concept

:::{card} Unit Tests
:icon: code
**Fast & Focused** (`tests/unit/`)
Test individual classes/functions. Mock external deps.
**Target**: 90%+ coverage.
:::

:::{card} Integration Tests
:icon: recycle
**Workflows** (`tests/integration/`)
Test subsystem interactions and build flows. Verify cache.
:::

:::{card} Benchmarks
:icon: zap
**Performance** (`tests/performance/`)
Measure speed on large sites. Catch regressions.
:::
:::{/cards}

## Quick Start

```bash
# Fast feedback loop (recommended during development)
pytest -m "not slow" -n auto  # ~20 seconds

# Unit tests only
pytest tests/unit -n auto  # ~8 seconds

# Full suite
pytest  # ~60 seconds
```

## Test Infrastructure

### Test Roots

Minimal, reusable site structures in `tests/roots/`:

| Root | Purpose | Pages |
|------|---------|-------|
| `test-basic` | Minimal smoke test | 1 |
| `test-directives` | Card, admonition, glossary | 4+ |
| `test-navigation` | Multi-level hierarchy | 8 |
| `test-large` | Performance testing | 100+ |

```python
@pytest.mark.bengal(testroot="test-directives")
def test_card_directive(site, build_site):
    build_site()
    assert "card-grid" in (site.output_dir / "cards/index.html").read_text()
```

### Canonical Mocks

Use shared mocks instead of inline class definitions:

```python
from tests._testing.mocks import MockPage, MockSection, MockSite

page = MockPage(title="Test", url="/test/", tags=["python"])
site = MockSite(pages=[page])
```

### Module-Scoped Fixtures

Rendering tests use module-scoped parser for efficiency:

```python
# In tests/unit/rendering/
def test_markdown(parser):  # Parser created once per module
    result = parser.parse("# Hello", {})
    assert "<h1>" in result
```

## Key Testing Patterns

### 1. Declarative Test Sites

```python
@pytest.mark.bengal(testroot="test-basic", confoverrides={"site.title": "Custom"})
def test_with_overrides(site):
    assert site.title == "Custom"
```

### 2. Property-Based Testing

For critical utilities, we use `hypothesis` to test edge cases (116 tests, 11,600+ examples).

### 3. Parallel Safety

Mark tests with internal parallelism:

```python
@pytest.mark.parallel_unsafe  # Prevents xdist worker crashes
def test_concurrent_operations():
    with ThreadPoolExecutor() as ex:
        ...
```

## Continuous Integration

Every PR runs:
1. **Linting**: `ruff` check and format
2. **Type Checking**: `mypy` strict mode
3. **Test Suite**: Unit + integration (`-m "not slow"`)
4. **Full Suite**: On main/release branches

See `tests/README.md` for complete documentation.
