# Testing Strategy

Bengal uses a comprehensive testing approach with pytest and coverage tracking.

## Test Infrastructure

**Location:** `tests/` directory with organized structure:
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for workflows
- `tests/e2e/` - End-to-end tests with example sites
- `tests/performance/` - Performance benchmarks
- `tests/fixtures/` - Shared test data
- `tests/conftest.py` - Shared pytest fixtures

**Tools:**
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-xdist` - Parallel test execution
- `ruff` - Linting
- `mypy` - Type checking

## Coverage Goals

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| **Utilities** | | | |
| Utils - Text | 95%+ | 91% | ✅ 74 tests |
| Utils - Date | 95%+ | 91% | ✅ 56 tests |
| Utils - File I/O | 95%+ | 23-91% | ⚠️ 54 tests (coverage grows with adoption) |
| Utils - Paginator | 95%+ | 96% | ✅ 10 tests |
| **Core Systems** | | | |
| Cache (BuildCache, DependencyTracker) | 95%+ | 95% | ✅ 32 tests |
| Postprocess (RSS, Sitemap) | 95%+ | 96% | ✅ Complete |
| Core Navigation & Menu | 90%+ | 98% | ✅ 13 tests |
| **Orchestration & Rendering** | | | |
| Orchestration (Taxonomy, Asset, Render) | 85%+ | 78-91% | ✅ Tested |
| Template Functions (16 modules) | 85%+ | 44-98% | ✅ 335+ tests |
| Rendering Pipeline | 80%+ | 71-87% | ⚠️ Partial |
| Parallel Processing | 80%+ | 90% | ✅ 12 tests |
| **Quality & Discovery** | | | |
| Health Validators (10 validators) | 75%+ | 13-98% | ⚠️ In Progress |
| Discovery (Content, Asset) | 80%+ | 75-81% | ⚠️ In Progress |
| Page Metadata | 85%+ | 86% | ✅ Improved (+146%) |
| **Entry Points** | | | |
| CLI | 75%+ | 0% | ❌ Not Started |
| Dev Server | 75%+ | 0% | ❌ Not Started |
| **Overall** | **85%** | **~68%** | 🎯 **Gap: 17%** (improved +4%) |

**Test Statistics:**
- Total tests: 1,084+ passing
- Test execution time: ~20 seconds (excluding performance benchmarks)
- Performance benchmarks: Separate suite with longer-running tests

## Test Types

1. **Unit Tests**
   - Test individual components in isolation
   - Fast execution (< 1 second)
   - Mock external dependencies
   - Examples:
     - `tests/unit/utils/test_text.py` (74 tests, 91% coverage)
     - `tests/unit/utils/test_dates.py` (56 tests, 91% coverage)
     - `tests/unit/utils/test_file_io.py` (54 tests, 23-91% coverage)
     - `tests/unit/utils/test_pagination.py` (10 tests, 96% coverage)

2. **Integration Tests**
   - Test component interactions
   - Full build workflows
   - Theme rendering
   - Example: Building a complete site from content

3. **End-to-End Tests**
   - Build example sites
   - Verify output correctness
   - Real-world scenarios

4. **Performance Tests**
   - Build speed benchmarks (`tests/performance/benchmark_*.py`)
   - Memory usage profiling (`tests/performance/test_memory_profiling.py`)
   - Large site stress tests

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=bengal

# Specific test file
pytest tests/unit/utils/test_pagination.py

# Parallel execution
pytest -n auto

# Generate HTML coverage report
pytest --cov=bengal --cov-report=html

# Performance tests
pytest tests/performance/benchmark_full_build.py -v

# Memory profiling tests (shows detailed output)
pytest tests/performance/test_memory_profiling.py -v -s

# Specific memory test with allocator details
pytest tests/performance/test_memory_profiling.py::TestMemoryProfiling::test_build_with_detailed_allocators -v -s
```
