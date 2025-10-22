# Bengal Testing Strategy

**Version**: 2.0  
**Last Updated**: 2025-10-22  
**Status**: Production-Ready

---

## Overview

This document outlines Bengal's comprehensive testing strategy, covering unit tests, integration tests, property-based testing, and test organization principles.

## Testing Philosophy

### Core Principles

1. **Test what matters most**: Focus on critical path (core build pipeline) with 75-100% coverage
2. **Property-based testing**: Use Hypothesis to find edge cases automatically (116 tests, 11,600+ examples)
3. **Fast feedback**: Full test suite runs in ~45 seconds
4. **Realistic tests**: Integration tests use real file systems and build workflows
5. **Intentional gaps**: Don't waste time testing interactive UIs and network-dependent code

### Coverage Goals

- **Overall target**: 70% (currently 68-70%)
- **Critical path target**: 80%+ (currently 75-100%)
- **Quality over quantity**: Well-tested critical code beats superficial coverage

## Test Organization

### Directory Structure

```
tests/
├── unit/                    # Unit tests (component isolation)
│   ├── core/               # Core objects (Page, Section, Site)
│   ├── rendering/          # Template engine, parsers, errors
│   ├── orchestration/      # Build orchestration, content processing
│   ├── utils/              # Utilities (with property tests)
│   ├── health/             # Health validators
│   ├── cli/                # CLI command tests
│   └── ...
├── integration/            # Integration tests (multi-component)
│   ├── stateful/          # State machine tests
│   └── ...
├── performance/            # Performance and benchmark tests
├── manual/                 # Manual testing scenarios
└── conftest.py            # Shared fixtures and configuration
```

### Test Markers

```python
@pytest.mark.unit           # Fast, isolated unit tests
@pytest.mark.integration    # Multi-component tests
@pytest.mark.e2e           # End-to-end workflow tests
@pytest.mark.hypothesis    # Property-based tests
@pytest.mark.slow          # Long-running tests (>10s)
@pytest.mark.performance   # Performance/benchmark tests
@pytest.mark.parallel_unsafe  # Must run sequentially
```

## Test Types

### 1. Unit Tests (~2,650 tests)

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (<1s per test typically)
- Mocked dependencies
- Single responsibility
- High coverage of edge cases

**Example**:
```python
def test_page_url_generation(tmp_path):
    """Test URL generation for a page."""
    page = Page(source_path=tmp_path / "post.md")
    page.metadata = {"title": "Test Post"}
    assert page.url == "/post/"
```

### 2. Property-Based Tests (116 tests)

**Purpose**: Find edge cases automatically through randomized testing

**Characteristics**:
- Uses Hypothesis framework
- Generates 100+ examples per test
- Tests invariants, not specific cases
- Excellent for finding bugs in text processing, URLs, paths

**Example**:
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_slugify_is_url_safe(text):
    """Test that slugified text is always URL-safe."""
    slug = slugify(text)
    assert slug == urllib.parse.quote(slug, safe="")
```

**Areas using property tests**:
- URL strategy (14 tests)
- Path utilities (19 tests)
- Text processing (25 tests)
- Pagination (16 tests)
- Date handling (23 tests)
- Slugification (18 tests)

### 3. Integration Tests (~150 tests)

**Purpose**: Test multi-component interactions and workflows

**Characteristics**:
- Real file system usage
- Multiple components working together
- Realistic build scenarios
- Slower than unit tests but still fast (~15s total)

**Example**:
```python
def test_full_site_build_url_consistency(tmp_path):
    """Test that URLs are consistent across full build."""
    # Create site structure
    create_test_site(tmp_path)
    
    # Build site
    site = Site.from_config(tmp_path)
    site.discover_content()
    site.build()
    
    # Verify URL consistency
    assert_url_consistency(site)
```

**Key integration test scenarios**:
- Full → Incremental build sequences
- Template error collection
- Resource cleanup
- Cache migration
- URL consistency across components
- Error recovery scenarios

### 4. Performance Tests

**Purpose**: Ensure builds remain fast and memory-efficient

**Characteristics**:
- Excluded from default test runs (`@pytest.mark.performance`)
- Measure build time, memory usage, parallelization
- Run nightly or on-demand

**Example**:
```python
@pytest.mark.performance
def test_large_site_build_performance(tmp_path):
    """Test build performance with 1000+ pages."""
    create_large_site(tmp_path, num_pages=1000)
    
    start = time.time()
    site = Site.from_config(tmp_path)
    site.build()
    duration = time.time() - start
    
    assert duration < 60.0  # Should build in under 60s
