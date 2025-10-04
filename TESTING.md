# Testing Guide for Bengal SSG

## Running Tests

### Setup

Install development dependencies:

```bash
pip install -e ".[dev]"
```

This installs:
- pytest
- pytest-cov (coverage)
- pytest-mock (mocking)
- pytest-xdist (parallel testing)
- black, mypy, ruff (linting)

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=bengal --cov-report=html

# Run in parallel (faster)
pytest -n auto
```

### Run Specific Tests

```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/rendering/test_template_errors.py

# Run specific test class
pytest tests/unit/rendering/test_template_errors.py::TestTemplateRenderError

# Run specific test
pytest tests/unit/rendering/test_template_errors.py::TestTemplateRenderError::test_error_classification_syntax
```

### Run Performance Benchmarks

```bash
# Run benchmarks (not part of regular test suite)
python tests/performance/benchmark_full_build.py
python tests/performance/benchmark_ssg_comparison.py
```

## Test Organization

```
tests/
├── unit/                          # Fast, isolated unit tests
│   ├── cache/                     # Cache and dependency tracking
│   ├── core/                      # Core functionality
│   ├── rendering/                 # Rendering pipeline
│   │   ├── test_template_errors.py       # NEW: Error system tests
│   │   ├── test_template_validator.py    # NEW: Validator tests
│   │   ├── test_mistune_parser.py
│   │   └── test_crossref.py
│   └── template_functions/        # Template function tests
├── integration/                   # End-to-end integration tests
│   ├── test_template_error_collection.py  # NEW: Error collection tests
│   ├── test_cascade_integration.py
│   └── test_output_quality.py
├── performance/                   # Performance benchmarks
│   ├── benchmark_full_build.py
│   ├── benchmark_ssg_comparison.py
│   └── ...
└── fixtures/                      # Test data and fixtures
    ├── configs/
    ├── content/
    └── sites/
```

## New Tests Added (Template Error System)

### Unit Tests

#### `tests/unit/rendering/test_template_errors.py`
Tests for the rich error system:
- Error context creation
- Inclusion chain formatting
- Error classification (syntax, filter, undefined, runtime)
- Error creation from Jinja2 exceptions
- Suggestion generation
- Alternative filter finding
- Error display formatting

Run with:
```bash
pytest tests/unit/rendering/test_template_errors.py -v
```

#### `tests/unit/rendering/test_template_validator.py`
Tests for template validation:
- Validator initialization
- Syntax validation
- Include validation
- Multiple template scanning
- Edge cases (empty files, nested directories)

Run with:
```bash
pytest tests/unit/rendering/test_template_validator.py -v
```

### Integration Tests

#### `tests/integration/test_template_error_collection.py`
Tests for error collection during builds:
- Valid template building
- Error collection without crashing
- Multiple error collection
- Strict mode behavior
- Parallel error collection
- Rich error information verification

Run with:
```bash
pytest tests/integration/test_template_error_collection.py -v
```

## Writing Tests

### Unit Test Example

```python
import pytest
from bengal.rendering.errors import TemplateRenderError

class TestMyFeature:
    """Test suite for my feature."""
    
    def test_something(self):
        """Test that something works."""
        result = my_function()
        assert result == expected_value
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError, match="Expected error"):
            my_function_that_raises()
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing."""
        file = tmp_path / "test.txt"
        file.write_text("test content")
        return file
```

### Integration Test Example

```python
from pathlib import Path
from bengal.core.site import Site

def test_full_build_workflow(tmp_path):
    """Test complete build workflow."""
    # Setup site structure
    (tmp_path / "content").mkdir()
    (tmp_path / "bengal.toml").write_text("""
[site]
title = "Test"
""")
    
    # Build site
    site = Site.from_config(tmp_path, None)
    stats = site.build()
    
    # Verify results
    assert stats.total_pages > 0
    assert (tmp_path / "public" / "index.html").exists()
```

## Test Coverage

View coverage report:

```bash
# Generate coverage
pytest --cov=bengal --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Target coverage: **>80%** for core modules

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Release tags

CI runs:
```bash
pytest -v --cov=bengal --cov-report=xml
```

## Debugging Tests

### Use pytest's built-in debugger

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show local variables on failure
pytest -l
```

### Use print debugging

```bash
# Show print output
pytest -s

# Show more verbose output
pytest -vv
```

### Run single test with debugging

```bash
# Run specific test with prints and locals
pytest tests/unit/rendering/test_template_errors.py::TestTemplateRenderError::test_error_classification_syntax -svl
```

## Common Issues

### Import Errors

If you get import errors:
```bash
# Make sure Bengal is installed in development mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Fixture Not Found

Make sure you're using pytest fixtures correctly:
```python
def test_with_fixture(tmp_path):  # tmp_path is built-in
    # tmp_path is provided by pytest
    pass
```

### Tests Pass Locally But Fail in CI

- Check file paths (use `Path` objects, not strings)
- Check for timing issues (use appropriate timeouts)
- Check for platform-specific code (Windows vs Unix)

## Best Practices

1. **One concept per test** - Test one thing at a time
2. **Clear test names** - Name should describe what's being tested
3. **Use fixtures** - Reuse setup code with fixtures
4. **Fast tests** - Unit tests should be < 100ms
5. **Isolated tests** - Tests shouldn't depend on each other
6. **Use tmp_path** - Don't create files in project directory
7. **Mock external dependencies** - Don't hit real APIs/files
8. **Test edge cases** - Empty inputs, None values, errors

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest parametrize](https://docs.pytest.org/en/stable/parametrize.html)
- [Coverage.py](https://coverage.readthedocs.io/)

## Questions?

See `tests/unit/rendering/test_mistune_parser.py` for examples of well-structured tests.

