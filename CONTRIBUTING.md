# Contributing to Bengal SSG

Thank you for your interest in contributing to Bengal! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.14 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Setup Development Environment

**Using uv (recommended):**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd bengal

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

**Using pip:**

```bash
# Clone the repository
git clone <repository-url>
cd bengal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Project Structure

```
bengal/
├── bengal/              # Main package
│   ├── core/           # Core object model
│   ├── rendering/      # Rendering pipeline
│   ├── discovery/      # Content/asset discovery
│   ├── config/         # Configuration system
│   ├── postprocess/    # Post-processing tools
│   ├── server/         # Dev server
│   ├── themes/         # Default themes
│   └── cli.py          # CLI interface
├── examples/           # Example sites
├── tests/              # Test suite
└── docs/               # Documentation
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Follow PEP 8 style guidelines
- Add docstrings to functions and classes
- Keep commits focused and atomic
- Write descriptive commit messages

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bengal

# Run specific test file
pytest tests/test_page.py
```

### 4. Format and Lint Code

```bash
# Format code with ruff
ruff format bengal/

# Lint and auto-fix with ruff
ruff check --fix bengal/

# Type check with mypy
mypy bengal/
```

### 5. Submit Pull Request

- Push your branch to GitHub
- Create a pull request with a clear description
- Link any related issues
- Wait for review and address feedback

## Code Style

### Python Style

Bengal uses **Python 3.14+** features and modern syntax:

**Type Hints:**
- ✅ Use `X | Y` instead of `Union[X, Y]`
- ✅ Use `X | None` instead of `Optional[X]`
- ✅ Use `type` keyword for type aliases
- ✅ Use PEP 695 generic syntax for generic classes
- ✅ No quotes needed for type annotations (we use `from __future__ import annotations`)
- ✅ Use `isinstance(obj, Type1 | Type2)` instead of `isinstance(obj, (Type1, Type2))`

**General:**
- Follow PEP 8
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all public functions/classes

Example:
```python
from __future__ import annotations

from pathlib import Path

def parse_content(
    file_path: Path,
    encoding: str = 'utf-8'
) -> tuple[str, dict]:
    """
    Parse content file and extract frontmatter.

    Args:
        file_path: Path to content file
        encoding: File encoding

    Returns:
        Tuple of (content, metadata)
    """
    # Implementation here
    pass

# Type aliases use the 'type' keyword
type PageID = str | int

# Generic classes use PEP 695 syntax
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

# Modern isinstance syntax
if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
    handle_function(node)
```

### Documentation

- Add docstrings to all public functions/classes
- Use Google-style docstrings
- Include type information in docstrings
- Provide examples where helpful

## Testing

### Writing Tests

Bengal has a comprehensive test infrastructure to make writing tests easier and more consistent. See `tests/_testing/README.md` for full documentation.

#### Test Organization

- **Unit tests** (`tests/unit/`): Fast, isolated tests of individual functions/classes
- **Integration tests** (`tests/integration/`): Tests that involve multiple components
- **Test roots** (`tests/roots/`): Minimal, reusable site templates for integration tests

#### Quick Start: Integration Tests with Test Roots

Use the `@pytest.mark.bengal` marker for declarative site setup:

```python
import pytest

@pytest.mark.bengal(testroot="test-basic")
def test_simple_build(site, build_site):
    """Test basic site building."""
    # site is pre-configured from test-basic root
    build_site()

    # Assert on results
    assert len(site.pages) == 1
    assert (site.output_dir / "index.html").exists()


@pytest.mark.bengal(
    testroot="test-baseurl",
    confoverrides={"site.baseurl": "/custom"}
)
def test_custom_baseurl(site):
    """Test with config overrides."""
    assert site.baseurl == "/custom"
```

**Available test roots:**
- `test-basic`: Minimal 1-page site
- `test-baseurl`: Tests baseurl handling
- `test-taxonomy`: 3 pages with tags
- `test-templates`: Template example documentation
- `test-assets`: Custom + theme assets
- `test-cascade`: Nested sections with cascade frontmatter

See `tests/roots/README.md` for full details.

#### CLI Testing

Use the `run_cli()` helper for standardized CLI testing:

```python
from tests._testing.cli import run_cli

def test_version_command():
    """Test version command."""
    result = run_cli(["--version"])

    # Assertions
    result.assert_ok()  # returncode == 0
    assert "Bengal" in result.stdout

    # Errors are automatically stripped of ANSI codes