```

## Testing Patterns

### Fixture Organization

**Session-scoped**: Expensive setup, shared across all tests
```python
@pytest.fixture(scope="session")
def sample_config_immutable():
    """Read-only config for tests that don't modify it."""
    return {"site": {"title": "Test"}, ...}
```

**Class-scoped**: Shared within test class
```python
@pytest.fixture(scope="class")
def class_tmp_site(tmp_path_factory):
    """Shared site for class tests."""
    return setup_test_site(tmp_path_factory.mktemp("site"))
```

**Function-scoped**: Fresh for each test (default)
```python
@pytest.fixture
def tmp_site(tmp_path):
    """Fresh site for each test."""
    return tmp_path
```

### Parametrized Tests

Use `@pytest.mark.parametrize` for testing multiple cases:

```python
@pytest.mark.parametrize("input,expected", [
    ("Hello World", "hello-world"),
    ("Python 3.14", "python-314"),
    ("Café", "cafe"),
])
def test_slugify(input, expected):
    assert slugify(input) == expected
```

**Benefits**:
- 2.6x better visibility than loops
- Each case reported separately
- Instant identification of failing cases

### Mock Usage

**When to mock**:
- External services (network, filesystem in some cases)
- Expensive operations
- Dependencies outside test scope

**When NOT to mock**:
- Core business logic
- Integration tests
- File system in integration tests (use tmp_path instead)

```python
from unittest.mock import Mock, patch

@patch('bengal.health.validators.connectivity.KnowledgeGraph')
def test_connectivity_validation(mock_kg_class, validator, site):
    """Test connectivity validator with mocked graph."""
    mock_graph = Mock()
    mock_graph.get_orphans.return_value = []
    mock_kg_class.return_value = mock_graph
    
    results = validator.validate(site)
    assert len(results) > 0
```

## Recent Improvements (October 2025)

### Added Tests

1. **Health Validators** (+70 tests)
   - Navigation validator: next/prev chains, breadcrumbs, sections
   - Taxonomy validator: tag pages, archives, pagination
   - Connectivity validator: orphans, hubs, graph metrics
   - Coverage: 12-24% → 60%+

2. **Rendering Error Handling** (+85 tests)
   - Message extraction (variables, filters, dict attributes)
   - Enhanced suggestion generation
   - Error classification edge cases
   - Context extraction with invalid data
   - Coverage: 54% → 70%

3. **CLI Commands** (+50 tests)
   - Programmatic build command tests
   - Clean command tests
   - Project validation tests
   - Graph command help tests
   - Coverage: 9-13% → 30-55%

4. **Error Recovery** (+35 tests)
   - Template error recovery
   - Missing file handling
   - Invalid configuration recovery
   - Partial build completion
   - Concurrent build resilience

### Total Impact
- **+240 tests** added
- **Overall coverage**: 65% → 68-70%
- **Health validators**: 12-24% → 60%+
- **Rendering errors**: 54% → 70%
- **CLI commands**: 9-13% → 30-55%

## Running Tests

### Quick Commands

```bash
# Run all tests (fast PR default: excludes performance/stateful)
pytest

# Run all tests including slow ones
pytest -m ""

# Run unit tests only
pytest tests/unit

# Run integration tests only
pytest tests/integration

# Run property tests only
pytest -m hypothesis

# Run with coverage report
pytest --cov=bengal --cov-report=html

# Run specific test file
pytest tests/unit/core/test_page.py

# Run specific test
pytest tests/unit/core/test_page.py::test_page_creation

# Run with verbose output
pytest -v

