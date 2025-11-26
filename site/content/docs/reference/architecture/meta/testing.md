---
title: Testing Strategy
description: Testing patterns and coverage goals
weight: 20
category: meta
tags: [meta, testing, test-strategy, unit-tests, integration-tests, benchmarks, coverage]
keywords: [testing, test strategy, unit tests, integration tests, benchmarks, coverage, pytest]
---

# Testing Strategy

Bengal maintains high code quality through a multi-layered testing strategy.

## Test Layers

::::{cards}
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
:icon: git-merge
**Workflows** (`tests/integration/`)
Test subsystem interactions and build flows. Verify cache.
:::

:::{card} Benchmarks
:icon: activity
**Performance** (`tests/performance/`)
Measure speed on large sites. Catch regressions.
:::
::::

## Key Testing Patterns

### 1. Fixtures

We use `pytest` fixtures extensively for setup/teardown.

```python
@pytest.fixture
def site(tmp_path):
    """Create a configured site instance."""
    root = tmp_path / "site"
    # ... setup structure ...
    return Site.from_config(root)
```

### 2. Snapshot Testing

For complex outputs (like HTML generation), we compare against known-good snapshots.

### 3. Property-Based Testing

For critical utilities (like slug generation), we use `hypothesis` to test edge cases.

## Continuous Integration

Every PR runs:
1.  **Linting**: `ruff` check and format.
2.  **Type Checking**: `mypy` strict mode.
3.  **Test Suite**: All unit and integration tests.
4.  **Benchmarks**: Verified against baseline.
