# Contributing to Bengal SSG

Thank you for your interest in contributing to Bengal! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.12 or higher
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

Bengal uses **Python 3.12+** features and modern syntax:

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

- Write tests for new features
- Ensure edge cases are covered
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

Example:
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

### Test Coverage

- Aim for >80% code coverage
- Focus on critical paths
- Test both success and failure cases

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
