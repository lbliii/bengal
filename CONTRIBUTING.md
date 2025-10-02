# Contributing to Bengal SSG

Thank you for your interest in contributing to Bengal! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip and virtualenv
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/bengal-ssg/bengal.git
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

### 4. Format Code

```bash
# Format with black
black bengal/

# Check with ruff
ruff check bengal/

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

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters
- Use descriptive variable names

Example:
```python
from typing import List, Optional
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
2. **Incremental Builds**: Track changes and rebuild only what's needed
3. **Performance Optimization**: Profile and optimize slow operations
4. **Test Coverage**: Improve test coverage across modules

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

- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Pull Requests**: Submit code changes via Pull Requests

## Code of Conduct

Be respectful, inclusive, and collaborative. We're all here to build something great together.

## Questions?

If you have questions, feel free to:
- Open a GitHub Discussion
- Comment on relevant issues
- Reach out to maintainers

Thank you for contributing to Bengal! 🎉