def test_build_command_failure():
    """Test build command with invalid site."""
    result = run_cli(["site", "build"], cwd="/nonexistent")

    result.assert_fail_with()  # returncode != 0
    result.assert_stderr_contains("not found")
```

#### Output Normalization

Use normalization utilities for deterministic assertions on HTML/JSON:

```python
from tests._testing.normalize import normalize_html, normalize_json

def test_asset_hashing(site, build_site):
    """Test asset hashing in output."""
    build_site()
    html = (site.output_dir / "index.html").read_text()

    # Normalize volatile elements (paths, hashes, timestamps)
    norm_html = normalize_html(html)

    # Assert on stable patterns
    assert 'href="/assets/css/style.HASH.css"' in norm_html
```

#### HTTP Server for Link Testing

Use the `http_server` fixture for ephemeral test servers:

```python
def test_external_links(site, build_site, http_server, tmp_path):
    """Test link checking with ephemeral server."""
    # Create test fixtures
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "test.html").write_text("<h1>Test</h1>")

    # Start server
    base_url = http_server.start(fixtures)

    # Build site with links to server
    # ... configure site to link to base_url ...
    build_site()

    # Assert link checking works
    # ...
```

#### Test Performance and Markers

Bengal uses pytest markers to organize tests:

- `@pytest.mark.slow`: Long-running tests (>5s per test)
- `@pytest.mark.hypothesis`: Property-based tests
- `@pytest.mark.serial`: Must run sequentially
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.network`: Requires internet

**Fast development loop** (skip slow tests):
```bash
# Fast feedback (~20s)
pytest -m "not slow" -n auto

# Full suite
pytest -n auto

# Slow tests only
pytest -m slow
```

#### General Testing Principles

- Write tests for new features
- Ensure edge cases are covered
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Aim for >80% code coverage
- Focus on critical paths
- Test both success and failure cases

Example unit test:
```python
def test_page_extracts_links():
    # Arrange
    page = Page(
        source_path=Path("test.md"),
        content="[link](https://example.com)"
    )

    # Act
    links = page.extract_links()

    # Assert
    assert len(links) == 1
    assert links[0] == "https://example.com"
```

## Areas for Contribution

### High Priority

1. **Plugin System**: Implement hooks for build events
2. **Performance Optimization**: Profile and optimize slow operations
3. **Test Coverage**: Improve test coverage across modules

### Medium Priority

1. **Additional Parsers**: reStructuredText, AsciiDoc support
2. **Theme System**: Enhanced theming capabilities
3. **Asset Pipeline**: Advanced optimization features
4. **CLI Improvements**: Better error messages and help text

### Low Priority

1. **Documentation**: Expand user guides and API docs
2. **Examples**: More example sites and use cases
3. **Integrations**: Deploy scripts for popular hosts
4. **Localization**: Multi-language support

## Architecture Guidelines

### Avoiding God Objects

- Keep classes focused on single responsibilities
- Use composition over inheritance
- Limit dependencies between modules

### Performance Considerations

- Use iterative approaches over deep recursion
- Support parallel processing where possible
- Cache expensive operations
- Profile before optimizing

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log warnings for recoverable errors
- Fail fast for critical errors

### Debugging Template Issues

For template-related debugging, Bengal provides several tools:

- **CLI tools**: `bengal template-dev debug <template>` for interactive debugging
- **Standalone scripts**:
  - `python debug_template_rendering.py [source_file]` for comprehensive template debugging
  - `python debug_macro_error.py` for focused macro testing and validation
  - `python test_macro_step_by_step.py [source_file]` for step-by-step macro syntax validation
- **Template validation**: `bengal template-dev validate <template>` for syntax checking
- **Performance profiling**: `bengal template-dev profile <template>` for performance analysis

The standalone debug scripts are particularly useful for quickly diagnosing template rendering issues during development. Use `debug_macro_error.py` for testing specific macros, `debug_template_rendering.py` for full template analysis, and `test_macro_step_by_step.py` for progressive macro syntax validation.

## Release Process

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Create Git tag
5. Build distribution: `python -m build`
6. Upload to PyPI: `twine upload dist/*`

## Communication

- Submit code changes via Pull Requests
- Report bugs and suggest features via issue tracking
- Document your changes clearly

## Code of Conduct

Be respectful, inclusive, and collaborative.

## Questions?

If you have questions:
- Check the documentation in [ARCHITECTURE.md](ARCHITECTURE.md)
- Review the examples in the `examples/` directory
- Comment on relevant issues