# Run in parallel (faster)
pytest -n auto
```

### CI/CD Configuration

**Fast PR checks** (default):
```bash
pytest -n auto -m "not performance and not stateful"
```

**Nightly comprehensive**:
```bash
pytest -n auto -m ""
```

**Coverage reporting**:
```bash
pytest --cov=bengal --cov-report=html --cov-report=term
```

## Best Practices

### Writing Good Tests

1. **Clear test names**: Describe what is being tested
   ```python
   # Good
   def test_page_url_generation_with_baseurl():
       ...
   
   # Bad
   def test_page():
       ...
   ```

2. **One assertion focus**: Test one thing at a time
   ```python
   # Good
   def test_slugify_lowercases():
       assert slugify("HELLO") == "hello"
   
   def test_slugify_replaces_spaces():
       assert slugify("hello world") == "hello-world"
   
   # Bad (tests multiple things)
   def test_slugify():
       assert slugify("HELLO") == "hello"
       assert slugify("hello world") == "hello-world"
       assert slugify("Café") == "cafe"
   ```

3. **Arrange-Act-Assert** pattern:
   ```python
   def test_page_creation():
       # Arrange
       source_path = tmp_path / "page.md"
       
       # Act
       page = Page(source_path=source_path)
       
       # Assert
       assert page.source_path == source_path
   ```

4. **Use fixtures** for common setup:
   ```python
   @pytest.fixture
   def sample_page(tmp_path):
       path = tmp_path / "page.md"
       path.write_text("---\ntitle: Test\n---\nContent")
       return Page(source_path=path)
   
   def test_page_title(sample_page):
       assert sample_page.metadata["title"] == "Test"
   ```

### Property Test Guidelines

1. **Test invariants**, not specific values
   ```python
   # Good: Tests invariant
   @given(st.text())
   def test_slugify_idempotent(text):
       """Slugify should be idempotent."""
       slug = slugify(text)
       assert slugify(slug) == slug
   
   # Bad: Tests specific value
   @given(st.text())
   def test_slugify_specific(text):
       assert slugify(text) == expected_value  # Wrong!
   ```

2. **Use appropriate strategies**
   ```python
   from hypothesis import strategies as st
   
   # Text that could be user input
   @given(st.text(min_size=1, max_size=100))
   
   # Valid URLs
   @given(st.from_regex(r"^/[a-z0-9-/]*/$"))
   
   # Valid dates
   @given(st.dates())
   ```

3. **Keep property tests fast**: Use `max_examples` for slow operations
   ```python
   from hypothesis import settings
   
   @settings(max_examples=10)  # Default is 100
   @given(st.text())
   def test_expensive_operation(text):
       ...
   ```

## Debugging Failed Tests

### Reading Test Output

pytest provides detailed failure information:

```
FAILED tests/unit/core/test_page.py::test_page_url - AssertionError
_________________________________ test_page_url __________________________________

    def test_page_url():
        page = Page(source_path=Path("/test/page.md"))
>       assert page.url == "/page/"
E       AssertionError: assert '/test/page/' == '/page/'
E         - /page/
E         + /test/page/

tests/unit/core/test_page.py:42: AssertionError
```

### Auto-saved Failure Details

Bengal's test suite automatically saves failure details to `.pytest_cache/last_failure.txt`:

```
================================================================================
PYTEST FAILURE DETAILS
================================================================================
Timestamp: 2025-10-22T14:30:00
Test: tests/unit/core/test_page.py::test_page_url
Location: ('tests/unit/core/test_page.py', 40, 'test_page_url')

FAILURE DETAILS:
--------------------------------------------------------------------------------
AssertionError: assert '/test/page/' == '/page/'
...
```

### Debugging Tips

1. **Use `-v` for verbose output**: Shows all test names
2. **Use `-s` to see print statements**: Disables output capture
3. **Use `--pdb` to drop into debugger**: On failure
4. **Use `-x` to stop on first failure**: Fast feedback
5. **Use `--lf` to run last failed**: Quickly re-run failures

```bash
# Debug failing test
pytest tests/unit/core/test_page.py::test_page_url -v -s --pdb
```

## Continuous Improvement

### Areas for Future Enhancement

1. **Dev server testing**: Specialized WebSocket/HTTP testing framework (currently 0-18%)
2. **Interactive CLI testing**: UI testing tools or acceptance tests (currently 13-30%)
3. **Visual regression testing**: Screenshot comparison for theme changes
4. **Load testing**: High-scale site builds (1000+ pages)

### Monitoring Test Health

- **Coverage trends**: Track coverage over time
- **Test duration**: Keep full suite under 60 seconds
- **Flaky tests**: Identify and fix tests that fail randomly
- **Test count per module**: Ensure balanced coverage

### Contributing New Tests

When adding features, include:

1. **Unit tests** for new functions/classes
2. **Integration tests** for multi-component features
3. **Property tests** for text/data processing
4. **Update TEST_COVERAGE.md** with new coverage metrics

## Conclusion

Bengal's testing strategy prioritizes:
- **High coverage of critical code** (75-100%)
- **Fast feedback loops** (~45 seconds)
- **Property-based testing** for automatic edge case discovery
- **Realistic integration tests** for confidence
- **Intentional gaps** in hard-to-test areas (UI, network)

This approach provides strong protection for business logic while remaining maintainable and fast.

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-22  
**Maintainer**: Bengal Testing Team
